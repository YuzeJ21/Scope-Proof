"""Reopened reviews compare explicit saved baselines without fetching or saving."""

from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.proto.WidgetStates_pb2 import WidgetStates
from streamlit.runtime.state.session_state_proxy import SessionStateProxy

from apps.web.deferred_exports import (
    DeferredExportUnavailable,
    deferred_saved_comparison_export,
)
from scopeproof_core.reporting.exporters import export_comparison_json
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import new_app, scope_key
from tests.saved_comparison_fixture import (
    CURRENT_HEAD,
    CURRENT_REVIEW_ID,
    HISTORY_HEAD,
    PREVIOUS_HEAD,
    PREVIOUS_REVIEW_ID,
    saved_comparison_states,
)


def reopened_comparison_app(
    *, selected_references=False, previous_checks_failing=False, final_acceptance_context=False,
):
    store = JsonReviewStore(default_local_review_directory())
    current, previous = saved_comparison_states(
        selected_references=selected_references, previous_checks_failing=previous_checks_failing,
        final_acceptance_context=final_acceptance_context,
    )
    store.save(current)
    store.save(previous)
    app = new_app()
    app = app.selectbox(key="saved_reopen_review_id").set_value(current.review.review_id).run()
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    return app, store


def apply_other_baseline(app):
    app = (
        app.selectbox(key="saved_comparison_baseline")
        .set_value(f"saved:{PREVIOUS_REVIEW_ID}")
        .run()
    )
    return app.button(key="compare_saved_analysis").click().run()


def comparison_downloads(app):
    return [
        button for button in app.download_button if button.key.startswith("download_comparison_")
    ]


def rendered(app):
    return "\n".join(
        item.value
        for group in (
            app.text,
            app.caption,
            app.markdown,
            app.warning,
            app.info,
        )
        for item in group
    )


def _scope_widget_payload(app, *elements) -> WidgetStates:
    widget_ids = {element.id for element in elements}
    payload = WidgetStates()
    payload.widgets.extend(
        widget for widget in app._tree.get_widget_states().widgets if widget.id in widget_ids
    )
    return payload


def test_saved_comparison_shows_separate_attributed_reference_context_without_mutation():
    app, store = reopened_comparison_app(selected_references=True)
    before = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}
    app = apply_other_baseline(app)
    assert not app.exception
    text = rendered(app)
    assert "Reviewer-selected reference comparison" in text
    assert "Only previous: 1" in text and "Only current: 1" in text
    assert "Constructed previous reference reviewer" in text
    assert "Constructed current reference reviewer" in text
    assert "Constructed previous source context; not execution evidence." in text
    assert "Constructed current source context; not execution evidence." in text
    assert "non-gating static context" in text
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == before


def test_saved_comparison_explains_changed_reasons_under_the_same_blocked_status():
    app, store = reopened_comparison_app(previous_checks_failing=True)
    before = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}
    app = apply_other_baseline(app)

    assert not app.exception
    text = rendered(app)
    assert "Blocked → Blocked" in text
    assert "No longer reported · Required Checks Failing" in text
    assert "Still reported · Blocking Criteria" in text
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == before


@pytest.mark.parametrize("side", ["previous", "current"])
def test_selected_reference_only_mutation_expires_saved_download(side):
    app, store = reopened_comparison_app(selected_references=True)
    app = apply_other_baseline(app)
    selection = app.session_state["saved_comparison_selection"]
    lease = app.session_state["saved_comparison_export_lease"]
    download = deferred_saved_comparison_export(
        selection, export_comparison_json, store=store, lease=lease,
    )
    target = PREVIOUS_REVIEW_ID if side == "previous" else CURRENT_REVIEW_ID

    def change_reference_only(state):
        from scopeproof_core.schemas.models import ReviewState

        reference = state.bundle.reviewer_selected_references[0]
        state.bundle.reviewer_selected_references[0] = reference.model_copy(update={
            "rationale": "Constructed external change to selected context only.",
        })
        return ReviewState.model_validate(state.model_dump(mode="python"))

    store.mutate(target, change_reference_only)
    before = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}
    with pytest.raises(DeferredExportUnavailable):
        download()
    app = app.run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.session_state["saved_comparison_selection"] is None
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == before


