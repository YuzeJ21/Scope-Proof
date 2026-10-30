"""Reopened reviews compare explicit saved baselines without fetching or saving."""

from unittest.mock import patch

import pytest

from apps.web.deferred_exports import (
    DeferredExportUnavailable,
    deferred_saved_comparison_export,
)
from scopeproof_core.reporting.exporters import export_comparison_json
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import new_app
from tests.saved_comparison_fixture import (
    CURRENT_HEAD,
    CURRENT_REVIEW_ID,
    HISTORY_HEAD,
    PREVIOUS_HEAD,
    PREVIOUS_REVIEW_ID,
    saved_comparison_states,
)


def reopened_comparison_app(*, selected_references=False):
    store = JsonReviewStore(default_local_review_directory())
    current, previous = saved_comparison_states(selected_references=selected_references)
    store.save(current)
    store.save(previous)
    app = new_app()
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
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
    assert "identical confirmed criteria" in rendered(app)
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
    before = {p.name: p.read_bytes() for p in store.directory.glob("*.json")}
    app = app.text_area(key="scope_note").set_value("Unsubmitted scope explanation").run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert lease.selection is None
    assert app.button(key="compare_saved_analysis").disabled
    app = app.button(key="clear_saved_comparison_scope_draft").click().run()
    assert not app.exception
    assert app.text_area(key="scope_note").value == ""
    assert not app.selectbox(key="saved_comparison_baseline").disabled
    app = apply_other_baseline(app)
    assert len(comparison_downloads(app)) == 2
    assert before == {p.name: p.read_bytes() for p in store.directory.glob("*.json")}


def test_submitted_scope_controls_do_not_permanently_block_saved_comparison() -> None:
    app, _ = reopened_comparison_app()
    app = app.selectbox(key="scope_file_path").set_value("notes.md").run()
    app = app.selectbox(key="scope_disposition").set_value("outside_confirmed_criteria").run()
    app = app.text_area(key="scope_note").set_value("Recorded current-head scope explanation").run()
    app = app.button(key="save_scope_decision").click().run()
    assert not app.exception
    assert app.session_state["review_state"].bundle.file_scope_decisions[-1].note == (
        "Recorded current-head scope explanation"
    )
    assert not app.selectbox(key="saved_comparison_baseline").disabled
    app = apply_other_baseline(app)
    assert not app.exception
    assert len(comparison_downloads(app)) == 2
