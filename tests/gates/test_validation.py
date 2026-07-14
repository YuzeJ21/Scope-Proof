import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import (
    validated_review_bundle,
    validated_review_state,
)
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import (
    GateVerdict,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
)


def test_validated_review_bundle_rejects_a_non_deterministic_gate() -> None:
    bundle = build_demo_review()
    bundle.gate = bundle.gate.model_copy(update={"verdict": GateVerdict.READY})

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        validated_review_bundle(bundle)


def test_validated_review_state_rejects_a_non_deterministic_historical_gate() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.analysis_history[0].gate = revised.analysis_history[0].gate.model_copy(
        update={"verdict": GateVerdict.READY}
    )

    with pytest.raises(
        ValueError,
        match="analysis history bundle gate must match deterministic evaluation",
    ):
        validated_review_state(revised)


def test_validated_review_state_rejects_resolutions_without_active_events() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Forged acceptance",
        )
        for criterion in state.bundle.criteria
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="active bundle resolutions must match active resolution events"
    ):
        validated_review_state(state)


def test_validated_review_state_rejects_final_acceptance_without_active_event() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    state.review.final_acceptance = True
    state.bundle.review.final_acceptance = True
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="final acceptance must match active resolution events"
    ):
        validated_review_state(state)


def test_validated_review_state_rejects_active_events_without_analysis() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.resolution_events.append(
        ResolutionEvent(
            final_acceptance=True,
            comment="Forged bundleless acceptance",
            criteria_revision_number=revised.criteria_revision.number,
        )
    )

    with pytest.raises(
        ValueError, match="active resolution events require an active analysis bundle"
    ):
        validated_review_state(revised)


def test_validated_review_state_rejects_duplicate_resolution_event_ids() -> None:
    state = new_review_state(build_demo_review())
    state.resolution_events = [
        ResolutionEvent(
            event_id="duplicate-event",
            final_acceptance=False,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="duplicate-event",
            final_acceptance=False,
            criteria_revision_number=1,
        ),
    ]

    with pytest.raises(ValueError, match="resolution event IDs must be unique"):
        validated_review_state(state)


@pytest.mark.parametrize("revision_number", [0, 2])
def test_validated_review_state_rejects_events_outside_revision_lineage(
    revision_number: int,
) -> None:
    state = new_review_state(build_demo_review())
    state.resolution_events.append(
        ResolutionEvent(
            event_id=f"revision-{revision_number}",
            final_acceptance=False,
            criteria_revision_number=revision_number,
        )
    )

    with pytest.raises(
        ValueError,
        match="resolution event revisions must reference an existing criteria revision",
    ):
        validated_review_state(state)


def test_validated_review_state_preserves_prior_revision_events() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.resolution_events.append(
        ResolutionEvent(
            event_id="prior-acceptance",
            final_acceptance=True,
            criteria_revision_number=1,
        )
    )

    validated = validated_review_state(revised)

    assert validated.resolution_events[0].event_id == "prior-acceptance"
    assert validated.review.final_acceptance is False
