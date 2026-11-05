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


@pytest.mark.parametrize("accept", [True, False])
def test_optional_rationale_is_only_saved_with_the_explicit_acceptance_event(accept):
    app, store, path, before = open_acceptance_review(accepted=not accept)
    raw = path.read_bytes()
    app = app.text_area(key="final_acceptance_note").set_value(NOTE).run()

    assert not app.exception
    assert path.read_bytes() == raw
    assert app.session_state["review_state"] == before
    assert app.button(key="save_review").disabled
    assert all(button.disabled for button in app.download_button)
    assert app.button(key="reopen_review").disabled
    action = "record_final_acceptance" if accept else "revoke_final_acceptance"
    assert not app.button(key=action).disabled

    app = app.button(key=action).click().run()
    assert not app.exception
    saved = store.load(before.review.review_id)
    assert saved.review.final_acceptance is accept
    assert saved.resolution_events[:-1] == before.resolution_events
    event = saved.resolution_events[-1]
    assert event.comment == NOTE
    assert event.reviewer == "Local reviewer"
    assert event.criteria_revision_number == before.criteria_revision.number
    assert app.text_area(key="final_acceptance_note").value == ""

    app = select_saved_review(new_app(), before.review.review_id)
    app = app.button(key="reopen_review").click().run()
    assert NOTE in [item.value for item in app.text]
    assert json.loads(export_json(saved))["resolution_events"][-1]["comment"] == NOTE
    assert "Constructed rationale &lt;keep as text&gt;" in export_html(saved)
    assert "Constructed rationale &lt;keep as text&gt;" in export_markdown(saved)


def test_changing_reviewer_clears_acceptance_rationale_without_recording_an_event():
    app, store, _, before = open_acceptance_review()
    app = app.text_area(key="final_acceptance_note").set_value(NOTE).run()
    app = app.text_input(key="decision_reviewer").set_value("Constructed next reviewer").run()

    assert app.text_area(key="final_acceptance_note").value == ""
    assert store.load(before.review.review_id) == before
    app = app.button(key="revoke_final_acceptance").click().run()
    event = store.load(before.review.review_id).resolution_events[-1]
    assert event.reviewer == "Constructed next reviewer"
    assert event.comment == "Reviewer revoked final acceptance"


def test_later_saved_state_cannot_be_replaced_by_an_older_acceptance_note():
    app, store, path, before = open_acceptance_review()
    app = app.text_area(key="final_acceptance_note").set_value(NOTE).run()
    external, _ = store.mutate(before.review.review_id, lambda state: append_resolution(
        state, ResolutionEvent(final_acceptance=False, reviewer="Constructed other workbench"),
    ))
    raw = path.read_bytes()

    app = app.run()
    assert app.text_area(key="final_acceptance_note").value == NOTE
    assert app.button(key="revoke_final_acceptance").disabled
    assert all(button.disabled for button in app.download_button)
    assert path.read_bytes() == raw
    app = app.button(key="clear_final_acceptance_note").click().run()
    assert app.session_state["review_state"] == external
    assert app.text_area(key="final_acceptance_note").value == ""
    assert path.read_bytes() == raw
