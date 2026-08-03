from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PACKAGE_ROOT))

from okf_trial_data.evaluator import (  # noqa: E402
    SCHEMA_VERSION,
    BenchmarkValidationError,
    JudgeRetriesExhausted,
    JudgeValidationError,
    PairingError,
    PairedDifference,
    build_gold_aware_judge_prompt,
    cluster_bootstrap_mean_difference,
    derive_outcomes,
    exact_mcnemar,
    holm_adjust,
    paired_differences,
    parse_judge_response,
    run_strict_judge,
    validate_benchmark,
)


def response(
    *,
    evaluation_id: str = "blind-17",
    disposition: str = "substantive_answer",
    scores: tuple[int, int, int, int] | None = (5, 4, 5, 4),
) -> str:
    values = scores or (None, None, None, None)
    return json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "evaluation_id": evaluation_id,
            "response_disposition": disposition,
            "correctness": values[0],
            "completeness": values[1],
            "groundedness": values[2],
            "citation_quality": values[3],
            "explanation": "The candidate agrees with the independently supplied evidence.",
        }
    )


def test_frozen_benchmark_passes_structural_publication_gate() -> None:
    benchmark_path = Path(__file__).resolve().parents[1] / "data" / "benchmark_questions.json"
    summary = validate_benchmark(json.loads(benchmark_path.read_text()))
    assert summary.benchmark_id == "wmp_okf_pge_93_v2"
    assert (summary.total, summary.answerable, summary.unanswerable) == (93, 79, 14)
    assert len(summary.qids) == len(set(summary.qids))


def test_benchmark_gate_rejects_count_or_page_contract_changes() -> None:
    benchmark_path = Path(__file__).resolve().parents[1] / "data" / "benchmark_questions.json"
    payload = json.loads(benchmark_path.read_text())
    payload["questions"][0]["expected_pages"] = []
    with pytest.raises(BenchmarkValidationError, match="lacks expected pages"):
        validate_benchmark(payload)


def test_parse_positive_and_derive_outcomes() -> None:
    parsed = parse_judge_response(
        response(), expected_evaluation_id="blind-17", answerable=True
    )
    outcomes = derive_outcomes(parsed, answerable=True)
    assert parsed.correctness == 5
    assert outcomes.answer_correctness == 5.0
    assert outcomes.answer_completeness == 4.0
    assert outcomes.negative_refusal_correct is None


def test_positive_refusal_uses_predeclared_floor_not_neutral_imputation() -> None:
    parsed = parse_judge_response(
        response(disposition="refusal", scores=None),
        expected_evaluation_id="blind-17",
        answerable=True,
    )
    outcomes = derive_outcomes(parsed, answerable=True)
    assert outcomes.answer_correctness == 1.0
    assert outcomes.answer_completeness == 1.0
    assert outcomes.groundedness is None


@pytest.mark.parametrize(
    ("disposition", "expected"),
    [("refusal", 1), ("substantive_answer", 0)],
)
def test_negative_scoring_is_separate(disposition: str, expected: int) -> None:
    parsed = parse_judge_response(
        response(disposition=disposition, scores=None),
        expected_evaluation_id="blind-17",
        answerable=False,
    )
    outcomes = derive_outcomes(parsed, answerable=False)
    assert outcomes.answer_correctness is None
    assert outcomes.negative_refusal_correct == expected


@pytest.mark.parametrize(
    "invalid",
    [
        lambda valid: "prose\n" + valid,
        lambda valid: "```json\n" + valid + "\n```",
        lambda valid: valid[:-1] + ', "extra": 1}',
        lambda valid: valid.replace('"correctness": 5', '"correctness": "5"'),
        lambda valid: valid.replace('"correctness": 5', '"correctness": true'),
        lambda valid: valid.replace('"correctness": 5', '"correctness": 6'),
        lambda valid: valid.replace('"correctness": 5', '"correctness": 5, "correctness": 4'),
    ],
)
def test_parser_rejects_coercion_and_ambiguous_json(invalid) -> None:
    with pytest.raises(JudgeValidationError):
        parse_judge_response(
            invalid(response()), expected_evaluation_id="blind-17", answerable=True
        )


def test_parser_rejects_scores_for_negative_question() -> None:
    with pytest.raises(JudgeValidationError, match="scores must be null"):
        parse_judge_response(
            response(), expected_evaluation_id="blind-17", answerable=False
        )


def test_parser_rejects_wrong_blinded_id() -> None:
    with pytest.raises(JudgeValidationError, match="evaluation_id"):
        parse_judge_response(
            response(), expected_evaluation_id="a-different-item", answerable=True
        )


