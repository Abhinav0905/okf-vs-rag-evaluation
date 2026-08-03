"""Simple RAG baseline: dense retrieval -> top-k -> generator (1 call)."""

from __future__ import annotations

from ..models import AnswerRecord, SystemName
from ..questions import Question
from .base import BaseSystem, WMP_SYSTEM_PROMPT, build_answer_prompt, _Meter


class SimpleRAG(BaseSystem):
    name = SystemName.SIMPLE_RAG

    def run(self, question: Question, corpus: str) -> AnswerRecord:
        meter = _Meter()
        top_k = self.cfg.get("top_k", self.config.retriever.top_k)

        hits = self.retriever.dense_search(question.question, corpus, top_k=top_k)
        context, included = self.retriever.get_context(hits, self.config.retriever.token_budget)
        res = meter.add(self.generator.generate(
            build_answer_prompt(question.question, context), system=WMP_SYSTEM_PROMPT))

        log = {
            "strategy": "dense_topk",
            "top_k": top_k,
            "n_retrieved": len(hits),
            "n_in_context": len(included),
            "dense_scores": [round(h.score, 4) for h in included],
        }
        return self._record(question, corpus, res.text, included, meter, log)
