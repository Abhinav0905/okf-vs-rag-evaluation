"""Configuration loader for the evaluation harness (Task 1.1).

Loads ``eval_config.yaml`` (safe to commit) and layers environment-sourced
secrets (AWS creds, DB password, API keys) on top. A ``.env`` file at the
harness root or repo root is auto-loaded if present.

Design: the YAML holds *policy* (which model, which backend, thresholds); the
environment holds *secrets and deployment specifics* (hostnames, tokens). This
keeps the committed config reproducible without leaking credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

# Repo root = two levels up from this file's package root (eval_harness/).
HARNESS_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = HARNESS_ROOT.parent


def _load_dotenv() -> None:
    """Minimal .env loader (no external dependency).

    Loads ``eval_harness/.env`` then the repo-root ``.env`` (the latter holds
    the shared AWS creds). Existing environment variables always win, so an
    explicit ``export`` overrides the file.
    """
    for candidate in (HARNESS_ROOT / ".env", REPO_ROOT / ".env"):
        if not candidate.exists():
            continue
        for raw in candidate.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


# ---------------------------------------------------------------------------
# Typed config sections
# ---------------------------------------------------------------------------

@dataclass
class PgConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    table: str

    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.dbname} "
            f"user={self.user} password={self.password}"
        )

    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
        )


@dataclass
class RetrieverConfig:
    backend: str
    top_k: int
    overfetch_k: int
    reranker_model: str
    token_budget: int
    embed_model: str
    embed_dim: int
    pg: PgConfig
    faiss_index_dir: str
    bedrock_kb_id: Optional[str]
    bedrock_rerank_model_arn: str
    device: str = "auto"          # cpu | mps | cuda | auto (local SLM device)


@dataclass
class GeneratorConfig:
    backend: str
    bedrock_model_id: str
    region: str
    max_tokens: int
    temperature: float
    openai_model: str


@dataclass
class EARConfig:
    base_model_path: str
    adapter_registry_path: str
    coverage_threshold: float
    iteration_cap: int
    allow_heuristic_fallback: bool


@dataclass
class JudgeConfig:
    backend: str
    model_id: str
    region: str
    temperature: float
    trials_per_question: int
    rubric_path: str
    openai_model: str
    gold_annotations_path: str


@dataclass
class OutputConfig:
    dir: str
    db_path: str
    records_jsonl: str
    table1_md: str
    stats_md: str
    cost_md: str
    audit_chain: str


@dataclass
class Config:
    seed: int
    retriever: RetrieverConfig
    generator: GeneratorConfig
    ear: EARConfig
    systems: dict[str, Any]
    judge: JudgeConfig
    pricing: dict[str, dict[str, float]]
    output: OutputConfig
    queries_per_day: int
    raw: dict[str, Any] = field(default_factory=dict)

    # -- helpers --------------------------------------------------------------
    def resolve(self, rel: str) -> Path:
        """Resolve a config-relative path against the harness root."""
        p = Path(rel)
        return p if p.is_absolute() else (HARNESS_ROOT / p)

    def price(self, model_id: str) -> dict[str, float]:
        """Return {'input_per_mtok', 'output_per_mtok'} for a model id.

        Falls back to zero cost for unknown models (e.g. mock) so cost
        accounting never crashes.
        """
        return self.pricing.get(model_id, {"input_per_mtok": 0.0, "output_per_mtok": 0.0})


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: str | Path | None = None) -> Config:
    """Load and validate the harness configuration.

    Args:
        path: path to ``eval_config.yaml``. Defaults to the harness root.
    """
    _load_dotenv()
    cfg_path = Path(path) if path else (HARNESS_ROOT / "eval_config.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError(f"eval config not found: {cfg_path}")
    data = yaml.safe_load(cfg_path.read_text())

    r = data["retriever"]
    pgc = r["pg"]
    pg = PgConfig(
        host=_env(pgc["host_env"], pgc["default_host"]),
        port=int(_env(pgc["port_env"], str(pgc["default_port"]))),
        dbname=_env(pgc["dbname_env"], pgc["default_dbname"]),
        user=_env(pgc["user_env"], pgc["default_user"]),
        password=_env(pgc["password_env"], pgc["default_password"]),
        table=pgc["table"],
    )
    retriever = RetrieverConfig(
        backend=r["backend"],
        top_k=int(r["top_k"]),
        overfetch_k=int(r["overfetch_k"]),
        reranker_model=r["reranker_model"],
        token_budget=int(r["token_budget"]),
        embed_model=r["embed_model"],
        embed_dim=int(r["embed_dim"]),
        pg=pg,
        faiss_index_dir=r["faiss"]["index_dir"],
        bedrock_kb_id=_env(r["bedrock_kb"]["knowledge_base_id_env"]),
        bedrock_rerank_model_arn=r["bedrock_kb"]["rerank_model_arn"],
        device=_env("EVAL_DEVICE", r.get("device", "auto")),
    )

    g = data["generator"]
    generator = GeneratorConfig(
        backend=g["backend"],
        bedrock_model_id=g["bedrock_model_id"],
        region=_env(g["region_env"], "us-west-2"),
        max_tokens=int(g["max_tokens"]),
        temperature=float(g["temperature"]),
        openai_model=g["openai_model"],
    )

    e = data["ear"]
    ear = EARConfig(
        base_model_path=e["base_model_path"],
        adapter_registry_path=e["adapter_registry_path"],
        coverage_threshold=float(e["coverage_threshold"]),
        iteration_cap=int(e["iteration_cap"]),
        allow_heuristic_fallback=bool(e["allow_heuristic_fallback"]),
    )

    j = data["judge"]
    judge = JudgeConfig(
        backend=j["backend"],
        model_id=j["model_id"],
        region=_env(j["region_env"], "us-west-2"),
        temperature=float(j["temperature"]),
        trials_per_question=int(j["trials_per_question"]),
        rubric_path=j["rubric_path"],
        openai_model=j["openai_model"],
        gold_annotations_path=j.get("gold_annotations_path", ""),
    )

    o = data["output"]
    output = OutputConfig(
        dir=o["dir"],
        db_path=o["db_path"],
        records_jsonl=o["records_jsonl"],
        table1_md=o["table1_md"],
        stats_md=o["stats_md"],
        cost_md=o["cost_md"],
        audit_chain=o["audit_chain"],
    )

    return Config(
        seed=int(data.get("seed", 42)),
        retriever=retriever,
        generator=generator,
        ear=ear,
        systems=data.get("systems", {}),
        judge=judge,
        pricing=data.get("pricing", {}),
        output=output,
        queries_per_day=int(data.get("projection", {}).get("queries_per_day", 10000)),
        raw=data,
    )


@lru_cache(maxsize=4)
def get_config(path: str | None = None) -> Config:
    """Cached config accessor for code that doesn't thread a Config through."""
    return load_config(path)


def resolve_device(name: str = "auto") -> str:
    """Resolve a requested device to a concrete torch device string.

    ``auto`` prefers CUDA, then Apple MPS, then CPU. An explicit request that is
    unavailable falls back to CPU (with the caller free to warn).
    """
    name = (name or "auto").lower()
    try:
        import torch
    except ImportError:
        return "cpu"
    has_cuda = torch.cuda.is_available()
    has_mps = getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
    if name == "auto":
        return "cuda" if has_cuda else ("mps" if has_mps else "cpu")
    if name == "cuda" and not has_cuda:
        return "cpu"
    if name == "mps" and not has_mps:
        return "cpu"
    return name


def set_global_seed(seed: int) -> None:
    """Fix all RNG seeds for reproducibility (Task 8 checklist item)."""
    import random

    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