def test_reopened_record_requires_explicit_baseline_then_renders_both_saved_identities() -> None:
    app, store = reopened_comparison_app()
    before = {p.name: p.read_bytes() for p in store.directory.glob("*.json")}
    assert app.selectbox(key="saved_comparison_baseline").value is None
    assert comparison_downloads(app) == []
    app = (
        app.selectbox(key="saved_comparison_baseline")
        .set_value(f"saved:{PREVIOUS_REVIEW_ID}")
        .run()
    )
    selector = next(item for item in app.expander if item.label == "Compare saved analyses")
    assert selector.proto.expanded
    assert comparison_downloads(app) == []
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=AssertionError("saved comparison must not fetch GitHub"),
        ),
        patch(
            "subprocess.run",
            side_effect=AssertionError("saved comparison must not execute target code"),
        ),
    ):
        app = app.button(key="compare_saved_analysis").click().run()
    assert not app.exception
    text = rendered(app)
    assert CURRENT_REVIEW_ID in text and PREVIOUS_REVIEW_ID in text
    assert CURRENT_HEAD in text and PREVIOUS_HEAD in text
    assert "src/unrelated.py" in text
    assert len(comparison_downloads(app)) == 2
    assert all(
        button.proto.ignore_rerun and button.proto.deferred_file_id
        for button in comparison_downloads(app)
    )
    assert before == {p.name: p.read_bytes() for p in store.directory.glob("*.json")}


def test_switching_to_history_clears_applied_comparison_until_explicit_action() -> None:
    app, _ = reopened_comparison_app()
    app = apply_other_baseline(app)
    lease = app.session_state["saved_comparison_export_lease"]
    assert lease.selection is not None
    app = app.selectbox(key="saved_comparison_baseline").set_value("history:0").run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert lease.selection is None
    app = app.button(key="compare_saved_analysis").click().run()
    assert not app.exception
    assert HISTORY_HEAD in rendered(app) and CURRENT_HEAD in rendered(app)
    assert len(comparison_downloads(app)) == 2


@pytest.mark.parametrize("change", ["baseline", "delete_baseline", "current"])
def test_changed_saved_record_invalidates_applied_comparison(change: str) -> None:
    app, store = reopened_comparison_app()
    app = apply_other_baseline(app)
    if change == "delete_baseline":
        store.delete(PREVIOUS_REVIEW_ID)
    else:
        review_id = CURRENT_REVIEW_ID if change == "current" else PREVIOUS_REVIEW_ID
        store.mutate(
            review_id,
            lambda state: append_resolution(
                state,
                ResolutionEvent(
                    criterion_id="AC-01",
                    decision=HumanDecision.REJECTED_FINDING,
                    comment="Constructed external update",
                    reviewer="Constructed reviewer",
                ),
            ),
        )
    before = {p.name: p.read_bytes() for p in store.directory.glob("*.json")}
    app = app.run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.session_state["saved_comparison_selection"] is None
    assert before == {p.name: p.read_bytes() for p in store.directory.glob("*.json")}


def test_pending_requirements_disable_saved_comparison_and_invalidate_lease() -> None:
    app, store = reopened_comparison_app()
    app = apply_other_baseline(app)
    lease = app.session_state["saved_comparison_export_lease"]
    before = {p.name: p.read_bytes() for p in store.directory.glob("*.json")}
    app = app.text_area(key="requirements_input").set_value("Pending different requirement").run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.button(key="compare_saved_analysis").disabled
    assert lease.selection is None
    assert before == {p.name: p.read_bytes() for p in store.directory.glob("*.json")}


def test_reopening_same_record_clears_selection_even_when_its_fingerprint_matches() -> None:
    app, _ = reopened_comparison_app()
    app = apply_other_baseline(app)
    lease = app.session_state["saved_comparison_export_lease"]
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.selectbox(key="saved_comparison_baseline").value is None
    assert lease.selection is None


