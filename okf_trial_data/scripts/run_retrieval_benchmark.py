#!/usr/bin/env python3
"""Run the deterministic, no-LLM retrieval portion of the OKF experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SRC = REPO_ROOT / "okf_trial_data/src"
HARNESS_SRC = REPO_ROOT / "eval_harness/src"
for source_root in (PACKAGE_SRC, HARNESS_SRC):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from evaluation.config import load_config, set_global_seed  # noqa: E402
from evaluation.retriever import get_retriever  # noqa: E402
from okf_trial_data.evaluator import exact_mcnemar  # noqa: E402
from okf_trial_data.harness_adapter import (  # noqa: E402
    OKFHybridHarnessRetriever,
    OKFNativeHarnessRetriever,
    load_benchmark,
    retrieval_outcomes,
)
from okf_trial_data.okf_bundle import OKFBundle  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _chunk_record(chunk: Any) -> dict[str, Any]:
    metadata = dict(chunk.metadata or {})
    pages = metadata.get("page_numbers", metadata.get("pages", []))
    if not pages and chunk.page_number is not None:
        pages = [chunk.page_number]
    return {
        "chunk_id": chunk.chunk_id,
        "page_number": chunk.page_number,
        "page_numbers": pages,
        "score": chunk.score,
        "retrieval_mode": metadata.get("okf_retrieval_mode", "raw_vector"),
        "link_depth": metadata.get("okf_link_depth", 0),
        "seed_concept_ids": metadata.get("okf_seed_concept_ids", []),
    }


def _summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for condition in sorted({row["condition"] for row in rows}):
        subset = [row for row in rows if row["condition"] == condition]
        scored = [row for row in subset if row["metrics"]["page_hit"] is not None]
        result[condition] = {
            "questions": len(subset),
            "scored_questions": len(scored),
            "page_hit_rate": statistics.mean(
                float(row["metrics"]["page_hit"]) for row in scored
            ),
            "mean_expected_page_recall": statistics.mean(
                row["metrics"]["expected_page_recall"] for row in scored
            ),
            "mean_reciprocal_rank": statistics.mean(
                row["metrics"]["reciprocal_rank"] for row in scored
            ),
            "median_latency_ms": statistics.median(row["latency_ms"] for row in subset),
            "mean_linked_chunk_fraction": statistics.mean(
                row["metrics"]["linked_chunk_fraction"] for row in subset
            ),
        }
    by_key = {(row["condition"], row["qid"]): row for row in rows}
    qids = [
        row["qid"]
        for row in rows
        if row["condition"] == "raw_vector" and row["metrics"]["page_hit"] is not None
    ]
    raw_hits = [int(by_key[("raw_vector", qid)]["metrics"]["page_hit"]) for qid in qids]
    okf_hits = [int(by_key[("okf_hybrid", qid)]["metrics"]["page_hit"]) for qid in qids]
    native_hits = [int(by_key[("okf_native", qid)]["metrics"]["page_hit"]) for qid in qids]
    result["raw_vs_okf_hybrid_page_hit_mcnemar"] = exact_mcnemar(raw_hits, okf_hits)
    result["raw_vs_okf_native_page_hit_mcnemar"] = exact_mcnemar(raw_hits, native_hits)
    result["okf_hybrid_vs_okf_native_page_hit_mcnemar"] = exact_mcnemar(
        okf_hits, native_hits
    )
    return result


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
        default=REPO_ROOT / "okf_trial_data/results/retrieval",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    experiment = yaml.safe_load(args.experiment_config.read_text(encoding="utf-8"))
    benchmark_path = REPO_ROOT / "okf_trial_data" / experiment["experiment"]["benchmark"]
    bundle_path = REPO_ROOT / "okf_trial_data" / experiment["okf"]["bundles_dir"] / "wmp_all_v0_2"
    bundle = OKFBundle.load(bundle_path)
    bundle.verify_integrity()

    config = load_config(args.harness_config)
    config.retriever.device = "cpu"
    set_global_seed(int(experiment["experiment"]["seed"]))
    base = get_retriever(config)
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
    treatments = {
        "raw_vector": base,
        "okf_native": native,
        "okf_hybrid": hybrid,
    }

    benchmark = load_benchmark(benchmark_path)
    questions = list(benchmark["questions"])
    if args.limit:
        questions = questions[: args.limit]

    # Warm the embedding model and database connection outside timed records.
    base.dense_search(questions[0]["question"], questions[0]["corpus"], top_k=1)

    rng = random.Random(int(experiment["experiment"]["seed"]))
    rows: list[dict[str, Any]] = []
    for number, question in enumerate(questions, start=1):
        order = list(treatments)
        rng.shuffle(order)
        for condition in order:
            started = time.perf_counter()
            chunks = treatments[condition].dense_search(
                question["question"], question["corpus"], top_k=args.top_k
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            rows.append(
                {
                    "qid": question["qid"],
                    "category": question["category"],
                    "answerable": question["answerable"],
                    "expected_pages": question["expected_pages"],
                    "condition": condition,
                    "top_k": args.top_k,
                    "latency_ms": elapsed_ms,
                    "metrics": retrieval_outcomes(chunks, question["expected_pages"]),
                    "hits": [_chunk_record(chunk) for chunk in chunks],
                }
            )
        if number % 10 == 0 or number == len(questions):
            print(f"[retrieval] {number}/{len(questions)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records_path = args.output_dir / "retrieval_records.jsonl"
    records_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = {
        "experiment_id": experiment["experiment"]["id"],
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": _sha256(benchmark_path),
        "bundle_content_sha256": json.loads(
            (bundle_path / "bundle_manifest.json").read_text(encoding="utf-8")
        )["bundle_content_sha256"],
        "top_k": args.top_k,
        "condition_order": "seeded within-question randomization",
        "results": _summarise(rows),
    }
    summary_path = args.output_dir / "retrieval_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["results"], indent=2, sort_keys=True))
    print(records_path)
    print(summary_path)
    base.close()


if __name__ == "__main__":
    main()
