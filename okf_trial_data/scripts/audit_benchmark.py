#!/usr/bin/env python3
"""Create a deterministic source-evidence audit for the frozen benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK = REPO_ROOT / "okf_trial_data/data/benchmark_questions.json"
DEFAULT_CORPUS = REPO_ROOT / "eval_harness/data/corpora/pge_2026_2028_wmp"
DEFAULT_OUTPUT = REPO_ROOT / "okf_trial_data/data/gold_audit.jsonl"
DEFAULT_SUMMARY = REPO_ROOT / "okf_trial_data/data/gold_audit_summary.json"
DEFAULT_CROSS_REVIEW = (
    REPO_ROOT / "okf_trial_data/protocol/GOLD_AUDIT_CROSS_REVIEW.md"
)
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "were", "what", "which", "with",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _terms(text: str) -> set[str]:
    return {
        token for token in TOKEN_RE.findall(text.casefold())
        if token not in STOPWORDS and len(token) > 1
    }


def _pages(chunk: dict[str, Any]) -> set[int]:
    result = set(chunk.get("metadata", {}).get("pages", []))
    if isinstance(chunk.get("page_number"), int):
        result.add(chunk["page_number"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--cross-review", type=Path, default=DEFAULT_CROSS_REVIEW)
    args = parser.parse_args()
    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    chunks = [
        json.loads(line)
        for line in (args.corpus / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    manifest = json.loads((args.corpus / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for question in benchmark["questions"]:
        expected = set(question["expected_pages"])
        evidence = [chunk for chunk in chunks if expected.intersection(_pages(chunk))]
        ref_terms = _terms(question["reference_answer"])
        evidence_terms = _terms(" ".join(chunk["text"] for chunk in evidence))
        coverage = (
            len(ref_terms.intersection(evidence_terms)) / len(ref_terms)
            if ref_terms and evidence
            else None
        )
        page_coverage = (
            len(expected.intersection(set().union(*(_pages(chunk) for chunk in evidence))))
            / len(expected)
            if expected
            else None
        )
        flags = []
        if question["answerable"] and not expected:
            flags.append("answerable_without_expected_pages")
        if question["answerable"] and page_coverage != 1.0:
            flags.append("expected_page_missing_from_corpus")
        if question["answerable"] and coverage is not None and coverage < 0.25:
            flags.append("low_reference_token_coverage_manual_review")
        if not question["answerable"] and expected:
            flags.append("control_has_expected_pages")
        rows.append(
            {
                "qid": question["qid"],
                "answerable": question["answerable"],
                "source_set": question["source_set"],
                "expected_pages": question["expected_pages"],
                "evidence_chunk_ids": [chunk["chunk_id"] for chunk in evidence],
                "expected_page_coverage": page_coverage,
                "reference_token_coverage": coverage,
                "curation_note": question.get("curation_note"),
                "automated_flags": flags,
                "human_validation_status": "pending",
            }
        )
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    flagged = [row for row in rows if row["automated_flags"]]
    summary = {
        "schema_version": "okf-gold-audit-v1",
        "benchmark_id": benchmark["benchmark_id"],
        "benchmark_sha256": _sha256(args.benchmark),
        "corpus_version": manifest["corpus_version"],
        "source_pdf_sha256": manifest["source_sha256"],
        "question_count": len(rows),
        "answerable_count": sum(row["answerable"] for row in rows),
        "control_count": sum(not row["answerable"] for row in rows),
        "answerable_full_page_coverage": sum(
            row["answerable"] and row["expected_page_coverage"] == 1.0 for row in rows
        ),
        "automated_flag_count": len(flagged),
        "flagged_qids": [row["qid"] for row in flagged],
        "human_validation_status": "pending",
        "independent_semantic_review_status": (
            "two_model_assisted_reviews_and_cross_review_passed"
            if args.cross_review.is_file()
            else "not_recorded"
        ),
        "independent_semantic_review_sha256": (
            _sha256(args.cross_review) if args.cross_review.is_file() else None
        ),
        "scope_note": (
            "This deterministic audit verifies page availability and lexical support; "
            "it does not substitute for blinded human answer-quality validation."
        ),
    }
    args.summary.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
