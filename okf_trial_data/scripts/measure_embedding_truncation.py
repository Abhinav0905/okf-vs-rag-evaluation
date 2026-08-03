#!/usr/bin/env python3
"""Measure how much of each passage the frozen dense encoder can actually read.

The confirmatory dense arm uses ``sentence-transformers/all-MiniLM-L6-v2``, whose
maximum input is 256 word-piece tokens. Passages longer than that are silently
truncated, so the part beyond the limit never reaches the embedding and cannot be
matched. A lexical index has no such limit.

This quantifies the handicap so the manuscript can cite a measured figure rather
than an asserted one. No network access and no model weights are required beyond
the tokenizer.

Writes ``results/embedding_truncation.json``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for source_root in (REPO_ROOT / "okf_trial_data/src", REPO_ROOT / "eval_harness/src"):
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

from okf_trial_data.fair_baselines import load_raw_chunks  # noqa: E402

MINILM = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_MAX_TOKENS = 256
TITAN = "amazon.titan-embed-text-v2:0"
TITAN_MAX_TOKENS = 8192


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="PGE", help="corpus to measure; 'all' for every corpus")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/embedding_truncation.json",
    )
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MINILM)
    chunks = load_raw_chunks()
    if args.corpus.lower() != "all":
        chunks = [chunk for chunk in chunks if chunk.corpus == args.corpus]
    if not chunks:
        raise SystemExit(f"no chunks found for corpus {args.corpus!r}")

    # add_special_tokens=False measures the passage itself, not the [CLS]/[SEP] pair.
    lengths = [len(tokenizer.encode(chunk.text, add_special_tokens=False)) for chunk in chunks]
    over = [length for length in lengths if length > MINILM_MAX_TOKENS]
    retained = [min(length, MINILM_MAX_TOKENS) / length for length in lengths]

    payload = {
        "corpus": args.corpus,
        "passages": len(lengths),
        "tokenizer": MINILM,
        "frozen_encoder": {"model": MINILM, "max_input_tokens": MINILM_MAX_TOKENS},
        "diagnostic_encoder": {"model": TITAN, "max_input_tokens": TITAN_MAX_TOKENS},
        "token_length": {
            "mean": statistics.mean(lengths),
            "median": statistics.median(lengths),
            "p90": sorted(lengths)[int(0.9 * (len(lengths) - 1))],
            "max": max(lengths),
            "min": min(lengths),
        },
        "truncated_passages": len(over),
        "truncated_fraction": len(over) / len(lengths),
        "mean_fraction_of_passage_encoded": statistics.mean(retained),
        "median_fraction_of_passage_encoded": statistics.median(retained),
        "note": (
            "Passages longer than max_input_tokens are truncated by the frozen "
            "encoder, so the remainder is never embedded. BM25 indexes every token."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(args.output)


if __name__ == "__main__":
    main()
