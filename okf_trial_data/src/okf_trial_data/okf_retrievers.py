"""Question-time retrieval over an OKF v0.2 evidence bundle.

Two controlled retrieval treatments are provided:

``OKFNativeRetriever``
    Weighted BM25 over evidence plus selected frontmatter, followed by local
    OKF link traversal.

``OKFHybridRetriever``
    Dense/vector seeds supplied by the existing evaluation retriever, mapped
    back to OKF concepts by immutable source chunk ID, followed by the same
    deterministic link traversal.

Neither implementation calls an LLM.  Both retain the exact source passage and
return an eval-harness-shaped dictionary through ``OKFRetrievalHit.as_chunk_dict``.
"""

from __future__ import annotations

import math
import re
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence

from .okf_bundle import OKFBundle, OKFConcept


_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
    }
)


@dataclass(frozen=True)
class OKFRetrievalHit:
    """One evidence passage selected from the OKF concept graph."""

    concept_id: str
    source_chunk_id: str
    corpus: str
    text: str
    score: float
    retrieval_mode: str
    lexical_score: float = 0.0
    vector_score: float = 0.0
    link_score: float = 0.0
    link_depth: int = 0
    seed_concept_ids: tuple[str, ...] = ()
    frontmatter: Mapping[str, Any] | None = None

    @property
    def page_number(self) -> int | None:
        if self.frontmatter is None:
            return None
        value = self.frontmatter.get("page_number")
        return value if isinstance(value, int) else None

    def as_chunk_dict(self) -> dict[str, Any]:
        """Return the field shape consumed by the existing RAG systems."""

        metadata = dict(self.frontmatter or {})
        metadata.update(
            {
                "okf_concept_id": self.concept_id,
                "okf_retrieval_mode": self.retrieval_mode,
                "okf_link_depth": self.link_depth,
                "okf_seed_concept_ids": list(self.seed_concept_ids),
                "okf_lexical_score": self.lexical_score,
                "okf_vector_score": self.vector_score,
                "okf_link_score": self.link_score,
            }
        )
        return {
            "chunk_id": self.source_chunk_id,
            "corpus": self.corpus,
            "text": self.text,
            "score": self.score,
            "rerank_score": None,
            "page_number": self.page_number,
            "section": metadata.get("section"),
            "document_name": metadata.get("document_name"),
            "metadata": metadata,
        }


@dataclass(frozen=True)
class VectorSeed:
    """A vector backend's source-chunk identifier and similarity score."""

    identifier: str
    score: float


class VectorSeedProvider(Protocol):
    """Minimal adapter surface required by :class:`OKFHybridRetriever`."""

    def search(self, query: str, *, corpus: str, top_k: int) -> Sequence[VectorSeed]:
        ...


class ExistingDenseRetrieverAdapter:
    """Adapt the eval harness's ``dense_search`` API without importing it.

    The wrapped backend may return Pydantic objects, dataclasses, or mappings.
    Its identifiers must be original ``chunk_id`` values, which the bundle
    maps to OKF concepts within the requested corpus.
    """

    def __init__(self, dense_retriever: Any, *, score_attribute: str = "score") -> None:
        if not hasattr(dense_retriever, "dense_search"):
            raise TypeError("dense_retriever must expose dense_search(query, corpus, top_k)")
        self.dense_retriever = dense_retriever
        self.score_attribute = score_attribute

    def search(self, query: str, *, corpus: str, top_k: int) -> Sequence[VectorSeed]:
        raw = self.dense_retriever.dense_search(query, corpus=corpus, top_k=top_k)
        seeds: list[VectorSeed] = []
        for item in raw:
            identifier = _field(item, "chunk_id")
            if identifier is None:
                identifier = _field(item, "source_chunk_id")
            score = _field(item, self.score_attribute)
            if identifier is None or score is None:
                continue
            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numeric_score):
                continue
            seeds.append(VectorSeed(str(identifier), numeric_score))
        return seeds