def test_incompatible_saved_baseline_is_explained_without_replacing_current() -> None:
    app, store = reopened_comparison_app()
    previous = store.load(PREVIOUS_REVIEW_ID)
    previous.review.pr_number = 8
    previous.bundle.review.pr_number = 8
    store.save(previous)
    before = {p.name: p.read_bytes() for p in store.directory.glob("*.json")}
    app = apply_other_baseline(app)
    assert not app.exception
    assert comparison_downloads(app) == []
    assert "The recorded pull request numbers differ." in rendered(app)
    assert "Use Compare saved requirements" not in rendered(app)
    assert app.session_state["review_state"].review.review_id == CURRENT_REVIEW_ID
    assert before == {p.name: p.read_bytes() for p in store.directory.glob("*.json")}


def test_deleted_current_and_missing_analysis_cannot_offer_comparison() -> None:
    app, store = reopened_comparison_app()
    app = apply_other_baseline(app)
    store.delete(CURRENT_REVIEW_ID)
    app = app.run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.button(key="compare_saved_analysis").disabled
    state = store.load(PREVIOUS_REVIEW_ID)
    state.bundle = None
    store.save(state)
    app = new_app()
    app = app.selectbox(key="saved_reopen_review_id").set_value(PREVIOUS_REVIEW_ID).run()
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert "requires a saved active analysis" in rendered(app)


@pytest.mark.parametrize("transition", ["reopen", "change_away_and_back"])
def test_old_download_callback_never_reactivates_after_reselecting_same_pair(
    transition: str,
) -> None:
    app, store = reopened_comparison_app()
    app = apply_other_baseline(app)
    lease = app.session_state["saved_comparison_export_lease"]
    old_download = deferred_saved_comparison_export(
        lease.selection, export_comparison_json, store=store, lease=lease,
    )
    if transition == "reopen":
        app = app.button(key="reopen_review").click().run()
    else:
        app = app.selectbox(key="saved_comparison_baseline").set_value("history:0").run()
    app = apply_other_baseline(app)
    assert not app.exception
    assert len(comparison_downloads(app)) == 2
    with pytest.raises(DeferredExportUnavailable):
        old_download()


def test_pending_file_scope_inputs_invalidate_comparison_and_can_be_cleared_read_only() -> None:
    app, store = reopened_comparison_app()
    app = apply_other_baseline(app)
    lease = app.session_state["saved_comparison_export_lease"]
    download = deferred_saved_comparison_export(
        lease.selection, export_comparison_json, store=store, lease=lease,
    )
    before = {p.name: p.read_bytes() for p in store.directory.glob("*.json")}
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    assert len(comparison_downloads(app)) == 2
    assert PREVIOUS_HEAD in download()
    assert app.button(key=scope_key(app, "save_scope_decision")).disabled
    app = app.text_area(key=scope_key(app, "scope_note")).set_value(
        "Unsubmitted scope explanation"
    ).run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert lease.selection is None
    assert app.button(key="compare_saved_analysis").disabled
    with pytest.raises(DeferredExportUnavailable):
        download()
    app = app.button(key=scope_key(app, "clear_saved_comparison_scope_draft")).click().run()
    assert not app.exception
    assert app.text_area(key=scope_key(app, "scope_note")).value == ""
    assert not app.selectbox(key="saved_comparison_baseline").disabled
    app = apply_other_baseline(app)
    assert len(comparison_downloads(app)) == 2
    assert before == {p.name: p.read_bytes() for p in store.directory.glob("*.json")}


