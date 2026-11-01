"""Mixed legacy fields must not replace the event target's applicable outcome."""

import re

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    ResolutionEvent,
    ReviewState,
)
from tests.reporting.test_resolution_audit_exports import audit_text
from tests.resolution_audit_fixture import resolution_audit_state


def _mixed_record(kind: str) -> ReviewState:
    if kind == "review-accepted":
        return append_resolution(new_review_state(build_demo_review()), ResolutionEvent(
            event_id="mixed-final-false-accepted", final_acceptance=False,
            decision=HumanDecision.ACCEPTED, reviewer="Constructed legacy recorder",
        ))
    if kind.startswith("review-manual"):
        state = new_review_state(build_demo_review())
        # Model a schema-valid loaded legacy event, not a new manual-entry transition.
        state.resolution_events = [ResolutionEvent(
            event_id="mixed-final-false-manual", final_acceptance=False,
            decision=HumanDecision.MANUALLY_VERIFIED, claimed_evidence_level=EvidenceLevel.E4,
            runtime_evidence_id="unmatched-recorded-link" if kind.endswith("id") else None,
            reviewer="Constructed legacy claimant", comment="Recorded extra manual claim",
            criteria_revision_number=1,
        )]
        return ReviewState.model_validate(state.model_dump(mode="python"))
    if kind == "criterion-false":
        return append_resolution(new_review_state(build_demo_review()), ResolutionEvent(
            event_id="mixed-criterion-false", criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED, final_acceptance=False,
            reviewer="Constructed criterion recorder",
        ))
    assert kind == "criterion-true"
    return append_resolution(resolution_audit_state(), ResolutionEvent(
        event_id="mixed-criterion-true", criterion_id="AC-01",
        decision=HumanDecision.ACCEPTED, final_acceptance=True,
        reviewer="Constructed criterion recorder", comment="Recorded candidate decision",
    ))


@pytest.mark.parametrize(
    ("kind", "exporter"), [("markdown", export_markdown), ("html", export_html)],
)
@pytest.mark.parametrize(("shape", "outcome", "additional"), [
    ("review-accepted", "final_acceptance=false", "accepted"),
    ("review-manual-none", "final_acceptance=false", "manually_verified"),
    ("review-manual-id", "final_acceptance=false", "manually_verified"),
    ("criterion-false", "change_required", "false"),
    ("criterion-true", "accepted", "true"),
])
def test_mixed_legacy_fields_retain_target_outcome_and_unapplied_context(
    kind, exporter, shape, outcome, additional,
):
    state = _mixed_record(shape)
    before = state.model_dump_json()
    machine_json, machine_csv = export_json(state), export_csv(state)
    assert state.review.final_acceptance is False
    text = audit_text(exporter(state), kind)
    if shape.startswith("review-"):
        assert "Final acceptance" in text
        assert re.search(rf"Recorded outcome:?\s+{re.escape(outcome)}\b", text)
        extra_label = re.escape("Additional decision field (not applied to this target)")
        assert re.search(rf"{extra_label}:?\s+{additional}\b", text)
        assert "Legacy unlinked; re-record at the active head" not in text
        if shape.startswith("review-manual"):
            assert "Claimed evidence level (not applied to this target)" in text
            assert "Runtime evidence link (not applied to this target)" in text
            assert "E4" in text
            if shape.endswith("id"):
                assert "unmatched-recorded-link" in text
            else:
                assert "Not recorded" in text
    else:
        last = text.split("mixed-criterion-", 1)[1]
        assert "AC-01" in last
        extra_label = re.escape("Additional final-acceptance field (not applied to this target)")
        assert re.search(rf"Recorded outcome:?\s+{outcome}\b", last)
        assert re.search(rf"{extra_label}:?\s+{additional}\b", last)
    assert state.model_dump_json() == before
    assert export_json(state) == machine_json
    assert export_csv(state) == machine_csv
