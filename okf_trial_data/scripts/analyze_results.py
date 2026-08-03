#!/usr/bin/env python3
"""Publication tables, statistics, and figures for the completed OKF trial."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable, Sequence

import numpy as np
from scipy import stats


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "okf_trial_data"
PACKAGE_SRC = PACKAGE_ROOT / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from okf_trial_data.evaluator import exact_mcnemar, holm_adjust  # noqa: E402


PIPELINES = ("simple_rag", "reranked_simple", "agentic_rag", "self_rag", "flare")
CONDITIONS = ("raw_vector", "okf_hybrid", "okf_native")
LABELS = {
    "simple_rag": "Simple RAG",
    "reranked_simple": "Reranked RAG",
    "agentic_rag": "Agentic RAG",
    "self_rag": "Self-RAG",
    "flare": "FLARE",
    "raw_vector": "Raw vector",
    "okf_hybrid": "OKF hybrid",
    "okf_native": "OKF native",
}

INVALIDATED_RUN_DEVIATION = {
    "date": "2026-08-02",
    "type": "benchmark_semantic_correction_after_partial_generation",
    "description": (
        "A semantic review after an incomplete paid generation run identified "
        "additional gold-label or reference errors. The run was stopped before "
        "judging, declared invalid, and excluded from all reported endpoints. The "
        "corrected benchmark received a new version and content hash before restart."
    ),
    "affects_reported_results": False,
}
SUPERSEDED_BENCHMARK_IDS = {"wmp_okf_pge_97_v1"}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _unique_index(
    rows: list[dict[str, Any]], fields: tuple[str, ...], *, label: str
) -> dict[tuple[Any, ...], dict[str, Any]]:
    indexed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for line_number, row in enumerate(rows, start=1):
        key = tuple(row[field] for field in fields)
        if key in indexed:
            raise RuntimeError(f"duplicate {label} key at row {line_number}: {key}")
        indexed[key] = row
    return indexed


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _percentile(values: Sequence[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _mean(values: Iterable[float | int]) -> float:
    numbers = [float(value) for value in values]
    return statistics.mean(numbers) if numbers else math.nan


def _bootstrap_ci(
    values: Sequence[float], *, repetitions: int = 10_000, seed: int = 42
) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(repetitions, len(array)), replace=True).mean(axis=1)
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))


def _wilcoxon(differences: Sequence[float]) -> float:
    values = np.asarray(differences, dtype=float)
    if np.allclose(values, 0):
        return 1.0
    return float(stats.wilcoxon(values, zero_method="wilcox", alternative="two-sided").pvalue)


def _paired_rows(
    rows: list[dict[str, Any]],
    *,
    pipeline: str,
    treatment: str,
    metric: str,
    answerable: bool | None,
) -> tuple[list[str], list[float], list[float]]:
    subset = [row for row in rows if row["pipeline"] == pipeline]
    if answerable is not None:
        subset = [row for row in subset if bool(row["answerable"]) == answerable]
    indexed = {(row["condition"], row["qid"]): row for row in subset}
    qids = sorted(
        qid
        for condition, qid in indexed
        if condition == "raw_vector"
        and (treatment, qid) in indexed
        and indexed[("raw_vector", qid)].get(metric) is not None
        and indexed[(treatment, qid)].get(metric) is not None
    )
    raw = [float(indexed[("raw_vector", qid)][metric]) for qid in qids]
    treated = [float(indexed[(treatment, qid)][metric]) for qid in qids]
    return qids, raw, treated


def _comparison_table(
    rows: list[dict[str, Any]],
    *,
    treatment: str,
    seed_offset: int,
    pipelines: Sequence[str],
    answerable_count: int,
    multiplicity_family: str | None = None,
) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    raw_p: dict[str, float] = {}
    for index, pipeline in enumerate(pipelines):
        qids, raw, treated = _paired_rows(
            rows,
            pipeline=pipeline,
            treatment=treatment,
            metric="answer_correctness",
            answerable=True,
        )
        if len(qids) != answerable_count:
            raise RuntimeError(
                f"complete-pair gate failed for {pipeline}/{treatment}: "
                f"{len(qids)} != {answerable_count}"
            )
        differences = [right - left for left, right in zip(raw, treated)]
        ci_low, ci_high = _bootstrap_ci(
            differences, seed=42 + seed_offset + index
        )
        p_value = _wilcoxon(differences)
        raw_p[pipeline] = p_value
        table.append(
            {
                "pipeline": pipeline,
                "n_pairs": len(qids),
                "raw_mean": _mean(raw),
                "treatment": treatment,
                "treatment_mean": _mean(treated),
                "mean_delta": _mean(differences),
                "median_delta": statistics.median(differences),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "improved": sum(value > 0 for value in differences),
                "tied": sum(value == 0 for value in differences),
                "worse": sum(value < 0 for value in differences),
                "wilcoxon_p": p_value,
                "holm_p": math.nan,
                "multiplicity_family": multiplicity_family or treatment,
                "multiplicity_family_size": len(pipelines),
            }
        )
    adjusted = holm_adjust(raw_p)
    for row in table:
        row["holm_p"] = adjusted[row["pipeline"]]
    return table


def _pooled_cluster_ci(
    rows: list[dict[str, Any]],
    treatment: str,
    *,
    pipelines: Sequence[str],
    answerable_count: int,
    repetitions: int = 10_000,
) -> dict[str, Any]:
    per_qid: dict[str, list[float]] = {}
    for pipeline in pipelines:
        qids, raw, treated = _paired_rows(
            rows,
            pipeline=pipeline,
            treatment=treatment,
            metric="answer_correctness",
            answerable=True,
        )
        for qid, left, right in zip(qids, raw, treated):
            per_qid.setdefault(qid, []).append(right - left)
    qids = sorted(per_qid)
    if len(qids) != answerable_count or any(
        len(per_qid[qid]) != len(pipelines) for qid in qids
    ):
        raise RuntimeError("pooled question-cluster matrix is incomplete")
    observed = _mean(value for qid in qids for value in per_qid[qid])
    rng = np.random.default_rng(42)
    estimates = []
    for _ in range(repetitions):
        sampled = rng.choice(qids, size=len(qids), replace=True)
        estimates.append(_mean(value for qid in sampled for value in per_qid[qid]))
    return {
        "treatment": treatment,
        "n_question_clusters": len(qids),
        "n_pipeline_question_pairs": len(qids) * len(pipelines),
        "mean_delta": observed,
        "ci_low": _percentile(estimates, 2.5),
        "ci_high": _percentile(estimates, 97.5),
        "bootstrap_repetitions": repetitions,
    }


def _control_table(
    rows: list[dict[str, Any]],
    treatment: str,
    *,
    pipelines: Sequence[str],
    control_count: int,
) -> list[dict[str, Any]]:
    output = []
    for pipeline in pipelines:
        qids, raw, treated = _paired_rows(
            rows,
            pipeline=pipeline,
            treatment=treatment,
            metric="negative_refusal_correct",
            answerable=False,
        )
        if len(qids) != control_count:
            raise RuntimeError(
                f"control-pair gate failed for {pipeline}/{treatment}: "
                f"{len(qids)} != {control_count}"
            )
        raw_binary = [int(value >= 2 / 3) for value in raw]
        treated_binary = [int(value >= 2 / 3) for value in treated]
        test = exact_mcnemar(raw_binary, treated_binary)
        output.append(
            {
                "pipeline": pipeline,
                "treatment": treatment,
                "n_pairs": len(qids),
                "raw_refusal_accuracy": _mean(raw),
                "treatment_refusal_accuracy": _mean(treated),
                "mean_delta": _mean(right - left for left, right in zip(raw, treated)),
                **test,
            }
        )
    return output


def _descriptive_table(
    rows: list[dict[str, Any]],
    *,
    pipelines: Sequence[str],
    conditions: Sequence[str],
    question_count: int,
    answerable_count: int,
    control_count: int,
) -> list[dict[str, Any]]:
    output = []
    for pipeline in pipelines:
        for condition in conditions:
            subset = [
                row for row in rows
                if row["pipeline"] == pipeline and row["condition"] == condition
            ]
            positives = [row for row in subset if row["answerable"]]
            controls = [row for row in subset if not row["answerable"]]
            if len(subset) != question_count:
                raise RuntimeError(
                    f"descriptive cell is incomplete for {pipeline}/{condition}: "
                    f"{len(subset)} != {question_count}"
                )
            if len(positives) != answerable_count:
                raise RuntimeError(f"answerable denominator mismatch for {pipeline}/{condition}")
            if len(controls) != control_count:
                raise RuntimeError(f"control denominator mismatch for {pipeline}/{condition}")
            output.append(
                {
                    "pipeline": pipeline,
                    "condition": condition,
                    "n": len(subset),
                    "n_answerable": len(positives),
                    "n_controls": len(controls),
                    "answer_correctness": _mean(
                        row["answer_correctness"] for row in positives
                    ),
                    "answer_completeness": _mean(
                        row["answer_completeness"] for row in positives
                    ),
                    "groundedness": _mean(
                        row["groundedness"]
                        for row in positives
                        if row["groundedness"] is not None
                    ),
                    "citation_quality": _mean(
                        row["citation_quality"]
                        for row in positives
                        if row["citation_quality"] is not None
                    ),
                    "positive_refusal_rate": _mean(row["refusal_fraction"] for row in positives),
                    "control_refusal_accuracy": _mean(
                        row["negative_refusal_correct"] for row in controls
                    ),
                    "page_hit_at_context": _mean(
                        float(row["retrieval_metrics_at_context"]["page_hit"])
                        for row in positives
                    ),
                    "expected_page_recall_at_context": _mean(
                        row["retrieval_metrics_at_context"]["expected_page_recall"]
                        for row in positives
                    ),
                    "mean_generator_calls": _mean(row["generator_calls"] for row in subset),
                    "median_latency_ms": statistics.median(row["latency_ms"] for row in subset),
                    "p95_latency_ms": _percentile([row["latency_ms"] for row in subset], 95),
                    "mean_generation_cost_usd": _mean(
                        row["generator_cost_usd"] for row in subset
                    ),
                    "mean_judge_cost_usd": _mean(row["judge_cost_usd"] for row in subset),
                    "mean_total_cost_usd": _mean(
                        row["generator_cost_usd"] + row["judge_cost_usd"] for row in subset
                    ),
                }
            )
    return output


def _judge_reliability(
    trials: list[dict[str, Any]], *, terminal_failure_count: int = 0
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in trials:
        grouped.setdefault((row["pipeline"], row["condition"], row["qid"]), []).append(row)
    positive_groups = [
        items for items in grouped.values()
        if items[0]["answerable"]
    ]
    exact = []
    ranges = []
    for items in positive_groups:
        values = [item["outcomes"]["answer_correctness"] for item in items]
        exact.append(len(set(values)) == 1)
        ranges.append(max(values) - min(values))
    return {
        "answer_cells": len(grouped),
        "trial_records": len(trials),
        "schema_retry_count": sum(len(row["attempts"]) - 1 for row in trials),
        "schema_retry_rate": _mean(int(len(row["attempts"]) > 1) for row in trials),
        "parse_failure_count": terminal_failure_count,
        "positive_answer_cells": len(positive_groups),
        "positive_cell_exact_correctness_agreement": _mean(exact),
        "positive_cell_mean_correctness_range": _mean(ranges),
    }


def _markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    header = "| " + " | ".join(fields) + " |"
    separator = "| " + " | ".join("---" for _ in fields) + " |"
    lines = [header, separator]
    for row in rows:
        values = []
        for field in fields:
            value = row[field]
            if isinstance(value, float):
                value = f"{value:.4f}"
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


_DIAGNOSTIC_FIGURE_ARMS = (
    ("raw_vector", "Dense, 256-token limit\n(frozen baseline)", False),
    ("okf_hybrid", "Dense + OKF links\n(confirmatory treatment)", True),
    ("okf_native", "BM25 concepts + OKF links", True),
    ("titan_dense", "Dense, 8192-token limit", False),
    ("bm25_raw", "Plain BM25, no OKF", False),
)


def _diagnostic_figure(
    diagnostics: dict[str, Any] | None, output_dir: Path, plt: Any
) -> Path | None:
    """Plot where the retrieval difference actually comes from.

    Bars are coloured by whether the arm uses any OKF component, which is the
    distinction the figure exists to make: the best-scoring arm uses none.
    """

    if not diagnostics:
        return None
    arms = diagnostics.get("arms", {})
    rows = [(key, label, uses) for key, label, uses in _DIAGNOSTIC_FIGURE_ARMS if key in arms]
    if len(rows) < 2:
        return None
    values = [arms[key]["page_hit_rate"] * 100 for key, _, _ in rows]
    labels = [label for _, label, _ in rows]
    bar_colors = ["#54A24B" if uses else "#4C78A8" for _, _, uses in rows]

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    positions = np.arange(len(rows))
    bars = ax.bar(positions, values, 0.62, color=bar_colors)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.4,
            f"{value:.1f}%",
            ha="center",
            fontsize=9.5,
        )
    ax.set_xticks(positions, labels, fontsize=8.6)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Questions with an expected page retrieved (%)")
    ax.set_title(
        "Where the retrieval difference comes from (top-10, 79 page-annotated questions)"
    )
    ax.grid(axis="y", alpha=0.2)
    handles = [
        plt.Rectangle((0, 0), 1, 1, color="#54A24B"),
        plt.Rectangle((0, 0), 1, 1, color="#4C78A8"),
    ]
    ax.legend(
        handles,
        ["Uses OKF", "No OKF component"],
        frameon=False,
        ncol=1,
        loc="upper left",
        fontsize=9,
    )
    fig.tight_layout()
    path = output_dir / "figure_diagnostic.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _figures(
    descriptive: list[dict[str, Any]],
    primary: list[dict[str, Any]],
    exploratory: list[dict[str, Any]],
    output_dir: Path,
    *,
    pipelines: Sequence[str] = PIPELINES,
    conditions: Sequence[str] = CONDITIONS,
    diagnostics: dict[str, Any] | None = None,
) -> list[str]:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 160,
        }
    )
    colors = {"raw_vector": "#4C78A8", "okf_hybrid": "#F58518", "okf_native": "#54A24B"}
    positions = np.arange(len(pipelines))
    width = 0.24
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for offset, condition in enumerate(conditions):
        values = [
            next(
                row["answer_correctness"]
                for row in descriptive
                if row["pipeline"] == pipeline and row["condition"] == condition
            )
            for pipeline in pipelines
        ]
        ax.bar(
            positions + (offset - 1) * width,
            values,
            width,
            label=LABELS.get(condition, condition),
            color=colors[condition],
        )
    ax.set_xticks(
        positions,
        [LABELS.get(pipeline, pipeline) for pipeline in pipelines],
        rotation=15,
        ha="right",
    )
    ax.set_ylim(1, 5)
    ax.set_ylabel("Gold-aware correctness (1-5)")
    ax.set_title("Answer correctness by RAG pipeline and retrieval condition")
    ax.legend(frameon=False, ncol=3)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    correctness_path = output_dir / "figure_correctness.png"
    fig.savefig(correctness_path, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    combined = [("OKF hybrid", row) for row in primary] + [
        ("OKF native", row) for row in exploratory
    ]
    y = np.arange(len(combined))
    deltas = [row["mean_delta"] for _, row in combined]
    lower = [row["mean_delta"] - row["ci_low"] for _, row in combined]
    upper = [row["ci_high"] - row["mean_delta"] for _, row in combined]
    point_colors = ["#F58518" if label == "OKF hybrid" else "#54A24B" for label, _ in combined]
    for index, (delta, low, high, color) in enumerate(
        zip(deltas, lower, upper, point_colors)
    ):
        ax.errorbar(
            delta,
            y[index],
            xerr=[[low], [high]],
            fmt="o",
            color=color,
            ecolor=color,
            capsize=3,
            zorder=3,
        )
    ax.axvline(0, color="#555555", linewidth=1)
    ax.set_yticks(
        y,
        [f"{label}: {LABELS.get(row['pipeline'], row['pipeline'])}" for label, row in combined],
    )
    ax.set_xlabel("Mean paired correctness difference vs raw vector (95% bootstrap CI)")
    ax.set_title("Pipeline-specific treatment effects")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    effects_path = output_dir / "figure_effects.png"
    fig.savefig(effects_path, bbox_inches="tight")
    plt.close(fig)
    figure_paths = [correctness_path, effects_path]
    diagnostic_path = _diagnostic_figure(diagnostics, output_dir, plt)
    if diagnostic_path is not None:
        figure_paths.append(diagnostic_path)
    if len({path.resolve() for path in figure_paths}) != len(figure_paths):
        raise RuntimeError("figure output paths collide")
    references = []
    for path in figure_paths:
        try:
            references.append(path.relative_to(PACKAGE_ROOT).as_posix())
        except ValueError:
            references.append(path.name)
    return references


def _validate_run_and_build_design(
    *,
    results_dir: Path,
    benchmark_path: Path,
    gold_audit_path: Path,
    retrieval: dict[str, Any],
    generation: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    trials: list[dict[str, Any]],
) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...], int]:
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    questions = list(benchmark["questions"])
    qids = [question["qid"] for question in questions]
    if len(qids) != len(set(qids)):
        raise RuntimeError("benchmark contains duplicate qids")
    question_by_qid = {question["qid"]: question for question in questions}
    question_count = len(questions)
    answerable_count = sum(bool(question["answerable"]) for question in questions)
    control_count = question_count - answerable_count
    declared_counts = benchmark.get("counts", {})
    expected_declared = {
        "total": question_count,
        "answerable": answerable_count,
        "negative_or_control": control_count,
    }
    for key, value in expected_declared.items():
        if key in declared_counts and int(declared_counts[key]) != value:
            raise RuntimeError(f"benchmark declared count {key} is stale")
    benchmark_id = str(benchmark["benchmark_id"])
    if benchmark_id in SUPERSEDED_BENCHMARK_IDS:
        raise RuntimeError(
            f"benchmark {benchmark_id} is explicitly superseded after semantic review"
        )

    run_manifest_path = results_dir / "run_manifest.json"
    judge_manifest_path = results_dir / "judge_manifest.json"
    schedule_path = results_dir / "schedule.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    judge_manifest = json.loads(judge_manifest_path.read_text(encoding="utf-8"))
    pipelines = tuple(str(value) for value in run_manifest["systems"])
    conditions = tuple(str(value) for value in run_manifest["conditions"])
    if len(pipelines) != len(set(pipelines)) or set(pipelines) != set(PIPELINES):
        raise RuntimeError(f"run pipelines differ from the frozen study: {pipelines}")
    if len(conditions) != len(set(conditions)) or set(conditions) != set(CONDITIONS):
        raise RuntimeError(f"run conditions differ from the frozen study: {conditions}")

    benchmark_digest = _sha256(benchmark_path)
    manifest_expectations = {
        "benchmark_id": benchmark_id,
        "benchmark_sha256": benchmark_digest,
        "ordered_qid_sha256": _json_sha256(qids),
        "question_count": question_count,
        "answerable_count": answerable_count,
        "control_count": control_count,
        "expected_records": question_count * len(pipelines) * len(conditions),
        "schedule_sha256": _sha256(schedule_path),
    }
    for key, expected in manifest_expectations.items():
        if run_manifest.get(key) != expected:
            raise RuntimeError(
                f"run manifest mismatch for {key}: {run_manifest.get(key)!r} != {expected!r}"
            )

    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    schedule_index = _unique_index(
        schedule, ("pipeline", "condition", "qid"), label="schedule"
    )
    expected_cells = {
        (pipeline, condition, qid)
        for pipeline in pipelines
        for condition in conditions
        for qid in qids
    }
    if set(schedule_index) != expected_cells:
        raise RuntimeError("schedule is not the exact benchmark x pipeline x condition product")
    if sorted(int(row["schedule_index"]) for row in schedule) != list(range(len(schedule))):
        raise RuntimeError("schedule_index values are not a complete zero-based sequence")

    generated = _unique_index(
        generation, ("pipeline", "condition", "qid"), label="generation"
    )
    scored = _unique_index(scores, ("pipeline", "condition", "qid"), label="score")
    if set(generated) != expected_cells or set(scored) != expected_cells:
        raise RuntimeError("generation or score records fail exact Cartesian completeness")
    for key in expected_cells:
        question = question_by_qid[key[2]]
        if bool(generated[key]["answerable"]) != bool(question["answerable"]):
            raise RuntimeError(f"generation answerability differs from benchmark: {key}")
        if bool(scored[key]["answerable"]) != bool(question["answerable"]):
            raise RuntimeError(f"score answerability differs from benchmark: {key}")
        if scored[key]["answer_sha256"] != generated[key]["answer_sha256"]:
            raise RuntimeError(f"answer hash mismatch: {key}")

    trials_per_answer = int(judge_manifest["trials_per_answer"])
    if trials_per_answer < 1:
        raise RuntimeError("judge manifest has an invalid trials-per-answer value")
    trial_index = _unique_index(
        trials,
        ("pipeline", "condition", "qid", "trial_index"),
        label="judge trial",
    )
    expected_trials = {
        (*cell, trial_number)
        for cell in expected_cells
        for trial_number in range(1, trials_per_answer + 1)
    }
    if set(trial_index) != expected_trials:
        raise RuntimeError("judge records fail exact answer-cell x trial completeness")
    for key, trial in trial_index.items():
        cell = key[:3]
        if trial["answer_sha256"] != generated[cell]["answer_sha256"]:
            raise RuntimeError(f"judge answer hash mismatch: {key}")
        if bool(trial["answerable"]) != bool(question_by_qid[cell[2]]["answerable"]):
            raise RuntimeError(f"judge answerability differs from benchmark: {key}")
    judge_expectations = {
        "generation_records_sha256": _sha256(results_dir / "generation_records.jsonl"),
        "generation_manifest_sha256": _sha256(run_manifest_path),
        "answer_count": len(expected_cells),
        "expected_trial_records": len(expected_trials),
    }
    for key, expected in judge_expectations.items():
        if judge_manifest.get(key) != expected:
            raise RuntimeError(
                f"judge manifest mismatch for {key}: {judge_manifest.get(key)!r} != {expected!r}"
            )
    if len(generation) != len(expected_cells) or len(scores) != len(expected_cells):
        raise RuntimeError("answer-record counts differ from the exact cell set")
    if len(trials) != len(expected_trials):
        raise RuntimeError("judge-trial count differs from the exact trial set")
    for key, score in scored.items():
        if int(score.get("judge_trials", -1)) != trials_per_answer:
            raise RuntimeError(f"score does not aggregate every judge trial: {key}")

    if retrieval.get("benchmark_id") != benchmark_id:
        raise RuntimeError("retrieval summary benchmark ID differs from the run")
    if retrieval.get("benchmark_sha256") != benchmark_digest:
        raise RuntimeError("retrieval summary benchmark hash differs from the run")
    required_retrieval = {
        "raw_vector",
        "okf_hybrid",
        "okf_native",
        "raw_vs_okf_hybrid_page_hit_mcnemar",
        "raw_vs_okf_native_page_hit_mcnemar",
    }
    missing_retrieval = sorted(required_retrieval - set(retrieval.get("results", {})))
    if missing_retrieval:
        raise RuntimeError(f"retrieval summary is incomplete: {missing_retrieval}")

    audit = json.loads(gold_audit_path.read_text(encoding="utf-8"))
    audit_expectations = {
        "benchmark_id": benchmark_id,
        "benchmark_sha256": benchmark_digest,
        "question_count": question_count,
        "answerable_count": answerable_count,
        "control_count": control_count,
    }
    for key, expected in audit_expectations.items():
        if audit.get(key) != expected:
            raise RuntimeError(f"gold-audit summary mismatch for {key}")
    if int(audit.get("automated_flag_count", -1)) != 0:
        raise RuntimeError("gold-audit summary still contains automated flags")

    deviations = list(benchmark.get("curation", {}).get("deviations", []))
    if not any(
        isinstance(item, dict) and item.get("type") == INVALIDATED_RUN_DEVIATION["type"]
        for item in deviations
    ):
        deviations.append(INVALIDATED_RUN_DEVIATION)
    design = {
        "benchmark_id": benchmark_id,
        "benchmark_sha256": benchmark_digest,
        "question_count": question_count,
        "answerable_count": answerable_count,
        "control_count": control_count,
        "pipeline_count": len(pipelines),
        "pipelines": list(pipelines),
        "condition_count": len(conditions),
        "conditions": list(conditions),
        "confirmatory_cells": question_count * len(pipelines) * 2,
        "exploratory_cells": question_count * len(pipelines),
        "judge_trials_per_answer": trials_per_answer,
        "human_validation_status": audit.get("human_validation_status", "pending"),
        "gold_audit_sha256": _sha256(gold_audit_path),
        "protocol_deviations": deviations,
        "superseded_partial_run_included": False,
    }
    return design, pipelines, conditions, trials_per_answer


_DIAGNOSTIC_ARM_ORDER = (
    ("raw_vector", "Dense, all-MiniLM-L6-v2 (256-token window)", "none"),
    ("titan_dense", "Dense, Titan v2 (8192-token window)", "none"),
    ("bm25_raw", "BM25 over raw chunks", "none"),
    ("rrf_bm25_titan", "RRF fusion of BM25 and Titan", "none"),
    ("okf_hybrid", "MiniLM seeds + one-hop OKF links", "yes"),
    ("okf_native", "Weighted BM25 over concepts + OKF links", "yes"),
    ("okf_evidence_only", "OKF consumer, frontmatter removed", "yes"),
    ("bm25_raw_adjacent", "BM25 + adjacency from chunk ordinal", "none"),
    ("titan_dense_adjacent", "Titan + adjacency from chunk ordinal", "none"),
)


_DIAGNOSTIC_CONTRAST_ORDER = (
    "confirmatory: dense_minilm -> okf_hybrid",
    "truncation effect: dense_minilm -> dense_titan",
    "lexical effect: dense_minilm -> bm25_raw",
    "lexical vs fair dense: dense_titan -> bm25_raw",
    "does OKF beat plain BM25: bm25_raw -> okf_native",
    "OKF frontmatter: okf_evidence_only -> okf_native",
    "adjacency without OKF: bm25_raw -> bm25_raw_adjacent",
    "adjacency on fair dense: dense_titan -> dense_titan_adjacent",
    "fusion: bm25_raw -> rrf_bm25_titan",
)


def _diagnostic_report(diagnostics: dict[str, Any] | None) -> list[str]:
    """Render the exploratory confound-decomposition tables."""

    if not diagnostics:
        return []
    arms = diagnostics.get("arms", {})
    lines = [
        "## Exploratory: retrieval confound decomposition",
        "",
        "Added after the frozen retrieval screen (protocol section 4.6). These arms",
        "vary one factor at a time so the retrieval difference can be attributed.",
        "`OKF?` states whether the arm uses any OKF component at all.",
        "",
        "| Arm | Description | OKF? | Page hit | Recall | MRR | nDCG@10 | Median ms |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, description, uses_okf in _DIAGNOSTIC_ARM_ORDER:
        arm = arms.get(key)
        if not arm:
            continue
        latency = arm.get("median_latency_ms")
        latency_text = f"{latency:.2f}" if isinstance(latency, (int, float)) else "frozen run"
        lines.append(
            f"| `{key}` | {description} | {uses_okf} | "
            f"{arm['page_hit_rate']:.4f} | {arm['mean_expected_page_recall']:.4f} | "
            f"{arm['mean_reciprocal_rank']:.4f} | {arm['mean_ndcg_at_k']:.4f} | {latency_text} |"
        )
    lines += [
        "",
        "| Contrast | only A | only B | McNemar p | Holm p | Recall delta [95% CI] |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    contrasts = diagnostics.get("contrasts", {})
    # Explanatory order, not the JSON's alphabetical key order.
    ordered = [key for key in _DIAGNOSTIC_CONTRAST_ORDER if key in contrasts]
    ordered += [key for key in contrasts if key not in _DIAGNOSTIC_CONTRAST_ORDER]
    for label in ordered:
        result = contrasts[label]
        mcnemar = result["page_hit_mcnemar"]
        delta = result["recall_delta"]
        holm = result.get("page_hit_p_holm")
        holm_text = f"{holm:.4f}" if isinstance(holm, (int, float)) else "n/a"
        lines.append(
            f"| {label} | {mcnemar['raw_only_correct']} | {mcnemar['okf_only_correct']} | "
            f"{mcnemar['p_value']:.2e} | {holm_text} | "
            f"{delta['mean_difference']:+.4f} [{delta['ci_low']:+.4f}, {delta['ci_high']:+.4f}] |"
        )
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/full",
    )
    parser.add_argument(
        "--retrieval-summary",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/retrieval/retrieval_summary.json",
    )
    parser.add_argument(
        "--retrieval-diagnostics",
        type=Path,
        default=REPO_ROOT
        / "okf_trial_data/results/retrieval_diagnostics/diagnostic_summary.json",
        help=(
            "post-hoc confound-decomposition arms (see protocol section 4.6). "
            "Exploratory; carries its own multiplicity family."
        ),
    )
    parser.add_argument(
        "--embedding-truncation",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/embedding_truncation.json",
        help="measured input-window truncation for the frozen dense encoder",
    )
    parser.add_argument(
        "--build-metrics",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/build_metrics.json",
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=PACKAGE_ROOT / "data/benchmark_questions.json",
    )
    parser.add_argument(
        "--gold-audit-summary",
        type=Path,
        default=PACKAGE_ROOT / "data/gold_audit_summary.json",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    output_dir = args.output_dir or (args.results_dir / "analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    generation = _load_jsonl(args.results_dir / "generation_records.jsonl")
    scores = _load_jsonl(args.results_dir / "answer_scores.jsonl")
    trials = _load_jsonl(args.results_dir / "judge_trial_records.jsonl")
    retrieval = json.loads(args.retrieval_summary.read_text(encoding="utf-8"))
    # The diagnostic arms are exploratory and were produced after the frozen
    # retrieval screen. They are attached verbatim so the manuscript can attribute
    # the observed retrieval differences instead of crediting them to OKF.
    diagnostics: dict[str, Any] | None = None
    if args.retrieval_diagnostics and args.retrieval_diagnostics.exists():
        diagnostics = json.loads(args.retrieval_diagnostics.read_text(encoding="utf-8"))
        if diagnostics.get("benchmark_sha256") != _sha256(args.benchmark):
            raise RuntimeError(
                "retrieval diagnostics were computed against a different benchmark hash"
            )
    truncation: dict[str, Any] | None = None
    if args.embedding_truncation and args.embedding_truncation.exists():
        truncation = json.loads(args.embedding_truncation.read_text(encoding="utf-8"))
    study_design, pipelines, conditions, trials_per_answer = _validate_run_and_build_design(
        results_dir=args.results_dir,
        benchmark_path=args.benchmark,
        gold_audit_path=args.gold_audit_summary,
        retrieval=retrieval,
        generation=generation,
        scores=scores,
        trials=trials,
    )
    answerable_count = int(study_design["answerable_count"])
    control_count = int(study_design["control_count"])
    question_count = int(study_design["question_count"])
    generated = _unique_index(
        generation, ("pipeline", "condition", "qid"), label="generation"
    )
    merged = []
    for score in scores:
        key = (score["pipeline"], score["condition"], score["qid"])
        if key not in generated:
            raise RuntimeError(f"score has no generation record: {key}")
        if score["answer_sha256"] != generated[key]["answer_sha256"]:
            raise RuntimeError(f"answer hash mismatch: {key}")
        merged.append({**generated[key], **score})

    primary = _comparison_table(
        merged,
        treatment="okf_hybrid",
        seed_offset=0,
        pipelines=pipelines,
        answerable_count=answerable_count,
        multiplicity_family="confirmatory_raw_vs_okf_hybrid",
    )
    exploratory = _comparison_table(
        merged,
        treatment="okf_native",
        seed_offset=100,
        pipelines=pipelines,
        answerable_count=answerable_count,
        multiplicity_family="exploratory_raw_vs_okf_native",
    )
    controls = _control_table(
        merged,
        "okf_hybrid",
        pipelines=pipelines,
        control_count=control_count,
    ) + _control_table(
        merged,
        "okf_native",
        pipelines=pipelines,
        control_count=control_count,
    )
    descriptive = _descriptive_table(
        merged,
        pipelines=pipelines,
        conditions=conditions,
        question_count=question_count,
        answerable_count=answerable_count,
        control_count=control_count,
    )
    failure_path = args.results_dir / "judge_failures.jsonl"
    terminal_failure_count = len(_load_jsonl(failure_path)) if failure_path.is_file() else 0
    reliability = _judge_reliability(
        trials, terminal_failure_count=terminal_failure_count
    )
    build_metrics = json.loads(args.build_metrics.read_text(encoding="utf-8"))
    pooled = [
        _pooled_cluster_ci(
            merged,
            "okf_hybrid",
            pipelines=pipelines,
            answerable_count=answerable_count,
        ),
        _pooled_cluster_ci(
            merged,
            "okf_native",
            pipelines=pipelines,
            answerable_count=answerable_count,
        ),
    ]
    costs = {
        "generation_usd": sum(row["generator_cost_usd"] for row in generation),
        "judging_usd": sum(row["judge_cost_usd"] for row in scores),
    }
    costs["total_usd"] = costs["generation_usd"] + costs["judging_usd"]

    _write_csv(output_dir / "primary_raw_vs_okf_hybrid.csv", primary)
    _write_csv(output_dir / "exploratory_raw_vs_okf_native.csv", exploratory)
    _write_csv(output_dir / "control_results.csv", controls)
    _write_csv(output_dir / "descriptive_results.csv", descriptive)
    figures = _figures(
        descriptive,
        primary,
        exploratory,
        output_dir,
        pipelines=pipelines,
        conditions=conditions,
        diagnostics=diagnostics,
    )
    summary = {
        "completion": {
            "generation_records": len(generation),
            "answer_scores": len(scores),
            "judge_trial_records": len(trials),
            "complete": True,
        },
        "study_design": study_design,
        "primary_raw_vs_okf_hybrid": primary,
        "exploratory_raw_vs_okf_native": exploratory,
        "pooled_cluster_bootstrap": pooled,
        "controls": controls,
        "descriptive": descriptive,
        "retrieval_only": retrieval,
        "retrieval_diagnostics": diagnostics,
        "embedding_truncation": truncation,
        "bundle_build": build_metrics,
        "judge_reliability": reliability,
        "costs": costs,
        "figures": figures,
    }
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = [
        "# OKF trial analysis tables",
        "",
        "## Confirmatory: OKF hybrid minus raw vector",
        "",
        _markdown_table(
            primary,
            [
                "pipeline", "n_pairs", "raw_mean", "treatment_mean", "mean_delta",
                "ci_low", "ci_high", "wilcoxon_p", "holm_p",
            ],
        ),
        "",
        "## Exploratory: OKF native minus raw vector",
        "",
        _markdown_table(
            exploratory,
            [
                "pipeline", "n_pairs", "raw_mean", "treatment_mean", "mean_delta",
                "ci_low", "ci_high", "wilcoxon_p", "holm_p",
            ],
        ),
        "",
        *_diagnostic_report(diagnostics),
        "## Run integrity",
        "",
        f"- Complete generated answers: {len(generation):,}",
        f"- Questions: {question_count:,} ({answerable_count:,} answerable; {control_count:,} controls)",
        f"- Answer cells: {len(generation):,} ({len(pipelines)} pipelines x {len(conditions)} conditions x {question_count} questions)",
        f"- Complete valid judge trials: {len(trials):,} ({trials_per_answer} per answer cell)",
        f"- Schema retries: {reliability['schema_retry_count']}",
        f"- Parse failures: {reliability['parse_failure_count']}",
        f"- Total measured API cost: ${costs['total_usd']:.2f}",
        "",
    ]
    (output_dir / "TABLES.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"primary": primary, "pooled": pooled, "costs": costs}, indent=2))
    print(output_dir)


if __name__ == "__main__":
    main()
