# Experiment protocol: OKF-hybrid retrieval across five RAG pipelines

Protocol version: 1.1 (amended before the clean v2 run)  
Prepared: 2026-08-02  
Experiment ID: `okf_wmp_paired_v2`  
Confirmatory corpus: PG&E 2026–2028 Base Wildfire Mitigation Plan (WMP)  
Direction of every reported contrast: **OKF-hybrid minus raw-vector**

This document is the analysis contract for the paid experiment. It must be
frozen, committed, and hashed before the confirmatory run. Any later change
must be recorded in a dated deviation log, including whether it was made before
or after anyone inspected condition-level results.

## 1. Objective and scope

The study tests whether one disclosed consumer of a pinned Open Knowledge
Format (OKF) v0.2 bundle changes retrieval effectiveness, answer quality, and
efficiency when substituted for raw-vector retrieval inside five existing RAG
pipelines.

The confirmatory systems are:

1. Simple RAG (`simple_rag`).
2. Reranked-Simple RAG (`reranked_simple`).
3. Agentic RAG (`agentic_rag`).
4. Self-RAG re-implementation (`self_rag`).
5. FLARE re-implementation (`flare`).

An in-house pipeline is withheld from execution, evaluation, tables, figures
and conclusions, and is not part of the public artifact. The experiment concerns
a knowledge representation and its consumer; it must not say that OKF replaces
RAG or vector databases.

The allowable causal claim is narrow:

> Under the frozen PG&E benchmark and implementation, replacing the raw-vector
> retrieval adapter with the disclosed OKF-hybrid adapter changed outcome *Y*
> by *Δ* (95% CI), while the remainder of pipeline *P* was held fixed.

The result does not establish an effect for OKF in general, other OKF producers
or consumers, other documents, or other RAG implementations.

## 2. Confirmatory design

The main experiment is a paired 5 × 2 factorial. Every question is evaluated in
both retrieval conditions within each pipeline.

| Pipeline | `raw_vector` | `okf_hybrid` |
|---|---|---|
| Simple RAG | Current pgvector dense top-k | Same vector discovery plus OKF mapping and bounded link expansion |
| Reranked-Simple | Current dense overfetch and cross-encoder rerank | OKF-hybrid candidates with the same cross-encoder and budget |
| Agentic RAG | Current critic/rewrite/retrieve loop | Same controller prompts and bounds; retrieval adapter changed |
| Self-RAG re-implementation | Current draft/reflect/retrieve/revise loop | Same loop and cap; retrieval adapter changed |
| FLARE re-implementation | Current active-retrieval approximation | Same loop and cap; retrieval adapter changed |

The experimental unit is one `(pipeline, qid)` pair. The analysis unit is the
question-level paired difference. Judge repeats and generator calls within a
question are not independent observations.

The primary estimand for pipeline *p* is:

```text
mean over answerable questions[
  correctness(p, q, okf_hybrid) - correctness(p, q, raw_vector)
]
```

The pooled effect across pipelines is secondary because it weights five
correlated observations from each question. Its confidence interval must
resample question IDs as clusters.

## 3. Frozen benchmark and source data

### 3.1 Question set

The confirmatory file is `data/benchmark_questions.json`, benchmark ID
`wmp_okf_pge_93_v2`. It is a deterministic derivation from:

- 35 questions from `evaluation/trial1_baseline/golden_test_set.json`.
- 65 questions from `evaluation/harmonized/wmp_questions.json`.

The frozen composition is 93 PG&E questions: 79 answerable questions and 14
unanswerable controls. Every record has a reference answer. All 79 answerable
questions have expected-page annotations. The benchmark also records
category, origin, table/image requirements, and multi-section requirements.

The benchmark SHA-256, record count, answerability counts, ordered QID hash, and
all source-file hashes must be written to the run manifest immediately before
execution. The run must abort if they differ from the preregistered manifest.

### 3.2 Gold audit, human validation, and versioning

Question metadata is not accepted as gold merely because it is present in a
legacy file. The planned safeguard was a two-reviewer, condition-blind human
audit against the source PDF before paid generation. That safeguard was not
fully completed before the partial v1 generation: an initial deterministic and
source-grounded review missed semantic defects, and blinded human validation is
still pending. This is a documented protocol deviation and must not be
described as completed or wholly pre-treatment. Before a final archival
release, human reviewers should:

- For each answerable question, confirm the reference answer and every expected
  page. Correct page-number mapping errors before freezing.
