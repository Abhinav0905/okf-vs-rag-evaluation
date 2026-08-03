#!/usr/bin/env python3
"""Create the archival Markdown and polished preprint PDF from frozen results."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import re
import shutil
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "okf_trial_data"
DEFAULT_ANALYSIS = PACKAGE_ROOT / "results/full/analysis/analysis_summary.json"
DEFAULT_MARKDOWN = PACKAGE_ROOT / "paper/manuscript.md"
DEFAULT_TEX = PACKAGE_ROOT / "paper/manuscript.tex"
DEFAULT_PDF = PACKAGE_ROOT / "output/pdf/okf_rag_preprint.pdf"
DEFAULT_PREPRINT_DATE = "2 August 2026"
ACCENT = colors.HexColor("#174A7E")
LIGHT = colors.HexColor("#EAF1F8")
GREEN = colors.HexColor("#2F7D32")
ORANGE = colors.HexColor("#C45A0A")


PIPELINE_LABELS = {
    "simple_rag": "Simple RAG",
    "reranked_simple": "Reranked RAG",
    "agentic_rag": "Agentic RAG",
    "self_rag": "Self-RAG (re-impl.)",
    "flare": "FLARE (re-impl.)",
}
CONDITION_LABELS = {
    "raw_vector": "Raw vector",
    "okf_hybrid": "OKF hybrid",
    "okf_native": "OKF native (exploratory)",
}


@dataclass(frozen=True)
class ManuscriptMetadata:
    """Author-controlled metadata kept separate from empirical results."""

    author: str
    affiliation: str
    preprint_date: str
    doi: str
    repository_url: str
    orcid: str
    funding_statement: str
    conflict_statement: str

    @property
    def doi_display(self) -> str:
        value = self.doi.strip()
        if not value or "pending" in value.casefold() or value.startswith("["):
            return "DOI pending"
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if value.casefold().startswith(prefix):
                value = value[len(prefix):]
                break
        return f"doi:{value}"

    @property
    def doi_url(self) -> str | None:
        if self.doi_display == "DOI pending":
            return None
        return "https://doi.org/" + self.doi_display.removeprefix("doi:")

    @property
    def has_public_artifact(self) -> bool:
        return bool(
            self.repository_url.strip()
            and not self.repository_url.strip().startswith("[")
            and self.doi_display != "DOI pending"
        )

    @property
    def is_draft(self) -> bool:
        required = (
            self.author,
            self.affiliation,
            self.orcid,
            self.funding_statement,
            self.conflict_statement,
        )
        return not self.has_public_artifact or any(
            not value.strip() or value.strip().startswith("[") for value in required
        )


REFERENCES = [
    (
        "GoogleCloudPlatform. Open Knowledge Format (OKF), Version 0.2, pinned "
        "specification at commit 3fcbb9f828c2f23d109c855ee403c3a4c81f3a96, 2026.",
        "https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/3fcbb9f828c2f23d109c855ee403c3a4c81f3a96/okf/SPEC.md",
    ),
    (
        "S. McVeety and A. Hormati. How the Open Knowledge Format can improve "
        "data sharing. Google Cloud Data Analytics Blog, June 12, 2026.",
        "https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/",
    ),
    (
        "S. McVeety and A. Hormati. Open Knowledge Format v0.2 tackles agentic "
        "trust. Google Cloud Data Analytics Blog, July 24, 2026.",
        "https://cloud.google.com/blog/products/data-analytics/okf-v0-2-adds-trust-signals/",
    ),
    (
        "P. Lewis et al. Retrieval-Augmented Generation for Knowledge-Intensive "
        "NLP Tasks. NeurIPS, 2020.",
        "https://papers.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html",
    ),
    (
        "V. Karpukhin et al. Dense Passage Retrieval for Open-Domain Question "
        "Answering. EMNLP, 2020. doi:10.18653/v1/2020.emnlp-main.550.",
        "https://doi.org/10.18653/v1/2020.emnlp-main.550",
    ),
    (
        "R. Nogueira and K. Cho. Passage Re-ranking with BERT. arXiv:1901.04085, 2019.",
        "https://arxiv.org/abs/1901.04085",
    ),
    (
        "Y. Luan, J. Eisenstein, K. Toutanova, and M. Collins. Sparse, Dense, and "
        "Attentional Representations for Text Retrieval. TACL 9, 2021. "
        "doi:10.1162/tacl_a_00369.",
        "https://doi.org/10.1162/tacl_a_00369",
    ),
    (
        "S. Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. "
        "ICLR, 2023.",
        "https://arxiv.org/abs/2210.03629",
    ),
    (
        "H. Trivedi, N. Balasubramanian, T. Khot, and A. Sabharwal. Interleaving "
        "Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step "
        "Questions. ACL, 2023. doi:10.18653/v1/2023.acl-long.557.",
        "https://doi.org/10.18653/v1/2023.acl-long.557",
    ),
    (
        "A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi. Self-RAG: Learning to "
        "Retrieve, Generate, and Critique through Self-Reflection. ICLR, 2024.",
        "https://openreview.net/forum?id=hSyW5go0v8",
    ),
    (
        "Z. Jiang et al. Active Retrieval Augmented Generation. EMNLP, 2023. "
        "doi:10.18653/v1/2023.emnlp-main.495.",
        "https://doi.org/10.18653/v1/2023.emnlp-main.495",
    ),
    (
        "D. Edge et al. From Local to Global: A Graph RAG Approach to Query-Focused "
        "Summarization. arXiv:2404.16130, 2024.",
        "https://arxiv.org/abs/2404.16130",
    ),
    (
        "N. Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation "
        "of Information Retrieval Models. NeurIPS Datasets and Benchmarks, 2021.",
        "https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract-round2.html",
    ),
    (
        "F. Petroni et al. KILT: a Benchmark for Knowledge Intensive Language Tasks. "
        "NAACL, 2021. doi:10.18653/v1/2021.naacl-main.200.",
        "https://doi.org/10.18653/v1/2021.naacl-main.200",
    ),
    (
        "P. Dasigi et al. A Dataset of Information-Seeking Questions and Answers "
        "Anchored in Research Papers. NAACL, 2021. doi:10.18653/v1/2021.naacl-main.365.",
        "https://doi.org/10.18653/v1/2021.naacl-main.365",
    ),
    (
        "S. Es, J. James, L. Espinosa Anke, and S. Schockaert. RAGAS: Automated "
        "Evaluation of Retrieval Augmented Generation. EACL System Demonstrations, "
        "2024. doi:10.18653/v1/2024.eacl-demo.16.",
        "https://doi.org/10.18653/v1/2024.eacl-demo.16",
    ),
    (
        "J. Saad-Falcon, O. Khattab, C. Potts, and M. Zaharia. ARES: An Automated "
        "Evaluation Framework for Retrieval-Augmented Generation Systems. NAACL, "
        "2024. doi:10.18653/v1/2024.naacl-long.20.",
        "https://doi.org/10.18653/v1/2024.naacl-long.20",
    ),
    (
        "Y. Liu et al. G-Eval: NLG Evaluation Using GPT-4 with Better Human "
        "Alignment. EMNLP, 2023. doi:10.18653/v1/2023.emnlp-main.153.",
        "https://doi.org/10.18653/v1/2023.emnlp-main.153",
    ),
    (
        "L. Zheng et al. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. "
        "NeurIPS Datasets and Benchmarks, 2023.",
        "https://papers.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html",
    ),
    (
        "D. Lakens. Equivalence Tests: A Practical Primer for t Tests, "
        "Correlations, and Meta-Analyses. Social Psychological and Personality "
        "Science 8(4), 2017. doi:10.1177/1948550617697177.",
        "https://doi.org/10.1177/1948550617697177",
    ),
]


def _f(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _p(value: float) -> str:
    return "<0.001" if value < 0.001 else f"{value:.3f}"


def _pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}%"


def _count_phrase(value: int, singular: str, plural: str | None = None) -> str:
    return f"{value} {singular if value == 1 else (plural or singular + 's')}"


def _row_by(rows: list[dict[str, Any]], **criteria: str) -> dict[str, Any]:
    return next(row for row in rows if all(row[key] == value for key, value in criteria.items()))


def _study_design(summary: dict[str, Any]) -> dict[str, Any]:
    """Read versioned design metadata, with conservative legacy-summary fallbacks."""

    design = dict(summary.get("study_design", {}))
    primary = summary["primary_raw_vs_okf_hybrid"]
    answerable = int(design.get("answerable_count", primary[0]["n_pairs"]))
    pipeline_count = int(design.get("pipeline_count", len(primary)))
    condition_count = int(design.get("condition_count", 3))
    generation_records = int(summary["completion"]["generation_records"])
    inferred_total = generation_records // max(1, pipeline_count * condition_count)
    total = int(design.get("question_count", inferred_total))
    controls = int(design.get("control_count", total - answerable))
    return {
        **design,
        "question_count": total,
        "answerable_count": answerable,
        "control_count": controls,
        "pipeline_count": pipeline_count,
        "condition_count": condition_count,
        "confirmatory_cells": int(design.get("confirmatory_cells", total * pipeline_count * 2)),
        "exploratory_cells": int(design.get("exploratory_cells", total * pipeline_count)),
        "human_validation_status": design.get("human_validation_status", "pending"),
    }


def _primary_interpretation(rows: list[dict[str, Any]]) -> str:
    significant = [row for row in rows if row["holm_p"] < 0.05]
    positive = [row for row in rows if row["mean_delta"] > 0]
    negative = [row for row in rows if row["mean_delta"] < 0]
    if not significant:
        return (
            f"None of the {len(rows)} pipeline-specific confirmatory comparisons survived "
            "Holm correction. This is a null result at the configured sample size, "
            "not evidence of equivalence."
        )
    direction = "positive" if len(positive) >= len(negative) else "negative"
    names = ", ".join(PIPELINE_LABELS[row["pipeline"]] for row in significant)
    return (
        f"Holm-adjusted differences were detected for {names}; the predominant "
        f"direction across pipelines was {direction}. Effects remain specific to "
        "this consumer and benchmark."
    )


def _abstract(summary: dict[str, Any]) -> str:
    design = _study_design(summary)
    retrieval = summary["retrieval_only"]["results"]
    raw_hit = retrieval["raw_vector"]["page_hit_rate"]
    hybrid_hit = retrieval["okf_hybrid"]["page_hit_rate"]
    native_hit = retrieval["okf_native"]["page_hit_rate"]
    pooled = {row["treatment"]: row for row in summary["pooled_cluster_bootstrap"]}
    hybrid = pooled["okf_hybrid"]
    native = pooled["okf_native"]
    significant = sum(
        row["holm_p"] < 0.05 for row in summary["primary_raw_vs_okf_hybrid"]
    )
    diagnostic = ""
    if _has_diagnostics(summary):
        arms = summary["retrieval_diagnostics"]["arms"]
        contrasts = summary["retrieval_diagnostics"]["contrasts"]
        titan = arms.get("titan_dense", {})
        bm25 = arms.get("bm25_raw", {})
        okf_delta = next(
            (
                value["recall_delta"]
                for key, value in contrasts.items()
                if key.startswith("does OKF beat plain BM25")
            ),
            None,
        )
        adjacency_delta = next(
            (
                value["recall_delta"]
                for key, value in contrasts.items()
                if key.startswith("adjacency without OKF")
            ),
            None,
        )
        truncation = summary.get("embedding_truncation") or {}
        truncated_share = (
            _pct(truncation["truncated_fraction"])
            if truncation
            else "most"
        )
        window = (
            f"{truncation['frozen_encoder']['max_input_tokens']} tokens"
            if truncation
            else "a few hundred tokens"
        )
        diagnostic = (
            "Because that difference could have several causes, we ran arms that change "
            f"one thing at a time. The dense baseline used an encoder whose input limit "
            f"is {window}, and {truncated_share} of these passages are longer than that, "
            "so much of each passage was never encoded. Replacing it with an encoder that reads the "
            f"whole passage raised the hit rate to {_pct(titan.get('page_hit_rate', 0.0))}. "
            "Plain BM25 over the original chunks, using no part of OKF, reached "
            f"{_pct(bm25.get('page_hit_rate', 0.0))} - higher than the OKF arm. Measured "
            "against plain BM25, adding OKF changed page recall by "
            f"{okf_delta['mean_difference']:+.3f} "
            f"(95% CI {okf_delta['ci_low']:+.3f} to {okf_delta['ci_high']:+.3f}). "
            "The loss comes from spending half of the result budget on neighbouring "
            "passages: reproducing the same neighbour expansion without OKF, from chunk "
            "order alone, reproduces the same loss "
            f"({adjacency_delta['mean_difference']:+.3f}, 95% CI "
            f"{adjacency_delta['ci_low']:+.3f} to {adjacency_delta['ci_high']:+.3f}). "
            "The apparent advantage therefore belongs to lexical matching and to a "
            "misconfigured baseline, not to the format. "
        )
    return (
        "The Open Knowledge Format (OKF) v0.2 stores knowledge as Markdown files with "
        "YAML metadata and ordinary links between them. It is a way of writing knowledge "
        "down, and it deliberately does not define how to search. Public commentary has "
        "nevertheless claimed that it replaces vector databases and retrieval-augmented "
        "generation (RAG). We tested that claim directly. We built one OKF v0.2 producer "
        "that copies each existing document chunk into one concept file without changing "
        "its text, and two search components that read those files. We ran them inside "
        "five unchanged RAG pipelines: Simple RAG, Reranked RAG, Agentic RAG, and "
        "disclosed re-implementations of Self-RAG and FLARE. The source document, the "
        f"{design['question_count']}-question benchmark, the generator, the prompts, the "
        "context budget, and the scoring procedure were all held fixed, so only retrieval "
        f"changed. Over {_count_phrase(design['answerable_count'], 'question')} with "
        "page-level answer keys, the share of questions where the retrieved passages "
        f"included a correct page was {_pct(raw_hit)} for ordinary vector search and "
        f"{_pct(hybrid_hit)} for the OKF version of the same search - no improvement. "
        f"Across the five pipelines, answer correctness changed by {_f(hybrid['mean_delta'])} "
        f"points on a five-point scale (95% clustered bootstrap interval "
        f"{_f(hybrid['ci_low'])} to {_f(hybrid['ci_high'])}), and {significant} of "
        f"{design['pipeline_count']} pipeline comparisons remained significant after Holm "
        f"correction. A second OKF component that searched the concept text with BM25 did "
        f"score much higher on retrieval, {_pct(native_hit)}. "
        + diagnostic
        + f"The study contains {summary['completion']['generation_records']:,} generated "
        f"answers and {summary['completion']['judge_trial_records']:,} valid scoring runs, "
        "with no substituted scores. An earlier incomplete run was stopped before scoring "
        "and discarded after we found errors in the answer key; blinded human checking of "
        "the corrected benchmark is still outstanding. Our conclusion is narrow and "
        "negative: for this document, this benchmark, and this implementation, writing the "
        "corpus in OKF and following its links did not make retrieval or answers better. "
        "This is what the specification itself implies, since it does not define a search "
        "method. We release the code, the bundle, the questions, every model output, and "
        "the analysis so the measurement can be rechecked and repeated."
    )


def _truncation_sentence(summary: dict[str, Any]) -> str:
    """Describe the frozen encoder's input limit from the measured artifact."""

    measured = summary.get("embedding_truncation")
    if not measured:
        return (
            "The frozen configuration used a sentence-transformer encoder with a short "
            "input window, so passages longer than that window were truncated before "
            "embedding, while a lexical index reads every word."
        )
    frozen = measured["frozen_encoder"]
    lengths = measured["token_length"]
    return (
        f"The frozen configuration used {frozen['model'].split('/')[-1]}, whose input limit "
        f"is {frozen['max_input_tokens']} word-piece tokens, and "
        f"{_pct(measured['truncated_fraction'])} of the "
        f"{measured['passages']:,} passages in this corpus exceed that limit "
        f"(median {lengths['median']:.0f} tokens, longest {lengths['max']:,}). "
        "Everything past the limit is discarded before embedding, so the encoder saw a "
        f"median of only {_pct(measured['median_fraction_of_passage_encoded'])} of each "
        "passage, whereas a lexical index reads every word."
    )


