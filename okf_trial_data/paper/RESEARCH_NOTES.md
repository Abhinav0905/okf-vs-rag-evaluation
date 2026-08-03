# Research foundation: OKF v0.2 as a retrieval substrate for RAG

Status: living design, audit, and manuscript notes  
Prepared: 2026-08-02  
Intended venue framing: arXiv `cs.IR` (primary), with `cs.CL` as a possible cross-list  
Results policy: no numerical result or performance conclusion belongs in the paper until it is produced by the corrected v2 protocol described below.

### Benchmark-integrity amendment

The operative confirmatory benchmark is `wmp_okf_pge_93_v2`: 93 questions
(79 answerable and 14 unanswerable controls), SHA-256
`edf8b8a7437543c36eef1f4c22f774f11c8bdb4a13574b6ee9154c922a66742d`.
It supersedes `wmp_okf_pge_97_v1`. A paid v1 generation run was stopped after
609 of 1,455 scheduled answer cells when a source review identified inherited
semantic gold errors that the earlier lexical audit had missed. No automated
judging or condition-level answer analysis was performed on that partial run;
its records are retained only as an invalidated audit artifact and must never
enter v2 results or the public release.

The v2 question, reference, page, and metadata corrections were completed and
hashed before the clean restart and before any automated judging or
condition-level answer analysis. The deterministic audit verifies page
availability and lexical support, and two independent model-assisted reviews
cross-checked the source corrections. These checks are not blinded human
validation. Human validation remains pending and must be disclosed in every
public draft until completed. Consequently, the paper must not describe the
final benchmark as having been frozen before *all* paid generation.

### Retrieval-confound amendment

The frozen retrieval screen showed `okf_native` at 0.911 page-hit against
`raw_vector` at 0.658 (exact McNemar p = 8.8e-5). **That difference must not be
reported as an OKF effect.** The two arms differ simultaneously in matching
family (BM25 versus dense), in embedding capacity, and in OKF content, so the
contrast identifies none of the three.

Two measurements settle the attribution:

1. `all-MiniLM-L6-v2`, the frozen dense encoder, truncates input at 256
   word-piece tokens. Measured over the 654 PGE passages, 80.9% exceed that
   limit (median 398 tokens, maximum 2,035), and the encoder receives a median
   of only 64.4% of each passage. BM25 indexes every token. The baseline was
   handicapped by configuration, not out-competed. The figures are produced by
   `scripts/measure_embedding_truncation.py` into
   `results/embedding_truncation.json`; the manuscript reads them from there.
2. Plain BM25 over the unmodified pgvector chunks — **no concepts, no
   frontmatter, no links, no OKF whatsoever** — reaches 0.975 page-hit, i.e.
   *above* `okf_native`'s 0.911. Against plain BM25, the OKF consumer is worse
   on expected-page recall (paired delta −0.070, 95% CI [−0.133, −0.013]).

The OKF component that the treatment actually adds — reserving half of the
result budget for one-hop previous/next passages — costs recall, because those
slots would otherwise hold better-matching passages. Reproducing the same
adjacency from chunk ordinals instead of OKF links reproduces the same loss
(−0.051, 95% CI [−0.108, +0.006]), which shows the mechanism is budget
displacement rather than anything specific to OKF. Frontmatter contributes
essentially nothing (−0.019, 95% CI [−0.051, 0.000]).

Consequences for the manuscript:

- The confirmatory contrast (`raw_vector` versus `okf_hybrid`) is a **null**:
  page-hit 0.658 versus 0.633, p = 0.73, recall delta −0.013, 95% CI
  [−0.076, +0.049]. Report it as a null, not as a trend.
- Never present the `okf_native`-versus-`raw_vector` gap as evidence about OKF.
  Whenever it appears, it must appear beside `bm25_raw` and `titan_dense`.
- The honest headline is that a chunk-preserving OKF producer with an
  adjacency-aware consumer **did not improve retrieval on this benchmark**, and
  that the apparent improvement decomposes into a lexical-matching effect plus a
  misconfigured dense baseline. This is a negative and corrective result. It is
  the finding, not a failure of the study.
- The paper should state plainly that this is consistent with the specification's
  own non-goals: OKF v0.2 does not define a retriever, so no retrieval gain
  should have been expected from serialization alone.
- The weak dense baseline is a limitation of the frozen configuration and is
  disclosed as such. `titan_dense` (8192-token window) is reported as the fair
  dense comparison, and it was added post hoc.

## 1. Scope and paper identity

This is a retrieval and RAG evaluation paper. An in-house pipeline is withheld from it entirely.

The confirmatory system set is:

1. Simple RAG.
2. Reranked-Simple RAG.
3. Agentic RAG.
4. Self-RAG **re-implementation**.
5. FLARE **re-implementation**.

The withheld in-house pipeline appears in no experiment, table, figure, comparison, or claim in this paper.

### Recommended title

**Open Knowledge Format v0.2 as a Retrieval Substrate: A Controlled Evaluation Across Five RAG Pipelines**

This title is neutral, names the pinned version, and does not imply that OKF is itself a retriever or that an improvement has already been observed.

### Acceptable alternatives

- **Does the Open Knowledge Format Improve Retrieval-Augmented Generation? A Controlled Study Across Five RAG Pipelines**
- **From Document Chunks to Linked Knowledge Concepts: Evaluating OKF v0.2 in Retrieval-Augmented Generation**
- **Structured Knowledge or Vector Chunks? A Paired Evaluation of OKF-Enhanced RAG**

Avoid titles containing “replaces RAG,” “replaces vector databases,” “RAG killer,” “breakthrough,” “state of the art,” or “productivity gain.” None is supported by the specification or by evidence available before the experiment.

