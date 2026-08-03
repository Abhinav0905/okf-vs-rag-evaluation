# Does Google's Open Knowledge Format improve RAG?

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21778673.svg)](https://doi.org/10.5281/zenodo.21778673)

A controlled study on one large regulatory document. Code, data, raw model
outputs, and the paper.

**Short answer: no.** Writing the corpus in OKF and following its links did not
improve retrieval or answer quality. The improvement OKF appears to give turns
out to depend entirely on what you compare it against.

Paper: **[PDF](okf_trial_data/paper/PAPER.pdf)** · **[Markdown](okf_trial_data/paper/PAPER.md)**

## The three findings

**1. The apparent OKF win is an artifact.** A lexical OKF retriever scored 91.1%
page-hit against 65.8% for the vector-database baseline. But the baseline's
encoder (`all-MiniLM-L6-v2`, 256-token limit) could only read a median of 64% of
each passage — 80.9% of passages are longer than its input window. Plain BM25
over the same text, using **no OKF at all**, scored 97.5%.

| Retrieval arm | Uses OKF | Page hit |
|---|---|---:|
| Dense, 256-token limit (frozen baseline) | no | 65.8% |
| Dense, 8192-token limit | no | 86.1% |
| **Plain BM25 over raw chunks** | **no** | **97.5%** |
| BM25 over OKF concepts + links | yes | 91.1% |

**2. OKF built the way it's meant to be used is worse, not better.** We rebuilt
the corpus as 1,011 topic concepts — one per topic, nested 6 levels, with parent,
child and sibling links — from the PDF's own 1,006-entry outline, keeping 99.9% of
the document's words verbatim. At a matched 2,200-token context budget it scored
75.9% against 88.6% for plain chunk retrieval.

Why, measured rather than guessed:
- **Links carried no new evidence.** 104 of 588 context units did arrive by
  traversal, but they supplied **zero** answer pages the direct matches hadn't
  already found.
- **Coarse topics become unreachable.** 12 topics exceed the entire context
  budget, so their text is in the bundle but can never be retrieved. The Table of
  Contents is a single 27,768-token concept, which alone loses the four questions
  asking what page a section begins on.

**3. The A/B depends on the baseline.** Adding OKF to a *weak* vector-only
pipeline improves page recall by +0.226 (95% CI +0.133 to +0.323, Holm p<0.001).
Adding it to a *strong* pipeline — BM25 + dense + reranking — gives nothing, and
answer quality does not improve on any measure:

| Arm | Correctness | Citation quality | Page hit |
|---|---:|---:|---:|
| **A: hybrid RAG** | **4.620** | **4.680** | **86.1%** |
| B: + OKF topics | 4.532 | 4.429 | 84.8% |
| B: + OKF chain | 4.506 | 4.583 | 82.3% |

Seven of eight paired dimension estimates are negative across two independent OKF
variants. Correctness is a null; citation quality (topics) and completeness
(chain) are measurably worse, intervals excluding zero.

## What OKF *is* good for

The study verifies real properties that are not retrieval properties: the bundle
is portable, reviewable in version control, addressed by stable identifiers,
carries provenance and page metadata that survive being handed to another
consumer, rebuilds to a matching content digest, and its passages are
byte-identical to the rows in the vector database. This matches OKF's own
materials, which describe "OKF **plus** RAG" as complementary layers — not OKF
instead of RAG.

## Layout

```
okf_trial_data/
  paper/PAPER.pdf                   typeset paper, 9 pages with figures
  paper/PAPER.md                    same content as Markdown
  paper/render_paper.py             regenerates both; no number is hand-typed
  paper/make_figures.py             regenerates the three figures
  scripts/                          build, run, judge, analyse
  src/okf_trial_data/               OKF producer, consumers, evaluator
  data/benchmark_questions.json     93 questions with page-level answer keys
  data/okf_bundles/wmp_all_v0_2/    chunk-preserving bundle (1,837 concepts)
  data/okf_bundles/pge_topics_v0_2/ topic-structured bundle (1,011 concepts)
  protocol/                         pre-results protocol + full deviations log
  results/                          every raw model output and analysis summary
  tests/                            52 offline tests
eval_harness/                       minimal retrieval/generation dependency
```

## Reproducing

```bash
cd okf_trial_data
python3.11 -m venv .venv
.venv/bin/pip install -r ../eval_harness/requirements.txt
.venv/bin/pip install -e '.[dev,analysis,paper]'
../eval_harness/scripts/start_pgvector.sh    # if present; else see eval_config.yaml

# free, no model calls
./scripts/with_experiment_env.sh .venv/bin/python scripts/build_topic_okf_bundle.py
./scripts/with_experiment_env.sh .venv/bin/python scripts/measure_embedding_truncation.py
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_retrieval_diagnostics.py
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_topic_retrieval_comparison.py

# billable, about $8 on Amazon Bedrock
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_hybrid_ab_experiment.py --stage all

.venv/bin/python paper/make_figures.py
.venv/bin/python paper/render_paper.py
```

## Caveats worth reading before citing

- **One document, one utility, 93 questions.** Nothing here generalises by itself.
- **Two producers, both verbatim-text.** A producer that re-authored passages, or
  added semantic rather than structural links, might behave differently.
- **The frozen dense baseline was weak** (truncating encoder). Reported as run
  rather than quietly swapped; an untruncated arm is added as a diagnostic.
- **Exploratory status.** The diagnostic arms, topic producer and A/B were all
  specified after retrieval results were seen. Each carries its own multiplicity
  family. These are attribution and estimation, not preregistered tests.
- **The A/B design is ours, not Google's.** Querying a vector store and an OKF
  bundle in parallel and merging is our construction; the OKF materials describe
  OKF as an authored source ingested *into* the retrieval stack.
- **A halted run.** An earlier five-pipeline matrix was stopped at 1,254 of 1,395
  cells when the study was redirected; its answer-quality endpoints are
  unreported. Raw records are published and labelled. See the deviations log.
- **Blinded human validation of the answer keys is outstanding.**

## Licence and citation

Code: MIT ([okf_trial_data/LICENSE](okf_trial_data/LICENSE)). Data and
annotations: CC BY 4.0, with source-document terms explained in
[okf_trial_data/DATA_LICENSE.md](okf_trial_data/DATA_LICENSE.md). Cite via
[okf_trial_data/CITATION.cff](okf_trial_data/CITATION.cff).

Kumar Abhinav, AiDash — ORCID [0009-0009-1839-841X](https://orcid.org/0009-0009-1839-841X)

Archived on Zenodo. Cite the concept DOI, which always resolves to the newest
version; cite the version DOI to pin an exact snapshot.

- Concept DOI (all versions): [10.5281/zenodo.21778673](https://doi.org/10.5281/zenodo.21778673)
- Version DOI (v1.0.0): [10.5281/zenodo.21778674](https://doi.org/10.5281/zenodo.21778674)

```bibtex
@software{abhinav_okf_rag_2026,
  author    = {Abhinav, Kumar},
  title     = {Does Google's Open Knowledge Format improve retrieval-augmented
               generation? A controlled study on one regulatory document},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.21778673},
  url       = {https://github.com/Abhinav0905/okf-vs-rag-evaluation}
}
```
