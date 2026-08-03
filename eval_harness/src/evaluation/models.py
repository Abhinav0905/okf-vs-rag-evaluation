"""Pydantic data models for the WMP-CRIS evaluation harness.

These are the canonical records that flow between the system runners
(``systems/``), the judge (``judge.py``), the SQLite store, and the statistics
module (``stats.py``).

Task 2 of the evaluation spec defines :class:`AnswerRecord`; the remaining
models support the judge protocol (Task 3) and auditability (Task 6).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Corpus(str, Enum):
    """Tenant / corpus identifier. Each maps to one utility's WMP.

    The string values match the ``utility_short`` prefixes used in the
    question set and the directory names under ``data/corpora/``.
    """

    PGE = "PGE"
    SCE = "SCE"
    PC = "PC"

    @property
    def corpus_dir(self) -> str:
        """Directory name under ``data/corpora/`` for this corpus."""
        return {
            Corpus.PGE: "pge_2026_2028_wmp",
            Corpus.SCE: "sce_2026_2028_wmp",
            Corpus.PC: "pc_2026_2028_wmp",
        }[self]

    @property
    def display_name(self) -> str:
        return {Corpus.PGE: "PG&E", Corpus.SCE: "SCE", Corpus.PC: "PacifiCorp"}[self]


class SystemName(str, Enum):
    """The five baseline systems compared in this evaluation."""

    SIMPLE_RAG = "simple_rag"
    RERANKED_SIMPLE = "reranked_simple"
    AGENTIC_RAG = "agentic_rag"
    SELF_RAG = "self_rag"
    FLARE = "flare"


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

class RetrievedChunk(BaseModel):
    """A single retrieved passage plus its provenance and scores."""

    chunk_id: str
    corpus: str
    text: str
    score: float = 0.0                 # dense similarity (cosine) at retrieval time
    rerank_score: Optional[float] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    document_name: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Answer record (Task 2)
# ---------------------------------------------------------------------------

class AnswerRecord(BaseModel):
    """One system's answer to one question, with cost/latency accounting.

    This is the unit of storage in ``results/evaluation.db`` and the unit of
    release in ``results/per_question_records.jsonl``.
    """

    system_name: str
    qid: str
    question: str
    answer_text: str
    citations: list[str] = Field(default_factory=list)   # chunk IDs cited
    generator_calls: int = 0
    generator_cost_usd: float = 0.0                       # Bedrock on-demand pricing
    latency_ms: float = 0.0
    retrieval_log: Optional[dict] = None                 # system-specific metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    corpus: str                                          # PGE, SCE, or PC (primary)

    # Convenience, not part of the required schema — the retrieved context is
    # needed by the judge for the retrieval-axis rubrics (R1-R3). Kept optional
    # so serialised release records can omit it.
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)

    @field_validator("generator_calls")
    @classmethod
    def _non_negative_calls(cls, v: int) -> int:
        if v < 0:
            raise ValueError("generator_calls must be >= 0")
        return v

    def refused(self) -> bool:
        """Heuristic: did the system decline to answer / say 'not found'?

        Used as the behavioural signal for negative (out-of-scope) questions and
        for the G3 (refusal appropriateness) rubric fallback.
        """
        a = self.answer_text.lower()
        markers = (
            "does not contain sufficient information",
            "not contain sufficient information",
            "cannot answer",
            "can't answer",
            "no information",
            "not found in",
            "not covered",
            "unable to answer",
            "not addressed in",
            "not mentioned in",
            "i don't have",
            "i do not have",
            "outside the scope",
            "not in the provided context",
        )
        return any(m in a for m in markers)


# ---------------------------------------------------------------------------
# Judge (Task 3)
# ---------------------------------------------------------------------------

class RubricScores(BaseModel):
    """The nine 1-5 rubric scores from a single judge trial.

    Retrieval axis: R1 relevance, R2 coverage, R3 citation quality.
    Generation axis: G1 correctness, G2 completeness, G3 refusal appropriateness.
    """

    R1: float
    R2: float
    R3: float
    G1: float
    G2: float
    G3: float
    explanation: str = ""

    @field_validator("R1", "R2", "R3", "G1", "G2", "G3")
    @classmethod
    def _in_range(cls, v: float) -> float:
        if not (1.0 <= v <= 5.0):
            raise ValueError(f"rubric score {v} out of 1-5 range")
        return v

    @property
    def retrieval_mean(self) -> float:
        return (self.R1 + self.R2 + self.R3) / 3.0

    @property
    def generation_mean(self) -> float:
        return (self.G1 + self.G2 + self.G3) / 3.0


class JudgeTrial(BaseModel):
    """A single judge invocation (one of N trials per answer)."""

    trial_index: int
    scores: RubricScores
    judge_model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    raw_response: str = ""


class JudgeResult(BaseModel):
    """Averaged judge scores across N trials for one AnswerRecord."""

    system_name: str
    qid: str
    corpus: str
    n_trials: int
    R1: float
    R2: float
    R3: float
    G1: float
    G2: float
    G3: float
    retrieval_mean: float
    generation_mean: float
    score_std: float = 0.0          # std of the six means across trials (determinism check)
    judge_model: str = ""
    total_cost_usd: float = 0.0
    trials: list[JudgeTrial] = Field(default_factory=list)

    @classmethod
    def from_trials(
        cls,
        system_name: str,
        qid: str,
        corpus: str,
        trials: list[JudgeTrial],
    ) -> "JudgeResult":
        import statistics

        n = len(trials)
        if n == 0:
            raise ValueError("cannot aggregate zero judge trials")

        def avg(attr: str) -> float:
            return sum(getattr(t.scores, attr) for t in trials) / n

        means = {k: avg(k) for k in ("R1", "R2", "R3", "G1", "G2", "G3")}
        ret_mean = (means["R1"] + means["R2"] + means["R3"]) / 3.0
        gen_mean = (means["G1"] + means["G2"] + means["G3"]) / 3.0

        # Determinism check: spread of the per-trial overall mean.
        per_trial_overall = [
            (t.scores.retrieval_mean + t.scores.generation_mean) / 2.0 for t in trials
        ]
        std = statistics.pstdev(per_trial_overall) if n > 1 else 0.0

        return cls(
            system_name=system_name,
            qid=qid,
            corpus=corpus,
            n_trials=n,
            **means,
            retrieval_mean=ret_mean,
            generation_mean=gen_mean,
            score_std=std,
            judge_model=trials[0].judge_model,
            total_cost_usd=sum(t.cost_usd for t in trials),
            trials=trials,
        )




__all__ = [
    "Corpus",
    "SystemName",
    "RetrievedChunk",
    "AnswerRecord",
    "RubricScores",
    "JudgeTrial",
    "JudgeResult",
]
