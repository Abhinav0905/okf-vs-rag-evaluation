"""Vector-store interface and retrievers (Task 1.3).

Three interchangeable backends behind one :class:`Retriever` ABC:

* :class:`PgVectorRetriever` — **primary**. Postgres + pgvector. The same code
  runs against the local Docker container and against Aurora PostgreSQL on AWS
  (only the connection host changes). Cosine similarity via the ``<=>`` operator.
* :class:`FaissRetriever` — local FAISS fallback for offline testing.
* :class:`BedrockKBRetriever` — managed Bedrock Knowledge Base ``Retrieve`` API
  (AWS path), with metadata-filter tenant scoping.

**Tenant isolation (R5).** Every ``dense_search`` requires a ``corpus`` argument
and scopes results to that single tenant — pgvector via ``WHERE corpus = %s``,
FAISS via per-corpus indexes, Bedrock via a metadata ``equals`` filter. A query
can never see another utility's chunks.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import numpy as np

from .config import Config
from .embeddings import Embedder, get_embedder
from .models import RetrievedChunk


# ---------------------------------------------------------------------------
# Token counting (shared with get_context budgeting)
# ---------------------------------------------------------------------------

def count_tokens(text: str) -> int:
    """Token count using tiktoken cl100k if available, else a word approx."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return int(len(text.split()) * 1.3) + 1


# ---------------------------------------------------------------------------
# Cross-encoder reranker (shared)
# ---------------------------------------------------------------------------

class CrossEncoderReranker:
    """Local cross-encoder reranker (default: ms-marco-MiniLM-L-6-v2)."""

    def __init__(self, model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 device: str | None = None):
        self.model_id = model_id
        self.device = device
        self._model = None

    def _lazy(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_id, device=self.device)
        return self._model

    def score(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return chunks
        try:
            model = self._lazy()
            pairs = [(query, c.text) for c in chunks]
            scores = model.predict(pairs, show_progress_bar=False)
            for c, s in zip(chunks, scores):
                c.rerank_score = float(s)
        except Exception:
            # Reranker unavailable: keep dense order, mark rerank as dense score.
            for c in chunks:
                c.rerank_score = c.score
        return sorted(chunks, key=lambda c: (c.rerank_score if c.rerank_score is not None else c.score),
                      reverse=True)


# ---------------------------------------------------------------------------
# Abstract retriever
# ---------------------------------------------------------------------------

class Retriever(ABC):
    """Abstract vector-store operations."""

    def __init__(self, config: Config, embedder: Optional[Embedder] = None,
                 reranker: Optional[CrossEncoderReranker] = None):
        self.config = config
        from .config import resolve_device

        self.device = resolve_device(config.retriever.device)
        self.embedder = embedder or get_embedder(
            config.retriever.embed_model, backend="sentence_transformers",
            dim=config.retriever.embed_dim, device=self.device,
        )
        self.reranker = reranker or CrossEncoderReranker(
            config.retriever.reranker_model, device=self.device)

    @abstractmethod
    def dense_search(self, query: str, corpus: str, top_k: int = 20) -> list[RetrievedChunk]:
        """Dense (embedding) search scoped to a single ``corpus`` (tenant)."""

    def rerank(self, query: str, candidates: list[RetrievedChunk],
               model: Optional[str] = None, top_k: Optional[int] = None) -> list[RetrievedChunk]:
        """Cross-encoder rerank; returns the top ``top_k`` reranked chunks."""
        reranked = self.reranker.score(query, candidates)
        return reranked[:top_k] if top_k else reranked

    def get_context(self, candidates: list[RetrievedChunk],
                    token_budget: int = 2200) -> tuple[str, list[RetrievedChunk]]:
        """Greedily pack chunks into a context string under ``token_budget``.

        Returns ``(context_text, included_chunks)``. Each chunk is prefixed with
        its id and page for citation traceability (R3).
        """
        used, included, parts = 0, [], []
        for c in candidates:
            header = f"[{c.chunk_id}"
            if c.page_number is not None:
                header += f" | p.{c.page_number}"
            header += "]"
            block = f"{header}\n{c.text}"
            n = count_tokens(block)
            if used + n > token_budget and included:
                break
            parts.append(block)
            included.append(c)
            used += n
        return "\n\n".join(parts), included

    def close(self) -> None:  # pragma: no cover - backend specific
        pass


# ---------------------------------------------------------------------------
# pgvector (primary)
# ---------------------------------------------------------------------------

class PgVectorRetriever(Retriever):
    """Postgres + pgvector retriever. Works on local Docker and Aurora alike."""

    def __init__(self, config: Config, **kw):
        super().__init__(config, **kw)
        import psycopg
        from pgvector.psycopg import register_vector

        self._pg = config.retriever.pg
        self._table = self._pg.table
        self._conn = psycopg.connect(self._pg.dsn(), autocommit=True)
        self._conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self._conn)

    def ensure_schema(self, dim: int) -> None:
        """Create the chunks table + indexes if missing (idempotent)."""
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
                chunk_id      TEXT PRIMARY KEY,
                corpus        TEXT NOT NULL,
                text          TEXT NOT NULL,
                page_number   INTEGER,
                section       TEXT,
                document_name TEXT,
                metadata      JSONB DEFAULT '{{}}'::jsonb,
                embedding     vector({dim})
            )
            """
        )
        self._conn.execute(
            f"CREATE INDEX IF NOT EXISTS {self._table}_corpus_idx ON {self._table} (corpus)"
        )
        # Cosine HNSW index for fast ANN search.
        self._conn.execute(
            f"CREATE INDEX IF NOT EXISTS {self._table}_emb_idx ON {self._table} "
            f"USING hnsw (embedding vector_cosine_ops)"
        )

    def upsert(self, chunks: list[RetrievedChunk], vectors: np.ndarray) -> int:
        """Insert/replace chunks with their embeddings. Returns rows written."""
        rows = 0
        with self._conn.cursor() as cur:
            for c, v in zip(chunks, vectors):
                cur.execute(
                    f"""
                    INSERT INTO {self._table}
                        (chunk_id, corpus, text, page_number, section, document_name, metadata, embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        corpus=EXCLUDED.corpus, text=EXCLUDED.text,
                        page_number=EXCLUDED.page_number, section=EXCLUDED.section,
                        document_name=EXCLUDED.document_name, metadata=EXCLUDED.metadata,
                        embedding=EXCLUDED.embedding
                    """,
                    (c.chunk_id, c.corpus, c.text, c.page_number, c.section,
                     c.document_name, json.dumps(c.metadata), np.asarray(v, dtype=np.float32)),
                )
                rows += 1
        return rows

    def count(self, corpus: Optional[str] = None) -> int:
        if corpus:
            r = self._conn.execute(
                f"SELECT count(*) FROM {self._table} WHERE corpus=%s", (corpus,)
            ).fetchone()
        else:
            r = self._conn.execute(f"SELECT count(*) FROM {self._table}").fetchone()
        return int(r[0])

    def dense_search(self, query: str, corpus: str, top_k: int = 20) -> list[RetrievedChunk]:
        qv = self.embedder.encode([query], is_query=True)[0]
        return self.search_vector(qv, corpus, top_k)

    def search_vector(self, qv, corpus: str, top_k: int = 20) -> list[RetrievedChunk]:
        """Vector-only search (no embedding step) — lets callers time embed vs. DB."""
        # Tenant isolation: WHERE corpus = %s. Cosine distance via <=>.
        cur = self._conn.execute(
            f"""
            SELECT chunk_id, corpus, text, page_number, section, document_name, metadata,
                   1 - (embedding <=> %s) AS score
            FROM {self._table}
            WHERE corpus = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (np.asarray(qv, dtype=np.float32), corpus, np.asarray(qv, dtype=np.float32), top_k),
        )
        out = []
        for row in cur.fetchall():
            cid, corp, text, page, section, docname, meta, score = row
            out.append(RetrievedChunk(
                chunk_id=cid, corpus=corp, text=text, page_number=page,
                section=section, document_name=docname,
                metadata=meta or {}, score=float(score),
            ))
        return out

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# FAISS (fallback)
# ---------------------------------------------------------------------------

