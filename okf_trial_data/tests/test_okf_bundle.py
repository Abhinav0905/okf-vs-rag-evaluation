from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from okf_trial_data.okf_bundle import (
    OKF_SPEC_COMMIT,
    OKFBundle,
    SourceValidationError,
    build_okf_bundle,
)


SOURCE_SHA = "a" * 64


def _write_source(
    root: Path,
    *,
    corpus: str = "TEST",
    chunks: list[dict] | None = None,
) -> Path:
    root.mkdir(parents=True)
    if chunks is None:
        chunks = [
            {
                "chunk_id": f"{corpus}-00000",
                "corpus": corpus,
                "text": "Covered conductors reduce ignition risk.",
                "page_number": 10,
                "section": "Grid hardening",
                "document_name": "plan.pdf",
                "metadata": {"pages": [10]},
            },
            {
                "chunk_id": f"{corpus}-00001",
                "corpus": corpus,
                "text": "Inspection targets are reported annually.\nSecond line is preserved.\n",
                "page_number": 11,
                "section": None,
                "document_name": "plan.pdf",
                "metadata": {"pages": [11, 12]},
            },
        ]
    manifest = {
        "corpus": corpus,
        "corpus_version": f"{corpus.lower()}_r0_20260719",
        "source_pdf": "plan.pdf",
        "source_sha256": SOURCE_SHA,
        "n_chunks": len(chunks),
        "embed_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embed_dim": 384,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (root / "chunks.jsonl").write_text(
        "".join(json.dumps(chunk, separators=(",", ":")) + "\n" for chunk in chunks),
        encoding="utf-8",
    )
    return root


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_builds_conformant_provenance_preserving_bundle_deterministically(tmp_path: Path):
    source = _write_source(tmp_path / "source")
    first = build_okf_bundle(
        [source],
        tmp_path / "bundle-a",
        build_date="2026-08-02",
        generated_at="2026-08-02T09:30:00-07:00",
    )
    second = build_okf_bundle(
        [source],
        tmp_path / "bundle-b",
        build_date="2026-08-02",
        generated_at="2026-08-02T16:30:00Z",
    )

    assert first.concept_count == 2
    assert first.corpus_count == 1
    assert first.bundle_content_sha256 == second.bundle_content_sha256
    assert _tree_digest(first.bundle_dir) == _tree_digest(second.bundle_dir)

    root_index = (first.bundle_dir / "index.md").read_text(encoding="utf-8")
    assert 'okf_version: "0.2"' in root_index
    assert OKF_SPEC_COMMIT in root_index
    assert "## 2026-08-02" in (first.bundle_dir / "log.md").read_text()

    concept_path = first.bundle_dir / "concepts" / "test" / "test-00001.md"
    document = concept_path.read_text(encoding="utf-8")
    yaml_text = document.split("---", 2)[1]
    frontmatter = yaml.safe_load(yaml_text)
    assert frontmatter["type"] == "Source Passage"
    assert frontmatter["corpus"] == "TEST"
    assert frontmatter["source_chunk_id"] == "TEST-00001"
    assert frontmatter["source_order"] == 1
    assert frontmatter["page_number"] == 11
    assert frontmatter["page_numbers"] == [11, 12]
    assert frontmatter["document_name"] == "plan.pdf"
    assert frontmatter["source_sha256"] == SOURCE_SHA
    assert frontmatter["sources"][0]["resource"].startswith(f"urn:sha256:{SOURCE_SHA}")
    assert frontmatter["generated"] == {
        "by": "process:okf-trial-bundle-v1",
        "at": "2026-08-02T16:30:00Z",
    }
    assert "[source passage](/concepts/test/test-00000.md)" in document

    bundle = OKFBundle.load(first.bundle_dir)
    bundle.verify_integrity()
    assert len(bundle) == 2
    concept = bundle.concept_for_source_chunk("TEST", "TEST-00001")
    assert concept is not None
    assert concept.evidence == "Inspection targets are reported annually.\nSecond line is preserved.\n"
    assert concept.links == ("concepts/test/test-00000",)

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["okf_version"] == "0.2"
    assert manifest["concept_count"] == 2
    assert manifest["sources"][0]["source_sha256"] == SOURCE_SHA


def test_optional_generated_family_is_omitted_instead_of_using_wall_clock(tmp_path: Path):
    source = _write_source(tmp_path / "source")
    result = build_okf_bundle([source], tmp_path / "bundle", build_date="2026-08-02")
    document = (result.bundle_dir / "concepts" / "test" / "test-00000.md").read_text()
    frontmatter = yaml.safe_load(document.split("---", 2)[1])
    assert "generated" not in frontmatter
    assert json.loads(result.manifest_path.read_text())["generated_at"] is None


def test_rejects_evaluation_question_fields(tmp_path: Path):
    chunks = [
        {
            "chunk_id": "TEST-00000",
            "corpus": "TEST",
            "text": "Source evidence only.",
            "page_number": 1,
            "metadata": {"pages": [1]},
            "question": "This must never enter the OKF producer.",
        }
    ]
    source = _write_source(tmp_path / "source", chunks=chunks)
    with pytest.raises(SourceValidationError, match="evaluation fields are forbidden"):
        build_okf_bundle([source], tmp_path / "bundle", build_date="2026-08-02")


def test_rejects_manifest_count_mismatch_and_requires_explicit_overwrite(tmp_path: Path):
    source = _write_source(tmp_path / "source")
    destination = tmp_path / "bundle"
    build_okf_bundle([source], destination, build_date="2026-08-02")
    with pytest.raises(FileExistsError):
        build_okf_bundle([source], destination, build_date="2026-08-02")

    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["n_chunks"] = 99
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SourceValidationError, match="n_chunks=99"):
        build_okf_bundle([source], tmp_path / "other", build_date="2026-08-02")
