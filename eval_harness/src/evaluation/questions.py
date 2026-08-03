"""Question set loader and filters (Task 1.2).

Loads ``data/questions/multi_wmp_questions.json`` (generated from the CSV via
:func:`build_json_from_csv`). Supports filtering by utility, category, and
difficulty, and maps a ``qid`` to the corpus/corpora it must be answered from.

Cross-utility questions (e.g. ``SCE_PC``) carry multiple corpora; the *primary*
corpus is the first-named utility. Tenant-isolation scoping (R5) always uses a
single corpus, so runners iterate the ``corpora`` list explicitly when needed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, Field

from .models import Corpus

# Map every utility token that appears in the ``utility`` column to its corpora.
_UTILITY_TO_CORPORA: dict[str, list[Corpus]] = {
    "PGE": [Corpus.PGE],
    "SCE": [Corpus.SCE],
    "PC": [Corpus.PC],
    "SCE_PC": [Corpus.SCE, Corpus.PC],
    "PC_SCE": [Corpus.PC, Corpus.SCE],
    "PC_PGE": [Corpus.PC, Corpus.PGE],
    "PGE_PC": [Corpus.PGE, Corpus.PC],
    "PGE_SCE": [Corpus.PGE, Corpus.SCE],
    "SCE_PGE": [Corpus.SCE, Corpus.PGE],
}


def _corpora_for_utility(utility: str) -> list[Corpus]:
    if utility not in _UTILITY_TO_CORPORA:
        raise ValueError(f"unknown utility token: {utility!r}")
    return _UTILITY_TO_CORPORA[utility]


class Question(BaseModel):
    """One benchmark question with its metadata."""

    qid: str
    utility: str
    utility_short: str
    category: str
    difficulty: int
    topic: str
    topic2: str = ""
    question: str
    is_negative: bool = False
    is_table: bool = False
    is_image: bool = False
    corpora: list[str] = Field(default_factory=list)     # e.g. ["SCE", "PC"]
    primary_corpus: str = ""                              # e.g. "SCE"

    @property
    def is_cross_utility(self) -> bool:
        return len(self.corpora) > 1


def _to_bool(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def build_json_from_csv(csv_path: str | Path, json_path: str | Path) -> list[Question]:
    """Convert the source CSV into the canonical JSON question set.

    Derives ``corpora`` and ``primary_corpus`` from the ``utility`` column.
    Idempotent — safe to re-run.
    """
    csv_path, json_path = Path(csv_path), Path(json_path)
    questions: list[Question] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            corpora = _corpora_for_utility(row["utility"])
            questions.append(
                Question(
                    qid=row["qid"],
                    utility=row["utility"],
                    utility_short=row["utility_short"],
                    category=row["category"],
                    difficulty=int(row["difficulty"]),
                    topic=row["topic"],
                    topic2=row.get("topic2", "") or "",
                    question=row["question"],
                    is_negative=_to_bool(row["is_negative"]),
                    is_table=_to_bool(row["is_table"]),
                    is_image=_to_bool(row["is_image"]),
                    corpora=[c.value for c in corpora],
                    primary_corpus=corpora[0].value,
                )
            )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps([q.model_dump() for q in questions], indent=2, ensure_ascii=False)
    )
    return questions


class QuestionSet:
    """In-memory collection of questions with filtering helpers."""

    def __init__(self, questions: list[Question]):
        self._questions = questions
        self._by_id = {q.qid: q for q in questions}

    # -- construction ---------------------------------------------------------
    @classmethod
    def load(cls, json_path: str | Path, csv_fallback: str | Path | None = None) -> "QuestionSet":
        """Load from JSON; if missing and a CSV fallback is given, build it."""
        json_path = Path(json_path)
        if not json_path.exists() and csv_fallback is not None:
            build_json_from_csv(csv_fallback, json_path)
        data = json.loads(json_path.read_text())
        return cls([Question(**d) for d in data])

    # -- access ---------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._questions)

    def __iter__(self):
        return iter(self._questions)

    def all(self) -> list[Question]:
        return list(self._questions)

    def get(self, qid: str) -> Question:
        return self._by_id[qid]

    def get_corpus_for_question(self, qid: str) -> str:
        """Return the primary corpus id (PGE/SCE/PC) for a question."""
        return self._by_id[qid].primary_corpus

    def get_corpora_for_question(self, qid: str) -> list[str]:
        """Return all corpora a (possibly cross-utility) question spans."""
        return list(self._by_id[qid].corpora)

    def corpus_dir_for_question(self, qid: str) -> str:
        return Corpus(self.get_corpus_for_question(qid)).corpus_dir

    # -- filtering ------------------------------------------------------------
    def filter(
        self,
        *,
        corpus: Optional[str | Iterable[str]] = None,
        category: Optional[str | Iterable[str]] = None,
        difficulty: Optional[int | Iterable[int]] = None,
        is_negative: Optional[bool] = None,
        single_corpus_only: bool = False,
    ) -> "QuestionSet":
        """Return a new QuestionSet matching all supplied predicates.

        ``corpus`` matches if the question's *primary* corpus is in the set
        (single-utility) — for cross-utility questions the primary is the
        first-named utility. Use ``single_corpus_only=True`` to drop
        cross-utility questions entirely (useful for tenant-scoped runs).
        """
        def as_set(v):
            if v is None:
                return None
            return {v} if isinstance(v, (str, int)) else set(v)

        corpus_s = as_set(corpus)
        category_s = as_set(category)
        diff_s = as_set(difficulty)

        out = []
        for q in self._questions:
            if single_corpus_only and q.is_cross_utility:
                continue
            if corpus_s is not None and q.primary_corpus not in corpus_s:
                continue
            if category_s is not None and q.category not in category_s:
                continue
            if diff_s is not None and q.difficulty not in diff_s:
                continue
            if is_negative is not None and q.is_negative != is_negative:
                continue
            out.append(q)
        return QuestionSet(out)

    def pilot(self, n: int = 10, seed: int = 42) -> "QuestionSet":
        """A deterministic, class-balanced pilot subset for smoke tests.

        Picks a spread across corpora, difficulties, and negative/positive so
        the 10-question pilot exercises every code path (Acceptance Criteria).
        """
        import random

        rng = random.Random(seed)
        # Guarantee coverage: at least one negative and one of each corpus.
        picks: list[Question] = []
        seen: set[str] = set()

        def take(pred, k=1):
            pool = [q for q in self._questions if pred(q) and q.qid not in seen]
            rng.shuffle(pool)
            for q in pool[:k]:
                picks.append(q)
                seen.add(q.qid)

        take(lambda q: q.primary_corpus == "PGE" and not q.is_negative, 2)
        take(lambda q: q.primary_corpus == "SCE" and not q.is_negative, 2)
        take(lambda q: q.primary_corpus == "PC" and not q.is_negative, 2)
        take(lambda q: q.is_negative, 2)
        take(lambda q: q.is_cross_utility, 1)
        # Fill the rest arbitrarily but deterministically.
        take(lambda q: True, max(0, n - len(picks)))
        return QuestionSet(picks[:n])