def _diagnostic_paragraphs(summary: dict[str, Any]) -> list[str]:
    """Prose for the exploratory decomposition of the retrieval difference."""

    if not _has_diagnostics(summary):
        return []
    arms = summary["retrieval_diagnostics"]["arms"]
    contrasts = summary["retrieval_diagnostics"]["contrasts"]

    def contrast(prefix: str) -> dict[str, Any] | None:
        return next(
            (value for key, value in contrasts.items() if key.startswith(prefix)), None
        )

    truncation = contrast("truncation effect")
    lexical = contrast("lexical effect")
    fair = contrast("lexical vs fair dense")
    okf_gain = contrast("does OKF beat plain BM25")
    frontmatter = contrast("OKF frontmatter")
    adjacency = contrast("adjacency without OKF")
    fair_adjacency = contrast("adjacency on fair dense")
    fusion = contrast("fusion")
    if not all((truncation, lexical, okf_gain, frontmatter, adjacency)):
        return []

    def interval(item: dict[str, Any]) -> str:
        """Effect with interval, without enclosing parentheses.

        Callers decide whether to wrap it, so the text never nests brackets.
        """

        delta = item["recall_delta"]
        formatted = _p(item["page_hit_p_holm"])
        holm = f"Holm p{formatted}" if formatted.startswith("<") else f"Holm p={formatted}"
        return (
            f"{delta['mean_difference']:+.3f}, 95% CI {delta['ci_low']:+.3f} to "
            f"{delta['ci_high']:+.3f}, {holm}"
        )

    def effect(item: dict[str, Any]) -> str:
        """Effect for mid-sentence use, e.g. "a change of +0.198 (95% CI ...)"."""

        delta = item["recall_delta"]
        formatted = _p(item["page_hit_p_holm"])
        holm = f"Holm p{formatted}" if formatted.startswith("<") else f"Holm p={formatted}"
        return (
            f"{delta['mean_difference']:+.3f} (95% CI {delta['ci_low']:+.3f} to "
            f"{delta['ci_high']:+.3f}, {holm})"
        )

    titan = arms.get("titan_dense", {})
    bm25 = arms.get("bm25_raw", {})
    native = arms.get("okf_native", {})
    raw = arms.get("raw_vector", {})
    paragraphs = [
        "The large OKF-native retrieval difference cannot be read as an effect of the "
        "format, because that comparison changes three things at once: the ranking "
        "function, the amount of each passage the encoder can read, and the OKF content "
        "itself. We therefore ran arms that vary one of those at a time. All of them use "
        "the same passages, the same questions, the same result budget, and the same "
        "page-level scoring. These arms were added after the frozen retrieval screen and "
        "are exploratory; they carry their own Holm correction and do not change the "
        "confirmatory comparison.",
        "Two facts explain the gap. First, the dense baseline was handicapped by its "
        f"encoder. {_truncation_sentence(summary)} Swapping in an encoder that accepts the whole "
        f"passage raised the page-hit rate from {_pct(raw.get('page_hit_rate', 0.0))} to "
        f"{_pct(titan.get('page_hit_rate', 0.0))}, a page-recall change of "
        f"{effect(truncation)}. Second, lexical matching suits this document. Plain "
        "BM25 over the original chunks, using no OKF component at all, reached "
        f"{_pct(bm25.get('page_hit_rate', 0.0))}, a change of {effect(lexical)} against "
        "the frozen dense baseline"
        + (
            f" and {effect(fair)} against the untruncated dense arm."
            if fair
            else "."
        ),
        "Against that corrected baseline, OKF does not add retrieval quality. Plain BM25 "
        f"reached {_pct(bm25.get('page_hit_rate', 0.0))} while the OKF-native consumer "
        f"reached {_pct(native.get('page_hit_rate', 0.0))}; adding OKF changed page recall "
        f"by {effect(okf_gain)}. The frontmatter fields the consumer boosts contribute "
        f"almost nothing ({interval(frontmatter)}). The loss is caused by the traversal "
        "policy: half of the result budget is reserved for neighbouring passages, and "
        "those positions would otherwise hold better-matching passages. That explanation "
        "is testable, and it holds. Reproducing the identical neighbour expansion without "
        "OKF, using only the order of the original chunks, reproduces the same loss "
        f"({interval(adjacency)})"
        + (
            f", as does applying it to the untruncated dense arm ({interval(fair_adjacency)})."
            if fair_adjacency
            else "."
        )
        + " The mechanism is budget displacement, not anything specific to the format.",
    ]
    if fusion:
        paragraphs.append(
            "Combining lexical and dense rankings by reciprocal-rank fusion did not beat "
            f"BM25 alone here ({interval(fusion)}), which is consistent with a document "
            "whose questions are dominated by exact program names, identifiers, and "
            "numbers. Cost differs sharply as well: the lexical index answered a query in "
            f"about {_f(bm25.get('median_latency_ms'), 1)} ms against roughly "
            f"{_f(titan.get('median_latency_ms'), 0)} ms for the hosted encoder, which "
            "must make a network call per query."
        )
    return paragraphs