def test_submitted_scope_controls_do_not_permanently_block_saved_comparison() -> None:
    app, _ = reopened_comparison_app()
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    app = app.selectbox(key=scope_key(app, "scope_disposition")).set_value(
        "outside_confirmed_criteria"
    ).run()
    app = app.text_area(key=scope_key(app, "scope_note")).set_value(
        "Recorded current-head scope explanation"
    ).run()
    app = app.button(key=scope_key(app, "save_scope_decision")).click().run()
    assert not app.exception
    assert app.session_state["review_state"].bundle.file_scope_decisions[-1].note == (
        "Recorded current-head scope explanation"
    )
    app = app.text_input(key="decision_reviewer").set_value("Constructed next reviewer").run()
    assert "Save or discard the pending file-scope decision" not in rendered(app)
    assert not app.button(key="reopen_review").disabled
    assert not app.selectbox(key="saved_comparison_baseline").disabled
    app = apply_other_baseline(app)
    assert not app.exception
    assert len(comparison_downloads(app)) == 2
    app = app.button(key="load_demo").click().run()
    assert "Save or discard the pending file-scope decision" not in rendered(app)
    app = app.text_input(key="criteria_source_confirmer").set_value("Constructed confirmer").run()
    assert not app.button(key="confirm_criteria").disabled


@pytest.mark.parametrize("field", ["note", "disposition"])
def test_scope_draft_stays_on_its_file_when_switch_arrives_with_first_edit(field) -> None:
    app, store = reopened_comparison_app()
    record = store.directory / f"{CURRENT_REVIEW_ID}.json"
    saved = record.read_bytes()
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    draft = "Constructed explanation for notes.md only."
    if field == "note":
        app.text_area(key=scope_key(app, "scope_note")).set_value(draft)
    else:
        app.selectbox(key=scope_key(app, "scope_disposition")).set_value(
            "within_confirmed_criteria"
        )

    # A client can send the first edit and a previously enabled selector together.
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("src/unrelated.py").run()
    assert not app.exception
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "notes.md"
    assert app.selectbox(key=scope_key(app, "scope_file_path")).disabled
    assert app.text_area(key=scope_key(app, "scope_note")).value == (
        draft if field == "note" else ""
    )
    assert app.selectbox(key=scope_key(app, "scope_disposition")).value == (
        "within_confirmed_criteria" if field == "disposition" else None
    )
    assert app.button(key="reopen_review").disabled
    assert app.download_button and all(button.disabled for button in app.download_button)
    assert record.read_bytes() == saved

    app = app.button(key=scope_key(app, "discard_scope_decision_draft")).click().run()
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "notes.md"
    assert not app.selectbox(key=scope_key(app, "scope_file_path")).disabled
    assert all(not button.disabled for button in app.download_button)
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("src/unrelated.py").run()
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "src/unrelated.py"
    assert app.selectbox(key=scope_key(app, "scope_disposition")).value is None
    assert app.text_area(key=scope_key(app, "scope_note")).value == ""
    assert record.read_bytes() == saved


def test_saving_scope_draft_allows_switch_with_no_retargeting() -> None:
    app, store = reopened_comparison_app()
    assert app.selectbox(key=scope_key(app, "scope_disposition")).disabled
    assert app.text_area(key=scope_key(app, "scope_note")).disabled
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    app = app.selectbox(key=scope_key(app, "scope_disposition")).set_value(
        "within_confirmed_criteria"
    ).run()
    app = app.selectbox(key=scope_key(app, "scope_criterion_id")).set_value("AC-01").run()
    draft = "Constructed decision for notes.md only."
    app = app.text_area(key=scope_key(app, "scope_note")).set_value(draft).run()
    assert app.selectbox(key=scope_key(app, "scope_file_path")).disabled
    app = app.button(key=scope_key(app, "save_scope_decision")).click().run()
    assert not app.exception
    assert not app.selectbox(key=scope_key(app, "scope_file_path")).disabled
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("src/unrelated.py").run()
    assert app.selectbox(key=scope_key(app, "scope_disposition")).value is None
    assert app.text_area(key=scope_key(app, "scope_note")).value == ""
    assert app.button(key=scope_key(app, "save_scope_decision")).disabled

    saved = store.load(CURRENT_REVIEW_ID)
    decision = saved.bundle.file_scope_decisions[-1]
    assert decision.path == "notes.md"
    assert decision.criterion_id == "AC-01"
    assert decision.note == draft
    assert all(item.path != "src/unrelated.py" for item in saved.bundle.file_scope_decisions)


