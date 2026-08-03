#!/usr/bin/env python3
"""Build the immutable, post-audit PG&E benchmark used by the OKF trial.

The repository contains two complementary inherited question sets.  This
script normalises and combines them without using model-generated content:

* ``evaluation/trial1_baseline/golden_test_set.json`` (35 questions)
* ``evaluation/harmonized/wmp_questions.json`` (65 questions)

The output records source-file hashes so a release can prove exactly which
inputs produced the benchmark.  It is intentionally deterministic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLDEN = REPO_ROOT / "evaluation/trial1_baseline/golden_test_set.json"
DEFAULT_HARMONIZED = REPO_ROOT / "evaluation/harmonized/wmp_questions.json"
DEFAULT_OUTPUT = REPO_ROOT / "okf_trial_data/data/benchmark_questions.json"

# Source-level review found duplicated controls, false-negative annotations,
# imprecise references, and unsupported synthetic joins in the inherited sets.
# The corrections below are explicit and source-grounded.  The first pass
# preceded paid execution; the second followed an invalidated partial generation
# run but preceded all answer-quality judging and condition-level analysis.  The
# timing and superseded hashes are recorded in the output metadata and protocol.
EXCLUDED_DUPLICATES = {
    "wmp_q59": "Near-exact duplicate of supported SF-002, but mislabeled unanswerable.",
    "wmp_q60": "Near-exact duplicate of wmp_q50.",
    "wmp_q62": "Near-exact duplicate of wmp_q51.",
}

# A second source-level review, performed before any answer-quality judging,
# found four synthetic prompts whose claimed causal links were not stated by
# the source.  Recasting them as unrelated conjunctions would change the
# construct, so the publication benchmark removes them rather than disguising
# the defect with a narrower reference answer.
EXCLUDED_UNSUPPORTED_SYNTHESIS = {
    "wmp_q36": (
        "The source does not connect the table-of-contents college partnership "
        "entry to the plan's adaptive-learning statement."
    ),
    "wmp_q38": (
        "The source does not connect Troublemen qualifications to monitoring or "
        "reinspection of Resource Conservation District projects."
    ),
    "wmp_q42": (
        "The source does not state that an illustrative risk calculation feeds "
        "the adaptive-strategy process, and the example overlaps corrected q49."
    ),
    "wmp_q48": (
        "The source does not state that the cited work-order backlog systems "
        "would have prevented the fuse behavior associated with the Dixie Fire."
    ),
}

ANNOTATION_CORRECTIONS: dict[str, dict[str, Any]] = {
    "SF-006": {
        "question": (
            "What radial clearance does GO 95 Appendix E Case 14 require from "
            "vegetation in the HFTD for bare conductors operating at 2,400 volts "
            "or more but below 72,000 volts?"
        ),
        "reference_answer": (
            "Case 14 requires 12 feet of radial clearance from vegetation in the "
            "HFTD for bare conductors on lines operating at 2,400 volts or more "
            "but below 72,000 volts."
        ),
        "expected_pages": [391],
        "curation_note": (
            "Corrected the evidence page to the page containing the Case 14 "
            "12-foot clearance row; the inherited page only introduced the table."
        ),
    },
    "TB-006": {
        "expected_pages": [357],
        "curation_note": (
            "Corrected the evidence page to the page containing the 1,983-device "
            "and 87-percent figures."
        ),
    },
    "CS-002": {
        "expected_pages": [34],
        "category": "simple_factual",
        "requires_multi_section": False,
        "curation_note": (
            "Removed a redundant page from a separate expanded list; page 34 "
            "contains the exact four-objective reference."
        ),
    },
    "CS-004": {
        "expected_pages": [211],
        "category": "method_detail",
        "requires_multi_section": False,
        "curation_note": (
            "Removed the background page; the complete selection and hybrid "
            "hardening approach appears on page 211."
        ),
    },
    "CS-005": {
        "reference_answer": (
            "PG&E deploys: (1) EPSS, which rapidly de-energizes lines when a fault "
            "is detected; (2) DCD, which detects and isolates high-impedance faults "
            "that EPSS alone may not catch; (3) Sensitive Ground Fault settings, "
            "revised in 2024 to detect a 5-ampere fault within 5 seconds; and (4) "
            "SmartMeter Partial Voltage Alerts for low-voltage conditions."
        ),
        "curation_note": (
            "Removed ComAPS because the question is scoped to distribution lines "
            "and the source identifies ComAPS as a transmission technology."
        ),
    },
    "MH-002": {
        "question": (
            "How did PG&E's reported PSPS customer impact change from 2019 to "
            "2023, and what measures does it identify for reducing future PSPS impacts?"
        ),
        "reference_answer": (
            "PG&E reports that PSPS customer impact peaked in 2019 with 2,036,019 "
            "customers affected across 8 events and 1,842 circuits, and fell to "
            "5,098 customers across 2 events and 27 circuits in 2023. The WMP "
            "identifies continued use of SCADA devices, improved risk-model "
            "sensitivity to weather, vegetation, and fuel conditions, undergrounding, "
            "sectionalizing devices for more targeted de-energization, and fixed power "
            "solutions as measures intended to "
            "reduce future PSPS impacts. The cited passages do not establish that "
            "each measure caused the historical decline."
        ),
        "curation_note": (
            "Removed a causal overclaim and distinguished the observed historical "
            "decline from measures identified for future impact reduction."
        ),
    },
    "IF-002": {
        "question": (
            "How does PG&E calculate distribution probability of ignition for "
            "asset- and location-based models, and how is wildfire risk then formed?"
        ),
        "reference_answer": (
            "For an asset, PG&E calculates probability of ignition as the asset's "
            "probability of ignition given an outage multiplied by its probability "
            "of outage: p(i) = p(i|o) x p(o). It uses the analogous product for "
            "location/pixel-based Contact From Object models. PG&E then combines "
            "probability of ignition with consequence to produce wildfire risk."
        ),
        "expected_pages": [90, 102],
        "category": "method_detail",
        "requires_image": False,
        "requires_multi_section": True,
        "curation_note": (
            "Replaced an image-only, mispaged figure target with the same method's "
            "text-supported equations and risk-composition description."
        ),
    },
    "IF-003": {
        "expected_pages": [97],
        "requires_image": False,
        "curation_note": (
            "Removed a printed-page number mistakenly used as a PDF evidence page."
        ),
    },
    "NEG-001": {
        "reference_answer": (
            "The PG&E WMP contains limited comparisons with Southern California "
            "Edison, but it does not provide SCE's undergrounding cost per mile. "
            "The answer should decline that specific request rather than substitute "
            "PG&E's cost."
        ),
        "curation_note": (
            "Tightened the control reference to acknowledge nearby SCE material "
            "while preserving the absent-fact label."
        ),
    },
    "NEG-002": {
        "reference_answer": (
            "The WMP provides projected expenditures for 2026-2028 and some "
            "longer-horizon planning information, but it cannot provide actual "
            "fiscal-year 2030 WMP expenditures."
        ),
        "curation_note": (
            "Tightened the temporal control: projections or targets are not actual "
            "fiscal-year 2030 expenditure data."
        ),
    },
    "NEG-003": {
        "reference_answer": (
            "The WMP contains generic enterprise-system, access-management, and "
            "all-hazards material, but it does not describe cybersecurity controls "
            "for PG&E's customer billing system."
        ),
        "curation_note": (
            "Tightened the scope control to distinguish nearby IT material from the "
            "requested billing-system cybersecurity controls."
        ),
    },
    "NEG-004": {
        "reference_answer": (
            "No. The WMP says PG&E will strive to get to zero ignitions, but it "
            "also plans containment and rapid-response measures because an "
            "ignition may still occur. Its stated statutory and plan goal is to "
            "minimize catastrophic-wildfire risk and reduce ignitions, not to "
            "guarantee zero equipment-caused ignitions."
        ),
        "expected_pages": [34, 41],
        "curation_note": (
            "Added the statutory-goal page and clarified that aspirational zero "
            "ignitions is not a guarantee."
        ),
    },
    "wmp_q35": {
        "expected_pages": [392],
        "category": "method_detail",
        "requires_multi_section": False,
        "curation_note": (
            "Removed unrelated pages; the cadence and required-update facts both "
            "appear on PDF page 392."
        ),
    },
    "wmp_q9": {
        "reference_answer": (
            "VM-14, Transmission Hazard Patrol (Second Patrol, Tree Mortality), "
            "is the vegetation management activity specifically designed to address "
            "tree mortality on transmission lines."
        ),
        "curation_note": (
            "Corrected the activity ID from VM-13 (routine transmission ground) "
            "to VM-14 (the tree-mortality patrol)."
        ),
    },
    "wmp_q14": {
        "question": (
            "According to the Risk Analysis Framework section, what factors must an "
            "electrical corporation evaluate at minimum when quantifying risk impact?"
        ),
        "reference_answer": (
            "The eight minimum factors are: Equipment/Assets; Topography; Weather; "
            "Vegetation; Climate Change; Social Vulnerability; Physical Vulnerability; "
            "and Access Capacities."
        ),
        "curation_note": (
            "Corrected the inherited five-factor premise to the eight factors listed "
            "by the source."
        ),
    },
    "wmp_q37": {
        "question": (
            "What qualifications does PG&E list for Troublemen in risk-event "
            "inspection, and how does it separately calculate distribution ignition "
            "rates in HFTD/HFRA?"
        ),
        "expected_pages": [309, 379],
        "reference_answer": (
            "Troublemen are QEWs, and the WMP says their work is important to safe "
            "equipment operation and wildfire-risk mitigation, although they have "
            "no wildfire- or PSPS-specific certification beyond QEW. Separately, "
            "PG&E calculates the HFTD/HFRA distribution ignition rate from "
            "CPUC-reportable ignitions caused by equipment failure or overload and "
            "utility operation, divided by HFTD/HFRA failures per year. The cited "
            "passages do not quantify a causal effect of Troublemen qualifications "
            "on the rate."
        ),
        "curation_note": (
            "Removed an unrelated disaster-billing page and bounded the synthesis "
            "so it does not claim a quantified causal relationship."
        ),
    },
    "wmp_q39": {
        "question": (
            "What does the WMP report about (a) combined covered-conductor/EPSS/DCD "
            "effectiveness, (b) Tribal vegetation-management partnerships, and "
            "(c) weather-station monitoring and escalation?"
        ),
        "reference_answer": (
            "PG&E estimates covered conductor combined with EPSS and DCD is "
            "approximately 79% effective at reducing ignition risk. Tribal partnerships "
            "support fire/fuel-crew capacity and roadside treatments that improve "
            "ingress and egress while reducing risk to and from PG&E assets. Separately, "
            "an external vendor collects weather-station data every 10 minutes, runs "
            "automated health checks, and escalates verified anomalies to PG&E's "
            "Enterprise Network Operations Center for a local technician to resolve."
        ),
        "curation_note": (
            "Replaced an integrated causal framing with three explicitly source-backed facts."
        ),
    },
    "wmp_q40": {
        "question": (
            "How does PG&E's quarterly compliance reporting differ between defined "
            "WMP targets and additional wildfire-related activities described in "
            "the plan?"
        ),
        "reference_answer": (
            "PG&E will use all defined targets for quarterly compliance reporting "
            "through QDR, QN, and ARC. It will not report additional wildfire-related "
            "activities through those mechanisms when they are descriptions of plans "
            "rather than defined targets, and their timing and scope may change. The "
            "page does not say those activities are exempt from all other monitoring "
            "or work-order controls."
        ),
        "expected_pages": [505],
        "category": "method_detail",
        "requires_multi_section": False,
        "curation_note": (
            "Removed unsupported implications and unrelated contents/work-order pages."
        ),
    },
    "wmp_q41": {
        "reference_answer": (
            "The WFC Model produces consequence values for ignition locations from "
            "simulated fire outcomes using detailed fuels, weather, and topography "
            "data. Within WDRM, WFC/CoRE results are combined with likelihood and "
            "ignition-probability results at asset and 100 m by 100 m pixel locations. "
            "PG&E then sums intersecting pixel risk and assigned asset risk along a "
            "circuit segment to obtain aggregated circuit-segment risk. Thus WFC "
            "consequence results are inputs to risk that is later aggregated; "
            "aggregated circuit risk does not feed into WFC."
        ),
        "expected_pages": [54, 101],
        "curation_note": (
            "Corrected the direction of the modeling flow and removed an unrelated "
            "reporting page."
        ),
    },
    "wmp_q43": {
        "question": (
            "What reliability did PG&E report for Remote Grid customers in 2023 "
            "and 2024, and what continuation and system-integration updates does it describe?"
        ),
        "reference_answer": (
            "PG&E reports overall Remote Grid customer reliability of 99.7% in "
            "2023 and 99.83% in 2024. These customers are no longer subject to "
            "outages caused by weather, tree strikes, or impacts to the former "
            "overhead distribution circuit. PG&E plans to continue the program in "
            "its current form and has integrated Remote Grid monitoring with SAP, "
            "EDGIS, the Outage Management Tool, and the Hazard Awareness and Warning "
            "Center to improve response, restoration, and asset management."
        ),
        "expected_pages": [238],
        "category": "method_detail",
        "requires_multi_section": False,
        "curation_note": (
            "Replaced an inferential plan-scope synthesis with the source's direct "
            "reliability, continuation, and integration statements."
        ),
    },
    "wmp_q44": {
        "question": (
            "How does PG&E's PRC 4292 pole-clearing approach relate to its "
            "transmission-switch failure-rate monitoring and remediation processes?"
        ),
        "reference_answer": (
            "PRC 4292 pole clearing removes flammable vegetation around applicable "
            "poles or towers supporting equipment such as switches, fuses, "
            "transformers, arresters, junctions, and dead ends. This is a "
            "complementary risk-control activity, but it is not counted as a "
            "vegetation component of the transmission-switch failure-rate metric. "
            "PG&E's switch failure-rate calculation includes outages attributed to "
            "equipment failure, non-lightning weather, contamination, and "
            "unknown/other causes and explicitly excludes vegetation and third-party "
            "damage. Switch remediation is driven by inspection findings under the "
            "cited maintenance procedures."
        ),
        "expected_pages": [325, 408],
        "curation_note": (
            "Corrected the false claim that vegetation outages enter the switch "
            "failure-rate calculation and removed an unrelated inspection page."
        ),
    },
    "wmp_q45": {
        "question": (
            "How does PG&E use LiDAR-based pole-loading results to prioritize risk, "
            "and what does the WMP separately report for System Hardening Target GH-12?"
        ),
        "reference_answer": (
            "PG&E uses LiDAR measurements as inputs to pole-loading calculations. "
            "Overloaded poles have a higher probability of failure, and PG&E compares "
            "their locations with wildfire ignition-consequence profiles to aid "
            "prioritization. Separately, PG&E reports approximately 1,230 miles of "
            "hardened overhead conductor installed since 2018 under GH-12, including "
            "about 145 miles in 2023 and 108 miles in 2024, and expects this activity "
            "to improve reliability. The cited text does not state that the LiDAR "
            "analysis selected those particular GH-12 miles."
        ),
        "expected_pages": [226, 281],
        "curation_note": (
            "Removed an unsupported causal link and an unrelated vegetation-work-order page."
        ),
    },
    "wmp_q46": {
        "question": (
            "How does the covered-conductor program relate to GH-12, and what does "
            "the WMP say about current and completed effectiveness evaluations?"
        ),
        "reference_answer": (
            "PG&E reports approximately 1,230 miles of hardened overhead conductor "
            "installed since 2018 under GH-12, including about 145 miles in 2023 and "
            "108 miles in 2024. It expects improved reliability and says it is working "
            "to quantify reliability improvements on covered-conductor and undergrounded "
            "segments. GH-02 (Evaluate Covered Conductor Effectiveness) and GH-03 "
            "(Evaluate and Implement Covered Conductor Effectiveness Impact on "
            "Inspections and Maintenance Standard) are listed as completed activities, "
            "with completion years 2025 and 2023 respectively; they are not future "
            "planned activities."
        ),
        "expected_pages": [226, 588],
        "curation_note": (
            "Corrected GH-02/GH-03 from planned to completed and removed an unrelated "
            "partnership page."
        ),
    },
    "wmp_q47": {
        "question": (
            "How are Resource Conservation District and Tribal-government vegetation "
            "partnerships similar in compliance reporting, and how do their operational "
            "emphases differ?"
        ),
        "reference_answer": (
            "Both partnership types are described as non-compliance-driven "
            "fuels-treatment work. Page 505 says additional activities that are not "
            "defined targets are not reported through QDR, QN, or ARC, so the cited "
            "passages do not establish different quarterly reporting treatment. "
            "Operationally, Tribal collaborations emphasize building fire/fuel-crew "
            "capacity and roadside projects that improve ingress and egress, while RCD "
            "grants fund specific fuels-treatment and roadside-brushing projects, "
            "including the anticipated 70-acre Spanish Flats/Traverse Creek treatment "
            "and two Nevada County roadside miles."
        ),
        "expected_pages": [420, 421, 431, 505],
        "curation_note": (
            "Corrected the unsupported claim of different reporting treatment and "
            "added the page containing the RCD table entry."
        ),
    },
    "wmp_q49": {
        "question": (
            "What does PG&E report about hardened-overhead-conductor mileage and "
            "reliability, and what does its illustrative risk-reduction calculation show?"
        ),
        "reference_answer": (
            "PG&E reports approximately 1,230 miles of hardened overhead conductor "
            "installed since 2018 under GH-12, including about 145 miles in 2023 and "
            "108 miles in 2024, and says the activity is expected to improve reliability. "
            "Separately, Table PG&E-6.2.1.2-2 illustrates calculation mechanics: "
            "applying an illustrative 98% effectiveness to 25 units of targeted WDRM "
            "risk exposure yields 24.5 units of workplan wildfire-risk reduction. The "
            "preceding text says these example values do not reflect specific commitments "
            "and do not necessarily align with WMP targets; they are not a measured 98% "
            "outcome for the installed GH-12 miles."
        ),
        "expected_pages": [187, 188, 226],
        "curation_note": (
            "Separated reported GH-12 mileage from an illustrative calculation, added "
            "the example disclaimer page, and removed an unrelated inspection page."
        ),
    },
    "wmp_q50": {
        "question": (
            "What is PG&E's total projected WMP expenditure for 2026-2028, in "
            "millions of dollars?"
        ),
        "answerable": True,
        "reference_answer": (
            "Projected WMP expenditures total $18,874.862 million for 2026-2028 "
            "($5,513.330 million in 2026, $6,449.108 million in 2027, and "
            "$6,912.424 million in 2028). PG&E notes that decisions in the cited "
            "cost-recovery proceedings may lead to revision of the WMP."
        ),
        "expected_pages": [53],
        "category": "table_based",
        "requires_table": True,
        "curation_note": (
            "Relabeled from unanswerable and corrected to the PDF page containing "
            "Table 3-3; its three annual figures deterministically answer the question."
        ),
    },
    "wmp_q51": {
        "question": (
            "Does the WMP identify the programming language used for FPI 5.0, and "
            "which model and geospatial frameworks does it name?"
        ),
        "answerable": True,
        "reference_answer": (
            "The WMP does not identify a programming language. It says FPI 5.0 "
            "uses a multiclass balanced random-forest model based on decision trees "
            "and aggregates fuel/topography features to 0.7 km2 hexagons using "
            "Uber's open-source H3 framework."
        ),
        "expected_pages": [496],
        "category": "method_detail",
        "curation_note": (
            "Relabeled from wholly unanswerable: the language is absent, but the "
            "model and geospatial frameworks are explicitly described on page 496."
        ),
    },
    "wmp_q52": {
        "reference_answer": (
            "The WMP describes forecast cadence, simulations, and forecast horizon, "
            "but it does not report the wall-clock runtime of one physics-based "
            "dynamic-weather-model iteration on current hardware."
        ),
        "curation_note": (
            "Tightened the runtime control to acknowledge operational cadence without "
            "mistaking it for wall-clock compute time."
        ),
    },
    "wmp_q54": {
        "reference_answer": (
            "The WMP describes qualitative benchmarking and collaboration with SCE "
            "and SDG&E, but it does not provide the requested quantitative comparison "
            "of their risk-assessment methodologies."
        ),
        "curation_note": (
            "Tightened the comparison control to acknowledge qualitative cross-utility "
            "material while preserving the missing quantitative comparison."
        ),
    },
    "wmp_q56": {
        "question": (
            "What survey-based evaluation of PSPS communications does PG&E report, "
            "and does the WMP provide numerical survey results?"
        ),
        "answerable": True,
        "reference_answer": (
            "PG&E reports annual PSPS education/outreach surveys, pre- and "
            "post-season surveys used as a KPI for AFN preparedness and resource "
            "awareness, post-event surveys of impacted customers and community-based "
            "organizations, and CRC-attendee surveys. It says feedback is used to "
            "identify improvements and points to AFN quarterly progress reports, but "
            "the WMP pages do not provide detailed numerical survey results. These "
            "passages document survey-based evaluation, not a separately identified "
            "formal human-factors study."
        ),
        "expected_pages": [532, 541, 550],
        "category": "cross_section_synthesis",
        "requires_multi_section": True,
        "curation_note": (
            "Relabeled from unanswerable and narrowed from a formal human-factors-study "
            "claim to the survey-based evaluation actually described by the source."
        ),
    },
    "wmp_q58": {
        "reference_answer": (
            "The WMP notes that WRF is used internationally and describes some "
            "collaboration outside the three large California utilities, but it does "
            "not explain how PG&E's mitigation strategy should be adapted for "
            "international utility contexts."
        ),
        "curation_note": (
            "Tightened the international control to acknowledge nearby global-use and "
            "collaboration statements without treating them as an adaptation method."
        ),
    },
    "wmp_q64": {
        "question": (
            "What open-source license or proprietary licensing agreement governs "
            "PG&E's use of the fire danger rating methodologies developed by the "
            "National Wildfire Coordinating Group?"
        ),
        "reference_answer": (
            "The WMP mentions fire-danger-rating courses offered by the National "
            "Wildfire Coordinating Group and use of the National Fire Danger Rating "
            "System, but it gives no open-source or proprietary licensing agreement."
        ),
        "curation_note": (
            "Corrected 'Center' to the source's 'Group' and tightened the licensing "
            "control reference; the requested license remains absent."
        ),
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalise_golden(item: dict[str, Any]) -> dict[str, Any]:
    # The source has no explicit answerability flag.  Four NEG items have no
    # supporting pages and require a refusal.  NEG-004 is intentionally
    # nuanced: the document supports the substantive answer "No" on page 34,
    # so treating every ``NEG-*`` item as unanswerable would mis-score it.
    expected_pages = item.get("expected_page_numbers", [])
    answerable = bool(expected_pages)
    return {
        "qid": item["id"],
        "question": item["question"],
        "reference_answer": item["expected_answer"],
        "answerable": answerable,
        "category": item["category"],
        "difficulty": item.get("difficulty", "unspecified"),
        "expected_pages": expected_pages,
        "expected_sections": item.get("expected_source_sections", []),
        "requires_table": bool(item.get("requires_table", False)),
        "requires_image": bool(item.get("requires_image", False)),
        "requires_multi_section": bool(item.get("requires_multi_section", False)),
        "corpus": "PGE",
        "source_set": "trial1_golden_v3",
    }


def _normalise_harmonized(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "qid": item["id"],
        "question": item["question"],
        "reference_answer": item["reference_answer"],
        "answerable": bool(item["answerable"]),
        "category": item["category"],
        "difficulty": item.get("difficulty", "unspecified"),
        "expected_pages": item.get("expected_pages", []),
        "expected_sections": ([item["expected_source"]]
                              if item.get("expected_source") else []),
        "requires_table": bool(item.get("requires_table", False)),
        "requires_image": bool(item.get("requires_image", False)),
        "requires_multi_section": item["category"] in {
            "cross_section_synthesis", "multi_hop"
        },
        "corpus": "PGE",
        "source_set": "harmonized_wmp",
    }


def build(golden_path: Path, harmonized_path: Path) -> dict[str, Any]:
    golden = [_normalise_golden(q) for q in _load(golden_path)["questions"]]
    harmonized = [
        _normalise_harmonized(q) for q in _load(harmonized_path)["questions"]
    ]
    questions = []
    for question in golden + harmonized:
        if question["qid"] in EXCLUDED_DUPLICATES:
            continue
        if question["qid"] in EXCLUDED_UNSUPPORTED_SYNTHESIS:
            continue
        correction = ANNOTATION_CORRECTIONS.get(question["qid"])
        if correction:
            question = {**question, **correction}
        questions.append(question)
    qids = [q["qid"] for q in questions]
    if len(questions) != 93:
        raise ValueError(f"expected 93 post-audit questions, found {len(questions)}")
    if len(qids) != len(set(qids)):
        raise ValueError("question IDs are not unique")
    if any(not q["reference_answer"].strip() for q in questions):
        raise ValueError("every question must have a non-empty reference answer")

    return {
        "schema_version": "1.1",
        "benchmark_id": "wmp_okf_pge_93_v2",
        "title": "PG&E WMP OKF Paired Evaluation Benchmark",
        "description": (
            "A deterministic, source-reviewed union of two inherited PG&E WMP "
            "evaluation sets. Three duplicate or contradictory controls and four "
            "unsupported synthetic joins are excluded; labels, questions, references, "
            "and evidence pages are corrected with a versioned audit trail."
        ),
        "corpus": "PGE",
        "source_document": "pge-2026-2028-base-wmp-vol1-r0.pdf",
        "sources": [
            {
                "path": str(golden_path.relative_to(REPO_ROOT)),
                "sha256": _sha256(golden_path),
                "question_count": len(golden),
            },
            {
                "path": str(harmonized_path.relative_to(REPO_ROOT)),
                "sha256": _sha256(harmonized_path),
                "question_count": len(harmonized),
            },
        ],
        "curation": {
            "timing": (
                "Initial corrections preceded paid execution. The v2 semantic "
                "corrections followed an invalidated 609-cell partial generation run "
                "and preceded all automated judging and condition-level answer analysis."
            ),
            "supersedes_benchmark_id": "wmp_okf_pge_97_v1",
            "superseded_benchmark_sha256": (
                "1ea5c2142565d4bde6a5b0395887528295bc1434a65780e7678529ccd8ee3971"
            ),
            "invalidated_partial_run": "results/superseded_gold_v1_partial",
            "excluded_duplicates": EXCLUDED_DUPLICATES,
            "excluded_unsupported_synthesis": EXCLUDED_UNSUPPORTED_SYNTHESIS,
            "annotation_corrections": {
                qid: values["curation_note"]
                for qid, values in ANNOTATION_CORRECTIONS.items()
            },
        },
        "counts": {
            "total": len(questions),
            "answerable": sum(q["answerable"] for q in questions),
            "negative_or_control": sum(not q["answerable"] for q in questions),
            "with_expected_pages": sum(bool(q["expected_pages"]) for q in questions),
        },
        "questions": questions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--harmonized", type=Path, default=DEFAULT_HARMONIZED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build(args.golden.resolve(), args.harmonized.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["counts"], sort_keys=True))
    print(args.output)


if __name__ == "__main__":
    main()
