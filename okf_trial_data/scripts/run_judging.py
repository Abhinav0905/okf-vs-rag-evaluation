#!/usr/bin/env python3
"""Strict, gold-aware, condition-blinded judging with trial-level resume."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SRC = REPO_ROOT / "okf_trial_data/src"
HARNESS_SRC = REPO_ROOT / "eval_harness/src"
for source_root in (PACKAGE_SRC, HARNESS_SRC):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from evaluation.config import load_config  # noqa: E402
from okf_trial_data.evaluator import (  # noqa: E402
    SCHEMA_VERSION,
    JudgeRetriesExhausted,
    build_gold_aware_judge_prompt,
    derive_outcomes,
    parse_judge_response,
    run_strict_judge,
)
from okf_trial_data.harness_adapter import CorpusEvidenceIndex  # noqa: E402
from run_generation import (  # noqa: E402
    Task as GenerationTask,
    _load_canonical_corpora,
    _validate_completed_record,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _refused(text: str) -> bool:
    lower = text.casefold()
    markers = (
        "does not contain sufficient information",
        "cannot answer",
        "can't answer",
        "no information",
        "not found in",
        "not covered",
        "unable to answer",
        "not addressed in",
        "not mentioned in",
        "outside the scope",
        "not in the provided context",
    )
    return any(marker in lower for marker in markers)


@dataclass(frozen=True)
class JudgeTask:
    record: dict[str, Any]
    trial_index: int

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (
            self.record["pipeline"],
            self.record["condition"],
            self.record["qid"],
            self.trial_index,
        )


class BedrockStructuredJudgeClient:
    """Claude judge via Bedrock Converse forced tool use.

    The model returns a typed tool input rather than free-form Markdown.  The
    input is serialized back to exact JSON and still passes through the strict
    independent parser; tool use removes formatting-only fence failures but
    does not coerce, impute, or relax any score rule.
    """

    def __init__(self, config: Any) -> None:
        import boto3
        from botocore.config import Config as BotoConfig

        self.model_id = config.judge.model_id
        self.price = config.price(self.model_id)
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=config.judge.region,
            config=BotoConfig(
                retries={"max_attempts": 8, "mode": "adaptive"},
                read_timeout=120,
                connect_timeout=15,
            ),
        )

    def invoke(self, prompt: str, evaluation_id: str) -> tuple[str, dict[str, Any]]:
        schema = {
            "type": "object",
            "properties": {
                "schema_version": {"type": "string", "enum": [SCHEMA_VERSION]},
                "evaluation_id": {"type": "string", "enum": [evaluation_id]},
                "response_disposition": {
                    "type": "string",
                    "enum": ["substantive_answer", "refusal"],
                },
                "correctness": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                "completeness": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                "groundedness": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                "citation_quality": {"type": ["integer", "null"], "minimum": 1, "maximum": 5},
                "explanation": {"type": "string", "minLength": 1, "maxLength": 1000},
            },
            "required": [
                "schema_version",
                "evaluation_id",
                "response_disposition",
                "correctness",
                "completeness",
                "groundedness",
                "citation_quality",
                "explanation",
            ],
            "additionalProperties": False,
        }
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 768, "temperature": 0.0},
            toolConfig={
                "tools": [
                    {
                        "toolSpec": {
                            "name": "submit_evaluation",
                            "description": "Submit one strict, blinded benchmark evaluation.",
                            "inputSchema": {"json": schema},
                        }
                    }
                ],
                "toolChoice": {"tool": {"name": "submit_evaluation"}},
            },
        )
        content = response.get("output", {}).get("message", {}).get("content", [])
        tool_uses = [item["toolUse"] for item in content if "toolUse" in item]
        if len(tool_uses) != 1 or tool_uses[0].get("name") != "submit_evaluation":
            raw_text = "".join(item.get("text", "") for item in content)
            return raw_text, {
                "model_id": self.model_id,
                "input_tokens": int(response.get("usage", {}).get("inputTokens", 0)),
                "output_tokens": int(response.get("usage", {}).get("outputTokens", 0)),
                "cost_usd": 0.0,
                "stop_reason": response.get("stopReason"),
                "transport_error": "expected exactly one submit_evaluation tool use",
            }
        usage = response.get("usage", {})
        input_tokens = int(usage.get("inputTokens", 0))
        output_tokens = int(usage.get("outputTokens", 0))
        cost = (
            input_tokens / 1_000_000 * self.price["input_per_mtok"]
            + output_tokens / 1_000_000 * self.price["output_per_mtok"]
        )
        tool_input = tool_uses[0].get("input")
        raw = json.dumps(tool_input, ensure_ascii=False, sort_keys=True)
        return raw, {
            "model_id": self.model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "stop_reason": response.get("stopReason"),
            "transport": "bedrock_converse_forced_tool",
        }


class BedrockJudgeCall:
    def __init__(self, client: BedrockStructuredJudgeClient, evaluation_id: str) -> None:
        self.client = client
        self.evaluation_id = evaluation_id
        self.invocations: list[dict[str, Any]] = []

    def __call__(self, prompt: str) -> str:
        raw, invocation = self.client.invoke(prompt, self.evaluation_id)
        self.invocations.append(invocation)
        return raw


class MockJudgeCall:
    def __init__(self, *, evaluation_id: str, answerable: bool, answer_text: str) -> None:
        self.evaluation_id = evaluation_id
        self.answerable = answerable
        self.answer_text = answer_text
        self.invocations: list[dict[str, Any]] = []

    def __call__(self, prompt: str) -> str:
        disposition = "refusal" if _refused(self.answer_text) else "substantive_answer"
        scored = self.answerable and disposition == "substantive_answer"
        self.invocations.append(
            {
                "model_id": "mock-strict-judge",
                "input_tokens": len(prompt.split()),
                "output_tokens": 40,
                "cost_usd": 0.0,
            }
        )
        return json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "evaluation_id": self.evaluation_id,
                "response_disposition": disposition,
                "correctness": 3 if scored else None,
                "completeness": 3 if scored else None,
                "groundedness": 3 if scored else None,
                "citation_quality": 3 if scored else None,
                "explanation": "Deterministic mock result for plumbing validation.",
            }
        )


def _evaluation_id(record: dict[str, Any], trial_index: int) -> str:
    opaque = "|".join(
        [
            "okf-blind-v1",
            record["pipeline"],
            record["condition"],
            record["qid"],
            record["answer_sha256"],
            str(trial_index),
        ]
    )
    return "blind-" + hashlib.sha256(opaque.encode("utf-8")).hexdigest()[:24]


def _run_task(
    task: JudgeTask,
    *,
    evidence: CorpusEvidenceIndex,
    backend: str,
    shared_judge: Any | None,
    max_attempts: int,
) -> dict[str, Any]:
    record = task.record
    evaluation_id = _evaluation_id(record, task.trial_index)
    gold_evidence = evidence.gold_evidence(
        record["expected_pages"], record["reference_answer"]
    )
    resolved = evidence.resolve_citations(record["citations"])
    prompt = build_gold_aware_judge_prompt(
        evaluation_id=evaluation_id,
        question=record["question"],
        answerable=bool(record["answerable"]),
        reference_answer=record["reference_answer"],
        gold_evidence=gold_evidence,
        system_answer=record["answer_text"],
        resolved_citations=resolved,
    )
    call = (
        BedrockJudgeCall(shared_judge, evaluation_id)
        if backend == "bedrock"
        else MockJudgeCall(
            evaluation_id=evaluation_id,
            answerable=bool(record["answerable"]),
            answer_text=record["answer_text"],
        )
    )
    started = time.perf_counter()
    try:
        run = run_strict_judge(
            call,
            prompt,
            expected_evaluation_id=evaluation_id,
            answerable=bool(record["answerable"]),
            max_attempts=max_attempts,
        )
    except JudgeRetriesExhausted as exc:
        exc.judge_invocations = list(call.invocations)  # type: ignore[attr-defined]
        raise
    elapsed_ms = (time.perf_counter() - started) * 1000
    outcomes = derive_outcomes(run.assessment, answerable=bool(record["answerable"]))
    return {
        "schema_version": "okf-judge-trial-record-v1",
        "pipeline": record["pipeline"],
        "condition": record["condition"],
        "arm": record["arm"],
        "qid": record["qid"],
        "answer_sha256": record["answer_sha256"],
        "answerable": record["answerable"],
        "trial_index": task.trial_index,
        "evaluation_id": evaluation_id,
        "assessment": asdict(run.assessment),
        "outcomes": asdict(outcomes),
        "attempts": [asdict(attempt) for attempt in run.attempts],
        "judge_invocations": call.invocations,
        "judge_input_tokens": sum(item["input_tokens"] for item in call.invocations),
        "judge_output_tokens": sum(item["output_tokens"] for item in call.invocations),
        "judge_cost_usd": sum(item["cost_usd"] for item in call.invocations),
        "judge_latency_ms": elapsed_ms,
        "gold_evidence_chunk_ids": [item["chunk_id"] for item in gold_evidence],
        "resolved_citation_chunk_ids": [item["chunk_id"] for item in resolved],
        "completed_at": _now(),
    }


def _validate_judge_record(
    row: dict[str, Any],
    *,
    task: JudgeTask,
    expected_model: str,
    max_attempts: int,
) -> None:
    record = task.record
    expected_fields = {
        "schema_version": "okf-judge-trial-record-v1",
        "pipeline": record["pipeline"],
        "condition": record["condition"],
        "arm": record["arm"],
        "qid": record["qid"],
        "answer_sha256": record["answer_sha256"],
        "answerable": record["answerable"],
        "trial_index": task.trial_index,
        "evaluation_id": _evaluation_id(record, task.trial_index),
    }
    mismatched = [key for key, value in expected_fields.items() if row.get(key) != value]
    if mismatched:
        raise ValueError(f"judge resume record mismatch {task.key}: {mismatched}")
    assessment = parse_judge_response(
        json.dumps(row.get("assessment"), ensure_ascii=False, sort_keys=True),
        expected_evaluation_id=expected_fields["evaluation_id"],
        answerable=bool(record["answerable"]),
    )
    if row.get("outcomes") != asdict(
        derive_outcomes(assessment, answerable=bool(record["answerable"]))
    ):
        raise ValueError(f"judge derived outcomes mismatch: {task.key}")
    attempts = row.get("attempts")
    if not isinstance(attempts, list) or not 1 <= len(attempts) <= max_attempts:
        raise ValueError(f"judge attempt log is invalid: {task.key}")
    if attempts[-1].get("validation_error") is not None:
        raise ValueError(f"judge record does not end in a valid attempt: {task.key}")
    invocations = row.get("judge_invocations")
    if not isinstance(invocations, list) or len(invocations) != len(attempts):
        raise ValueError(f"judge invocation log is invalid: {task.key}")
    if any(item.get("model_id") != expected_model for item in invocations):
        raise ValueError(f"judge model ID mismatch: {task.key}")
    sums = {
        "judge_input_tokens": sum(int(item["input_tokens"]) for item in invocations),
        "judge_output_tokens": sum(int(item["output_tokens"]) for item in invocations),
    }
    for field, value in sums.items():
        if row.get(field) != value:
            raise ValueError(f"judge accounting mismatch ({field}): {task.key}")
    cost = sum(float(item["cost_usd"]) for item in invocations)
    if not math.isclose(
        float(row.get("judge_cost_usd", -1.0)), cost, rel_tol=0, abs_tol=1e-12
    ):
        raise ValueError(f"judge cost accounting mismatch: {task.key}")


def _completed_keys(
    path: Path,
    *,
    tasks: list[JudgeTask],
    expected_model: str,
    max_attempts: int,
) -> set[tuple[str, str, str, int]]:
    keys: set[tuple[str, str, str, int]] = set()
    if not path.exists():
        return keys
    scheduled = {task.key: task for task in tasks}
    for row in _load_jsonl(path):
        key = (row["pipeline"], row["condition"], row["qid"], int(row["trial_index"]))
        if key in keys:
            raise ValueError(f"duplicate judge trial: {key}")
        task = scheduled.get(key)
        if task is None:
            raise ValueError(f"judge record is absent from schedule: {key}")
        _validate_judge_record(
            row,
            task=task,
            expected_model=expected_model,
            max_attempts=max_attempts,
        )
        keys.add(key)
    return keys


def _mean_optional(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [row["outcomes"][field] for row in rows if row["outcomes"][field] is not None]
    return statistics.mean(values) if values else None


def _write_answer_scores(
    generation: list[dict[str, Any]],
    trials: list[dict[str, Any]],
    output_path: Path,
    trials_per_answer: int,
) -> None:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for trial in trials:
        grouped[(trial["pipeline"], trial["condition"], trial["qid"])].append(trial)
    output: list[dict[str, Any]] = []
    for record in generation:
        key = (record["pipeline"], record["condition"], record["qid"])
        items = sorted(grouped.get(key, []), key=lambda row: row["trial_index"])
        if len(items) != trials_per_answer:
            raise RuntimeError(f"answer {key} has {len(items)} valid trials")
        if any(item["answer_sha256"] != record["answer_sha256"] for item in items):
            raise RuntimeError(f"answer hash changed for {key}")
        dispositions = [item["assessment"]["response_disposition"] for item in items]
        output.append(
            {
                "schema_version": "okf-answer-score-v1",
                "pipeline": record["pipeline"],
                "condition": record["condition"],
                "arm": record["arm"],
                "qid": record["qid"],
                "category": record["category"],
                "answerable": record["answerable"],
                "answer_sha256": record["answer_sha256"],
                "answer_correctness": _mean_optional(items, "answer_correctness"),
                "answer_completeness": _mean_optional(items, "answer_completeness"),
                "groundedness": _mean_optional(items, "groundedness"),
                "citation_quality": _mean_optional(items, "citation_quality"),
                "negative_refusal_correct": _mean_optional(items, "negative_refusal_correct"),
                "refusal_fraction": dispositions.count("refusal") / len(dispositions),
                "judge_trials": len(items),
                "judge_attempts": sum(len(item["attempts"]) for item in items),
                "judge_cost_usd": sum(item["judge_cost_usd"] for item in items),
                "judge_input_tokens": sum(item["judge_input_tokens"] for item in items),
                "judge_output_tokens": sum(item["judge_output_tokens"] for item in items),
            }
        )
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in output),
        encoding="utf-8",
    )


def _preflight_aws(region: str) -> dict[str, str]:
    import boto3

    identity = boto3.client("sts", region_name=region).get_caller_identity()
    return {
        "account_sha256": hashlib.sha256(str(identity["Account"]).encode()).hexdigest(),
        "arn_sha256": hashlib.sha256(str(identity["Arn"]).encode()).hexdigest(),
    }


def _validate_generation_artifact(
    *,
    generation_dir: Path,
    generation: list[dict[str, Any]],
    manifest: dict[str, Any],
    benchmark_path: Path,
) -> None:
    """Fail closed before any paid judge call if provenance or cells drifted."""

    if _sha256(benchmark_path) != manifest.get("benchmark_sha256"):
        raise RuntimeError("benchmark hash differs from generation manifest")
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    if benchmark.get("benchmark_id") != manifest.get("benchmark_id"):
        raise RuntimeError("benchmark ID differs from generation manifest")
    questions = benchmark.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("benchmark questions are missing")
    question_by_qid = {str(item["qid"]): item for item in questions}
    if len(question_by_qid) != len(questions):
        raise RuntimeError("benchmark contains duplicate QIDs")

    schedule_path = generation_dir / "schedule.json"
    if not schedule_path.is_file():
        raise RuntimeError("generation schedule is missing")
    if _sha256(schedule_path) != manifest.get("schedule_sha256"):
        raise RuntimeError("schedule hash differs from generation manifest")
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    expected_records = int(manifest["expected_records"])
    if len(schedule) != expected_records:
        raise RuntimeError("schedule length differs from generation manifest")
    indices = [row.get("schedule_index") for row in schedule]
    if indices != list(range(expected_records)):
        raise RuntimeError("schedule indices are not unique and continuous")

    tasks: list[GenerationTask] = []
    scheduled_keys: set[tuple[str, str, str]] = set()
    for item in schedule:
        qid = str(item.get("qid", ""))
        question = question_by_qid.get(qid)
        if question is None:
            raise RuntimeError(f"schedule QID is absent from benchmark: {qid}")
        task = GenerationTask(
            int(item["schedule_index"]),
            str(item["pipeline"]),
            str(item["condition"]),
            question,
        )
        if task.key in scheduled_keys:
            raise RuntimeError(f"schedule contains duplicate cell: {task.key}")
        scheduled_keys.add(task.key)
        tasks.append(task)
    generated_keys = {
        (str(row.get("pipeline")), str(row.get("condition")), str(row.get("qid")))
        for row in generation
    }
    if len(generated_keys) != len(generation):
        raise RuntimeError("generation records contain duplicate cells")
    if generated_keys != scheduled_keys:
        missing = sorted(scheduled_keys - generated_keys)[:5]
        extra = sorted(generated_keys - scheduled_keys)[:5]
        raise RuntimeError(f"generation/schedule key-set mismatch; missing={missing}, extra={extra}")

    provenance = manifest.get("code_provenance", {}).get("file_sha256")
    if not isinstance(provenance, dict) or not provenance:
        raise RuntimeError("generation manifest lacks code-file provenance")
    for relative, expected_hash in provenance.items():
        path = REPO_ROOT / relative
        if not path.is_file() or _sha256(path) != expected_hash:
            raise RuntimeError(f"code provenance changed after generation: {relative}")

    canonical, canonical_hashes = _load_canonical_corpora()
    recorded_hashes = manifest.get("database_snapshot", {}).get(
        "canonical_chunks_jsonl_sha256"
    )
    if canonical_hashes != recorded_hashes:
        raise RuntimeError("canonical corpus hashes differ from generation manifest")
    task_by_key = {task.key: task for task in tasks}
    for row in generation:
        key = (row["pipeline"], row["condition"], row["qid"])
        _validate_completed_record(
            row,
            task=task_by_key[key],
            canonical_chunks=canonical,
            expected_model=str(manifest["generator_model"]),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generation-dir",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/full",
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/data/benchmark_questions.json",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--harness-config",
        type=Path,
        default=REPO_ROOT / "eval_harness/eval_config.yaml",
    )
    parser.add_argument("--judge-backend", choices=("bedrock", "mock"), default="bedrock")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.trials < 1 or args.max_attempts < 1 or args.workers < 1:
        raise SystemExit("trials, max-attempts, and workers must be positive")
    output_dir = args.output_dir or args.generation_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    generation_path = args.generation_dir / "generation_records.jsonl"
    generation_manifest_path = args.generation_dir / "run_manifest.json"
    if not generation_path.is_file() or not generation_manifest_path.is_file():
        raise SystemExit("generation records/manifest are missing")
    generation = _load_jsonl(generation_path)
    generation_manifest = json.loads(generation_manifest_path.read_text(encoding="utf-8"))
    if len(generation) != int(generation_manifest["expected_records"]):
        raise RuntimeError("generation matrix is incomplete; judging cannot start")
    _validate_generation_artifact(
        generation_dir=args.generation_dir,
        generation=generation,
        manifest=generation_manifest,
        benchmark_path=args.benchmark,
    )

    config = load_config(args.harness_config)
    config.generator.region = config.judge.region
    shared_judge = BedrockStructuredJudgeClient(config) if args.judge_backend == "bedrock" else None
    aws_identity = (
        _preflight_aws(config.judge.region)
        if args.judge_backend == "bedrock"
        else {"status": "not_required_for_mock"}
    )
    evidence = CorpusEvidenceIndex.load(
        REPO_ROOT / "eval_harness/data/corpora/pge_2026_2028_wmp"
    )

    tasks = [
        JudgeTask(record, trial_index)
        for record in generation
        for trial_index in range(1, args.trials + 1)
    ]
    random.Random(42).shuffle(tasks)
    records_path = output_dir / "judge_trial_records.jsonl"
    failures_path = output_dir / "judge_failures.jsonl"
    manifest_path = output_dir / "judge_manifest.json"
    scores_path = output_dir / "answer_scores.jsonl"
    manifest = {
        "schema_version": "okf-judge-manifest-v1",
        "generation_records_sha256": _sha256(generation_path),
        "generation_manifest_sha256": _sha256(generation_manifest_path),
        "answer_count": len(generation),
        "trials_per_answer": args.trials,
        "expected_trial_records": len(tasks),
        "max_attempts_per_trial": args.max_attempts,
        "judge_backend": args.judge_backend,
        "judge_model": config.judge.model_id if args.judge_backend == "bedrock" else "mock-strict-judge",
        "judge_transport": (
            "bedrock_converse_forced_tool" if args.judge_backend == "bedrock" else "mock"
        ),
        "judge_region": config.judge.region,
        "temperature": 0.0,
        "workers": args.workers,
        "python": platform.python_version(),
        "aws_identity": aws_identity,
    }
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            raise RuntimeError("existing judge manifest differs; choose a new output directory")
    else:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    completed = _completed_keys(
        records_path,
        tasks=tasks,
        expected_model=manifest["judge_model"],
        max_attempts=args.max_attempts,
    )
    pending = [task for task in tasks if task.key not in completed]
    print(
        f"[judge] expected={len(tasks)} complete={len(completed)} "
        f"pending={len(pending)} backend={args.judge_backend} workers={args.workers}"
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
                evidence=evidence,
                backend=args.judge_backend,
                shared_judge=shared_judge,
                max_attempts=args.max_attempts,
            ): task
            for task in pending
        }
        for future in as_completed(futures):
            task = futures[future]
            try:
                payload = future.result()
            except JudgeRetriesExhausted as exc:
                failures += 1
                _append_jsonl(
                    failures_path,
                    {
                        "pipeline": task.record["pipeline"],
                        "condition": task.record["condition"],
                        "qid": task.record["qid"],
                        "trial_index": task.trial_index,
                        "error_type": type(exc).__name__,
                        "attempts": [asdict(attempt) for attempt in exc.attempts],
                        "judge_invocations": getattr(exc, "judge_invocations", []),
                        "judge_cost_usd": sum(
                            item.get("cost_usd", 0.0)
                            for item in getattr(exc, "judge_invocations", [])
                        ),
                        "failed_at": _now(),
                    },
                )
            except Exception as exc:
                failures += 1
                _append_jsonl(
                    failures_path,
                    {
                        "pipeline": task.record["pipeline"],
                        "condition": task.record["condition"],
                        "qid": task.record["qid"],
                        "trial_index": task.trial_index,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:2000],
                        "failed_at": _now(),
                    },
                )
            else:
                _append_jsonl(records_path, payload)
                successes += 1
            processed = successes + failures
            if processed % 50 == 0 or processed == len(pending):
                elapsed = time.perf_counter() - started
                total_cost = 0.0
                if records_path.exists():
                    total_cost = sum(
                        row["judge_cost_usd"] for row in _load_jsonl(records_path)
                    )
                print(
                    f"[judge] processed={processed}/{len(pending)} failures={failures} "
                    f"elapsed_s={elapsed:.1f} cost_usd={total_cost:.4f}"
                )
    except KeyboardInterrupt:
        interrupted = True
        for future in futures:
            future.cancel()
        print(
            "[judge] interrupted; pending futures cancelled. "
            "Completed trial records are durable and the same command can resume."
        )
    finally:
        pool.shutdown(wait=not interrupted, cancel_futures=interrupted)
    if interrupted:
        raise SystemExit(130)

    final_keys = _completed_keys(
        records_path,
        tasks=tasks,
        expected_model=manifest["judge_model"],
        max_attempts=args.max_attempts,
    )
    print(
        f"[judge] final_complete={len(final_keys)}/{len(tasks)} "
        f"new_failures={failures} records={records_path}"
    )
    if len(final_keys) != len(tasks):
        raise SystemExit(2)
    trials = _load_jsonl(records_path)
    _write_answer_scores(generation, trials, scores_path, args.trials)
    print(scores_path)


if __name__ == "__main__":
    main()
