#!/usr/bin/env python3
"""Compare topic-structured OKF against chunk retrieval at a matched token budget.

The question
------------
Does organising a document as OKF intends - one concept per topic, nested, with
real links - retrieve answer evidence better than retrieving flat text chunks?

Why top-k would be the wrong comparison
---------------------------------------
Topic concepts and 500-token chunks are different sizes (topic median is about 76
words, chunks about 260, largest topic 3,360). Asking each arm for its top 10
units would hand more text to whichever arm has bigger units, and more text
trivially covers more pages. So every arm here fills the **same context token
budget** and is scored on what actually lands inside that budget, which is the
measure the protocol names as most defensible.

Packing rule: walk the ranked list, add a unit whole if it fits in the remaining
budget, skip it if it does not, and stop when the budget is exhausted. Units are
never truncated, because a truncated passage would otherwise earn page credit for
text that was not supplied.

Arms
----
``chunks_dense``        dense MiniLM over the original chunks (the frozen baseline)
``chunks_bm25``         BM25 over the original chunks - the strong non-OKF baseline
``okf_chain_bm25``      chunk-preserving OKF bundle, BM25 + previous/next links
``okf_topic_bm25``      topic bundle, BM25 over topic text and heading, no traversal
``okf_topic_hierarchy`` topic bundle, BM25 seeds + one hop over parent/child/sibling links

Usage
-----
    scripts/with_experiment_env.sh .venv/bin/python \\
        scripts/run_topic_retrieval_comparison.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
from okf_trial_data.fair_baselines import BM25RawRetriever, load_raw_chunks  # noqa: E402
from okf_trial_data.harness_adapter import load_benchmark  # noqa: E402
from okf_trial_data.okf_bundle import OKFBundle  # noqa: E402
from okf_trial_data.okf_retrievers import OKFNativeRetriever  # noqa: E402

BENCHMARK = REPO_ROOT / "okf_trial_data/data/benchmark_questions.json"
CHAIN_BUNDLE = REPO_ROOT / "okf_trial_data/data/okf_bundles/wmp_all_v0_2"
TOPIC_BUNDLE = REPO_ROOT / "okf_trial_data/data/okf_bundles/pge_topics_v0_2"
TOKENIZER = "sentence-transformers/all-MiniLM-L6-v2"

CONTRASTS = [
    ("baseline: dense chunks -> BM25 chunks", "chunks_dense", "chunks_bm25"),
    ("OKF chain vs BM25 chunks", "chunks_bm25", "okf_chain_bm25"),
    ("topic structure vs BM25 chunks", "chunks_bm25", "okf_topic_bm25"),
    ("topic structure vs OKF chain", "okf_chain_bm25", "okf_topic_bm25"),
    ("following hierarchy links", "okf_topic_bm25", "okf_topic_hierarchy"),
    ("topic hierarchy vs BM25 chunks", "chunks_bm25", "okf_topic_hierarchy"),
    # The requested A/B: plain RAG versus vector-database-plus-OKF.
    ("A/B: plain RAG -> OKF+RAG (topic)", "chunks_dense", "okf_plus_rag_topic"),
    ("A/B: plain RAG -> OKF+RAG (chain)", "chunks_dense", "okf_plus_rag_chain"),
    ("OKF+RAG (topic) vs BM25 chunks", "chunks_bm25", "okf_plus_rag_topic"),
]


class Unit:
    """One retrievable unit: its text, its pages, and its token cost."""

    __slots__ = ("uid", "text", "pages", "tokens")

    def __init__(self, uid: str, text: str, pages: Sequence[int], tokens: int) -> None:
        self.uid = uid
        self.text = text
        self.pages = tuple(sorted({int(p) for p in pages}))
        self.tokens = tokens


def _count_tokens(texts: Sequence[str]) -> list[int]:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER)
    return [
        len(tokenizer.encode(text, add_special_tokens=False, truncation=False))
        for text in texts
    ]


def pack(units: Sequence[Unit], budget: int) -> list[Unit]:
    """Fill the budget with whole units in rank order."""

    packed: list[Unit] = []
    remaining = budget
    for unit in units:
        if unit.tokens <= remaining:
            packed.append(unit)
            remaining -= unit.tokens
        if remaining <= 0:
            break
    return packed


def fuse_rrf(ranked_lists: Sequence[Sequence[Unit]], *, k: float = 60.0) -> list[Unit]:
    """Reciprocal-rank fusion across retrievers that return different unit types.

    This is the "OKF plus RAG" arm: the vector database and the OKF bundle are
    queried independently and their ranked lists merged, rather than one
    replacing the other. Units from the two sources are different sizes, so
    fusion happens on rank position, which is scale-free.
    """

    scores: dict[str, float] = {}
    lookup: dict[str, Unit] = {}
    for ranked in ranked_lists:
        for rank, unit in enumerate(ranked, start=1):
            lookup[unit.uid] = unit
            scores[unit.uid] = scores.get(unit.uid, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [lookup[uid] for uid, _ in ordered]


def redundancy(packed: Sequence[Unit]) -> float:
    """Fraction of packed tokens whose pages were already covered by an earlier unit.

    The OKF bundle holds a verbatim copy of the same document, so a fused context
    can spend budget twice on the same words. This quantifies that waste.
    """

    seen: set[int] = set()
    duplicate = 0
    total = 0
    for unit in packed:
        total += unit.tokens
        if unit.pages and set(unit.pages) <= seen:
            duplicate += unit.tokens
        seen |= set(unit.pages)
    return duplicate / total if total else 0.0


def score(packed: Sequence[Unit], expected_pages: Sequence[int]) -> dict[str, Any]:
    expected = {int(p) for p in expected_pages}
    covered: set[int] = set()
    rank_of_first_hit = 0
    for rank, unit in enumerate(packed, start=1):
        hit = expected & set(unit.pages)
        if hit and rank_of_first_hit == 0:
            rank_of_first_hit = rank
        covered |= hit
    return {
        "page_hit": bool(covered),
        "expected_page_recall": len(covered) / len(expected) if expected else None,
        "reciprocal_rank": 1.0 / rank_of_first_hit if rank_of_first_hit else 0.0,
        "units_in_context": len(packed),
        "tokens_in_context": sum(u.tokens for u in packed),
        "pages_in_context": len({p for u in packed for p in u.pages}),
        "duplicate_token_fraction": redundancy(packed),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-budget", type=int, default=2200)
    parser.add_argument("--candidate-depth", type=int, default=40,
                        help="ranked units requested per arm before packing")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/topic_okf",
    )
    args = parser.parse_args()

    benchmark = load_benchmark(BENCHMARK)
    questions = [
        q for q in benchmark["questions"] if q.get("answerable") and q.get("expected_pages")
    ]
    print(f"[benchmark] {benchmark['benchmark_id']}  scored questions={len(questions)}")
    print(f"[budget]    {args.token_budget} tokens, whole units only\n")

    # ---- unit inventories -------------------------------------------------
    raw_chunks = [c for c in load_raw_chunks() if c.corpus == "PGE"]
    chain_bundle = OKFBundle.load(CHAIN_BUNDLE)
    topic_bundle = OKFBundle.load(TOPIC_BUNDLE)
    topic_bundle.verify_integrity()

    chunk_tokens = dict(
        zip([c.chunk_id for c in raw_chunks], _count_tokens([c.text for c in raw_chunks]))
    )
    def chunk_pages(chunk: Any) -> list[int]:
        """Every page a chunk covers.

        266 of the 654 PG&E chunks straddle a page boundary and their metadata
        lists both pages. Using only ``page_number`` would credit the chunk arms
        with one page while the OKF arms, which carry the full ``page_numbers``
        list for the same text, were credited with two.
        """

        pages = [p for p in (chunk.metadata or {}).get("pages", []) if isinstance(p, int)]
        if not pages and chunk.page_number is not None:
            pages = [chunk.page_number]
        return pages

    chunk_units = {
        c.chunk_id: Unit(c.chunk_id, c.text, chunk_pages(c), chunk_tokens[c.chunk_id])
        for c in raw_chunks
    }

    topic_concepts = [c for c in topic_bundle if c.corpus == "PGE"]
    topic_tokens = dict(
        zip(
            [c.concept_id for c in topic_concepts],
            _count_tokens([c.evidence for c in topic_concepts]),
        )
    )
    topic_units = {
        c.concept_id: Unit(
            c.concept_id,
            c.evidence,
            c.frontmatter.get("page_numbers") or [],
            topic_tokens[c.concept_id],
        )
        for c in topic_concepts
    }
    chain_concepts = [c for c in chain_bundle if c.corpus == "PGE"]
    chain_units = {
        c.concept_id: Unit(
            c.concept_id,
            c.evidence,
            c.frontmatter.get("page_numbers") or [],
            chunk_tokens.get(c.source_chunk_id, 0),
        )
        for c in chain_concepts
    }

    print(f"[units] chunks={len(chunk_units)}  chain concepts={len(chain_units)}  "
          f"topic concepts={len(topic_units)}")
    for name, units in (("chunk", chunk_units), ("topic", topic_units)):
        sizes = sorted(u.tokens for u in units.values())
        print(f"        {name} tokens: median {sizes[len(sizes)//2]}  "
              f"mean {sum(sizes)//len(sizes)}  max {sizes[-1]}")
    print()

    # ---- retrievers -------------------------------------------------------
    from evaluation.config import load_config, set_global_seed
    from evaluation.retriever import get_retriever

    config = load_config(REPO_ROOT / "eval_harness/eval_config.yaml")
    config.retriever.device = "cpu"
    set_global_seed(42)
    dense = get_retriever(config)

    question_pages = {q["question"]: tuple(q["expected_pages"]) for q in questions}
    bm25_chunks = BM25RawRetriever(raw_chunks)
    chain_bm25 = OKFNativeRetriever(chain_bundle, link_decay=0.35)
    topic_bm25 = OKFNativeRetriever(topic_bundle, link_decay=0.35)

    depth = args.candidate_depth

    def arm_chunks_dense(question: str) -> list[Unit]:
        hits = dense.dense_search(question, "PGE", top_k=depth)
        return [chunk_units[h.chunk_id] for h in hits if h.chunk_id in chunk_units]

    def arm_chunks_bm25(question: str) -> list[Unit]:
        return [chunk_units[cid] for cid, _ in bm25_chunks.ranked(question, "PGE", depth)]

    def arm_chain_bm25(question: str) -> list[Unit]:
        hits = chain_bm25.search(question, corpus="PGE", top_k=depth,
                                 seed_k=max(1, depth // 2), max_link_depth=1)
        return [chain_units[h.concept_id] for h in hits if h.concept_id in chain_units]

    def arm_topic_bm25(question: str) -> list[Unit]:
        hits = topic_bm25.search(question, corpus="PGE", top_k=depth,
                                 seed_k=depth, max_link_depth=0)
        return [topic_units[h.concept_id] for h in hits if h.concept_id in topic_units]

    # Mechanism accounting for the hierarchy arm: how many packed units arrived by
    # link traversal, and whether any expected page was supplied *only* by one.
    mechanism = {"packed_units": 0, "from_traversal": 0, "pages_only_from_traversal": 0}

    def arm_topic_hierarchy(question: str) -> list[Unit]:
        hits = topic_bm25.search(question, corpus="PGE", top_k=depth,
                                 seed_k=max(1, depth // 2), max_link_depth=1)
        by_id = {h.concept_id: h for h in hits}
        units = [topic_units[h.concept_id] for h in hits if h.concept_id in topic_units]
        packed = pack(units, args.token_budget)
        traversed = [u for u in packed if by_id[u.uid].link_depth > 0]
        direct_pages = {
            p for u in packed if by_id[u.uid].link_depth == 0 for p in u.pages
        }
        expected = {int(p) for p in question_pages.get(question, ())}
        mechanism["packed_units"] += len(packed)
        mechanism["from_traversal"] += len(traversed)
        mechanism["pages_only_from_traversal"] += len(
            (expected & {p for u in traversed for p in u.pages}) - direct_pages
        )
        return units

    def arm_okf_plus_rag_topic(question: str) -> list[Unit]:
        """Vector database AND topic-structured OKF, merged."""

        return fuse_rrf([arm_chunks_dense(question), arm_topic_bm25(question)])

    def arm_okf_plus_rag_chain(question: str) -> list[Unit]:
        """Vector database AND the chunk-preserving OKF bundle, merged."""

        return fuse_rrf([arm_chunks_dense(question), arm_chain_bm25(question)])

    arms = {
        "chunks_dense": arm_chunks_dense,
        "chunks_bm25": arm_chunks_bm25,
        "okf_chain_bm25": arm_chain_bm25,
        "okf_topic_bm25": arm_topic_bm25,
        "okf_topic_hierarchy": arm_topic_hierarchy,
        "okf_plus_rag_topic": arm_okf_plus_rag_topic,
        "okf_plus_rag_chain": arm_okf_plus_rag_chain,
    }

    # Warm the embedding model outside the timed loop.
    dense.dense_search(questions[0]["question"], "PGE", top_k=1)

    results: dict[str, dict[str, dict[str, Any]]] = {name: {} for name in arms}
    latency: dict[str, list[float]] = {name: [] for name in arms}
    for number, question in enumerate(questions, start=1):
        for name, fn in arms.items():
            started = time.perf_counter()
            ranked = fn(question["question"])
            latency[name].append((time.perf_counter() - started) * 1000.0)
            packed = pack(ranked, args.token_budget)
            results[name][question["qid"]] = score(packed, question["expected_pages"])
        if number % 20 == 0 or number == len(questions):
            print(f"[progress] {number}/{len(questions)}")
    dense.close()

    # ---- report -----------------------------------------------------------
    summary_arms: dict[str, Any] = {}
    print(f"\n{'arm':22}{'page hit':>10}{'recall':>9}{'MRR':>8}{'units':>8}{'tokens':>9}{'pages':>7}{'dup%':>7}{'ms':>9}")
    print("-" * 89)
    for name in arms:
        rows = list(results[name].values())
        entry = {
            "page_hit_rate": statistics.mean(float(r["page_hit"]) for r in rows),
            "mean_expected_page_recall": statistics.mean(r["expected_page_recall"] for r in rows),
            "mean_reciprocal_rank": statistics.mean(r["reciprocal_rank"] for r in rows),
            "mean_units_in_context": statistics.mean(r["units_in_context"] for r in rows),
            "mean_tokens_in_context": statistics.mean(r["tokens_in_context"] for r in rows),
            "mean_pages_in_context": statistics.mean(r["pages_in_context"] for r in rows),
            "mean_duplicate_token_fraction": statistics.mean(
                r["duplicate_token_fraction"] for r in rows
            ),
            "median_latency_ms": statistics.median(latency[name]),
        }
        summary_arms[name] = entry
        print(f"{name:22}{entry['page_hit_rate']:>10.4f}{entry['mean_expected_page_recall']:>9.4f}"
              f"{entry['mean_reciprocal_rank']:>8.4f}{entry['mean_units_in_context']:>8.1f}"
              f"{entry['mean_tokens_in_context']:>9.0f}{entry['mean_pages_in_context']:>7.1f}"
              f"{100*entry['mean_duplicate_token_fraction']:>6.1f}%"
              f"{entry['median_latency_ms']:>9.2f}")

    qids = [q["qid"] for q in questions]
    tests: dict[str, Any] = {}
    raw_p: dict[str, float] = {}
    for label, a, b in CONTRASTS:
        a_hits = [int(results[a][q]["page_hit"]) for q in qids]
        b_hits = [int(results[b][q]["page_hit"]) for q in qids]
        mcnemar = exact_mcnemar(a_hits, b_hits)
        pairs = [
            PairedDifference(
                pipeline="retrieval", qid=q,
                raw_vector=results[a][q]["expected_page_recall"],
                okf_hybrid=results[b][q]["expected_page_recall"],
                difference=results[b][q]["expected_page_recall"]
                - results[a][q]["expected_page_recall"],
            )
            for q in qids
        ]
        boot = cluster_bootstrap_mean_difference(pairs, repetitions=10_000, seed=42)
        tests[label] = {"arm_a": a, "arm_b": b, "page_hit_mcnemar": mcnemar,
                        "recall_delta": boot}
        raw_p[label] = float(mcnemar["p_value"])
    adjusted = holm_adjust(raw_p)
    for label in tests:
        tests[label]["page_hit_p_holm"] = adjusted[label]

    print(f"\n{'contrast':40}{'a>b':>5}{'b>a':>5}{'p':>11}{'p_holm':>9}   recall delta [95% CI]")
    print("-" * 112)
    for label, result in tests.items():
        m, d = result["page_hit_mcnemar"], result["recall_delta"]
        print(f"{label:40}{m['raw_only_correct']:>5}{m['okf_only_correct']:>5}"
              f"{m['p_value']:>11.2e}{result['page_hit_p_holm']:>9.4f}"
              f"   {d['mean_difference']:+.4f} [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]")

    oversized = sorted(
        (
            {"concept_id": uid, "tokens": unit.tokens}
            for uid, unit in topic_units.items()
            if unit.tokens > args.token_budget
        ),
        key=lambda item: -item["tokens"],
    )
    print(f"\n[mechanism] packed units {mechanism['packed_units']}, "
          f"{mechanism['from_traversal']} arrived via hierarchy links, "
          f"{mechanism['pages_only_from_traversal']} expected pages came only from a link")
    print(f"[granularity] {len(oversized)} topic concepts exceed the {args.token_budget}-token "
          f"budget and can never be retrieved whole")
    for item in oversized[:4]:
        print(f"    {item['tokens']:>6} tok  {item['concept_id'].split('/')[-1][:58]}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = args.output_dir / "topic_records.jsonl"
    with records.open("w", encoding="utf-8") as handle:
        for name in sorted(results):
            for qid in sorted(results[name]):
                handle.write(json.dumps({"arm": name, "qid": qid,
                                         "metrics": results[name][qid]},
                                        sort_keys=True) + "\n")
    topic_manifest = json.loads((TOPIC_BUNDLE / "bundle_manifest.json").read_text())
    summary = {
        "experiment_id": "okf_topic_structure_v1",
        "status": "exploratory_added_after_confirmatory_run",
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": hashlib.sha256(BENCHMARK.read_bytes()).hexdigest(),
        "token_budget": args.token_budget,
        "candidate_depth": depth,
        "packing_rule": "whole units in rank order; never truncated",
        "tokenizer": TOKENIZER,
        "scored_questions": len(questions),
        "topic_bundle": {
            "concept_count": topic_manifest["concept_count"],
            "max_depth": topic_manifest["max_depth"],
            "bundle_content_sha256": topic_manifest["bundle_content_sha256"],
            "topic_source": topic_manifest["topic_source"],
            "text_policy": topic_manifest["text_policy"],
        },
        "oversized_topic_concepts": {
            "token_budget": args.token_budget,
            "count": len(oversized),
            "note": (
                "topic concepts larger than the whole context budget can never be "
                "retrieved, so their text is present in the bundle but unreachable"
            ),
            "largest": oversized[:10],
        },
        "hierarchy_link_mechanism": mechanism,
        "arms": summary_arms,
        "contrasts": tests,
        "multiplicity": {"method": "holm", "family": "topic_structure_contrasts",
                         "n_tests": len(raw_p)},
    }
    summary_path = args.output_dir / "topic_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {records}\nwrote {summary_path}")


if __name__ == "__main__":
    main()