- For each unanswerable control, search the full eligible PG&E document and
  confirm that the requested fact is absent. Absence from a retrieved context is
  not evidence of corpus-level unanswerability.
- Detect semantic duplicates and contradictory labels across the two source
  sets. Resolve them before calculating benchmark counts.
- Record reviewer, decision, evidence page(s), and adjudication notes in a gold
  audit table. Reviewers must not inspect raw-versus-OKF outputs while doing
  this work.

The initial review removed `wmp_q59` (a contradictory near-duplicate of
`SF-002`), `wmp_q60` (duplicate of `wmp_q50`), and `wmp_q62` (duplicate of
`wmp_q51`), and corrected several false-negative labels. A later independent
source review found additional inherited page, reference, and unsupported-
synthesis defects before any automated judging. The partial v1 generation was
stopped and invalidated in full. Version 2 removes four artificial causal joins
(`wmp_q36`, `wmp_q38`, `wmp_q42`, and `wmp_q48`) and applies source-backed
question, reference, page, and metadata corrections recorded by QID in the
builder and audit report. Two independent model-assisted reviews cross-checked
the final v2 set; this is not represented as human validation. Human validation
remains pending and must be disclosed in any public draft.

If human validation changes any question, reference answer, answerability label,
or expected page, assign a new benchmark ID and content hash and rerun every
affected retrieval, generation, judging, and analysis artifact from clean
outputs. Never revise gold labels silently after inspecting results. If the
review confirms v2 unchanged, archive the blinded assignments, decisions, and
adjudication record with the release.

### 3.3 Corpus snapshot

Both arms use exactly one source snapshot:

- Document: `pge-2026-2028-base-wmp-vol1-r0.pdf`.
- Source PDF SHA-256:
  `e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a`.
- Corpus version: `pge_wmp_r0_20260719`.
- Extracted source passages: 654.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions.
- Source chunk target/overlap: 500/60 tokens.

The raw index and OKF bundle must be derived from this same 654-passage file.
No other utility corpus may be searched. Tenant filtering to `PGE` is required
and tested.

## 4. Treatment definition

### 4.1 Raw-vector condition

`raw_vector` is the existing pgvector condition. It uses the frozen source
passages, MiniLM embeddings, and each pipeline's existing retrieval/reranking
logic. The confirmatory defaults are top-k 10, dense overfetch 25 where
applicable, the local `cross-encoder/ms-marco-MiniLM-L-6-v2` reranker, and a
2,200-token final context budget.

### 4.2 OKF producer

The producer targets OKF v0.2 at specification commit
`3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`. It is deterministic and makes no
LLM calls. Each raw source chunk becomes one `Source Passage` concept with the
original text, chunk ID, page number, document name, corpus version, and source
hash preserved. Consecutive source passages are linked. The producer accepts no
questions, references, expected pages, or results.

This is intentionally a content-matched representation: OKF does not receive a
question-aware summary or manually curated semantic graph. Any observed main
effect is therefore attributable to the disclosed mapping/filter/traversal
behavior and its interaction with the fixed pipelines—not to extra private
knowledge.

Before execution, verify and archive:

- OKF version and specification commit.
- Producer source commit and version.
- Bundle manifest, source hashes, concept count, and whole-bundle content hash.
- One-to-one `(corpus, source_chunk_id)` mapping for all 654 source passages.
- No broken required provenance and no evaluation fields in concepts.
- Byte-identical output from two builds with identical declared inputs.

### 4.3 OKF-hybrid consumer

`okf_hybrid` uses the same dense retriever to obtain vector seeds. It maps seed
chunk IDs to their one-to-one OKF concepts, filters to the PG&E corpus, performs
bounded local traversal, and returns original source evidence in the existing
retriever shape. It makes no LLM call.

The treatment-defining parameters are frozen in `config/experiment.yaml` and
the adapter:

- For every dense-search request,
  `seed_k = max(1, min(top_k, ceil(top_k × 0.5)))`.
- The consumer retrieves those vector seeds, traverses bidirectional sequential
  OKF links to depth 1 with link decay 0.35, unions seeds and neighbors,
  score-sorts them with deterministic ID tie-breaking, and truncates to the
  requested `top_k`.
- A source concept that is already a direct seed remains depth zero and is not
  relabeled or score-inflated when reached from a neighboring seed.
