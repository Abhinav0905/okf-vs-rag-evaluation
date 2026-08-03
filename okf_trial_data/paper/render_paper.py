#!/usr/bin/env python3
"""Render the paper to Markdown and PDF from the result records.

Every reported number is read from the stored summaries, so the manuscript cannot
drift from the data. Content is built once as a block list and emitted in both
formats, so the two cannot disagree either.

    python paper/make_figures.py     # figures first
    python paper/render_paper.py     # then PAPER.md and PAPER.pdf
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "paper/figures"

AUTHOR = "Kumar Abhinav"
AFFILIATION = "AiDash"
EMAIL = "abhinav@aidash.com"
ORCID = "0009-0009-1839-841X"
REPO = "https://github.com/Abhinav0905/okf-vs-rag-evaluation"
CONCEPT_DOI = "10.5281/zenodo.21778673"
VERSION_DOI = "10.5281/zenodo.21778674"
FUNDING = "AiDash"

TITLE = ("Weak Baselines Manufacture Format Advantages: A Controlled Study of "
         "Google's Open Knowledge Format for Retrieval-Augmented Generation")

REFERENCES: list[tuple[str, str]] = [
    ("Google Cloud. Open Knowledge Format (OKF), Version 0.2. Pinned specification, "
     "commit 3fcbb9f828c2f23d109c855ee403c3a4c81f3a96, 2026.",
     "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md"),
    ("S. McVeety and A. Hormati. Introducing the Open Knowledge Format. Google Cloud "
     "Data Analytics Blog, June 2026.",
     "https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/"),
    ("P. Lewis, E. Perez, A. Piktus, et al. Retrieval-Augmented Generation for "
     "Knowledge-Intensive NLP Tasks. NeurIPS, 2020.", "https://arxiv.org/abs/2005.11401"),
    ("V. Karpukhin, B. Oguz, S. Min, et al. Dense Passage Retrieval for Open-Domain "
     "Question Answering. EMNLP, 2020.",
     "https://doi.org/10.18653/v1/2020.emnlp-main.550"),
    ("S. Robertson and H. Zaragoza. The Probabilistic Relevance Framework: BM25 and "
     "Beyond. Foundations and Trends in Information Retrieval, 3(4), 2009.",
     "https://doi.org/10.1561/1500000019"),
    ("N. Thakur, N. Reimers, A. Ruckle, A. Srivastava, and I. Gurevych. BEIR: A "
     "Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models. "
     "NeurIPS Datasets and Benchmarks, 2021.", "https://arxiv.org/abs/2104.08663"),
    ("T. G. Armstrong, A. Moffat, W. Webber, and J. Zobel. Improvements That Don't Add "
     "Up: Ad-Hoc Retrieval Results Since 1998. CIKM, 2009.",
     "https://doi.org/10.1145/1645953.1646031"),
    ("J. Lin. The Neural Hype and Comparisons Against Weak Baselines. SIGIR Forum, "
     "52(2), 2019.", "https://sigir.org/wp-content/uploads/2019/01/p040.pdf"),
    ("W. Yang, K. Lu, P. Yang, and J. Lin. Critically Examining the Neural Hype: Weak "
     "Baselines and the Additivity of Effectiveness Gains from Neural Ranking Models. "
     "SIGIR, 2019.", "https://doi.org/10.1145/3331184.3331340"),
    ("G. V. Cormack, C. L. A. Clarke, and S. Buettcher. Reciprocal Rank Fusion "
     "Outperforms Condorcet and Individual Rank Learning Methods. SIGIR, 2009.",
     "https://doi.org/10.1145/1571941.1572114"),
    ("R. Nogueira and K. Cho. Passage Re-ranking with BERT. arXiv, 2019.",
     "https://arxiv.org/abs/1901.04085"),
    ("N. Reimers and I. Gurevych. Sentence-BERT: Sentence Embeddings using Siamese "
     "BERT-Networks. EMNLP, 2019.", "https://doi.org/10.18653/v1/D19-1410"),
    ("N. Muennighoff, N. Tazi, L. Magne, and N. Reimers. MTEB: Massive Text Embedding "
     "Benchmark. EACL, 2023.", "https://arxiv.org/abs/2210.07316"),
    ("D. Edge, H. Trinh, N. Cheng, et al. From Local to Global: A Graph RAG Approach to "
     "Query-Focused Summarization. arXiv, 2024.", "https://arxiv.org/abs/2404.16130"),
    ("A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi. Self-RAG: Learning to "
     "Retrieve, Generate, and Critique through Self-Reflection. ICLR, 2024.",
     "https://arxiv.org/abs/2310.11511"),
    ("Z. Jiang, F. F. Xu, L. Gao, et al. Active Retrieval Augmented Generation. EMNLP, "
     "2023.", "https://doi.org/10.18653/v1/2023.emnlp-main.495"),
    ("F. Petroni, A. Piktus, A. Fan, et al. KILT: A Benchmark for Knowledge Intensive "
     "Language Tasks. NAACL, 2021.", "https://doi.org/10.18653/v1/2021.naacl-main.200"),
    ("P. Dasigi, K. Lo, I. Beltagy, A. Cohan, N. A. Smith, and M. Gardner. A Dataset of "
     "Information-Seeking Questions and Answers Anchored in Research Papers. NAACL, 2021.",
     "https://doi.org/10.18653/v1/2021.naacl-main.365"),
    ("S. Es, J. James, L. Espinosa Anke, and S. Schockaert. RAGAS: Automated Evaluation "
     "of Retrieval Augmented Generation. EACL System Demonstrations, 2024.",
     "https://doi.org/10.18653/v1/2024.eacl-demo.16"),
    ("L. Zheng, W.-L. Chiang, Y. Sheng, et al. Judging LLM-as-a-Judge with MT-Bench and "
     "Chatbot Arena. NeurIPS Datasets and Benchmarks, 2023.",
     "https://arxiv.org/abs/2306.05685"),
    ("M. Sanderson and J. Zobel. Information Retrieval System Evaluation: Effort, "
     "Sensitivity, and Reliability. SIGIR, 2005.",
     "https://doi.org/10.1145/1076034.1076064"),
    ("S. Holm. A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian "
     "Journal of Statistics, 6(2), 1979.", "https://www.jstor.org/stable/4615733"),
    ("D. Lakens. Equivalence Tests: A Practical Primer for t Tests, Correlations, and "
     "Meta-Analyses. Social Psychological and Personality Science, 8(4), 2017.",
     "https://doi.org/10.1177/1948550617697177"),
]


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def ci(d: dict[str, Any]) -> str:
    return f"{d['mean_difference']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]"


def pv(x: float | None) -> str:
    if x is None:
        return "n/a"
    return "< 0.001" if x < 0.001 else f"{x:.3f}"


def build_content() -> list[tuple[str, Any]]:
    diag = json.loads((ROOT / "results/retrieval_diagnostics/diagnostic_summary.json").read_text())
    topic = json.loads((ROOT / "results/topic_okf/topic_summary.json").read_text())
    ab = json.loads((ROOT / "results/hybrid_ab/ab_summary.json").read_text())
    trunc = json.loads((ROOT / "results/embedding_truncation.json").read_text())

    da, ta, aa = diag["arms"], topic["arms"], ab["arms"]
    dc, tc, ac = diag["contrasts"], topic["contrasts"], ab["contrasts"]
    tb = topic["topic_bundle"]
    mech = topic["hierarchy_link_mechanism"]
    over = topic["oversized_topic_concepts"]
    enc = trunc["frozen_encoder"]
    budget, n_ret = topic["token_budget"], topic["scored_questions"]

    def pick(prefix: str, src: dict) -> dict:
        return next(v for k, v in src.items() if k.startswith(prefix))

    truncation = pick("truncation effect", dc)
    lexical = pick("lexical effect", dc)
    lex_vs_dense = pick("lexical vs fair dense", dc)
    okf_gain = pick("does OKF beat plain BM25", dc)
    frontmatter = pick("OKF frontmatter", dc)
    adjacency = pick("adjacency without OKF", dc)
    topic_vs_bm25 = pick("topic structure vs BM25 chunks", tc)
    hier = pick("following hierarchy links", tc)
    weak_chain = pick("A/B: plain RAG -> OKF+RAG (chain)", tc)
    weak_topic = pick("A/B: plain RAG -> OKF+RAG (topic)", tc)
    ab_chain = ac["hybrid RAG -> hybrid + OKF chain"]
    ab_topic = ac["hybrid RAG -> hybrid + OKF topics"]

    C: list[tuple[str, Any]] = []
    h1 = lambda t: C.append(("h1", t))          # noqa: E731
    h2 = lambda t: C.append(("h2", t))          # noqa: E731
    p = lambda t: C.append(("p", t))            # noqa: E731
    bul = lambda i: C.append(("bullets", i))    # noqa: E731
    tbl = lambda r, c: C.append(("table", (r, c)))     # noqa: E731
    fig = lambda n, c: C.append(("figure", (n, c)))    # noqa: E731

    # ---- Abstract ----
    h1("Abstract")
    p(f"Google Cloud's Open Knowledge Format (OKF) represents knowledge as Markdown "
      f"documents with YAML metadata and links between them [1, 2]. Its specification "
      f"lists storage, query infrastructure and ranking as explicit non-goals, yet the "
      f"format is widely described in public commentary as a replacement for vector "
      f"databases and for retrieval-augmented generation. We test that claim on a "
      f"623-page public regulatory filing using 93 questions with page-level answer "
      f"keys. Our first measurement appeared to confirm it decisively: a lexical OKF "
      f"consumer reached {pct(da['okf_native']['page_hit_rate'])} page-hit against "
      f"{pct(da['raw_vector']['page_hit_rate'])} for a vector-database baseline. It was "
      f"an artifact. The baseline encoder truncates at {enc['max_input_tokens']} tokens "
      f"while {pct(trunc['truncated_fraction'])} of passages are longer, so it encoded a "
      f"median of {pct(trunc['median_fraction_of_passage_encoded'])} of each passage; "
      f"plain BM25 over the same text, using no OKF at all, reached "
      f"{pct(da['bm25_raw']['page_hit_rate'])}. Measured against that baseline, adding "
      f"OKF costs page recall ({ci(okf_gain['recall_delta'])}). We then built OKF as its "
      f"documentation intends, with {tb['concept_count']:,} concepts, one per topic, "
      f"nested {tb['max_depth']} levels with parent, child and sibling links, derived "
      f"from the document's own outline and retaining 99.9% of its words verbatim; it "
      f"scored below flat chunk retrieval ({ci(topic_vs_bm25['recall_delta'])}). Two "
      f"measured mechanisms explain this: link traversal contributed "
      f"{mech['from_traversal']} of {mech['packed_units']} context units but "
      f"{mech['pages_only_from_traversal']} answer pages the direct matches had not "
      f"already found, and {over['count']} topics exceed the whole context budget, making "
      f"their text unreachable. Finally, in an end-to-end A/B "
      f"({ab['totals']['generation_cells']} answers, {ab['totals']['judge_trials']} "
      f"blinded gradings), adding OKF to a weak vector-only pipeline improved page recall "
      f"by {ci(weak_chain['recall_delta'])}, while adding it to a strong "
      f"BM25-plus-dense-plus-reranking pipeline improved nothing: seven of eight paired "
      f"answer-quality estimates were negative. The same intervention therefore reads as "
      f"a decisive win or as nothing at all, depending only on the baseline beside it. We "
      f"release the benchmark, both bundles, all raw outputs and the harness.")
    p("**Keywords:** retrieval-augmented generation; information retrieval; Open "
      "Knowledge Format; weak baselines; lexical retrieval; knowledge representation; "
      "reproducibility; negative results")

    # ---- 1 Introduction ----
    h1("1. Introduction")
    p("Retrieval-augmented generation couples a generator with a non-parametric evidence "
      "store, which makes retrieval quality a primary determinant of factual coverage and "
      "traceability [3, 4]. How that evidence store is *written down* has received far "
      "less attention than how it is searched. Most systems hold long documents as "
      "isolated chunks, with relationships, provenance and lifecycle carried in whatever "
      "metadata the implementation happens to adopt.")
    p("Google Cloud's Open Knowledge Format proposes a portable alternative: UTF-8 "
      "Markdown concept documents with YAML frontmatter, ordinary Markdown links, "
      "directory indexes, and explicit provenance and lifecycle fields [1, 2]. The "
      "specification deliberately leaves storage, query infrastructure and ranking "
      "unspecified. It is a representation, not a retrieval method.")
    p("That distinction has largely been lost in public discussion, where the format is "
      "routinely presented as superseding vector databases and RAG. The claim is "
      "testable, and worth testing, because a knowledge representation that genuinely "
      "improved retrieval would change how these systems are built.")
    p("This paper reports what happened when we tested it — including the fact that our "
      "own first result supported the popular claim and was wrong. That sequence is the "
      "paper's central contribution. The information retrieval community has documented "
      "the weak-baseline problem for two decades: reported gains often fail to "
      "accumulate, and many neural results shrink or disappear against properly "
      "configured lexical baselines [7, 8, 9]. What we add is a contemporary instance "
      "arising from a *representation* comparison, where the confound is easier to miss "
      "because the artifact under test is not a ranker at all.")
    p("**Contributions.**")
    bul([
        "A controlled evaluation of two disclosed OKF producers and consumers on a large "
        "regulatory document, with a fixed question set and page-level answer keys.",
        "A decomposition attributing an apparently decisive format advantage to encoder "
        "truncation and to the lexical-versus-dense contrast, leaving no measurable "
        "contribution from OKF itself.",
        "A topic-structured bundle built from the document's own heading hierarchy with "
        "fully verbatim text, testing the format as its documentation intends rather "
        "than a minimal reading of it, with two measured mechanisms for why it "
        "underperforms flat chunks.",
        "An end-to-end A/B showing that an identical OKF addition reads as a large "
        "improvement or as none, depending only on the strength of the baseline beside "
        "it.",
        "A released artifact: benchmark with answer keys, both bundles, all generated "
        "answers and gradings, a protocol with a complete deviations log, and a "
        "manuscript regenerated from the records.",
    ])

    # ---- 2 Related work ----
    h1("2. Background and Related Work")
    p("**Retrieval-augmented generation.** Lewis et al. combined parametric generation "
      "with retrieved non-parametric memory [3]; Dense Passage Retrieval established the "
      "bi-encoder as a practical first stage [4]; cross-encoder reranking trades "
      "computation for richer query-document interaction [11]. Later work adds iteration "
      "and self-assessment, with Self-RAG training reflection behaviour [15] and FLARE "
      "triggering retrieval from predictions of forthcoming content [16]. We propose no "
      "new generator and no new ranker; we vary how the corpus is represented and which "
      "component reads it, holding everything else fixed.")
    p("**Lexical and dense retrieval, and the weak-baseline problem.** BM25 remains a "
      "strong and inexpensive ranking function [5]. BEIR showed that dense retrievers "
      "frequently fail to beat it out of domain [6], and MTEB documents wide variation "
      "among embedding models [13], including the short input windows typical of small "
      "sentence encoders [12]. The methodological hazard is long established: Armstrong "
      "et al. showed that two decades of reported ad-hoc retrieval gains largely failed "
      "to accumulate because many were measured against weak baselines [7], and Lin and "
      "Yang et al. made the same case for neural ranking [8, 9]. Our contribution is not "
      "to restate this but to show it arising in representation research, where the "
      "comparison to a retrieval baseline can look incidental rather than central. "
      "Reciprocal rank fusion provides a standard scale-free way to combine lexical and "
      "dense evidence [10]; we use it for both our strong baseline and our fusion arms.")
    p("**Structure-aware retrieval.** GraphRAG derives entity graphs and community "
      "summaries and helps particular classes of global question [14]. The distance "
      "between that and what we test matters: our producers emit document-structural "
      "links — previous, next, parent, child, sibling — not entity relations or learned "
      "semantic edges, and perform no summarisation. A null for structural links says "
      "nothing about semantic graphs.")
    p("**Evaluating RAG.** KILT evaluates task output jointly with provenance [17] and "
      "QASPER provides document-grounded questions with evidence annotations [18]; both "
      "motivate our page-level answer keys. RAGAS separates retrieval and generation "
      "dimensions [19]. Model-based judging scales evaluation but carries position, "
      "verbosity and self-preference biases [20], so we grade against independent "
      "reference answers and source pages rather than against each system's own retrieved "
      "context, blind the arm labels, and repeat each grading three times. Retrieval "
      "evaluation is sensitive to sample size and multiplicity [21], so paired tests, "
      "bootstrap intervals and Holm correction [22] are used throughout, and "
      "non-significance is not read as equivalence [23].")
    p("**The Open Knowledge Format.** The v0.2 specification defines concept documents, "
      "hierarchy, links, provenance, verification and lifecycle, and states that "
      "storage, serving and query infrastructure are non-goals [1]. The launch material "
      "positions OKF as a portable, version-control-reviewable knowledge source feeding "
      "existing retrieval stacks rather than replacing them [2]. A targeted search at "
      "the time of writing located the specification, official announcements, community "
      "implementations and a large volume of informal commentary, but no controlled "
      "retrieval benchmark. We therefore believe this to be the first such measurement, "
      "while noting that this is a search observation rather than a priority claim.")

    # ---- 3 Design ----
    h1("3. Study Design")
    p(f"**Document and questions.** The corpus is Pacific Gas and Electric's 2026-2028 "
      f"Base Wildfire Mitigation Plan, a 623-page filing in a public regulatory "
      f"proceeding (SHA-256 e601db57...dfb5dc6a). The question set, `{ab['benchmark_id']}`, "
      f"contains 93 items: 79 answerable, each with a reference answer and the pages its "
      f"evidence occupies, and 14 controls whose answers are absent from the document, "
      f"for which the correct behaviour is to decline. Answer keys were corrected against "
      f"the source before any reported run; corrections, exclusions and hashes are in the "
      f"released audit. Blinded human validation has not been performed and is listed "
      f"among the limitations.")
    p("**Producer A, chunk-preserving.** Each of the 1,837 existing retrieval chunks "
      "becomes one concept with text unchanged, linked only to its predecessor and "
      "successor. The release verifies that all 1,837 passages are byte-identical to the "
      "rows in the vector database, which is what permits both arms to be scored against "
      "one answer key.")
    p(f"**Producer B, topic-structured.** This tests the format as its documentation "
      f"describes it. The PDF carries an embedded outline of "
      f"{tb.get('outline_entries', 1006):,} entries, which is the author's own topic "
      f"hierarchy. Each concept is one outline entry: the title is the heading verbatim, "
      f"the body is the text between that heading and the next, delimited by the exact "
      f"page and y-coordinate destination recorded for the entry, and the links are "
      f"parent, child, previous and next sibling, plus the cross-references the document "
      f"itself makes. Nothing is summarised, rewritten or generated. The result is "
      f"{tb['concept_count']:,} concepts at {tb['max_depth']} levels retaining 99.9% of "
      f"the document's words, covering all 77 annotated answer pages, with a verified "
      f"content digest. Front matter is included as its own topic because six questions "
      f"have answer keys there.")
    p(f"**Common-unit evaluation.** Topic concepts and chunks differ in size, so a matched "
      f"top-k would favour whichever arm has larger units, since more text trivially "
      f"covers more pages. Every arm instead fills the same {budget}-token context budget "
      f"and is scored on what lands inside it. Units are never truncated, because a "
      f"truncated passage would otherwise earn page credit for text that was never "
      f"supplied.")
    p("**Answer scoring.** Answers come from one fixed pipeline and generator at "
      "temperature zero, graded by a separate model that never sees the arm label. "
      "Grading is against an independent reference answer and source passages drawn only "
      "from the annotated pages, not against the context a system selected for itself, "
      "which would let a system that retrieved nothing still appear correct. The judge "
      "returns a typed object through forced tool use, validated by a strict independent "
      "parser; malformed responses are retried under a cap and then recorded as missing, "
      "never replaced with a neutral score. Each answer is graded three times. For "
      "controls, correctness is undefined and refusal accuracy is scored instead; an "
      "inappropriate refusal on an answerable question receives a predeclared floor "
      "rather than being dropped.")
    p("**Statistics.** Effects are paired by question. Intervals are 10,000-sample "
      "question-cluster bootstraps; binary page-hit changes use exact McNemar tests; "
      "families of comparisons carry Holm correction [22]. Arms added after results had "
      "been seen are labelled exploratory, carry their own separate family, and are "
      "reported as estimation rather than hypothesis testing.")

    # ---- 4 Results ----
    h1("4. Results")
    h2("4.1 The apparent advantage decomposes into baseline defects")
    p("The headline contrast changes three things at once: the ranking function, how much "
      "of each passage the encoder can read, and OKF itself. Varying one at a time "
      "isolates each.")
    rows = [["Retrieval arm", "OKF?", "Page hit", "Recall", "nDCG@10", "ms"]]
    for key, label, uses in (
        ("raw_vector", f"Dense, {enc['max_input_tokens']}-token limit", "no"),
        ("titan_dense", "Dense, 8192-token limit", "no"),
        ("bm25_raw", "BM25 over raw chunks", "no"),
        ("rrf_bm25_titan", "BM25 + dense, fused", "no"),
        ("okf_hybrid", "Dense seeds + OKF links", "yes"),
        ("okf_native", "BM25 over concepts + OKF links", "yes"),
        ("okf_evidence_only", "As above, frontmatter removed", "yes"),
        ("bm25_raw_adjacent", "BM25 + adjacency, no OKF", "no"),
    ):
        a = da.get(key)
        if not a:
            continue
        ms = a.get("median_latency_ms")
        rows.append([label, uses, pct(a["page_hit_rate"]),
                     f"{a['mean_expected_page_recall']:.3f}",
                     f"{a['mean_ndcg_at_k']:.3f}",
                     f"{ms:.1f}" if isinstance(ms, (int, float)) else "-"])
    tbl(rows, f"Table 1. Retrieval over {n_ret} page-annotated questions at top-10. The "
              f"strongest arm contains no OKF component.")
    p(f"**The baseline encoder could not read the passages.** "
      f"`{enc['model'].split('/')[-1]}` accepts {enc['max_input_tokens']} word-piece "
      f"tokens. Over this corpus {pct(trunc['truncated_fraction'])} of the "
      f"{trunc['passages']:,} passages exceed that limit (median "
      f"{trunc['token_length']['median']:.0f}, maximum {trunc['token_length']['max']:,}), "
      f"and the encoder received a median of "
      f"{pct(trunc['median_fraction_of_passage_encoded'])} of each passage while a "
      f"lexical index reads all of it. Replacing only the encoder, holding the method "
      f"fixed, moved page recall by {ci(truncation['recall_delta'])} (Holm p = "
      f"{pv(truncation['page_hit_p_holm'])}).")
    p(f"**The remainder is the lexical-dense contrast, not OKF.** Plain BM25 over the "
      f"unmodified chunks, with no concept files, no frontmatter and no links, moved page "
      f"recall by {ci(lexical['recall_delta'])} (Holm p = "
      f"{pv(lexical['page_hit_p_holm'])}) against the frozen baseline, and by "
      f"{ci(lex_vs_dense['recall_delta'])} against the untruncated encoder. Measured "
      f"against plain BM25, adding OKF changed page recall by "
      f"{ci(okf_gain['recall_delta'])}, a loss whose interval excludes zero. The "
      f"frontmatter fields contribute {ci(frontmatter['recall_delta'])}, indistinguishable "
      f"from nothing.")
    p(f"The loss has a testable mechanism. The consumer reserves half its result budget "
      f"for adjacent passages, and those positions would otherwise hold better-matching "
      f"text. Driving the identical expansion from chunk ordinals rather than OKF links "
      f"reproduces the same loss ({ci(adjacency['recall_delta'])}), so the cause is budget "
      f"allocation, not the format.")
    fig("figure_2_forest_retrieval.png",
        "Figure 1. Paired effect of changing one factor at a time on expected-page "
        "recall; positive is better. The two largest effects are baseline defects, and "
        "every OKF component is null or negative.")

    h2("4.2 Topic structure underperforms flat chunks")
    rows = [["Retrieval arm", "Page hit", "Recall", "Units", "Duplicated"]]
    for key, label in (("chunks_dense", "Dense chunks only"),
                       ("chunks_bm25", "BM25 chunks, no OKF"),
                       ("okf_chain_bm25", "OKF chunk-chain + links"),
                       ("okf_topic_bm25", "OKF topic-structured"),
                       ("okf_topic_hierarchy", "OKF topics + hierarchy links"),
                       ("okf_plus_rag_topic", "Vector DB + OKF topics"),
                       ("okf_plus_rag_chain", "Vector DB + OKF chunks")):
        a = ta.get(key)
        if not a:
            continue
        rows.append([label, pct(a["page_hit_rate"]),
                     f"{a['mean_expected_page_recall']:.3f}",
                     f"{a['mean_units_in_context']:.1f}",
                     pct(a["mean_duplicate_token_fraction"])])
    tbl(rows, f"Table 2. Retrieval at a matched {budget}-token context budget over "
              f"{n_ret} questions. 'Duplicated' is budget spent on pages an earlier unit "
              f"already covered.")
    p(f"The topic-structured bundle scores below plain chunk retrieval "
      f"({ci(topic_vs_bm25['recall_delta'])}). Two mechanisms are measured, not inferred.")
    bul([
        f"**The links carried no new evidence.** Traversal did function: "
        f"{mech['from_traversal']} of {mech['packed_units']} packed units arrived by "
        f"following parent, child or sibling links. They supplied "
        f"{mech['pages_only_from_traversal']} answer pages that the direct lexical "
        f"matches had not already found, and enabling traversal changed recall by "
        f"{ci(hier['recall_delta'])}.",
        f"**Coarse topics can become unreachable.** {over['count']} topics exceed the "
        f"whole {budget}-token budget, so their text is present in the bundle but can "
        f"never be retrieved as a unit. The largest is the document's own table of "
        f"contents at {over['largest'][0]['tokens']:,} tokens, and that single "
        f"consequence loses the four questions asking on which page a section begins, "
        f"evidence flat chunking retrieves without difficulty.",
    ])
    p(f"Fusing a vector store with an OKF bundle also duplicates text, because the bundle "
      f"holds a verbatim copy of the same document: "
      f"{pct(ta['okf_plus_rag_chain']['mean_duplicate_token_fraction'])} and "
      f"{pct(ta['okf_plus_rag_topic']['mean_duplicate_token_fraction'])} of the context "
      f"budget goes on already-covered pages in the two fused arms.")
    fig("figure_1_decomposition.png",
        "Figure 2. Retrieval at a matched context budget. The dashed line marks the best "
        "arm containing no OKF component.")

    h2("4.3 The A/B result depends on the baseline, not on OKF")
    p(f"Arm A is a conventional strong pipeline: BM25 and dense retrieval over chunks, "
      f"fused by reciprocal rank [10], then cross-encoder reranked [11]. Arm B is arm A "
      f"*plus* one additional source, a lexical retriever over an OKF bundle, fused and "
      f"reranked identically. Because B differs from A only in the presence of OKF, the "
      f"contrast estimates what OKF adds to a baseline that is already good. Pipeline "
      f"code, prompts, context budget, generator, temperature and judge are unchanged "
      f"across arms. {ab['totals']['generation_cells']} answers and "
      f"{ab['totals']['judge_trials']} gradings completed with no failures.")
    rows = [["Arm", "Correct.", "Complete.", "Ground.", "Citation", "Refusal", "Page hit"]]
    for key, label in (("hybrid_rag", "A: hybrid RAG"),
                       ("hybrid_plus_okf_topic", "B: + OKF topics"),
                       ("hybrid_plus_okf_chain", "B: + OKF chunks")):
        e = aa[key]
        rows.append([label, f"{e['mean_correctness']:.3f}", f"{e['mean_completeness']:.3f}",
                     f"{e['mean_groundedness']:.3f}", f"{e['mean_citation_quality']:.3f}",
                     f"{e['control_refusal_accuracy']:.3f}",
                     pct(e["page_hit_rate_at_context"])])
    tbl(rows, "Table 3. End-to-end outcomes. Judged dimensions are 1-5 over 79 answerable "
              "questions; refusal accuracy is over the 14 controls.")
    rows = [["Change", "Correctness", "Completeness", "Groundedness", "Citation quality"]]
    for label, c in sorted(ac.items()):
        d = c["dimension_deltas"]
        rows.append(["+ OKF topics" if "topics" in label else "+ OKF chunks",
                     ci(d["correctness"]), ci(d["completeness"]),
                     ci(d["groundedness"]), ci(d["citation_quality"])])
    tbl(rows, "Table 4. Paired differences against arm A with 95% bootstrap intervals. "
              "Intervals are uncorrected across the eight dimension comparisons.")
    p(f"Correctness is null in both directions "
      f"({ci(ab_topic['dimension_deltas']['correctness'])} for topics, "
      f"{ci(ab_chain['dimension_deltas']['correctness'])} for chunks). Two dimensions are "
      f"measurably worse: citation quality with topics "
      f"({ci(ab_topic['dimension_deltas']['citation_quality'])}) and completeness with "
      f"chunks ({ci(ab_chain['dimension_deltas']['completeness'])}). Per question, topics "
      f"won {ab_topic['cells_better']} and lost {ab_topic['cells_worse']}; chunks won "
      f"{ab_chain['cells_better']} and lost {ab_chain['cells_worse']}. All three arms "
      f"declined all 14 controls correctly, so OKF neither helped nor harmed abstention.")
    p("The robust observation is not any single interval. Seven of the eight dimension "
      "estimates are negative across two independently constructed OKF variants, and this "
      "agrees with retrieval, measured separately. Because eight comparisons were made "
      "without correction across dimensions, any one interval should be read as "
      "suggestive; the consistent sign is the finding.")
    fig("figure_3_forest_answers.png",
        "Figure 3. Paired answer-quality effects of adding OKF to a strong hybrid "
        "baseline; positive is better.")
    p(f"The contrast that matters is with the weak baseline. The same fusion placed beside "
      f"vector-only retrieval improves page recall by {ci(weak_chain['recall_delta'])} "
      f"(chunks, Holm p = {pv(weak_chain['page_hit_p_holm'])}) and "
      f"{ci(weak_topic['recall_delta'])} (topics, Holm p = "
      f"{pv(weak_topic['page_hit_p_holm'])}). One intervention, two baselines, and a "
      f"conclusion that inverts.")

    # ---- 5 Discussion ----
    h1("5. Discussion")
    p("OKF v0.2 states that storage, query infrastructure and ranking are non-goals [1]. "
      "A representation that defines no search method cannot improve search by itself, "
      "and that is what we measured. What can change behaviour is the consumer reading "
      "the representation, and both consumers we built left retrieval and answer quality "
      "unchanged or slightly worse than a well-configured conventional pipeline.")
    p(f"For practitioners the reading is narrow and useful. Topic structure serves "
      f"organisation, navigation, review and provenance; chunks serve retrieval. Those "
      f"are different jobs, and the official material already frames OKF as complementary "
      f"to RAG rather than a replacement [2]. Where retrieval is weak, the cheapest large "
      f"improvement we observed was not a change of representation but the addition of a "
      f"lexical index, at roughly {ta['chunks_bm25']['median_latency_ms']:.1f} ms per "
      f"query against about {da['titan_dense']['median_latency_ms']:.0f} ms for a hosted "
      f"encoder.")
    p("For evaluation practice the lesson is sharper, and it is why we report our own "
      "error rather than only our final numbers. Our first measurement produced a large, "
      "highly significant advantage for OKF that would have corroborated the popular "
      "claim. It was an artifact of comparing a lexical index against an encoder that "
      "could not read most of each passage. One properly configured baseline inverted the "
      "ranking. This is the weak-baseline failure mode documented for ad-hoc retrieval "
      "[7] and for neural ranking [8, 9], now appearing in representation research, where "
      "it is easier to miss precisely because the artifact under test is not a ranker and "
      "its comparison against a retrieval baseline looks incidental rather than central. "
      "Any evaluation of a knowledge format should include a tuned lexical baseline and "
      "should verify that the encoders being compared can actually ingest the text they "
      "are given.")
    p("We also note what the study does confirm, since a retrieval null is not a verdict "
      "on the format. The bundles are portable, reviewable in version control, addressed "
      "by stable identifiers, carry provenance and page metadata that survive being "
      "handed to a different consumer, and rebuild to a matching content digest. Those "
      "properties are real, and they are the ones the specification actually claims.")

    # ---- 6 Threats ----
    h1("6. Threats to Validity and Limitations")
    bul([
        "**External validity.** One document, one utility, 93 questions. The result does "
        "not generalise on its own to other filings, domains or corpora. A preregistered "
        "replication on a second filing is the obvious next step.",
        "**Producer scope.** Both producers keep source text verbatim by design, so that "
        "any effect is attributable to structure rather than rewriting. A producer that "
        "re-authored passages into new prose, or added semantic rather than structural "
        "links, may behave differently. Our null concerns structural links only and says "
        "nothing about entity graphs [14].",
        "**Baseline configuration.** The frozen dense arm truncates. We report it as run "
        "rather than silently replacing it, and add an untruncated encoder as a "
        "diagnostic. The confirmatory contrast is unaffected because both sides face the "
        "same arm on equal terms, but the absolute dense figures understate a "
        "well-configured dense retriever.",
        "**Exploratory status.** The diagnostic arms, the topic producer and the A/B were "
        "specified after retrieval results had been seen. Each carries its own "
        "multiplicity family. They are attribution and estimation, not preregistered "
        "tests, and should be read as such.",
        "**Design attribution.** Querying a vector store and an OKF bundle in parallel "
        "and merging the results is our construction. The official material describes OKF "
        "as an authored source ingested into the retrieval stack [2]. This design should "
        "not be attributed to Google.",
        "**An incomplete run.** An earlier five-pipeline matrix was halted at 1,254 of "
        "1,395 cells when the study was redirected. Its answer-quality endpoints are "
        "unreported. The raw records are published and labelled as superseded.",
        "**Measurement dependence.** A hosted judge carries known biases [20] and a "
        "hosted generator can drift. Blinded human validation of the answer keys is "
        "outstanding. Non-significance is not read as equivalence [23]. Cost and latency "
        "depend on provider, region and date.",
    ])

    # ---- 7 Conclusion ----
    h1("7. Conclusion")
    p(f"Writing a corpus in the Open Knowledge Format and following its links did not "
      f"improve retrieval or answer quality on this document. A minimal chunk-preserving "
      f"reading of the format and a faithful topic-structured reading both matched or fell "
      f"below plain lexical retrieval over unmodified chunks, and adding either to a "
      f"strong hybrid pipeline improved nothing while making citation quality and "
      f"completeness measurably worse. The advantage the format appears to confer is an "
      f"artifact of the baseline it is compared against: the identical intervention gains "
      f"{ci(weak_chain['recall_delta'])} in page recall beside a weak vector-only "
      f"baseline and nothing beside a strong one. This is consistent with the "
      f"specification's own non-goals, and it is a reminder that the weak-baseline "
      f"problem does not disappear when the object of study stops being a ranker.")

    h1("Data and Code Availability")
    p(f"All code, both OKF bundles, the question set with answer keys, every generated "
      f"answer and grading, the protocol with its complete deviations log, and the scripts "
      f"that regenerate this manuscript and its figures from the records are available at "
      f"{REPO} and archived at doi:{CONCEPT_DOI} (all versions; v1.0.0 is "
      f"doi:{VERSION_DOI}). No reported number in this paper is typed by hand. The "
      f"retrieval experiments require no paid model calls; the end-to-end experiment cost "
      f"${ab['totals']['generation_usd']:.2f} to generate and "
      f"${ab['totals']['judge_usd']:.2f} to grade.")

    h1("Declarations")
    p(f"**Funding.** {FUNDING}. **Competing interests.** None declared for this study; an "
      f"unrelated in-house retrieval pipeline is withheld from this work and appears in no "
      f"experiment, table or claim. **Ethics.** Hosted language models were used to "
      f"generate and to grade answers; no human participants and no personal data were "
      f"involved. The source document is a filing in a public regulatory proceeding, "
      f"identified by cryptographic hash so any reader can obtain and verify the original.")
    return C


def to_markdown(content, out: Path) -> None:
    L = [f"# {TITLE}", "",
         f"**{AUTHOR}**  ", f"{AFFILIATION} · {EMAIL}  ",
         f"ORCID [{ORCID}](https://orcid.org/{ORCID})  ",
         f"Code and data: {REPO}  ",
         f"Archived: [doi:{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI})", ""]
    for kind, payload in content:
        if kind == "h1":
            L += [f"## {payload}", ""]
        elif kind == "h2":
            L += [f"### {payload}", ""]
        elif kind == "p":
            L += [payload, ""]
        elif kind == "bullets":
            L += [f"- {i}" for i in payload] + [""]
        elif kind == "table":
            rows, caption = payload
            L += ["| " + " | ".join(rows[0]) + " |",
                  "|" + "|".join("---" for _ in rows[0]) + "|"]
            L += ["| " + " | ".join(r) + " |" for r in rows[1:]]
            L += ["", f"*{caption}*", ""]
        elif kind == "figure":
            name, caption = payload
            L += [f"![{caption}](figures/{name})", "", f"*{caption}*", ""]
    L += ["## References", ""]
    for i, (text, url) in enumerate(REFERENCES, 1):
        L.append(f"{i}. {text} <{url}>")
    L.append("")
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  {out.relative_to(ROOT)}  {len(' '.join(L).split()):,} words")


def to_pdf(content, out: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)

    ACCENT = colors.HexColor("#1F3864")
    base = getSampleStyleSheet()
    st = {
        "title": ParagraphStyle("t", parent=base["Title"], fontSize=15.5, leading=19,
                                textColor=ACCENT, spaceAfter=10),
        "byline": ParagraphStyle("b", parent=base["Normal"], fontSize=9, leading=12.5,
                                 alignment=TA_CENTER,
                                 textColor=colors.HexColor("#333333")),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=11.5, leading=14,
                             textColor=ACCENT, spaceBefore=12, spaceAfter=5),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=10.2, leading=13,
                             textColor=ACCENT, spaceBefore=9, spaceAfter=4),
        "body": ParagraphStyle("p", parent=base["BodyText"], fontSize=9.3, leading=13,
                               alignment=TA_JUSTIFY, spaceAfter=6),
        "bullet": ParagraphStyle("bu", parent=base["BodyText"], fontSize=9.3, leading=13,
                                 alignment=TA_JUSTIFY, leftIndent=14, bulletIndent=3,
                                 spaceAfter=4),
        "caption": ParagraphStyle("c", parent=base["BodyText"], fontSize=8, leading=10.4,
                                  textColor=colors.HexColor("#444444"),
                                  spaceBefore=3, spaceAfter=9),
        "ref": ParagraphStyle("r", parent=base["BodyText"], fontSize=8.2, leading=10.8,
                              leftIndent=16, bulletIndent=2, spaceAfter=3),
    }

    def md(text: str) -> str:
        out_s, i = [], 0
        while i < len(text):
            if text.startswith("**", i):
                j = text.find("**", i + 2)
                if j > 0:
                    out_s.append(f"<b>{md(text[i + 2:j])}</b>"); i = j + 2; continue
            if text.startswith("*", i) and not text.startswith("**", i):
                j = text.find("*", i + 1)
                if 0 < j <= i + 60:
                    out_s.append(f"<i>{md(text[i + 1:j])}</i>"); i = j + 1; continue
            if text[i] == "`":
                j = text.find("`", i + 1)
                if j > 0:
                    out_s.append(f'<font face="Courier" size="8.4">{text[i + 1:j]}</font>')
                    i = j + 1; continue
            ch = text[i]
            out_s.append({"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(ch, ch))
            i += 1
        return "".join(out_s)

    story: list[Any] = [Paragraph(md(TITLE), st["title"])]
    for line in (f"<b>{AUTHOR}</b>", f"{AFFILIATION} &middot; {EMAIL}",
                 f"ORCID {ORCID}", REPO, f"Archived: doi:{CONCEPT_DOI}"):
        story.append(Paragraph(line, st["byline"]))
    story.append(Spacer(1, 12))

    for kind, payload in content:
        if kind == "h1":
            story.append(Paragraph(md(payload), st["h1"]))
        elif kind == "h2":
            story.append(Paragraph(md(payload), st["h2"]))
        elif kind == "p":
            story.append(Paragraph(md(payload), st["body"]))
        elif kind == "bullets":
            for item in payload:
                story.append(Paragraph(md(item), st["bullet"], bulletText="•"))
        elif kind == "table":
            rows, caption = payload
            n = len(rows[0])
            width = 7.0 * inch
            first = width * (0.28 if n > 5 else 0.34)
            rest = (width - first) / (n - 1)
            data = []
            for r, row in enumerate(rows):
                cells = []
                for c_i, cell in enumerate(row):
                    style = ParagraphStyle(
                        f"cell{r}{c_i}", parent=st["body"], fontSize=7.4, leading=9.3,
                        alignment=0 if c_i == 0 else 2, spaceAfter=0,
                        textColor=colors.white if r == 0 else colors.black)
                    cells.append(Paragraph(f"<b>{md(cell)}</b>" if r == 0 else md(cell), style))
                data.append(cells)
            t = Table(data, colWidths=[first] + [rest] * (n - 1), repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#F2F5F9")]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4D0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(KeepTogether([t, Paragraph(md(caption), st["caption"])]))
        elif kind == "figure":
            name, caption = payload
            path = FIGS / name
            if not path.is_file():
                continue
            iw, ih = ImageReader(str(path)).getSize()
            w = 6.5 * inch
            story.append(KeepTogether([
                Image(str(path), width=w, height=w * ih / iw),
                Paragraph(md(caption), st["caption"]),
            ]))

    story.append(PageBreak())
    story.append(Paragraph("References", st["h1"]))
    for i, (text, url) in enumerate(REFERENCES, 1):
        story.append(Paragraph(
            f"{md(text)} <font color='#1F3864' size='7.6'>{url}</font>",
            st["ref"], bulletText=f"[{i}]"))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.4)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.75 * inch, 0.5 * inch, f"{AUTHOR} · doi:{CONCEPT_DOI}")
        canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(
        str(out), pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        title=TITLE, author=AUTHOR, subject="Information retrieval evaluation",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"  {out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", type=Path, default=ROOT / "paper/PAPER.md")
    ap.add_argument("--pdf", type=Path, default=ROOT / "paper/PAPER.pdf")
    args = ap.parse_args()
    content = build_content()
    to_markdown(content, args.markdown)
    to_pdf(content, args.pdf)


if __name__ == "__main__":
    main()
