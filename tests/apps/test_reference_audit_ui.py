"""Audited source reference actions remain explicit, attributable and non-gating."""

from unittest.mock import patch

import pytest

from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_selected_references import complete_reference, reference_app
from tests.apps.test_source_attachment import load_matching, reopen, saved_reference


def with_reference():
    app = complete_reference(reference_app()).button(key="save_selected_reference").click().run()
    assert not app.exception
    return app


def audit_draft(app, action="Withdraw"):
    app = app.selectbox(key="selected_reference_action").set_value(action).run()
    reference = app.session_state["review_state"].bundle.reviewer_selected_references[-1]
    app = app.selectbox(key="selected_reference_target").set_value(reference.reference_id).run()
    app = app.text_input(key="selected_reference_reviewer").set_value("Audit actor").run()
    return (
        app.text_area(key="selected_reference_reason")
        .set_value("Constructed correction reason")
        .run()
    )


def correct_draft(app, *, line=7):
    app = audit_draft(app, "Correct")
    app = (
        app.selectbox(key="selected_reference_source")
        .set_value("changed_file:src/reference_only.py")
        .run()
    )
    app = app.selectbox(key="selected_reference_line").set_value(line).run()
    return app.text_area(key="selected_reference_rationale").set_value("Revised rationale").run()


def test_correct_same_source_preserves_original_and_shows_linked_event():
    app = with_reference()
    original = app.session_state["review_state"].bundle.reviewer_selected_references[0]
    before = app.session_state["review_state"].bundle.model_dump(mode="json")
    app = correct_draft(app)
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    state = app.session_state["review_state"]
    assert state.bundle.reviewer_selected_references[0] == original
    replacement = state.bundle.reviewer_selected_references[1]
    event = state.bundle.selected_reference_events[0]
    assert event.replacement_reference_id == replacement.reference_id
    assert event.reason == "Constructed correction reason" and event.reviewer == "Audit actor"
    assert replacement.rationale == "Revised rationale"
    assert state.bundle.active_reviewer_selected_reference_ids == [replacement.reference_id]
    after = state.bundle.model_dump(mode="json")
    for field in ("evidence", "findings", "gate", "resolutions", "runtime_evidence"):
        assert after[field] == before[field]
    text = "\n".join(v.value for group in (app.text, app.caption, app.code) for v in group)
    assert "Corrected" in text and "Active" in text
    assert event.event_id in text and replacement.reference_id in text
    assert event.reason in text and event.occurred_at.isoformat() in text
    assert app.selectbox(key="selected_reference_action").value == "Add"
    assert app.session_state["selected_reference_target"] is None
    assert app.session_state["selected_reference_reason"] == ""


def test_correction_can_choose_another_explicit_source_line_after_reopen():
    app, _, snapshot = saved_reference()
    app = correct_draft(load_matching(app, snapshot), line=8)
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert (
        app.session_state["review_state"].bundle.reviewer_selected_references[-1].line_number == 8
    )


def test_withdraw_after_reopen_needs_no_source_and_is_persisted():
    app = with_reference()
    state = app.session_state["review_state"]
    app = audit_draft(reopen(state.review.review_id))
    assert app.session_state["snapshot"] is None
    assert not app.button(key="save_selected_reference").disabled
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    after = app.session_state["review_state"]
    assert after.bundle.reviewer_selected_references == state.bundle.reviewer_selected_references
    assert after.bundle.active_reviewer_selected_reference_ids == []
    assert after.bundle.selected_reference_events[0].action == "withdrawn"
    saved = JsonReviewStore(default_local_review_directory()).load(state.review.review_id)
    assert saved == after
    app = reopen(state.review.review_id)
    assert not app.exception
    assert any("Withdrawn" in v.label for v in app.expander)
    app = app.selectbox(key="selected_reference_action").set_value("Withdraw").run()
    assert app.selectbox(key="selected_reference_target").options == []
    assert app.button(key="save_selected_reference").disabled


@pytest.mark.parametrize("field", ["action", "target", "reviewer", "reason"])
def test_audit_drafts_block_exports_acceptance_and_clear_completely(field):
    app = with_reference()
    if field in ("action", "target"):
        app = app.selectbox(key="selected_reference_action").set_value("Withdraw").run()
        if field == "target":
            ref = app.session_state["review_state"].bundle.reviewer_selected_references[0]
            app = app.selectbox(key="selected_reference_target").set_value(ref.reference_id).run()
    elif field == "reviewer":
        app = app.text_input(key="selected_reference_reviewer").set_value("Draft actor").run()
    else:
        app = app.selectbox(key="selected_reference_action").set_value("Withdraw").run()
        app = app.text_area(key="selected_reference_reason").set_value("Pending reason").run()
    assert not app.exception
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    assert app.button(key="record_final_acceptance").disabled
    app = app.button(key="clear_criterion_detail_drafts").click().run()
    assert not app.exception
    assert app.selectbox(key="selected_reference_action").value == "Add"
    assert app.session_state["selected_reference_target"] is None
    assert app.session_state["selected_reference_reason"] == ""
    assert not app.download_button(key="download_json").disabled


