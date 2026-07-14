"""Pydantic and deterministic-gate validation for trusted review boundaries."""

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.resolution_events import current_resolutions, final_acceptance
from scopeproof_core.schemas.models import ReviewBundle, ReviewState


def _require_deterministic_gate(bundle: ReviewBundle, location: str) -> None:
    expected_gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )
    if bundle.gate != expected_gate:
        raise ValueError(f"{location} gate must match deterministic evaluation")


def validated_review_bundle(bundle: ReviewBundle) -> ReviewBundle:
    """Return an independently validated bundle with reproducible gate truth."""
    validated = ReviewBundle.model_validate(bundle.model_dump(mode="python"))
    _require_deterministic_gate(validated, "analysis bundle")
    return validated


def validated_review_state(state: ReviewState) -> ReviewState:
    """Return validated lifecycle state with deterministic active and historical gates."""
    validated = ReviewState.model_validate(state.model_dump(mode="python"))
    if validated.bundle is not None:
        _require_deterministic_gate(validated.bundle, "analysis bundle")
    for historical_bundle in validated.analysis_history:
        _require_deterministic_gate(historical_bundle, "analysis history bundle")
    active_revision = validated.criteria_revision.number
    active_events = [
        event
        for event in validated.resolution_events
        if event.criteria_revision_number == active_revision
    ]
    if validated.bundle is None and active_events:
        raise ValueError("active resolution events require an active analysis bundle")
    if validated.bundle is not None:
        expected_resolutions = current_resolutions(
            validated.resolution_events, active_revision
        )
        if validated.bundle.resolutions != expected_resolutions:
            raise ValueError(
                "active bundle resolutions must match active resolution events"
            )
    expected_final_acceptance = final_acceptance(
        validated.resolution_events, active_revision
    )
    if validated.review.final_acceptance != expected_final_acceptance:
        raise ValueError("final acceptance must match active resolution events")
    return validated
