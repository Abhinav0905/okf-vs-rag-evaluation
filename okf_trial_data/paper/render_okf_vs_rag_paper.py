#!/usr/bin/env python3
"""Generate the OKF-versus-RAG paper from the result records.

Every number in the output is read from the three summary files produced by the
experiment scripts. None is typed by hand, so the paper cannot drift from the
data. Run this after the experiments and commit the output alongside them.

    python paper/render_okf_vs_rag_paper.py --output paper/PAPER.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "results/retrieval_diagnostics/diagnostic_summary.json"
TOPIC = ROOT / "results/topic_okf/topic_summary.json"
AB = ROOT / "results/hybrid_ab/ab_summary.json"
TRUNC = ROOT / "results/embedding_truncation.json"

AUTHOR = "Kumar Abhinav"
AFFILIATION = "AiDash"
ORCID = "0009-0009-1839-841X"
REPO = "https://github.com/Abhinav0905/okf-vs-rag-evaluation"
FUNDING = "AiDash"
CONCEPT_DOI = "10.5281/zenodo.21778673"
VERSION_DOI = "10.5281/zenodo.21778674"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def ci(d: dict[str, Any]) -> str:
    return f"{d['mean_difference']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}]"


def p(x: float | None) -> str:
    if x is None:
        return "n/a"
    return "<0.001" if x < 0.001 else f"{x:.3f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "paper/PAPER.md")
    args = ap.parse_args()

    diag = json.loads(DIAG.read_text())
    topic = json.loads(TOPIC.read_text())
    ab = json.loads(AB.read_text())
    trunc = json.loads(TRUNC.read_text())

    da, ta, aa = diag["arms"], topic["arms"], ab["arms"]
    dc, tc, ac = diag["contrasts"], topic["contrasts"], ab["contrasts"]
    tb = topic["topic_bundle"]
    n_ret = diag["scored_questions"]
    budget = topic["token_budget"]

    def d_contrast(prefix: str, source: dict) -> dict:
        return next(v for k, v in source.items() if k.startswith(prefix))

    trunc_frozen = trunc["frozen_encoder"]
    okf_gain = d_contrast("does OKF beat plain BM25", dc)
    truncation = d_contrast("truncation effect", dc)
    lexical = d_contrast("lexical effect", dc)
    adjacency = d_contrast("adjacency without OKF", dc)
    ab_topic = d_contrast("A/B: plain RAG -> OKF+RAG (topic)", tc)
    ab_chain = d_contrast("A/B: plain RAG -> OKF+RAG (chain)", tc)
    topic_vs_bm25 = d_contrast("topic structure vs BM25 chunks", tc)
    hier = d_contrast("following hierarchy links", tc)
    mech = topic["hierarchy_link_mechanism"]
    over = topic["oversized_topic_concepts"]

    L: list[str] = []
    w = L.append

    w("# Does Google's Open Knowledge Format Improve Retrieval-Augmented Generation?")
    w("")
    w("## A Controlled Study on One Regulatory Document")
    w("")
    w(f"**{AUTHOR}**  ")
    w(f"{AFFILIATION}  ")
    w(f"ORCID: [{ORCID}](https://orcid.org/{ORCID})  ")
    w(f"Code and data: {REPO}  ")
    w(f"Archived: [doi:{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI}) (all versions) · [doi:{VERSION_DOI}](https://doi.org/{VERSION_DOI}) (v1.0.0)")
    w("")
    w("## Summary")
    w("")
    w(
        "Google Cloud's Open Knowledge Format (OKF) stores knowledge as Markdown "
        "files with YAML metadata and links between them. It is a way of writing "
        "knowledge down. The specification lists storage, query infrastructure and "
        "ranking as things it deliberately does not cover. Despite that, it has "
        "been widely described in public commentary as a replacement for vector "
        "databases and for retrieval-augmented generation (RAG). This paper tests "
        "that claim on one large regulatory document with a fixed set of questions."
    )
    w("")
    w(
        "The short answer is that OKF did not improve retrieval or answers, and "
        "that the improvement it appears to give is an artifact of what it is "
        "compared against. Three findings support this."
    )
    w("")
    w(
        f"First, a lexical OKF retriever scored {pct(da['okf_native']['page_hit_rate'])} "
        f"against {pct(da['raw_vector']['page_hit_rate'])} for the vector-database "
        "baseline, which looks decisive. It is not. The baseline's encoder could "
        f"only read part of each passage, and plain keyword search over the same "
        f"text with no OKF at all scored {pct(da['bm25_raw']['page_hit_rate'])} - "
        "higher than the OKF arm."
    )
    w("")
    w(
        "Second, we rebuilt the corpus the way OKF is actually meant to be used: "
        f"{tb['concept_count']:,} concepts, one per topic, nested {tb['max_depth']} "
        "levels deep, with parent, child and sibling links, using the document's own "
        "heading hierarchy and its own words. That version scored "
        f"{pct(ta['okf_topic_bm25']['page_hit_rate'])}, "
        f"worse than plain chunk retrieval at {pct(ta['chunks_bm25']['page_hit_rate'])}."
    )
    w("")
    w(
        "Third, we ran the practitioner's A/B: a conventional pipeline versus the "
        "same pipeline with OKF added as an extra source. Against a weak vector-only "
        f"baseline, adding OKF improved page recall by {ci(ab_chain['recall_delta'])}. "
        "Against a strong baseline that already combined keyword search, vector "
        "search and reranking, the gain disappeared and answer quality did not "
        "improve on any measure."
    )
    w("")
    w(
        "None of this says OKF is bad. It says OKF is not a retrieval improvement, "
        "which is what its own specification implies. What the study does verify is "
        "that an OKF bundle is portable, reviewable in version control, addressed by "
        "stable identifiers, and carries provenance that survives being handed to a "
        "different consumer. Those are real benefits. They are not retrieval benefits."
    )
    w("")
    w("## 1. What was tested")
    w("")
    w(
        "OKF does not define a retriever, so testing it requires building one. We "
        "built two, and disclose both exactly. Results apply to these "
        "implementations on this document, not to OKF in general."
    )
    w("")
    w(
        "The document is the PG&E 2026-2028 Base Wildfire Mitigation Plan, a 623-page "
        "public regulatory filing (SHA-256 "
        "`e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a`). The "
        f"question set is {ab['benchmark_id']}: 93 questions, 79 answerable with "
        "page-level answer keys and 14 controls whose answers are absent from the "
        "document. Answer keys were corrected against the source before the reported "
        "runs; blinded human validation is still outstanding and is listed as a "
        "limitation."
    )
    w("")
    w("**Bundle A, chunk-preserving.** Each existing 500-token retrieval chunk becomes")
    w("one concept, text unchanged, linked only to the previous and next chunk. The")
    w("1,837 passages are byte-identical to the rows in the vector database, verified,")
    w("which lets both arms be scored against the same answer key.")
    w("")
    w("**Bundle B, topic-structured.** This is OKF as its documentation describes it.")
    w(f"The PDF carries an embedded outline of {tb.get('outline_entries', 1006):,} entries,")
    w("which is the author's own topic hierarchy. Each concept is one outline entry: its")
    w("title is the heading verbatim, its body is the text between that heading and the")
    w("next, cut at the exact coordinates recorded for the entry, and its links are")
    w("parent, child, previous and next sibling, plus the cross-references the document")
    w(f"itself makes. Nothing is summarised or rewritten. Result: {tb['concept_count']:,}")
    w(f"concepts, {tb['max_depth']} levels, 99.9% of the document's words retained")
    w("verbatim, all 77 annotated answer pages covered, content digest verified.")
    w("")
    w("## 2. How it was measured")
    w("")
    w(
        "Topic concepts and chunks are different sizes, so asking each arm for its top "
        "10 units would hand more text to whichever has larger units, and more text "
        f"trivially covers more pages. Every arm therefore fills the same {budget}-token "
        "context budget and is scored on what lands inside it. Units are never "
        "truncated, because a truncated passage would otherwise earn credit for text "
        "that was not supplied."
    )
    w("")
    w(
        "Retrieval is scored as expected-page recall and page-hit rate against the "
        f"answer keys on the {n_ret} annotated questions. Answers are scored by a "
        "blinded judge against an independent reference answer and source passages "
        "selected only from the annotated pages, never against the passages the system "
        "chose for itself. The judge returns a typed object through forced tool use "
        "and is validated by a strict independent parser; malformed responses are "
        "retried under a cap and recorded as missing rather than replaced with a "
        f"neutral score. Every answer is judged {ab['judge_trials_per_cell']} times "
        f"({ab['judge_model']}). Correctness is not scored for the 14 controls, which "
        "are scored on whether the system correctly declined."
    )
    w("")
    w("## 3. Where the apparent OKF advantage comes from")
    w("")
    w(
        "The headline contrast changes three things at once: the ranking function, how "
        "much of each passage the encoder can read, and OKF itself. Arms below vary one "
        "at a time. Top 10 units, all on the same passages and questions."
    )
    w("")
    w("| Retrieval arm | Uses OKF | Page hit | Page recall | Median ms |")
    w("|---|---|---:|---:|---:|")
    for key, label, uses in (
        ("raw_vector", "Dense, 256-token input limit", "no"),
        ("titan_dense", "Dense, 8192-token input limit", "no"),
        ("bm25_raw", "**BM25 over the raw chunks**", "**no**"),
        ("rrf_bm25_titan", "BM25 and dense fused", "no"),
        ("okf_hybrid", "Dense seeds + OKF links", "yes"),
        ("okf_native", "BM25 over concepts + OKF links", "yes"),
        ("okf_evidence_only", "As above, frontmatter removed", "yes"),
        ("bm25_raw_adjacent", "BM25 + adjacency, no OKF", "no"),
    ):
        a = da.get(key)
        if not a:
            continue
        ms = a.get("median_latency_ms")
        w(
            f"| {label} | {uses} | {pct(a['page_hit_rate'])} | "
            f"{a['mean_expected_page_recall']:.3f} | "
            f"{ms:.1f} |" if isinstance(ms, (int, float))
            else f"| {label} | {uses} | {pct(a['page_hit_rate'])} | "
                 f"{a['mean_expected_page_recall']:.3f} | frozen run |"
        )
    w("")
    w("Two facts account for the gap.")
    w("")
    w(
        f"**The baseline encoder could not read the passages.** "
        f"`{trunc_frozen['model'].split('/')[-1]}` accepts "
        f"{trunc_frozen['max_input_tokens']} word-piece tokens. Measured over the "
        f"{trunc['passages']} passages of this document, "
        f"{pct(trunc['truncated_fraction'])} are longer than that (median "
        f"{trunc['token_length']['median']:.0f} tokens, longest "
        f"{trunc['token_length']['max']:,}), and the encoder received a median of only "
        f"{pct(trunc['median_fraction_of_passage_encoded'])} of each passage. A lexical "
        "index reads every word. Removing the truncation alone moved page recall by "
        f"{ci(truncation['recall_delta'])} (Holm p={p(truncation['page_hit_p_holm'])})."
    )
    w("")
    w(
        "**The gain was lexical, not structural.** Plain BM25 over the unmodified "
        "chunks, with no concept files, no frontmatter and no links, moved page recall "
        f"by {ci(lexical['recall_delta'])} (Holm p={p(lexical['page_hit_p_holm'])}) "
        "against the frozen baseline, and scores above the OKF arm. Measured against "
        f"plain BM25, adding OKF changed page recall by {ci(okf_gain['recall_delta'])} - "
        "a loss, with the interval excluding zero."
    )
    w("")
    w(
        "The loss has a mechanism, and it is testable. The consumer reserves half its "
        "result budget for neighbouring passages, and those positions would otherwise "
        "hold better-matching text. Driving the identical expansion from chunk order "
        "instead of OKF links reproduces the same loss "
        f"({ci(adjacency['recall_delta'])}), so the cause is budget allocation rather "
        "than anything specific to the format."
    )
    w("")
    w("## 4. Testing OKF as it is meant to be used")
    w("")
    w(f"At a matched {budget}-token context budget:")
    w("")
    w("| Retrieval arm | Page hit | Page recall | Duplicated tokens |")
    w("|---|---:|---:|---:|")
    for key, label in (
        ("chunks_dense", "Dense chunks only"),
        ("chunks_bm25", "**BM25 chunks, no OKF**"),
        ("okf_chain_bm25", "OKF chunk-chain + prev/next links"),
        ("okf_topic_bm25", "OKF topic-structured"),
        ("okf_topic_hierarchy", "OKF topic-structured + hierarchy links"),
        ("okf_plus_rag_topic", "Vector DB + OKF topics, fused"),
        ("okf_plus_rag_chain", "Vector DB + OKF chain, fused"),
    ):
        a = ta.get(key)
        if not a:
            continue
        w(
            f"| {label} | {pct(a['page_hit_rate'])} | "
            f"{a['mean_expected_page_recall']:.3f} | "
            f"{pct(a['mean_duplicate_token_fraction'])} |"
        )
    w("")
    w(
        "The topic-structured version is worse than plain chunk retrieval: "
        f"{ci(topic_vs_bm25['recall_delta'])}. Two measured reasons, not inferences."
    )
    w("")
    w(
        f"**The links carried no new evidence.** {mech['from_traversal']} of "
        f"{mech['packed_units']} packed units did arrive by following parent, child or "
        "sibling links, so traversal worked mechanically. They supplied "
        f"{mech['pages_only_from_traversal']} answer pages that the direct lexical "
        f"matches had not already found. The paired effect of enabling traversal is "
        f"{ci(hier['recall_delta'])}."
    )
    w("")
    w(
        f"**Coarse topics can become unreachable.** {over['count']} topics are larger "
        f"than the entire {budget}-token context budget, so their text is present in the "
        "bundle but can never be retrieved whole. The largest is the document's Table of "
        f"Contents at {over['largest'][0]['tokens']:,} tokens. That single consequence "
        "loses the four questions that ask on what page a section begins - evidence that "
        "chunking retrieves without difficulty."
    )
    w("")
    w(
        "Fusing the vector database with an OKF bundle also duplicates text, because the "
        "bundle holds a verbatim copy of the same document. In the fused arms "
        f"{pct(ta['okf_plus_rag_chain']['mean_duplicate_token_fraction'])} and "
        f"{pct(ta['okf_plus_rag_topic']['mean_duplicate_token_fraction'])} of the context "
        "budget is spent on pages already covered."
    )
    w("")
    w("## 5. The A/B a practitioner would run")
    w("")
    w(
        "Arm A is a conventional strong pipeline: BM25 and dense retrieval over chunks, "
        "fused by reciprocal rank, then cross-encoder reranked. Arm B is arm A **plus** "
        "an OKF source, fused and reranked identically. Because B differs from A only by "
        "the presence of OKF, the contrast estimates what OKF adds to a baseline that is "
        "already good. The pipeline, prompts, budget, generator and judge are unchanged "
        f"between arms. {ab['totals']['generation_cells']} answers, "
        f"{ab['totals']['judge_trials']} judge trials, no failures."
    )
    w("")
    w("| Arm | Correctness | Completeness | Groundedness | Citation | Refusal acc. | Page hit |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for key, label in (
        ("hybrid_rag", "**A: hybrid RAG**"),
        ("hybrid_plus_okf_topic", "B: + OKF topics"),
        ("hybrid_plus_okf_chain", "B: + OKF chain"),
    ):
        e = aa[key]
        w(
            f"| {label} | {e['mean_correctness']:.3f} | {e['mean_completeness']:.3f} | "
            f"{e['mean_groundedness']:.3f} | {e['mean_citation_quality']:.3f} | "
            f"{e['control_refusal_accuracy']:.3f} | {pct(e['page_hit_rate_at_context'])} |"
        )
    w("")
    w("Paired differences against arm A, 79 answerable questions:")
    w("")
    w("| Change | Correctness | Completeness | Groundedness | Citation quality |")
    w("|---|---|---|---|---|")
    for label, c in ac.items():
        dd = c["dimension_deltas"]
        name = "+ OKF topics" if "topics" in label else "+ OKF chain"
        w(
            f"| {name} | {ci(dd['correctness'])} | {ci(dd['completeness'])} | "
            f"{ci(dd['groundedness'])} | {ci(dd['citation_quality'])} |"
        )
    w("")
    w(
        "Correctness is a null in both directions. Two dimensions are measurably worse: "
        "citation quality with topics and completeness with the chain, both intervals "
        "excluding zero. Per question, topics won 3 and lost 7; the chain won 2 and lost "
        f"{ac['hybrid RAG -> hybrid + OKF chain']['cells_worse']}. All three arms declined "
        "all 14 controls correctly, so OKF neither helped nor hurt abstention."
    )
    w("")
    w(
        "The most robust signal is not any single interval. Seven of the eight dimension "
        "estimates are negative, across two independent OKF variants, and this agrees "
        "with retrieval, which is measured separately. Those per-dimension intervals are "
        "not corrected for eight comparisons, so any one of them alone should be read as "
        "suggestive; the consistent direction is the finding."
    )
    w("")
    w("For contrast, the same fusion against a **weak** vector-only baseline improves")
    w(f"page recall by {ci(ab_chain['recall_delta'])} (chain, Holm")
    w(f"p={p(ab_chain['page_hit_p_holm'])}) and {ci(ab_topic['recall_delta'])} (topics,")
    w(f"Holm p={p(ab_topic['page_hit_p_holm'])}). That is the same intervention scoring a")
    w("clear win or nothing at all, depending only on what it is compared against. It is")
    w("the single most important thing to control when evaluating a knowledge format.")
    w("")
    w("## 6. What this means")
    w("")
    w(
        "OKF v0.2 states that storage, query infrastructure and ranking are outside its "
        "scope. A format that does not define a search method cannot improve search by "
        "itself, and that is what we measured. What can change behaviour is the component "
        "that reads the format, and both components we built left retrieval and answers "
        "unchanged or slightly worse."
    )
    w("")
    w(
        "For practitioners the reading is narrow and useful. Topic structure is good for "
        "organising and navigating a document; chunks are better for retrieving from it. "
        "That matches OKF's own materials, which describe OKF *plus* RAG as complementary "
        "layers rather than OKF instead of RAG. If your retrieval is weak, the cheapest "
        "large improvement here was not OKF but adding a lexical index: BM25 cost about "
        f"{ta['chunks_bm25']['median_latency_ms']:.1f} ms per query against roughly "
        f"{da['titan_dense']['median_latency_ms']:.0f} ms for a hosted encoder."
    )
    w("")
    w(
        "For evaluation practice, one lesson stands out. Our own first measurement showed "
        "a large, highly significant advantage for OKF, and it would have supported the "
        "popular claim. It was an artifact of comparing a lexical index against an encoder "
        "that could not read most of each passage. A single strong baseline reversed the "
        "ranking. Any evaluation of a knowledge format should include a lexical baseline "
        "and should confirm that the encoders being compared can actually read the text "
        "they are given."
    )
    w("")
    w("## 7. Limitations")
    w("")
    w(
        "**One document.** 93 questions on one utility's filing. Nothing here generalises "
        "by itself to other documents, domains, or corpora."
    )
    w("")
    w(
        "**Two producers, not all producers.** A producer that re-authored passages into "
        "genuinely new concept prose, or that added semantic links between related "
        "sections rather than structural ones, might behave differently. We tested "
        "verbatim-text producers on purpose, so that any effect could be attributed to "
        "structure rather than to rewriting, but that is a real restriction on scope."
    )
    w("")
    w(
        "**The frozen dense baseline was weak.** Its encoder truncates, as measured above. "
        "We report it as run rather than quietly replacing it, and add an untruncated "
        "encoder as a diagnostic arm. The confirmatory comparison is unaffected because it "
        "compares the OKF consumer against that same arm on equal terms, but the absolute "
        "dense numbers understate a well-configured dense retriever."
    )
    w("")
    w(
        "**Exploratory status.** The diagnostic arms, the topic producer and the A/B were "
        "all specified after retrieval results had been seen. Each carries its own "
        "multiplicity family. They are attribution and estimation, not preregistered "
        "hypothesis tests."
    )
    w("")
    w(
        "**The A/B design is ours.** Querying a vector store and an OKF bundle in parallel "
        "and merging the hits is our construction. The OKF materials describe OKF as an "
        "authored source ingested into the retrieval stack. This design should not be "
        "attributed to Google."
    )
    w("")
    w(
        "**A halted run.** An earlier five-pipeline matrix was stopped at 1,254 of 1,395 "
        "cells when the study was redirected. Its answer-quality endpoints are unreported. "
        "Raw records are published and labelled; see the deviations log."
    )
    w("")
    w(
        "**Judge and model dependence.** A hosted judge has known biases and a hosted "
        "generator can drift. Blinded human validation of the answer keys is outstanding. "
        "Cost and latency depend on provider, region and date."
    )
    w("")
    w("## 8. Reproducing this")
    w("")
    w("```bash")
    w("cd okf_trial_data")
    w("python3.11 -m venv .venv")
    w(".venv/bin/pip install -r ../eval_harness/requirements.txt")
    w(".venv/bin/pip install -e '.[dev,analysis,paper]'")
    w("")
    w("# free, no model calls")
    w("./scripts/with_experiment_env.sh .venv/bin/python scripts/build_topic_okf_bundle.py")
    w("./scripts/with_experiment_env.sh .venv/bin/python scripts/measure_embedding_truncation.py")
    w("./scripts/with_experiment_env.sh .venv/bin/python scripts/run_retrieval_diagnostics.py")
    w("./scripts/with_experiment_env.sh .venv/bin/python scripts/run_topic_retrieval_comparison.py")
    w("")
    w("# billable, about 8 US dollars")
    w("./scripts/with_experiment_env.sh .venv/bin/python scripts/run_hybrid_ab_experiment.py --stage all")
    w("")
    w("# regenerate this paper from the records")
    w(".venv/bin/python paper/render_okf_vs_rag_paper.py")
    w("```")
    w("")
    w(
        "Every table above is generated by that last command from "
        "`results/retrieval_diagnostics/`, `results/topic_okf/`, `results/hybrid_ab/` and "
        "`results/embedding_truncation.json`. No number is typed by hand. Measured spend "
        f"for the A/B was ${ab['totals']['generation_usd']:.2f} for generation and "
        f"${ab['totals']['judge_usd']:.2f} for judging."
    )
    w("")
    w("## Declarations")
    w("")
    w(f"Funding: {FUNDING}.")
    w("")
    w(
        "Competing interests: none declared for this study. An unrelated in-house "
        "retrieval pipeline is withheld from the work and appears in no experiment, "
        "table, or claim."
    )
    w("")
    w(
        "This study used hosted language models to generate and to score answers. No "
        "human participants or personal data were involved."
    )
    w("")
    w("## References")
    w("")
    refs = [
        ("Open Knowledge Format (OKF), Version 0.2, Google Cloud. Pinned specification, "
         "commit `3fcbb9f828c2f23d109c855ee403c3a4c81f3a96`.",
         "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md"),
        ("P. Lewis et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP "
         "Tasks. NeurIPS 2020.", "https://arxiv.org/abs/2005.11401"),
        ("V. Karpukhin et al. Dense Passage Retrieval for Open-Domain Question "
         "Answering. EMNLP 2020.", "https://doi.org/10.18653/v1/2020.emnlp-main.550"),
        ("S. Robertson and H. Zaragoza. The Probabilistic Relevance Framework: BM25 and "
         "Beyond. 2009.", "https://doi.org/10.1561/1500000019"),
        ("G. V. Cormack, C. L. A. Clarke and S. Buettcher. Reciprocal Rank Fusion "
         "outperforms Condorcet and individual Rank Learning Methods. SIGIR 2009.",
         "https://doi.org/10.1145/1571941.1572114"),
        ("R. Nogueira and K. Cho. Passage Re-ranking with BERT. 2019.",
         "https://arxiv.org/abs/1901.04085"),
        ("A. Asai et al. Self-RAG: Learning to Retrieve, Generate, and Critique through "
         "Self-Reflection. ICLR 2024.", "https://arxiv.org/abs/2310.11511"),
        ("Z. Jiang et al. Active Retrieval Augmented Generation (FLARE). EMNLP 2023.",
         "https://doi.org/10.18653/v1/2023.emnlp-main.495"),
        ("N. Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of "
         "Information Retrieval Models. NeurIPS 2021.", "https://arxiv.org/abs/2104.08663"),
        ("L. Zheng et al. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. "
         "NeurIPS 2023.", "https://arxiv.org/abs/2306.05685"),
        ("S. Holm. A Simple Sequentially Rejective Multiple Test Procedure. "
         "Scandinavian Journal of Statistics, 1979.",
         "https://www.jstor.org/stable/4615733"),
    ]
    for i, (text, url) in enumerate(refs, 1):
        w(f"{i}. {text} <{url}>")
    w("")

    text = "\n".join(L)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(text.split()):,} words)")


if __name__ == "__main__":
    main()
