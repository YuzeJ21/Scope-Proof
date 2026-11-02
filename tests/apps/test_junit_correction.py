"""A source-free mapping editor commits only explicit, current whole-import corrections."""

import pytest

from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_junit_audit import reopen


def select_import(app):
    return app.selectbox(key="junit_correction_target").set_value("constructed-junit-import").run()


def staged(app):
    app = select_import(app)
    app = app.selectbox(key="junit_correction_remove").set_value("AC-02").run()
    app = app.button(key="remove_junit_correction_group").click().run()
    app = app.selectbox(key="junit_correction_criterion").set_value("AC-01").run()
    app = app.multiselect(key="junit_correction_cases").set_value(["suite-0001-case-0002"]).run()
    app = app.button(key="stage_junit_correction_group").click().run()
    app = (
        app.text_input(key="junit_correction_reviewer").set_value("CONSTRUCTED UI correction").run()
    )
    return app.text_area(key="junit_correction_reason").set_value("CONSTRUCTED wrong mapping").run()


def confirmed(app):
    return staged(app).checkbox(key="junit_correction_confirm").check().run()


def test_source_free_editor_has_explicit_target_and_pristine_preview_is_not_pending():
    app, state, store, path = reopen()
    before = path.read_bytes()
    assert app.selectbox(key="junit_correction_target").value is None
    assert app.button(key="save_junit_correction").disabled
    app = select_import(app)
    assert not app.download_button(key="download_json").disabled
    assert app.button(key="save_junit_correction").disabled
    app = confirmed(app)
    assert not app.exception
    assert path.read_bytes() == before
    assert app.download_button(key="download_json").disabled
    assert app.button(key="withdraw_junit_import").disabled
    assert not app.button(key="save_junit_correction").disabled
    app = app.button(key="save_junit_correction").click().run()
    assert not app.exception
    updated = store.load(state.review.review_id)
    assert updated.bundle.junit_evidence_imports == state.bundle.junit_evidence_imports
    assert updated.bundle.gate == state.bundle.gate
    assert len(updated.bundle.junit_import_events) == 1
    assert updated.bundle.junit_import_events[0].action == "mapping_corrected"
    assert [(x.criterion_id, x.test_case_ids) for x in
            updated.bundle.effective_junit_mappings["constructed-junit-import"]] == [
        ("AC-01", ["suite-0001-case-0002"]),
    ]
    assert not app.download_button(key="download_json").disabled
    assert "JUnit mapping correction saved." in [x.value for x in app.success]


def test_changed_mapping_requires_confirmation_and_controls_invalidate_it():
    app, _state, _store, path = reopen()
    app = staged(app)
    before = path.read_bytes()
    assert app.button(key="save_junit_correction").disabled
    app = app.checkbox(key="junit_correction_confirm").check().run()
    assert not app.button(key="save_junit_correction").disabled
    app = app.selectbox(key="junit_correction_criterion").set_value("AC-02").run()
    assert not app.checkbox(key="junit_correction_confirm").value
    assert app.button(key="save_junit_correction").disabled
    assert path.read_bytes() == before


@pytest.mark.parametrize("change", ["external", "deleted", "save-failure"])
def test_queued_correction_preserves_external_bytes_deletion_and_draft(monkeypatch, change):
    app, state, store, path = reopen()
    app = confirmed(app)
    before_memory = app.session_state["review_state"].model_dump_json()
    if change == "external":
        store.mutate(state.review.review_id, lambda current: append_resolution(
            current, ResolutionEvent(criterion_id="AC-02", decision=HumanDecision.CHANGE_REQUIRED),
        ))
    elif change == "deleted":
        path.unlink()  # External deletion of this disposable fixture, not product deletion.
    else:
        def fail(*_args, **_kwargs):
            raise OSError("CONSTRUCTED storage failure")
        monkeypatch.setattr(JsonReviewStore, "_save_unlocked", fail)
    before = path.read_bytes() if path.exists() else None
    app = app.button(key="save_junit_correction").click().run()
    assert not app.exception
    assert (path.read_bytes() if path.exists() else None) == before
    assert app.session_state["review_state"].model_dump_json() == before_memory
    assert app.text_area(key="junit_correction_reason").value == "CONSTRUCTED wrong mapping"
    assert not any("correction saved" in x.value for x in app.success)


def test_context_switch_clears_mapping_attribution_and_confirmation():
    app, _state, _store, path = reopen()
    app = confirmed(app)
    before = path.read_bytes()
    app = app.selectbox(key="selected_criterion").set_value("AC-02").run()
    assert not app.exception
    assert app.selectbox(key="junit_correction_target").value is None
    assert app.text_input(key="junit_correction_reviewer").value == ""
    assert not app.checkbox(key="junit_correction_confirm").value
    assert path.read_bytes() == before


@pytest.mark.parametrize("operation", ["decision", "runtime"])
def test_pending_correction_blocks_other_detail_writes(operation):
    app, _state, _store, path = reopen()
    app = staged(app)
    before = path.read_bytes()
    if operation == "decision":
        app = (
            app.selectbox(key="resolution_decision").set_value(HumanDecision.CHANGE_REQUIRED).run()
        )
        key = "save_resolution"
    else:
        for field in ("runtime_artifact_reference", "runtime_scenario", "runtime_environment",
                      "runtime_result", "runtime_reviewer"):
            app.session_state[field] = "CONSTRUCTED runtime draft"
        app = app.run()
        key = "save_runtime_evidence"
    assert not app.exception
    assert app.button(key=key).disabled
    assert path.read_bytes() == before


def test_other_draft_blocks_mapping_correction_save():
    app, _state, _store, path = reopen()
    app = confirmed(app)
    before = path.read_bytes()
    app = app.text_area(key="resolution_note").set_value("CONSTRUCTED unsaved decision").run()
    assert app.button(key="save_junit_correction").disabled
    assert path.read_bytes() == before