### One-sentence paper thesis

The paper tests whether a chunk-preserving OKF v0.2 producer plus a deterministic previous/next-passage adjacency consumer changes the effectiveness–efficiency trade-off of five existing RAG pipelines when source evidence, questions, generator, prompts, context budget, and evaluation protocol are held fixed.

### Suggested keywords

Retrieval-augmented generation; information retrieval; Open Knowledge Format; structured knowledge; hybrid retrieval; graph traversal; provenance; RAG evaluation; document question answering.

## 2. What OKF is—and what this experiment can test

Google Cloud introduced OKF as a vendor-neutral representation format for portable knowledge bundles. In v0.2, a bundle is a directory tree of Markdown concept documents with YAML frontmatter. `type` is the only universally required concept field. Directory hierarchy, `index.md` files, ordinary Markdown links, source provenance, verification, status, and staleness fields can provide machine-readable signals to a consumer.

OKF does **not** prescribe a storage engine, query engine, retriever, ranking function, graph algorithm, embedding model, agent framework, or serving runtime. The v0.2 specification explicitly lists storage, serving, and query infrastructure as non-goals and identifies search indexes as valid consumers. Therefore:

- The independent variable is not “OKF versus RAG.” OKF is a knowledge representation that can be consumed inside RAG.
- The experiment evaluates **one disclosed, chunk-preserving OKF producer and one disclosed, adjacency-aware consumer**. Each existing source chunk becomes one `Source Passage` concept with unchanged evidence text and deterministic links only to consecutive passages in the same document.
- Any causal language must name the implemented treatment: for example, “the pinned chunk-preserving producer and one-hop adjacency consumer changed evidence recall in this benchmark,” not “OKF improves retrieval.”
- A vector index may still be used to seed discovery over OKF concepts. That is compatible with OKF and should be described openly.
- The confirmatory hybrid consumer does not test semantic concept re-authoring, an entity graph, arbitrary cross-concept links, trust/freshness reasoning, or general frontmatter-aware routing. Those capabilities must not be credited for an observed effect.

### Specification pin

All production, validation, experiments, and paper claims must target exactly:

- Format: Open Knowledge Format v0.2.
- Repository commit: `3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`.
- Immutable specification: [OKF v0.2 `SPEC.md` at the pinned commit](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md).
- SHA-256 of the raw pinned `SPEC.md`: `5a3311d270bebb16d558010e75064f5b75323f284992641732b1c8097511f948`.
- Date verified: 2026-08-02.

The bundle-root `index.md` should declare `okf_version: "0.2"`. Experiment code and the manuscript must never cite `main` as the operative specification. Later OKF versions are future work unless a separately preregistered replication is run.

## 3. Research gap and contribution framing

The RAG literature establishes dense passage retrieval, reranking, iterative retrieval, self-reflection, and graph-assisted retrieval. OKF v0.2 standardizes a portable, linked, provenance-bearing representation, but its official specification deliberately leaves consumption behavior open. The scientific gap is consequently not whether files can be written in OKF. This study asks the narrower question of whether deterministic local adjacency, exposed through one chunk-preserving conformant bundle and consumer, produces measurable benefits when inserted into otherwise fixed RAG pipelines, and what computational costs accompany those benefits.

A targeted web search on 2026-08-02 found the official specification, official launch materials, community implementations, and informal OKF-versus-RAG articles, but did not identify a peer-reviewed controlled OKF retrieval benchmark. This is a search note, not proof of priority. Before submission, repeat a documented scholarly search in Google Scholar, Semantic Scholar, arXiv, Crossref, ACL Anthology, DBLP, and OpenReview. Do not use “first” or “first-ever” unless that search is reported and the claim remains defensible.

### Conditional contribution language

If the implementation and evaluation are completed as designed, the paper can claim these contributions without presupposing a positive result:

1. A reproducible PDF-chunk-to-OKF v0.2 producer that preserves the original chunk text, identifiers, page metadata, document hashes, and source provenance in a conformant, immutable bundle.
2. A disclosed consumer that maps the existing dense/vector seeds back to those unchanged concepts and performs deterministic, bounded expansion over previous/next-passage links.
3. A paired comparison of raw-vector and OKF-enhanced retrieval across five fixed RAG pipelines.
4. Mechanism controls separating serialization from seed-capacity allocation and one-hop adjacency expansion.
5. A public benchmark package containing questions, common-unit evidence labels, raw outputs, execution traces, analysis code, and versioned artifacts.
6. An empirical result that may be positive, null, negative, or heterogeneous; the contribution is the controlled measurement, not a required win.

## 4. Abstract skeleton—fill only after analysis is frozen

