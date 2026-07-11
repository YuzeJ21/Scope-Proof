from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    confirm_criteria,
    current_resolutions,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    CheckState,
    Criterion,
    EvidenceLevel,
    Finding,
    FindingStatus,
    GateDecision,
    GateVerdict,
    HumanDecision,
    ResolutionEvent,
    Review,
    ReviewBundle,
)


def initial_state():
    review = Review(
        review_id="review-1",
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        criteria_confirmed=True,
    )
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    finding = Finding(
        criterion_id="AC-01",
        status=FindingStatus.EVIDENCE_FOUND,
        evidence_level=EvidenceLevel.E1,
        reason="Candidate found",
        recommended_action="Review evidence",
    )
    bundle = ReviewBundle(
        review=review,
        source_text="Export CSV",
        criteria=[criterion],
        evidence=[],
        findings=[finding],
        gate=GateDecision(verdict=GateVerdict.NEEDS_REVIEW),
    )
    return new_review_state(bundle)


def test_editing_confirmed_criteria_creates_revision_and_invalidates_analysis() -> None:
    state = initial_state()
    revised = revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )

    assert revised.criteria_revision.number == 2
    assert revised.criteria_revision.criteria[0].text == "Export filtered CSV"
    assert revised.review.criteria_confirmed is False
    assert revised.bundle is None
    assert len(revised.analysis_history) == 1


def test_confirmation_keeps_revision_and_unblocks_future_analysis() -> None:
    revised = revise_criteria(
        initial_state(), [Criterion(criterion_id="AC-01", text="Export filtered CSV")], "Updated"
    )

    confirmed = confirm_criteria(revised)

    assert confirmed.criteria_revision.number == 2
    assert confirmed.review.criteria_confirmed is True


def test_resolution_events_preserve_history_and_latest_decision_controls_gate() -> None:
    state = initial_state()
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="event-1",
            criterion_id="AC-01",
            decision=HumanDecision.REJECTED_FINDING,
            comment="Evidence is elsewhere",
        ),
    )
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="event-2",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Reviewed candidate evidence",
        ),
    )

    current = current_resolutions(state.resolution_events)
    assert len(state.resolution_events) == 2
    assert current[0].decision is HumanDecision.ACCEPTED
    assert state.bundle is not None
    assert state.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW


def test_final_acceptance_event_allows_ready_after_criterion_resolution() -> None:
    state = append_resolution(
        initial_state(),
        ResolutionEvent(
            event_id="event-1",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
        ),
    )
    state = append_resolution(
        state,
        ResolutionEvent(event_id="event-2", final_acceptance=True, comment="Release approved"),
    )

    assert state.review.final_acceptance is True
    assert state.bundle is not None
    assert state.bundle.gate.verdict is GateVerdict.READY
