# Does Google's Open Knowledge Format Improve Retrieval-Augmented Generation?

## A Controlled Study on One Regulatory Document

**Kumar Abhinav**  
AiDash  
ORCID: [0009-0009-1839-841X](https://orcid.org/0009-0009-1839-841X)  
Code and data: https://github.com/Abhinav0905/okf-vs-rag-evaluation  
Archived: [doi:10.5281/zenodo.21778673](https://doi.org/10.5281/zenodo.21778673) (all versions) · [doi:10.5281/zenodo.21778674](https://doi.org/10.5281/zenodo.21778674) (v1.0.0)

## Summary

Google Cloud's Open Knowledge Format (OKF) stores knowledge as Markdown files with YAML metadata and links between them. It is a way of writing knowledge down. The specification lists storage, query infrastructure and ranking as things it deliberately does not cover. Despite that, it has been widely described in public commentary as a replacement for vector databases and for retrieval-augmented generation (RAG). This paper tests that claim on one large regulatory document with a fixed set of questions.

The short answer is that OKF did not improve retrieval or answers, and that the improvement it appears to give is an artifact of what it is compared against. Three findings support this.

First, a lexical OKF retriever scored 91.1% against 65.8% for the vector-database baseline, which looks decisive. It is not. The baseline's encoder could only read part of each passage, and plain keyword search over the same text with no OKF at all scored 97.5% - higher than the OKF arm.

Second, we rebuilt the corpus the way OKF is actually meant to be used: 1,011 concepts, one per topic, nested 6 levels deep, with parent, child and sibling links, using the document's own heading hierarchy and its own words. That version scored 75.9%, worse than plain chunk retrieval at 88.6%.

Third, we ran the practitioner's A/B: a conventional pipeline versus the same pipeline with OKF added as an extra source. Against a weak vector-only baseline, adding OKF improved page recall by +0.226 [+0.133, +0.323]. Against a strong baseline that already combined keyword search, vector search and reranking, the gain disappeared and answer quality did not improve on any measure.

None of this says OKF is bad. It says OKF is not a retrieval improvement, which is what its own specification implies. What the study does verify is that an OKF bundle is portable, reviewable in version control, addressed by stable identifiers, and carries provenance that survives being handed to a different consumer. Those are real benefits. They are not retrieval benefits.

## 1. What was tested

OKF does not define a retriever, so testing it requires building one. We built two, and disclose both exactly. Results apply to these implementations on this document, not to OKF in general.

The document is the PG&E 2026-2028 Base Wildfire Mitigation Plan, a 623-page public regulatory filing (SHA-256 `e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a`). The question set is wmp_okf_pge_93_v2: 93 questions, 79 answerable with page-level answer keys and 14 controls whose answers are absent from the document. Answer keys were corrected against the source before the reported runs; blinded human validation is still outstanding and is listed as a limitation.

**Bundle A, chunk-preserving.** Each existing 500-token retrieval chunk becomes
one concept, text unchanged, linked only to the previous and next chunk. The
1,837 passages are byte-identical to the rows in the vector database, verified,
which lets both arms be scored against the same answer key.

**Bundle B, topic-structured.** This is OKF as its documentation describes it.
The PDF carries an embedded outline of 1,006 entries,
which is the author's own topic hierarchy. Each concept is one outline entry: its
title is the heading verbatim, its body is the text between that heading and the
next, cut at the exact coordinates recorded for the entry, and its links are
parent, child, previous and next sibling, plus the cross-references the document
itself makes. Nothing is summarised or rewritten. Result: 1,011
concepts, 6 levels, 99.9% of the document's words retained
verbatim, all 77 annotated answer pages covered, content digest verified.

## 2. How it was measured

Topic concepts and chunks are different sizes, so asking each arm for its top 10 units would hand more text to whichever has larger units, and more text trivially covers more pages. Every arm therefore fills the same 2200-token context budget and is scored on what lands inside it. Units are never truncated, because a truncated passage would otherwise earn credit for text that was not supplied.

Retrieval is scored as expected-page recall and page-hit rate against the answer keys on the 79 annotated questions. Answers are scored by a blinded judge against an independent reference answer and source passages selected only from the annotated pages, never against the passages the system chose for itself. The judge returns a typed object through forced tool use and is validated by a strict independent parser; malformed responses are retried under a cap and recorded as missing rather than replaced with a neutral score. Every answer is judged 3 times (us.anthropic.claude-haiku-4-5-20251001-v1:0). Correctness is not scored for the 14 controls, which are scored on whether the system correctly declined.

## 3. Where the apparent OKF advantage comes from

The headline contrast changes three things at once: the ranking function, how much of each passage the encoder can read, and OKF itself. Arms below vary one at a time. Top 10 units, all on the same passages and questions.

| Retrieval arm | Uses OKF | Page hit | Page recall | Median ms |
|---|---|---:|---:|---:|
| Dense, 256-token input limit | no | 65.8% | 0.599 | frozen run |
| Dense, 8192-token input limit | no | 86.1% | 0.797 | 341.6 |
| **BM25 over the raw chunks** | **no** | 97.5% | 0.925 | 1.6 |
| BM25 and dense fused | no | 96.2% | 0.899 | 323.6 |
| Dense seeds + OKF links | yes | 63.3% | 0.586 | frozen run |
| BM25 over concepts + OKF links | yes | 91.1% | 0.855 | frozen run |
| As above, frontmatter removed | yes | 92.4% | 0.874 | 1.8 |
| BM25 + adjacency, no OKF | no | 92.4% | 0.874 | 1.5 |

Two facts account for the gap.

**The baseline encoder could not read the passages.** `all-MiniLM-L6-v2` accepts 256 word-piece tokens. Measured over the 654 passages of this document, 80.9% are longer than that (median 398 tokens, longest 2,035), and the encoder received a median of only 64.4% of each passage. A lexical index reads every word. Removing the truncation alone moved page recall by +0.198 [+0.110, +0.291] (Holm p=0.001).

**The gain was lexical, not structural.** Plain BM25 over the unmodified chunks, with no concept files, no frontmatter and no links, moved page recall by +0.326 [+0.226, +0.427] (Holm p=<0.001) against the frozen baseline, and scores above the OKF arm. Measured against plain BM25, adding OKF changed page recall by -0.070 [-0.133, -0.013] - a loss, with the interval excluding zero.

The loss has a mechanism, and it is testable. The consumer reserves half its result budget for neighbouring passages, and those positions would otherwise hold better-matching text. Driving the identical expansion from chunk order instead of OKF links reproduces the same loss (-0.051 [-0.108, +0.006]), so the cause is budget allocation rather than anything specific to the format.

## 4. Testing OKF as it is meant to be used

At a matched 2200-token context budget:

| Retrieval arm | Page hit | Page recall | Duplicated tokens |
|---|---:|---:|---:|
| Dense chunks only | 59.5% | 0.549 | 3.9% |
| **BM25 chunks, no OKF** | 88.6% | 0.814 | 1.4% |
| OKF chunk-chain + prev/next links | 89.9% | 0.827 | 2.0% |
| OKF topic-structured | 75.9% | 0.710 | 3.6% |
| OKF topic-structured + hierarchy links | 75.9% | 0.710 | 4.2% |
| Vector DB + OKF topics, fused | 79.7% | 0.752 | 7.6% |
| Vector DB + OKF chain, fused | 82.3% | 0.774 | 12.9% |

The topic-structured version is worse than plain chunk retrieval: -0.104 [-0.211, +0.000]. Two measured reasons, not inferences.

**The links carried no new evidence.** 104 of 588 packed units did arrive by following parent, child or sibling links, so traversal worked mechanically. They supplied 0 answer pages that the direct lexical matches had not already found. The paired effect of enabling traversal is +0.000 [+0.000, +0.000].

**Coarse topics can become unreachable.** 12 topics are larger than the entire 2200-token context budget, so their text is present in the bundle but can never be retrieved whole. The largest is the document's Table of Contents at 27,768 tokens. That single consequence loses the four questions that ask on what page a section begins - evidence that chunking retrieves without difficulty.

Fusing the vector database with an OKF bundle also duplicates text, because the bundle holds a verbatim copy of the same document. In the fused arms 12.9% and 7.6% of the context budget is spent on pages already covered.

## 5. The A/B a practitioner would run

Arm A is a conventional strong pipeline: BM25 and dense retrieval over chunks, fused by reciprocal rank, then cross-encoder reranked. Arm B is arm A **plus** an OKF source, fused and reranked identically. Because B differs from A only by the presence of OKF, the contrast estimates what OKF adds to a baseline that is already good. The pipeline, prompts, budget, generator and judge are unchanged between arms. 279 answers, 837 judge trials, no failures.

| Arm | Correctness | Completeness | Groundedness | Citation | Refusal acc. | Page hit |
|---|---:|---:|---:|---:|---:|---:|
| **A: hybrid RAG** | 4.620 | 4.608 | 4.776 | 4.680 | 1.000 | 86.1% |
| B: + OKF topics | 4.532 | 4.612 | 4.654 | 4.429 | 1.000 | 84.8% |
| B: + OKF chain | 4.506 | 4.481 | 4.693 | 4.583 | 1.000 | 82.3% |

Paired differences against arm A, 79 answerable questions:

| Change | Correctness | Completeness | Groundedness | Citation quality |
|---|---|---|---|---|
| + OKF chain | -0.114 [-0.270, +0.030] | -0.127 [-0.262, -0.017] | -0.083 [-0.232, +0.048] | -0.096 [-0.241, +0.031] |
| + OKF topics | -0.089 [-0.291, +0.118] | +0.004 [-0.118, +0.152] | -0.127 [-0.338, +0.062] | -0.228 [-0.425, -0.048] |

Correctness is a null in both directions. Two dimensions are measurably worse: citation quality with topics and completeness with the chain, both intervals excluding zero. Per question, topics won 3 and lost 7; the chain won 2 and lost 10. All three arms declined all 14 controls correctly, so OKF neither helped nor hurt abstention.

The most robust signal is not any single interval. Seven of the eight dimension estimates are negative, across two independent OKF variants, and this agrees with retrieval, which is measured separately. Those per-dimension intervals are not corrected for eight comparisons, so any one of them alone should be read as suggestive; the consistent direction is the finding.

For contrast, the same fusion against a **weak** vector-only baseline improves
page recall by +0.226 [+0.133, +0.323] (chain, Holm
p=<0.001) and +0.204 [+0.113, +0.297] (topics,
Holm p=0.003). That is the same intervention scoring a
clear win or nothing at all, depending only on what it is compared against. It is
the single most important thing to control when evaluating a knowledge format.

## 6. What this means

OKF v0.2 states that storage, query infrastructure and ranking are outside its scope. A format that does not define a search method cannot improve search by itself, and that is what we measured. What can change behaviour is the component that reads the format, and both components we built left retrieval and answers unchanged or slightly worse.

For practitioners the reading is narrow and useful. Topic structure is good for organising and navigating a document; chunks are better for retrieving from it. That matches OKF's own materials, which describe OKF *plus* RAG as complementary layers rather than OKF instead of RAG. If your retrieval is weak, the cheapest large improvement here was not OKF but adding a lexical index: BM25 cost about 2.3 ms per query against roughly 342 ms for a hosted encoder.

For evaluation practice, one lesson stands out. Our own first measurement showed a large, highly significant advantage for OKF, and it would have supported the popular claim. It was an artifact of comparing a lexical index against an encoder that could not read most of each passage. A single strong baseline reversed the ranking. Any evaluation of a knowledge format should include a lexical baseline and should confirm that the encoders being compared can actually read the text they are given.

## 7. Limitations

**One document.** 93 questions on one utility's filing. Nothing here generalises by itself to other documents, domains, or corpora.

**Two producers, not all producers.** A producer that re-authored passages into genuinely new concept prose, or that added semantic links between related sections rather than structural ones, might behave differently. We tested verbatim-text producers on purpose, so that any effect could be attributed to structure rather than to rewriting, but that is a real restriction on scope.

**The frozen dense baseline was weak.** Its encoder truncates, as measured above. We report it as run rather than quietly replacing it, and add an untruncated encoder as a diagnostic arm. The confirmatory comparison is unaffected because it compares the OKF consumer against that same arm on equal terms, but the absolute dense numbers understate a well-configured dense retriever.

**Exploratory status.** The diagnostic arms, the topic producer and the A/B were all specified after retrieval results had been seen. Each carries its own multiplicity family. They are attribution and estimation, not preregistered hypothesis tests.

**The A/B design is ours.** Querying a vector store and an OKF bundle in parallel and merging the hits is our construction. The OKF materials describe OKF as an authored source ingested into the retrieval stack. This design should not be attributed to Google.

**A halted run.** An earlier five-pipeline matrix was stopped at 1,254 of 1,395 cells when the study was redirected. Its answer-quality endpoints are unreported. Raw records are published and labelled; see the deviations log.

**Judge and model dependence.** A hosted judge has known biases and a hosted generator can drift. Blinded human validation of the answer keys is outstanding. Cost and latency depend on provider, region and date.

## 8. Reproducing this

```bash
cd okf_trial_data
python3.11 -m venv .venv
.venv/bin/pip install -r ../eval_harness/requirements.txt
.venv/bin/pip install -e '.[dev,analysis,paper]'

# free, no model calls
./scripts/with_experiment_env.sh .venv/bin/python scripts/build_topic_okf_bundle.py
./scripts/with_experiment_env.sh .venv/bin/python scripts/measure_embedding_truncation.py
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_retrieval_diagnostics.py
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_topic_retrieval_comparison.py

# billable, about 8 US dollars
./scripts/with_experiment_env.sh .venv/bin/python scripts/run_hybrid_ab_experiment.py --stage all

# regenerate this paper from the records
.venv/bin/python paper/render_okf_vs_rag_paper.py
```

Every table above is generated by that last command from `results/retrieval_diagnostics/`, `results/topic_okf/`, `results/hybrid_ab/` and `results/embedding_truncation.json`. No number is typed by hand. Measured spend for the A/B was $2.97 for generation and $4.95 for judging.

## Declarations

Funding: AiDash.

Competing interests: none declared for this study. An unrelated in-house retrieval pipeline is withheld from the work and appears in no experiment, table, or claim.

This study used hosted language models to generate and to score answers. No human participants or personal data were involved.

## References

1. Open Knowledge Format (OKF), Version 0.2, Google Cloud. Pinned specification, commit `3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`. <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md>
2. P. Lewis et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020. <https://arxiv.org/abs/2005.11401>
3. V. Karpukhin et al. Dense Passage Retrieval for Open-Domain Question Answering. EMNLP 2020. <https://doi.org/10.18653/v1/2020.emnlp-main.550>
4. S. Robertson and H. Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. 2009. <https://doi.org/10.1561/1500000019>
5. G. V. Cormack, C. L. A. Clarke and S. Buettcher. Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. SIGIR 2009. <https://doi.org/10.1145/1571941.1572114>
6. R. Nogueira and K. Cho. Passage Re-ranking with BERT. 2019. <https://arxiv.org/abs/1901.04085>
7. A. Asai et al. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. ICLR 2024. <https://arxiv.org/abs/2310.11511>
8. Z. Jiang et al. Active Retrieval Augmented Generation (FLARE). EMNLP 2023. <https://doi.org/10.18653/v1/2023.emnlp-main.495>
9. N. Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models. NeurIPS 2021. <https://arxiv.org/abs/2104.08663>
10. L. Zheng et al. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS 2023. <https://arxiv.org/abs/2306.05685>
11. S. Holm. A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian Journal of Statistics, 1979. <https://www.jstor.org/stable/4615733>
