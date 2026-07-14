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
