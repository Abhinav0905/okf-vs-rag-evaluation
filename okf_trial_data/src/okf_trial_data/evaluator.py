"""Fail-closed evaluation helpers for the OKF paired trial.

This module is deliberately independent of the legacy ``eval_harness`` judge.
It does not call a model or a network service.  Callers inject a text-in/text-out
judge function, which makes the parsing, retry, pairing, and statistical helpers
unit-testable without paid API calls.

The central rule is that malformed judge output is *missing evaluation data*.
It is never converted to a midpoint or any other score.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import random
from typing import Any, Callable, Iterable, Mapping, Sequence


SCHEMA_VERSION = "okf-trial-judge-v1"
PIPELINES = (
    "simple_rag",
    "reranked_simple",
    "agentic_rag",
    "self_rag",
    "flare",
)
ARMS = ("raw_vector", "okf_hybrid")
SCORE_FIELDS = ("correctness", "completeness", "groundedness", "citation_quality")
_JUDGE_KEYS = frozenset(
    {
        "schema_version",
        "evaluation_id",
        "response_disposition",
        *SCORE_FIELDS,
        "explanation",
    }
)


class JudgeValidationError(ValueError):
    """A judge response violated the predeclared output schema."""


class DuplicateJSONKeyError(JudgeValidationError):
    """A JSON object repeated a key, making its meaning ambiguous."""


class PairingError(ValueError):
    """Paired analysis cannot proceed because observations are incomplete."""


class BenchmarkValidationError(ValueError):
    """The frozen benchmark violates its declared publication schema."""


@dataclass(frozen=True)
class BenchmarkSummary:
    benchmark_id: str
    total: int
    answerable: int
    unanswerable: int
    qids: tuple[str, ...]


@dataclass(frozen=True)
class JudgeAssessment:
    """A schema-valid, blinded assessment of one answer.

    Scores are present only for a substantive answer to an answerable question.
    They are structural ``None`` values for refusals and negative questions.
    The analysis layer, not the judge parser, assigns the predeclared floor score
    to an inappropriate refusal on an answerable question.
    """

    schema_version: str
    evaluation_id: str
    response_disposition: str
    correctness: int | None
    completeness: int | None
    groundedness: int | None
    citation_quality: int | None
    explanation: str


@dataclass(frozen=True)
class DerivedOutcomes:
    """Outcomes separated by gold answerability.

    ``answer_*`` fields are defined only for answerable questions.  An
    inappropriate refusal receives the predeclared floor of 1 for correctness
    and completeness, rather than a parser fallback.  Citation outcomes remain
    not applicable for a refusal.  ``negative_refusal_correct`` is defined only
    for gold-negative questions.
    """

    answer_correctness: float | None
    answer_completeness: float | None
    groundedness: float | None
    citation_quality: float | None
    negative_refusal_correct: int | None


@dataclass(frozen=True)
class JudgeAttempt:
    attempt: int
    raw_response: str
    validation_error: str | None


@dataclass(frozen=True)
class JudgeRun:
    assessment: JudgeAssessment
    attempts: tuple[JudgeAttempt, ...]


class JudgeRetriesExhausted(RuntimeError):
    """All strict judge attempts failed; carries every raw response for audit."""

    def __init__(self, attempts: Sequence[JudgeAttempt]):
        self.attempts = tuple(attempts)
        errors = "; ".join(a.validation_error or "unknown error" for a in attempts)
        super().__init__(f"judge output invalid after {len(attempts)} attempts: {errors}")


@dataclass(frozen=True)
class PairedDifference:
    pipeline: str
    qid: str
    raw_vector: float
    okf_hybrid: float
    difference: float


def validate_benchmark(
    payload: Mapping[str, Any],
    *,
    expected_id: str = "wmp_okf_pge_93_v2",
    expected_total: int = 93,
    expected_answerable: int = 79,
    expected_unanswerable: int = 14,
) -> BenchmarkSummary:
    """Validate the frozen PG&E benchmark before a trial is scheduled.

    The validator checks declared/observed counts, QID uniqueness, condition-
    independent reference fields, corpus isolation, and the page-label contract.
    It is intentionally narrower than JSON Schema so semantic audit decisions
    remain source-reviewed and versioned in the benchmark itself. Human
    validation status is tracked separately.
    """

    if not isinstance(payload, Mapping):
        raise BenchmarkValidationError("benchmark must be a mapping")
    if payload.get("benchmark_id") != expected_id:
        raise BenchmarkValidationError(
            f"benchmark_id must be {expected_id!r}, got {payload.get('benchmark_id')!r}"
        )
    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise BenchmarkValidationError("questions must be a list")
    if len(questions) != expected_total:
        raise BenchmarkValidationError(
            f"expected {expected_total} questions, found {len(questions)}"
        )

    qids: list[str] = []
    answerable_count = 0
    for index, question in enumerate(questions):
        if not isinstance(question, Mapping):
            raise BenchmarkValidationError(f"question {index} must be a mapping")
        qid = question.get("qid")
        if not isinstance(qid, str) or not qid.strip():
            raise BenchmarkValidationError(f"question {index} has an invalid qid")
        qids.append(qid)
        for field in ("question", "reference_answer"):
            value = question.get(field)
            if not isinstance(value, str) or not value.strip():
                raise BenchmarkValidationError(f"{qid} has an invalid {field}")
        if question.get("corpus") != "PGE":
            raise BenchmarkValidationError(f"{qid} is not isolated to corpus PGE")
        answerable = question.get("answerable")
        if type(answerable) is not bool:
            raise BenchmarkValidationError(f"{qid} answerable must be a JSON boolean")
        pages = question.get("expected_pages")
        if not isinstance(pages, list):
            raise BenchmarkValidationError(f"{qid} expected_pages must be a list")
        if any(type(page) is not int or page < 1 for page in pages):
            raise BenchmarkValidationError(f"{qid} has invalid expected page values")
        if len(set(pages)) != len(pages):
            raise BenchmarkValidationError(f"{qid} has duplicate expected pages")
        if answerable:
            answerable_count += 1
            if not pages:
                raise BenchmarkValidationError(f"answerable item {qid} lacks expected pages")
        elif pages:
            raise BenchmarkValidationError(
                f"unanswerable control {qid} must not declare positive evidence pages"
            )

    if len(set(qids)) != len(qids):
        raise BenchmarkValidationError("benchmark contains duplicate qids")
    unanswerable_count = len(questions) - answerable_count
    if answerable_count != expected_answerable or unanswerable_count != expected_unanswerable:
        raise BenchmarkValidationError(
            "observed answerability counts differ from the frozen contract: "
            f"{answerable_count}/{unanswerable_count}"
        )
    declared = payload.get("counts")
    expected_counts = {
        "total": expected_total,
        "answerable": expected_answerable,
        "negative_or_control": expected_unanswerable,
        "with_expected_pages": expected_answerable,
    }
    if not isinstance(declared, Mapping) or any(
        declared.get(key) != value for key, value in expected_counts.items()
    ):
        raise BenchmarkValidationError(
            f"declared counts do not match frozen contract: {expected_counts}"
        )
    return BenchmarkSummary(
        benchmark_id=expected_id,
        total=len(questions),
        answerable=answerable_count,
        unanswerable=unanswerable_count,
        qids=tuple(qids),
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> None:
    raise JudgeValidationError(f"non-finite JSON number is forbidden: {value}")


def _is_score(value: Any) -> bool:
    return type(value) is int and 1 <= value <= 5


def parse_judge_response(
    text: str,
    *,
    expected_evaluation_id: str,
    answerable: bool,
) -> JudgeAssessment:
    """Parse one response using the complete, exact JSON document.

    Markdown fences, prose before/after the object, missing/extra keys, duplicate
    keys, coerced strings, booleans, fractional scores, and out-of-range scores
    are rejected.  This strictness is intentional: a retry may repair formatting,
    while silent coercion can create differential bias between trial arms.
    """

    if not isinstance(text, str) or not text.strip():
        raise JudgeValidationError("judge response is empty or not text")
    try:
        payload = json.loads(
            text.strip(),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except JudgeValidationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise JudgeValidationError(f"response is not one exact JSON document: {exc}") from exc

    if type(payload) is not dict:
        raise JudgeValidationError("top-level JSON value must be an object")
    keys = frozenset(payload)
    if keys != _JUDGE_KEYS:
        missing = sorted(_JUDGE_KEYS - keys)
        extra = sorted(keys - _JUDGE_KEYS)
        raise JudgeValidationError(f"schema keys differ; missing={missing}, extra={extra}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise JudgeValidationError(
            f"schema_version must be {SCHEMA_VERSION!r}, got {payload['schema_version']!r}"
        )
    if payload["evaluation_id"] != expected_evaluation_id:
        raise JudgeValidationError("evaluation_id does not match the blinded item")

    disposition = payload["response_disposition"]
    if disposition not in {"substantive_answer", "refusal"}:
        raise JudgeValidationError(
            "response_disposition must be 'substantive_answer' or 'refusal'"
        )

    scores = [payload[field] for field in SCORE_FIELDS]
    should_score = bool(answerable and disposition == "substantive_answer")
    if should_score:
        invalid = [field for field in SCORE_FIELDS if not _is_score(payload[field])]
        if invalid:
            raise JudgeValidationError(
                f"answerable substantive responses require integer 1-5 scores: {invalid}"
            )
    elif any(value is not None for value in scores):
        raise JudgeValidationError(
            "scores must be null for refusals and gold-negative questions"
        )

    explanation = payload["explanation"]
    if not isinstance(explanation, str) or not explanation.strip():
        raise JudgeValidationError("explanation must be a non-empty string")
    if len(explanation) > 1_000:
        raise JudgeValidationError("explanation exceeds 1,000 characters")

    return JudgeAssessment(
        schema_version=payload["schema_version"],
        evaluation_id=payload["evaluation_id"],
        response_disposition=disposition,
        correctness=payload["correctness"],
        completeness=payload["completeness"],
        groundedness=payload["groundedness"],
        citation_quality=payload["citation_quality"],
        explanation=explanation.strip(),
    )


def derive_outcomes(assessment: JudgeAssessment, *, answerable: bool) -> DerivedOutcomes:
    """Apply the predeclared positive/negative scoring branches."""

    if not answerable:
        return DerivedOutcomes(
            answer_correctness=None,
            answer_completeness=None,
            groundedness=None,
            citation_quality=None,
            negative_refusal_correct=int(assessment.response_disposition == "refusal"),
        )
    if assessment.response_disposition == "refusal":
        return DerivedOutcomes(
            answer_correctness=1.0,
            answer_completeness=1.0,
            groundedness=None,
            citation_quality=None,
            negative_refusal_correct=None,
        )
    return DerivedOutcomes(
        answer_correctness=float(assessment.correctness),
        answer_completeness=float(assessment.completeness),
        groundedness=float(assessment.groundedness),
        citation_quality=float(assessment.citation_quality),
        negative_refusal_correct=None,
    )


def build_gold_aware_judge_prompt(
    *,
    evaluation_id: str,
    question: str,
    answerable: bool,
    reference_answer: str,
    gold_evidence: Sequence[Mapping[str, Any]],
    system_answer: str,
    resolved_citations: Sequence[Mapping[str, Any]],
) -> str:
    """Build a blinded prompt that judges against independent gold evidence.

    The caller must use an opaque ``evaluation_id`` and must not include a system
    or retrieval-arm label in any supplied text.  ``resolved_citations`` contains
    canonical source passages reached by citations in the answer; it is not the
    system's self-selected context presented as ground truth.
    """

    item = {
        "evaluation_id": evaluation_id,
        "question": question,
        "gold_answerability": "answerable" if answerable else "unanswerable",
        "reference_answer": reference_answer,
        "gold_evidence": list(gold_evidence),
        "candidate_answer": system_answer,
        "resolved_candidate_citations": list(resolved_citations),
    }
    schema = {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "response_disposition": "substantive_answer|refusal",
        "correctness": "integer 1-5 or null",
        "completeness": "integer 1-5 or null",
        "groundedness": "integer 1-5 or null",
        "citation_quality": "integer 1-5 or null",
        "explanation": "non-empty string, at most 1000 characters",
    }
    return (
        "You are a blinded evaluator. Judge only against the independent reference "
        "answer and canonical gold evidence below; do not use outside knowledge. "
        "Do not infer the system or retrieval condition. A partial answer with a caveat "
        "is a substantive_answer; a response whose main action is declining because "
        "the corpus lacks support is a refusal.\n\n"
        "For a gold-answerable item with a substantive answer, score each field 1-5: "
        "correctness (factual agreement with gold), completeness (coverage of required "
        "answer facets), groundedness (claims entailed by canonical evidence), and "
        "citation_quality (candidate citations support and locate the claims). Use 1 for "
        "wholly incorrect/absent support and 5 for fully correct/complete/supported. "
        "For a refusal, or for every gold-unanswerable item, set all four scores to null; "
        "the analysis computes refusal outcomes separately.\n\n"
        "Return exactly one JSON object, with no Markdown or surrounding prose, matching:\n"
        f"{json.dumps(schema, ensure_ascii=False, sort_keys=True)}\n\n"
        "ITEM:\n"
        f"{json.dumps(item, ensure_ascii=False, sort_keys=True)}"
    )


def run_strict_judge(
    call: Callable[[str], str],
    prompt: str,
    *,
    expected_evaluation_id: str,
    answerable: bool,
    max_attempts: int = 3,
) -> JudgeRun:
    """Call an injected judge with bounded schema retries.

    ``max_attempts=3`` means one initial attempt plus at most two repairs.  Each
    raw response and validation error is retained.  Exhaustion raises
    :class:`JudgeRetriesExhausted`; callers must persist the failure and leave the
    score missing.  No value is imputed here.
    """

    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    attempts: list[JudgeAttempt] = []
    next_prompt = prompt
    for attempt_number in range(1, max_attempts + 1):
        raw = call(next_prompt)
        try:
            assessment = parse_judge_response(
                raw,
                expected_evaluation_id=expected_evaluation_id,
                answerable=answerable,
            )
        except JudgeValidationError as exc:
            attempts.append(
                JudgeAttempt(
                    attempt=attempt_number,
                    raw_response=raw if isinstance(raw, str) else repr(raw),
                    validation_error=str(exc),
                )
            )
            next_prompt = (
                prompt
                + "\n\nSCHEMA RETRY: The prior response failed deterministic validation: "
                + str(exc)
                + ". Re-evaluate the original item and return exactly one valid JSON object."
            )
            continue
        attempts.append(
            JudgeAttempt(
                attempt=attempt_number,
                raw_response=raw,
                validation_error=None,
            )
        )
        return JudgeRun(assessment=assessment, attempts=tuple(attempts))
    raise JudgeRetriesExhausted(attempts)


def paired_differences(
    rows: Iterable[Mapping[str, Any]],
    *,
    metric: str,
    expected_pipelines: Sequence[str] | None = None,
    expected_qids: Sequence[str] | None = None,
) -> tuple[PairedDifference, ...]:
    """Validate exact raw/OKF pairs and return ``okf_hybrid - raw_vector``.

    Rows require ``pipeline``, ``qid``, ``arm``, and ``metric``.  Duplicate rows,
    withheld-pipeline rows, unknown arms/pipelines, missing/non-finite metrics, or an incomplete
    pair raise :class:`PairingError`.  Consequently, listwise deletion cannot
    happen silently.
    """

    configured_pipelines = tuple(PIPELINES if expected_pipelines is None else expected_pipelines)
    if len(set(configured_pipelines)) != len(configured_pipelines):
        raise PairingError("expected_pipelines contains duplicates")
    allowed = set(configured_pipelines)
    if "ear" in allowed:
        raise PairingError("a withheld in-house pipeline is excluded from this study")
    unknown_configured = allowed - set(PIPELINES)
    if unknown_configured:
        raise PairingError(f"unknown configured pipelines: {sorted(unknown_configured)}")
    values: dict[tuple[str, str, str], float] = {}
    observed_pipelines: set[str] = set()
    observed_qids: set[str] = set()

    for index, row in enumerate(rows):
        try:
            pipeline = row["pipeline"]
            qid = row["qid"]
            arm = row["arm"]
            value = row[metric]
        except KeyError as exc:
            raise PairingError(f"row {index} is missing required field {exc.args[0]!r}") from exc
        if pipeline == "ear":
            raise PairingError("a withheld in-house pipeline is excluded from this study")
        if pipeline not in allowed:
            raise PairingError(f"unknown or unexpected pipeline: {pipeline!r}")
        if arm not in ARMS:
            raise PairingError(f"unknown arm: {arm!r}")
        if not isinstance(qid, str) or not qid.strip():
            raise PairingError(f"row {index} has an invalid qid")
        if isinstance(value, bool):
            number = float(int(value))
        elif isinstance(value, (int, float)):
            number = float(value)
        else:
            raise PairingError(f"row {index} metric {metric!r} is not numeric")
        if not math.isfinite(number):
            raise PairingError(f"row {index} metric {metric!r} is not finite")
        key = (pipeline, qid, arm)
        if key in values:
            raise PairingError(f"duplicate observation: {key}")
        values[key] = number
        observed_pipelines.add(pipeline)
        observed_qids.add(qid)

    if not values:
        raise PairingError("no observations supplied")
    required_pipelines = tuple(
        sorted(observed_pipelines) if expected_pipelines is None else expected_pipelines
    )
    required_qids = tuple(sorted(observed_qids) if expected_qids is None else expected_qids)
    if len(set(required_qids)) != len(required_qids):
        raise PairingError("expected_qids contains duplicates")
    if expected_qids is not None:
        extra_qids = observed_qids - set(required_qids)
        if extra_qids:
            raise PairingError(f"unexpected qids present: {sorted(extra_qids)}")
    missing: list[tuple[str, str, str]] = []
    pairs: list[PairedDifference] = []
    for pipeline in required_pipelines:
        for qid in required_qids:
            for arm in ARMS:
                if (pipeline, qid, arm) not in values:
                    missing.append((pipeline, qid, arm))
            if not missing or all(m[:2] != (pipeline, qid) for m in missing):
                raw = values[(pipeline, qid, "raw_vector")]
                okf = values[(pipeline, qid, "okf_hybrid")]
                pairs.append(
                    PairedDifference(
                        pipeline=pipeline,
                        qid=qid,
                        raw_vector=raw,
                        okf_hybrid=okf,
                        difference=okf - raw,
                    )
                )
    if missing:
        preview = ", ".join(map(str, missing[:10]))
        suffix = " ..." if len(missing) > 10 else ""
        raise PairingError(f"{len(missing)} observations missing: {preview}{suffix}")
    return tuple(sorted(pairs, key=lambda item: (item.pipeline, item.qid)))


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values, preserving input labels."""

    checked: list[tuple[str, float]] = []
    for label, value in p_values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"p-value for {label!r} is not numeric")
        p = float(value)
        if not math.isfinite(p) or not 0.0 <= p <= 1.0:
            raise ValueError(f"p-value for {label!r} is outside [0, 1]")
        checked.append((label, p))
    checked.sort(key=lambda item: (item[1], item[0]))
    count = len(checked)
    adjusted: dict[str, float] = {}
    running_max = 0.0
    for rank, (label, p) in enumerate(checked):
        candidate = min(1.0, (count - rank) * p)
        running_max = max(running_max, candidate)
        adjusted[label] = running_max
    return {label: adjusted[label] for label in p_values}


