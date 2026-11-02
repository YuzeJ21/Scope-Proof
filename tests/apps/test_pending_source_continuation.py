"""Real workbench continuation after reopening and confirming edited criteria."""

from unittest.mock import patch

from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_source_attachment import load_matching, reopen, saved_reference


def test_reopened_criteria_revision_loads_source_and_analyzes_same_review():
    app, original, snapshot = saved_reference()
    app = (
        app.text_input(key="criterion_text_AC-01")
        .set_value("CONSTRUCTED revised CSV export criterion")
        .run()
    )
    app = app.button(key="confirm_criteria").click().run()
    assert not app.exception
    pending = app.session_state["review_state"]
    assert pending.bundle is None and pending.criteria_revision.confirmed
    assert pending.analysis_history == [original.bundle]
    assert app.button(key="run_analysis").disabled
    assert not app.button(key="load_reviewed_source").disabled
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{original.review.review_id}.json"
    before = path.read_bytes()
    app = load_matching(app, snapshot)
    assert not app.exception and path.read_bytes() == before
    assert not app.button(key="run_analysis").disabled
    app = app.button(key="run_analysis").click().run()
    assert not app.exception
    after = app.session_state["review_state"]
    assert after.review.review_id == original.review.review_id
    assert after.criteria_revision == pending.criteria_revision
    assert after.analysis_history == [original.bundle]
    assert after.bundle.criteria_revision_number == 2
    assert not after.bundle.reviewer_selected_references
    assert not after.bundle.resolutions and not after.review.final_acceptance
    assert app.session_state["review_source_attachment"] is None
    assert store.load(original.review.review_id) == after
    assert app.session_state["saved_review_fingerprint"] == store.state_fingerprint(after)
    app = reopen(after.review.review_id)
    assert app.session_state["review_state"] == after


def test_failed_pending_analysis_commit_keeps_pending_workbench_and_saved_record():
    app, original, snapshot = saved_reference()
    app = app.text_input(key="criterion_text_AC-01").set_value("CONSTRUCTED revised scope").run()
    app = app.button(key="confirm_criteria").click().run()
    app = load_matching(app, snapshot)
    pending = app.session_state["review_state"].model_copy(deep=True)
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{original.review.review_id}.json"
    before = path.read_bytes()
    with patch.object(
        JsonReviewStore, "_save_unlocked", side_effect=OSError("CONSTRUCTED failure")
    ):
        app = app.button(key="run_analysis").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == pending
    assert pending.bundle is None and path.read_bytes() == before
