# Cross-review and freeze record for `wmp_okf_pge_93_v2`

Date: 2026-08-02  
Benchmark SHA-256: `edf8b8a7437543c36eef1f4c22f774f11c8bdb4a13574b6ee9154c922a66742d`  
Source PDF SHA-256: `e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a`

## Review design

Two independent model-assisted source reviews divided the inherited benchmark, then cross-reviewed one another's corrected items against the canonical PG&E source passages. Neither review used per-question retrieval-condition outcomes or answer-quality scores. This procedure is an engineering quality-control review, not human annotation; human validation remains pending.

## Final decision

Freeze pass for the clean v2 run:

- 93 unique questions: 79 answerable and 14 corpus-unanswerable controls.
- All 79 answerable questions have source-backed expected PDF pages.
- All controls have empty expected-page lists and source-bounded refusal references.
- Exactly seven inherited QIDs are omitted: three duplicates or contradictory controls (`wmp_q59`, `wmp_q60`, `wmp_q62`) and four unsupported synthetic joins (`wmp_q36`, `wmp_q38`, `wmp_q42`, `wmp_q48`).
- No new QIDs were added and no duplicate QIDs remain.
- A clean build to a separate temporary path was byte-identical.
- The deterministic page/lexical audit reports 79/79 page coverage and zero flags.
- The package test suite reports 31 passed tests.

## Material corrections confirmed by cross-review

The cross-review verified corrections to evidence pages, reference scope, or task wording for `SF-006`, `TB-006`, `CS-002`, `CS-004`, `CS-005`, `MH-002`, `IF-002`, `IF-003`, `NEG-004`, `wmp_q9`, `wmp_q14`, `wmp_q35`, `wmp_q37`, `wmp_q39`, `wmp_q40`, `wmp_q41`, `wmp_q43` through `wmp_q47`, `wmp_q49` through `wmp_q51`, and `wmp_q56`. The exact final question, reference, page, metadata, and curation-note values are generated deterministically by `scripts/build_benchmark.py` and stored in `data/benchmark_questions.json`.

The first-pass defect analysis and source-chunk rationale are preserved in `protocol/GOLD_AUDIT_REVIEW.md`. The superseded v1 benchmark and audit files are preserved under `protocol/superseded/wmp_okf_pge_97_v1/`. The 609-cell v1 partial generation is invalidated in full under `results/superseded_gold_v1_partial/` and must never enter v2 judging or analysis.

## Remaining publication gate

The benchmark is frozen for the controlled v2 system run, but `human_validation_status` remains `pending`. Before strong public claims based on the automated rubric, the author should complete the blinded human-validation sample described in the experiment protocol or retain the limitation prominently in the preprint.