def test_action_and_criterion_changes_clear_previous_target_and_source():
    app = correct_draft(with_reference())
    app = app.selectbox(key="selected_reference_action").set_value("Withdraw").run()
    assert not app.exception
    assert app.selectbox(key="selected_reference_target").value is None
    assert app.session_state["selected_reference_source"] is None
    assert app.session_state["selected_reference_rationale"] == ""
    app = audit_draft(app)
    current = app.selectbox(key="selected_criterion").value
    other = next(v for v in app.selectbox(key="selected_criterion").options if v != current)
    app = app.selectbox(key="selected_criterion").set_value(other).run()
    assert not app.exception
    assert app.selectbox(key="selected_reference_action").value == "Add"
    assert app.session_state["selected_reference_target"] is None
    assert app.session_state["selected_reference_reason"] == ""


def test_correction_requires_source_and_target_actor_reason_are_explicit():
    app = with_reference()
    app = app.selectbox(key="selected_reference_action").set_value("Withdraw").run()
    assert app.selectbox(key="selected_reference_target").value is None
    assert app.button(key="save_selected_reference").disabled
    app = audit_draft(app)
    app = app.text_area(key="selected_reference_reason").set_value("").run()
    assert app.button(key="save_selected_reference").disabled
    app = audit_draft(app)
    app = app.text_input(key="selected_reference_reviewer").set_value("").run()
    assert app.button(key="save_selected_reference").disabled
    state = app.session_state["review_state"]
    app = reopen(state.review.review_id)
    app = app.selectbox(key="selected_reference_action").set_value("Correct").run()
    assert not any(b.key == "save_selected_reference" and not b.disabled for b in app.button)
    assert any("Load matching source" in c.value for c in app.caption)


def test_failed_audit_transition_keeps_pending_inputs():
    app = audit_draft(with_reference())
    before = app.session_state["review_state"]
    with patch(
        "apps.web.selected_references.withdraw_reviewer_selected_reference",
        side_effect=ValueError("Stale"),
    ):
        app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == before
    assert app.text_area(key="selected_reference_reason").value
    assert any("could not be recorded" in v.value for v in app.error)


def test_source_authority_conflict_blocks_withdrawal_without_discarding_draft():
    app = audit_draft(with_reference())
    before = app.session_state["review_state"]
    app.session_state["source_authority_guard"].block(before)
    app = app.run()
    assert not app.exception
    assert app.button(key="save_selected_reference").disabled
    assert app.session_state["review_state"] == before
    assert app.text_area(key="selected_reference_reason").value


def test_external_save_conflict_blocks_audit_and_preserves_saved_record():
    from scopeproof_core.reviews.lifecycle import append_resolution
    from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent

    app = audit_draft(with_reference())
    before = app.session_state["review_state"]
    store = JsonReviewStore(default_local_review_directory())
    changed = append_resolution(
        before,
        ResolutionEvent(
            criterion_id="AC-01",
            reviewer="Concurrent actor",
            decision=HumanDecision.CHANGE_REQUIRED,
            comment="Preserve concurrent decision",
        ),
    )
    store.save(changed)
    path = store.directory / f"{before.review.review_id}.json"
    saved = path.read_bytes()
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert app.session_state["review_save_conflict"]
    assert app.session_state["review_state"] == before
    assert path.read_bytes() == saved
    assert app.button(key="save_selected_reference").disabled
    assert app.text_area(key="selected_reference_reason").value


@pytest.mark.parametrize("action", ["Add", "Correct", "Withdraw"])
def test_final_acceptance_requires_revocation_before_reference_action(action):
    from tests.apps.test_deferred_exports import accepted_review_state

    state = accepted_review_state()
    JsonReviewStore(default_local_review_directory()).save(state)
    app = reopen(state.review.review_id)
    assert app.session_state["review_state"].review.final_acceptance
    before = app.session_state["review_state"]
    app = app.selectbox(key="selected_reference_action").set_value(action).run()
    assert not app.exception
    assert any("Revoke final acceptance" in c.value for c in app.caption)
    assert not any(b.key == "save_selected_reference" and not b.disabled for b in app.button)
    assert app.session_state["review_state"] == before


def test_target_change_clears_staged_source_and_action_inputs_before_queued_save():
    app, _, snapshot = saved_reference()
    app = load_matching(app, snapshot)
    app = (
        app.selectbox(key="selected_reference_source")
        .set_value("changed_file:src/reference_only.py")
        .run()
    )
    app = app.selectbox(key="selected_reference_line").set_value(8).run()
    app = app.text_input(key="selected_reference_reviewer").set_value("Second actor").run()
    app = app.text_area(key="selected_reference_rationale").set_value("Second reference").run()
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    app = correct_draft(app)
    target = app.session_state["review_state"].bundle.reviewer_selected_references[0]
    app.selectbox(key="selected_reference_target").set_value(target.reference_id)
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert app.button(key="save_selected_reference").disabled
    assert app.session_state["selected_reference_source"] is None
    assert app.session_state["selected_reference_line"] is None
    assert app.session_state["selected_reference_reason"] == ""
    assert app.session_state["selected_reference_rationale"] == ""
    assert app.session_state["review_state"].bundle.selected_reference_events == []
    assert any("target changed" in item.value for item in app.info)