> The Open Knowledge Format (OKF) v0.2 represents knowledge as portable Markdown concepts with YAML metadata and links, but it deliberately does not prescribe retrieval. Whether a particular OKF producer and consumer improve retrieval-augmented generation (RAG) over conventional document-chunk retrieval is therefore an empirical question. We present a controlled, paired evaluation across five pipelines: Simple RAG, Reranked-Simple RAG, an LLM-controlled Agentic RAG loop, and disclosed re-implementations of Self-RAG and FLARE. For each pipeline, we compare the existing raw-vector condition with a narrowly defined OKF-hybrid treatment: every original source chunk is serialized unchanged as a provenance-bearing `Source Passage`, the same vector backend supplies seed chunks, and the consumer reserves result capacity for deterministic one-hop expansion to immediately previous and next passages. Both conditions share the same PG&E Wildfire Mitigation Plan source snapshot, corrected versioned benchmark of 93 questions (79 answerable and 14 unanswerable controls), generator, prompts, final context budget, and evaluation protocol. Reference answers are available for all questions, and all 79 answerable questions have expected-page annotations for common-page retrieval evaluation. We measure answer correctness, faithfulness, citation quality, answerability decisions, latency, token use, model calls, monetary cost, and corpus-build overhead, together with retrieval recall and ranking on the page-annotated subset. An OKF-native lexical condition supplies a secondary retrieval comparison and, after the retrieval screen, an explicitly exploratory five-pipeline downstream transfer check. A semantic source review conducted after an incomplete paid generation run required benchmark corrections; the incomplete run was stopped before judging, invalidated in full, and excluded from this analysis. Deterministic and model-assisted source audits do not constitute blinded human validation, which remains pending. Relative to raw-vector retrieval, this chunk-preserving OKF adjacency treatment changes [PRIMARY ENDPOINT] by [EFFECT, 95% CI] and [EFFICIENCY ENDPOINT] by [EFFECT, 95% CI], with [INTERACTION SUMMARY] across pipelines and question types. [ONE-SENTENCE QUALIFIED INTERPRETATION THAT ACKNOWLEDGES THE SINGLE-DOCUMENT DOMAIN AND IMPLEMENTATION-SPECIFIC TREATMENT.] We release the producer, consumer, pinned bundle, question/evidence annotations, raw outputs, and analysis package at [REPOSITORY] and [DOI].

The final abstract should report absolute scores, paired deltas, and confidence intervals—not only percentages. If the primary result is null, say so. If effects differ by pipeline or question type, do not collapse them into a universal headline.

## 5. Research questions and preregistered hypotheses

### Research questions

**RQ1 — End-to-end effectiveness.** Holding the RAG pipeline and generation stack fixed, how does the chunk-preserving OKF adjacency condition change gold-evidence answer correctness relative to the existing raw-vector condition?

**RQ2 — Retrieval behavior.** How does the chunk-preserving, adjacency-aware condition change retrieval of gold evidence under a common final token budget, including recall, ranking, and provenance/citation accuracy?

**RQ3 — Efficiency.** What are the effects on retrieval latency, end-to-end latency, generator calls, input/output tokens, per-query cost, build time, storage, and update cost?

**RQ4 — Pipeline interaction.** Does the treatment effect differ among Simple, Reranked-Simple, Agentic, Self-RAG re-implementation, and FLARE re-implementation?

**RQ5 — Mechanism.** How much of any observed effect is attributable to deterministic previous/next-passage expansion, and how much is attributable to reserving result capacity for fewer direct vector seeds?

**RQ6 — Query characteristics.** Are effects different for direct lookup, lexical/identifier-heavy, multi-evidence, cross-section, global/synthesis, and unanswerable questions?

### Hypotheses

These hypotheses should be preregistered before the confirmatory run. Directional language is theory-driven, not a promised result.

**H1.** The chunk-preserving OKF adjacency consumer will increase gold-evidence recall under the fixed context-token budget relative to raw-vector retrieval, with the largest expected effect on questions whose supporting evidence lies next to a directly retrieved passage.

**H2.** The chunk-preserving OKF adjacency condition will improve gold-grounded answer correctness and citation precision, mediated by improved evidence retrieval. Mediation should be described as exploratory unless a formal, preregistered mediation analysis is used.

**H3.** At a matched dense-seed budget, deterministic one-hop previous/next expansion will increase gold-evidence recall relative to returning the seeds alone. This does not predict a benefit from semantic links or OKF metadata that the treatment does not use.

**H4.** OKF serialization will add one-time ingestion time and storage overhead. Query-time latency may increase because of seed-to-concept mapping and adjacency traversal; whether reduced re-retrieval/model calls offsets that overhead is an empirical question.

**H5.** The size of the OKF treatment effect will interact with pipeline type because iterative pipelines can compensate for first-stage misses, while single-pass pipelines cannot. The direction of each pairwise interaction should remain exploratory unless justified before data inspection.

For each hypothesis, retain and report its null. A nonsignificant difference is not evidence of equivalence. If equivalence is substantively important, preregister a smallest effect size of interest and use an equivalence test or show that the entire confidence interval lies within that margin.

## 6. Experimental treatment and controls

### Confirmatory 5 × 2 matrix

The paper's primary design is five pipelines crossed with two retrieval treatments: **raw-vector** and **OKF-hybrid**.

| Pipeline | Raw-vector condition | OKF-hybrid condition |
|---|---|---|
| Simple RAG | Existing dense top-k retrieval | Vector seeds + one-hop adjacent passages, same final context budget |
| Reranked-Simple | Existing dense overfetch + cross-encoder rerank | Adjacency-augmented candidates + matched reranking and budget |
| Agentic RAG | Existing LLM critic/rewrite/retrieve loop | Same controller and bounds, adjacency-aware retriever |
| Self-RAG re-implementation | Existing draft/reflect/retrieve/revise loop | Same loop and call cap, adjacency-aware retriever |
| FLARE re-implementation | Existing active-retrieval approximation | Same loop and call cap, adjacency-aware retriever |

Only the retrieval adapter and represented corpus may differ. Freeze the generator model identifier, generation prompts, controller prompts, sampling parameters, maximum calls, reranker, final context-token budget, answer formatting instructions, question order policy, and evaluator.

The operative v2 confirmatory set was frozen after the versioned source audit at **93 questions over one document domain, the PG&E Wildfire Mitigation Plan**:

- 35 golden questions and 58 harmonized questions;
- 79 answerable questions and 14 unanswerable-control questions;
- reference answers for all 93 questions;
- expected-page annotations for all 79 answerable questions.

