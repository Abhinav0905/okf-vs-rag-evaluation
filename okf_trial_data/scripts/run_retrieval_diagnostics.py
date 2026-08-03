#!/usr/bin/env python3
"""Decompose the observed retrieval differences into their causes.

The frozen confirmatory run (``scripts/run_retrieval_benchmark.py``) compared
``raw_vector``, ``okf_hybrid`` and ``okf_native``.  ``okf_native`` scored far
above ``raw_vector``, but that single contrast mixes three different factors:
lexical versus dense matching, embedding truncation, and OKF itself.

This script keeps the corpus, questions, top-k and page-level scoring fixed and
varies one factor at a time.  Frozen-run conditions are read from the existing
records rather than recomputed, so nothing in the confirmatory result changes.

These arms are diagnostic and exploratory.  They were added after the
confirmatory run and are not part of the preregistered hypothesis family.

Usage
-----
    python scripts/run_retrieval_diagnostics.py [--top-k 10] [--skip-titan]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
for source_root in (REPO_ROOT / "okf_trial_data/src", REPO_ROOT / "eval_harness/src"):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from okf_trial_data.evaluator import (  # noqa: E402
    PairedDifference,
    cluster_bootstrap_mean_difference,
    exact_mcnemar,
    holm_adjust,
)
from okf_trial_data.fair_baselines import (  # noqa: E402
    AdjacencyWrapper,
    BM25RawRetriever,
    OKFEvidenceOnlyRetriever,
    RRFFusionRetriever,
    TitanDenseRetriever,
    load_raw_chunks,
)
from okf_trial_data.harness_adapter import load_benchmark, retrieval_outcomes  # noqa: E402
from okf_trial_data.okf_bundle import OKFBundle  # noqa: E402

BUNDLE_DIR = REPO_ROOT / "okf_trial_data/data/okf_bundles/wmp_all_v0_2"
BENCHMARK = REPO_ROOT / "okf_trial_data/data/benchmark_questions.json"
FROZEN_RECORDS = REPO_ROOT / "okf_trial_data/results/retrieval/retrieval_records.jsonl"
EMBED_CACHE = REPO_ROOT / "okf_trial_data/data/titan_embeddings.json"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def page_ndcg(chunks: Sequence[Mapping[str, Any]], expected_pages: Sequence[int]) -> float:
    """Binary page-level nDCG over the ranked list.

    A position scores 1 the first time it contributes a not-yet-seen expected
    page, so several chunks from one page cannot inflate the gain.  The ideal
    ranking places ``min(len(expected), len(chunks))`` relevant positions first.
    """

    expected = {int(page) for page in expected_pages}
    if not expected:
        return 0.0
    credited: set[int] = set()
    dcg = 0.0
    for rank, chunk in enumerate(chunks, start=1):
        pages = set()
        page_number = chunk.get("page_number")
        if isinstance(page_number, int):
            pages.add(page_number)
        pages.update(
            value
            for value in (chunk.get("metadata") or {}).get("pages", [])
            if isinstance(value, int)
        )
        fresh = pages.intersection(expected) - credited
        if fresh:
            credited.update(fresh)
            dcg += 1.0 / math.log2(rank + 1)
    ideal_count = min(len(expected), len(chunks))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / idcg if idcg > 0 else 0.0


def summarise(label: str, config: str, per_question: Mapping[str, Mapping[str, Any]],
              latencies: Sequence[float] | None = None) -> dict[str, Any]:
    scored = [m for m in per_question.values() if m.get("page_hit") is not None]
    return {
        "label": label,
        "config": config,
        "questions": len(per_question),
        "scored_questions": len(scored),
        "page_hit_rate": statistics.mean(float(m["page_hit"]) for m in scored),
        "mean_expected_page_recall": statistics.mean(m["expected_page_recall"] for m in scored),
        "mean_reciprocal_rank": statistics.mean(m["reciprocal_rank"] for m in scored),
        "mean_ndcg_at_k": statistics.mean(m.get("ndcg", 0.0) for m in scored),
        "median_latency_ms": statistics.median(latencies) if latencies else None,
    }


# ---------------------------------------------------------------------------
# Arm execution
# ---------------------------------------------------------------------------


def _clear_query_caches(retriever: Any) -> None:
    """Drop memoised query embeddings so latency is measured, not replayed.

    ``TitanDenseRetriever`` caches query vectors, which is correct for
    throughput but would make any arm that reuses a query appear almost
    instantaneous.  Latency is a reported endpoint, so every arm must pay the
    embedding round-trip exactly once per question.
    """

    targets = [retriever, getattr(retriever, "base", None), *getattr(retriever, "arms", [])]
    for target in targets:
        cache = getattr(target, "_query_cache", None)
        if isinstance(cache, dict):
            cache.clear()


def run_live_arm(retriever: Any, questions: Sequence[Mapping[str, Any]], *, top_k: int
                 ) -> tuple[dict[str, dict[str, Any]], list[float]]:
    per_question: dict[str, dict[str, Any]] = {}
    latencies: list[float] = []
    _clear_query_caches(retriever)
    for question in questions:
        started = time.perf_counter()
        chunks = retriever.dense_search(
            question["question"], question.get("corpus", "PGE"), top_k=top_k
        )
        latencies.append((time.perf_counter() - started) * 1000.0)
        metrics = dict(retrieval_outcomes(chunks, question["expected_pages"]))
        metrics["ndcg"] = page_ndcg(chunks, question["expected_pages"])
        per_question[question["qid"]] = metrics
    return per_question, latencies


def load_frozen_arms(path: Path, top_k: int) -> dict[str, dict[str, dict[str, Any]]]:
    """Read per-question metrics for the frozen confirmatory conditions."""

    arms: dict[str, dict[str, dict[str, Any]]] = {}
    for line in path.open(encoding="utf-8"):
        row = json.loads(line)
        if int(row.get("top_k", top_k)) != top_k:
            continue
        metrics = dict(row["metrics"])
        # The frozen run did not record nDCG; recompute it from the stored hits.
        metrics["ndcg"] = page_ndcg(
            [
                {"page_number": hit.get("page_number"),
                 "metadata": {"pages": hit.get("page_numbers") or []}}
                for hit in row.get("hits", [])
            ],
            row["expected_pages"],
        )
        arms.setdefault(row["condition"], {})[row["qid"]] = metrics
    return arms


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


CONTRASTS = [
    # (label, arm_a, arm_b) -- tests whether B differs from A
    ("confirmatory: dense_minilm -> okf_hybrid", "raw_vector", "okf_hybrid"),
    ("truncation effect: dense_minilm -> dense_titan", "raw_vector", "titan_dense"),
    ("lexical effect: dense_minilm -> bm25_raw", "raw_vector", "bm25_raw"),
    ("lexical vs fair dense: dense_titan -> bm25_raw", "titan_dense", "bm25_raw"),
    ("does OKF beat plain BM25: bm25_raw -> okf_native", "bm25_raw", "okf_native"),
    ("OKF frontmatter: okf_evidence_only -> okf_native", "okf_evidence_only", "okf_native"),
    ("adjacency without OKF: bm25_raw -> bm25_raw_adjacent", "bm25_raw", "bm25_raw_adjacent"),
    ("adjacency on fair dense: dense_titan -> dense_titan_adjacent", "titan_dense", "titan_dense_adjacent"),
    ("fusion: bm25_raw -> rrf_bm25_titan", "bm25_raw", "rrf_bm25_titan"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--skip-titan", action="store_true",
                        help="omit the Bedrock embedding arms (offline mode)")
    parser.add_argument("--output-dir", type=Path,
                        default=REPO_ROOT / "okf_trial_data/results/retrieval_diagnostics")
    args = parser.parse_args()

    bundle = OKFBundle.load(BUNDLE_DIR)
    bundle.verify_integrity()
    raw_chunks = load_raw_chunks()

    # Integrity gate: the OKF arms and the raw arms must see identical text, or
    # no comparison between them is meaningful.
    by_chunk = {concept.source_chunk_id: concept for concept in bundle}
    raw_by_id = {chunk.chunk_id: chunk for chunk in raw_chunks}
    if set(by_chunk) != set(raw_by_id):
        raise SystemExit("corpus membership differs between the bundle and pgvector")
    mismatches = [
        cid for cid, concept in by_chunk.items()
        if concept.evidence.strip() != raw_by_id[cid].text.strip()
    ]
    if mismatches:
        raise SystemExit(f"{len(mismatches)} passages differ in text, e.g. {mismatches[:5]}")
    print(f"[integrity] {len(raw_by_id)} passages identical in bundle and pgvector")

    benchmark = load_benchmark(BENCHMARK)
    questions = [
        q for q in benchmark["questions"] if q.get("answerable") and q.get("expected_pages")
    ]
    print(f"[benchmark] {benchmark['benchmark_id']}  scored questions={len(questions)}\n")

    arms: dict[str, dict[str, dict[str, Any]]] = {}
    summaries: list[dict[str, Any]] = []

    frozen = load_frozen_arms(FROZEN_RECORDS, args.top_k)
    for condition in ("raw_vector", "okf_hybrid", "okf_native"):
        if condition not in frozen:
            raise SystemExit(f"frozen records missing condition {condition}")
        arms[condition] = frozen[condition]
        summaries.append(summarise(condition, "frozen confirmatory run", frozen[condition]))

    bm25_raw = BM25RawRetriever(raw_chunks)
    live: list[tuple[str, Any, str]] = [
        ("bm25_raw", bm25_raw, f"BM25 over raw chunks, top_k={args.top_k}, no OKF"),
        ("bm25_raw_adjacent", AdjacencyWrapper(bm25_raw),
         f"BM25 raw, {math.ceil(args.top_k/2)} seeds + ordinal neighbours"),
        ("okf_evidence_only", OKFEvidenceOnlyRetriever(bundle, link_decay=0.35),
         "OKF consumer, frontmatter removed from the index"),
    ]

    if not args.skip_titan:
        titan = TitanDenseRetriever(raw_chunks, EMBED_CACHE)
        live.append(("titan_dense", titan,
                     f"{titan.model_id} (8192-token window), top_k={args.top_k}"))
        live.append(("titan_dense_adjacent", AdjacencyWrapper(titan),
                     f"Titan dense, {math.ceil(args.top_k/2)} seeds + ordinal neighbours"))
        live.append(("rrf_bm25_titan", RRFFusionRetriever([bm25_raw, titan]),
                     "reciprocal-rank fusion (k=60, depth=50) of BM25 and Titan"))

    for label, retriever, config in live:
        print(f"[arm] {label} ...", flush=True)
        if label == "okf_evidence_only":
            # Match the OKF consumer's seed/traversal budget exactly.
            per_question: dict[str, dict[str, Any]] = {}
            latencies: list[float] = []
            seed_k = max(1, math.ceil(args.top_k * 0.5))
            for question in questions:
                started = time.perf_counter()
                hits = retriever.search(
                    question["question"], corpus=question.get("corpus", "PGE"),
                    top_k=args.top_k, seed_k=seed_k, max_link_depth=1,
                )
                latencies.append((time.perf_counter() - started) * 1000.0)
                chunk_dicts = [hit.as_chunk_dict() for hit in hits]
                metrics = dict(retrieval_outcomes(chunk_dicts, question["expected_pages"]))
                metrics["ndcg"] = page_ndcg(chunk_dicts, question["expected_pages"])
                per_question[question["qid"]] = metrics
        else:
            per_question, latencies = run_live_arm(retriever, questions, top_k=args.top_k)
        arms[label] = per_question
        summaries.append(summarise(label, config, per_question, latencies))

    # ---- report ----------------------------------------------------------
    print()
    header = f"{'arm':24}{'page_hit':>10}{'recall':>9}{'MRR':>8}{'nDCG':>8}{'ms':>9}"
    print(header)
    print("-" * len(header))
    order = ["raw_vector", "titan_dense", "bm25_raw", "rrf_bm25_titan",
             "okf_hybrid", "okf_native", "okf_evidence_only",
             "bm25_raw_adjacent", "titan_dense_adjacent"]
    ranked = sorted(summaries, key=lambda s: order.index(s["label"]) if s["label"] in order else 99)
    for s in ranked:
        latency = f"{s['median_latency_ms']:.2f}" if s["median_latency_ms"] else "frozen"
        print(f"{s['label']:24}{s['page_hit_rate']:>10.4f}{s['mean_expected_page_recall']:>9.4f}"
              f"{s['mean_reciprocal_rank']:>8.4f}{s['mean_ndcg_at_k']:>8.4f}{latency:>9}")

    # ---- paired statistics ----------------------------------------------
    qids = [q["qid"] for q in questions]
    tests: dict[str, dict[str, Any]] = {}
    raw_p: dict[str, float] = {}
    for label, arm_a, arm_b in CONTRASTS:
        if arm_a not in arms or arm_b not in arms:
            continue
        a_hits = [int(arms[arm_a][q]["page_hit"]) for q in qids]
        b_hits = [int(arms[arm_b][q]["page_hit"]) for q in qids]
        mcnemar = exact_mcnemar(a_hits, b_hits)
        pairs = [
            PairedDifference(
                pipeline="retrieval", qid=q,
                raw_vector=arms[arm_a][q]["expected_page_recall"],
                okf_hybrid=arms[arm_b][q]["expected_page_recall"],
                difference=arms[arm_b][q]["expected_page_recall"]
                - arms[arm_a][q]["expected_page_recall"],
            )
            for q in qids
        ]
        bootstrap = cluster_bootstrap_mean_difference(pairs, repetitions=10_000, seed=42)
        tests[label] = {
            "arm_a": arm_a, "arm_b": arm_b,
            "page_hit_mcnemar": mcnemar,
            "recall_delta": bootstrap,
        }
        raw_p[label] = float(mcnemar["p_value"])

    adjusted = holm_adjust(raw_p) if raw_p else {}
    print("\npaired contrasts (page-hit McNemar, Holm-adjusted across the diagnostic family)")
    print(f"{'contrast':52}{'a>b':>5}{'b>a':>5}{'p':>11}{'p_holm':>10}   recall delta [95% CI]")
    print("-" * 128)
    for label, result in tests.items():
        m = result["page_hit_mcnemar"]
        b = result["recall_delta"]
        result["page_hit_p_holm"] = adjusted.get(label)
        print(f"{label:52}{m['raw_only_correct']:>5}{m['okf_only_correct']:>5}"
              f"{m['p_value']:>11.2e}{adjusted.get(label, float('nan')):>10.4f}"
              f"   {b['mean_difference']:+.4f} [{b['ci_low']:+.4f}, {b['ci_high']:+.4f}]")
    print("\n'a>b' = questions where only arm A retrieved an expected page; 'b>a' = only arm B.")

    # ---- persist ---------------------------------------------------------
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records_path = args.output_dir / "diagnostic_records.jsonl"
    with records_path.open("w", encoding="utf-8") as handle:
        for label, per_question in sorted(arms.items()):
            for qid, metrics in sorted(per_question.items()):
                handle.write(json.dumps(
                    {"arm": label, "qid": qid, "metrics": metrics},
                    ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "experiment_id": "okf_wmp_retrieval_diagnostics_v1",
        "status": "exploratory_diagnostic_added_after_confirmatory_run",
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": hashlib.sha256(BENCHMARK.read_bytes()).hexdigest(),
        "top_k": args.top_k,
        "scored_questions": len(questions),
        "embedding_arms_included": not args.skip_titan,
        "arms": {s["label"]: {k: v for k, v in s.items() if k != "label"} for s in summaries},
        "contrasts": tests,
        "multiplicity": {"method": "holm", "family": "retrieval_diagnostic_contrasts",
                         "n_tests": len(raw_p)},
    }
    summary_path = args.output_dir / "diagnostic_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {records_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
