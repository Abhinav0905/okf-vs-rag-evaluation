"""Embedding backends (shared by ingestion and retrieval).

Primary backend is a local sentence-transformers bi-encoder (offline,
reproducible, no per-call cost). A Bedrock Titan backend is provided for the
managed-KB / AWS path. Both expose the same :class:`Embedder` protocol so
ingestion and the retriever can be pointed at either by config.

Reproducibility: the sentence-transformers model id and dimension are pinned in
``eval_config.yaml`` and recorded in the corpus manifest at ingestion time.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """Minimal embedding interface."""

    dim: int
    model_id: str

    def encode(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        """Return an (n, dim) float32 array of L2-normalised embeddings."""
        ...


def _l2_normalise(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (mat / norms).astype(np.float32)


class SentenceTransformerEmbedder:
    """Local bi-encoder via sentence-transformers.

    Deterministic given a fixed model and input (eval runs on CPU by default).
    """

    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
                 device: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model_id = model_id
        self._model = SentenceTransformer(model_id, device=device)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(
            texts,
            batch_size=64,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return _l2_normalise(np.asarray(vecs, dtype=np.float32))


class BedrockTitanEmbedder:
    """Amazon Titan Text Embeddings v2 via bedrock-runtime (AWS path).

    Requires valid AWS credentials. Used when embedding into an Aurora-pgvector
    Bedrock Knowledge Base so query and document vectors share a space.
    """

    def __init__(self, model_id: str = "amazon.titan-embed-text-v2:0",
                 region: str = "us-west-2", dim: int = 1024):
        import boto3
        import json

        self.model_id = model_id
        self.dim = dim
        self._region = region
        self._json = json
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def encode(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            body = self._json.dumps({"inputText": t, "dimensions": self.dim,
                                     "normalize": True})
            resp = self._client.invoke_model(modelId=self.model_id, body=body)
            payload = self._json.loads(resp["body"].read())
            out[i] = np.asarray(payload["embedding"], dtype=np.float32)
        return _l2_normalise(out)


class HashingEmbedder:
    """Deterministic, dependency-free fallback embedder (offline CI / tests).

    Produces stable pseudo-embeddings from token hashes. NOT semantically
    meaningful — only for wiring tests when no model can be downloaded.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.model_id = f"hashing-{dim}"

    def encode(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in t.lower().split():
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                out[i, h % self.dim] += 1.0
        return _l2_normalise(out)


@lru_cache(maxsize=8)
def get_embedder(model_id: str, backend: str = "sentence_transformers",
                 region: str = "us-west-2", dim: int = 384,
                 device: str | None = None) -> Embedder:
    """Factory. Falls back to HashingEmbedder if the model can't be loaded."""
    if backend == "bedrock_titan":
        return BedrockTitanEmbedder(model_id=model_id, region=region, dim=dim)
    if backend == "hashing":
        return HashingEmbedder(dim=dim)
    try:
        return SentenceTransformerEmbedder(model_id=model_id, device=device)
    except Exception as exc:  # pragma: no cover - network/model failure path
        import warnings

        warnings.warn(
            f"SentenceTransformer '{model_id}' unavailable ({exc}); "
            f"falling back to HashingEmbedder(dim={dim}).",
            RuntimeWarning,
        )
        return HashingEmbedder(dim=dim)
