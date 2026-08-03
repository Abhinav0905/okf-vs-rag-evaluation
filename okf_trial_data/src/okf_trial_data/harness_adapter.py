"""Adapters between the repository evaluation harness and OKF consumers.

The experiment reuses the existing five RAG implementations unchanged.  These
adapters vary only the retriever supplied to those systems, which is the
controlled treatment in the paired study.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .okf_retrievers import OKFHybridRetriever, OKFNativeRetriever


_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_DIFFICULTY = {"easy": 1, "medium": 2, "hard": 3, "unspecified": 2}


def load_benchmark(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    questions = payload.get("questions", [])
    if payload.get("counts", {}).get("total") != len(questions):
        raise ValueError("benchmark count does not match the questions array")
    if len({item["qid"] for item in questions}) != len(questions):
        raise ValueError("benchmark question IDs are not unique")
    return payload


def to_harness_question(item: Mapping[str, Any]) -> Any:
    """Convert a gold benchmark row to ``evaluation.questions.Question``."""

    from evaluation.questions import Question

    raw_difficulty = item.get("difficulty", "unspecified")
    if isinstance(raw_difficulty, int):
        difficulty = raw_difficulty
    else:
        difficulty = _DIFFICULTY.get(str(raw_difficulty).casefold(), 2)
    return Question(
        qid=str(item["qid"]),
        utility="Pacific Gas and Electric Company",
        utility_short="PGE",
        category=str(item.get("category", "unspecified")),
        difficulty=difficulty,
        topic=str(item.get("category", "wildfire mitigation")),
        topic2="",
        question=str(item["question"]),
        is_negative=not bool(item["answerable"]),
        is_table=bool(item.get("requires_table", False)),
        is_image=bool(item.get("requires_image", False)),
        corpora=[str(item.get("corpus", "PGE"))],
        primary_corpus=str(item.get("corpus", "PGE")),
    )


class _DelegatingHarnessRetriever:
    """Duck-typed harness retriever that shares ranking/context policy."""

    def __init__(self, base_retriever: Any) -> None:
        self.base_retriever = base_retriever
        self.config = base_retriever.config
        self.reranker = base_retriever.reranker

    def rerank(self, query: str, candidates: list[Any], **kwargs: Any) -> list[Any]:
        return self.base_retriever.rerank(query, candidates, **kwargs)

    def get_context(self, candidates: list[Any], token_budget: int = 2200):
        return self.base_retriever.get_context(candidates, token_budget)

    def close(self) -> None:
        # The base retriever is shared by the raw and OKF arms and is closed by
        # the experiment runner exactly once.
        return None


class OKFHybridHarnessRetriever(_DelegatingHarnessRetriever):
    """Expose vector-seed plus OKF-neighbor traversal as ``dense_search``."""

    def __init__(
        self,
        base_retriever: Any,
        bundle: str | Path,
        *,
        seed_fraction: float = 0.5,
        max_link_depth: int = 1,
        link_decay: float = 0.35,
        bidirectional_links: bool = True,
    ) -> None:
        super().__init__(base_retriever)
        if not 0 < seed_fraction <= 1:
            raise ValueError("seed_fraction must be in (0, 1]")
        self.seed_fraction = float(seed_fraction)
        self.max_link_depth = int(max_link_depth)
        self.bidirectional_links = bool(bidirectional_links)
        self.consumer = OKFHybridRetriever.from_dense_retriever(
            bundle, base_retriever, link_decay=link_decay
        )

    def dense_search(self, query: str, corpus: str, top_k: int = 20) -> list[Any]:
        from evaluation.models import RetrievedChunk

        seed_k = max(1, min(top_k, math.ceil(top_k * self.seed_fraction)))
        hits = self.consumer.search(
            query,
            corpus=corpus,
            top_k=top_k,
            seed_k=seed_k,
            max_link_depth=self.max_link_depth,
            bidirectional_links=self.bidirectional_links,
        )
        return [RetrievedChunk(**hit.as_chunk_dict()) for hit in hits]


class OKFNativeHarnessRetriever(_DelegatingHarnessRetriever):
    """Expose OKF weighted lexical search and traversal as ``dense_search``."""

    def __init__(
        self,
        base_retriever: Any,
        bundle: str | Path,
        *,
        seed_fraction: float = 0.5,
        max_link_depth: int = 1,
        link_decay: float = 0.35,
        bidirectional_links: bool = True,
    ) -> None:
        super().__init__(base_retriever)
        if not 0 < seed_fraction <= 1:
            raise ValueError("seed_fraction must be in (0, 1]")
        self.seed_fraction = float(seed_fraction)
        self.max_link_depth = int(max_link_depth)
        self.bidirectional_links = bool(bidirectional_links)
        self.consumer = OKFNativeRetriever(bundle, link_decay=link_decay)

    def dense_search(self, query: str, corpus: str, top_k: int = 20) -> list[Any]:
        from evaluation.models import RetrievedChunk

        seed_k = max(1, min(top_k, math.ceil(top_k * self.seed_fraction)))
        hits = self.consumer.search(
            query,
            corpus=corpus,
            top_k=top_k,
            seed_k=seed_k,
            max_link_depth=self.max_link_depth,
            bidirectional_links=self.bidirectional_links,
        )
        return [RetrievedChunk(**hit.as_chunk_dict()) for hit in hits]


@dataclass(frozen=True)
class CorpusEvidenceIndex:
    """Canonical source chunks used only for gold evaluation and citation lookup."""

    chunks_by_id: Mapping[str, Mapping[str, Any]]
    source_sha256: str

    @classmethod
    def load(cls, corpus_dir: str | Path) -> "CorpusEvidenceIndex":
        directory = Path(corpus_dir)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        chunks: dict[str, Mapping[str, Any]] = {}
        with (directory / "chunks.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    item = json.loads(line)
                    chunks[item["chunk_id"]] = item
        if len(chunks) != int(manifest["n_chunks"]):
            raise ValueError("corpus manifest/chunk count mismatch")
        return cls(chunks_by_id=chunks, source_sha256=manifest["source_sha256"])

    def resolve_citations(
        self, citation_ids: Iterable[str], *, max_chars_per_chunk: int = 3500
    ) -> list[dict[str, Any]]:
        resolved = []
        for chunk_id in citation_ids:
            chunk = self.chunks_by_id.get(str(chunk_id))
            if chunk is not None:
                resolved.append(self._evidence_record(chunk, max_chars_per_chunk))
        return resolved

    def gold_evidence(
        self,
        expected_pages: Sequence[int],
        reference_answer: str,
        *,
        max_chunks: int = 6,
        max_chars_per_chunk: int = 3500,
    ) -> list[dict[str, Any]]:
        """Select question-independent source chunks covering the annotated pages.

        Page membership defines eligibility.  Reference-token overlap only orders
        multiple chunks on the same page so the judge prompt remains bounded.
        """

        pages = {int(page) for page in expected_pages}
        if not pages:
            return []
        candidates = [
            chunk
            for chunk in self.chunks_by_id.values()
            if pages.intersection(_chunk_pages(chunk))
        ]
        ref_terms = set(_terms(reference_answer))

        def rank(chunk: Mapping[str, Any]) -> tuple[float, str]:
            body_terms = set(_terms(str(chunk["text"])))
            overlap = len(ref_terms.intersection(body_terms)) / max(1, len(ref_terms))
            return (-overlap, str(chunk["chunk_id"]))

        ordered = sorted(candidates, key=rank)
        chosen: list[Mapping[str, Any]] = []
        # First retain the best passage for every annotated page.
        for page in sorted(pages):
            for chunk in ordered:
                if page in _chunk_pages(chunk) and chunk not in chosen:
                    chosen.append(chunk)
                    break
        for chunk in ordered:
            if len(chosen) >= max_chunks:
                break
            if chunk not in chosen:
                chosen.append(chunk)
        return [
            self._evidence_record(chunk, max_chars_per_chunk)
            for chunk in chosen[:max_chunks]
        ]

    def _evidence_record(
        self, chunk: Mapping[str, Any], max_chars: int
    ) -> dict[str, Any]:
        return {
            "chunk_id": chunk["chunk_id"],
            "document_sha256": self.source_sha256,
            "pages": sorted(_chunk_pages(chunk)),
            "text": str(chunk["text"])[:max_chars],
        }


def retrieval_outcomes(
    chunks: Sequence[Any], expected_pages: Sequence[int]
) -> dict[str, Any]:
    """Deterministic page-based retrieval outcomes for one ranked list."""

    expected = {int(page) for page in expected_pages}
    ranked_pages = [_object_pages(chunk) for chunk in chunks]
    if expected:
        found = set().union(*ranked_pages) if ranked_pages else set()
        ranks = [
            rank
            for rank, pages in enumerate(ranked_pages, start=1)
            if pages.intersection(expected)
        ]
        page_recall = len(found.intersection(expected)) / len(expected)
        reciprocal_rank = 1.0 / min(ranks) if ranks else 0.0
        page_hit = bool(ranks)
    else:
        page_recall = None
        reciprocal_rank = None
        page_hit = None
    linked = sum(
        int((_object_metadata(chunk).get("okf_link_depth") or 0) > 0)
        for chunk in chunks
    )
    return {
        "page_hit": page_hit,
        "expected_page_recall": page_recall,
        "reciprocal_rank": reciprocal_rank,
        "retrieved_count": len(chunks),
        "linked_chunk_count": linked,
        "linked_chunk_fraction": linked / len(chunks) if chunks else 0.0,
    }


def _object_metadata(item: Any) -> Mapping[str, Any]:
    metadata = item.get("metadata", {}) if isinstance(item, Mapping) else getattr(item, "metadata", {})
    return metadata if isinstance(metadata, Mapping) else {}


def _object_pages(item: Any) -> set[int]:
    if isinstance(item, Mapping):
        page_number = item.get("page_number")
    else:
        page_number = getattr(item, "page_number", None)
    pages = set()
    if isinstance(page_number, int):
        pages.add(page_number)
    values = _object_metadata(item).get("page_numbers")
    if values is None:
        values = _object_metadata(item).get("pages", [])
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
        pages.update(value for value in values if isinstance(value, int))
    return pages


def _chunk_pages(chunk: Mapping[str, Any]) -> set[int]:
    pages = set()
    page = chunk.get("page_number")
    if isinstance(page, int):
        pages.add(page)
    metadata = chunk.get("metadata") or {}
    if isinstance(metadata, Mapping):
        pages.update(value for value in metadata.get("pages", []) if isinstance(value, int))
    return pages


def _terms(text: str) -> list[str]:
    return _WORD_RE.findall(text.casefold())