- Corpus filtering is `PGE`; deprecated concepts are excluded.
- The final context is packed with the common token counter and 2,200-token
  budget. For a typical `top_k=10` request, five dense seeds enter the candidate
  union and link-expanded neighbors can occupy the remaining positions only if
  their decayed scores survive final ranking.

Changing any of these after confirmatory results are visible is a protocol
deviation, not routine tuning.

### 4.4 Held-equal components

Within each pipeline pair, hold constant:

- question text and allowed PG&E corpus;
- generator model ID, region, temperature, maximum output tokens, and system/user prompts;
- controller/reflection prompts and call caps;
- embedding and reranker models;
- final 2,200-token context budget and condition-neutral evidence renderer;
- citation instructions and source page/chunk identifiers;
- timeout, retry, and error policy;
- evaluator model, gold package, judge prompt, and parser;
- hardware/process allocation as far as practical.

The context *content* is expected to differ; selecting different evidence is the
treatment. Metadata/header tokens count toward the same final budget. The
generator prompt must not say `raw`, `OKF`, or reveal a condition label.

### 4.5 Secondary OKF-native condition

`okf_native` uses the disclosed weighted BM25 fields over OKF concepts followed
by the same bounded link traversal. Its retrieval and query-time efficiency
outcomes are secondary. After the frozen, no-LLM retrieval screen—but before any
paid answer generation—the team added an end-to-end `okf_native` run for all
five pipelines because its page-level retrieval results warranted checking
whether the gain transferred downstream. This answer-quality arm is explicitly
exploratory and data-motivated. It does not enter the 5 × 2 confirmatory family,
the five primary Holm-adjusted tests, or the main confirmatory answer table.

### 4.6 Post-hoc retrieval confound decomposition (diagnostic)

The frozen retrieval screen reported a large `okf_native` advantage over
`raw_vector` (page-hit 0.911 versus 0.658). That single contrast is **not
attributable to OKF**, because the two arms differ in three ways at once:

1. **Matching family.** `okf_native` ranks with BM25; `raw_vector` ranks with
   dense embeddings.
2. **Embedding capacity.** `raw_vector` uses `all-MiniLM-L6-v2`, whose input
   window is 256 word-piece tokens. Measured over the 654 PGE passages, 80.9%
   exceed that limit (median 398 tokens, maximum 2,035) and the encoder receives
   a median of only 64.4% of each passage, while BM25 indexes all of it. See
   `scripts/measure_embedding_truncation.py` and
   `results/embedding_truncation.json`.
3. **OKF itself.** Concept serialization, weighted frontmatter fields, and
   one-hop previous/next link traversal.

Reporting factor 3 as the cause of the whole difference would be wrong.
`scripts/run_retrieval_diagnostics.py` therefore varies one factor at a time
over the same corpus, questions, `top_k`, and page-level scoring:

| Arm | Isolates | OKF used? |
|---|---|---|
| `bm25_raw` | Lexical matching, nothing else | none |
| `titan_dense` | Dense retrieval without truncation (`amazon.titan-embed-text-v2:0`, 8192-token window) | none |
| `rrf_bm25_titan` | Conventional lexical+dense fusion (RRF, k=60) | none |
| `bm25_raw_adjacent` | One-hop adjacency delivered by chunk ordinal instead of OKF links | none |
| `titan_dense_adjacent` | The same adjacency on a fair dense arm | none |
| `okf_evidence_only` | The OKF consumer with frontmatter removed from the index | yes |

`bm25_raw` is a genuine non-OKF baseline: the producer writes each source chunk
into a concept without altering its text, and the release verifies that the
1,837 bundle passages are byte-identical to the pgvector rows, so BM25 over the
concept evidence and BM25 over the raw corpus index the same strings.

These arms are **diagnostic and exploratory**. They were specified and run after
the confirmatory retrieval screen, they do not alter the frozen `raw_vector`,
`okf_hybrid`, or `okf_native` records, and they are excluded from the
confirmatory Holm family. They carry their own Holm correction over the
diagnostic contrast family. Their purpose is attribution, not hypothesis
testing: the paper must not credit OKF for an effect these arms show is caused
by the matching family or by a truncated embedding baseline.

### 4.7 Topic-structured producer and the hybrid A/B (exploratory)

The confirmatory producer is chunk-preserving: one retrieval chunk becomes one
concept and the only links are previous/next. That is a minimal reading of OKF
and does not exercise what the format is for. Two additions test the format as
its documentation actually describes it. Both are **exploratory**, were specified
after the confirmatory retrieval screen, and carry their own Holm families.

