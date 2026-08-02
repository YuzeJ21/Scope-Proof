from datetime import UTC, datetime

import pytest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    CriteriaSourceProvenance,
    Criterion,
    Finding,
    FindingStatus,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    IngestionState,
    Priority,
    Review,
)


def ci_observation_for(check_state: CheckState) -> CIObservation:
    if check_state is CheckState.PASSING:
        return CIObservation(
            state=CheckState.PASSING,
            reason="Fixture",
            total_check_runs=1,
            successful_check_runs=1,
        )
    if check_state is CheckState.FAILING:
        return CIObservation(
            state=CheckState.FAILING,
            reason="Fixture",
            total_check_runs=1,
            failing_check_runs=1,
        )
    if check_state is CheckState.PENDING:
        return CIObservation(
            state=CheckState.PENDING,
            reason="Fixture",
            total_check_runs=1,
            pending_check_runs=1,
        )
    return CIObservation(reason="Fixture")


def valid_provenance() -> CriteriaSourceProvenance:
    return CriteriaSourceProvenance(
        source_uri="https://example.test/requirements",
        source_text_sha256="a" * 64,
        normalized_criteria_sha256="b" * 64,
        confirmed_by="Fixture owner",
        confirmed_at=datetime(2026, 8, 2, tzinfo=UTC),
    )


def gate_case(
    confirmed: bool,
    check_state: CheckState,
    priority: Priority,
    status: FindingStatus,
) -> tuple[Review, Criterion, Finding]:
    review = Review(
        repository="acme/widget",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        check_state=check_state,
        ci_observation=ci_observation_for(check_state),
        criteria_confirmed=confirmed,
        criteria_source_provenance=valid_provenance() if confirmed else None,
        final_acceptance=True,
    )
    criterion = Criterion(criterion_id="AC-01", text="Export CSV", priority=priority)
    finding = Finding(
        criterion_id="AC-01",
        status=status,
        reason="Fixture reason",
        missing_evidence=[] if status is FindingStatus.EVIDENCE_FOUND else ["Required evidence"],
        recommended_action="Review the criterion",
    )
    return review, criterion, finding


@pytest.mark.parametrize(
    ("confirmed", "check_state", "priority", "status", "expected"),
    [
        (
            False,
            CheckState.PASSING,
            Priority.MUST_HAVE,
            FindingStatus.EVIDENCE_FOUND,
            GateVerdict.NEEDS_REVIEW,
        ),
        (
            True,
            CheckState.FAILING,
            Priority.MUST_HAVE,
            FindingStatus.EVIDENCE_FOUND,
            GateVerdict.BLOCKED,
        ),
        (
            True,
            CheckState.PASSING,
            Priority.MUST_HAVE,
            FindingStatus.MISSING,
            GateVerdict.BLOCKED,
        ),
        (
            True,
            CheckState.PASSING,
            Priority.MUST_HAVE,
            FindingStatus.NEEDS_REVIEW,
            GateVerdict.NEEDS_REVIEW,
        ),
        (
            True,
            CheckState.PASSING,
            Priority.SHOULD_HAVE,
            FindingStatus.MISSING,
            GateVerdict.CONDITIONAL,
        ),
    ],
)
def test_gate_truth_table(
    confirmed: bool,
    check_state: CheckState,
    priority: Priority,
    status: FindingStatus,
    expected: GateVerdict,
) -> None:
    review, criterion, finding = gate_case(confirmed, check_state, priority, status)
    assert evaluate_gate(review, [criterion], [finding], []).verdict is expected


def test_ready_requires_final_acceptance() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    review.final_acceptance = False
    resolution = HumanResolution(criterion_id="AC-01", decision=HumanDecision.ACCEPTED)
    decision = evaluate_gate(review, [criterion], [finding], [resolution])
    assert decision.verdict is GateVerdict.NEEDS_REVIEW
    assert "final_acceptance_required" in decision.reason_codes