def _section_content(
    summary: dict[str, Any], metadata: ManuscriptMetadata
) -> list[tuple[str, list[str]]]:
    primary = summary["primary_raw_vs_okf_hybrid"]
    exploratory = summary["exploratory_raw_vs_okf_native"]
    pooled = {row["treatment"]: row for row in summary["pooled_cluster_bootstrap"]}
    retrieval = summary["retrieval_only"]["results"]
    reliability = summary["judge_reliability"]
    build = summary["bundle_build"]
    costs = summary["costs"]
    hybrid_mcnemar = retrieval["raw_vs_okf_hybrid_page_hit_mcnemar"]
    native_mcnemar = retrieval["raw_vs_okf_native_page_hit_mcnemar"]
    design = _study_design(summary)
    deviations = design.get("protocol_deviations", [])
    deviation_description = next(
        (
            item["description"]
            for item in deviations
            if isinstance(item, dict)
            and item.get("type") == "benchmark_semantic_correction_after_partial_generation"
            and item.get("description")
        ),
        (
            "A semantic review after an incomplete paid generation run identified "
            "additional gold-label or reference errors. The run was stopped before "
            "judging, declared invalid, and excluded from all reported endpoints. The "
            "corrected benchmark received a new version and content hash before restart."
        ),
    )

    return [
        (
            "1. Introduction",
            [
                "Retrieval-augmented generation (RAG) separates language generation "
                "from a non-parametric evidence store, making retrieval quality a key "
                "determinant of factual coverage and traceability [4,5]. Dense search, "
                "cross-encoder reranking, iterative retrieval, and reflection can each "
                "recover different failure modes [6-11]. Yet most operational systems "
                "still represent long documents as isolated chunks whose relationships, "
                "provenance, and lifecycle are carried in implementation-specific metadata.",
                "Google's Open Knowledge Format (OKF) v0.2 proposes a portable exchange "
                "representation: UTF-8 Markdown concept files with YAML frontmatter, "
                "ordinary Markdown links, optional directory indexes, and explicit "
                "provenance, verification, lifecycle, and attestation fields [1-3]. The "
                "specification intentionally leaves storage, query infrastructure, and "
                "ranking unspecified. Consequently, OKF is not a retrieval algorithm and "
                "does not replace RAG or a vector database. Any performance claim must "
                "identify the producer and consumer that operationalize the format.",
                "Despite that, the format has been widely described in public commentary as "
                "a replacement for vector databases and for RAG. That is a testable claim, "
                "and it is the claim this paper tests. Because OKF does not define a "
                "retriever, testing it requires choosing one, so we pin and disclose exactly "
                "what we built and report results for that implementation only.",
                "The implementation is deliberately narrow. A deterministic producer copies "
                "each pre-existing chunk of the source document, unchanged, into one OKF "
                "Source Passage concept carrying source hashes and page metadata, and adds "
                "only previous/next links between consecutive passages. One consumer starts "
                "from the same vector backend the baseline uses, reserves half of each result "
                "budget for those vector seeds, expands one hop to the previous and next "
                "passage, and returns the original number of results. A second consumer "
                "ranks the concept text with weighted BM25 and performs the same traversal. "
                "Because the producer changes no text, the passages in the bundle are "
                "byte-identical to the rows in the vector database, which lets both arms be "
                "scored against the same page-level answer key.",
                "Our headline finding is negative, and it arrived by way of a mistake worth "
                "reporting. The BM25-based OKF consumer initially appeared to beat vector "
                "search decisively, which would have supported the popular claim. Adding the "
                "controls that comparison was missing showed the advantage belonged to "
                "lexical matching and to a dense baseline whose encoder could not read most "
                "of each passage - not to OKF. Plain BM25 with no OKF component scored "
                "higher still, and the format's own link traversal slightly reduced page "
                "recall.",
                "We make five contributions: (i) a lossless, pinned OKF v0.2 producer and an "
                "auditable bundle that rebuilds to a matching digest; (ii) two disclosed "
                "consumers that drop into five existing RAG pipelines without changing them; "
                "(iii) a paired, answer-key-based protocol that repairs silent judge-fallback "
                "defects found in a prior harness; (iv) a decomposition that separates the "
                "matching function, the encoder's input limit, and the OKF components, so the "
                "measured difference is attributed rather than assumed; and (v) a complete "
                "artifact containing source hashes, question curation, retrieval traces, "
                "model outputs, costs, statistics, and the code that generates this "
                "manuscript from them.",
            ],
        ),
        (
            "2. Background and Related Work",
            [
                "Lewis et al. combined parametric generation with retrieved memory [4], "
                "while Dense Passage Retrieval established an efficient bi-encoder design "
                "for passage discovery [5]. Cross-encoder reranking trades additional "
                "computation for richer query-passage interaction [6]. Sparse and dense "
                "representations capture complementary lexical and semantic signals [7], "
                "which motivates retaining a lexical OKF-native consumer alongside the "
                "dense-seeded confirmatory condition.",
                "Agentic and iterative methods introduce additional retrieval opportunities. "
                "ReAct and IRCoT interleave reasoning with actions or retrieval [8,9]. "
                "Canonical Self-RAG trains reflection-token behavior [10], and FLARE uses "
                "forward-looking, confidence-triggered retrieval [11]. Our Agentic RAG is "
                "a repository-specific critic/rewrite loop. The Self-RAG and FLARE systems "
                "are behavioral re-implementations, not the original checkpoints or exact "
                "decoding algorithms; this label is retained in every result.",
                "Graph-assisted retrieval may improve global or multi-evidence questions, "
                "but graph structures differ materially [12]. The present links express "
                "only document adjacency. They are not entity relations, semantic edges, "
                "or community summaries. KILT, BEIR, and QASPER motivate common-unit "
                "retrieval and provenance evaluation [13-15]. RAGAS and ARES separate "
                "retrieval, faithfulness, and answer relevance [16,17]. G-Eval and MT-Bench "
                "show that structured LLM judging can scale but is subject to position, "
                "verbosity, and model-family biases [18,19]; our protocol therefore combines "
                "gold pages, strict structured output, repeated trials, and explicit limits.",
            ],
        ),
        (
            "3. OKF Producer and Retrieval Conditions",
            [
                "The producer targets OKF v0.2 at immutable commit "
                "3fcbb9f828c2f23d109c855ee403c3a4c81f3a96 [1]. It consumes only corpus "
                "manifests and source-chunk JSONL files; benchmark questions and answers "
                "are rejected as inputs. Every concept preserves exact evidence text, "
                "original chunk ID, corpus, document name, page list, corpus version, "
                "source PDF hash, content hash, and original metadata. The bundle declares "
                "the specification version at its root and includes conformant index and "
                "update-log files.",
                f"The final bundle contains {build['concept_count']:,} concepts and "
                f"{build['markdown_artifact_count']:,} Markdown artifacts across three "
                f"utility corpora. A clean rebuild took {_f(build['build_seconds'], 2)} s, "
                f"load plus integrity verification took {_f(build['load_and_verify_seconds'], 2)} s, "
                f"and the bundle occupied {build['bundle_bytes'] / 1_048_576:.2f} MiB "
                f"({_f(build['bundle_to_source_size_ratio'], 2)}x the manifest-plus-JSONL "
                "source size). The rebuilt content digest exactly matched the archived "
                f"digest {build['rebuilt_bundle_content_sha256']}.",
                "Raw vector uses all requested positions for direct MiniLM vector results. "
                "OKF hybrid uses seed_k = ceil(0.5 x top_k), maps the seeds to concepts, "
                "traverses previous and next links bidirectionally to depth one with decay "
                "0.35, unions seeds and neighbors, score-sorts with deterministic ID tie "
                "breaking, and returns at most top_k unchanged passages. OKF native uses "
                "weighted BM25 over evidence and selected frontmatter followed by the same "
                "bounded traversal. All conditions enforce the PGE corpus filter and share "
                "the same reranker and 2,200-token context budget inside each pipeline.",
            ],
        ),
        (
            "4. Experimental Design",
            [
                "The confirmatory corpus is the PG&E 2026-2028 Base Wildfire Mitigation "
                "Plan snapshot (PDF SHA-256 e601db5767c0dcaa5e534315c49c3d90ad0b7b09b467da8a37ffc2c3dfb5dc6a). "
                "The versioned benchmark combines two inherited question sets. Its machine-readable "
                f"release contains {_count_phrase(design['question_count'], 'question')}: "
                f"{_count_phrase(design['answerable_count'], 'answerable item')} with reference "
                "answers and expected pages, and "
                f"{_count_phrase(design['control_count'], 'source-checked unanswerable control')}. A "
                "deterministic audit verifies page availability and lexical support but does not "
                "constitute blinded human validation; that validation remains pending.",
                f"{deviation_description} This versioned deviation prevents describing the "
                "final benchmark as wholly frozen before any paid generation.",
                f"{design['pipeline_count']} pipelines were crossed with raw vector and OKF hybrid "
                f"for {design['confirmatory_cells']:,} confirmatory answer cells. After a frozen "
                "no-LLM retrieval screen on the superseded v1 benchmark showed stronger page "
                "retrieval for OKF native, "
                f"{design['exploratory_cells']:,} native answer cells were added "
                "as an explicitly exploratory, data-motivated arm. Conditions were "
                "randomized within pipeline-question blocks. Claude Sonnet 4.5 on Amazon "
                "Bedrock generated answers at temperature zero; local all-MiniLM-L6-v2 "
                "embeddings and ms-marco-MiniLM-L-6-v2 reranking were held fixed.",
                "The primary endpoint is gold-aware correctness on a 1-5 ordinal rubric. "
                "For answerable questions, an inappropriate refusal receives the declared "
                "floor of one for correctness and completeness. For controls, refusal "
                "accuracy is analyzed separately. The blinded evaluator receives the "
                "question, independent reference answer, canonical source passages selected "
                "only from expected pages, candidate answer, and resolved candidate "
                "citations. Claude Haiku 4.5 returns a forced Bedrock tool object that is "
                "then validated by an exact-schema parser. Malformed trials remain missing; "
                f"no midpoint is imputed. {design.get('judge_trials_per_answer', 3)} valid "
                "judge trials are averaged within each answer cell.",
                "For each pipeline we report raw and treatment means, mean and median paired "
                "differences, 10,000-resample paired-question bootstrap intervals, two-sided "
                f"Wilcoxon signed-rank tests, and Holm correction across the {design['pipeline_count']} confirmatory "
                "p-values. The pooled secondary interval resamples question IDs as clusters "
                f"to preserve the {design['pipeline_count']} correlated pipeline observations. Binary control and "
                "retrieval-hit changes use exact McNemar tests. Nonsignificance is not "
                "interpreted as equivalence [20].",
            ],
        ),
        (
            "5. Results",
            [
                f"All {summary['completion']['generation_records']:,} scheduled answer "
                f"cells and {summary['completion']['judge_trial_records']:,} judge trials "
                f"completed. The strict evaluator recorded {reliability['schema_retry_count']} "
                f"schema retries and {reliability['parse_failure_count']} terminal parse "
                f"failures. Exact {design.get('judge_trials_per_answer', 3)}-trial correctness "
                "agreement across answerable cells "
                f"was {_pct(reliability['positive_cell_exact_correctness_agreement'])}; the "
                f"mean within-cell range was {_f(reliability['positive_cell_mean_correctness_range'])} points.",
                f"At top-10 retrieval, raw vector hit at least one expected page for "
                f"{_pct(retrieval['raw_vector']['page_hit_rate'])} of "
                f"{_count_phrase(design['answerable_count'], 'answerable question')}. "
                f"OKF hybrid reached {_pct(retrieval['okf_hybrid']['page_hit_rate'])}, a "
                f"{_pct(retrieval['okf_hybrid']['page_hit_rate'] - retrieval['raw_vector']['page_hit_rate'])} "
                f"absolute change (exact McNemar p={_p(hybrid_mcnemar['p_value'])}). "
                f"OKF native reached {_pct(retrieval['okf_native']['page_hit_rate'])}, a "
                f"{_pct(retrieval['okf_native']['page_hit_rate'] - retrieval['raw_vector']['page_hit_rate'])} "
                f"absolute change (p={_p(native_mcnemar['p_value'])}). Mean expected-page "
                f"recall was {_f(retrieval['raw_vector']['mean_expected_page_recall'])}, "
                f"{_f(retrieval['okf_hybrid']['mean_expected_page_recall'])}, and "
                f"{_f(retrieval['okf_native']['mean_expected_page_recall'])}, respectively.",
                *_diagnostic_paragraphs(summary),
                f"Across all {design['pipeline_count']} pipelines, the clustered mean correctness change for "
                f"OKF hybrid was {_f(pooled['okf_hybrid']['mean_delta'])} points "
                f"(95% CI {_f(pooled['okf_hybrid']['ci_low'])} to "
                f"{_f(pooled['okf_hybrid']['ci_high'])}). {_primary_interpretation(primary)}",
                f"The exploratory OKF-native pooled correctness change was "
                f"{_f(pooled['okf_native']['mean_delta'])} points (95% CI "
                f"{_f(pooled['okf_native']['ci_low'])} to "
                f"{_f(pooled['okf_native']['ci_high'])}). Because this end-to-end arm "
                "was added after viewing retrieval-only outcomes, its answer-quality "
                "contrasts are hypothesis-generating and cannot be promoted to the "
                "confirmatory family.",
                f"Measured API spend was ${costs['generation_usd']:.2f} for generation "
                f"and ${costs['judging_usd']:.2f} for evaluation, totaling "
                f"${costs['total_usd']:.2f}. Judge expense is an experimental cost, not "
                "a deployment query cost. Latency and generation-call results are shown "
                "by pipeline and condition in the artifact tables; they reflect one local "
                "machine, a warm local database, controlled concurrency, and contemporaneous "
                "Bedrock network conditions.",
            ],
        ),
        (
            "6. Discussion",
            [
                "The result is a null, and the specification predicts it. OKF v0.2 defines "
                "how to write knowledge down and states that storage, query infrastructure, "
                "and ranking are outside its scope. A format that does not specify a search "
                "method cannot improve search on its own. What can change behaviour is the "
                "component that reads the format, and here the component we built - reserve "
                "half the result budget, expand one hop to the previous and next passage - "
                "left retrieval and answers unchanged or slightly worse.",
                "The one change the traversal reliably makes is how the result budget is "
                "spent. Every position given to a neighbouring passage is taken from a "
                "better-matching passage. Whether that trade pays depends on how often "
                "evidence sits next to something already retrieved rather than being "
                "retrievable itself. On this document it did not pay, and the same loss "
                "appears when the identical expansion is driven by chunk order instead of "
                "OKF links. Reporting the effect as a property of OKF would therefore be "
                "wrong twice over: the mechanism is budget allocation, and it is available "
                "without the format.",
                "The wider lesson concerns how such comparisons are run. Our own frozen "
                "screen produced a large, highly significant advantage for the OKF arm, and "
                "that number would have supported the popular claim that OKF supersedes "
                "vector search. It was an artifact of comparing a lexical index against a "
                "dense encoder that could not read most of each passage. A single strong "
                "baseline - plain BM25, costing nothing and running in about a millisecond - "
                "reversed the ranking. Any evaluation of a new knowledge format should "
                "include a lexical baseline and should confirm that the encoders being "
                "compared can actually read the passages they are given.",
                "None of this argues against OKF. It argues for locating its value "
                "correctly. What we verified are engineering properties: the bundle is "
                "portable, reviewable in version control, addressed by stable identifiers, "
                "and carries provenance and page metadata that survive being handed to a "
                "different consumer. We rebuilt it deterministically and matched its "
                "content digest exactly, and its passages are byte-identical to the rows in "
                "the vector database. Those are real benefits for auditing, exchange, and "
                "governance. They are simply not retrieval benefits, and the two should not "
                "be advertised as one.",
            ],
        ),
        (
            "7. Limitations",
            [
                "The confirmatory corpus is one large regulatory document from one utility. "
                f"{_count_phrase(design['question_count'], 'question')} "
                f"{'does' if design['question_count'] == 1 else 'do'} not establish cross-domain, cross-utility, or "
                "open-domain generality. The benchmark was inherited and version-corrected "
                "after an invalidated partial run; annotation error may remain. Several controls form "
                "thematic clusters, reducing their effective diversity.",
                "The producer preserves source chunks one-to-one and adds only sequential "
                "links. It does not test semantic concept authoring, entity graphs, rich "
                "cross-concept relationships, trust-tier routing, freshness, lifecycle, or "
                "attested computation. Conclusions cannot be extended to those OKF v0.2 "
                "features. A producer that rewrote passages into genuine concepts, or that "
                "added meaningful links between related sections rather than merely "
                "consecutive ones, might behave differently; our result says nothing about "
                "that design, only about the one we pinned and disclosed.",
                "The frozen dense baseline was weaker than it should have been. Its encoder "
                "reads at most 256 word-piece tokens, and most passages here are longer, so "
                "the confirmatory dense arm was working from truncated text. We report that "
                "configuration as run rather than quietly replacing it, and we add an "
                "untruncated encoder as a diagnostic arm. This does not affect the "
                "confirmatory conclusion, which compares the OKF consumer against that same "
                "dense arm on equal terms, but it does mean the absolute dense numbers "
                "understate what a well-configured dense retriever would achieve. The "
                "diagnostic arms were chosen after seeing retrieval results and are "
                "exploratory. A preregistered replication should fix the encoder first and "
                "state the baseline set in advance.",
                "Self-RAG and FLARE are re-implementations, and Agentic RAG is repository-"
                "specific. Hosted model behavior can drift and need not be deterministic at "
                "temperature zero. The LLM judge was schema-constrained and gold-aware, but "
                "it can still exhibit systematic bias. A blinded human-validation sample is "
                "required before making strong claims based solely on rubric scores. Dollar "
                "cost and latency are tied to provider pricing, region, hardware, cache state, "
                "and the execution date.",
            ],
        ),
        (
            "8. Reproducibility, Ethics, and Artifact Availability",
            [
                "The artifact records the pinned OKF specification, source and benchmark "
                "hashes, deterministic bundle inventory, exact model IDs, prompts, schedule, "
                "token and call counts, costs, raw answers, resolved citations, trial-level "
                "judge objects, parse diagnostics, and seeded analysis. Generation and "
                "judging use append-only JSONL with exact complete-pair gates. The archived "
                "bundle digest is bec2561aa21eb4be38259d04d9aa34ed96b9abd57058fe7d10ce775eded1eb03.",
                f"The reported run is bound to benchmark {design.get('benchmark_id', '[benchmark ID]')} "
                f"with SHA-256 {design.get('benchmark_sha256', '[benchmark hash]')}. The "
                "analysis manifest records the invalidated-run deviation and sets "
                "superseded_partial_run_included to false.",
                "The public release should include code, derived annotations, the OKF bundle, "
                "and results only where licensing permits. If the source PDF cannot be "
                "redistributed, the release should provide its hash and lawful acquisition "
                "instructions rather than bundling it. Credentials, AWS identities, local "
                "database dumps, and private logs must be excluded. Final GitHub, Zenodo DOI, "
                "author, affiliation, ORCID, license, funding, and conflict metadata must be "
                "approved by the author before a public release.",
            ],
        ),
        (
            "9. Conclusion",
            [
                "Writing this corpus in the Open Knowledge Format and following its links "
                "did not improve retrieval or answer quality. The confirmatory comparison is "
                "a null, the format's own traversal policy costs a little page recall by "
                "displacing better-matching passages, and the one arm that did score highly "
                "was beaten by plain BM25 using no part of OKF at all. The apparent "
                "advantage we first measured came from comparing a lexical index against a "
                "dense encoder that could not read most of each passage. This is a narrow, "
                "negative, single-document result about one pinned producer and consumer, and "
                "it is consistent with a specification that deliberately leaves search "
                "undefined. OKF should be judged on what it does provide - portable, "
                "reviewable, provenance-carrying knowledge that outlives any one tool - and "
                "not marketed as a replacement for retrieval machinery it does not attempt to "
                "replace. We release the full artifact so that anyone can recheck these "
                "numbers or extend the comparison to producers and consumers that use more of "
                "what the format allows."
            ],
        ),
        (
            "10. Declarations",
            [
                f"Funding: {metadata.funding_statement}",
                f"Competing interests: {metadata.conflict_statement}",
                "The study used hosted language models to generate and evaluate answers. "
                "No human participants or personal data were involved. A future human "
                "validation exercise must use an approved annotation and "
                "data-handling protocol.",
            ],
        ),
    ]


