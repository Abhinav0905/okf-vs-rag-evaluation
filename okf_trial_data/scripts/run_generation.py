#!/usr/bin/env python3
"""Generate interleaved raw-vector and OKF RAG answers with safe resume."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import subprocess
import sys
import threading
import time
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SRC = REPO_ROOT / "okf_trial_data/src"
HARNESS_SRC = REPO_ROOT / "eval_harness/src"
for source_root in (PACKAGE_SRC, HARNESS_SRC):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from evaluation.config import load_config, set_global_seed  # noqa: E402
from evaluation.generator import get_generator  # noqa: E402
from evaluation.retriever import get_retriever  # noqa: E402
from evaluation.systems import build_system  # noqa: E402
from okf_trial_data.evaluator import validate_benchmark  # noqa: E402
from okf_trial_data.harness_adapter import (  # noqa: E402
    OKFHybridHarnessRetriever,
    OKFNativeHarnessRetriever,
    load_benchmark,
    retrieval_outcomes,
    to_harness_question,
)
from okf_trial_data.okf_bundle import OKFBundle  # noqa: E402


SYSTEMS = ("simple_rag", "reranked_simple", "agentic_rag", "self_rag", "flare")
CONDITIONS = ("raw_vector", "okf_hybrid", "okf_native")
CORPUS_DIRS = {
    "PGE": REPO_ROOT / "eval_harness/data/corpora/pge_2026_2028_wmp",
    "SCE": REPO_ROOT / "eval_harness/data/corpora/sce_2026_2028_wmp",
    "PC": REPO_ROOT / "eval_harness/data/corpora/pc_2026_2028_wmp",
}
CODE_PROVENANCE_PATHS = (
    "okf_trial_data/scripts/run_generation.py",
    "okf_trial_data/scripts/run_judging.py",
    "okf_trial_data/scripts/analyze_results.py",
    "okf_trial_data/src/okf_trial_data/evaluator.py",
    "okf_trial_data/src/okf_trial_data/harness_adapter.py",
    "okf_trial_data/src/okf_trial_data/okf_bundle.py",
    "okf_trial_data/src/okf_trial_data/okf_retrievers.py",
    "eval_harness/src/evaluation/config.py",
    "eval_harness/src/evaluation/generator.py",
    "eval_harness/src/evaluation/retriever.py",
    "eval_harness/src/evaluation/systems/base.py",
    "eval_harness/src/evaluation/systems/simple_rag.py",
    "eval_harness/src/evaluation/systems/reranked_simple.py",
    "eval_harness/src/evaluation/systems/agentic_rag.py",
    "eval_harness/src/evaluation/systems/self_rag.py",
    "eval_harness/src/evaluation/systems/flare.py",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _git_provenance() -> dict[str, Any]:
    """Record Git state without treating an untracked research tree as clean."""

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return {"available": False}
    return {
        "available": True,
        "head": head,
        "dirty": bool(status),
        "status_entry_count": len(status),
    }


def _code_provenance() -> dict[str, Any]:
    hashes: dict[str, str] = {}
    for relative in CODE_PROVENANCE_PATHS:
        path = REPO_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"required provenance file is missing: {relative}")
        hashes[relative] = _sha256(path)
    return {"git": _git_provenance(), "file_sha256": hashes}


def _load_canonical_corpora() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    chunks: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for corpus, directory in CORPUS_DIRS.items():
        path = directory / "chunks.jsonl"
        hashes[corpus] = _sha256(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            row = json.loads(line)
            chunk_id = str(row["chunk_id"])
            if chunk_id in chunks:
                raise RuntimeError(f"duplicate canonical chunk ID: {chunk_id}")
            if row["corpus"] != corpus:
                raise RuntimeError(f"canonical corpus mismatch for {chunk_id}")
            chunks[chunk_id] = row
    return chunks, hashes


def _gold_audit_snapshot(benchmark: dict[str, Any], benchmark_path: Path) -> dict[str, Any]:
    summary_path = REPO_ROOT / "okf_trial_data/data/gold_audit_summary.json"
    records_path = REPO_ROOT / "okf_trial_data/data/gold_audit.jsonl"
    review_path = REPO_ROOT / "okf_trial_data/protocol/GOLD_AUDIT_CROSS_REVIEW.md"
    for path in (summary_path, records_path, review_path):
        if not path.is_file():
            raise RuntimeError(f"required gold-audit artifact is missing: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected = {
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": _sha256(benchmark_path),
        "question_count": benchmark["counts"]["total"],
        "answerable_count": benchmark["counts"]["answerable"],
        "control_count": benchmark["counts"]["negative_or_control"],
        "answerable_full_page_coverage": benchmark["counts"]["answerable"],
        "automated_flag_count": 0,
        "independent_semantic_review_status": (
            "two_model_assisted_reviews_and_cross_review_passed"
        ),
        "independent_semantic_review_sha256": _sha256(review_path),
    }
    mismatched = [key for key, value in expected.items() if summary.get(key) != value]
    if mismatched:
        raise RuntimeError(f"gold-audit summary differs from frozen benchmark: {mismatched}")
    if summary.get("human_validation_status") != "pending":
        raise RuntimeError("unexpected human-validation status in gold audit")
    rows = [line for line in records_path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != benchmark["counts"]["total"]:
        raise RuntimeError("gold-audit record count differs from frozen benchmark")
    return {
        "summary_sha256": _sha256(summary_path),
        "records_sha256": _sha256(records_path),
        "cross_review_sha256": _sha256(review_path),
        "human_validation_status": summary["human_validation_status"],
        "independent_semantic_review_status": summary[
            "independent_semantic_review_status"
        ],
    }


def _pgvector_snapshot(
    base: Any,
    canonical: dict[str, dict[str, Any]],
    canonical_hashes: dict[str, str],
) -> dict[str, Any]:
    """Fail closed unless pgvector exactly matches the canonical corpus snapshot."""

    connection = getattr(base, "_conn", None)
    table = str(getattr(base, "_table", ""))
    if connection is None or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise RuntimeError("publication run requires an inspectable pgvector backend")
    rows = connection.execute(
        f"SELECT chunk_id, corpus, text, page_number, section, document_name, "
        f"metadata, embedding::text FROM {table} ORDER BY chunk_id"
    ).fetchall()
    if len(rows) != len(canonical):
        raise RuntimeError(
            f"pgvector/canonical row-count mismatch: {len(rows)} != {len(canonical)}"
        )
    content_digest = hashlib.sha256()
    embedding_digest = hashlib.sha256()
    corpus_counts: dict[str, int] = {}
    dimensions: set[int] = set()
    observed_ids: set[str] = set()
    for row in rows:
        chunk_id, corpus, text_value, page, section, document, metadata, embedding = row
        chunk_id = str(chunk_id)
        if chunk_id in observed_ids:
            raise RuntimeError(f"duplicate pgvector chunk ID: {chunk_id}")
        observed_ids.add(chunk_id)
        expected = canonical.get(chunk_id)
        if expected is None:
            raise RuntimeError(f"unexpected pgvector chunk ID: {chunk_id}")
        actual_fields = {
            "corpus": corpus,
            "text": text_value,
            "page_number": page,
            "section": section,
            "document_name": document,
            "metadata": metadata or {},
        }
        expected_fields = {key: expected.get(key) for key in actual_fields}
        expected_fields["metadata"] = expected.get("metadata", {}) or {}
        if actual_fields != expected_fields:
            raise RuntimeError(f"pgvector content mismatch for {chunk_id}")
        if embedding is None:
            raise RuntimeError(f"null embedding for {chunk_id}")
        embedding_text = str(embedding)
        dimensions.add(len(embedding_text.strip("[]").split(",")))
        corpus_counts[str(corpus)] = corpus_counts.get(str(corpus), 0) + 1
        content_digest.update(
            (json.dumps([chunk_id, actual_fields], ensure_ascii=False, sort_keys=True) + "\n")
            .encode("utf-8")
        )
        embedding_digest.update(f"{chunk_id}|{embedding_text}\n".encode("utf-8"))
    if observed_ids != set(canonical):
        raise RuntimeError("pgvector chunk-ID inventory differs from canonical corpora")
    if dimensions != {384}:
        raise RuntimeError(f"unexpected embedding dimensions: {sorted(dimensions)}")
    return {
        "table": table,
        "row_count": len(rows),
        "corpus_counts": dict(sorted(corpus_counts.items())),
        "canonical_chunks_jsonl_sha256": dict(sorted(canonical_hashes.items())),
        "database_content_sha256": content_digest.hexdigest(),
        "embedding_inventory_sha256": embedding_digest.hexdigest(),
        "embedding_dimensions": sorted(dimensions),
    }


def _parse_names(value: str, allowed: Iterable[str]) -> list[str]:
    allowed_tuple = tuple(allowed)
    if value.strip().lower() == "all":
        return list(allowed_tuple)
    names = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(names) - set(allowed_tuple))
    if unknown:
        raise SystemExit(f"unknown values {unknown}; allowed={allowed_tuple}")
    if len(names) != len(set(names)):
        raise SystemExit("duplicate values are not allowed")
    return names


def _select_pilot(questions: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    """Deterministically span answerability and categories for an API pilot."""

    if count <= 0 or count >= len(questions):
        return list(questions)
    answerable = [q for q in questions if q["answerable"]]
    controls = [q for q in questions if not q["answerable"]]
    selected: list[dict[str, Any]] = []
    used_categories: set[str] = set()
    if controls:
        selected.append(controls[0])
        used_categories.add(controls[0]["category"])
    for question in answerable:
        if len(selected) >= count:
            break
        if question["category"] not in used_categories:
            selected.append(question)
            used_categories.add(question["category"])
    for question in questions:
        if len(selected) >= count:
            break
        if question not in selected:
            selected.append(question)
    return selected[:count]


class LockedRetriever:
    """Serialize local embedding/reranker access while network calls overlap."""

    def __init__(self, inner: Any, lock: threading.RLock) -> None:
        self.inner = inner
        self.lock = lock
        self.config = inner.config
        self.reranker = inner.reranker

    def dense_search(self, *args: Any, **kwargs: Any):
        with self.lock:
            return self.inner.dense_search(*args, **kwargs)

    def rerank(self, *args: Any, **kwargs: Any):
        with self.lock:
            return self.inner.rerank(*args, **kwargs)

    def get_context(self, *args: Any, **kwargs: Any):
        with self.lock:
            return self.inner.get_context(*args, **kwargs)

    def close(self) -> None:
        return None


@dataclass
class MeteredGenerator:
    """Per-answer usage meter around the shared thread-safe model client."""

    inner: Any
    invocations: list[dict[str, Any]] = field(default_factory=list)

    def generate(self, *args: Any, **kwargs: Any):
        result = self.inner.generate(*args, **kwargs)
        self.invocations.append(
            {
                "model_id": result.model_id,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": result.cost_usd,
                "calls": result.calls,
            }
        )
        return result

    @property
    def input_tokens(self) -> int:
        return sum(int(item["input_tokens"]) for item in self.invocations)

    @property
    def output_tokens(self) -> int:
        return sum(int(item["output_tokens"]) for item in self.invocations)

    @property
    def cost_usd(self) -> float:
        return sum(float(item["cost_usd"]) for item in self.invocations)


@dataclass(frozen=True)
class Task:
    schedule_index: int
    pipeline: str
    condition: str
    question: dict[str, Any]

    @property
    def key(self) -> tuple[str, str, str]:
        return self.pipeline, self.condition, self.question["qid"]


def _schedule(
    questions: list[dict[str, Any]],
    systems: list[str],
    conditions: list[str],
    seed: int,
) -> list[Task]:
    rng = random.Random(seed)
    tasks: list[Task] = []
    index = 0
    # Pair/block conditions next to one another, while rotating pipeline order
    # across questions to limit clock-time confounding.
    for question in questions:
        pipeline_order = list(systems)
        rng.shuffle(pipeline_order)
        for pipeline in pipeline_order:
            condition_order = list(conditions)
            rng.shuffle(condition_order)
            for condition in condition_order:
                tasks.append(Task(index, pipeline, condition, question))
                index += 1
    return tasks


def _validate_completed_record(
    row: dict[str, Any],
    *,
    task: Task,
    canonical_chunks: dict[str, dict[str, Any]],
    expected_model: str,
) -> None:
    q = task.question
    expected_fields = {
        "schema_version": "okf-generation-record-v1",
        "schedule_index": task.schedule_index,
        "pipeline": task.pipeline,
        "condition": task.condition,
        "arm": task.condition,
        "qid": q["qid"],
        "question": q["question"],
        "category": q["category"],
        "answerable": q["answerable"],
        "reference_answer": q["reference_answer"],
        "expected_pages": q["expected_pages"],
        "corpus": q["corpus"],
    }
    mismatched = [key for key, value in expected_fields.items() if row.get(key) != value]
    if mismatched:
        raise ValueError(
            f"resume record differs from frozen task {task.key}: {mismatched}"
        )
    answer = row.get("answer_text")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"resume record has an empty answer: {task.key}")
    if row.get("answer_sha256") != hashlib.sha256(answer.encode("utf-8")).hexdigest():
        raise ValueError(f"resume answer hash mismatch: {task.key}")
    invocations = row.get("model_invocations")
    if not isinstance(invocations, list) or not invocations:
        raise ValueError(f"resume invocation log is missing: {task.key}")
    if any(item.get("model_id") != expected_model for item in invocations):
        raise ValueError(f"resume model ID mismatch: {task.key}")
    accounting = {
        "generator_calls": sum(int(item["calls"]) for item in invocations),
        "generator_input_tokens": sum(int(item["input_tokens"]) for item in invocations),
        "generator_output_tokens": sum(int(item["output_tokens"]) for item in invocations),
    }
    for field, value in accounting.items():
        if row.get(field) != value:
            raise ValueError(f"resume invocation accounting mismatch ({field}): {task.key}")
    invocation_cost = sum(float(item["cost_usd"]) for item in invocations)
    if not math.isclose(
        float(row.get("generator_cost_usd", -1.0)), invocation_cost, rel_tol=0, abs_tol=1e-12
    ):
        raise ValueError(f"resume cost accounting mismatch: {task.key}")

    retrieved = row.get("retrieved_chunks")
    if not isinstance(retrieved, list):
        raise ValueError(f"resume retrieved chunks are missing: {task.key}")
    retrieved_ids: set[str] = set()
    for chunk in retrieved:
        chunk_id = str(chunk.get("chunk_id", ""))
        if not chunk_id or chunk_id in retrieved_ids:
            raise ValueError(f"invalid/duplicate retrieved chunk in {task.key}: {chunk_id}")
        retrieved_ids.add(chunk_id)
        canonical = canonical_chunks.get(chunk_id)
        if canonical is None:
            raise ValueError(f"retrieved chunk is absent from canonical source: {chunk_id}")
        for field in ("corpus", "text", "page_number", "section", "document_name"):
            if chunk.get(field) != canonical.get(field):
                raise ValueError(f"retrieved {field} mismatch for {task.key}/{chunk_id}")
        metadata = chunk.get("metadata") or {}
        canonical_metadata = canonical.get("metadata") or {}
        if task.condition == "raw_vector":
            if metadata != canonical_metadata:
                raise ValueError(f"raw metadata mismatch for {task.key}/{chunk_id}")
        else:
            if metadata.get("source_chunk_id") != chunk_id:
                raise ValueError(f"OKF source ID mismatch for {task.key}/{chunk_id}")
            if metadata.get("source_metadata") != canonical_metadata:
                raise ValueError(f"OKF source metadata mismatch for {task.key}/{chunk_id}")
            if metadata.get("okf_retrieval_mode") != task.condition:
                raise ValueError(f"OKF treatment marker mismatch for {task.key}/{chunk_id}")
    recomputed = retrieval_outcomes(retrieved, q["expected_pages"])
    if row.get("retrieval_metrics_at_context") != recomputed:
        raise ValueError(f"resume retrieval-metric mismatch: {task.key}")


def _load_completed(
    path: Path,
    *,
    tasks: list[Task],
    canonical_chunks: dict[str, dict[str, Any]],
    expected_model: str,
) -> set[tuple[str, str, str]]:
    completed: set[tuple[str, str, str]] = set()
    if not path.exists():
        return completed
    scheduled = {task.key: task for task in tasks}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row["pipeline"], row["condition"], row["qid"])
        if key in completed:
            raise ValueError(f"duplicate completed record at line {line_number}: {key}")
        task = scheduled.get(key)
        if task is None:
            raise ValueError(f"completed record is absent from schedule at line {line_number}: {key}")
        _validate_completed_record(
            row,
            task=task,
            canonical_chunks=canonical_chunks,
            expected_model=expected_model,
        )
        completed.add(key)
    return completed


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _run_task(
    task: Task,
    *,
    config: Any,
    retrievers: dict[str, Any],
    shared_generator: Any,
) -> dict[str, Any]:
    metered = MeteredGenerator(shared_generator)
    runner = build_system(task.pipeline, config, retrievers[task.condition], metered)
    question = to_harness_question(task.question)
    started = time.perf_counter()
    record = runner.run(question, task.question["corpus"])
    wall_ms = (time.perf_counter() - started) * 1000
    included = record.retrieved_chunks
    return {
        "schema_version": "okf-generation-record-v1",
        "schedule_index": task.schedule_index,
        "pipeline": task.pipeline,
        "condition": task.condition,
        "arm": task.condition,
        "qid": task.question["qid"],
        "question": task.question["question"],
        "category": task.question["category"],
        "answerable": task.question["answerable"],
        "reference_answer": task.question["reference_answer"],
        "expected_pages": task.question["expected_pages"],
        "corpus": task.question["corpus"],
        "answer_text": record.answer_text,
        "answer_sha256": hashlib.sha256(record.answer_text.encode("utf-8")).hexdigest(),
        "citations": record.citations,
        "generator_calls": record.generator_calls,
        "generator_input_tokens": metered.input_tokens,
        "generator_output_tokens": metered.output_tokens,
        "generator_cost_usd": metered.cost_usd,
        "latency_ms": wall_ms,
        "retrieval_log": record.retrieval_log,
        "retrieval_metrics_at_context": retrieval_outcomes(
            included, task.question["expected_pages"]
        ),
        "retrieved_chunks": [chunk.model_dump(mode="json") for chunk in included],
        "model_invocations": metered.invocations,
        "completed_at": _now(),
    }


def _preflight_aws(region: str) -> dict[str, str]:
    import boto3

    identity = boto3.client("sts", region_name=region).get_caller_identity()
    return {
        "account_sha256": hashlib.sha256(str(identity["Account"]).encode()).hexdigest(),
        "arn_sha256": hashlib.sha256(str(identity["Arn"]).encode()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/config/experiment.yaml",
    )
    parser.add_argument(
        "--harness-config",
        type=Path,
        default=REPO_ROOT / "eval_harness/eval_config.yaml",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/full",
    )
    parser.add_argument("--systems", default="all")
    parser.add_argument("--conditions", default="all")
    parser.add_argument("--generator-backend", choices=("bedrock", "mock"), default="bedrock")
    parser.add_argument("--pilot", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    experiment = yaml.safe_load(args.experiment_config.read_text(encoding="utf-8"))
    seed = int(experiment["experiment"]["seed"])
    set_global_seed(seed)
    benchmark_path = REPO_ROOT / "okf_trial_data" / experiment["experiment"]["benchmark"]
    bundle_path = (
        REPO_ROOT
        / "okf_trial_data"
        / experiment["okf"]["bundles_dir"]
        / "wmp_all_v0_2"
    )
    bundle = OKFBundle.load(bundle_path)
    bundle.verify_integrity()
    benchmark = load_benchmark(benchmark_path)
    validate_benchmark(benchmark)
    if int(experiment["experiment"]["question_count"]) != len(benchmark["questions"]):
        raise RuntimeError("experiment question_count differs from frozen benchmark")
    gold_audit_snapshot = _gold_audit_snapshot(benchmark, benchmark_path)
    questions = list(benchmark["questions"])
    if args.pilot:
        questions = _select_pilot(questions, args.pilot)
    elif args.limit:
        questions = questions[: args.limit]

    systems = _parse_names(args.systems, SYSTEMS)
    conditions = _parse_names(args.conditions, CONDITIONS)
    tasks = _schedule(questions, systems, conditions, seed)

    config = load_config(args.harness_config)
    config.retriever.device = "cpu"
    config.generator.backend = args.generator_backend
    if args.generator_backend == "mock":
        config.generator.bedrock_model_id = "mock"
    aws_identity = (
        _preflight_aws(config.generator.region)
        if args.generator_backend == "bedrock"
        else {"status": "not_required_for_mock"}
    )
    base = get_retriever(config)
    canonical_chunks, canonical_hashes = _load_canonical_corpora()
    database_snapshot = _pgvector_snapshot(base, canonical_chunks, canonical_hashes)
    retrieval_cfg = experiment["retrieval"]
    hybrid = OKFHybridHarnessRetriever(
        base,
        bundle_path,
        seed_fraction=float(retrieval_cfg["okf_seed_fraction"]),
        max_link_depth=int(retrieval_cfg["okf_link_hops"]),
        link_decay=float(retrieval_cfg["okf_link_decay"]),
        bidirectional_links=bool(retrieval_cfg["okf_bidirectional_links"]),
    )
    native = OKFNativeHarnessRetriever(
        base,
        bundle_path,
        seed_fraction=float(retrieval_cfg["okf_seed_fraction"]),
        max_link_depth=int(retrieval_cfg["okf_link_hops"]),
        link_decay=float(retrieval_cfg["okf_link_decay"]),
        bidirectional_links=bool(retrieval_cfg["okf_bidirectional_links"]),
    )
    retrieval_lock = threading.RLock()
    retrievers = {
        "raw_vector": LockedRetriever(base, retrieval_lock),
        "okf_hybrid": LockedRetriever(hybrid, retrieval_lock),
        "okf_native": LockedRetriever(native, retrieval_lock),
    }
    shared_generator = get_generator(config)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records_path = args.output_dir / "generation_records.jsonl"
    failures_path = args.output_dir / "generation_failures.jsonl"
    schedule_path = args.output_dir / "schedule.json"
    manifest_path = args.output_dir / "run_manifest.json"
    schedule_payload = [
        {
            "schedule_index": task.schedule_index,
            "pipeline": task.pipeline,
            "condition": task.condition,
            "qid": task.question["qid"],
        }
        for task in tasks
    ]
    if schedule_path.exists():
        if json.loads(schedule_path.read_text(encoding="utf-8")) != schedule_payload:
            raise RuntimeError("existing schedule differs; choose a new output directory")
    else:
        schedule_path.write_text(
            json.dumps(schedule_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    bundle_manifest = json.loads(
        (bundle_path / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    manifest = {
        "schema_version": "okf-run-manifest-v1",
        "experiment_id": experiment["experiment"]["id"],
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": _sha256(benchmark_path),
        "ordered_qid_sha256": _json_sha256([q["qid"] for q in questions]),
        "question_count": len(questions),
        "answerable_count": sum(bool(q["answerable"]) for q in questions),
        "control_count": sum(not bool(q["answerable"]) for q in questions),
        "systems": systems,
        "conditions": conditions,
        "expected_records": len(tasks),
        "seed": seed,
        "generator_backend": args.generator_backend,
        "generator_model": config.generator.bedrock_model_id,
        "generator_region": config.generator.region,
        "temperature": config.generator.temperature,
        "max_tokens": config.generator.max_tokens,
        "bundle_content_sha256": bundle_manifest["bundle_content_sha256"],
        "okf_spec_commit": bundle_manifest["okf_spec_commit"],
        "source_pdf_sha256": next(
            source["source_sha256"]
            for source in bundle_manifest["sources"]
            if source["corpus"] == "PGE"
        ),
        "experiment_config_sha256": _sha256(args.experiment_config),
        "harness_config_sha256": _sha256(args.harness_config),
        "schedule_sha256": _sha256(schedule_path),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "workers": args.workers,
        "aws_identity": aws_identity,
        "code_provenance": _code_provenance(),
        "database_snapshot": database_snapshot,
        "gold_audit_snapshot": gold_audit_snapshot,
    }
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous != manifest:
            raise RuntimeError("existing run manifest differs; choose a new output directory")
    else:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    completed = _load_completed(
        records_path,
        tasks=tasks,
        canonical_chunks=canonical_chunks,
        expected_model=config.generator.bedrock_model_id,
    )
    pending = [task for task in tasks if task.key not in completed]
    print(
        f"[generation] expected={len(tasks)} complete={len(completed)} "
        f"pending={len(pending)} backend={args.generator_backend} workers={args.workers}"
    )
    started = time.perf_counter()
    successes = 0
    failures = 0
    pool = ThreadPoolExecutor(max_workers=args.workers)
    interrupted = False
    try:
        futures = {
            pool.submit(
                _run_task,
                task,
                config=config,
                retrievers=retrievers,
                shared_generator=shared_generator,
            ): task
            for task in pending
        }
        for future in as_completed(futures):
            task = futures[future]
            try:
                payload = future.result()
            except Exception as exc:
                failures += 1
                _append_jsonl(
                    failures_path,
                    {
                        "pipeline": task.pipeline,
                        "condition": task.condition,
                        "qid": task.question["qid"],
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:2000],
                        "failed_at": _now(),
                    },
                )
            else:
                _append_jsonl(records_path, payload)
                successes += 1
            finished = len(completed) + successes
            if (successes + failures) % 10 == 0 or successes + failures == len(pending):
                elapsed = time.perf_counter() - started
                cost = 0.0
                if records_path.exists():
                    cost = sum(
                        float(json.loads(line)["generator_cost_usd"])
                        for line in records_path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    )
                print(
                    f"[generation] processed={successes + failures}/{len(pending)} "
                    f"total_complete={finished}/{len(tasks)} failures={failures} "
                    f"elapsed_s={elapsed:.1f} cost_usd={cost:.4f}"
                )
    except KeyboardInterrupt:
        interrupted = True
        for future in futures:
            future.cancel()
        print(
            "[generation] interrupted; pending futures cancelled. "
            "Completed records are durable and the same command can resume."
        )
    finally:
        pool.shutdown(wait=not interrupted, cancel_futures=interrupted)
        base.close()
    if interrupted:
        raise SystemExit(130)
    final = _load_completed(
        records_path,
        tasks=tasks,
        canonical_chunks=canonical_chunks,
        expected_model=config.generator.bedrock_model_id,
    )
    print(
        f"[generation] final_complete={len(final)}/{len(tasks)} "
        f"new_failures={failures} records={records_path}"
    )
    if len(final) != len(tasks):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