End-to-end answer and answerability outcomes use all 93 questions. Page-level retrieval metrics use the 79 answerable questions with expected-page annotations; the 14 unanswerable controls have no fabricated retrieval target. Every table must print the relevant denominator. Golden versus harmonized origin and answerability should be retained as analysis fields; subgroup effects are exploratory unless separately powered and preregistered.

Question `NEG-004` is **answerable**: the supported substantive answer is “No,” with evidence on page 34. It must not be scored as a refusal control merely because its identifier begins with `NEG`. The 14 audited unanswerable items require an abstention or a clear statement that the requested fact is not reported. Answerability must come from the audited label field, never an ID prefix.

### Versioned benchmark curation and deviation

The inherited 100-question union was not accepted mechanically. An initial
audit produced a 97-question v1 benchmark:

- `wmp_q59` was removed because it contradicted its unanswerable label and duplicated answerable `SF-002`.
- `wmp_q60` and `wmp_q62` were removed as near-exact duplicates of `wmp_q50` and `wmp_q51`.
- `wmp_q50`, `wmp_q51`, and `wmp_q56` were relabeled/referenced using source-grounded answers and expected pages.
- All answerable v1 questions received expected-page annotations.

After 609 of 1,455 scheduled v1 answer cells had been generated, a separate
source review identified additional inherited semantic defects. Execution was
stopped before automated judging or condition-level answer analysis, and the
partial run was invalidated in full. Version 2 removed four unsupported
synthetic joins (`wmp_q36`, `wmp_q38`, `wmp_q42`, and `wmp_q48`) and applied
source-backed question, reference, page, and metadata corrections recorded by
QID in the benchmark and audit artifacts. The clean v2 schedule therefore has
1,395 answer cells: 930 confirmatory cells and 465 exploratory OKF-native
cells.

The release must preserve the inherited input hashes, deterministic curation
script, exclusion reasons, annotation corrections, benchmark IDs and hashes,
and the complete deviation record. It must state that the v2 corrections
followed an invalidated partial paid-generation run but preceded the clean v2
restart, all automated judging, and all condition-level answer analysis. This
audit improves label validity but does not make the benchmark independently
authored, eliminate possible annotation error, or substitute for blinded human
validation.

This is intentionally a single-domain, single-document-family study. It can provide a controlled estimate on a large regulatory document; it cannot establish cross-domain or cross-corpus generality.

### Secondary OKF-native comparison

Run an **OKF-native retrieval-only** condition as a secondary experiment. Evaluate it on the 79 page-annotated answerable questions using the same common-page relevance mapping and report retrieval quality, query latency, and storage/build overhead. Here, “native” means the repository's disclosed weighted BM25 over evidence and selected frontmatter followed by the same bounded adjacency traversal; it does not mean a standard retriever prescribed by OKF.

After the frozen v1 retrieval screen, but before paid answer generation, the study added OKF-native across the five generators because its page-hit result motivated a downstream transfer check. The corrected v2 exploratory arm contains 465 cells. Its inclusion is data-motivated and therefore exploratory. It must not enter the confirmatory 5 x 2 family or be presented as preregistered answer-quality evidence. The retrieval screen itself must be identified as having used the superseded v1 benchmark; all reported v2 retrieval results must be recomputed from the corrected benchmark.

### Mechanism ablations

Run these on all questions with the cheapest fixed generation pipeline, or on a preregistered representative subset. Do not expand every ablation across all five pipelines unless cost and power support it.

| Condition | Purpose |
|---|---|
| Raw-vector | Existing source chunks; all `top_k` positions are direct dense/vector results; primary baseline |
| OKF-serialized/vector-only | The same unchanged concept evidence is mapped from vector results, with traversal disabled; verifies that serialization and ID mapping alone do not change retrieval |
| Dense seed-budget control | Return only the same number of direct vector seeds reserved by the hybrid arm; measures the cost of reducing direct-result capacity |
| OKF-adjacency | The matched vector seeds plus deterministic one-hop previous/next-passage expansion, with the preregistered decay and final `top_k` |

The producer performs no concept summarization or semantic resegmentation: one source chunk becomes one concept and the evidence text is retained exactly. The ablation must therefore preserve the same text, identifiers, vector scores, ranking/tie policy, and final context budget while changing only seed capacity or adjacency expansion. Otherwise, an apparent adjacency effect could be a candidate-capacity effect.

### Content and leakage safeguards

- Derive both conditions from one immutable source-document snapshot.
- Preserve and test the one-to-one mapping from every raw chunk to its OKF concept, including exact evidence text, chunk ID, pages, document identity, and source hash.
- Do not add facts absent from the source. The confirmatory producer performs no LLM summarization or semantic rewriting.
- Keep question text, gold answers, and gold evidence outside the OKF producer's input surface. Freeze the audited benchmark before a clean confirmatory run; if treatment logic was tuned against benchmark outcomes, hold out a fresh confirmatory subset. Disclose the v1 partial-generation deviation rather than claiming that v2 preceded all paid treatment generation.
- Do not manually repair concepts in response to test failures. All producer edits must be rule-based, versioned, and made before unblinding.
- Report the deterministic producer code version, configuration, conversion time, validation results, and any human review. If a future producer uses an LLM, additionally report its model, prompt, decoding settings, retries, tokens, and cost.
- Validate bundle conformance automatically against the pinned interpretation of v0.2 and publish the validation report.
- Hash source files, extracted text, concept files, index files, question set, and gold annotations.

### Common-unit retrieval evaluation

Raw chunks and OKF concepts are intentionally one-to-one in this implementation, with identical evidence text and boundaries. Verify that identity in the release and score both conditions against the same expected pages for the 79 annotated answerable questions. The most defensible retrieval measure is expected-page recall in the **final context under the shared token budget**. Also report rank-based metrics at agreed cutoffs and explain how multiple retrieved units mapping to the same page are deduplicated. Do not invent retrieval-success labels for the 14 unanswerable controls merely because a generated response matches the abstention reference.

