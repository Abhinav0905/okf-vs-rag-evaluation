# OKF trial data

Reproducible code and artifacts for a controlled evaluation of Open Knowledge
Format (OKF) v0.2 as a retrieval substrate across five RAG pipelines.

The study compares:

- Simple RAG
- Reranked RAG
- Agentic RAG
- Self-RAG re-implementation
- FLARE re-implementation

The confirmatory contrast is raw pgvector retrieval versus a frozen OKF-hybrid
consumer. A frozen OKF-native lexical consumer is evaluated as a secondary
retrieval condition and an explicitly exploratory end-to-end condition.

## Scientific scope

OKF is a Markdown-plus-YAML knowledge representation, not a replacement for a
vector database or for RAG. This repository evaluates one exact implementation:
each existing WMP source chunk becomes one provenance-bearing OKF `Source
Passage`, consecutive passages are linked, and consumers may traverse one hop
to the previous/next passage. Claims therefore apply to this producer,
consumer, source snapshot, and benchmark—not to OKF generally.

The operative specification is OKF v0.2 at commit
[`3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md).

## What we found

Writing this corpus in OKF and following its links did not improve retrieval.
The result is a null, and it is what the specification implies: OKF v0.2 lists
storage, query infrastructure and ranking as non-goals, so it does not define a
way to search.

Retrieval over the 79 questions that have page-level answer keys, top-10, share
of questions where a correct page was retrieved:

| Retrieval arm | Uses OKF | Page hit |
|---|---|---:|
| Dense, `all-MiniLM-L6-v2` (frozen baseline) | no | 65.8% |
| Dense seeds + one-hop OKF links (confirmatory treatment) | yes | 63.3% |
| Dense, `titan-embed-text-v2` (8192-token window) | no | 86.1% |
| Weighted BM25 over concepts + OKF links | yes | 91.1% |
| **Plain BM25 over the raw chunks** | **no** | **97.5%** |

The BM25-over-concepts arm looked like a large win for OKF against the frozen
baseline (91.1% versus 65.8%, McNemar p = 8.8e-5). It is not one. Two controls
explain it:

1. **The frozen dense baseline was handicapped.** `all-MiniLM-L6-v2` accepts 256
   word-piece tokens; 80.9% of these passages are longer, and the encoder
   received a median of only 64.4% of each passage. A lexical index reads every
   word. Removing the truncation alone accounts for +0.198 page recall
   (95% CI +0.110 to +0.291).
2. **The gain was lexical, not structural.** Plain BM25 over the unmodified
   chunks, with no concept files, no frontmatter and no links, scores *higher*
   than the OKF arm. Adding OKF to plain BM25 changes page recall by −0.070
   (95% CI −0.133 to −0.013).

The one thing OKF's traversal reliably does is spend half the result budget on
neighbouring passages, which displaces better-matching ones. Driving the same
expansion from chunk order instead of OKF links reproduces the same loss
(−0.051, 95% CI −0.108 to +0.006), so the mechanism is budget allocation rather
than anything specific to the format.

What the study does verify about OKF is engineering, not retrieval: the bundle is
portable, reviewable in version control, addressed by stable identifiers, carries
provenance and page metadata, rebuilds to a matching content digest, and its
1,837 passages are byte-identical to the rows in the vector database. Those are
real benefits for auditing and exchange. They are not retrieval benefits.

Full numbers, confidence intervals and Holm-adjusted p-values are in
`results/retrieval_diagnostics/diagnostic_summary.json` and the manuscript.

## Testing OKF as it is actually meant to be used

The bundle above is a minimal reading of OKF: one concept per retrieval chunk,
linked only to the previous and next chunk. That is not what the format is for, so
a null for it says little about OKF as documented. A second bundle tests the real
thing, for PG&E only.

`scripts/build_topic_okf_bundle.py` builds **one concept per topic**, nested, with
parent, child, sibling and cross-reference links. The topics are not invented: the
PDF carries an embedded outline of 1,006 entries six levels deep, which is the
author's own hierarchy. Each concept's title is a heading verbatim and its body is
the text between that heading and the next, cut at the exact coordinates recorded
for the outline entry. Nothing is summarised or rewritten. Result: 1,011 concepts,
6 levels, **99.9% of the document's words retained verbatim**, all 77 annotated
answer pages covered, content digest verified.

Because topic concepts and chunks are different sizes, comparing "top 10 units"
would reward whichever arm has bigger units. Every arm is therefore packed to the
same 2,200-token context budget, whole units only. At that budget:

| Retrieval arm | Page hit |
|---|---:|
| Dense chunks | 59.5% |
| **Plain BM25 over chunks, no OKF** | **88.6%** |
| OKF chunk-chain + previous/next links | 89.9% |
| OKF topic-structured | 76.0% |
| OKF topic-structured + hierarchy links | 76.0% |

The topic version is **worse** than plain chunk retrieval: −0.104 page recall
(95% CI −0.211 to 0.000). Two measured reasons:

1. **The links carried no new evidence.** 104 of 588 packed units did arrive by
   following parent/child/sibling links, so traversal worked, but they supplied
   **zero** answer pages the direct lexical matches had not already found.
2. **Coarse topics can become unreachable.** 12 topics exceed the whole context
   budget, so their text is in the bundle but can never be retrieved. The Table of
   Contents is a single 27,768-token concept, which alone loses the four questions
   that ask on what page a section begins.

The practical reading: topic structure is good for organising and navigating a
document, chunks are better for retrieving from it. That matches the OKF
materials, which describe "OKF plus RAG" rather than OKF instead of it.

## Caveats a reader should not skip

- The confirmatory 5x2 generation run was **halted at 1,254 of 1,395 cells** and
  its answer-quality endpoints are unreported. See the deviations log.
- The topic producer, the diagnostic arms and the hybrid A/B are all
  **exploratory**, added after retrieval results had been seen, each with its own
  multiplicity family.
- The hybrid A/B design - querying a vector store and an OKF bundle in parallel
  and merging - is **ours, not Google's**. The OKF materials describe OKF as an
  authored source ingested into the retrieval stack, not a parallel query target.
- Blinded human validation of the answer key is still outstanding.
- One document, one utility, one benchmark. Nothing here generalises by itself.

## Frozen data

- Source snapshot: PG&E 2026-2028 Base Wildfire Mitigation Plan
- Source PDF SHA-256: `e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a`
- Confirmatory benchmark: versioned counts in `data/benchmark_questions.json`
- Answerable questions: every item has reference pages and machine-resolved gold evidence
- Unanswerable controls: source-checked, with blinded human validation still pending
- Full OKF bundle: 1,837 concepts across PG&E, SCE, and PacifiCorp
- Bundle content SHA-256: `bec2561aa21eb4be38259d04d9aa34ed96b9abd57058fe7d10ce775eded1eb03`

The deterministic benchmark builder records inherited source hashes, excluded
duplicates, and every annotation correction. A partial paid generation run was
stopped before judging when an additional semantic review found gold errors.
That run is explicitly superseded and excluded from all reported endpoints; the
corrected benchmark receives a new version and hash before the complete restart.

## Environment

Python 3.11 is recommended. Live Bedrock runs require standard AWS
authentication:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN       # when temporary credentials are used
AWS_REGION              # us-west-2 in the frozen run
```

The code uses AWS SigV4 credentials through `boto3`; no separate Bedrock API key
is required. Local pgvector defaults to `localhost:5433`, database `wmp_eval`,
table `wmp_chunks`. The corresponding optional overrides are `DB_HOST`,
`DB_PORT`, `DB_NAME`, `DB_USERNAME`, and `DB_PASSWORD`.

Never commit `.env` files, credentials, account identifiers, or session tokens.

## Reproduction

### Environment wrapper: use it

Run every command through `scripts/with_experiment_env.sh`. The shared project
`.env` supplies AWS credentials, but it also sets `DB_HOST`, `DB_PORT` and
`DB_NAME` for an unrelated application database. The evaluation harness reads
those same variable names, so loading `.env` directly points the retriever at the
wrong database. The wrapper loads credentials, drops the database overrides so the
`eval_config.yaml` defaults apply (`localhost:5433`, database `wmp_eval`, table
`wmp_chunks`), and pins `EVAL_DEVICE=cpu` for reproducible latency. It parses
`.env` line by line rather than sourcing it, because the file contains a key whose
name is not a valid shell identifier.

### Setup

```bash
cd okf_trial_data
python3.11 -m venv .venv
.venv/bin/pip install -r ../eval_harness/requirements.txt
.venv/bin/pip install -e '.[dev,analysis,paper]'

# pgvector corpus (1,837 passages across PGE, SCE, PC)
../eval_harness/scripts/start_pgvector.sh

.venv/bin/python scripts/build_benchmark.py
.venv/bin/python scripts/audit_benchmark.py
.venv/bin/pytest -q tests
```

### Retrieval (no model calls, free)

```bash
# Frozen confirmatory screen: raw_vector, okf_hybrid, okf_native
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_retrieval_benchmark.py

# How much of each passage the frozen encoder can actually read
./scripts/with_experiment_env.sh .venv/bin/python scripts/measure_embedding_truncation.py

# Confound decomposition. Add --skip-titan to stay fully offline; otherwise this
# embeds 1,837 passages once with amazon.titan-embed-text-v2:0 and caches them.
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_retrieval_diagnostics.py
```

### Generation, judging, analysis (billable)

Measured cost for the full matrix is roughly 48 US dollars: about 25 for
generation and about 20 for judging.

```bash
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_generation.py \
  --generator-backend bedrock --output-dir results/full --workers 3

./scripts/with_experiment_env.sh .venv/bin/python scripts/run_judging.py \
  --generation-dir results/full \
  --judge-backend bedrock --trials 3 --max-attempts 3 --workers 6

./scripts/with_experiment_env.sh .venv/bin/python scripts/analyze_results.py
```

Use `--generator-backend mock` for a free, offline end-to-end check first.

### Manuscript and release

```bash
.venv/bin/python paper/render_paper.py \
  --author '[Author name]' --affiliation '[Affiliation]' --orcid '[ORCID]' \
  --repository-url '[Repository URL]' --doi pending \
  --funding-statement '[Funding statement]' \
  --conflict-statement '[Conflict-of-interest statement]'

.venv/bin/python scripts/build_release.py --status draft
```

All generation and judging stages append durable JSONL records and resume only
missing cells. A changed schedule or run manifest causes an abort rather than a
silent overwrite. Every number in the manuscript is read from those records;
none is typed by hand.

## Layout

```text
config/                 Frozen experiment configuration
data/benchmark_questions.json
data/okf_bundles/       Deterministic OKF v0.2 bundle
paper/                  Research notes and manuscript sources
protocol/               Pre-results experiment protocol and deviations
scripts/                Build, run, judge, analyze, and paper scripts
src/okf_trial_data/     Producer, consumers, adapters, evaluator
tests/                   Offline tests
results/                 Raw records, statistics, tables, and figures
output/pdf/              Final rendered manuscript
```

## Evaluation safeguards

- Reference-answer and expected-page evaluation, rather than judging only
  against each system's self-selected context
- Condition-blinded judge prompts
- Bedrock forced-tool structured output followed by a strict independent parser
- Three valid judge trials per answer
- No neutral score imputation for malformed responses
- Exact complete-pair gates
- Paired bootstrap intervals, Wilcoxon tests, Holm correction, and McNemar tests
- Historical aggregates treated only as sanity checks

## Public release

Before creating a GitHub release and Zenodo DOI, fill in authorship, affiliation,
ORCID, repository URL, license choices, source-PDF redistribution status, and
funding/conflict disclosures. Publish code, derived annotations, hashes, raw
model outputs, analysis artifacts, and the OKF bundle only where their licenses
permit redistribution. `build_release.py --status final` enforces the manuscript
placeholder gate and requires `LICENSE`, `DATA_LICENSE.md`, and `CITATION.cff`;
draft archives remain clearly labeled and are not publication candidates.