**Topic-structured bundle** (`scripts/build_topic_okf_bundle.py`,
`data/okf_bundles/pge_topics_v0_2`). One concept per topic, nested, with real
relationships. Topics are not invented: the source PDF carries an embedded
outline of 1,006 entries to six levels, which is the author's own hierarchy.
Each concept's title is an outline heading verbatim, its body is the document
text between that heading and the next, located by the exact `(page, y)`
destination recorded for the entry, and its links are parent, child, previous and
next sibling, plus the cross-references the document itself makes. No text is
summarised, rewritten, or generated. The result is 1,011 concepts retaining
99.9% of the document's words, covering all 77 annotated answer pages, with a
verified content digest. PG&E only.

**Common-unit evaluation.** Topic concepts and chunks are different sizes, so a
matched `top_k` would favour whichever arm has larger units, because more text
trivially covers more pages. Every arm is therefore packed to the same 2,200-token
context budget, whole units only, and scored on what lands inside it. Units are
never truncated, since a truncated passage would otherwise earn page credit for
text that was not supplied.

**Hybrid A/B** (`scripts/run_hybrid_ab_experiment.py`). Arm A is a strong
conventional baseline: BM25 and dense retrieval over chunks, fused by reciprocal
rank, cross-encoder reranked. Arm B is **arm A plus one additional source**, a
lexical retriever over an OKF bundle, fused and reranked identically. Because B
differs from A only by the presence of the OKF source, the contrast estimates
what OKF adds on top of a baseline that is already good. Corpus, questions,
overfetch, reranker, context budget, generator, prompts, temperature and the
blinded gold-aware judge are fixed, and the pipeline is the repository's existing
`reranked_simple` system unmodified, so no generation or prompting difference can
explain a result. Two OKF variants are run (topic-structured and
chunk-preserving) so the granularity question is not begged.

This design is the user's requested A/B and is **not** what the OKF materials
describe. Those describe a pipeline in which OKF is the authored source that is
ingested into the retrieval stack; querying the vector store and the bundle in
parallel and merging the hits is a query-time fusion of our own construction.
The manuscript must say so and must not attribute the design to Google.

Because the bundle holds a verbatim copy of the same document, a fused context
can spend budget twice on the same words. The duplicate-token fraction is
recorded per question and must be reported alongside any gain.

## 5. Research questions and hypotheses

### 5.1 Primary question

For each of the five pipelines, does OKF-hybrid change gold-aware answer
correctness on answerable questions relative to raw-vector retrieval?

The five null hypotheses are `mean paired difference = 0`. The alternative is
two-sided. Although improvement is hoped for, two-sided testing permits an
honest negative result.

### 5.2 Key secondary questions

- Does OKF-hybrid change refusal accuracy on corpus-unanswerable controls?
- Does it change expected-page recall under the common context budget?
- Does it change answer completeness, groundedness, and citation quality?
- Does it change retrieval latency, end-to-end latency, generator calls, token
  use, or per-query generation cost?
- What one-time build time and storage overhead does the OKF bundle add?
- Does treatment effect vary by pipeline, question category, multi-section,
  table, or image requirement?

Subgroup and interaction results are exploratory unless explicitly promoted in
a preregistration before full execution.

## 6. Development, pilot, and confirmatory execution

### 6.1 Development isolation

Retriever tuning may use synthetic questions or a development set not contained
in the 93 confirmatory QIDs. Confirmatory questions, reference answers, and
expected pages must never be inputs to the OKF producer, link construction, or
ranking weights. The producer already rejects obvious evaluation fields; the
run manifest must also demonstrate that its only inputs were the corpus manifest
and source chunks.

### 6.2 Offline gates

Before a paid call:

1. Run the complete unit test suite.
2. Rebuild and verify the OKF bundle.
3. Verify raw/OKF source-ID and text equality for all concepts.
4. Verify tenant isolation and deterministic retrieval/tie breaking.
5. Verify benchmark semantic audit and hashes.
6. Validate AWS identity and model access without logging credentials.
7. Run mock-generator and mock-judge smoke tests through all five pipelines and
   both arms.
8. Confirm that output paths are new or explicitly resumable; never overwrite a
   completed run silently.

### 6.3 Pilot

Use a non-confirmatory development set for parameter tuning. After tuning is
closed, run a small paid smoke pilot to check API compatibility, schema success,
latency instrumentation, and cost. Do not select link depth, decay, or prompts
based on which arm wins on confirmatory questions.

