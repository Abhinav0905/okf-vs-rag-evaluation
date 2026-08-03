#!/usr/bin/env python3
"""Build the paper's figures from the result records.

Three figures, each reading only from the stored summaries so they cannot drift
from the data:

    figure_1_decomposition.png  retrieval by arm, coloured by whether OKF is used
    figure_2_forest_retrieval.png  paired page-recall effect of each single change
    figure_3_forest_answers.png    paired answer-quality effects in the A/B

Usage:  python paper/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "paper/figures"
DIAG = json.loads((ROOT / "results/retrieval_diagnostics/diagnostic_summary.json").read_text())
TOPIC = json.loads((ROOT / "results/topic_okf/topic_summary.json").read_text())
AB = json.loads((ROOT / "results/hybrid_ab/ab_summary.json").read_text())

# Colour-blind-safe: blue for arms with no OKF, orange for arms using OKF.
NO_OKF = "#3B6FB6"
USES_OKF = "#D95F02"
GREY = "#5A5A5A"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
    "figure.dpi": 200,
})


def figure_1() -> None:
    """Retrieval at a matched context budget, ordered worst to best."""
    arms = TOPIC["arms"]
    rows = [
        ("Dense chunks only", "chunks_dense", False),
        ("OKF topics + hierarchy links", "okf_topic_hierarchy", True),
        ("OKF topics", "okf_topic_bm25", True),
        ("Vector DB + OKF topics", "okf_plus_rag_topic", True),
        ("Vector DB + OKF chunks", "okf_plus_rag_chain", True),
        ("BM25 chunks (no OKF)", "chunks_bm25", False),
        ("OKF chunk-chain + links", "okf_chain_bm25", True),
    ]
    rows = [r for r in rows if r[1] in arms]
    rows.sort(key=lambda r: arms[r[1]]["page_hit_rate"])
    labels = [r[0] for r in rows]
    values = [100 * arms[r[1]]["page_hit_rate"] for r in rows]
    colours = [USES_OKF if r[2] else NO_OKF for r in rows]

    fig, ax = plt.subplots(figsize=(6.6, 3.35))
    bars = ax.barh(labels, values, color=colours, height=0.68)
    for bar, value in zip(bars, values):
        ax.text(value + 0.9, bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}%", va="center", fontsize=8.5)
    best_no_okf = max(v for v, r in zip(values, rows) if not r[2])
    ax.axvline(best_no_okf, color=GREY, ls="--", lw=1.0)
    ax.annotate("best arm using no OKF", xy=(best_no_okf, len(rows) - 0.4),
                xytext=(best_no_okf - 2.5, len(rows) - 0.35),
                fontsize=7.8, color=GREY, ha="right", va="center")
    ax.set_xlabel("Questions where an expected page reached the context (%)")
    ax.set_xlim(0, 104)
    handles = [plt.Rectangle((0, 0), 1, 1, color=NO_OKF),
               plt.Rectangle((0, 0), 1, 1, color=USES_OKF)]
    ax.legend(handles, ["no OKF", "uses OKF"], loc="lower right",
              frameon=True, framealpha=0.95, edgecolor="none", fontsize=8)
    ax.set_title(f"Retrieval at a matched {TOPIC['token_budget']}-token context budget "
                 f"(n={TOPIC['scored_questions']})", fontsize=9.5, pad=8)
    fig.tight_layout()
    fig.savefig(FIGS / "figure_1_decomposition.png", bbox_inches="tight")
    plt.close(fig)


def _forest(ax, entries, xlabel, title) -> None:
    ys = list(range(len(entries)))[::-1]
    for y, (label, delta, low, high, sig) in zip(ys, entries):
        colour = USES_OKF if sig else GREY
        ax.plot([low, high], [y, y], color=colour, lw=1.6, solid_capstyle="round")
        ax.plot([low, low], [y - 0.13, y + 0.13], color=colour, lw=1.2)
        ax.plot([high, high], [y - 0.13, y + 0.13], color=colour, lw=1.2)
        ax.plot([delta], [y], "o", color=colour, ms=5.5, zorder=3)
    ax.axvline(0, color="black", lw=0.9)
    ax.set_yticks(ys)
    ax.set_yticklabels([e[0] for e in entries], fontsize=8.3)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=9.5, pad=8)


def figure_2() -> None:
    """Effect of changing one factor at a time on page recall."""
    dc, tc = DIAG["contrasts"], TOPIC["contrasts"]

    def pick(prefix, source):
        return next(v for k, v in source.items() if k.startswith(prefix))

    spec = [
        ("Remove encoder truncation", pick("truncation effect", dc)),
        ("Switch dense → BM25", pick("lexical effect", dc)),
        ("BM25 vs untruncated dense", pick("lexical vs fair dense", dc)),
        ("Add OKF to plain BM25", pick("does OKF beat plain BM25", dc)),
        ("OKF frontmatter fields", pick("OKF frontmatter", dc)),
        ("Adjacency, no OKF", pick("adjacency without OKF", dc)),
        ("Topic structure vs BM25 chunks", pick("topic structure vs BM25 chunks", tc)),
        ("Follow hierarchy links", pick("following hierarchy links", tc)),
    ]
    entries = []
    for label, c in spec:
        d = c["recall_delta"]
        sig = d["ci_low"] > 0 or d["ci_high"] < 0
        entries.append((label, d["mean_difference"], d["ci_low"], d["ci_high"], sig))

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    _forest(ax, entries,
            "Change in expected-page recall (paired, 95% bootstrap CI)",
            "Each row changes exactly one factor; positive is better")
    ax.text(0.985, 0.03, "coloured = interval excludes zero", transform=ax.transAxes,
            ha="right", fontsize=7.6, color=USES_OKF)
    fig.tight_layout()
    fig.savefig(FIGS / "figure_2_forest_retrieval.png", bbox_inches="tight")
    plt.close(fig)


def figure_3() -> None:
    """Answer-quality effects of adding OKF to a strong hybrid baseline."""
    entries = []
    for label, c in sorted(AB["contrasts"].items()):
        arm = "OKF topics" if "topics" in label else "OKF chunks"
        for dim in ("correctness", "completeness", "groundedness", "citation_quality"):
            d = c["dimension_deltas"][dim]
            sig = d["ci_low"] > 0 or d["ci_high"] < 0
            pretty = dim.replace("_", " ").capitalize()
            entries.append((f"{pretty} — {arm}", d["mean_difference"],
                            d["ci_low"], d["ci_high"], sig))

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    _forest(ax, entries,
            "Change in judged score, 1–5 scale (paired, 95% bootstrap CI)",
            "Adding OKF to a strong hybrid baseline (n=79); positive is better")
    ax.text(0.985, 0.02, "coloured = interval excludes zero", transform=ax.transAxes,
            ha="right", fontsize=7.6, color=USES_OKF)
    fig.tight_layout()
    fig.savefig(FIGS / "figure_3_forest_answers.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    figure_1()
    figure_2()
    figure_3()
    for path in sorted(FIGS.glob("*.png")):
        print(f"  {path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