class OKFNativeRetriever:
    """Weighted BM25 over OKF bodies/frontmatter with deterministic traversal."""

    def __init__(
        self,
        bundle: OKFBundle | str | Path,
        *,
        k1: float = 1.2,
        b: float = 0.75,
        link_decay: float = 0.35,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between zero and one")
        if not 0 <= link_decay <= 1:
            raise ValueError("link_decay must be between zero and one")
        self.bundle = bundle if isinstance(bundle, OKFBundle) else OKFBundle.load(bundle)
        self.k1 = float(k1)
        self.b = float(b)
        self.link_decay = float(link_decay)
        self._term_frequencies: dict[str, Counter[str]] = {}
        self._document_lengths: dict[str, float] = {}
        for concept in self.bundle:
            frequencies = _weighted_terms(concept)
            self._term_frequencies[concept.concept_id] = frequencies
            self._document_lengths[concept.concept_id] = sum(frequencies.values())

    def search(
        self,
        query: str,
        *,
        corpus: str | None = None,
        top_k: int = 20,
        seed_k: int | None = None,
        max_link_depth: int = 1,
        bidirectional_links: bool = True,
        metadata_filters: Mapping[str, Any] | None = None,
        include_deprecated: bool = False,
    ) -> list[OKFRetrievalHit]:
        """Retrieve lexical seeds and expand their OKF graph neighborhood."""

        _validate_search_limits(top_k, seed_k, max_link_depth)
        if not isinstance(query, str) or not query.strip():
            return []
        eligible = _eligible_concepts(
            self.bundle,
            corpus=corpus,
            metadata_filters=metadata_filters,
            include_deprecated=include_deprecated,
        )
        if not eligible:
            return []
        query_terms = _query_terms(query)
        if not query_terms:
            return []
        lexical = self._bm25(query_terms, eligible)
        lexical = {concept_id: score for concept_id, score in lexical.items() if score > 0}
        if not lexical:
            return []
        requested_seeds = (
            seed_k
            if seed_k is not None
            else _default_seed_count(top_k, max_link_depth=max_link_depth)
        )
        seeds = sorted(lexical, key=lambda key: (-lexical[key], key))[:requested_seeds]
        link_scores, link_depths, origins = _expand_links(
            self.bundle,
            [(concept_id, lexical[concept_id]) for concept_id in seeds],
            eligible_ids=set(eligible),
            max_depth=max_link_depth,
            link_decay=self.link_decay,
            bidirectional=bidirectional_links,
        )
        # Only the declared lexical seeds and their graph neighborhood enter
        # the candidate pool.  Including every lexical match here would fill
        # ``top_k`` with lexical results and make link traversal a no-op.
        candidate_ids = set(seeds).union(link_scores)
        hits = []
        for concept_id in candidate_ids:
            concept = eligible.get(concept_id)
            if concept is None:
                continue
            lexical_score = lexical.get(concept_id, 0.0)
            link_score = link_scores.get(concept_id, 0.0)
            score = max(lexical_score, link_score)
            hits.append(
                _hit(
                    concept,
                    score=score,
                    retrieval_mode="okf_native",
                    lexical_score=lexical_score,
                    link_score=link_score,
                    link_depth=link_depths.get(concept_id, 0),
                    seed_concept_ids=origins.get(concept_id, ()),
                )
            )
        return sorted(hits, key=_hit_sort_key)[:top_k]

    def _bm25(
        self, query_terms: Sequence[str], eligible: Mapping[str, OKFConcept]
    ) -> dict[str, float]:
        n_documents = len(eligible)
        avg_length = (
            sum(self._document_lengths[concept_id] for concept_id in eligible) / n_documents
        )
        if avg_length <= 0:
            avg_length = 1.0
        document_frequency = {
            term: sum(
                1 for concept_id in eligible if self._term_frequencies[concept_id].get(term, 0) > 0
            )
            for term in set(query_terms)
        }
        scores: dict[str, float] = {}
        query_counts = Counter(query_terms)
        for concept_id in eligible:
            frequencies = self._term_frequencies[concept_id]
            length = self._document_lengths[concept_id]
            score = 0.0
            for term, query_frequency in query_counts.items():
                tf = float(frequencies.get(term, 0.0))
                if tf <= 0:
                    continue
                df = document_frequency[term]
                idf = math.log(1.0 + (n_documents - df + 0.5) / (df + 0.5))
                denominator = tf + self.k1 * (
                    1.0 - self.b + self.b * length / avg_length
                )
                score += query_frequency * idf * (tf * (self.k1 + 1.0)) / denominator
            scores[concept_id] = score
        return scores


class OKFHybridRetriever:
    """Vector-seed retrieval followed by OKF link expansion."""

    def __init__(
        self,
        bundle: OKFBundle | str | Path,
        vector_seed_provider: VectorSeedProvider,
        *,
        link_decay: float = 0.35,
    ) -> None:
        if not hasattr(vector_seed_provider, "search"):
            raise TypeError("vector_seed_provider must expose search(query, corpus=..., top_k=...)")
        if not 0 <= link_decay <= 1:
            raise ValueError("link_decay must be between zero and one")
        self.bundle = bundle if isinstance(bundle, OKFBundle) else OKFBundle.load(bundle)
        self.vector_seed_provider = vector_seed_provider
        self.link_decay = float(link_decay)

    @classmethod
    def from_dense_retriever(
        cls,
        bundle: OKFBundle | str | Path,
        dense_retriever: Any,
        *,
        link_decay: float = 0.35,
        score_attribute: str = "score",
    ) -> "OKFHybridRetriever":
        """Wrap an existing pgvector/FAISS/Bedrock-KB dense retriever."""

        return cls(
            bundle,
            ExistingDenseRetrieverAdapter(
                dense_retriever, score_attribute=score_attribute
            ),
            link_decay=link_decay,
        )

    def search(
        self,
        query: str,
        *,
        corpus: str,
        top_k: int = 20,
        seed_k: int | None = None,
        max_link_depth: int = 1,
        bidirectional_links: bool = True,
        metadata_filters: Mapping[str, Any] | None = None,
        include_deprecated: bool = False,
    ) -> list[OKFRetrievalHit]:
        """Retrieve dense seeds within one corpus and traverse OKF links.

        ``corpus`` is mandatory so this layer preserves the existing
        retriever's tenant-isolation contract.
        """

        _validate_search_limits(top_k, seed_k, max_link_depth)
        if not isinstance(query, str) or not query.strip():
            return []
        if not isinstance(corpus, str) or not corpus.strip():
            raise ValueError("corpus is required for hybrid retrieval")
        eligible = _eligible_concepts(
            self.bundle,
            corpus=corpus,
            metadata_filters=metadata_filters,
            include_deprecated=include_deprecated,
        )
        requested_seeds = (
            seed_k
            if seed_k is not None
            else _default_seed_count(top_k, max_link_depth=max_link_depth)
        )
        raw_seeds = self.vector_seed_provider.search(
            query, corpus=corpus, top_k=requested_seeds
        )
        vector_scores: dict[str, float] = {}
        for seed in raw_seeds:
            if not math.isfinite(float(seed.score)):
                continue
            concept = self.bundle.concept_for_source_chunk(corpus, str(seed.identifier))
            if concept is None and str(seed.identifier) in self.bundle.concepts:
                concept = self.bundle.get(str(seed.identifier))
            if concept is None or concept.concept_id not in eligible:
                continue
            previous = vector_scores.get(concept.concept_id, -math.inf)
            vector_scores[concept.concept_id] = max(previous, float(seed.score))
        if not vector_scores:
            return []
        ordered_seeds = sorted(vector_scores, key=lambda key: (-vector_scores[key], key))[
            :requested_seeds
        ]
        link_scores, link_depths, origins = _expand_links(
            self.bundle,
            [(concept_id, max(0.0, vector_scores[concept_id])) for concept_id in ordered_seeds],
            eligible_ids=set(eligible),
            max_depth=max_link_depth,
            link_decay=self.link_decay,
            bidirectional=bidirectional_links,
        )
        candidate_ids = set(vector_scores).union(link_scores)
        hits = []
        for concept_id in candidate_ids:
            concept = eligible.get(concept_id)
            if concept is None:
                continue
            vector_score = vector_scores.get(concept_id, 0.0)
            link_score = link_scores.get(concept_id, 0.0)
            # Direct seeds retain the backend's similarity scale (including a
            # possible negative cosine); graph-only hits use the decayed,
            # non-negative traversal score.
            final_score = (
                vector_score if concept_id in vector_scores else link_score
            )
            hits.append(
                _hit(
                    concept,
                    score=final_score,
                    retrieval_mode="okf_hybrid",
                    vector_score=vector_score,
                    link_score=link_score,
                    link_depth=link_depths.get(concept_id, 0),
                    seed_concept_ids=origins.get(concept_id, ()),
                )
            )
        return sorted(hits, key=_hit_sort_key)[:top_k]


def _eligible_concepts(
    bundle: OKFBundle,
    *,
    corpus: str | None,
    metadata_filters: Mapping[str, Any] | None,
    include_deprecated: bool,
) -> dict[str, OKFConcept]:
    result: dict[str, OKFConcept] = {}
    for concept in bundle:
        metadata = concept.frontmatter
        if corpus is not None and str(metadata.get("corpus", "")) != str(corpus):
            continue
        if not include_deprecated and str(metadata.get("status", "stable")) == "deprecated":
            continue
        if metadata_filters and not all(
            _metadata_matches(metadata, key, expected)
            for key, expected in metadata_filters.items()
        ):
            continue
        result[concept.concept_id] = concept
    return result


def _metadata_matches(metadata: Mapping[str, Any], dotted_key: str, expected: Any) -> bool:
    actual: Any = metadata
    for part in dotted_key.split("."):
        if not isinstance(actual, Mapping) or part not in actual:
            return False
        actual = actual[part]
    if isinstance(actual, (list, tuple, set, frozenset)):
        if isinstance(expected, (list, tuple, set, frozenset)):
            return set(expected).issubset(set(actual))
        return expected in actual
    if isinstance(expected, (list, tuple, set, frozenset)):
        return actual in expected
    return actual == expected


def _weighted_terms(concept: OKFConcept) -> Counter[str]:
    fields: tuple[tuple[Any, float], ...] = (
        (concept.evidence, 1.0),
        (concept.frontmatter.get("title", ""), 3.0),
        (concept.frontmatter.get("description", ""), 2.0),
        (concept.frontmatter.get("type", ""), 1.0),
        (concept.frontmatter.get("section", ""), 1.5),
        (" ".join(str(tag) for tag in concept.frontmatter.get("tags", [])), 2.5),
    )
    frequencies: Counter[str] = Counter()
    for value, weight in fields:
        for token in _tokens(str(value)):
            frequencies[token] += weight
    return frequencies


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())


