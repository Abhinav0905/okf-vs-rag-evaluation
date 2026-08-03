"""Agentic RAG baseline: LLM-driven retrieve/judge/rewrite loop (3-8 calls).

Loop: retrieve -> LLM critic decides {sufficient?, refined_query} -> if
insufficient, rewrite and re-retrieve -> ... -> final LLM answer. The critic and
the answer are separate generator calls, so total calls vary with difficulty.

Bounds (Acceptance Criteria): >= ``min_calls`` (3) and <= ``max_calls`` (8).
When the critic response can't be parsed as JSON (e.g. the offline mock
generator), a deterministic schedule keeps the loop bounded and the call count
in range.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ..models import AnswerRecord, RetrievedChunk, SystemName
from ..questions import Question
from .base import BaseSystem, WMP_SYSTEM_PROMPT, build_answer_prompt, _Meter

_CRITIC_SYSTEM = (
    "You are a retrieval controller for a WMP question-answering system. Given a "
    "question and the currently retrieved context, decide whether the context is "
    "sufficient to answer completely. Respond ONLY with JSON: "
    '{"sufficient": true|false, "refined_query": "<a better search query if not '
    'sufficient, else empty>", "reasoning": "<one sentence>"}.'
)


def _extract_json(text: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


class AgenticRAG(BaseSystem):
    name = SystemName.AGENTIC_RAG

    def run(self, question: Question, corpus: str) -> AnswerRecord:
        meter = _Meter()
        max_calls = self.cfg.get("max_calls", 8)
        min_calls = self.cfg.get("min_calls", 3)
        overfetch = self.config.retriever.overfetch_k
        top_k = self.config.retriever.top_k

        query = question.question
        pool: dict[str, RetrievedChunk] = {}
        rewrites: list[str] = []
        decisions: list[dict] = []

        # Reserve one call for the final answer.
        max_critic = max(1, max_calls - 1)
        min_critic = max(1, min_calls - 1)

        for i in range(max_critic):
            hits = self.retriever.dense_search(query, corpus, top_k=overfetch)
            for h in hits:
                pool.setdefault(h.chunk_id, h)
            current = self.retriever.rerank(question.question, list(pool.values()), top_k=top_k)
            ctx, _ = self.retriever.get_context(current, self.config.retriever.token_budget)

            critic_prompt = (
                f"Question: {question.question}\n\nCurrent context:\n{ctx or 'NONE'}\n\n"
                f"Is this sufficient? Respond with the JSON schema."
            )
            res = meter.add(self.generator.generate(critic_prompt, system=_CRITIC_SYSTEM,
                                                    max_tokens=256))
            parsed = _extract_json(res.text)
            if parsed is None:
                # Offline / unparseable: deterministic schedule.
                parsed = {"sufficient": (i + 1) >= min_critic,
                          "refined_query": f"{question.question} {question.topic} {question.utility_short}",
                          "reasoning": "fallback schedule"}
            decisions.append(parsed)

            sufficient = bool(parsed.get("sufficient")) and (i + 1) >= min_critic
            if sufficient:
                break
            rq = (parsed.get("refined_query") or "").strip()
            query = rq or f"{question.question} {question.topic}"
            rewrites.append(query)

        final = self.retriever.rerank(question.question, list(pool.values()), top_k=top_k)
        context, included = self.retriever.get_context(final, self.config.retriever.token_budget)
        ans = meter.add(self.generator.generate(
            build_answer_prompt(question.question, context), system=WMP_SYSTEM_PROMPT))

        log = {
            "strategy": "agentic_loop",
            "critic_iterations": len(decisions),
            "rewrites": rewrites,
            "decisions": decisions,
            "pool_size": len(pool),
            "n_in_context": len(included),
        }
        return self._record(question, corpus, ans.text, included, meter, log)
