"""Source-free, persisted JUnit withdrawal with guarded drafts and failed-save recovery."""

import pytest

from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import new_app, select_saved_review
from tests.junit_audit_fixture import junit_audit_state


def reopen():
    state = junit_audit_state()
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    app = select_saved_review(new_app(), state.review.review_id)
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.session_state["snapshot"] is None
    return app, state, store, path


def stage(app):
    app = app.selectbox(key="junit_withdrawal_target").set_value("constructed-junit-import").run()
    app = app.text_input(key="junit_withdrawal_reviewer").set_value("Constructed UI actor").run()
    return app.text_area(key="junit_withdrawal_reason").set_value("Constructed wrong mapping").run()


def test_reopened_import_requires_explicit_target_attribution_and_whole_import_scope():
    app, state, store, path = reopen()
    before = path.read_bytes()
    assert app.selectbox(key="junit_withdrawal_target").value is None
    assert app.button(key="withdraw_junit_import").disabled
    app = stage(app)
    assert app.download_button(key="download_json").disabled
    assert not app.button(key="withdraw_junit_import").disabled
    assert "AC-01, AC-02" in [item.value for item in app.text]
    assert path.read_bytes() == before
    app = app.button(key="withdraw_junit_import").click().run()
    assert not app.exception
    updated = store.load(state.review.review_id)
    assert updated.bundle.junit_evidence_imports == state.bundle.junit_evidence_imports
    assert updated.bundle.gate == state.bundle.gate
    assert updated.bundle.active_junit_import_ids == []
    assert updated.bundle.junit_import_events[0].reviewer == "Constructed UI actor"
    assert updated.bundle.junit_import_events[0].reason == "Constructed wrong mapping"
    assert "Withdrawn" in [item.value for item in app.text]
    assert "Constructed wrong mapping" in [item.value for item in app.text]
    assert not app.download_button(key="download_json").disabled
    assert app.button(key="withdraw_junit_import").disabled


@pytest.mark.parametrize("change", ["external", "deleted", "save-failure"])
def test_queued_withdrawal_does_not_overwrite_delete_recreate_or_mutate_on_save_failure(
    monkeypatch,
    change,
):
    app, state, store, path = reopen()
    app = stage(app)
    before_memory = app.session_state["review_state"].model_dump_json()
    if change == "external":
        store.mutate(
            state.review.review_id,
            lambda current: append_resolution(
                current,
                ResolutionEvent(
                    criterion_id="AC-02",
                    decision=HumanDecision.CHANGE_REQUIRED,
                    reviewer="Constructed external updater",
                ),
            ),
        )
    elif change == "deleted":
        store.delete(state.review.review_id)
    else:

        def fail_write(*_args, **_kwargs):
            raise OSError("Constructed storage failure before publication")

        monkeypatch.setattr(JsonReviewStore, "_save_unlocked", fail_write)
    before_bytes = path.read_bytes() if path.exists() else None
    app = app.button(key="withdraw_junit_import").click().run()
    assert not app.exception
    assert (path.read_bytes() if path.exists() else None) == before_bytes
    assert app.session_state["review_state"].model_dump_json() == before_memory
    assert not app.session_state["review_state"].bundle.junit_import_events
    assert not any("withdrawal saved" in item.value for item in app.success)


def test_criterion_switch_clears_withdrawal_draft_and_cannot_retarget_it():
    app, _state, _store, path = reopen()
    app = stage(app)
    before = path.read_bytes()
    app = app.selectbox(key="selected_criterion").set_value("AC-02").run()
    assert not app.exception
    assert app.selectbox(key="junit_withdrawal_target").value is None
    assert app.text_input(key="junit_withdrawal_reviewer").value == ""
    assert app.text_area(key="junit_withdrawal_reason").value == ""
    assert app.button(key="withdraw_junit_import").disabled
    assert path.read_bytes() == before


def test_other_pending_detail_input_blocks_withdrawal():
    app, _state, _store, path = reopen()
    app = stage(app)
    before = path.read_bytes()
    app = app.text_area(key="resolution_note").set_value("Constructed unsaved decision").run()
    assert app.button(key="withdraw_junit_import").disabled
    assert path.read_bytes() == before


@pytest.mark.parametrize("operation", ["decision", "runtime"])
def test_pending_withdrawal_blocks_other_detail_writes(operation):
    app, _state, _store, path = reopen()
    app = stage(app)
    before = path.read_bytes()
    if operation == "decision":
        app = (
            app.selectbox(key="resolution_decision").set_value(HumanDecision.CHANGE_REQUIRED).run()
        )
        control = "save_resolution"
    else:
        for key in (
            "runtime_artifact_reference",
            "runtime_scenario",
            "runtime_environment",
            "runtime_result",
            "runtime_reviewer",
        ):
            app.session_state[key] = "Constructed runtime draft"
        app = app.run()
        control = "save_runtime_evidence"
    assert not app.exception
    assert app.button(key=control).disabled
    assert path.read_bytes() == before