def test_scope_form_rejects_late_edits_from_the_previous_file() -> None:
    app, store = reopened_comparison_app()
    record = store.directory / f"{CURRENT_REVIEW_ID}.json"
    saved = record.read_bytes()
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    selector = app.selectbox(key=scope_key(app, "scope_file_path"))
    disposition = app.selectbox(key=scope_key(app, "scope_disposition"))
    note = app.text_area(key=scope_key(app, "scope_note"))
    disposition.set_value("outside_confirmed_criteria")
    note.set_value("Constructed delayed edit for notes.md only.")
    payload = _scope_widget_payload(app, selector, disposition, note)
    disposition.set_value(None)
    note.set_value("")
    app = selector.set_value("src/unrelated.py").run()
    app = app._run(payload)

    assert not app.exception
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "src/unrelated.py"
    assert app.selectbox(key=scope_key(app, "scope_disposition")).value is None
    assert app.text_area(key=scope_key(app, "scope_note")).value == ""
    assert app.button(key=scope_key(app, "save_scope_decision")).disabled
    assert record.read_bytes() == saved


@pytest.mark.parametrize("action", ["save_scope_decision", "discard_scope_decision_draft"])
def test_scope_form_rejects_replayed_action_after_resolution(action: str) -> None:
    app, store = reopened_comparison_app()
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    app = app.selectbox(key=scope_key(app, "scope_disposition")).set_value(
        "outside_confirmed_criteria"
    ).run()
    app = app.text_area(key=scope_key(app, "scope_note")).set_value("Constructed first note.").run()
    click = app.button(key=scope_key(app, action)).click()
    payload = _scope_widget_payload(app, click)
    app = click.run()
    record = store.directory / f"{CURRENT_REVIEW_ID}.json"
    saved = record.read_bytes()
    app = app.selectbox(key=scope_key(app, "scope_disposition")).set_value(
        "outside_confirmed_criteria"
    ).run()
    new_note = "Constructed second note for the same file."
    app = app.text_area(key=scope_key(app, "scope_note")).set_value(new_note).run()
    app = app._run(payload)
    assert not app.exception
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "notes.md"
    assert app.selectbox(key=scope_key(app, "scope_file_path")).disabled
    assert app.text_area(key=scope_key(app, "scope_note")).value == new_note
    assert record.read_bytes() == saved


def test_interrupted_scope_save_persists_once_when_rerun() -> None:
    app, store = reopened_comparison_app()
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    app = app.selectbox(key=scope_key(app, "scope_disposition")).set_value(
        "outside_confirmed_criteria"
    ).run()
    note = "Constructed note submitted just before a rerun."
    app = app.text_area(key=scope_key(app, "scope_note")).set_value(note).run()
    save = app.button(key=scope_key(app, "save_scope_decision")).click()
    payload = _scope_widget_payload(app, save)
    set_state = SessionStateProxy.__setitem__
    interrupted = False

    def interrupt_after_append(proxy, key, value):
        nonlocal interrupted
        set_state(proxy, key, value)
        if key == "review_state" and value.bundle.file_scope_decisions and not interrupted:
            interrupted = True
            st.rerun()

    with patch.object(SessionStateProxy, "__setitem__", interrupt_after_append):
        app = save.run()
    app = app._run(payload)
    assert interrupted
    assert not app.exception
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "notes.md"
    assert not app.selectbox(key=scope_key(app, "scope_file_path")).disabled
    assert app.text_area(key=scope_key(app, "scope_note")).value == ""
    decision, = store.load(CURRENT_REVIEW_ID).bundle.file_scope_decisions
    assert (decision.path, decision.note) == ("notes.md", note)