def _primary_table(summary: dict[str, Any]) -> list[list[str]]:
    rows = [["Pipeline", "Raw", "OKF hybrid", "Delta [95% CI]", "Holm p"]]
    for row in summary["primary_raw_vs_okf_hybrid"]:
        rows.append(
            [
                PIPELINE_LABELS[row["pipeline"]],
                _f(row["raw_mean"]),
                _f(row["treatment_mean"]),
                f"{_f(row['mean_delta'])} [{_f(row['ci_low'])}, {_f(row['ci_high'])}]",
                _p(row["holm_p"]),
            ]
        )
    return rows


def _native_table(summary: dict[str, Any]) -> list[list[str]]:
    rows = [["Pipeline", "Raw", "OKF native", "Delta [95% CI]", "Holm p*"]]
    for row in summary["exploratory_raw_vs_okf_native"]:
        rows.append(
            [
                PIPELINE_LABELS[row["pipeline"]],
                _f(row["raw_mean"]),
                _f(row["treatment_mean"]),
                f"{_f(row['mean_delta'])} [{_f(row['ci_low'])}, {_f(row['ci_high'])}]",
                _p(row["holm_p"]),
            ]
        )
    return rows


def _retrieval_table(summary: dict[str, Any]) -> list[list[str]]:
    results = summary["retrieval_only"]["results"]
    rows = [["Condition", "Page hit", "Page recall", "MRR", "Median ms", "Linked"]]
    for condition in ("raw_vector", "okf_hybrid", "okf_native"):
        row = results[condition]
        rows.append(
            [
                CONDITION_LABELS[condition],
                _pct(row["page_hit_rate"]),
                _f(row["mean_expected_page_recall"]),
                _f(row["mean_reciprocal_rank"]),
                _f(row["median_latency_ms"], 2),
                _pct(row["mean_linked_chunk_fraction"]),
            ]
        )
    return rows