def test_reopen_candidate_paths_include_active_references_and_automatic_evidence_only():
    from scopeproof_core.reviews.reference_audit import withdraw_reviewer_selected_reference
    from scopeproof_core.schemas.models import EvidenceSourceScope, ReviewState
    from tests.reviews.test_source_attachment import unchanged_reference_state

    source = reference_app()
    state, snapshot = source.session_state["review_state"], source.session_state["snapshot"]
    state, _ = unchanged_reference_state(
        state, snapshot, ["src/history_only.py", "src/active_reference.py"]
    )
    state = withdraw_reviewer_selected_reference(
        state,
        reference_id=state.bundle.reviewer_selected_references[0].reference_id,
        reviewer="Constructed audit actor",
        reason="Historic context is withdrawn",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
    )
    # Keep independently selected automatic evidence requirements in the reopen form.
    automatic = state.bundle.evidence[0]
    automatic = automatic.model_copy(
        update={
            "source_scope": EvidenceSourceScope.UNCHANGED_CANDIDATE,
            "file_path": "src/automatic_required.py",
        }
    )
    state.bundle.evidence[0] = automatic
    state = ReviewState.model_validate(state.model_dump(mode="python"))
    JsonReviewStore(default_local_review_directory()).save(state)
    app = reopen(state.review.review_id)
    assert not app.exception
    assert app.text_area(key="candidate_paths").value.splitlines() == [
        "src/active_reference.py",
        "src/automatic_required.py",
    ]


def saturated_reference_form():
    import streamlit as st

    from apps.web.selected_references import render_selected_references

    transition = render_selected_references(
        st.session_state["fixture_state"], st.session_state["fixture_source"], "AC-01"
    )
    if transition is not None:
        st.session_state["transition"] = transition


def test_full_retained_history_explains_limit_and_allows_withdrawal():
    from datetime import timedelta

    from streamlit.testing.v1 import AppTest

    from tests.reviews.test_reference_audit import correct
    from tests.reviews.test_reference_audit_safety import prepared

    state, snapshot = prepared()
    payload = correct(state, snapshot).model_dump(mode="python")
    bundle = payload["bundle"]
    first, replacement = bundle["reviewer_selected_references"]
    event = bundle["selected_reference_events"][0]
    bundle["reviewer_selected_references"] = [first] + [
        {
            **replacement,
            "reference_id": f"replacement-{i}",
            "selected_at": event["occurred_at"] + timedelta(seconds=i),
        }
        for i in range(127)
    ]
    refs = bundle["reviewer_selected_references"]
    bundle["selected_reference_events"] = [
        {
            **event,
            "event_id": f"correction-{i}",
            "reference_id": refs[i]["reference_id"],
            "replacement_reference_id": refs[i + 1]["reference_id"],
            "occurred_at": refs[i + 1]["selected_at"],
        }
        for i in range(127)
    ]
    state = type(state).model_validate(payload)
    app = AppTest.from_function(saturated_reference_form)
    app.session_state["fixture_state"] = state
    app.session_state["fixture_source"] = snapshot
    app = app.run()
    assert not app.exception
    assert any("128 of 128 retained" in c.value for c in app.caption)
    assert any("Retained reference history is full" in c.value for c in app.caption)
    assert app.button(key="save_selected_reference").disabled
    app = app.selectbox(key="selected_reference_action").set_value("Correct").run()
    target = state.bundle.active_reviewer_selected_reference_ids[0]
    app = app.selectbox(key="selected_reference_target").set_value(target).run()
    app = (
        app.selectbox(key="selected_reference_source").set_value("changed_file:src/export.py").run()
    )
    app = app.selectbox(key="selected_reference_line").set_value(10).run()
    app = app.text_input(key="selected_reference_reviewer").set_value("Capacity actor").run()
    app = app.text_area(key="selected_reference_reason").set_value("Correction reason").run()
    app = app.text_area(key="selected_reference_rationale").set_value("New rationale").run()
    assert app.button(key="save_selected_reference").disabled
    app = app.selectbox(key="selected_reference_action").set_value("Withdraw").run()
    app = app.selectbox(key="selected_reference_target").set_value(target).run()
    app = app.text_input(key="selected_reference_reviewer").set_value("Capacity actor").run()
    app = app.text_area(key="selected_reference_reason").set_value("Withdraw old context").run()
    assert not app.button(key="save_selected_reference").disabled
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert app.session_state["transition"].bundle.active_reviewer_selected_reference_ids == []