def test_strict_judge_retries_schema_failure_then_succeeds() -> None:
    outputs = iter(["not JSON", response()])
    prompts: list[str] = []

    def fake_call(prompt: str) -> str:
        prompts.append(prompt)
        return next(outputs)

    run = run_strict_judge(
        fake_call,
        "base prompt",
        expected_evaluation_id="blind-17",
        answerable=True,
        max_attempts=3,
    )
    assert len(run.attempts) == 2
    assert run.attempts[0].validation_error is not None
    assert run.attempts[1].validation_error is None
    assert "SCHEMA RETRY" in prompts[1]


def test_strict_judge_exhaustion_preserves_failures_and_does_not_score() -> None:
    with pytest.raises(JudgeRetriesExhausted) as caught:
        run_strict_judge(
            lambda _: "invalid",
            "base prompt",
            expected_evaluation_id="blind-17",
            answerable=True,
            max_attempts=2,
        )
    assert len(caught.value.attempts) == 2
    assert all(item.validation_error for item in caught.value.attempts)


def test_gold_prompt_is_blinded_and_uses_canonical_evidence() -> None:
    prompt = build_gold_aware_judge_prompt(
        evaluation_id="opaque-1",
        question="What is the target?",
        answerable=True,
        reference_answer="The target is 10 miles.",
        gold_evidence=[{"document_sha256": "abc", "page": 10, "text": "10 miles"}],
        system_answer="The target is 10 miles [PGE-00001].",
        resolved_citations=[{"citation": "PGE-00001", "page": 10, "text": "10 miles"}],
    )
    assert "opaque-1" in prompt
    assert "canonical gold evidence" in prompt
    assert "simple_rag" not in prompt
    assert '"page": 10' in prompt


def test_paired_differences_require_exact_raw_okf_pairs() -> None:
    rows = [
        {"pipeline": "simple_rag", "qid": "Q1", "arm": "raw_vector", "score": 2},
        {"pipeline": "simple_rag", "qid": "Q1", "arm": "okf_hybrid", "score": 4},
        {"pipeline": "simple_rag", "qid": "Q2", "arm": "raw_vector", "score": 3},
        {"pipeline": "simple_rag", "qid": "Q2", "arm": "okf_hybrid", "score": 2},
    ]
    result = paired_differences(
        rows,
        metric="score",
        expected_pipelines=["simple_rag"],
        expected_qids=["Q1", "Q2"],
    )
    assert [item.difference for item in result] == [2.0, -1.0]

    with pytest.raises(PairingError, match="observations missing"):
        paired_differences(
            rows[:-1],
            metric="score",
            expected_pipelines=["simple_rag"],
            expected_qids=["Q1", "Q2"],
        )
    with pytest.raises(PairingError, match="unexpected qids"):
        paired_differences(
            rows,
            metric="score",
            expected_pipelines=["simple_rag"],
            expected_qids=["Q1"],
        )


def test_paired_differences_reject_duplicates_and_ear() -> None:
    row = {"pipeline": "simple_rag", "qid": "Q1", "arm": "raw_vector", "score": 2}
    with pytest.raises(PairingError, match="duplicate"):
        paired_differences([row, row], metric="score", expected_pipelines=["simple_rag"])
    with pytest.raises(PairingError, match="withheld"):
        paired_differences(
            [{"pipeline": "ear", "qid": "Q1", "arm": "raw_vector", "score": 2}],
            metric="score",
        )
    with pytest.raises(PairingError, match="no observations"):
        paired_differences([], metric="score")


def test_holm_adjustment_is_monotone_in_ranked_order() -> None:
    adjusted = holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adjusted == pytest.approx({"a": 0.03, "b": 0.06, "c": 0.06})


def test_exact_mcnemar() -> None:
    result = exact_mcnemar([0, 0, 0, 0], [1, 1, 1, 1])
    assert result["okf_only_correct"] == 4
    assert result["raw_only_correct"] == 0
    assert result["p_value"] == pytest.approx(0.125)


def test_cluster_bootstrap_constant_difference_has_point_interval() -> None:
    pairs = [
        PairedDifference("simple_rag", "Q1", 2.0, 3.0, 1.0),
        PairedDifference("self_rag", "Q1", 3.0, 4.0, 1.0),
        PairedDifference("simple_rag", "Q2", 1.0, 2.0, 1.0),
    ]
    result = cluster_bootstrap_mean_difference(pairs, repetitions=100, seed=7)
    assert result["n_question_clusters"] == 2
    assert result["mean_difference"] == pytest.approx(1.0)
    assert result["ci_low"] == pytest.approx(1.0)
    assert result["ci_high"] == pytest.approx(1.0)
