"""SQLite persistence for answers and judge scores (Task 5).

One clean schema that supports the full 410-question x 6-system x 3-corpus run
plus incremental resumption (``INSERT OR REPLACE`` on the natural key
(system_name, qid)). Also exports per-question JSONL for release.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from .models import AnswerRecord, JudgeResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS answers (
    system_name        TEXT NOT NULL,
    qid                TEXT NOT NULL,
    corpus             TEXT NOT NULL,
    question           TEXT NOT NULL,
    answer_text        TEXT NOT NULL,
    citations          TEXT NOT NULL,      -- json list[str]
    generator_calls    INTEGER NOT NULL,
    generator_cost_usd REAL NOT NULL,
    latency_ms         REAL NOT NULL,
    retrieval_log      TEXT,               -- json
    retrieved_chunks   TEXT,               -- json list[RetrievedChunk]
    timestamp          TEXT NOT NULL,
    PRIMARY KEY (system_name, qid)
);
CREATE TABLE IF NOT EXISTS judge_scores (
    system_name     TEXT NOT NULL,
    qid             TEXT NOT NULL,
    corpus          TEXT NOT NULL,
    n_trials        INTEGER NOT NULL,
    R1 REAL, R2 REAL, R3 REAL, G1 REAL, G2 REAL, G3 REAL,
    retrieval_mean  REAL NOT NULL,
    generation_mean REAL NOT NULL,
    score_std       REAL NOT NULL,
    judge_model     TEXT,
    total_cost_usd  REAL NOT NULL,
    trials          TEXT,                  -- json list[JudgeTrial]
    PRIMARY KEY (system_name, qid)
);
CREATE TABLE IF NOT EXISTS run_meta (
    key TEXT PRIMARY KEY, value TEXT
);
CREATE INDEX IF NOT EXISTS answers_sys_corpus ON answers (system_name, corpus);
CREATE INDEX IF NOT EXISTS judge_sys_corpus ON judge_scores (system_name, corpus);
"""


class Store:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # -- writes ---------------------------------------------------------------
    def save_answer(self, rec: AnswerRecord) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO answers
               (system_name, qid, corpus, question, answer_text, citations,
                generator_calls, generator_cost_usd, latency_ms, retrieval_log,
                retrieved_chunks, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec.system_name, rec.qid, rec.corpus, rec.question, rec.answer_text,
             json.dumps(rec.citations), rec.generator_calls, rec.generator_cost_usd,
             rec.latency_ms, json.dumps(rec.retrieval_log),
             json.dumps([c.model_dump() for c in rec.retrieved_chunks]),
             rec.timestamp.isoformat()),
        )
        self.conn.commit()

    def save_judge(self, jr: JudgeResult) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO judge_scores
               (system_name, qid, corpus, n_trials, R1,R2,R3,G1,G2,G3,
                retrieval_mean, generation_mean, score_std, judge_model,
                total_cost_usd, trials)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (jr.system_name, jr.qid, jr.corpus, jr.n_trials, jr.R1, jr.R2, jr.R3,
             jr.G1, jr.G2, jr.G3, jr.retrieval_mean, jr.generation_mean, jr.score_std,
             jr.judge_model, jr.total_cost_usd,
             json.dumps([t.model_dump() for t in jr.trials])),
        )
        self.conn.commit()

    def set_meta(self, key: str, value) -> None:
        self.conn.execute("INSERT OR REPLACE INTO run_meta VALUES (?,?)",
                          (key, json.dumps(value)))
        self.conn.commit()

    # -- reads ----------------------------------------------------------------
    def has_answer(self, system_name: str, qid: str) -> bool:
        r = self.conn.execute(
            "SELECT 1 FROM answers WHERE system_name=? AND qid=?", (system_name, qid)
        ).fetchone()
        return r is not None

    def has_judge(self, system_name: str, qid: str) -> bool:
        r = self.conn.execute(
            "SELECT 1 FROM judge_scores WHERE system_name=? AND qid=?", (system_name, qid)
        ).fetchone()
        return r is not None

    def get_answer(self, system_name: str, qid: str) -> Optional[AnswerRecord]:
        row = self.conn.execute(
            "SELECT * FROM answers WHERE system_name=? AND qid=?", (system_name, qid)
        ).fetchone()
        return _row_to_answer(row) if row else None

    def iter_answers(self) -> Iterable[AnswerRecord]:
        for row in self.conn.execute("SELECT * FROM answers"):
            yield _row_to_answer(row)

    def judge_rows(self, system_name: Optional[str] = None,
                   corpus: Optional[str] = None) -> list[dict]:
        q = "SELECT * FROM judge_scores"
        clauses, args = [], []
        if system_name:
            clauses.append("system_name=?"); args.append(system_name)
        if corpus:
            clauses.append("corpus=?"); args.append(corpus)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        return [dict(r) for r in self.conn.execute(q, args)]

    def answer_rows(self, system_name: Optional[str] = None,
                    corpus: Optional[str] = None) -> list[dict]:
        q = "SELECT * FROM answers"
        clauses, args = [], []
        if system_name:
            clauses.append("system_name=?"); args.append(system_name)
        if corpus:
            clauses.append("corpus=?"); args.append(corpus)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        return [dict(r) for r in self.conn.execute(q, args)]

    def export_jsonl(self, path: str | Path) -> int:
        """Export joined answer+judge records for release."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with path.open("w") as fh:
            rows = self.conn.execute(
                """SELECT a.*, j.retrieval_mean, j.generation_mean, j.score_std,
                          j.R1,j.R2,j.R3,j.G1,j.G2,j.G3, j.judge_model
                   FROM answers a LEFT JOIN judge_scores j
                   ON a.system_name=j.system_name AND a.qid=j.qid"""
            )
            for row in rows:
                d = dict(row)
                for k in ("citations", "retrieval_log", "retrieved_chunks"):
                    if d.get(k):
                        d[k] = json.loads(d[k])
                fh.write(json.dumps(d) + "\n")
                n += 1
        return n

    def close(self):
        self.conn.close()


def _row_to_answer(row: sqlite3.Row) -> AnswerRecord:
    from .models import RetrievedChunk

    d = dict(row)
    return AnswerRecord(
        system_name=d["system_name"], qid=d["qid"], corpus=d["corpus"],
        question=d["question"], answer_text=d["answer_text"],
        citations=json.loads(d["citations"]),
        generator_calls=d["generator_calls"], generator_cost_usd=d["generator_cost_usd"],
        latency_ms=d["latency_ms"],
        retrieval_log=json.loads(d["retrieval_log"]) if d["retrieval_log"] else None,
        retrieved_chunks=[RetrievedChunk(**c) for c in json.loads(d["retrieved_chunks"] or "[]")],
        timestamp=datetime.fromisoformat(d["timestamp"]),
    )
