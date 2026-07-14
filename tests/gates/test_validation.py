import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.validation import (
    validated_review_bundle,
    validated_review_state,
)
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import GateVerdict


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
