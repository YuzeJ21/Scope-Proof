"""Other saved histories remain explicit, read-only and fingerprint-bound."""

import json
from unittest.mock import patch

import pytest

from apps.web.deferred_exports import DeferredExportUnavailable, deferred_saved_comparison_export
from scopeproof_core.reporting.exporters import export_comparison_json
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_saved_comparison_ui import comparison_downloads, rendered
from tests.apps.test_streamlit_app import new_app
from tests.saved_comparison_fixture import (
    CURRENT_REVIEW_ID,
    FOREIGN_HISTORY_HEAD,
    PREVIOUS_REVIEW_ID,
    saved_comparison_states,
)


def foreign_history_app(*, history_only=False, incompatible_active=False):
    store = JsonReviewStore(default_local_review_directory())
    current, previous = saved_comparison_states(selected_references=True, foreign_history=True)
    if history_only:
        previous.bundle = None
    elif incompatible_active:
        provenance = previous.review.criteria_source_provenance.model_copy(
            update={
                "source_uri": "https://example.test/constructed-other-active-source",
            }
        )
        previous.review.criteria_source_provenance = provenance
        previous.criteria_revision.source_provenance = provenance
        previous.bundle.review.criteria_source_provenance = provenance
        reference = previous.bundle.reviewer_selected_references[0]
        previous.bundle.reviewer_selected_references[0] = reference.model_copy(
            update={
                "criteria_source_provenance": provenance,
            }
        )
    store.save(current)
    store.save(ReviewState.model_validate(previous.model_dump(mode="python")))
    app = new_app()
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.button(key="reopen_review").click().run()
    app = (
        app.selectbox(key="saved_comparison_baseline")
        .set_value(f"saved:{PREVIOUS_REVIEW_ID}")
        .run()
    )
    assert not app.exception
    assert any(item.key == "saved_comparison_analysis" for item in app.selectbox), (
        "another saved record needs an explicit active/history analysis selector"
    )
    return app, store


def choose_history(app):
    return app.selectbox(key="saved_comparison_analysis").set_value("history:0").run()


def record_bytes(store):
    return {path.name: path.read_bytes() for path in store.directory.glob("*.json")}


@pytest.mark.parametrize("mode", ["normal", "history_only", "incompatible_active"])
def test_foreign_history_can_be_explicitly_selected_without_source_reload_or_saved_mutation(mode):
    app, store = foreign_history_app(
        history_only=mode == "history_only",
        incompatible_active=mode == "incompatible_active",
    )
    before = record_bytes(store)
    assert any(
        FOREIGN_HISTORY_HEAD in option and "criteria revision 1" in option
        for option in app.selectbox(key="saved_comparison_analysis").options
    )
    if mode == "history_only":
        assert app.selectbox(key="saved_comparison_analysis").value is None
        assert app.button(key="compare_saved_analysis").disabled
    app = choose_history(app)
    assert comparison_downloads(app) == []
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=AssertionError("historical comparison must not fetch source"),
        ),
        patch("subprocess.run", side_effect=AssertionError("target code must not execute")),
    ):
        app = app.button(key="compare_saved_analysis").click().run()
    assert not app.exception
    selection = app.session_state["saved_comparison_selection"]
    assert selection.baseline_review_id == PREVIOUS_REVIEW_ID
    assert selection.history_index == 0
    assert FOREIGN_HISTORY_HEAD in rendered(app)
    assert f"Baseline record: {PREVIOUS_REVIEW_ID}" in rendered(app)
    assert "Analysis: History 1" in rendered(app)
    assert "Constructed foreign-history reference reviewer" in rendered(app)
    lease = app.session_state["saved_comparison_export_lease"]
    data = json.loads(
        deferred_saved_comparison_export(
            selection,
            export_comparison_json,
            store=store,
            lease=lease,
        )()
    )
    assert data["previous_head_sha"] == FOREIGN_HISTORY_HEAD
    assert data["file_scope"]["previous"]["review_id"] == PREVIOUS_REVIEW_ID
    assert data["file_scope"]["previous"]["criteria_revision_number"] == 1
    assert data["previous_gate"] == data["current_gate"] == "blocked"
    assert record_bytes(store) == before


@pytest.mark.parametrize("applied", [False, True])
@pytest.mark.parametrize("change", ["reference_only", "remove_history", "replace_history"])
def test_changed_foreign_snapshot_clears_pending_and_applied_choice_without_active_fallback(
    applied,
    change,
):
    app, store = foreign_history_app()
    app = choose_history(app)
    old_download = None
    if applied:
        app = app.button(key="compare_saved_analysis").click().run()
        lease = app.session_state["saved_comparison_export_lease"]
        old_download = deferred_saved_comparison_export(
            lease.selection,
            export_comparison_json,
            store=store,
            lease=lease,
        )

    def modify(state):
        if change == "remove_history":
            state.analysis_history.clear()
        elif change == "replace_history":
            from tests.saved_comparison_fixture import (
                _constructed_state,
                _with_prior_scope_decision,
            )

            state.analysis_history = [
                _with_prior_scope_decision(
                    _constructed_state(
                        PREVIOUS_REVIEW_ID,
                        "f" * 40,
                        added_path=False,
                        selected_context="replacement",
                    )
                ).bundle
            ]
        else:
            reference = state.analysis_history[0].reviewer_selected_references[0]
            state.analysis_history[0].reviewer_selected_references[0] = reference.model_copy(
                update={
                    "rationale": "Constructed external replacement of retained context.",
                }
            )
        return ReviewState.model_validate(state.model_dump(mode="python"))

    store.mutate(PREVIOUS_REVIEW_ID, modify)
    before = record_bytes(store)
    app = app.run()
    assert not app.exception
    assert app.selectbox(key="saved_comparison_analysis").value is None
    assert app.button(key="compare_saved_analysis").disabled
    assert comparison_downloads(app) == []
    assert app.session_state["saved_comparison_selection"] is None
    if old_download is not None:
        with pytest.raises(DeferredExportUnavailable):
            old_download()
    assert record_bytes(store) == before


