import pytest
from pydantic import ValidationError

from scopeproof_core.reviews.lifecycle import (
    ResolutionEventStatus,
    append_resolution,
    append_runtime_evidence,
    confirm_criteria,
    current_resolutions,
    new_review_state,
    resolution_event_statuses,
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
    RuntimeEvidence,
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


@pytest.mark.parametrize("source_text", ["", "   ", "\t", "\n\r"])
def test_revise_criteria_rejects_blank_requirements_source(source_text: str) -> None:
    state = initial_state()

    with pytest.raises(
        ValidationError, match="requirements source must contain non-whitespace text"
    ):
        revise_criteria(state, state.criteria_revision.criteria, source_text)


def test_revise_criteria_preserves_valid_requirements_source() -> None:
    source_text = "  Export filtered CSV\n"

    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        source_text,
    )

    assert revised.criteria_revision.source_text == source_text


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


def test_resolution_event_statuses_identify_latest_event_for_each_target() -> None:
    events = [
        ResolutionEvent(
            event_id="criterion-old",
            criterion_id="AC-01",
            decision=HumanDecision.REJECTED_FINDING,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="acceptance-old",
            final_acceptance=False,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="criterion-current",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="acceptance-current",
            final_acceptance=True,
            criteria_revision_number=1,
        ),
    ]

    assert resolution_event_statuses(events, active_revision_number=1) == [
        ResolutionEventStatus.SUPERSEDED,
        ResolutionEventStatus.SUPERSEDED,
        ResolutionEventStatus.CURRENT,
        ResolutionEventStatus.CURRENT,
    ]


def test_resolution_event_statuses_separate_prior_revisions() -> None:
    events = [
        ResolutionEvent(
            event_id="revision-1",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="revision-2",
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            criteria_revision_number=2,
        ),
    ]

    assert resolution_event_statuses(events, active_revision_number=2) == [
        ResolutionEventStatus.PRIOR_REVISION,
        ResolutionEventStatus.CURRENT,
    ]


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


def test_runtime_evidence_is_append_only_and_does_not_change_gate() -> None:
    state = initial_state()
    updated = append_runtime_evidence(
        state,
        RuntimeEvidence(
            criterion_id="AC-01",
            artifact_reference="https://example.test/run/1",
            scenario="Export CSV",
            environment="staging",
            result="passed",
            reviewer="QA",
            evidence_level=EvidenceLevel.E3,
        ),
    )

    assert state.bundle is not None and state.bundle.runtime_evidence == []
    assert updated.bundle is not None
    assert updated.bundle.runtime_evidence[0].artifact_reference.endswith("/1")
    assert updated.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