class FaissRetriever(Retriever):
    """Per-corpus FAISS indexes loaded from ``data/faiss_index/<corpus>/``."""

    def __init__(self, config: Config, **kw):
        super().__init__(config, **kw)
        self._dir = config.resolve(config.retriever.faiss_index_dir)
        self._indexes: dict[str, object] = {}
        self._chunks: dict[str, list[RetrievedChunk]] = {}

    def _load(self, corpus: str):
        if corpus in self._indexes:
            return
        import faiss

        cdir = self._dir / corpus
        idx = faiss.read_index(str(cdir / "index.faiss"))
        chunks = [RetrievedChunk(**d) for d in json.loads((cdir / "chunks.json").read_text())]
        self._indexes[corpus] = idx
        self._chunks[corpus] = chunks

    def dense_search(self, query: str, corpus: str, top_k: int = 20) -> list[RetrievedChunk]:
        self._load(corpus)
        qv = self.embedder.encode([query], is_query=True).astype(np.float32)
        scores, idxs = self._indexes[corpus].search(qv, top_k)
        out = []
        for score, i in zip(scores[0], idxs[0]):
            if i < 0:
                continue
            c = self._chunks[corpus][i].model_copy()
            c.score = float(score)
            out.append(c)
        return out


# ---------------------------------------------------------------------------
# Bedrock managed Knowledge Base (AWS path)
# ---------------------------------------------------------------------------

class BedrockKBRetriever(Retriever):
    """Managed Bedrock KB ``Retrieve`` with metadata-filter tenant scoping."""

    def __init__(self, config: Config, **kw):
        super().__init__(config, **kw)
        import boto3

        self._kb_id = config.retriever.bedrock_kb_id
        self._client = boto3.client("bedrock-agent-runtime", region_name=config.generator.region)

    def dense_search(self, query: str, corpus: str, top_k: int = 20) -> list[RetrievedChunk]:
        resp = self._client.retrieve(
            knowledgeBaseId=self._kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": top_k,
                    "filter": {"equals": {"key": "corpus", "value": corpus}},
                }
            },
        )
        out = []
        for i, r in enumerate(resp.get("retrievalResults", [])):
            meta = r.get("metadata", {})
            out.append(RetrievedChunk(
                chunk_id=meta.get("chunk_id", f"{corpus}-kb-{i}"),
                corpus=corpus,
                text=r.get("content", {}).get("text", ""),
                score=float(r.get("score", 0.0)),
                page_number=meta.get("x-amz-bedrock-kb-document-page-number"),
                document_name=meta.get("filename"),
                metadata=meta,
            ))
        return out


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_retriever(config: Config, embedder: Optional[Embedder] = None) -> Retriever:
    backend = config.retriever.backend
    if backend == "pgvector":
        return PgVectorRetriever(config, embedder=embedder)
    if backend == "faiss":
        return FaissRetriever(config, embedder=embedder)
    if backend == "bedrock_kb":
        return BedrockKBRetriever(config, embedder=embedder)
    raise ValueError(f"unknown retriever backend: {backend}")