def _efficiency_table(summary: dict[str, Any]) -> list[list[str]]:
    rows = [["Pipeline", "Condition", "Correct.", "Calls", "Median s", "Gen $/q"]]
    for pipeline in PIPELINE_LABELS:
        for condition in ("raw_vector", "okf_hybrid", "okf_native"):
            row = _row_by(summary["descriptive"], pipeline=pipeline, condition=condition)
            rows.append(
                [
                    PIPELINE_LABELS[pipeline],
                    CONDITION_LABELS[condition].replace(" (exploratory)", ""),
                    _f(row["answer_correctness"]),
                    _f(row["mean_generator_calls"], 2),
                    _f(row["median_latency_ms"] / 1000, 2),
                    f"{row['mean_generation_cost_usd']:.4f}",
                ]
            )
    return rows


DIAGNOSTIC_ARMS = (
    ("raw_vector", "Dense, 256-token window", "no"),
    ("titan_dense", "Dense, 8192-token window", "no"),
    ("bm25_raw", "BM25, raw chunks", "no"),
    ("rrf_bm25_titan", "BM25 + dense fusion", "no"),
    ("okf_hybrid", "Dense seeds + OKF links", "yes"),
    ("okf_native", "BM25 concepts + OKF links", "yes"),
    ("okf_evidence_only", "As above, no frontmatter", "yes"),
    ("bm25_raw_adjacent", "BM25 + adjacency, no OKF", "no"),
    ("titan_dense_adjacent", "Dense + adjacency, no OKF", "no"),
)

DIAGNOSTIC_CONTRAST_LABELS = {
    "confirmatory: dense_minilm -> okf_hybrid": "OKF link expansion",
    "truncation effect: dense_minilm -> dense_titan": "Removing embedding truncation",
    "lexical effect: dense_minilm -> bm25_raw": "Switching to BM25",
    "lexical vs fair dense: dense_titan -> bm25_raw": "BM25 vs untruncated dense",
    "does OKF beat plain BM25: bm25_raw -> okf_native": "Adding OKF to plain BM25",
    "OKF frontmatter: okf_evidence_only -> okf_native": "OKF frontmatter fields",
    "adjacency without OKF: bm25_raw -> bm25_raw_adjacent": "Adjacency without OKF (BM25)",
    "adjacency on fair dense: dense_titan -> dense_titan_adjacent": "Adjacency without OKF (dense)",
    "fusion: bm25_raw -> rrf_bm25_titan": "Adding dense fusion to BM25",
}