def _query_terms(query: str) -> list[str]:
    tokens = _tokens(query)
    informative = [token for token in tokens if token not in _STOPWORDS]
    return informative or tokens


def _expand_links(
    bundle: OKFBundle,
    seeds: Sequence[tuple[str, float]],
    *,
    eligible_ids: set[str],
    max_depth: int,
    link_decay: float,
    bidirectional: bool,
) -> tuple[dict[str, float], dict[str, int], dict[str, tuple[str, ...]]]:
    seed_ids = {concept_id for concept_id, _ in seeds}
    link_scores: dict[str, float] = {}
    depths: dict[str, int] = {concept_id: 0 for concept_id, _ in seeds}
    origin_sets: dict[str, set[str]] = {
        concept_id: {concept_id} for concept_id, _ in seeds
    }
    if max_depth == 0 or link_decay == 0:
        return link_scores, depths, {
            concept_id: tuple(sorted(origins)) for concept_id, origins in origin_sets.items()
        }
    for seed_id, seed_score in seeds:
        queue: deque[tuple[str, int]] = deque([(seed_id, 0)])
        visited = {seed_id}
        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor_id in bundle.neighbors(current_id, bidirectional=bidirectional):
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                # A directly retrieved concept remains a depth-zero seed.  It
                # must not be relabelled or score-inflated merely because a
                # neighboring seed also links to it.
                if neighbor_id in seed_ids:
                    continue
                next_depth = depth + 1
                if neighbor_id in eligible_ids:
                    contribution = max(0.0, seed_score) * (link_decay**next_depth)
                    if contribution > link_scores.get(neighbor_id, -math.inf):
                        link_scores[neighbor_id] = contribution
                        depths[neighbor_id] = next_depth
                        origin_sets[neighbor_id] = {seed_id}
                    elif math.isclose(
                        contribution, link_scores.get(neighbor_id, -math.inf), rel_tol=1e-12
                    ):
                        origin_sets.setdefault(neighbor_id, set()).add(seed_id)
                    queue.append((neighbor_id, next_depth))
    return link_scores, depths, {
        concept_id: tuple(sorted(origins)) for concept_id, origins in origin_sets.items()
    }


