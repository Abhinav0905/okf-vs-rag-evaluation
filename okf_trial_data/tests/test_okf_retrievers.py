from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from okf_trial_data.okf_bundle import CorpusInput, OKFBundle, build_okf_bundle
from okf_trial_data.okf_retrievers import (
    ExistingDenseRetrieverAdapter,
    OKFHybridRetriever,
    OKFNativeRetriever,
    VectorSeed,
)


def _source(root: Path, corpus: str, texts: list[str]) -> CorpusInput:
    directory = root / corpus.lower()
    directory.mkdir(parents=True)
    manifest = {
        "corpus": corpus,
        "corpus_version": f"{corpus.lower()}_20260802",
        "source_pdf": f"{corpus.lower()}-plan.pdf",
        "source_sha256": ("a" if corpus == "A" else "b") * 64,
        "n_chunks": len(texts),
    }
    chunks = [
        {
            "chunk_id": f"{corpus}-{index:05d}",
            "corpus": corpus,
            "text": text,
            "page_number": index + 1,
            "section": "Operations" if index == 1 else None,
            "document_name": f"{corpus.lower()}-plan.pdf",
            "metadata": {"pages": [index + 1]},
        }
        for index, text in enumerate(texts)
    ]
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "chunks.jsonl").write_text(
        "".join(json.dumps(chunk) + "\n" for chunk in chunks), encoding="utf-8"
    )
    return CorpusInput.from_directory(directory)


def _bundle(tmp_path: Path) -> OKFBundle:
    sources = [
        _source(
            tmp_path,
            "A",
            [
                "Weather stations measure wind speed and humidity.",
                "Covered conductors are installed on high-risk circuits.",
                "Annual inspections identify damaged poles and equipment.",
                "Vegetation crews maintain clearance around power lines.",
            ],
        ),
        _source(
            tmp_path,
            "B",
            ["Covered conductors occur in another tenant's plan."],
        ),
    ]
    result = build_okf_bundle(
        sources, tmp_path / "bundle", build_date="2026-08-02"
    )
    return OKFBundle.load(result.bundle_dir)


def test_native_retrieval_scores_evidence_frontmatter_and_links(tmp_path: Path):
    bundle = _bundle(tmp_path)
    retriever = OKFNativeRetriever(bundle, link_decay=0.5)

    hits = retriever.search(
        "Which high-risk circuits use covered conductors?",
        corpus="A",
        top_k=3,
        seed_k=1,
        max_link_depth=1,
    )

    assert hits[0].source_chunk_id == "A-00001"
    assert hits[0].retrieval_mode == "okf_native"
    assert hits[0].lexical_score > 0
    assert {hit.source_chunk_id for hit in hits[1:]} == {"A-00000", "A-00002"}
    assert all(hit.link_depth == 1 for hit in hits[1:])
    assert all(hit.seed_concept_ids == ("concepts/a/a-00001",) for hit in hits)
    assert all(hit.corpus == "A" for hit in hits)
    assert "another tenant" not in " ".join(hit.text for hit in hits)

    operations = retriever.search(
        "covered conductors",
        corpus="A",
        metadata_filters={"section": "Operations", "tags": "corpus-a"},
        max_link_depth=0,
    )
    assert [hit.source_chunk_id for hit in operations] == ["A-00001"]
    assert operations[0].as_chunk_dict()["metadata"]["okf_concept_id"] == (
        "concepts/a/a-00001"
    )


class FakeVectorProvider:
    def search(self, query: str, *, corpus: str, top_k: int):
        assert corpus == "A"
        assert top_k == 1
        return [VectorSeed("A-00002", 0.9), VectorSeed("B-00000", 0.99)]


def test_hybrid_uses_vector_seeds_then_expands_links_without_tenant_leakage(tmp_path: Path):
    retriever = OKFHybridRetriever(_bundle(tmp_path), FakeVectorProvider(), link_decay=0.5)
    hits = retriever.search(
        "inspection program",
        corpus="A",
        top_k=3,
        seed_k=1,
        max_link_depth=1,
    )

    assert hits[0].source_chunk_id == "A-00002"
    assert hits[0].vector_score == 0.9
    assert hits[0].score == 0.9
    assert {hit.source_chunk_id for hit in hits[1:]} == {"A-00001", "A-00003"}
    assert all(hit.link_score == 0.45 for hit in hits[1:])
    assert all(hit.retrieval_mode == "okf_hybrid" for hit in hits)
    assert all(hit.corpus == "A" for hit in hits)


class DefaultSeedProvider:
    def __init__(self):
        self.requested_top_k = None

    def search(self, query: str, *, corpus: str, top_k: int):
        self.requested_top_k = top_k
        return [VectorSeed("A-00001", 0.8), VectorSeed("A-00003", 0.7)][:top_k]


def test_hybrid_default_reserves_result_capacity_for_links(tmp_path: Path):
    provider = DefaultSeedProvider()
    retriever = OKFHybridRetriever(_bundle(tmp_path), provider, link_decay=0.5)
    hits = retriever.search("grid work", corpus="A", top_k=4, max_link_depth=1)

    assert provider.requested_top_k == 2
    assert {hit.source_chunk_id for hit in hits} == {
        "A-00000",
        "A-00001",
        "A-00002",
        "A-00003",
    }
    assert sum(hit.link_depth == 0 for hit in hits) == 2


@dataclass
class DenseResult:
    chunk_id: str
    score: float


class FakeDenseRetriever:
    def dense_search(self, query: str, corpus: str, top_k: int):
        return [DenseResult(f"{corpus}-00000", 0.75), {"chunk_id": "A-00001", "score": 0.5}]


def test_existing_dense_retriever_adapter_and_convenience_constructor(tmp_path: Path):
    dense = FakeDenseRetriever()
    adapter = ExistingDenseRetrieverAdapter(dense)
    assert adapter.search("wind", corpus="A", top_k=2) == [
        VectorSeed("A-00000", 0.75),
        VectorSeed("A-00001", 0.5),
    ]

    retriever = OKFHybridRetriever.from_dense_retriever(
        _bundle(tmp_path), dense, link_decay=0.25
    )
    hits = retriever.search(
        "wind", corpus="A", top_k=3, seed_k=2, max_link_depth=1
    )
    assert [hit.source_chunk_id for hit in hits[:2]] == ["A-00000", "A-00001"]
    assert all(hit.link_depth == 0 for hit in hits[:2])