def _has_diagnostics(summary: dict[str, Any]) -> bool:
    return bool(summary.get("retrieval_diagnostics"))


def _diagnostic_table(summary: dict[str, Any]) -> list[list[str]]:
    arms = summary["retrieval_diagnostics"]["arms"]
    rows = [["Retrieval arm", "Uses OKF", "Page hit", "Recall", "nDCG@10", "Median ms"]]
    for key, description, uses_okf in DIAGNOSTIC_ARMS:
        arm = arms.get(key)
        if not arm:
            continue
        latency = arm.get("median_latency_ms")
        rows.append(
            [
                description,
                uses_okf,
                _pct(arm["page_hit_rate"]),
                _f(arm["mean_expected_page_recall"]),
                _f(arm["mean_ndcg_at_k"]),
                _f(latency, 1) if isinstance(latency, (int, float)) else "n/a",
            ]
        )
    return rows


def _diagnostic_contrast_table(summary: dict[str, Any]) -> list[list[str]]:
    """Contrasts in explanatory order, not the JSON's alphabetical key order."""

    contrasts = summary["retrieval_diagnostics"]["contrasts"]
    rows = [["Change tested", "Recall delta [95% CI]", "Holm p"]]
    ordered = [key for key in DIAGNOSTIC_CONTRAST_LABELS if key in contrasts]
    ordered += [key for key in contrasts if key not in DIAGNOSTIC_CONTRAST_LABELS]
    for key in ordered:
        result = contrasts[key]
        delta = result["recall_delta"]
        holm = result.get("page_hit_p_holm")
        rows.append(
            [
                DIAGNOSTIC_CONTRAST_LABELS.get(key, key),
                f"{delta['mean_difference']:+.3f} "
                f"[{delta['ci_low']:+.3f}, {delta['ci_high']:+.3f}]",
                _p(holm) if isinstance(holm, (int, float)) else "n/a",
            ]
        )
    return rows


def _treatment_table() -> list[list[str]]:
    return [
        ["Condition", "Discovery", "Traversal", "Status"],
        ["Raw vector", "Dense top-k", "None", "Confirmatory control"],
        ["OKF hybrid", "50% dense seeds", "One-hop prev/next", "Confirmatory treatment"],
        ["OKF native", "Weighted BM25", "One-hop prev/next", "Exploratory"],
    ]


def _md_table(data: list[list[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(data[0]) + " |",
            "| " + " | ".join("---" for _ in data[0]) + " |",
            *("| " + " | ".join(row) + " |" for row in data[1:]),
        ]
    )


def _markdown(summary: dict[str, Any], metadata: ManuscriptMetadata) -> str:
    blocks = [
        "# Open Knowledge Format v0.2 as a Retrieval Substrate",
        "",
        "## A Controlled Evaluation Across Five RAG Pipelines",
        "",
        f"**{metadata.author}**  ",
        f"{metadata.affiliation}  ",
        f"ORCID: {metadata.orcid}  ",
        f"Preprint - {metadata.preprint_date} - {metadata.doi_display}",
        "",
        "## Abstract",
        "",
        _abstract(summary),
        "",
        "**Keywords:** retrieval-augmented generation; information retrieval; Open "
        "Knowledge Format; hybrid retrieval; provenance; document question answering",
        "",
    ]
    for title, paragraphs in _section_content(summary, metadata):
        blocks.extend([f"## {title}", ""])
        for paragraph in paragraphs:
            blocks.extend([paragraph, ""])
        if title == "3. OKF Producer and Retrieval Conditions":
            blocks.extend([_md_table(_treatment_table()), ""])
        if title == "5. Results":
            blocks.extend(
                [
                    "### Retrieval-only outcomes",
                    "",
                    _md_table(_retrieval_table(summary)),
                    "",
                    *(
                        [
                            "### Where the retrieval difference comes from",
                            "",
                            _md_table(_diagnostic_table(summary)),
                            "",
                            _md_table(_diagnostic_contrast_table(summary)),
                            "",
                        ]
                        if _has_diagnostics(summary)
                        else []
                    ),
                    "### Confirmatory answer correctness",
                    "",
                    _md_table(_primary_table(summary)),
                    "",
                    "### Exploratory OKF-native answer correctness",
                    "",
                    _md_table(_native_table(summary)),
                    "",
                    "### Efficiency",
                    "",
                    _md_table(_efficiency_table(summary)),
                    "",
                ]
            )
        if title == "8. Reproducibility, Ethics, and Artifact Availability":
            archival_identifier = (
                f"[{metadata.doi_display}]({metadata.doi_url})"
                if metadata.doi_url
                else metadata.doi_display
            )
            blocks.extend(
                [
                    f"**Artifact repository:** {metadata.repository_url}  ",
                    f"**Archival identifier:** {archival_identifier}",
                    "",
                ]
            )
    blocks.extend(["## References", ""])
    for index, (citation, url) in enumerate(REFERENCES, start=1):
        blocks.extend([f"{index}. {citation} {url}", ""])
    return "\n".join(blocks).rstrip() + "\n"


def _tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


_CITATION_RE = re.compile(r"\[((?:\d+)(?:[-,]\d+)*)\]")


def _citation_keys(label: str) -> list[str]:
    keys: list[str] = []
    for part in label.split(","):
        if "-" in part:
            start, end = (int(value) for value in part.split("-", 1))
            keys.extend(f"ref{value}" for value in range(start, end + 1))
        else:
            keys.append(f"ref{int(part)}")
    return keys


def _latex_text(text: str) -> str:
    """Escape prose while converting numeric bracket citations to real citations."""

    parts: list[str] = []
    cursor = 0
    for match in _CITATION_RE.finditer(text):
        parts.append(_tex_escape(text[cursor:match.start()]))
        parts.append(r"\cite{" + ",".join(_citation_keys(match.group(1))) + "}")
        cursor = match.end()
    parts.append(_tex_escape(text[cursor:]))
    return "".join(parts)


def _latex_table(
    data: list[list[str]], align: str, *, caption: str, label: str, size: str = "small"
) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        rf"\{size}",
        rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
    ]
    lines.append(" & ".join(rf"\textbf{{{_tex_escape(value)}}}" for value in data[0]) + r" \\")
    lines.append(r"\midrule")
    for row in data[1:]:
        lines.append(" & ".join(_tex_escape(value) for value in row) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            rf"\caption{{{_tex_escape(caption)}}}",
            rf"\label{{{label}}}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines)


def _latex(summary: dict[str, Any], metadata: ManuscriptMetadata) -> str:
    design = _study_design(summary)
    author_lines = [metadata.author, metadata.affiliation]
    if metadata.orcid.strip():
        author_lines.append(f"ORCID: {metadata.orcid}")
    latex_author = r"\\".join(_tex_escape(value) for value in author_lines)
    lines = [
        r"\documentclass[10pt]{article}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[letterpaper,margin=0.75in]{geometry}",
        r"\usepackage{booktabs}",
        r"\usepackage{graphicx}",
        r"\usepackage{xcolor}",
        r"\usepackage{microtype}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\usepackage{url}",
        r"\definecolor{accent}{HTML}{174A7E}",
        r"\hypersetup{colorlinks=true,urlcolor=accent,citecolor=accent,linkcolor=accent}",
        r"\title{\textcolor{accent}{Open Knowledge Format v0.2 as a Retrieval Substrate}\\\large A Controlled Evaluation Across Five RAG Pipelines}",
        rf"\author{{{latex_author}}}",
        rf"\date{{Preprint -- {_tex_escape(metadata.preprint_date)} -- {_tex_escape(metadata.doi_display)}}}",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{abstract}",
        _latex_text(_abstract(summary)),
        r"\end{abstract}",
        r"\noindent\textbf{Keywords:} retrieval-augmented generation; information retrieval; Open Knowledge Format; hybrid retrieval; provenance; document question answering",
    ]
    for title, paragraphs in _section_content(summary, metadata):
        section_title = title.split(". ", 1)[1] if ". " in title else title
        lines.append(rf"\section{{{_tex_escape(section_title)}}}")
        lines.extend(_latex_text(paragraph) + "\n" for paragraph in paragraphs)
        if title == "3. OKF Producer and Retrieval Conditions":
            lines.append(
                _latex_table(
                    _treatment_table(),
                    "llll",
                    caption=(
                        "Frozen retrieval conditions. OKF evidence text and source "
                        "boundaries are unchanged."
                    ),
                    label="tab:treatments",
                )
            )
        if title == "5. Results":
            lines.extend(
                [
                    r"\subsection{Retrieval-only outcomes}",
                    _latex_table(
                        _retrieval_table(summary),
                        "lrrrrr",
                        caption=(
                            "Top-10 retrieval over "
                            f"{_count_phrase(design['answerable_count'], 'answerable question')}."
                        ),
                        label="tab:retrieval",
                    ),
                    *(
                        [
                            r"\subsection{Where the retrieval difference comes from}",
                            _latex_table(
                                _diagnostic_table(summary),
                                "llrrrr",
                                caption=(
                                    "Exploratory decomposition. Each arm changes one "
                                    "factor: matching family, embedding input window, "
                                    "or OKF component. Added after the frozen screen."
                                ),
                                label="tab:diagnostic",
                            ),
                            _latex_table(
                                _diagnostic_contrast_table(summary),
                                "lrr",
                                caption=(
                                    "Paired page-recall effect of each single change, "
                                    "with Holm correction inside the diagnostic family."
                                ),
                                label="tab:diagnostic-contrasts",
                            ),
                            r"\begin{figure}[ht]",
                            r"\centering\includegraphics[width=\linewidth]{figures/figure_diagnostic.png}",
                            r"\caption{Where the retrieval difference comes from. "
                            r"The best-scoring arm uses no OKF component.}",
                            r"\end{figure}",
                        ]
                        if _has_diagnostics(summary)
                        else []
                    ),
                    r"\subsection{Confirmatory answer correctness}",
                    _latex_table(
                        _primary_table(summary),
                        "lrrrr",
                        caption=(
                            "Gold-aware correctness. Delta is OKF hybrid minus raw "
                            f"vector; Holm correction spans {design['pipeline_count']} pipelines."
                        ),
                        label="tab:primary",
                    ),
                    r"\begin{figure}[ht]",
                    r"\centering\includegraphics[width=\linewidth]{figures/figure_correctness.png}",
                    r"\caption{Absolute correctness by pipeline and retrieval condition. OKF-native answer results are exploratory.}",
                    r"\end{figure}",
                    r"\subsection{Exploratory OKF-native results}",
                    _latex_table(
                        _native_table(summary),
                        "lrrrr",
                        caption=(
                            "Exploratory paired contrasts. Holm adjustment is internal "
                            "to the separately named exploratory family."
                        ),
                        label="tab:exploratory",
                    ),
                    r"\begin{figure}[ht]",
                    r"\centering\includegraphics[width=\linewidth]{figures/figure_effects.png}",
                    r"\caption{Mean paired correctness differences with 95\% bootstrap intervals.}",
                    r"\end{figure}",
                    r"\subsection{Efficiency}",
                    _latex_table(
                        _efficiency_table(summary),
                        "llrrrr",
                        caption=(
                            "Descriptive generation efficiency. Cost excludes the "
                            "experimental judge."
                        ),
                        label="tab:efficiency",
                        size="scriptsize",
                    ),
                ]
            )
        if title == "8. Reproducibility, Ethics, and Artifact Availability":
            repository = metadata.repository_url.strip()
            if repository.startswith(("https://", "http://")):
                repository_value = rf"\url{{{repository}}}"
            else:
                repository_value = _tex_escape(repository)
            lines.extend(
                [
                    rf"\noindent\textbf{{Artifact repository:}} {repository_value}\\",
                    (
                        rf"\textbf{{Archival identifier:}} \href{{{metadata.doi_url}}}"
                        rf"{{{_tex_escape(metadata.doi_display)}}}"
                        if metadata.doi_url
                        else rf"\textbf{{Archival identifier:}} {_tex_escape(metadata.doi_display)}"
                    ),
                ]
            )
    lines.append(r"\begin{thebibliography}{99}")
    for index, (citation, url) in enumerate(REFERENCES, start=1):
        lines.append(
            rf"\bibitem{{ref{index}}} {_tex_escape(citation)} \url{{{url}}}"
        )
    lines.extend([r"\end{thebibliography}", r"\end{document}", ""])
    return "\n\n".join(lines)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PaperTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
            leading=23, textColor=ACCENT, alignment=TA_CENTER, spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=12,
            leading=15, alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceAfter=14,
        ),
        "author": ParagraphStyle(
            "Author", parent=base["Normal"], fontName="Helvetica", fontSize=10,
            leading=13, alignment=TA_CENTER, spaceAfter=12,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Times-Roman", fontSize=9.5,
            leading=12.5, alignment=TA_JUSTIFY, spaceAfter=7, allowWidows=0, allowOrphans=0,
        ),
        "body_long_token": ParagraphStyle(
            "BodyLongToken", parent=base["BodyText"], fontName="Times-Roman", fontSize=9.5,
            leading=12.5, alignment=TA_LEFT, spaceAfter=7, allowWidows=0, allowOrphans=0,
        ),
        "abstract": ParagraphStyle(
            "Abstract", parent=base["BodyText"], fontName="Helvetica", fontSize=8.8,
            leading=11.5, alignment=TA_JUSTIFY, leftIndent=10, rightIndent=10, spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=13.5,
            leading=16, textColor=ACCENT, spaceBefore=12, spaceAfter=6, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5,
            leading=13, textColor=colors.HexColor("#333333"), spaceBefore=9, spaceAfter=5,
            keepWithNext=True,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=7.7,
            leading=9.5, alignment=TA_LEFT, textColor=colors.HexColor("#444444"), spaceAfter=8,
        ),
        "reference": ParagraphStyle(
            "Reference", parent=base["Normal"], fontName="Times-Roman", fontSize=7.8,
            leading=10, leftIndent=14, firstLineIndent=-14, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
            leading=9.5, textColor=colors.HexColor("#444444"),
        ),
    }


