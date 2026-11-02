"""A retired manual-only source path cannot obstruct fresh confirmed analysis."""

from unittest.mock import patch

import pytest

from scopeproof_core.reviews.source_attachment import required_source_candidate_paths
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_reference_audit_ui import audit_draft
from tests.apps.test_source_attachment import reopen
from tests.reviews.test_reference_audit_attachment import attached


@pytest.mark.parametrize("action", ["Withdraw", "Correct"])
def test_retired_loaded_path_is_not_reused_or_refetched_for_new_criteria(tmp_path, action):
    before, snapshot, candidates, receipt = attached(tmp_path / "source-receipt")
    store = JsonReviewStore(default_local_review_directory())
    store.save(before)
    app = reopen(before.review.review_id)
    target = before.bundle.reviewer_selected_references[0]
    app = app.selectbox(key="selected_criterion").set_value(target.criterion_id).run()
    app.session_state["snapshot"] = snapshot
    app.session_state["candidate_files"] = candidates
    app.session_state["review_source_attachment"] = receipt
    app = app.run()
    app = audit_draft(app, action)
    if action == "Correct":
        app = (
            app.selectbox(key="selected_reference_source")
            .set_value("changed_file:src/export.py")
            .run()
        )
        app = app.selectbox(key="selected_reference_line").set_value(11).run()
        app = (
            app.text_area(key="selected_reference_rationale")
            .set_value("CONSTRUCTED moved reference to a changed file")
            .run()
        )
    app = app.button(key="save_selected_reference").click().run()
    retired = app.session_state["review_state"]
    assert retired.bundle.selected_reference_events[-1].action == (
        "withdrawn" if action == "Withdraw" else "corrected"
    )
    assert app.session_state["candidate_files"] == candidates
    app = (
        app.text_input(key="criterion_text_AC-01")
        .set_value("CONSTRUCTED revised requirement")
        .run()
    )
    app = app.button(key="confirm_criteria").click().run()
    pending = app.session_state["review_state"]
    assert pending.bundle is None and pending.criteria_revision.confirmed
    assert required_source_candidate_paths(pending) == []
    assert not app.button(key="run_analysis").disabled
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=AssertionError("No refetch expected"),
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=AssertionError("No candidate fetch expected"),
        ),
    ):
        app = app.button(key="run_analysis").click().run()
    assert not app.exception
    after = app.session_state["review_state"]
    assert after.bundle is not None
    assert after.review.review_id == before.review.review_id
    assert after.analysis_history == [retired.bundle]
    assert after.criteria_revision == pending.criteria_revision
    assert not after.bundle.reviewer_selected_references
    assert not any(e.file_path == candidates[0].path for e in after.bundle.evidence)
    assert app.session_state["candidate_files"] == []
    assert store.load(after.review.review_id) == after
