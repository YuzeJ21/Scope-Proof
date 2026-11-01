"""Mixed legacy audit fields must not change the workbench's applicable outcome."""

from datetime import datetime, timedelta, timezone

import pytest

from scopeproof_core.reporting.exporters import export_csv, export_json
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    ResolutionEvent,
    ReviewState,
)
from tests.apps.test_streamlit_app import analyzed_demo, new_app
from tests.resolution_audit_fixture import resolution_audit_state


@pytest.mark.parametrize(("shape", "outcome", "additional_label", "additional"), [
    ("review-accepted", "final_acceptance=false",
     "Additional decision field (not applied to this target)", "accepted"),
    ("review-manual-none", "final_acceptance=false",
     "Additional decision field (not applied to this target)", "manually_verified"),
    ("review-manual-id", "final_acceptance=false",
     "Additional decision field (not applied to this target)", "manually_verified"),
    ("criterion-false", "change_required",
     "Additional final-acceptance field (not applied to this target)", "false"),
    ("criterion-true", "accepted",
     "Additional final-acceptance field (not applied to this target)", "true"),
])
def test_workbench_mixed_legacy_target_controls_outcome(
    shape, outcome, additional_label, additional,
):
    app = analyzed_demo(new_app())
    state = app.session_state["review_state"].model_copy(deep=True)
    if shape.startswith("review-manual"):
        state.resolution_events = [ResolutionEvent(
            event_id="constructed-mixed-manual", final_acceptance=False,
            decision=HumanDecision.MANUALLY_VERIFIED, claimed_evidence_level=EvidenceLevel.E4,
            runtime_evidence_id="unmatched-recorded-id" if shape.endswith("id") else None,
            reviewer="Constructed legacy claimant", comment="Constructed unapplied manual claim",
            criteria_revision_number=1,
        )]
        state = ReviewState.model_validate(state.model_dump(mode="python"))
    else:
        criterion = shape.startswith("criterion")
        state = append_resolution(state, ResolutionEvent(
            event_id="constructed-mixed-outcome", criterion_id="AC-01" if criterion else None,
            decision=(HumanDecision.CHANGE_REQUIRED if shape.endswith("false")
                      else HumanDecision.ACCEPTED),
            final_acceptance=None if criterion else False, reviewer="Constructed legacy recorder",
        ))
        if criterion:
            # A supported saved legacy shape, not a new final-acceptance transition.
            state.resolution_events[-1].final_acceptance = shape == "criterion-true"
            state = ReviewState.model_validate(state.model_dump(mode="python"))
    before = state.model_dump_json()
    machine_before = export_json(state), export_csv(state)
    app.session_state["review_state"] = state
    app.session_state["bundle"] = state.bundle
    app = app.run()
    assert not app.exception
    captions = [item.value for item in app.caption]
    text = [item.value for item in app.text]
    assert "Recorded outcome" in captions
    assert outcome in text
    assert additional_label in captions and additional in text
    if shape.startswith("review-manual"):
        assert "Claimed evidence level (not applied to this target)" in captions
        assert "Runtime evidence link (not applied to this target)" in captions
        assert "Legacy unlinked; re-record at the active head" not in [
            item.value for item in app.warning
        ]
    after = app.session_state["review_state"]
    assert after.model_dump_json() == before
    assert (export_json(after), export_csv(after)) == machine_before


@pytest.mark.parametrize(("recorded_at", "expected"), [
    (datetime(2026, 10, 31, 12, tzinfo=timezone(timedelta(hours=5, minutes=45))),
     "2026-10-31T12:00:00+05:45"),
    (datetime(2026, 10, 31, 12), "2026-10-31T12:00:00 (timezone not recorded)"),
])
def test_workbench_preserves_recorded_time_and_labels_timezone_uncertainty(recorded_at, expected):
    app = analyzed_demo(new_app())
    state = append_resolution(app.session_state["review_state"], ResolutionEvent(
        event_id="constructed-recorded-time", final_acceptance=False,
        reviewer="Constructed clock assertion", timestamp=recorded_at,
    ))
    before = state.model_dump_json()
    app.session_state["review_state"] = state
    app.session_state["bundle"] = state.bundle
    app = app.run()
    assert not app.exception
    assert expected in [item.value for item in app.text]
    assert "Recorded at (as recorded)" in [item.value for item in app.caption]
    assert app.session_state["review_state"].model_dump_json() == before


@pytest.mark.parametrize(("url", "expected"), [
    (None, "Not recorded"), ("", "Empty value recorded"),
])
def test_workbench_discloses_missing_and_explicit_empty_audit_values(url, expected):
    app = analyzed_demo(new_app())
    state = append_resolution(app.session_state["review_state"], ResolutionEvent(
        event_id="constructed-empty-values", final_acceptance=False,
        reviewer="Constructed empty recorder", comment="", evidence_url=url,
    ))
    app.session_state["review_state"] = state
    app.session_state["bundle"] = state.bundle
    app = app.run()
    assert not app.exception
    assert "constructed-empty-values" in [item.value for item in app.code]
    captions = [item.value for item in app.caption]
    text = [item.value for item in app.text]
    for label in ("Reviewer note", "Evidence URL (as recorded)", "Claimed evidence level",
                  "Runtime evidence link", "Criteria revision", "Asserted reviewer"):
        assert label in captions
    assert expected in text and "Empty value recorded" in text


def test_workbench_history_keeps_hostile_metadata_inert():
    app = analyzed_demo(new_app())
    hostile = '<img src="https://example.invalid/audit" onerror="bad()"> **Ready**'
    state = append_resolution(app.session_state["review_state"], ResolutionEvent(
        event_id="constructed-hostile-event", final_acceptance=False,
        reviewer=hostile, comment=hostile, evidence_url="javascript:bad()",
    ))
    app.session_state["review_state"] = state
    app.session_state["bundle"] = state.bundle
    app = app.run()
    assert not app.exception
    assert [item.value for item in app.text].count(hostile) == 2
    assert "javascript:bad()" in [item.value for item in app.text]
    markdown = "\n".join(item.value for item in app.markdown)
    assert hostile not in markdown and "javascript:bad()" not in markdown


def test_workbench_empty_history_is_explicit():
    app = analyzed_demo(new_app())
    assert not app.exception
    assert "No resolution events were recorded for this saved review." in [
        item.value for item in app.caption
    ]


def test_workbench_retains_append_order_and_revision_status_without_timestamp_authority():
    app = analyzed_demo(new_app())
    state = resolution_audit_state()
    before = state.model_dump_json()
    app.session_state["review_state"] = state
    app.session_state["bundle"] = state.bundle
    app = app.run()
    assert not app.exception
    ids = ["r1-old-accept", "r2-old-change", "r2-current-accept", "r2-ac02-accept",
           "r2-ac03-accept", "r2-ac04-accept", "r2-final-true", "r2-final-false"]
    assert [item.value for item in app.code if item.value in ids] == ids
    statuses = [item.value for item in app.text if item.value.startswith(
        ("Current · revision ", "Superseded · revision ", "Prior revision · revision ")
    )]
    assert statuses == [
        "Prior revision · revision 1", "Superseded · revision 2", "Current · revision 2",
        "Current · revision 2", "Current · revision 2", "Current · revision 2",
        "Superseded · revision 2", "Current · revision 2",
    ]
    assert app.session_state["review_state"].model_dump_json() == before
