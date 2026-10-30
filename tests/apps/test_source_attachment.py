"""Saved source continuation is explicit, read-only and guarded on new contradictions."""

from unittest.mock import patch

import pytest

from apps.web.deferred_exports import DeferredExportUnavailable, deferred_review_export
from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.reporting.exporters import export_json
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    CIObservation,
    LineChangeType,
)
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_deferred_exports import accepted_review_state
from tests.apps.test_selected_references import complete_reference
from tests.apps.test_streamlit_app import load_demo, new_app


def reopen(review_id):
    app = new_app().selectbox(key="saved_reopen_review_id").set_value(review_id).run()
    return app.button(key="reopen_review").click().run()


def saved_reference():
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(
        ChangedFile(
            path="src/reference_only.py",
            status="modified",
            lines=[
                ChangedLine(change_type=LineChangeType.ADDED, line_number=i, content=f"return {i}")
                for i in (7, 8, 9)
            ],
        )
    )
    app = app.run().button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    snapshot = app.session_state["snapshot"].model_copy(deep=True)
    app = complete_reference(app).button(key="save_selected_reference").click().run()
    state = app.session_state["review_state"]
    return reopen(state.review.review_id), state, snapshot


def load_matching(app, snapshot):
    # Reproduction must fail on the missing control before patching the new module.
    button = app.button(key="load_reviewed_source")
    with (
        patch("apps.web.source_attachment.load_demo_snapshot", return_value=snapshot),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=AssertionError("Constructed source must stay offline"),
        ),
    ):
        return button.click().run()


def test_reopen_load_and_repeated_reference_saves_preserve_analysis_and_saved_confirmation():
    app, before, snapshot = saved_reference()
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{before.review.review_id}.json"
    original_bytes = path.read_bytes()
    assert app.session_state["snapshot"] is None
    app = load_matching(app, snapshot)
    assert not app.exception
    assert app.session_state["review_state"] == before
    assert app.session_state["criteria_confirmed"]
    assert app.session_state["snapshot"] == snapshot
    assert path.read_bytes() == original_bytes
    assert app.button(key="run_analysis").disabled
    for number in (8, 9):
        app = (
            app.selectbox(key="selected_reference_source")
            .set_value("changed_file:src/reference_only.py")
            .run()
        )
        app = app.selectbox(key="selected_reference_line").set_value(number).run()
        app = (
            app.text_input(key="selected_reference_reviewer")
            .set_value("Constructed resumed actor")
            .run()
        )
        app = (
            app.text_area(key="selected_reference_rationale")
            .set_value("Constructed continued inspection")
            .run()
        )
        app = app.button(key="save_selected_reference").click().run()
        assert not app.exception
    after = app.session_state["review_state"].model_dump(mode="json")
    refs = after["bundle"].pop("reviewer_selected_references")
    assert [r["line_number"] for r in refs] == [7, 8, 9]
    original = before.model_dump(mode="json")
    assert refs[0] == original["bundle"].pop("reviewer_selected_references")[0]
    assert after["bundle"].pop("active_reviewer_selected_reference_ids") == [
        r["reference_id"] for r in refs
    ]
    original["bundle"].pop("active_reviewer_selected_reference_ids")
    assert after == original
    assert store.load(before.review.review_id) == app.session_state["review_state"]


def test_source_contradiction_blocks_old_ready_exports_and_survives_reopen():
    state = accepted_review_state()
    store = JsonReviewStore(default_local_review_directory())
    store.save(state)
    path = store.directory / f"{state.review.review_id}.json"
    saved = path.read_bytes()
    app = reopen(state.review.review_id)
    assert app.button(key="load_reviewed_source")
    guard = app.session_state["source_authority_guard"]
    deferred = deferred_review_export(
        state,
        export_json,
        store=store,
        expected_fingerprint=store.state_fingerprint(state),
        authority_check=lambda: guard.allows(state),
    )
    assert deferred()
    snapshot = load_demo_snapshot()
    snapshot.ci_observation = CIObservation(
        state=CheckState.FAILING,
        total_check_runs=1,
        failing_check_runs=1,
        reason="Constructed fresh CI failure",
    )
    snapshot.check_state = snapshot.ci_observation.state
    app = load_matching(app, snapshot)
    assert not app.exception
    assert app.session_state["review_state"] == state
    assert path.read_bytes() == saved
    assert not guard.allows(state)
    assert not any("**Review status: Ready**" in m.value for m in app.markdown)
    assert any("Refresh required" in m.value for m in app.markdown)
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    with pytest.raises(DeferredExportUnavailable):
        deferred()
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert not app.session_state["source_authority_guard"].allows(state)
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    app = load_matching(app, load_demo_snapshot())
    assert not app.exception
    assert app.session_state["source_authority_guard"].allows(state)
    assert path.read_bytes() == saved


def test_pending_requirements_draft_disables_attachment_without_discarding_it():
    app, _, _ = saved_reference()
    app = (
        app.text_area(key="requirements_input").set_value("Constructed unsaved requirements").run()
    )
    assert app.button(key="load_reviewed_source").disabled
    assert app.text_area(key="requirements_input").value == "Constructed unsaved requirements"


def test_new_current_head_path_still_requires_explicit_reanalysis():
    app, _, snapshot = saved_reference()
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request", return_value=snapshot
        ),
        patch("scopeproof_core.github.client.GitHubClient.fetch_candidate_files", return_value=[]),
    ):
        app = app.button(key="fetch_pr").click().run()
    assert not app.exception
    assert app.session_state["review_state"] is None
    assert not app.session_state["criteria_confirmed"]
