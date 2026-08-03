"""Shared scaffolding for the system runners (Task 1.4).

Every runner subclasses :class:`BaseSystem` and implements :meth:`run`, which
takes a :class:`Question` + corpus id and returns an :class:`AnswerRecord`
carrying the answer, citations, generator-call count, USD cost, latency, and a
system-specific ``retrieval_log``.

The runners share:
* a WMP answer-prompt builder (domain rules: cite, don't hallucinate, refuse
  when context is insufficient — mirrors the production RAG service prompt);
* a citation parser that maps answer text back to retrieved chunk ids (R3);
* cost/latency bookkeeping via a small :class:`_Meter`.
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from ..config import Config
from ..generator import GenResult, Generator
from ..models import AnswerRecord, RetrievedChunk, SystemName
from ..questions import Question
from ..retriever import Retriever

_CHUNK_ID_RE = re.compile(r"\b([A-Z]{2,3}-\d{5})\b")

WMP_SYSTEM_PROMPT = (
    "You are a domain expert on California electric utility Wildfire Mitigation "
    "Plans (WMPs). Answer using ONLY the retrieved context provided. Rules:\n"
    "1. CITE SOURCES using the bracketed chunk id and page, e.g. [SCE-00123 | p.42].\n"
    "2. Address EVERY part of the question; if a sub-part is unsupported, say so.\n"
    "3. If the context does not contain enough information, reply EXACTLY: "
    "'The retrieved context does not contain sufficient information to answer this.'\n"
    "4. Reproduce numbers, dates, and targets EXACTLY as written; never guess."
)


def build_answer_prompt(question: str, context: str) -> str:
    """Compose the user prompt from the question and packed context."""
    ctx = context.strip() or "NO_CONTEXT"
    return (
        f"Retrieved context:\n{ctx}\n\n"
        f"Question: {question}\n\n"
        f"Answer (cite chunk ids in brackets):"
    )


def parse_citations(answer_text: str, included: list[RetrievedChunk]) -> list[str]:
    """Return chunk ids that appear in the answer AND were in the context.

    Falls back to nothing if the model cited ids we never supplied (prevents
    fabricated citations from being counted as valid — feeds the R3 rubric).
    """
    supplied = {c.chunk_id for c in included}
    cited = []
    for cid in _CHUNK_ID_RE.findall(answer_text):
        if cid in supplied and cid not in cited:
            cited.append(cid)
    return cited


class _Meter:
    """Accumulates generator calls, cost, and wall-clock latency."""

    def __init__(self):
        self.calls = 0
        self.cost = 0.0
        self._t0 = time.perf_counter()

    def add(self, res: GenResult) -> GenResult:
        self.calls += res.calls
        self.cost += res.cost_usd
        return res

    @property
    def latency_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0


class BaseSystem(ABC):
    """Base class for all six systems.

    Constructed once per run with shared ``retriever`` and ``generator`` so heavy
    models load a single time; :meth:`run` is then called per question. This
    honours the spec's ``(question, corpus, config)`` contract — ``config`` is
    held on the instance and ``run(question, corpus)`` supplies the rest.
    """

    name: SystemName

    def __init__(self, config: Config, retriever: Retriever, generator: Generator):
        self.config = config
        self.retriever = retriever
        self.generator = generator
        self.cfg = config.systems.get(self.name.value, {}) if hasattr(self, "name") else {}

    @abstractmethod
    def run(self, question: Question, corpus: str) -> AnswerRecord:
        ...

    # -- helpers --------------------------------------------------------------
    def _record(self, question: Question, corpus: str, answer: str,
                included: list[RetrievedChunk], meter: _Meter,
                retrieval_log: dict) -> AnswerRecord:
        return AnswerRecord(
            system_name=self.name.value,
            qid=question.qid,
            question=question.question,
            answer_text=answer,
            citations=parse_citations(answer, included),
            generator_calls=meter.calls,
            generator_cost_usd=round(meter.cost, 8),
            latency_ms=round(meter.latency_ms, 2),
            retrieval_log=retrieval_log,
            corpus=corpus,
            retrieved_chunks=included,
        )
