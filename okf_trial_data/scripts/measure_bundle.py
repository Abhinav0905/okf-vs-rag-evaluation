#!/usr/bin/env python3
"""Measure deterministic OKF bundle construction and storage overhead."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SRC = REPO_ROOT / "okf_trial_data/src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from okf_trial_data.okf_bundle import (  # noqa: E402
    OKFBundle,
    build_okf_bundle,
    discover_corpus_inputs,
)


def _tree_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpora-root",
        type=Path,
        default=REPO_ROOT / "eval_harness/data/corpora",
    )
    parser.add_argument(
        "--existing-bundle",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/data/okf_bundles/wmp_all_v0_2",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "okf_trial_data/results/build_metrics.json",
    )
    args = parser.parse_args()
    sources = discover_corpus_inputs(args.corpora_root)
    existing_manifest = json.loads(
        (args.existing_bundle / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    source_bytes = sum(
        source.manifest_path.stat().st_size + source.chunks_path.stat().st_size
        for source in sources
    )
    with tempfile.TemporaryDirectory(prefix="okf-trial-rebuild-") as temp:
        destination = Path(temp) / "bundle"
        started = time.perf_counter()
        result = build_okf_bundle(
            sources,
            destination,
            build_date="2026-08-02",
            generated_at="2026-08-02T00:00:00Z",
        )
        build_seconds = time.perf_counter() - started
        load_started = time.perf_counter()
        rebuilt = OKFBundle.load(destination)
        rebuilt.verify_integrity()
        load_verify_seconds = time.perf_counter() - load_started
        rebuilt_bytes = _tree_bytes(destination)
        markdown_count = len(list(destination.rglob("*.md")))
        rebuilt_digest = result.bundle_content_sha256
    metrics = {
        "source_corpus_count": len(sources),
        "source_chunk_count": sum(item["concept_count"] for item in existing_manifest["sources"]),
        "source_manifest_and_jsonl_bytes": source_bytes,
        "bundle_bytes": rebuilt_bytes,
        "bundle_to_source_size_ratio": rebuilt_bytes / source_bytes,
        "concept_count": result.concept_count,
        "markdown_artifact_count": markdown_count,
        "build_seconds": build_seconds,
        "load_and_verify_seconds": load_verify_seconds,
        "existing_bundle_content_sha256": existing_manifest["bundle_content_sha256"],
        "rebuilt_bundle_content_sha256": rebuilt_digest,
        "byte_deterministic_content_digest": (
            rebuilt_digest == existing_manifest["bundle_content_sha256"]
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