The pilot report must include call counts, token counts, parse/retry rate by arm,
missing pairs, and a projected full-run cost. A pilot performance estimate is
diagnostic and is not combined with confirmatory results.

### 6.4 Full run and randomization

For every `(pipeline, qid)`, deterministically randomize whether `raw_vector` or
`okf_hybrid` runs first using the frozen seed. Block the schedule so conditions
and pipelines are interleaved over clock time; do not run all raw cells on one
day and all OKF cells later. Save the generated schedule before execution.

Use temperature 0 for all configured model calls. Provider determinism is not
assumed: record request IDs where available, exact model IDs, timestamps, token
usage, retry counts, and raw outputs. Resume only missing cells. A resume may not
regenerate successful cells unless the entire paired replicate is explicitly
rerun and versioned.

The expected main matrix is:

```text
93 questions × 5 pipelines × 2 retrieval arms = 930 answer records
```

An additional exploratory OKF-native matrix contains 93 × 5 = 465 records, for
1,395 generated answers in the combined artifact. Its contrasts use separately
named multiplicity families and are labeled exploratory throughout.

The actual total model-call count is larger because Agentic, Self-RAG, and FLARE
may call the generator more than once. Record both final-answer calls and
controller/reflection calls.

### 6.5 Historical outputs

Previous aggregate RAG numbers are sanity checks only. They cannot be subtracted
from new OKF aggregates for the primary claim. A historical raw answer may be
used as a secondary cost-saving comparison only if its question, corpus hash,
pipeline code/configuration, prompt, generator model, and per-question provenance
match; both historical and new answers must then be evaluated with the same
repaired gold-aware evaluator. Historical timing from a resumed or differently
configured run is not an admissible latency control.

The publication-grade primary analysis should use the interleaved paired run.

## 7. Outcome definitions

### 7.1 Answerable questions

The preregistered primary outcome is gold-aware **correctness**, on an integer
1–5 scale per valid judge trial. A substantive answer is scored against the
independent reference answer and canonical gold evidence. A refusal on a
gold-answerable question receives the predeclared floor score of 1 for
correctness and completeness. This is part of the endpoint definition, not a
fallback for malformed judge output.

Secondary answer outcomes are:

- completeness (1–5);
- groundedness in canonical source evidence (1–5);
- citation quality (1–5);
- substantive-answer rate;
- unsupported factual-claim count, if added to the frozen judge schema;
- exact-match or numeric tolerance checks for questions where a deterministic
  answer key can be expressed.

Groundedness and citation quality are structurally not applicable to a refusal.
Report their denominators and the substantive-answer rate; do not silently drop
refusals and imply an end-to-end citation benefit.

### 7.2 Unanswerable controls

Unanswerable controls are analyzed separately. The outcome is whether the
candidate refuses or clearly states that the PG&E corpus does not support the
requested fact. A substantive answer is incorrect even if it is plausible.
Correctness/completeness/groundedness/citation rubric values are `null` for these
items; they must not be averaged with answerable-question scores.

The main negative metric is refusal accuracy. Also report false-answer rate and
the exact denominator. With only 14 controls, emphasize confidence
intervals rather than strong null conclusions.

### 7.3 Retrieval outcomes

Retrieval is evaluated against expected PDF pages on the audited page-annotated
answerable set. Compute from the final packed context and, separately, from the
pre-packing candidate list:

- expected-page hit rate: at least one expected page retrieved;
- expected-page recall: unique expected pages retrieved divided by expected pages;
- complete-page coverage: every expected page retrieved;
- reciprocal rank of the first expected-page hit;
- recall at the fixed 2,200-token context budget;
- number of unique source pages and passages packed;
- for OKF-hybrid, seed versus link-expanded contribution and traversal path.

Deduplicate repeated chunks from the same expected page when computing page
recall. Use exact audited PDF-page identifiers; any mapping to printed page
labels must be frozen. Expected pages are a coarse relevance label, so describe
these measures as page-proxy retrieval metrics rather than passage-level truth.

### 7.4 Efficiency outcomes

Record, without combining into a proprietary composite:

- retrieval latency and end-to-end latency (median, p95, and paired difference);
- generator/controller calls per query;
- generator input/output tokens and total tokens;
- generation and judge cost using a dated, archived price table;
- raw-index build time and size;
- OKF build time, concept count, byte size, and any added index time;
- cold-start and warm-query latency, labeled separately;
- errors and retries by condition and pipeline.