## 7. Exact baseline naming and fidelity disclosure

The paper must describe what the code actually runs rather than borrowing the full claims of the original algorithms.

| Paper label | Operational behavior in this repository | Required disclosure |
|---|---|---|
| Simple RAG | Dense top-k retrieval followed by one generator call | Conventional local baseline |
| Reranked-Simple | Dense overfetch, cross-encoder rerank, fixed top-k context, one generator call | Reranking control |
| Agentic RAG | LLM critic decides sufficiency and may rewrite/retrieve before final generation | Repository-specific agentic loop, motivated by iterative retrieval literature |
| Self-RAG (re-impl.) | Draft, JSON reflection, possible expanded retrieval and revision, capped calls | Not the trained Self-RAG checkpoint and not native reflection-token decoding |
| FLARE (re-impl.) | Draft text contributes to a look-ahead query; heuristic confidence markers may trigger another round | Approximation, not the original token-probability FLARE implementation |

Never shorten the last two labels to imply canonical implementations. The distinction belongs in the abstract, methods, tables, figure legends, and limitations.

## 8. Outcome hierarchy and measurement

### Recommended primary endpoint

Use one preregistered end-to-end primary endpoint: **gold-evidence answer correctness**, scored from the frozen question, reference answer, and independent gold evidence. The scoring instrument may combine a deterministic task metric where applicable with a blinded rubric, but its computation must be fixed before result inspection.

If two co-primary endpoints are required (for example correctness and evidence recall), adjust the primary family for multiplicity and say so explicitly.

### Key secondary outcomes

| Dimension | Measures |
|---|---|
| Retrieval | Common-evidence recall under the context budget; Recall@k; nDCG@k; MRR; evidence precision; duplicate rate; fraction reached by link traversal |
| Generation | Correctness; completeness; faithfulness to supplied evidence; reference-answer coverage; citation precision and recall |
| Answerability | Answerable/unanswerable macro-F1; refusal precision; refusal recall; unsupported-answer rate |
| Efficiency | Retrieval and end-to-end p50/p95 latency; generator calls; controller/judge calls; input/output tokens; cost/query |
| Corpus build | Extraction time; OKF construction time; embedding/index time; bundle bytes; index bytes; number and length of units; update time |
| Robustness | Golden/harmonized-origin and per-question-type effects; cold/warm latency; repeated-run variability |

Report both absolute values and paired deltas. “Efficiency” should not be reduced to provider cost: latency, calls, tokens, build overhead, and storage are separate outcomes.

### Judge safeguards

1. Judge correctness against independent gold/reference evidence, never only against the evidence each system retrieved.
2. Give faithfulness evaluation the actual retrieved context, but keep it separate from correctness.
3. Blind system and treatment labels. Randomize response position for pairwise checks and audit position sensitivity.
4. Use a strict machine-validated output schema. Retry malformed outputs under a documented cap; if still malformed, record missing/error. Never replace parse failures with neutral scores.
5. Pin the judge model identifier, prompt hash, temperature, maximum tokens, region, and execution date.
6. Aggregate repeated judge trials within question before inferential analysis; judge repeats are not independent questions.
7. Validate the judge on a blinded human sample stratified by system, treatment, golden/harmonized origin, answerability, and score range. Report agreement with uncertainty, not only a correlation point estimate.
8. Archive raw judge text and parsing diagnostics.

LLM judges can scale evaluation, but the literature documents position, verbosity, and self-enhancement biases. Human validation and deterministic retrieval/provenance measures are therefore essential, not optional decoration.

## 9. Statistical analysis plan

1. Freeze a protocol and analysis script before the confirmatory run. If practical, preregister the hypotheses, endpoints, exclusions, and smallest effect size of interest on OSF.
2. Pair observations by question, pipeline, and run replicate. Never compare only aggregate means from unrelated runs.
3. Estimate the primary treatment effect with a paired bootstrap confidence interval over questions, with prespecified stratification by answerability if needed. Report the mean/median paired delta and a standardized or ordinal-compatible effect size.
4. Fit a hierarchical treatment model with fixed effects for condition, pipeline, and condition × pipeline, plus a question-level random intercept. Choose the link/distribution to match the endpoint; do not treat a single ordinal rating as interval data without justification. There is no corpus-level generalization term because the confirmatory study has one document domain.
5. For per-pipeline confirmatory comparisons, use paired tests and control the family-wise error rate (for example, Holm adjustment). Publish adjusted and unadjusted values, effect sizes, and 95% confidence intervals.
6. Treat question-type subgroup analyses as exploratory unless powered and preregistered. Report interaction tests rather than claiming differences because one subgroup is significant and another is not.
7. If claiming quality parity/non-inferiority, set the smallest effect size of interest before seeing results and use an appropriate one-sided or equivalence procedure. “Not significant” does not establish parity.
8. Determine sample size or the minimum detectable effect from a pilot that is excluded from confirmatory analysis, or transparently label the study as precision-driven and report the achieved interval widths.
9. Handle failures by transparent denominators and sensitivity analyses. Do not silently drop failed calls or impute a midpoint.
10. Save a tidy per-question table from which every number and figure can be regenerated.

### Reuse of existing numbers

Existing aggregate numbers may be used as historical context or a pipeline sanity check. Earlier multi-corpus aggregates are not the primary comparator for this fixed 93-question study. Existing per-question outputs are eligible for the primary paired comparison only if all of the following match the OKF run or are uniformly re-evaluated:

- identical source snapshot and corpus membership;
- identical question text, IDs, answerability labels, and gold evidence;
- identical pipeline code/configuration and retrieval budgets;
- identical generator model/prompt/settings;
- identical judge model/prompt/parser and gold-evidence protocol;
- compatible execution and pricing dates;
- complete per-question raw outputs and error logs.

If any item differs, rerun the raw-vector cells beside the OKF cells or uniformly rescore both sets of raw answers with the repaired evaluator. Comparing a new OKF mean to an old published aggregate is not a controlled experiment.

## 10. Results shell—do not populate early

### Main effectiveness table

| Pipeline | Raw-vector score | OKF-hybrid score | Paired delta | 95% CI | Adjusted p | Effect size |
|---|---:|---:|---:|---:|---:|---:|
| Simple RAG | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Reranked-Simple | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Agentic RAG | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Self-RAG (re-impl.) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| FLARE (re-impl.) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

### Main efficiency table

| Pipeline × condition | Retrieval p50/p95 | End-to-end p50/p95 | Calls/query | Tokens/query | Cost/query |
|---|---:|---:|---:|---:|---:|
| [rows] | [ ] | [ ] | [ ] | [ ] | [ ] |

### Recommended figures

1. Forest plot of paired OKF effects with 95% CIs by pipeline and endpoint.
2. Quality–latency and quality–cost Pareto plots, with raw and OKF versions connected within pipeline.
3. Retrieval funnel showing direct vector seeds, one-hop adjacent candidates, and final packed evidence.
4. Ablation plot for raw-vector, serialized/vector-only, the matched seed-budget control, and adjacency expansion.
5. Question-type interaction plot with uncertainty; mark exploratory panels clearly.

Do not lead with only a radar chart or percentage-improvement graphic. Readers need denominators, absolute values, paired effects, and uncertainty.

## 11. Related-work narrative

### Retrieval-augmented generation and retrieval components

Lewis et al. introduced RAG as a combination of parametric generation and retrieved non-parametric memory. Dense Passage Retrieval established a practical bi-encoder approach for passage discovery, while BERT passage reranking and later sparse/dense comparisons illustrate the distinction between efficient candidate retrieval and expensive interaction-based ranking. This paper does not propose a new generator; it changes the represented knowledge and the retrieval adapter while keeping the generator fixed.

### Iterative and agent-controlled retrieval

ReAct interleaves reasoning and actions, and IRCoT interleaves retrieval with reasoning for multi-step QA. These works motivate the repository's LLM-controlled Agentic RAG baseline, but the exact baseline is a disclosed retrieve/critic/rewrite loop rather than a canonical implementation of either paper. Self-RAG trains a model to produce retrieval and critique reflection tokens. FLARE uses predicted forthcoming content and low-confidence tokens to drive retrieval during generation. The repository uses behavioral re-implementations of these ideas, so fidelity limitations must be explicit.

### Hybrid and graph-assisted retrieval

Sparse and dense representations capture partly complementary signals, and hybrid retrieval can outperform a dense-only model in some settings. GraphRAG demonstrates that graph-derived representations and community summaries can help a particular class of global corpus questions. The present producer emits only deterministic previous/next Markdown links between consecutive source chunks; these are not semantic relations, an entity knowledge graph, or GraphRAG. Graph retrieval is contextual background for link-following consumers, but equivalence between these structures must not be implied.

### Evaluation and provenance

BEIR motivates heterogeneous, retrieval-first evaluation using standard ranking metrics. KILT evaluates both downstream tasks and provenance. QASPER illustrates document-grounded, evidence-annotated information-seeking QA. RAGAS and ARES separate dimensions such as context relevance, answer faithfulness, and answer relevance, while G-Eval and MT-Bench show both the utility and biases of LLM judges. The present protocol combines common-unit gold-evidence retrieval metrics, end-to-end answer evaluation, and human validation rather than relying on a single model-graded mean.

### OKF v0.2

The official v0.2 specification is the authoritative definition. It describes concept files, hierarchy, links, provenance, verification, lifecycle, and optional attested computations while intentionally leaving retrieval and serving open. The official launch and v0.2 posts are product/specification sources, not peer-reviewed evidence that OKF improves RAG. They should support format descriptions only; performance claims must come from this experiment.

## 12. Annotated bibliography: primary and original sources

The bibliography below favors specifications, proceedings, and original papers. Use DOI links for proceedings when available and arXiv/OpenReview links when a conventional DOI is unavailable.

1. GoogleCloudPlatform. **Open Knowledge Format (OKF), Version 0.2.** Pinned specification, commit `3fcbb9f...`, 2026. Defines conformance, concept structure, links, provenance, trust, lifecycle, and non-goals. [Immutable specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md).

2. S. McVeety and A. Hormati. **Introducing the Open Knowledge Format.** Google Cloud Data Analytics Blog, June 12, 2026. Official v0.1 launch and format/platform distinction. [Official announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/).