def _pdf_table(data: list[list[str]], widths: list[float], *, font_size: float = 7.5) -> Table:
    header_style = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=font_size,
        leading=font_size + 2,
        textColor=colors.white,
    )
    body_style = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=font_size,
        leading=font_size + 2,
        textColor=colors.HexColor("#1F2328"),
    )
    cells = [
        [
            Paragraph(escape(str(value)), header_style if row_index == 0 else body_style)
            for value in row
        ]
        for row_index, row in enumerate(data)
    ]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4D0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _pdf_table_block(
    data: list[list[str]],
    widths: list[float],
    caption: str,
    caption_style: ParagraphStyle,
    *,
    font_size: float = 7.5,
) -> KeepTogether:
    return KeepTogether(
        [
            _pdf_table(data, widths, font_size=font_size),
            Paragraph(caption, caption_style),
        ]
    )


def _pdf_subsection_table(
    title: str,
    data: list[list[str]],
    widths: list[float],
    caption: str,
    styles: dict[str, ParagraphStyle],
    *,
    font_size: float = 7.5,
) -> KeepTogether:
    return KeepTogether(
        [
            Paragraph(title, styles["h2"]),
            _pdf_table(data, widths, font_size=font_size),
            Paragraph(caption, styles["caption"]),
        ]
    )


def _scaled_image(path: Path, *, max_width: float, max_height: float) -> Image:
    """Preserve figure aspect ratio while fitting the available page frame."""

    image = Image(str(path))
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    return image


def _artifact_pdf_lines(metadata: ManuscriptMetadata, style: ParagraphStyle) -> list[Paragraph]:
    repository = escape(metadata.repository_url)
    if metadata.repository_url.startswith(("https://", "http://")):
        repository = (
            f'<link href="{escape(metadata.repository_url)}" color="#174A7E">'
            f"{repository}</link>"
        )
    doi = escape(metadata.doi_display)
    if metadata.doi_url:
        doi = f'<link href="{escape(metadata.doi_url)}" color="#174A7E">{doi}</link>'
    return [
        Paragraph(f"<b>Artifact repository:</b> {repository}", style),
        Paragraph(f"<b>Archival identifier:</b> {doi}", style),
    ]


