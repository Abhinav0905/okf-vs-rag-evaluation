"""Self-RAG baseline (re-implementation): retrieve -> generate -> reflect ->
[retrieve -> generate] (2-4 calls).

Approximates Asai et al. (2023) reflection tokens (ISREL / ISSUP / ISUSE): the
model drafts an answer, then a reflection call judges whether the answer is
supported and whether more retrieval is warranted. If not fully supported, it
retrieves more and revises. A final short reflection may run when budget allows.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from ..models import AnswerRecord, RetrievedChunk, SystemName
from ..questions import Question
from .base import BaseSystem, WMP_SYSTEM_PROMPT, build_answer_prompt, _Meter

_REFLECT_SYSTEM = (
    "You are the reflection module of a Self-RAG system. Given a question, the "
    "retrieved context, and a draft answer, emit reflection tokens as JSON: "
    '{"is_relevant": true|false, "is_supported": true|false, '
    '"needs_more_retrieval": true|false, "critique": "<one sentence>"}.'
)


def _extract_json(text: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None


class SelfRAG(BaseSystem):
    name = SystemName.SELF_RAG

    def run(self, question: Question, corpus: str) -> AnswerRecord:
        meter = _Meter()
        max_calls = self.cfg.get("max_calls", 4)
        top_k = self.config.retriever.top_k
        overfetch = self.config.retriever.overfetch_k

        # 1) initial retrieval + draft
        pool: dict[str, RetrievedChunk] = {
            h.chunk_id: h for h in self.retriever.dense_search(question.question, corpus, top_k=overfetch)
        }
        ranked = self.retriever.rerank(question.question, list(pool.values()), top_k=top_k)
        context, included = self.retriever.get_context(ranked, self.config.retriever.token_budget)
        draft = meter.add(self.generator.generate(
            build_answer_prompt(question.question, context), system=WMP_SYSTEM_PROMPT))
        answer = draft.text
        reflections: list[dict] = []
        revised = False

        # 2) reflect
        if meter.calls < max_calls:
            reflect_prompt = (
                f"Question: {question.question}\n\nContext:\n{context or 'NONE'}\n\n"
                f"Draft answer:\n{answer}\n\nEmit the reflection JSON."
            )
            r = meter.add(self.generator.generate(reflect_prompt, system=_REFLECT_SYSTEM, max_tokens=256))
            parsed = _extract_json(r.text) or {
                "is_relevant": True, "is_supported": False,
                "needs_more_retrieval": True, "critique": "fallback",
            }
            reflections.append(parsed)

            # 3) if unsupported / needs more -> expand retrieval and revise
            needs_more = parsed.get("needs_more_retrieval") or not parsed.get("is_supported", True)
            if needs_more and meter.calls < max_calls:
                exp_query = f"{question.question} {question.topic} {question.topic2}".strip()
                for h in self.retriever.dense_search(exp_query, corpus, top_k=overfetch):
                    pool.setdefault(h.chunk_id, h)
                ranked = self.retriever.rerank(question.question, list(pool.values()), top_k=top_k)
                context, included = self.retriever.get_context(ranked, self.config.retriever.token_budget)
                rev = meter.add(self.generator.generate(
                    build_answer_prompt(question.question, context), system=WMP_SYSTEM_PROMPT))
                answer = rev.text
                revised = True

        log = {
            "strategy": "self_rag_reflect",
            "reflections": reflections,
            "revised": revised,
            "pool_size": len(pool),
            "n_in_context": len(included),
        }
        return self._record(question, corpus, answer, included, meter, log)