def test_ready_after_explicit_acceptance() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    resolution = HumanResolution(
        criterion_id="AC-01", decision=HumanDecision.ACCEPTED, comment="Evidence reviewed"
    )
    decision = evaluate_gate(review, [criterion], [finding], [resolution])
    assert decision.verdict is GateVerdict.READY


def test_missing_criteria_source_provenance_fails_closed_before_ready() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    review.criteria_source_provenance = None
    resolution = HumanResolution(
        criterion_id="AC-01", decision=HumanDecision.ACCEPTED, comment="Reviewed"
    )

    decision = evaluate_gate(review, [criterion], [finding], [resolution])

    assert decision.verdict is GateVerdict.NEEDS_REVIEW
    assert decision.reason_codes == ["criteria_source_provenance_missing"]


def test_provenance_missing_reason_follows_confirmation_before_ingestion_reasons() -> None:
    review, criterion, finding = gate_case(
        False, CheckState.PENDING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    review.ingestion_state = IngestionState.PARTIAL

    decision = evaluate_gate(review, [criterion], [finding], [])

    assert decision.reason_codes == [
        "unresolved_criteria",
        "criteria_not_confirmed",
        "criteria_source_provenance_missing",
        "partial_ingestion",
        "checks_not_passing",
    ]


def test_partial_ingestion_forces_needs_review() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    review.ingestion_state = IngestionState.PARTIAL
    resolution = HumanResolution(criterion_id="AC-01", decision=HumanDecision.ACCEPTED)
    decision = evaluate_gate(review, [criterion], [finding], [resolution])
    assert decision.verdict is GateVerdict.NEEDS_REVIEW
    assert "partial_ingestion" in decision.reason_codes


def test_limitation_provenance_defensively_prevents_ready() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    contradictory = review.model_copy(update={"skipped_files": ["src/skipped.py"]})
    resolution = HumanResolution(criterion_id="AC-01", decision=HumanDecision.ACCEPTED)

    decision = evaluate_gate(contradictory, [criterion], [finding], [resolution])

    assert decision.verdict is GateVerdict.NEEDS_REVIEW
    assert "ingestion_limitations_present" in decision.reason_codes


def test_change_required_blocks_even_when_finding_has_evidence() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    resolution = HumanResolution(criterion_id="AC-01", decision=HumanDecision.CHANGE_REQUIRED)
    decision = evaluate_gate(review, [criterion], [finding], [resolution])
    assert decision.verdict is GateVerdict.BLOCKED
    assert decision.blocking_criteria == ["AC-01"]


def test_accepted_exception_is_conditional() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.MISSING
    )
    resolution = HumanResolution(
        criterion_id="AC-01", decision=HumanDecision.ACCEPTED_EXCEPTION, comment="Follow-up ticket"
    )
    decision = evaluate_gate(review, [criterion], [finding], [resolution])
    assert decision.verdict is GateVerdict.CONDITIONAL
    assert decision.resolved_exceptions == ["AC-01"]


def test_legacy_unlinked_manual_verification_requires_reconfirmation() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    resolution = HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment="Historical runtime observation",
        reviewer="QA",
        claimed_evidence_level="E3",
    )

    decision = evaluate_gate(review, [criterion], [finding], [resolution])

    assert decision.verdict is GateVerdict.NEEDS_REVIEW
    assert decision.unresolved_criteria == ["AC-01"]
    assert decision.reason_codes == [
        "unresolved_criteria",
        "runtime_verification_reconfirmation_required",
    ]


def test_linked_manual_verification_retains_ready_gate_meaning() -> None:
    review, criterion, finding = gate_case(
        True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND
    )
    resolution = HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment="Observed at the active head",
        reviewer="QA",
        claimed_evidence_level="E3",
        runtime_evidence_id="runtime-001",
    )

    decision = evaluate_gate(review, [criterion], [finding], [resolution])

    assert decision.verdict is GateVerdict.READY
    assert decision.unresolved_criteria == []
    assert "runtime_verification_reconfirmation_required" not in decision.reason_codes