One-time corpus construction cost must not be hidden inside or confused with
per-query serving cost. If amortized costs are reported, state the assumed query
volume and show unamortized values as well.

## 8. Gold-aware evaluator and judge protocol

The legacy judge is not used for primary scoring because it treats a system's
own retrieved context as the correctness reference and can replace malformed
outputs with neutral scores. The OKF trial evaluator is independent and
fail-closed.

### 8.1 Blinded input

Each judge item contains:

- an opaque randomized evaluation ID;
- the question and audited answerability label;
- the independent reference answer;
- canonical gold evidence resolved from audited source pages;
- the candidate answer;
- canonical source passages resolved from citations actually present in the
  candidate.

It must not contain pipeline name, condition name, run order, or a filename that
reveals the arm. Correctness is judged from the reference/gold package, never
only from self-retrieved context. Faithfulness to supplied context, if evaluated,
is a separate metric.

### 8.2 Strict schema

The required schema is `okf-trial-judge-v1`, implemented in
`src/okf_trial_data/evaluator.py`. The complete response must be one exact JSON
object. The parser rejects prose/fences, missing or extra keys, duplicate keys,
wrong evaluation IDs, strings or booleans masquerading as scores, fractional or
out-of-range scores, and non-finite values.

For an answerable substantive response, all four rubric scores must be integers
1–5. For a refusal or a gold-negative item, they must all be JSON `null`.

### 8.3 Trials, retries, and failures

Run three valid judge trials per answer using the pinned evaluator model and
temperature 0. Each trial gets one initial attempt and at most two schema-repair
attempts. A schema repair repeats evaluation of the original item; it is not a
new independent judge trial.

Persist every raw judge response, parser diagnostic, input/output token count,
cost, model ID, and attempt number. If all three attempts for a trial fail, that
trial remains missing and the answer is not assigned a midpoint or other score.
The confirmatory publication gate is 100% valid answer-level paired evaluation.
Resume missing judge cells until complete or disclose the study as incomplete.

Aggregate valid trial-level derived correctness scores to one answer-level mean
before pairing. On answerable items, each refusal trial contributes the
predeclared floor of 1. On controls, classify refusal by the majority of three
valid dispositions and retain the three-trial refusal fraction as a sensitivity
measure. Judge trials never increase inferential sample size.

### 8.4 Human validation

Before relying on the automated judge, select a blinded stratified sample across
pipeline, arm, answerability, benchmark origin, category, and automated score
range. A recommended minimum is 100 answer records (about 10% of the main matrix),
with deliberate oversampling of disagreements and controls. Two independent
annotators score the same rubric; disagreements receive adjudication.

Report weighted kappa or an ordinal agreement coefficient with a confidence
interval, exact agreement, and arm-specific confusion/error patterns. Correlation
alone is insufficient. If material differential judge bias by arm is found, use
human-adjudicated scoring for the affected primary cells or revise and uniformly
rerun the judge before unblinding final results.

## 9. Statistical analysis

### 9.1 Pair construction and completeness

Construct exact pairs by `(pipeline, qid)` and require one `raw_vector` and one
`okf_hybrid` observation for the endpoint. Reject duplicates, non-finite values,
withheld-pipeline rows, and incomplete pairs. The evaluator utilities enforce this
and do not perform silent listwise deletion.

Report a CONSORT-style accounting table even though this is a systems study:
planned cells, attempted cells, successful generations, judge attempts, schema
retries, persistent failures, and analyzed pairs by pipeline and arm.

### 9.2 Confirmatory family

For the primary answer-correctness endpoint, conduct five paired, two-sided
comparisons—one per pipeline—on the audited answerable questions. Use the
Wilcoxon signed-rank test as configured, while reporting the mean paired delta,
median paired delta, raw and arm means, and a 10,000-resample paired-question
bootstrap 95% confidence interval.

Apply Holm correction across the five primary p-values. Report both unadjusted
and adjusted p-values. Statistical significance requires adjusted `p < 0.05`;
the substantive interpretation must also consider effect magnitude and the
confidence interval.

Do not call a nonsignificant difference “equivalent” or “the same.” An
equivalence/non-inferiority claim requires a smallest effect size of interest
and an appropriate test frozen before results are inspected.

### 9.3 Negative-control and secondary families