def test_pending_scope_draft_survives_until_explicit_discard_before_reopening() -> None:
    app, store = reopened_comparison_app()
    before = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}
    app = app.selectbox(key="saved_reopen_review_id").set_value(PREVIOUS_REVIEW_ID).run()
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    assert not app.button(key="reopen_review").disabled
    assert not app.button(key="load_demo").disabled
    draft = "Constructed draft must stay with the open review."
    app.text_area(key=scope_key(app, "scope_note")).set_value(draft)
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.button(key="reopen_review").disabled
    assert app.button(key="load_demo").disabled
    assert app.text_area(key=scope_key(app, "scope_note")).value == draft
    assert app.session_state["review_state"].review.review_id == CURRENT_REVIEW_ID
    app = app.selectbox(key=scope_key(app, "scope_disposition")).set_value(
        "outside_confirmed_criteria"
    ).run()

    app = app.button(key=scope_key(app, "discard_scope_decision_draft")).click().run()
    assert not app.exception
    assert app.text_area(key=scope_key(app, "scope_note")).value == ""
    assert app.selectbox(key=scope_key(app, "scope_disposition")).value is None
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "notes.md"
    assert not app.button(key="reopen_review").disabled
    app = app.button(key="reopen_review").click().run()
    assert app.session_state["review_state"].review.review_id == PREVIOUS_REVIEW_ID
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == before


def test_pending_scope_draft_blocks_applying_criteria_edits_until_discarded() -> None:
    app, store = reopened_comparison_app()
    before = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    revised = "Export CSV with headers"
    app = app.text_input(key="criterion_text_AC-01").set_value(revised).run()
    assert not app.button(key="confirm_criteria").disabled
    draft = "Constructed unsubmitted scope explanation."
    app.text_area(key=scope_key(app, "scope_note")).set_value(draft)
    app = app.button(key="confirm_criteria").click().run()
    assert not app.exception
    assert app.button(key="confirm_criteria").disabled
    assert app.button(key="remove_AC-01").disabled
    assert app.text_area(key=scope_key(app, "scope_note")).value == draft
    assert app.session_state["review_state"].bundle is not None
    app = app.button(key=scope_key(app, "discard_scope_decision_draft")).click().run()
    assert not app.exception
    assert app.text_input(key="criterion_text_AC-01").value == revised
    assert not app.button(key="confirm_criteria").disabled
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == before


def test_scope_draft_blocks_stale_acceptance_note_action() -> None:
    app, store = reopened_comparison_app(final_acceptance_context=True)
    before = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    assert not app.button(key="add_final_acceptance_note").disabled
    draft = "Constructed draft remains with the recorded file."
    app.text_area(key=scope_key(app, "scope_note")).set_value(draft)
    app = app.button(key="add_final_acceptance_note").click().run()
    assert not app.exception
    assert not any(area.key == "final_acceptance_note" for area in app.text_area)
    assert app.button(key="revoke_final_acceptance").disabled
    assert app.text_area(key=scope_key(app, "scope_note")).value == draft
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == before


def test_discard_scope_draft_preserves_inspection_after_neutral_saved_update() -> None:
    app, store = reopened_comparison_app()
    app = app.selectbox(key=scope_key(app, "scope_file_path")).set_value("notes.md").run()
    draft = "Constructed draft while the saved decision changes."
    app = app.text_area(key=scope_key(app, "scope_note")).set_value(draft).run()
    original = app.session_state["review_state"]
    updated, _ = store.mutate(
        CURRENT_REVIEW_ID,
        lambda state: append_resolution(state, ResolutionEvent(
            criterion_id="AC-01", decision=HumanDecision.REJECTED_FINDING,
            comment="Constructed update from another workbench",
            reviewer="Constructed reviewer",
        )),
    )
    assert updated.review == original.review
    saved = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}

    app = app.run()
    assert app.session_state["review_state"] == original
    assert app.text_area(key=scope_key(app, "scope_note")).value == draft
    app = app.button(key=scope_key(app, "discard_scope_decision_draft")).click().run()
    assert not app.exception
    assert app.session_state["review_state"] == updated
    assert app.selectbox(key=scope_key(app, "scope_file_path")).value == "notes.md"
    assert app.text_area(key=scope_key(app, "scope_note")).value == ""
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == saved
