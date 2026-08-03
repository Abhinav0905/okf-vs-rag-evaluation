"""Diagnostic retrieval baselines added after the confirmatory retrieval run.

Why these exist
---------------
The frozen confirmatory run compared three conditions: ``raw_vector`` (dense
``all-MiniLM-L6-v2`` over pgvector), ``okf_hybrid`` (the same dense seeds plus
one-hop OKF adjacency), and ``okf_native`` (weighted BM25 over OKF concept text
plus the same adjacency).  ``okf_native`` scored far above ``raw_vector``.

That contrast confounds three separate factors:

1. **Matching family** - BM25 is lexical, ``raw_vector`` is dense.
2. **Embedding capacity** - ``all-MiniLM-L6-v2`` truncates input at 256
   word-piece tokens. Measured over the 654 PGE passages, 80.9% exceed that
   limit (median 398 tokens), so the encoder receives a median of only 64.4% of
   each passage while BM25 indexes every token. See
   ``scripts/measure_embedding_truncation.py``.
3. **OKF itself** - concept serialization, frontmatter fields, and link
   traversal.

The arms below hold the corpus, questions, top-k and page-level scoring fixed
while varying one factor at a time, so the confound can be decomposed:

``BM25RawRetriever``
    BM25 over the unmodified pgvector chunk text.  No OKF involvement at all -
    no concept files, no frontmatter, no links.  Isolates factor 1.
``TitanDenseRetriever``
    Dense retrieval with ``amazon.titan-embed-text-v2:0`` (8192-token input
    window), so no passage is truncated.  Isolates factor 2.
``RRFFusionRetriever``
    Reciprocal-rank fusion of a lexical and a dense arm - the conventional
    strong baseline this literature would expect.

These arms are **diagnostic and exploratory**.  They were added after the
confirmatory run and are not part of the preregistered ``raw_vector`` versus
``okf_hybrid`` hypothesis family.  The confirmatory result is unchanged by them.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .okf_retrievers import OKFNativeRetriever, _tokens, _query_terms


# --------------------------------------------------------------------------
# Corpus access
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RawChunk:
    """One unmodified source chunk exactly as stored in pgvector."""

    chunk_id: str
    corpus: str
    text: str
    page_number: int | None
    section: str | None
    document_name: str | None
    metadata: Mapping[str, Any]

    @property
    def source_order(self) -> int:
        """Ordinal encoded in the chunk identifier, e.g. ``PGE-00100`` -> 100."""

        tail = self.chunk_id.rsplit("-", 1)[-1]
        return int(tail) if tail.isdigit() else -1

    def as_chunk_dict(self, score: float, *, mode: str) -> dict[str, Any]:
        metadata = dict(self.metadata or {})
        metadata.setdefault("pages", [self.page_number] if self.page_number else [])
        metadata["retrieval_mode"] = mode
        return {
            "chunk_id": self.chunk_id,
            "corpus": self.corpus,
            "text": self.text,
            "score": float(score),
            "rerank_score": None,
            "page_number": self.page_number,
            "section": self.section,
            "document_name": self.document_name,
            "metadata": metadata,
        }


def load_raw_chunks(
    *,
    host: str | None = None,
    port: int | None = None,
    dbname: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> list[RawChunk]:
    """Read every chunk from the evaluation pgvector table.

    Connection defaults match ``eval_harness/eval_config.yaml`` rather than the
    ambient ``DB_*`` environment, because the shared project ``.env`` points at
    an unrelated application database.
    """

    import psycopg

    conn = psycopg.connect(
        host=host or "localhost",
        port=int(port or 5433),
        dbname=dbname or "wmp_eval",
        user=user or "postgres",
        password=password or "postgres",
        connect_timeout=10,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            "select chunk_id, corpus, text, page_number, section, document_name, metadata "
            "from wmp_chunks order by chunk_id"
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [
        RawChunk(
            chunk_id=str(r[0]),
            corpus=str(r[1]),
            text=str(r[2]),
            page_number=r[3] if isinstance(r[3], int) else None,
            section=r[4],
            document_name=r[5],
            metadata=r[6] or {},
        )
        for r in rows
    ]


# --------------------------------------------------------------------------
# Shared BM25
# --------------------------------------------------------------------------


class BM25Index:
    """Okapi BM25 with the same k1/b defaults as ``OKFNativeRetriever``.

    Kept numerically identical to the OKF consumer so that any difference
    between the OKF and raw-chunk arms comes from the indexed text, not from a
    different ranking function.
    """

    def __init__(self, documents: Mapping[str, str], *, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1 = float(k1)
        self.b = float(b)
        self.frequencies: dict[str, Counter[str]] = {}
        self.lengths: dict[str, float] = {}
        for key, text in documents.items():
            freq = Counter(_tokens(text))
            self.frequencies[key] = freq
            self.lengths[key] = float(sum(freq.values()))

    def score(self, query: str, eligible: Sequence[str]) -> dict[str, float]:
        terms = _query_terms(query)
        if not terms or not eligible:
            return {}
        n_documents = len(eligible)
        total = sum(self.lengths.get(key, 0.0) for key in eligible)
        avg_length = (total / n_documents) if total > 0 else 1.0
        query_counts = Counter(terms)
        document_frequency = {
            term: sum(1 for key in eligible if self.frequencies.get(key, {}).get(term, 0) > 0)
            for term in query_counts
        }
        scores: dict[str, float] = {}
        for key in eligible:
            freq = self.frequencies.get(key)
            if not freq:
                continue
            length = self.lengths.get(key, 0.0)
            score = 0.0
            for term, query_frequency in query_counts.items():
                tf = float(freq.get(term, 0.0))
                if tf <= 0:
                    continue
                df = document_frequency[term]
                idf = math.log(1.0 + (n_documents - df + 0.5) / (df + 0.5))
                denominator = tf + self.k1 * (1.0 - self.b + self.b * length / avg_length)
                score += query_frequency * idf * (tf * (self.k1 + 1.0)) / denominator
            if score > 0:
                scores[key] = score
        return scores


# --------------------------------------------------------------------------
# Arms
# --------------------------------------------------------------------------


class BM25RawRetriever:
    """BM25 over unmodified source chunks. Contains no OKF component."""

    mode = "bm25_raw"

    def __init__(self, chunks: Iterable[RawChunk]) -> None:
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.index = BM25Index({cid: c.text for cid, c in self.chunks.items()})
        self._by_corpus: dict[str, list[str]] = {}
        for cid, chunk in self.chunks.items():
            self._by_corpus.setdefault(chunk.corpus, []).append(cid)

    def ranked(self, query: str, corpus: str, top_k: int) -> list[tuple[str, float]]:
        eligible = self._by_corpus.get(corpus, [])
        scores = self.index.score(query, eligible)
        ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return ordered[:top_k]

    def dense_search(self, query: str, corpus: str, top_k: int = 10) -> list[dict[str, Any]]:
        return [
            self.chunks[cid].as_chunk_dict(score, mode=self.mode)
            for cid, score in self.ranked(query, corpus, top_k)
        ]


class TitanDenseRetriever:
    """Dense retrieval with a non-truncating embedding model.

    ``amazon.titan-embed-text-v2:0`` has an 8192-token input window, so every
    passage in this corpus is embedded in full.  This is the fair dense
    counterpart to the frozen ``all-MiniLM-L6-v2`` arm.
    """

    mode = "titan_dense"
    model_id = "amazon.titan-embed-text-v2:0"
    dimensions = 1024

    def __init__(self, chunks: Iterable[RawChunk], cache_path: str | Path) -> None:
        import numpy as np

        self.np = np
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.cache_path = Path(cache_path)
        vectors = self._load_or_build()
        self.ids = list(vectors)
        self.matrix = np.asarray([vectors[cid] for cid in self.ids], dtype="float32")
        # Titan is asked for normalised vectors; renormalise defensively so the
        # dot product is exactly cosine similarity.
        norms = np.linalg.norm(self.matrix, axis=1, keepdims=True)
        self.matrix = self.matrix / np.clip(norms, 1e-12, None)
        self._rows = {cid: i for i, cid in enumerate(self.ids)}
        self._by_corpus: dict[str, list[int]] = {}
        for cid, chunk in self.chunks.items():
            if cid in self._rows:
                self._by_corpus.setdefault(chunk.corpus, []).append(self._rows[cid])
        self._query_cache: dict[str, Any] = {}

    # -- embedding -------------------------------------------------------

    def _client(self):
        import boto3

        return boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-west-2"))

    def _embed(self, text: str, *, client=None) -> list[float]:
        client = client or self._client()
        body = json.dumps(
            {"inputText": text, "dimensions": self.dimensions, "normalize": True}
        )
        last: Exception | None = None
        for attempt in range(6):
            try:
                response = client.invoke_model(modelId=self.model_id, body=body)
                return json.loads(response["body"].read())["embedding"]
            except Exception as exc:  # throttling and transient faults
                last = exc
                if "Throttl" in type(exc).__name__ or "Throttl" in str(exc):
                    time.sleep(min(2**attempt, 20))
                    continue
                raise
        raise RuntimeError(f"embedding failed after retries: {last}")

    def _load_or_build(self) -> dict[str, list[float]]:
        if self.cache_path.exists():
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if payload.get("model_id") == self.model_id and payload.get(
                "corpus_sha256"
            ) == self._corpus_hash():
                return payload["vectors"]
        client = self._client()
        vectors: dict[str, list[float]] = {}
        total = len(self.chunks)
        for index, (cid, chunk) in enumerate(sorted(self.chunks.items()), start=1):
            vectors[cid] = self._embed(chunk.text, client=client)
            if index % 200 == 0 or index == total:
                print(f"[titan] embedded {index}/{total}", flush=True)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(
                {
                    "model_id": self.model_id,
                    "dimensions": self.dimensions,
                    "corpus_sha256": self._corpus_hash(),
                    "vectors": vectors,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return vectors

    def _corpus_hash(self) -> str:
        digest = hashlib.sha256()
        for cid, chunk in sorted(self.chunks.items()):
            digest.update(cid.encode())
            digest.update(chunk.text.encode())
        return digest.hexdigest()

    # -- search ----------------------------------------------------------

    def _query_vector(self, query: str):
        if query not in self._query_cache:
            vector = self.np.asarray(self._embed(query), dtype="float32")
            norm = float(self.np.linalg.norm(vector)) or 1.0
            self._query_cache[query] = vector / norm
        return self._query_cache[query]

    def ranked(self, query: str, corpus: str, top_k: int) -> list[tuple[str, float]]:
        rows = self._by_corpus.get(corpus, [])
        if not rows:
            return []
        index = self.np.asarray(rows, dtype="int64")
        similarities = self.matrix[index] @ self._query_vector(query)
        order = self.np.argsort(-similarities)[:top_k]
        return [(self.ids[int(index[i])], float(similarities[int(i)])) for i in order]

    def dense_search(self, query: str, corpus: str, top_k: int = 10) -> list[dict[str, Any]]:
        return [
            self.chunks[cid].as_chunk_dict(score, mode=self.mode)
            for cid, score in self.ranked(query, corpus, top_k)
        ]


class RRFFusionRetriever:
    """Reciprocal-rank fusion of two ranked arms.

    ``score(d) = sum_arms 1 / (k + rank_arm(d))`` with ``k = 60``, the value used
    in the original formulation.  Fusion depth is deliberately larger than the
    reported top-k so that documents ranked highly by only one arm can surface.
    """

    mode = "rrf_fusion"

    def __init__(self, arms: Sequence[Any], *, k: float = 60.0, fusion_depth: int = 50) -> None:
        if len(arms) < 2:
            raise ValueError("fusion needs at least two arms")
        self.arms = list(arms)
        self.k = float(k)
        self.fusion_depth = int(fusion_depth)
        self.chunks: dict[str, RawChunk] = {}
        for arm in self.arms:
            self.chunks.update(getattr(arm, "chunks", {}))

    def ranked(self, query: str, corpus: str, top_k: int) -> list[tuple[str, float]]:
        fused: dict[str, float] = {}
        for arm in self.arms:
            for rank, (cid, _score) in enumerate(
                arm.ranked(query, corpus, self.fusion_depth), start=1
            ):
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (self.k + rank)
        ordered = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))
        return ordered[:top_k]

    def dense_search(self, query: str, corpus: str, top_k: int = 10) -> list[dict[str, Any]]:
        return [
            self.chunks[cid].as_chunk_dict(score, mode=self.mode)
            for cid, score in self.ranked(query, corpus, top_k)
        ]


class OKFEvidenceOnlyRetriever(OKFNativeRetriever):
    """``OKFNativeRetriever`` with the frontmatter contribution removed.

    The production consumer indexes the passage text plus weighted ``title``,
    ``description``, ``type``, ``section`` and ``tags`` fields.  This subclass
    reindexes the passage text alone and changes nothing else, so the difference
    against ``okf_native`` measures exactly what the frontmatter fields
    contribute to retrieval.
    """

    def __init__(self, bundle, **kwargs) -> None:
        super().__init__(bundle, **kwargs)
        self._term_frequencies = {}
        self._document_lengths = {}
        for concept in self.bundle:
            frequencies = Counter(_tokens(concept.evidence))
            self._term_frequencies[concept.concept_id] = frequencies
            self._document_lengths[concept.concept_id] = float(sum(frequencies.values()))


class AdjacencyWrapper:
    """Reserve part of the result budget for source-order-adjacent chunks.

    This reproduces the OKF consumer's one-hop previous/next expansion *without
    OKF*: adjacency comes from the chunk identifier ordinal rather than from
    Markdown links.  Comparing this with the OKF arms separates "adjacency as an
    idea" from "adjacency delivered through OKF links".
    """

    def __init__(self, base: Any, *, seed_fraction: float = 0.5, link_decay: float = 0.35) -> None:
        self.base = base
        self.seed_fraction = float(seed_fraction)
        self.link_decay = float(link_decay)
        self.chunks = getattr(base, "chunks", {})
        self.mode = f"{getattr(base, 'mode', 'base')}+adjacent"
        self._order: dict[str, dict[int, str]] = {}
        for cid, chunk in self.chunks.items():
            self._order.setdefault(chunk.corpus, {})[chunk.source_order] = cid

    def ranked(self, query: str, corpus: str, top_k: int) -> list[tuple[str, float]]:
        seed_k = max(1, math.ceil(top_k * self.seed_fraction))
        seeds = self.base.ranked(query, corpus, seed_k)
        scores = {cid: score for cid, score in seeds}
        ordinals = self._order.get(corpus, {})
        for cid, score in seeds:
            chunk = self.chunks.get(cid)
            if chunk is None:
                continue
            for delta in (-1, 1):
                neighbour = ordinals.get(chunk.source_order + delta)
                if neighbour is None or neighbour in scores:
                    continue
                scores[neighbour] = max(0.0, score) * self.link_decay
        ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return ordered[:top_k]

    def dense_search(self, query: str, corpus: str, top_k: int = 10) -> list[dict[str, Any]]:
        return [
            self.chunks[cid].as_chunk_dict(score, mode=self.mode)
            for cid, score in self.ranked(query, corpus, top_k)
        ]