def _header_footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.7 * inch, 10.55 * inch, "OKF v0.2 as a Retrieval Substrate")
        canvas.drawRightString(7.8 * inch, 10.55 * inch, "Preprint")
        canvas.setStrokeColor(colors.HexColor("#D0D7DE"))
        canvas.line(0.7 * inch, 10.45 * inch, 7.8 * inch, 10.45 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(4.25 * inch, 0.42 * inch, str(doc.page))
    canvas.restoreState()


def _render_pdf(
    summary: dict[str, Any], output: Path, metadata: ManuscriptMetadata
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    design = _study_design(summary)
    styles = _styles()
    doc = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.65 * inch,
        title="Open Knowledge Format v0.2 as a Retrieval Substrate",
        author=metadata.author,
        subject="Controlled evaluation across five RAG pipelines",
        keywords="OKF, RAG, information retrieval, provenance",
    )
    story: list[Any] = [
        Spacer(1, 0.15 * inch),
        Paragraph("Open Knowledge Format v0.2 as a Retrieval Substrate", styles["title"]),
        Paragraph("A Controlled Evaluation Across Five RAG Pipelines", styles["subtitle"]),
        Paragraph(
            f"<b>{escape(metadata.author)}</b><br/>{escape(metadata.affiliation)}<br/>"
            f"ORCID: {escape(metadata.orcid)}<br/>"
            f"Preprint - {escape(metadata.preprint_date)} - {escape(metadata.doi_display)}",
            styles["author"],
        ),
        HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceAfter=10),
        Table(
            [[Paragraph("<b>Abstract</b>", styles["abstract"])], [Paragraph(escape(_abstract(summary)), styles["abstract"])]],
            colWidths=[6.85 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.6, ACCENT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        ),
        Spacer(1, 7),
        Paragraph(
            "<b>Keywords:</b> retrieval-augmented generation; information retrieval; "
            "Open Knowledge Format; hybrid retrieval; provenance; document question answering",
            styles["small"],
        ),
    ]

    for title, paragraphs in _section_content(summary, metadata):
        story.append(Paragraph(escape(title), styles["h1"]))
        for paragraph in paragraphs:
            body_style = (
                styles["body_long_token"]
                if re.search(r"\b[0-9a-f]{40,}\b", paragraph, flags=re.IGNORECASE)
                else styles["body"]
            )
            story.append(Paragraph(escape(paragraph), body_style))
        if title == "3. OKF Producer and Retrieval Conditions":
            story.append(
                _pdf_table_block(
                    _treatment_table(),
                    [1.15 * inch, 1.5 * inch, 1.65 * inch, 2.2 * inch],
                    "Table 1. Frozen retrieval conditions. OKF evidence text and source boundaries are unchanged.",
                    styles["caption"],
                )
            )
        if title == "5. Results":
            # The diagnostic decomposition occupies subsection 5.2, two tables and
            # one figure when present, so later numbering shifts accordingly.
            shift = 2 if _has_diagnostics(summary) else 0
            figure_paths = {
                Path(path).name: Path(path) for path in summary.get("figures", [])
            }
            diagnostic_figure = figure_paths.get(
                "figure_diagnostic.png", Path("__missing__")
            )
            fig_shift = 1 if diagnostic_figure.is_file() else 0
            story.extend(
                [
                    _pdf_subsection_table(
                        "5.1 Retrieval-only outcomes",
                        _retrieval_table(summary),
                        [1.65 * inch, 0.85 * inch, 0.85 * inch, 0.65 * inch, 0.8 * inch, 0.75 * inch],
                        "Table 2. Top-10 retrieval over "
                        f"{_count_phrase(design['answerable_count'], 'answerable question')}. "
                        "Page hit denotes at least one expected page; linked is the mean fraction reached through traversal.",
                        styles,
                    ),
                ]
            )
            if _has_diagnostics(summary):
                story.extend(
                    [
                        _pdf_subsection_table(
                            "5.2 Where the retrieval difference comes from",
                            _diagnostic_table(summary),
                            [1.72 * inch, 0.62 * inch, 0.72 * inch, 0.68 * inch, 0.72 * inch, 0.78 * inch],
                            "Table 3. Exploratory decomposition over "
                            f"{_count_phrase(design['answerable_count'], 'answerable question')}. "
                            "Each arm changes one factor: the matching family, the embedding input window, or an OKF component. "
                            "Added after the frozen retrieval screen.",
                            styles,
                            font_size=6.8,
                        ),
                        _pdf_table_block(
                            _diagnostic_contrast_table(summary),
                            [2.6 * inch, 2.35 * inch, 0.7 * inch],
                            "Table 4. Paired page-recall effect of each single change. "
                            "Holm correction is internal to the diagnostic family and does not alter confirmatory inference.",
                            styles["caption"],
                            font_size=6.8,
                        ),
                    ]
                )
                if diagnostic_figure.is_file():
                    story.append(
                        KeepTogether(
                            [
                                _scaled_image(
                                    diagnostic_figure,
                                    max_width=6.55 * inch,
                                    max_height=3.3 * inch,
                                ),
                                Paragraph(
                                    "Figure 1. Where the retrieval difference comes from. "
                                    "Bars are shaded by whether the arm uses any OKF component; "
                                    "the best-scoring arm uses none.",
                                    styles["caption"],
                                ),
                            ]
                        )
                    )
            story.extend(
                [
                    _pdf_subsection_table(
                        f"5.{2 + shift // 2} Confirmatory answer correctness",
                        _primary_table(summary),
                        [1.45 * inch, 0.6 * inch, 0.8 * inch, 2.35 * inch, 0.7 * inch],
                        f"Table {3 + shift}. Gold-aware correctness over "
                        f"{_count_phrase(design['answerable_count'], 'paired answerable question')} "
                        f"per pipeline. Delta is OKF hybrid minus raw vector; p-values are Holm-adjusted across {design['pipeline_count']} tests.",
                        styles,
                    ),
                ]
            )
            correctness = figure_paths.get("figure_correctness.png", Path("__missing__"))
            effects = figure_paths.get("figure_effects.png", Path("__missing__"))
            if correctness.is_file():
                story.extend(
                    [
                        KeepTogether(
                            [
                                _scaled_image(
                                    correctness,
                                    max_width=6.55 * inch,
                                    max_height=3.14 * inch,
                                ),
                                Paragraph(
                                    f"Figure {1 + fig_shift}. Absolute correctness by pipeline and retrieval condition. OKF-native answer results are exploratory.",
                                    styles["caption"],
                                ),
                            ]
                        ),
                    ]
                )
            story.extend(
                [
                    _pdf_subsection_table(
                        f"5.{3 + shift // 2} Exploratory OKF-native answer correctness",
                        _native_table(summary),
                        [1.45 * inch, 0.6 * inch, 0.8 * inch, 2.35 * inch, 0.7 * inch],
                        f"Table {4 + shift}. Exploratory paired contrasts. Holm p-values are internal to the separately named exploratory family and do not alter confirmatory inference.",
                        styles,
                    ),
                ]
            )
            if effects.is_file():
                story.extend(
                    [
                        KeepTogether(
                            [
                                _scaled_image(
                                    effects,
                                    max_width=6.55 * inch,
                                    max_height=3.49 * inch,
                                ),
                                Paragraph(
                                    f"Figure {2 + fig_shift}. Pipeline-specific mean paired correctness differences with 95% bootstrap intervals.",
                                    styles["caption"],
                                ),
                            ]
                        ),
                    ]
                )
            story.extend(
                [
                    _pdf_subsection_table(
                        f"5.{4 + shift // 2} Efficiency",
                        _efficiency_table(summary),
                        [1.28 * inch, 1.15 * inch, 0.62 * inch, 0.55 * inch, 0.68 * inch, 0.7 * inch],
                        f"Table {5 + shift}. Descriptive generation efficiency. Cost excludes the experimental judge. Concurrent wall time and model-provider conditions limit portability.",
                        styles,
                        font_size=6.6,
                    ),
                ]
            )
        if title == "8. Reproducibility, Ethics, and Artifact Availability":
            story.extend(_artifact_pdf_lines(metadata, styles["small"]))

    story.append(PageBreak())
    story.append(Paragraph("References", styles["h1"]))
    for index, (citation, url) in enumerate(REFERENCES, start=1):
        story.append(
            Paragraph(
                f"[{index}] {escape(citation)} <link href=\"{escape(url)}\" color=\"#174A7E\">{escape(url)}</link>",
                styles["reference"],
            )
        )
    story.extend(
        [
            Spacer(1, 8),
            HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#B8C4D0")),
            Paragraph(
                (
                    "Draft artifact note. Author identity, affiliation, ORCID, licenses, "
                    "repository URL, and Zenodo DOI must be approved before public submission. "
                    if metadata.is_draft
                    else "Artifact note. This manuscript identifies the approved repository and archival DOI. "
                )
                + "A blinded human-validation sample remains recommended before strong rubric-based claims.",
                styles["small"],
            ),
        ]
    )
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)


def _resolve_figure_paths(
    summary: dict[str, Any], analysis_path: Path
) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for value in summary.get("figures", []):
        path = Path(value)
        candidates = (
            [path]
            if path.is_absolute()
            else [
                analysis_path.parent / path,
                analysis_path.parent / path.name,
                PACKAGE_ROOT / path,
                REPO_ROOT / path,
            ]
        )
        source = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
        if source is not None:
            resolved[source.name] = source
    required = {"figure_correctness.png", "figure_effects.png"}
    # Produced only when the exploratory diagnostic arms are present.
    optional = {"figure_diagnostic.png"}
    missing = sorted(required - set(resolved))
    if missing:
        raise FileNotFoundError(f"analysis figures are missing: {missing}")
    kept = sorted((required | optional) & set(resolved))
    summary["figures"] = [str(resolved[name]) for name in kept]
    return {name: resolved[name] for name in kept}


def _stage_latex_figures(figures: dict[str, Path], tex_path: Path) -> None:
    figure_dir = tex_path.parent / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    for name, source in figures.items():
        destination = figure_dir / name
        if source != destination.resolve():
            shutil.copyfile(source, destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--tex", type=Path, default=DEFAULT_TEX)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--author", default="[Author name]")
    parser.add_argument("--affiliation", default="[Affiliation]")
    parser.add_argument("--orcid", default="[ORCID]")
    parser.add_argument("--preprint-date", default=DEFAULT_PREPRINT_DATE)
    parser.add_argument("--doi", default="pending")
    parser.add_argument("--repository-url", default="[Repository URL]")
    parser.add_argument("--funding-statement", default="[Funding statement]")
    parser.add_argument("--conflict-statement", default="[Conflict-of-interest statement]")
    args = parser.parse_args()
    summary = json.loads(args.analysis.read_text(encoding="utf-8"))
    if not summary.get("completion", {}).get("complete"):
        raise RuntimeError("analysis is not complete")
    metadata = ManuscriptMetadata(
        author=args.author,
        affiliation=args.affiliation,
        preprint_date=args.preprint_date,
        doi=args.doi,
        repository_url=args.repository_url,
        orcid=args.orcid,
        funding_statement=args.funding_statement,
        conflict_statement=args.conflict_statement,
    )
    figures = _resolve_figure_paths(summary, args.analysis.resolve())
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.tex.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(
        _markdown(summary, metadata), encoding="utf-8"
    )
    _stage_latex_figures(figures, args.tex)
    args.tex.write_text(_latex(summary, metadata), encoding="utf-8")
    _render_pdf(summary, args.pdf, metadata)
    print(args.markdown)
    print(args.tex)
    print(args.pdf)


if __name__ == "__main__":
    main()