For refusal accuracy, use paired binary outcomes and the exact McNemar test per
pipeline. Report discordant counts (`raw only correct`, `OKF only correct`) and
Wilson/Newcombe confidence intervals for paired differences. Holm-adjust the
five refusal-accuracy tests as their own key-secondary family.

For each other endpoint, keep the five per-pipeline comparisons in a clearly
named family and Holm-adjust within that family. Alternatively, label the entire
set exploratory and emphasize estimates/intervals. Never select a correction
family after seeing which p-values are favorable.

The pooled across-pipeline mean, if shown, must use a question-cluster bootstrap
so all five pipeline observations for a sampled QID move together. Pipeline ×
condition interactions may be estimated in a hierarchical model with a
question random intercept, but this is secondary and must respect the ordinal or
binary scale of the endpoint.

### 9.4 Missingness and sensitivity

Generation/API errors are retried under one frozen policy and then resumed as
missing cells; a score is never synthesized. Before publication, require a
complete primary pair matrix. If completion is impossible, report missingness by
arm and pipeline, do not claim a confirmatory result, and show best/worst-case
sensitivity bounds.

Structurally non-applicable values—citation scores for refusals and quality
scores for controls—are not parser failures and must not be mean-imputed.

### 9.5 Reproducible analysis output

The immutable per-question table must contain at least:

```text
run_id, pipeline, arm, qid, answerable, category, source_set,
question_hash, prompt_hash, corpus_hash, bundle_hash,
retrieved_source_ids, retrieved_pages, traversal_trace,
answer_text, citations, response_disposition,
correctness, completeness, groundedness, citation_quality,
generator_calls, input_tokens, output_tokens, retrieval_ms,
end_to_end_ms, generator_cost_usd, judge_cost_usd,
generation_status, judge_status, timestamps
```

Every aggregate, table, confidence interval, p-value, and figure must be
regenerable from this table and the frozen analysis script.

## 10. Quality-control and stopping rules

Stop before the full paid run if any of these gates fails:

- unresolved contradictory answerability/reference labels;
- benchmark, corpus, prompt, config, or model hash mismatch;
- question/gold leakage into the OKF producer;
- missing or duplicate source-to-concept mappings;
- inconsistent source text between raw and OKF concepts;
- tenant leakage outside PG&E;
- non-deterministic offline retrieval under identical inputs;
- a judge parser path that can assign neutral/default scores;
- the run schedule is not paired and interleaved;
- required environment credentials or model permissions fail the smoke test.

Do not stop a running condition early because interim results look favorable or
unfavorable. Cost or infrastructure stopping is allowed only by a rule set
before unblinding (for example, a hard dollar cap); retain all partial logs and
restart with a versioned continuation.

## 11. Reporting requirements

The paper must lead with absolute scores, paired effects, confidence intervals,
and denominators. Percentage change may appear only alongside the absolute
values and with a meaningful nonzero denominator.

Required main tables/figures are:

1. Per-pipeline raw and OKF correctness, paired delta, 95% CI, raw p-value, and
   Holm-adjusted p-value.
2. Expected-page retrieval metrics under the fixed token budget.
3. Refusal accuracy with discordant-pair counts.
4. Calls, tokens, latency, per-query cost, build time, and storage.
5. A forest plot of paired correctness effects by pipeline.
6. A quality–latency or quality–cost plot joining each pipeline's paired arms.

Always describe Self-RAG and FLARE as re-implementations. State that the study
uses one regulatory document, one producer, one consumer, one embedding model,
and sequential adjacency links rather than a manually curated semantic graph.
Do not generalize metadata/provenance/freshness benefits that the frozen consumer
does not actually use.

Null or negative results are publishable. The contribution is the controlled,
reproducible measurement.

## 12. Artifact and preregistration checklist

Before unblinding confirmatory results, archive:

- this protocol and its SHA-256;
- benchmark and gold-audit table with hashes;
- source manifest/chunks and legal redistribution note;
- OKF specification pin, producer/consumer code commit, bundle manifest/hash;
- experiment config and random execution schedule;
- environment lockfile and dependency versions;
- prompt/model/price manifests;
- offline test report and pilot cost report;
- analysis script with seeded resampling;
- empty results-table templates.

Preregister the protocol and analysis on OSF if feasible. After validation,
publish a versioned GitHub release and archive it in Zenodo. Reserve the DOI
only when artifact metadata, authorship, licenses, and release contents are
ready; never include secrets, proprietary credentials, or unlicensed source
PDFs in the public artifact.

## 13. Required deviations log