3. S. McVeety and A. Hormati. **Open Knowledge Format v0.2 Tackles Agentic Trust.** Google Cloud Data Analytics Blog, July 24, 2026. Official explanation of the v0.2 provenance, trust, freshness, lifecycle, and attestation additions. [Official v0.2 announcement](https://cloud.google.com/blog/products/data-analytics/okf-v0-2-adds-trust-signals/).

4. P. Lewis et al. **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.** NeurIPS 2020. Foundational RAG formulation combining parametric and non-parametric memory. [Proceedings](https://papers.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html); [arXiv:2005.11401](https://arxiv.org/abs/2005.11401).

5. V. Karpukhin et al. **Dense Passage Retrieval for Open-Domain Question Answering.** EMNLP 2020. Original dense bi-encoder passage-retrieval baseline. [DOI: 10.18653/v1/2020.emnlp-main.550](https://doi.org/10.18653/v1/2020.emnlp-main.550); [arXiv:2004.04906](https://arxiv.org/abs/2004.04906).

6. R. Nogueira and K. Cho. **Passage Re-ranking with BERT.** 2019. Early cross-encoder passage-reranking work relevant to the reranked baseline. [arXiv:1901.04085](https://arxiv.org/abs/1901.04085).

7. Y. Luan, J. Eisenstein, K. Toutanova, and M. Collins. **Sparse, Dense, and Attentional Representations for Text Retrieval.** TACL 9, 2021. Provides evidence on representation trade-offs and sparse–dense hybrids. [DOI: 10.1162/tacl_a_00369](https://doi.org/10.1162/tacl_a_00369); [ACL Anthology](https://aclanthology.org/2021.tacl-1.20/).

8. S. Yao et al. **ReAct: Synergizing Reasoning and Acting in Language Models.** ICLR 2023. Motivates interleaved reasoning/action loops over external resources. [arXiv:2210.03629](https://arxiv.org/abs/2210.03629); [project/code](https://react-lm.github.io/).

9. H. Trivedi, N. Balasubramanian, T. Khot, and A. Sabharwal. **Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions.** ACL 2023. Original IRCoT work on iterative retrieval and reasoning. [DOI: 10.18653/v1/2023.acl-long.557](https://doi.org/10.18653/v1/2023.acl-long.557); [arXiv:2212.10509](https://arxiv.org/abs/2212.10509).

10. A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi. **Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.** ICLR 2024. Canonical trained Self-RAG method; use it to explain why the repository baseline must be labeled a re-implementation. [OpenReview](https://openreview.net/forum?id=hSyW5go0v8); [arXiv:2310.11511](https://arxiv.org/abs/2310.11511).

11. Z. Jiang et al. **Active Retrieval Augmented Generation.** EMNLP 2023. Introduces FLARE and forward-looking, confidence-triggered retrieval. [DOI: 10.18653/v1/2023.emnlp-main.495](https://doi.org/10.18653/v1/2023.emnlp-main.495); [arXiv:2305.06983](https://arxiv.org/abs/2305.06983).

12. D. Edge et al. **From Local to Global: A Graph RAG Approach to Query-Focused Summarization.** 2024. Related graph-assisted retrieval/summarization work; its entity/community graph is materially different from OKF's untyped links. [Microsoft Research publication page](https://www.microsoft.com/en-us/research/project/graphrag/publications/); [arXiv:2404.16130](https://arxiv.org/abs/2404.16130).

13. N. Thakur, N. Reimers, A. Rücklé, A. Srivastava, and I. Gurevych. **BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models.** NeurIPS Datasets and Benchmarks 2021. Motivates broad retrieval evaluation and nDCG/recall reporting. [Official proceedings](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract-round2.html); [arXiv:2104.08663](https://arxiv.org/abs/2104.08663).

14. F. Petroni et al. **KILT: a Benchmark for Knowledge Intensive Language Tasks.** NAACL 2021. Important precedent for jointly evaluating task output and provenance. [DOI: 10.18653/v1/2021.naacl-main.200](https://doi.org/10.18653/v1/2021.naacl-main.200); [arXiv:2009.02252](https://arxiv.org/abs/2009.02252).

15. P. Dasigi, K. Lo, I. Beltagy, A. Cohan, N. A. Smith, and M. Gardner. **A Dataset of Information-Seeking Questions and Answers Anchored in Research Papers.** NAACL 2021. Introduces QASPER with supporting evidence annotations. [DOI: 10.18653/v1/2021.naacl-main.365](https://doi.org/10.18653/v1/2021.naacl-main.365); [arXiv:2105.03011](https://arxiv.org/abs/2105.03011).

16. S. Es, J. James, L. Espinosa Anke, and S. Schockaert. **RAGAS: Automated Evaluation of Retrieval Augmented Generation.** EACL 2024 System Demonstrations. Separates RAG evaluation dimensions, but is not a substitute for gold evidence or human validation. [DOI: 10.18653/v1/2024.eacl-demo.16](https://doi.org/10.18653/v1/2024.eacl-demo.16); [arXiv:2309.15217](https://arxiv.org/abs/2309.15217).

17. J. Saad-Falcon, O. Khattab, C. Potts, and M. Zaharia. **ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems.** NAACL 2024. Evaluates context relevance, answer faithfulness, and answer relevance. [DOI: 10.18653/v1/2024.naacl-long.20](https://doi.org/10.18653/v1/2024.naacl-long.20); [arXiv:2311.09476](https://arxiv.org/abs/2311.09476).

18. Y. Liu et al. **G-Eval: NLG Evaluation Using GPT-4 with Better Human Alignment.** EMNLP 2023. Supports structured LLM evaluation while warning about evaluator bias toward LLM-generated text. [DOI: 10.18653/v1/2023.emnlp-main.153](https://doi.org/10.18653/v1/2023.emnlp-main.153); [arXiv:2303.16634](https://arxiv.org/abs/2303.16634).

19. L. Zheng et al. **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.** NeurIPS 2023 Datasets and Benchmarks. Documents agreement potential and position, verbosity, and self-enhancement biases. [Official proceedings](https://papers.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html); [arXiv:2306.05685](https://arxiv.org/abs/2306.05685).

20. D. Lakens. **Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses.** Social Psychological and Personality Science 8(4), 2017. Supports preregistered equivalence bounds instead of interpreting nonsignificance as parity. [DOI: 10.1177/1948550617697177](https://doi.org/10.1177/1948550617697177).

## 13. Limitations to preserve in the final paper

1. **Format–consumer scope.** Results identify the behavior of one chunk-preserving producer and one adjacency-aware consumer at one pinned OKF version, not the intrinsic performance of all OKF systems.
2. **Treatment composition.** The hybrid arm combines source-chunk serialization, fewer direct vector seeds, seed-to-concept mapping, and one-hop adjacency expansion. The vector-only and seed-budget controls are required to identify which component drives an effect.
3. **Single-domain scope.** The confirmatory data are 93 questions over one PG&E Wildfire Mitigation Plan. This does not establish generality even to other utilities' plans, much less code, databases, medicine, scientific literature, open-domain web search, or enterprise catalogs.
4. **Baseline fidelity.** The Self-RAG and FLARE conditions are re-implementations with different mechanisms from the trained/original systems. Agentic RAG is repository-specific.
5. **Model dependence.** A hosted generator and judge can drift, may not be bitwise deterministic at temperature zero, and may favor particular answer styles.
6. **Evaluation dependence.** Gold evidence can be incomplete; LLM judges have known biases; human samples have their own uncertainty.
7. **Candidate-allocation mismatch.** Concepts and chunks have identical evidence text and boundaries, but the hybrid arm reserves result capacity for adjacent passages instead of using every slot for a direct vector result. Matched seed-capacity controls are essential.
8. **Version instability.** OKF is new and evolving. The paper studies v0.2 at one immutable commit.
9. **Trust/freshness coverage.** If every source is current and treated identically, the experiment does not test v0.2 trust, lifecycle, freshness, or attestation features. Do not claim benefits from fields that were not manipulated.
10. **Cost portability.** Dollar cost depends on provider, region, model, date, caching, and pricing plan. Tokens and calls are more portable but still incomplete efficiency proxies.
11. **Latency portability.** Local hardware, database cache state, concurrency, and network conditions affect latency. Report hardware and cold/warm protocols.
12. **Power and multiplicity.** A 93-question design may be underpowered for small interaction or subgroup effects, especially the 14-question unanswerable subset. Confidence intervals and multiplicity control are required.

## 14. Claims discipline

### Defensible formulations after results exist

- “Under the pinned protocol, the chunk-preserving OKF adjacency consumer changed [metric] by [paired effect and CI].”
- “The one-hop previous/next-passage ablation suggests that [bounded, evidence-backed mechanism statement].”
- “Benefits were concentrated in [question type/origin], while [other group] showed [null/negative effect].”
- “The treatment incurred [build/query overhead] and produced [quality/efficiency trade-off].”

### Formulations to reject

- “OKF replaces vector databases/RAG.”
- “Google proved that OKF is more efficient.”
- “OKF guarantees trust, freshness, or factuality.”
- “Self-RAG/FLARE were beaten” without “re-implementation” and matched-condition detail.
- “Equivalent” based only on a nonsignificant p-value.
- “Production productivity increased” when only benchmark latency or cost was measured.
- “First” without a documented, current literature search.
- “General improvement” when effects are question-type-, document-, or pipeline-specific.

## 15. arXiv `cs.IR` manuscript structure

1. **Introduction.** Motivate the representation/retrieval interface; state that OKF is a format, not a retriever; list neutral contributions.
2. **Background and Related Work.** RAG retrieval; reranking; iterative/agentic methods; Self-RAG and FLARE; hybrid/graph retrieval; OKF specification; RAG evaluation.
3. **Problem Formulation.** Define source corpus, raw chunks, OKF concepts, consumer, evidence mappings, pipelines, and outcome variables.
4. **OKF Producer and Consumer.** Give algorithms, data model, traversal bounds, ranking/fusion, provenance handling, conformance, and complexity.
5. **Experimental Design.** Corpora, questions, conditions, frozen models/prompts/budgets, gold annotations, evaluator, hardware, cost model, and statistics.
6. **Results.** Primary endpoint first; retrieval, answerability, efficiency, interactions, ablations, robustness, and human validation.
7. **Discussion.** Mechanisms, trade-offs, negative/null findings, when the approach is useful, and what remains untested.
8. **Limitations and Ethics.** Preserve the limitations above; disclose synthetic generation and judge use.
9. **Reproducibility and Artifact Availability.** GitHub release, Zenodo DOI, licenses, hashes, and one-command reproduction.
10. **Conclusion.** One measured conclusion without product or replacement rhetoric.

Prefer a conventional research-paper label over “white paper” on arXiv. A polished preprint may also be hosted as a white paper, but the manuscript should read as a reproducible empirical `cs.IR` study.

## 16. Reproducibility manifest required for publication

Archive at least:

- source-document inventory, licenses/redistribution status, and SHA-256 hashes;
- extraction code/version and extracted-text hashes;
- OKF spec commit and checksum;
- producer code, prompts, model IDs, config, logs, and costs;
- immutable OKF bundle plus conformance report;
- raw-chunk and OKF index manifests;
- stable crosswalk from both retrieval units to common evidence IDs;
- frozen questions, reference answers, answerability labels, and gold evidence;
- pipeline source commit and complete config;
- generator/judge identifiers, prompts, parsers, prices, dates, and regions;
- raw responses, retrieved-unit traces, traversal traces, token/call accounting, errors, and retries;
- human annotation protocol, blinded assignments, raw labels, and agreement analysis;
- analysis environment lockfile/container, random seeds, statistical scripts, and figure code;
- a machine-readable result schema, `CITATION.cff`, open-source/data licenses, release tag, and Zenodo DOI.

The paper should be regenerable from immutable raw records. Hand-copied result tables are unacceptable.
