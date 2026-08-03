#!/usr/bin/env python3
"""End-to-end A/B: strong hybrid RAG versus the same hybrid plus OKF.

The comparison
--------------
Arm A is a conventional strong baseline: BM25 and dense retrieval over the
document's chunks, fused by reciprocal rank, then cross-encoder reranked.

Arm B is **arm A plus one extra source**: the same BM25 and dense chunk
retrievers, plus a lexical retriever over the OKF bundle, fused the same way and
reranked by the same model. Because B differs from A only by the presence of the
OKF source, the difference measures what OKF adds on top of a baseline that is
already good, rather than on top of a weak one.

Two OKF variants are run so the granularity question is not begged:

``hybrid_plus_okf_topic``  the topic-structured bundle (one concept per heading,
                           nested, real parent/child/sibling links)
``hybrid_plus_okf_chain``  the chunk-preserving bundle (one concept per chunk,
                           previous/next links)

Everything else is held fixed across arms: corpus (PG&E only), questions,
overfetch, reranker, context token budget, generator, prompts, temperature, and
the blinded gold-aware judge. The pipeline itself is the repository's existing
``reranked_simple`` system, unmodified - only the candidate source is swapped, so
no generation or prompting difference can explain a result.

Stages are resumable and append-only. Rerunning skips completed cells.

Usage
-----
    scripts/with_experiment_env.sh .venv/bin/python \\
        scripts/run_hybrid_ab_experiment.py --stage all
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
for source_root in (REPO_ROOT / "okf_trial_data/src", REPO_ROOT / "eval_harness/src"):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from okf_trial_data.evaluator import (  # noqa: E402
    JudgeRetriesExhausted,
    PairedDifference,
    build_gold_aware_judge_prompt,
    cluster_bootstrap_mean_difference,
    derive_outcomes,
    exact_mcnemar,
    holm_adjust,
    run_strict_judge,
)
from okf_trial_data.fair_baselines import BM25RawRetriever, load_raw_chunks  # noqa: E402
from okf_trial_data.harness_adapter import (  # noqa: E402
    CorpusEvidenceIndex,
    load_benchmark,
    retrieval_outcomes,
    to_harness_question,
)
from okf_trial_data.okf_bundle import OKFBundle  # noqa: E402
from okf_trial_data.okf_retrievers import OKFNativeRetriever  # noqa: E402

BENCHMARK = REPO_ROOT / "okf_trial_data/data/benchmark_questions.json"
CHAIN_BUNDLE = REPO_ROOT / "okf_trial_data/data/okf_bundles/wmp_all_v0_2"
TOPIC_BUNDLE = REPO_ROOT / "okf_trial_data/data/okf_bundles/pge_topics_v0_2"
CORPUS_DIR = REPO_ROOT / "eval_harness/data/corpora/pge_2026_2028_wmp"
CORPUS = "PGE"
PIPELINE = "reranked_simple"

ARMS = ("hybrid_rag", "hybrid_plus_okf_topic", "hybrid_plus_okf_chain")
CONTRASTS = [
    ("hybrid RAG -> hybrid + OKF topics", "hybrid_rag", "hybrid_plus_okf_topic"),
    ("hybrid RAG -> hybrid + OKF chain", "hybrid_rag", "hybrid_plus_okf_chain"),
]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Retrieval arms
# ---------------------------------------------------------------------------


def _rrf(ranked_lists: Sequence[Sequence[str]], *, k: float = 60.0) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, uid in enumerate(ranked, start=1):
            scores[uid] = scores.get(uid, 0.0) + 1.0 / (k + rank)
    return [uid for uid, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


class FusionHarnessRetriever:
    """Duck-typed harness retriever exposing fused candidates as ``dense_search``.

    Reranking and context packing are delegated to the real retriever so both
    arms share one ranking and budget policy.
    """

    def __init__(
        self,
        base: Any,
        chunk_bm25: BM25RawRetriever,
        units: Mapping[str, Any],
        *,
        okf: OKFNativeRetriever | None = None,
        okf_units: Mapping[str, Any] | None = None,
        okf_seed_k: int = 25,
    ) -> None:
        self.base_retriever = base
        self.config = base.config
        self.reranker = base.reranker
        self.chunk_bm25 = chunk_bm25
        self.units = dict(units)
        if okf_units:
            self.units.update(okf_units)
        self.okf = okf
        self.okf_seed_k = okf_seed_k

    def rerank(self, query: str, candidates: list[Any], **kwargs: Any) -> list[Any]:
        return self.base_retriever.rerank(query, candidates, **kwargs)

    def get_context(self, candidates: list[Any], token_budget: int = 2200):
        return self.base_retriever.get_context(candidates, token_budget)

    def close(self) -> None:
        return None

    def dense_search(self, query: str, corpus: str, top_k: int = 25) -> list[Any]:
        from evaluation.models import RetrievedChunk

        dense = [hit.chunk_id for hit in self.base_retriever.dense_search(query, corpus, top_k=top_k)]
        lexical = [uid for uid, _ in self.chunk_bm25.ranked(query, corpus, top_k)]
        lists = [dense, lexical]
        if self.okf is not None:
            hits = self.okf.search(
                query, corpus=corpus, top_k=self.okf_seed_k,
                seed_k=self.okf_seed_k, max_link_depth=0,
            )
            lists.append([hit.concept_id for hit in hits])
        fused = _rrf(lists)[:top_k]
        return [RetrievedChunk(**self.units[uid]) for uid in fused if uid in self.units]


def _chunk_payload(chunk: Any) -> dict[str, Any]:
    pages = [p for p in (chunk.metadata or {}).get("pages", []) if isinstance(p, int)]
    if not pages and chunk.page_number is not None:
        pages = [chunk.page_number]
    return {
        "chunk_id": chunk.chunk_id,
        "corpus": chunk.corpus,
        "text": chunk.text,
        "score": 0.0,
        "rerank_score": None,
        "page_number": chunk.page_number,
        "section": chunk.section,
        "document_name": chunk.document_name,
        "metadata": {"pages": pages, "source": "chunk"},
    }


def _concept_payload(concept: Any) -> dict[str, Any]:
    pages = [p for p in (concept.frontmatter.get("page_numbers") or []) if isinstance(p, int)]
    return {
        "chunk_id": concept.concept_id,
        "corpus": concept.corpus,
        "text": concept.evidence,
        "score": 0.0,
        "rerank_score": None,
        "page_number": pages[0] if pages else None,
        "section": concept.frontmatter.get("section_number"),
        "document_name": concept.frontmatter.get("document_name"),
        "metadata": {
            "pages": pages,
            "source": "okf",
            "okf_title": concept.frontmatter.get("title"),
            "okf_level": concept.frontmatter.get("outline_level"),
        },
    }


def build_arms(config: Any) -> tuple[dict[str, Any], Any]:
    from evaluation.retriever import get_retriever

    base = get_retriever(config)
    raw_chunks = [c for c in load_raw_chunks() if c.corpus == CORPUS]
    chunk_bm25 = BM25RawRetriever(raw_chunks)
    chunk_units = {c.chunk_id: _chunk_payload(c) for c in raw_chunks}

    topic_bundle = OKFBundle.load(TOPIC_BUNDLE)
    topic_bundle.verify_integrity()
    chain_bundle = OKFBundle.load(CHAIN_BUNDLE)
    topic_units = {
        c.concept_id: _concept_payload(c) for c in topic_bundle if c.corpus == CORPUS
    }
    chain_units = {
        c.concept_id: _concept_payload(c) for c in chain_bundle if c.corpus == CORPUS
    }

    arms = {
        "hybrid_rag": FusionHarnessRetriever(base, chunk_bm25, chunk_units),
        "hybrid_plus_okf_topic": FusionHarnessRetriever(
            base, chunk_bm25, chunk_units,
            okf=OKFNativeRetriever(topic_bundle, link_decay=0.35), okf_units=topic_units,
        ),
        "hybrid_plus_okf_chain": FusionHarnessRetriever(
            base, chunk_bm25, chunk_units,
            okf=OKFNativeRetriever(chain_bundle, link_decay=0.35), okf_units=chain_units,
        ),
    }
    return arms, base


# ---------------------------------------------------------------------------
# Stage 1: generation
# ---------------------------------------------------------------------------


def stage_generate(args: argparse.Namespace, questions: Sequence[Mapping[str, Any]]) -> None:
    from evaluation.config import load_config, set_global_seed
    from evaluation.generator import get_generator
    from evaluation.systems import build_system

    config = load_config(REPO_ROOT / "eval_harness/eval_config.yaml")
    config.retriever.device = "cpu"
    config.generator.backend = args.generator_backend
    set_global_seed(42)

    arms, base = build_arms(config)
    generator = get_generator(config, args.generator_backend)

    path = args.output_dir / "ab_generation.jsonl"
    done = {(r["arm"], r["qid"]) for r in _read_jsonl(path)}
    todo = [(arm, q) for q in questions for arm in ARMS if (arm, q["qid"]) not in done]
    print(f"[generate] backend={args.generator_backend} pending={len(todo)} "
          f"complete={len(done)}/{len(ARMS) * len(questions)}")

    spend = 0.0
    for index, (arm, question) in enumerate(todo, start=1):
        system = build_system(PIPELINE, config, arms[arm], generator)
        harness_question = to_harness_question(question)
        started = time.perf_counter()
        record = system.run(harness_question, CORPUS)
        elapsed = (time.perf_counter() - started) * 1000.0
        included = [
            chunk.model_dump() if hasattr(chunk, "model_dump") else dict(chunk)
            for chunk in record.retrieved_chunks
        ]
        okf_units = sum(1 for c in included if (c.get("metadata") or {}).get("source") == "okf")
        row = {
            "arm": arm,
            "pipeline": PIPELINE,
            "qid": question["qid"],
            "question": question["question"],
            "answerable": bool(question["answerable"]),
            "category": question.get("category"),
            "expected_pages": question.get("expected_pages") or [],
            "reference_answer": question.get("reference_answer", ""),
            "answer_text": record.answer_text,
            "answer_sha256": _sha256_text(record.answer_text),
            "citations": list(record.citations or []),
            "retrieved_chunk_ids": [c["chunk_id"] for c in included],
            "context_units": len(included),
            "context_units_from_okf": okf_units,
            "retrieval_metrics_at_context": retrieval_outcomes(
                included, question.get("expected_pages") or []
            ),
            # AnswerRecord exposes cost, calls and latency but not token counts,
            # so tokens are recorded as null rather than 0.
            "generator_input_tokens": None,
            "generator_output_tokens": None,
            "generator_cost_usd": float(record.generator_cost_usd or 0.0),
            "generator_calls": int(record.generator_calls or 0),
            "latency_ms": elapsed,
        }
        spend += row["generator_cost_usd"]
        _append_jsonl(path, row)
        if index % 20 == 0 or index == len(todo):
            print(f"[generate] {index}/{len(todo)} spend=${spend:.2f}")
    base.close()
    print(f"[generate] done, spend=${spend:.2f} -> {path}")


# ---------------------------------------------------------------------------
# Stage 2: judging
# ---------------------------------------------------------------------------


def stage_judge(args: argparse.Namespace) -> None:
    judging = _load_module(Path(__file__).resolve().parent / "run_judging.py", "_run_judging")

    generation = _read_jsonl(args.output_dir / "ab_generation.jsonl")
    if not generation:
        raise SystemExit("no generation records; run --stage generate first")
    evidence = CorpusEvidenceIndex.load(CORPUS_DIR)

    trials_path = args.output_dir / "ab_judge_trials.jsonl"
    failures_path = args.output_dir / "ab_judge_failures.jsonl"
    existing = _read_jsonl(trials_path)
    done = {(r["arm"], r["qid"], r["trial"]) for r in existing}

    client = None
    judge_model = args.judge_model
    if args.judge_backend == "bedrock":
        from evaluation.config import load_config

        config = load_config(REPO_ROOT / "eval_harness/eval_config.yaml")
        client = judging.BedrockStructuredJudgeClient(config)
        judge_model = client.model_id

    pending = [
        (row, trial)
        for row in generation
        for trial in range(1, args.trials + 1)
        if (row["arm"], row["qid"], trial) not in done
    ]
    print(f"[judge] pending={len(pending)} complete={len(done)}")

    spend = 0.0
    for index, (row, trial) in enumerate(pending, start=1):
        # The evaluation id is opaque and carries no arm or system label.
        evaluation_id = _sha256_text(f"{row['arm']}|{row['qid']}|{trial}|{row['answer_sha256']}")[:24]
        gold = evidence.gold_evidence(
            row["expected_pages"], row.get("reference_answer", "")
        ) if row["expected_pages"] else []
        prompt = build_gold_aware_judge_prompt(
            evaluation_id=evaluation_id,
            question=row["question"],
            answerable=row["answerable"],
            reference_answer=row.get("reference_answer", ""),
            gold_evidence=gold,
            system_answer=row["answer_text"],
            resolved_citations=evidence.resolve_citations(row.get("citations") or []),
        )
        if client is not None:
            call = judging.BedrockJudgeCall(client, evaluation_id)
        else:
            call = judging.MockJudgeCall(
                evaluation_id=evaluation_id,
                answerable=row["answerable"],
                answer_text=row["answer_text"],
            )
        try:
            run = run_strict_judge(
                call, prompt,
                expected_evaluation_id=evaluation_id,
                answerable=row["answerable"],
                max_attempts=args.max_attempts,
            )
        except JudgeRetriesExhausted as exc:
            _append_jsonl(failures_path, {
                "arm": row["arm"], "qid": row["qid"], "trial": trial,
                "error": str(exc)[:500],
            })
            continue
        outcomes = derive_outcomes(run.assessment, answerable=row["answerable"])
        # Every invocation bills, including schema-repair retries.
        invocations = list(getattr(call, "invocations", []))
        cost = sum(float(i.get("cost_usd", 0.0) or 0.0) for i in invocations)
        meta = {
            "input_tokens": sum(int(i.get("input_tokens", 0) or 0) for i in invocations),
            "output_tokens": sum(int(i.get("output_tokens", 0) or 0) for i in invocations),
            "model_id": invocations[-1].get("model_id") if invocations else None,
        }
        spend += cost
        # Scores come from derive_outcomes, never from the raw assessment: that is
        # where the predeclared branches live. Correctness is None for gold-negative
        # controls, and an inappropriate refusal on an answerable question takes the
        # predeclared floor of 1.0 rather than being dropped or imputed.
        _append_jsonl(trials_path, {
            "arm": row["arm"], "qid": row["qid"], "trial": trial,
            "evaluation_id": evaluation_id,
            "answer_sha256": row["answer_sha256"],
            "answerable": row["answerable"],
            "response_disposition": run.assessment.response_disposition,
            "correctness": outcomes.answer_correctness,
            "completeness": outcomes.answer_completeness,
            "groundedness": outcomes.groundedness,
            "citation_quality": outcomes.citation_quality,
            "refusal_correct": outcomes.negative_refusal_correct,
            "attempts": len(run.attempts),
            "judge_cost_usd": cost,
            "judge_input_tokens": int(meta.get("input_tokens", 0) or 0),
            "judge_output_tokens": int(meta.get("output_tokens", 0) or 0),
            "judge_model_id": meta.get("model_id"),
            "judge_invocations": len(invocations),
        })
        if index % 50 == 0 or index == len(pending):
            print(f"[judge] {index}/{len(pending)} spend=${spend:.2f}")
    print(f"[judge] done, spend=${spend:.2f} -> {trials_path}")


# ---------------------------------------------------------------------------
# Stage 3: analysis
# ---------------------------------------------------------------------------


def _judge_model_used(args: argparse.Namespace) -> str:
    """The judge model actually used, read from the harness config when live."""

    if args.judge_backend != "bedrock":
        return "mock-strict-judge"
    from evaluation.config import load_config

    return load_config(REPO_ROOT / "eval_harness/eval_config.yaml").judge.model_id


def stage_analyze(args: argparse.Namespace) -> None:
    generation = _read_jsonl(args.output_dir / "ab_generation.jsonl")
    trials = _read_jsonl(args.output_dir / "ab_judge_trials.jsonl")
    if not trials:
        raise SystemExit("no judge trials; run --stage judge first")

    dimensions = ("correctness", "completeness", "groundedness", "citation_quality")
    per_dimension: dict[str, dict[tuple[str, str], list[float]]] = {d: {} for d in dimensions}
    refusals: dict[tuple[str, str], list[int]] = {}
    for row in trials:
        key = (row["arm"], row["qid"])
        for dimension in dimensions:
            value = row.get(dimension)
            if value is not None:
                per_dimension[dimension].setdefault(key, []).append(float(value))
        if row.get("refusal_correct") is not None:
            refusals.setdefault(key, []).append(int(row["refusal_correct"]))
    cell_means = {
        dimension: {key: statistics.mean(v) for key, v in cells.items()}
        for dimension, cells in per_dimension.items()
    }
    by_cell = per_dimension["correctness"]
    scores = cell_means["correctness"]
    refusal_scores = {key: statistics.mean(v) for key, v in refusals.items()}

    # A rubric pinned at its maximum cannot separate arms at any sample size.
    # Report that explicitly instead of presenting the resulting tie as a finding.
    saturation = {}
    for dimension in dimensions:
        values = [v for cells in per_dimension[dimension].values() for v in cells]
        if not values:
            continue
        at_ceiling = sum(1 for v in values if v >= 5.0) / len(values)
        saturation[dimension] = {
            "trials_scored": len(values),
            "mean": statistics.mean(values),
            "fraction_at_ceiling": at_ceiling,
            "distinct_values": sorted({v for v in values}),
            "discriminating": at_ceiling < 0.98,
        }
    print("\nrubric headroom (a dimension pinned at 5.0 cannot separate arms)")
    print(f"{'dimension':20}{'trials':>8}{'mean':>7}{'at ceiling':>12}   values")
    print("-" * 72)
    for dimension, info in saturation.items():
        flag = "" if info["discriminating"] else "   <- SATURATED"
        print(f"{dimension:20}{info['trials_scored']:>8}{info['mean']:>7.3f}"
              f"{100*info['fraction_at_ceiling']:>11.1f}%   "
              f"{info['distinct_values']}{flag}")
    trial_counts = {key: len(values) for key, values in by_cell.items()}
    incomplete = [key for key, n in trial_counts.items() if n != args.trials]
    if incomplete:
        print(f"[warn] {len(incomplete)} cells lack {args.trials} valid trials; "
              "they are excluded from paired tests")

    gen_index = {(r["arm"], r["qid"]): r for r in generation}
    answerable = {r["qid"] for r in generation if r["answerable"]}

    print(f"\n{'arm':24}{'correct':>9}{'page hit':>10}{'okf units':>11}{'calls':>7}{'$/q':>9}{'ms':>9}")
    print("-" * 80)
    arm_summary: dict[str, Any] = {}
    for arm in ARMS:
        rows = [r for r in generation if r["arm"] == arm]
        if not rows:
            continue
        cells = [scores[(arm, r["qid"])] for r in rows if (arm, r["qid"]) in scores]
        hits = [
            float(r["retrieval_metrics_at_context"]["page_hit"])
            for r in rows
            if r["retrieval_metrics_at_context"]["page_hit"] is not None
        ]
        entry = {
            "n_cells": len(rows),
            "mean_correctness": statistics.mean(cells) if cells else None,
            "page_hit_rate_at_context": statistics.mean(hits) if hits else None,
            "mean_context_units": statistics.mean(r["context_units"] for r in rows),
            "mean_context_units_from_okf": statistics.mean(
                r["context_units_from_okf"] for r in rows
            ),
            "mean_generator_calls": statistics.mean(r["generator_calls"] for r in rows),
            "mean_cost_usd": statistics.mean(r["generator_cost_usd"] for r in rows),
            "median_latency_ms": statistics.median(r["latency_ms"] for r in rows),
        }
        for dimension in dimensions:
            values = [
                cell_means[dimension][(arm, r["qid"])]
                for r in rows
                if (arm, r["qid"]) in cell_means[dimension]
            ]
            entry[f"mean_{dimension}"] = statistics.mean(values) if values else None
        control_scores = [
            refusal_scores[(arm, r["qid"])]
            for r in rows
            if not r["answerable"] and (arm, r["qid"]) in refusal_scores
        ]
        entry["control_refusal_accuracy"] = (
            statistics.mean(control_scores) if control_scores else None
        )
        entry["n_control_cells"] = len(control_scores)
        arm_summary[arm] = entry
        print(f"{arm:24}{entry['mean_correctness']:>9.3f}"
              f"{entry['page_hit_rate_at_context']:>10.4f}"
              f"{entry['mean_context_units_from_okf']:>11.2f}"
              f"{entry['mean_generator_calls']:>7.2f}{entry['mean_cost_usd']:>9.4f}"
              f"{entry['median_latency_ms']:>9.0f}")

    tests: dict[str, Any] = {}
    raw_p: dict[str, float] = {}
    for label, arm_a, arm_b in CONTRASTS:
        qids = sorted(
            q for q in answerable
            if (arm_a, q) in scores and (arm_b, q) in scores
            and trial_counts.get((arm_a, q)) == args.trials
            and trial_counts.get((arm_b, q)) == args.trials
        )
        if not qids:
            continue
        pairs = [
            PairedDifference(
                pipeline=PIPELINE, qid=q,
                raw_vector=scores[(arm_a, q)], okf_hybrid=scores[(arm_b, q)],
                difference=scores[(arm_b, q)] - scores[(arm_a, q)],
            )
            for q in qids
        ]
        boot = cluster_bootstrap_mean_difference(pairs, repetitions=10_000, seed=42)
        dimension_deltas = {}
        for dimension in dimensions:
            means = cell_means[dimension]
            shared = [q for q in qids if (arm_a, q) in means and (arm_b, q) in means]
            if not shared:
                continue
            dimension_pairs = [
                PairedDifference(
                    pipeline=PIPELINE, qid=q,
                    raw_vector=means[(arm_a, q)], okf_hybrid=means[(arm_b, q)],
                    difference=means[(arm_b, q)] - means[(arm_a, q)],
                )
                for q in shared
            ]
            dimension_deltas[dimension] = cluster_bootstrap_mean_difference(
                dimension_pairs, repetitions=10_000, seed=42
            )
        a_hits = [
            int(gen_index[(arm_a, q)]["retrieval_metrics_at_context"]["page_hit"]) for q in qids
        ]
        b_hits = [
            int(gen_index[(arm_b, q)]["retrieval_metrics_at_context"]["page_hit"]) for q in qids
        ]
        mcnemar = exact_mcnemar(a_hits, b_hits)
        wins = sum(1 for p in pairs if p.difference > 0)
        losses = sum(1 for p in pairs if p.difference < 0)
        tests[label] = {
            "arm_a": arm_a, "arm_b": arm_b, "n_pairs": len(pairs),
            "correctness_delta": boot, "dimension_deltas": dimension_deltas,
            "page_hit_mcnemar": mcnemar,
            "cells_better": wins, "cells_worse": losses,
            "cells_tied": len(pairs) - wins - losses,
        }
        raw_p[label] = float(mcnemar["p_value"])
    adjusted = holm_adjust(raw_p) if raw_p else {}
    for label in tests:
        tests[label]["page_hit_p_holm"] = adjusted.get(label)

    print(f"\n{'contrast':38}{'n':>5}{'better':>8}{'worse':>7}   correctness delta [95% CI]")
    print("-" * 96)
    for label, result in tests.items():
        d = result["correctness_delta"]
        print(f"{label:38}{result['n_pairs']:>5}{result['cells_better']:>8}"
              f"{result['cells_worse']:>7}   {d['mean_difference']:+.3f} "
              f"[{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]")

    summary = {
        "experiment_id": "okf_hybrid_ab_v1",
        "status": "exploratory_added_after_confirmatory_run",
        "design": "arm B is arm A plus an OKF source; all else fixed",
        "corpus": CORPUS,
        "pipeline": PIPELINE,
        "benchmark_id": json.loads(BENCHMARK.read_text())["benchmark_id"],
        "benchmark_sha256": hashlib.sha256(BENCHMARK.read_bytes()).hexdigest(),
        "judge_trials_per_cell": args.trials,
        "judge_model": _judge_model_used(args),
        "rubric_saturation": saturation,
        "arms": arm_summary,
        "contrasts": tests,
        "totals": {
            "generation_cells": len(generation),
            "judge_trials": len(trials),
            "generation_usd": sum(r["generator_cost_usd"] for r in generation),
            "judge_usd": sum(r.get("judge_cost_usd", 0.0) for r in trials),
        },
        "multiplicity": {"method": "holm", "family": "hybrid_ab_contrasts", "n_tests": len(raw_p)},
    }
    out = args.output_dir / "ab_summary.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    totals = summary["totals"]
    print(f"\ntotal spend: generation ${totals['generation_usd']:.2f} + "
          f"judging ${totals['judge_usd']:.2f}")
    print(f"wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("generate", "judge", "analyze", "all"), default="all")
    parser.add_argument("--generator-backend", choices=("bedrock", "mock"), default="bedrock")
    parser.add_argument("--judge-backend", choices=("bedrock", "mock"), default="bedrock")
    parser.add_argument("--judge-model", default="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--output-dir", type=Path, default=REPO_ROOT / "okf_trial_data/results/hybrid_ab"
    )
    args = parser.parse_args()

    benchmark = load_benchmark(BENCHMARK)
    questions = [q for q in benchmark["questions"] if str(q.get("corpus", CORPUS)) == CORPUS]
    if args.limit:
        questions = questions[: args.limit]
    print(f"[design] {len(ARMS)} arms x {len(questions)} questions = "
          f"{len(ARMS) * len(questions)} cells, pipeline={PIPELINE}, corpus={CORPUS}")

    if args.stage in ("generate", "all"):
        stage_generate(args, questions)
    if args.stage in ("judge", "all"):
        stage_judge(args)
    if args.stage in ("analyze", "all"):
        stage_analyze(args)


if __name__ == "__main__":
    main()
