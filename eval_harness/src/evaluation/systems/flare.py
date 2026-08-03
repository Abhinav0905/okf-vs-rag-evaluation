"""FLARE baseline (re-implementation): forward-looking active retrieval (2-3 calls).

Approximates Jiang et al. (2023): draft a forward-looking answer, then use the
anticipated content as a new retrieval query to fetch better evidence, and
regenerate. If the draft signals low confidence (hedging / refusal), a second
active-retrieval round runs, capped at ``max_calls`` (3).
"""

from __future__ import annotations

from ..models import AnswerRecord, RetrievedChunk, SystemName
from ..questions import Question
from .base import BaseSystem, WMP_SYSTEM_PROMPT, build_answer_prompt, _Meter

_LOW_CONF_MARKERS = (
    "does not contain sufficient", "not contain sufficient", "unclear",
    "might", "may ", "possibly", "not sure", "cannot", "no information",
)


class FLARE(BaseSystem):
    name = SystemName.FLARE

    def _low_confidence(self, text: str) -> bool:
        t = text.lower()
        return any(m in t for m in _LOW_CONF_MARKERS)

    def run(self, question: Question, corpus: str) -> AnswerRecord:
        meter = _Meter()
        max_calls = self.cfg.get("max_calls", 3)
        top_k = self.config.retriever.top_k
        overfetch = self.config.retriever.overfetch_k

        pool: dict[str, RetrievedChunk] = {
            h.chunk_id: h for h in self.retriever.dense_search(question.question, corpus, top_k=overfetch)
        }
        ranked = self.retriever.rerank(question.question, list(pool.values()), top_k=top_k)
        context, included = self.retriever.get_context(ranked, self.config.retriever.token_budget)

        # 1) forward-looking draft
        draft = meter.add(self.generator.generate(
            build_answer_prompt(question.question, context), system=WMP_SYSTEM_PROMPT))
        answer = draft.text
        rounds = []

        # 2..N) active retrieval using the anticipated answer as the query
        while meter.calls < max_calls:
            lookahead_query = f"{question.question} {answer[:300]}"
            new_hits = self.retriever.dense_search(lookahead_query, corpus, top_k=overfetch)
            before = len(pool)
            for h in new_hits:
                pool.setdefault(h.chunk_id, h)
            ranked = self.retriever.rerank(question.question, list(pool.values()), top_k=top_k)
            context, included = self.retriever.get_context(ranked, self.config.retriever.token_budget)
            regen = meter.add(self.generator.generate(
                build_answer_prompt(question.question, context), system=WMP_SYSTEM_PROMPT))
            rounds.append({"added_chunks": len(pool) - before, "low_conf": self._low_confidence(answer)})
            answer = regen.text
            if not self._low_confidence(answer):
                break

        log = {
            "strategy": "flare_active_retrieval",
            "active_rounds": len(rounds),
            "rounds": rounds,
            "pool_size": len(pool),
            "n_in_context": len(included),
        }
        return self._record(question, corpus, answer, included, meter, log)
