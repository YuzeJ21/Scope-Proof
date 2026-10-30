"""Reference retirement preserves an already bound, healthy source attachment."""

import json

import pytest

from apps.web.deferred_exports import DeferredExportUnavailable, deferred_review_export
from scopeproof_core.reporting.exporters import export_json
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_reference_audit_ui import audit_draft
from tests.apps.test_source_attachment import reopen
from tests.reviews.test_reference_audit_attachment import attached


@pytest.mark.parametrize("action", ["Withdraw", "Correct"])
def test_retiring_last_unchanged_reference_preserves_loaded_attachment_and_exports(
    tmp_path, action
):
    before, snapshot, candidates, receipt = attached(tmp_path / "receipt")
    store = JsonReviewStore(default_local_review_directory())
    store.save(before)
    app = reopen(before.review.review_id)
    target = before.bundle.reviewer_selected_references[0]
    app = app.selectbox(key="selected_criterion").set_value(target.criterion_id).run()
    app.session_state["snapshot"] = snapshot
    app.session_state["candidate_files"] = candidates
    app.session_state["review_source_attachment"] = receipt
    app = app.run()
    assert not app.exception
    guard = app.session_state["source_authority_guard"]
    assert guard.allows(before)
    old_download = deferred_review_export(
        before,
        export_json,
        store=store,
        expected_fingerprint=store.state_fingerprint(before),
        authority_check=lambda: guard.allows(before),
    )
    assert old_download()
    app = audit_draft(app, action)
    if action == "Correct":
        app = (
            app.selectbox(key="selected_reference_source")
            .set_value("changed_file:src/export.py")
            .run()
        )
        app = app.selectbox(key="selected_reference_line").set_value(10).run()
        app = (
            app.text_area(key="selected_reference_rationale")
            .set_value("Changed source provides the intended static context")
            .run()
        )
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    after = app.session_state["review_state"]
    assert after.bundle.selected_reference_events[-1].action == (
        "withdrawn" if action == "Withdraw" else "corrected"
    )
    assert app.session_state["source_authority_guard"].allows(after)
    assert app.session_state["snapshot"] == snapshot
    assert app.session_state["candidate_files"] == candidates
    assert app.session_state["review_source_attachment"] == receipt
    assert after.bundle.gate == before.bundle.gate
    assert store.load(before.review.review_id) == after
    assert all(not b.disabled for b in app.download_button if b.key.startswith("download_"))
    current_download = deferred_review_export(
        after,
        export_json,
        store=store,
        expected_fingerprint=store.state_fingerprint(after),
        authority_check=lambda: guard.allows(after),
    )
    assert ReviewState.model_validate(json.loads(current_download())) == after
    with pytest.raises(DeferredExportUnavailable):
        old_download()
