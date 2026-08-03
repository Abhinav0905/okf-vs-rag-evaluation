"""Offline tests for the diagnostic retrieval baselines.

These arms carry the paper's central attribution claim - that the apparent OKF
retrieval advantage is a lexical effect rather than a format effect - so their
ranking, corpus isolation, and budget accounting are tested directly. Nothing
here touches the network or the database.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from okf_trial_data.fair_baselines import (
    AdjacencyWrapper,
    BM25Index,
    BM25RawRetriever,
    RawChunk,
    RRFFusionRetriever,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _chunk(chunk_id: str, text: str, *, corpus: str = "PGE", page: int | None = None) -> RawChunk:
    return RawChunk(
        chunk_id=chunk_id,
        corpus=corpus,
        text=text,
        page_number=page,
        section=None,
        document_name="doc.pdf",
        metadata={},
    )


@pytest.fixture
def corpus() -> list[RawChunk]:
    return [
        _chunk("PGE-00000", "covered conductor installation targets for 2026", page=1),
        _chunk("PGE-00001", "vegetation management inspection cycles", page=2),
        _chunk("PGE-00002", "undergrounding of electric distribution lines", page=3),
        _chunk("PGE-00003", "public safety power shutoff decision criteria", page=4),
        _chunk("SCE-00000", "covered conductor installation targets for 2026", corpus="SCE", page=9),
    ]


class TestSourceOrder:
    def test_parses_ordinal_from_identifier(self) -> None:
        assert _chunk("PGE-00042", "x").source_order == 42

    def test_non_numeric_suffix_is_sentinel(self) -> None:
        assert _chunk("PGE-alpha", "x").source_order == -1


class TestBM25Index:
    def test_scores_only_matching_documents(self) -> None:
        index = BM25Index({"a": "covered conductor", "b": "vegetation management"})
        scores = index.score("conductor", ["a", "b"])
        assert set(scores) == {"a"}
        assert scores["a"] > 0

    def test_empty_query_returns_nothing(self) -> None:
        index = BM25Index({"a": "covered conductor"})
        assert index.score("   ", ["a"]) == {}

    def test_stopword_only_query_still_matches(self) -> None:
        # _query_terms falls back to raw tokens when every token is a stopword,
        # so a query of pure stopwords must not silently score nothing.
        index = BM25Index({"a": "the of and"})
        assert index.score("the of", ["a"])


class TestBM25RawRetriever:
    def test_ranks_the_lexically_closest_passage_first(self, corpus) -> None:
        retriever = BM25RawRetriever(corpus)
        hits = retriever.dense_search("undergrounding distribution lines", "PGE", top_k=3)
        assert hits[0]["chunk_id"] == "PGE-00002"

    def test_respects_corpus_isolation(self, corpus) -> None:
        retriever = BM25RawRetriever(corpus)
        hits = retriever.dense_search("covered conductor targets", "PGE", top_k=10)
        assert {hit["chunk_id"] for hit in hits}.isdisjoint({"SCE-00000"})
        assert all(hit["corpus"] == "PGE" for hit in hits)

    def test_honours_top_k(self, corpus) -> None:
        retriever = BM25RawRetriever(corpus)
        assert len(retriever.dense_search("targets inspection lines criteria", "PGE", top_k=2)) == 2

    def test_unknown_corpus_returns_nothing(self, corpus) -> None:
        assert BM25RawRetriever(corpus).dense_search("conductor", "NOPE", top_k=5) == []

    def test_emits_page_metadata_for_scoring(self, corpus) -> None:
        hit = BM25RawRetriever(corpus).dense_search("undergrounding", "PGE", top_k=1)[0]
        assert hit["page_number"] == 3
        assert hit["metadata"]["pages"] == [3]
        assert hit["metadata"]["retrieval_mode"] == "bm25_raw"


class TestAdjacencyWrapper:
    def test_reserves_half_the_budget_and_adds_neighbours(self, corpus) -> None:
        base = BM25RawRetriever(corpus)
        wrapped = AdjacencyWrapper(base, seed_fraction=0.5)
        ranked = wrapped.ranked("undergrounding distribution lines", "PGE", 4)
        returned = {chunk_id for chunk_id, _ in ranked}
        # PGE-00002 is the lexical match; its ordinal neighbours must appear.
        assert "PGE-00002" in returned
        assert {"PGE-00001", "PGE-00003"} & returned

    def test_neighbours_score_below_their_seed(self, corpus) -> None:
        wrapped = AdjacencyWrapper(BM25RawRetriever(corpus), seed_fraction=0.5, link_decay=0.35)
        scores = dict(wrapped.ranked("undergrounding distribution lines", "PGE", 4))
        assert scores["PGE-00002"] > scores.get("PGE-00001", 0.0)

    def test_does_not_cross_corpus_boundaries(self, corpus) -> None:
        wrapped = AdjacencyWrapper(BM25RawRetriever(corpus), seed_fraction=0.5)
        hits = wrapped.dense_search("covered conductor targets", "PGE", top_k=6)
        assert all(hit["corpus"] == "PGE" for hit in hits)

    def test_never_exceeds_top_k(self, corpus) -> None:
        wrapped = AdjacencyWrapper(BM25RawRetriever(corpus), seed_fraction=0.5)
        assert len(wrapped.ranked("targets inspection lines criteria", "PGE", 3)) <= 3


class TestRRFFusion:
    def test_requires_two_arms(self, corpus) -> None:
        with pytest.raises(ValueError):
            RRFFusionRetriever([BM25RawRetriever(corpus)])

    def test_promotes_a_document_ranked_highly_by_either_arm(self, corpus) -> None:
        base = BM25RawRetriever(corpus)

        class Stub:
            """Ranks one fixed document first, ignoring the query."""

            chunks = {chunk.chunk_id: chunk for chunk in corpus}
            mode = "stub"

            def ranked(self, query, corpus_name, top_k):
                return [("PGE-00003", 1.0)]

        fused = RRFFusionRetriever([base, Stub()])
        returned = {cid for cid, _ in fused.ranked("undergrounding lines", "PGE", 5)}
        assert {"PGE-00002", "PGE-00003"} <= returned


class TestPageNDCG:
    """`page_ndcg` lives in the diagnostics script, which is not an importable package."""

    @staticmethod
    def _load():
        path = REPO_ROOT / "okf_trial_data/scripts/run_retrieval_diagnostics.py"
        spec = importlib.util.spec_from_file_location("_diag", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["_diag"] = module
        spec.loader.exec_module(module)
        return module.page_ndcg

    @staticmethod
    def _hit(page: int) -> dict:
        return {"page_number": page, "metadata": {"pages": [page]}}

    def test_perfect_ranking_scores_one(self) -> None:
        ndcg = self._load()
        assert ndcg([self._hit(5), self._hit(6)], [5, 6]) == pytest.approx(1.0)

    def test_no_relevant_page_scores_zero(self) -> None:
        ndcg = self._load()
        assert ndcg([self._hit(1), self._hit(2)], [9]) == 0.0

    def test_no_expected_pages_scores_zero(self) -> None:
        ndcg = self._load()
        assert ndcg([self._hit(1)], []) == 0.0

    def test_later_hit_scores_lower(self) -> None:
        ndcg = self._load()
        early = ndcg([self._hit(5), self._hit(1)], [5])
        late = ndcg([self._hit(1), self._hit(5)], [5])
        assert early > late

    def test_duplicate_pages_are_not_double_credited(self) -> None:
        ndcg = self._load()
        # Two chunks from the same expected page must not outscore a perfect
        # ranking, or an arm could inflate nDCG by returning one page repeatedly.
        assert ndcg([self._hit(5), self._hit(5)], [5]) == pytest.approx(1.0)