def test_incompatible_foreign_history_rejects_even_if_active_is_compatible():
    app, store = foreign_history_app()

    def modify(state):
        historical = state.analysis_history[0]
        provenance = historical.review.criteria_source_provenance.model_copy(
            update={
                "source_uri": "https://example.test/constructed-other-history-source",
            }
        )
        historical.review.criteria_source_provenance = provenance
        reference = historical.reviewer_selected_references[0]
        historical.reviewer_selected_references[0] = reference.model_copy(
            update={
                "criteria_source_provenance": provenance,
            }
        )
        return ReviewState.model_validate(state.model_dump(mode="python"))

    store.mutate(PREVIOUS_REVIEW_ID, modify)
    app = app.run()
    app = choose_history(app)
    before = record_bytes(store)
    app = app.button(key="compare_saved_analysis").click().run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.session_state["saved_comparison_selection"] is None
    assert "cannot be compared" in rendered(app)
    assert record_bytes(store) == before


def test_discovery_to_prepare_change_is_rejected_instead_of_repointing_history():
    app, store = foreign_history_app()
    app = choose_history(app)
    from apps.web import saved_comparison

    original = saved_comparison.prepare_saved_comparison

    def mutate_then_prepare(*args, **kwargs):
        def modify(state):
            reference = state.analysis_history[0].reviewer_selected_references[0]
            state.analysis_history[0].reviewer_selected_references[0] = reference.model_copy(
                update={
                    "rationale": "Constructed writer between discovery and preparation.",
                }
            )
            return ReviewState.model_validate(state.model_dump(mode="python"))

        store.mutate(PREVIOUS_REVIEW_ID, modify)
        return original(*args, **kwargs)

    with patch.object(
        saved_comparison, "prepare_saved_comparison", side_effect=mutate_then_prepare
    ):
        app = app.button(key="compare_saved_analysis").click().run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.session_state["saved_comparison_selection"] is None
    assert "cannot be compared" in rendered(app)


def test_switching_foreign_analysis_invalidates_old_download_even_after_reselection():
    app, store = foreign_history_app()
    app = choose_history(app)
    app = app.button(key="compare_saved_analysis").click().run()
    lease = app.session_state["saved_comparison_export_lease"]
    old_download = deferred_saved_comparison_export(
        lease.selection,
        export_comparison_json,
        store=store,
        lease=lease,
    )
    before = record_bytes(store)
    app = app.selectbox(key="saved_comparison_analysis").set_value("active").run()
    assert not app.exception and comparison_downloads(app) == []
    assert lease.selection is None
    app = choose_history(app)
    app = app.button(key="compare_saved_analysis").click().run()
    assert len(comparison_downloads(app)) == 2
    with pytest.raises(DeferredExportUnavailable):
        old_download()
    assert record_bytes(store) == before


@pytest.mark.parametrize("damage", ["delete", "corrupt"])
def test_unavailable_foreign_record_never_falls_back_to_another_analysis(damage):
    app, store = foreign_history_app()
    app = choose_history(app)
    app = app.button(key="compare_saved_analysis").click().run()
    path = store.directory / f"{PREVIOUS_REVIEW_ID}.json"
    if damage == "delete":
        path.unlink()
    else:
        path.write_text("constructed corrupt JSON")
    before = record_bytes(store)
    app = app.run()
    assert not app.exception
    assert comparison_downloads(app) == []
    assert app.session_state["saved_comparison_selection"] is None
    assert app.button(key="compare_saved_analysis").disabled
    assert record_bytes(store) == before


def test_unselected_foreign_records_are_not_loaded_to_discover_history():
    app, store = foreign_history_app()
    (store.directory / "constructed-unselected.json").write_text("constructed corrupt JSON")
    original = JsonReviewStore.load

    def reject_unselected(self, review_id):
        if review_id == "constructed-unselected":
            raise AssertionError("an unselected record must not be eagerly loaded")
        return original(self, review_id)

    with patch.object(JsonReviewStore, "load", reject_unselected):
        app = app.run()
        app = choose_history(app)
        app = app.button(key="compare_saved_analysis").click().run()
    assert not app.exception
    assert FOREIGN_HISTORY_HEAD in rendered(app)
    assert len(comparison_downloads(app)) == 2
