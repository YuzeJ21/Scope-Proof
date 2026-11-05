import json

import pytest

from scopeproof_core.reporting.exporters import export_html, export_json, export_markdown
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_deferred_exports import accepted_review_state
from tests.apps.test_streamlit_app import new_app, select_saved_review

NOTE = "Constructed rationale <keep as text>\nEvidence reviewed at the recorded head."


def open_acceptance_review(*, accepted: bool = True):
    store = JsonReviewStore(default_local_review_directory())
    state = accepted_review_state()
    if not accepted:
        state = append_resolution(state, ResolutionEvent(
            final_acceptance=False, reviewer="Constructed baseline reviewer",
        ))
    path = store.save(state)
    app = select_saved_review(new_app(), state.review.review_id)
    return app.button(key="reopen_review").click().run(), store, path, state


def open_note_editor(app):
    app = app.button(key="add_final_acceptance_note").click().run()
    assert all(button.disabled for button in app.download_button)
    return app


@pytest.mark.parametrize("accept", [True, False])
def test_optional_rationale_is_only_saved_with_the_explicit_acceptance_event(accept):
    app, store, path, before = open_acceptance_review(accepted=not accept)
    raw = path.read_bytes()
    app = open_note_editor(app)

    assert not app.exception
    assert path.read_bytes() == raw
    assert app.session_state["review_state"] == before
    assert app.button(key="save_review").disabled
    assert all(button.disabled for button in app.download_button)
    assert app.button(key="reopen_review").disabled
    assert not [box for box in app.checkbox if box.key == "replace_unsaved_review_confirmed"]
    action = "record_final_acceptance" if accept else "revoke_final_acceptance"
    assert not app.button(key=action).disabled

    app.text_area(key="final_acceptance_note").set_value(NOTE)
    app = app.button(key=action).click().run()
    assert not app.exception
    saved = store.load(before.review.review_id)
    assert saved.review.final_acceptance is accept
    assert saved.resolution_events[:-1] == before.resolution_events
    event = saved.resolution_events[-1]
    assert event.comment == NOTE
    assert event.reviewer == "Local reviewer"
    assert event.criteria_revision_number == before.criteria_revision.number
    assert app.button(key="add_final_acceptance_note").label == "Add final acceptance note"

    app = select_saved_review(new_app(), before.review.review_id)
    app = app.button(key="reopen_review").click().run()
    assert NOTE in [item.value for item in app.text]
    assert json.loads(export_json(saved))["resolution_events"][-1]["comment"] == NOTE
    assert "Constructed rationale &lt;keep as text&gt;" in export_html(saved)
    assert "Constructed rationale &lt;keep as text&gt;" in export_markdown(saved)


def test_changing_reviewer_clears_acceptance_rationale_without_recording_an_event():
    app, store, _, before = open_acceptance_review()
    app = open_note_editor(app)
    app.text_area(key="final_acceptance_note").set_value(NOTE)
    app = app.text_input(key="decision_reviewer").set_value("Constructed next reviewer").run()

    assert not [area for area in app.text_area if area.key == "final_acceptance_note"]
    assert store.load(before.review.review_id) == before
    app = app.button(key="revoke_final_acceptance").click().run()
    event = store.load(before.review.review_id).resolution_events[-1]
    assert event.reviewer == "Constructed next reviewer"
    assert event.comment == "Reviewer revoked final acceptance"


def test_later_saved_state_cannot_be_replaced_by_an_older_acceptance_note():
    app, store, path, before = open_acceptance_review()
    app = open_note_editor(app)
    external, _ = store.mutate(before.review.review_id, lambda state: append_resolution(
        state, ResolutionEvent(final_acceptance=False, reviewer="Constructed other workbench"),
    ))
    raw = path.read_bytes()

    app = app.run()
    assert app.text_area(key="final_acceptance_note").value == ""
    assert app.button(key="revoke_final_acceptance").disabled
    assert all(button.disabled for button in app.download_button)
    assert path.read_bytes() == raw
    app = app.button(key="clear_final_acceptance_note").click().run()
    assert app.session_state["review_state"] == external
    assert not [area for area in app.text_area if area.key == "final_acceptance_note"]
    assert path.read_bytes() == raw


def test_save_race_keeps_note_pending_without_claiming_the_event_was_saved(monkeypatch):
    app, store, _, before = open_acceptance_review()
    app = open_note_editor(app)
    newer = append_resolution(before, ResolutionEvent(
        final_acceptance=False, reviewer="Constructed other workbench",
    ))
    real_save = JsonReviewStore.save
    injected = False

    def save_after_external_change(self, state, **kwargs):
        nonlocal injected
        if not injected:
            injected = True
            real_save(self, newer)
        return real_save(self, state, **kwargs)

    monkeypatch.setattr(JsonReviewStore, "save", save_after_external_change)
    app.text_area(key="final_acceptance_note").set_value(NOTE)
    app = app.button(key="revoke_final_acceptance").click().run()

    assert injected and store.load(before.review.review_id) == newer
    assert app.session_state["review_state"] == before
    assert app.text_area(key="final_acceptance_note").value == NOTE
    assert any("Your note is still pending" in notice.value for notice in app.error)
    assert not any("revocation appended" in notice.value for notice in app.success)
