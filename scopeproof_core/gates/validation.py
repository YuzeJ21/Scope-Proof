"""Pydantic and deterministic-gate validation for trusted review boundaries."""

from scopeproof_core.gates.evaluator import evaluate_gate
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
    return validated
