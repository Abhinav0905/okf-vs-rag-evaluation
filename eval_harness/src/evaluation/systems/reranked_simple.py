"""Reranked-Simple baseline: dense -> cross-encoder rerank -> generator (1 call)."""

from __future__ import annotations

from ..models import AnswerRecord, SystemName
from ..questions import Question
from .base import BaseSystem, WMP_SYSTEM_PROMPT, build_answer_prompt, _Meter


class RerankedSimple(BaseSystem):
    name = SystemName.RERANKED_SIMPLE

    def run(self, question: Question, corpus: str) -> AnswerRecord:
        meter = _Meter()
        overfetch = self.cfg.get("overfetch_k", self.config.retriever.overfetch_k)
        top_k = self.cfg.get("top_k", self.config.retriever.top_k)

        candidates = self.retriever.dense_search(question.question, corpus, top_k=overfetch)
        reranked = self.retriever.rerank(question.question, candidates, top_k=top_k)
        context, included = self.retriever.get_context(reranked, self.config.retriever.token_budget)
        res = meter.add(self.generator.generate(
            build_answer_prompt(question.question, context), system=WMP_SYSTEM_PROMPT))

        log = {
            "strategy": "dense_rerank_topk",
            "overfetch_k": overfetch,
            "top_k": top_k,
            "n_retrieved": len(candidates),
            "n_in_context": len(included),
            "rerank_scores": [round(h.rerank_score, 4) for h in included if h.rerank_score is not None],
        }
        return self._record(question, corpus, res.text, included, meter, log)