def _hit(
    concept: OKFConcept,
    *,
    score: float,
    retrieval_mode: str,
    lexical_score: float = 0.0,
    vector_score: float = 0.0,
    link_score: float = 0.0,
    link_depth: int = 0,
    seed_concept_ids: Iterable[str] = (),
) -> OKFRetrievalHit:
    return OKFRetrievalHit(
        concept_id=concept.concept_id,
        source_chunk_id=concept.source_chunk_id,
        corpus=concept.corpus,
        text=concept.evidence,
        score=float(score),
        retrieval_mode=retrieval_mode,
        lexical_score=float(lexical_score),
        vector_score=float(vector_score),
        link_score=float(link_score),
        link_depth=int(link_depth),
        seed_concept_ids=tuple(seed_concept_ids),
        frontmatter=concept.frontmatter,
    )


def _hit_sort_key(hit: OKFRetrievalHit) -> tuple[float, int, str]:
    return (-hit.score, hit.link_depth, hit.concept_id)


def _validate_search_limits(top_k: int, seed_k: int | None, max_link_depth: int) -> None:
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if seed_k is not None and (
        not isinstance(seed_k, int) or isinstance(seed_k, bool) or seed_k < 1
    ):
        raise ValueError("seed_k must be a positive integer or null")
    if (
        not isinstance(max_link_depth, int)
        or isinstance(max_link_depth, bool)
        or max_link_depth < 0
    ):
        raise ValueError("max_link_depth must be a non-negative integer")


def _default_seed_count(top_k: int, *, max_link_depth: int) -> int:
    """Reserve half of a linked result set for deterministic graph expansion."""

    if max_link_depth == 0:
        return top_k
    return max(1, (top_k + 1) // 2)


def _field(item: Any, name: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(name)
    return getattr(item, name, None)
