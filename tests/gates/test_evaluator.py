import pytest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.schemas.models import (
    CheckState,
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
        criteria_confirmed=confirmed,
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