def exact_mcnemar(raw: Sequence[int | bool], okf: Sequence[int | bool]) -> dict[str, float | int]:
    """Two-sided exact McNemar test for paired binary outcomes."""

    if len(raw) != len(okf):
        raise ValueError("raw and okf binary sequences must have equal length")
    normalized: list[tuple[int, int]] = []
    for index, (a, b) in enumerate(zip(raw, okf)):
        if a not in (0, 1, False, True) or b not in (0, 1, False, True):
            raise ValueError(f"non-binary outcome at pair {index}")
        normalized.append((int(a), int(b)))
    raw_only = sum(a == 1 and b == 0 for a, b in normalized)
    okf_only = sum(a == 0 and b == 1 for a, b in normalized)
    discordant = raw_only + okf_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(min(raw_only, okf_only) + 1))
        p_value = min(1.0, 2.0 * tail / (2**discordant))
    return {
        "n": len(normalized),
        "raw_only_correct": raw_only,
        "okf_only_correct": okf_only,
        "discordant": discordant,
        "p_value": float(p_value),
    }


def cluster_bootstrap_mean_difference(
    pairs: Sequence[PairedDifference],
    *,
    repetitions: int = 10_000,
    seed: int = 42,
    confidence: float = 0.95,
) -> dict[str, float | int]:
    """Question-cluster bootstrap CI for the mean paired difference.

    Resampling by ``qid`` preserves the five correlated pipeline observations
    when a pooled effect is estimated.  For a single pipeline it reduces to the
    ordinary paired-question bootstrap.
    """

    if not pairs:
        raise ValueError("at least one paired difference is required")
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("repetitions must be a positive integer")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")
    clusters: dict[str, list[float]] = {}
    for pair in pairs:
        if not math.isfinite(pair.difference):
            raise ValueError("paired differences must be finite")
        clusters.setdefault(pair.qid, []).append(pair.difference)
    qids = sorted(clusters)
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(repetitions):
        sampled_values: list[float] = []
        for _ in qids:
            sampled_values.extend(clusters[rng.choice(qids)])
        estimates.append(sum(sampled_values) / len(sampled_values))
    estimates.sort()

    def quantile(probability: float) -> float:
        position = probability * (len(estimates) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return estimates[lower]
        weight = position - lower
        return estimates[lower] * (1.0 - weight) + estimates[upper] * weight

    alpha = 1.0 - confidence
    observed = sum(pair.difference for pair in pairs) / len(pairs)
    return {
        "n_pairs": len(pairs),
        "n_question_clusters": len(qids),
        "mean_difference": float(observed),
        "ci_low": float(quantile(alpha / 2.0)),
        "ci_high": float(quantile(1.0 - alpha / 2.0)),
        "confidence": float(confidence),
        "repetitions": repetitions,
        "seed": seed,
    }