Append every deviation below; never edit prior entries silently.

| Date | Stage | Change | Reason | Results seen? | Consequence |
|---|---|---|---|---|---|
| 2026-08-02 | Initial pre-run audit | Removed `wmp_q59`, `wmp_q60`, and `wmp_q62`; corrected `wmp_q50`, `wmp_q51`, and `wmp_q56`; benchmark changed from 100 (80/20) to 97 (83/14) | Duplicate, contradictory, or false-negative inherited labels found during source audit | No answer-quality results | Produced v1, later superseded |
| 2026-08-02 | Pre-paid retrieval screen | Added an exploratory five-pipeline `okf_native` answer-generation arm (485 records) | Frozen retrieval-only results showed higher expected-page recall, motivating a downstream transfer check | Retrieval outcomes only; no paid answer or judge outcomes | Confirmatory 5×2 hypotheses remain unchanged; native answer results are exploratory and separately corrected |
| 2026-08-02 | Partial generation QC | Stopped and invalidated the v1 run after 609 of 1,455 answer cells; no judging was performed | Independent source review found inherited semantic gold errors that the lexical audit could not detect | Retrieval aggregates and isolated record-integrity checks only; no condition-level answer scores existed | Preserved under `results/superseded_gold_v1_partial`; excluded from every v2 result and release |
| 2026-08-02 | Pre-v2 freeze | Removed four unsupported synthetic joins and corrected source pages, references, wording, and task metadata; benchmark changed from 97 (83/14) to 93 (79/14) | Two independent model-assisted source reviews and cross-review identified and verified the defects | No v2 generation or answer-quality result | New benchmark ID/hash; retrieval, generation, judging, and analysis rerun from clean outputs; human validation still pending |
| 2026-08-02 | Confirmatory 5x2 generation halted | Stopped the confirmatory generation run at 1,254 of 1,395 cells ($25.65 spent) at the author's instruction; records retained and resumable | The author redirected the study to a topic-structured OKF producer on one document and to a hybrid-baseline A/B, judging the chunk-preserving 5x2 matrix no longer the question of interest | Retrieval outcomes seen; no judging or condition-level answer analysis had been performed on the halted run | The 5x2 confirmatory answer endpoints are unreported. Any future use of `results/full` must state that it is a partial run and re-derive the schedule; retrieval results are unaffected |
| 2026-08-02 | Topic-structured producer added | Built a second, topic-structured OKF bundle for PG&E from the PDF's own 1,006-entry outline (1,011 concepts, 6 levels, verbatim text) and evaluated it at a matched 2,200-token context budget; see §4.7 | The chunk-preserving producer does not exercise OKF's stated purpose, so a null for it could not speak to the format as documented | Confirmatory and diagnostic retrieval outcomes had been seen | Exploratory, own Holm family; the confirmatory records are unchanged |
| 2026-08-02 | Hybrid A/B added | Added an end-to-end A/B in which arm B is a strong hybrid baseline plus an OKF source, on PG&E with the `reranked_simple` pipeline; see §4.7 | Requested by the author to test OKF as an addition to a strong baseline rather than as a replacement for a weak one | Retrieval outcomes had been seen | Exploratory, own Holm family; design is the author's, not specified by the OKF materials, and must not be attributed to Google |
| 2026-08-02 | Comparison bug found and fixed | Corrected page crediting in the topic comparison: 266 of 654 chunks span two pages and were being credited with one, while OKF concepts carrying the same text were credited with both | Self-audit of the first topic-comparison run found an asymmetry that flattered the OKF arms | Yes, first-pass topic results had been seen and were discarded | Superseded numbers were not reported; all topic and A/B results come from the corrected run |
| 2026-08-02 | Post-retrieval-screen confound audit | Added six diagnostic retrieval arms (`bm25_raw`, `titan_dense`, `rrf_bm25_titan`, `bm25_raw_adjacent`, `titan_dense_adjacent`, `okf_evidence_only`) and a page-level nDCG measure; see §4.6 | The frozen `okf_native` versus `raw_vector` contrast confounded lexical-versus-dense matching, a 256-token embedding truncation affecting 80.9% of passages, and OKF itself, so no causal attribution to OKF was possible | Frozen retrieval outcomes had been seen; no answer-quality or judge results existed | Frozen confirmatory records unchanged and still authoritative; diagnostic arms are exploratory with their own Holm family; the paper attributes the retrieval difference to matching family and embedding capacity rather than to OKF |
