"""Read-only workbench handoffs retain retired associations and original snapshots."""

import pytest

from scopeproof_core.reviews.junit_audit import withdraw_junit_evidence_import
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import new_app, select_saved_review
from tests.reporting.test_junit_correction import correct, correction_state, mappings, moved


@pytest.mark.parametrize("removed", ["original", "intermediate", "withdrawn_intermediate"])
def test_unmapped_criterion_retains_correction_audit_without_current_mapped_cases(removed):
    original = correction_state()
    state = moved(original)
    criterion_id = "AC-01"
    if removed != "original":
        state = correct(
            state, original.bundle.junit_evidence_imports[0].criterion_mappings,
            reason="CONSTRUCTED return to original mappings",
        )
        criterion_id = "AC-03"
    if removed == "withdrawn_intermediate":
        state = withdraw_junit_evidence_import(
            state, import_id=state.bundle.junit_evidence_imports[0].import_id,
            reviewer="CONSTRUCTED withdrawal actor", reason="CONSTRUCTED terminal retirement",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        )
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    before = path.read_bytes()
    app = select_saved_review(new_app(), state.review.review_id)
    app = app.button(key="reopen_review").click().run()
    app = app.selectbox(key="selected_criterion").set_value(criterion_id).run()
    assert not app.exception
    assert "Recorded imported JUnit results (0)" in [x.label for x in app.expander]
    text = "\n".join(x.value for x in app.text)
    for event in state.bundle.junit_import_events:
        assert event.reason in text
        assert event.event_id in text
    assert path.read_bytes() == before


def test_comparison_of_corrected_versions_shows_both_original_and_effective_snapshots():
    previous = moved(correction_state())
    current = correct(previous, mappings(("AC-03", [
        "suite-0001-case-0001", "suite-0001-case-0002", "suite-0001-case-0003",
    ])), reason="CONSTRUCTED consolidate explicit mappings")
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(current)
    before = path.read_bytes()
    app = select_saved_review(new_app(), current.review.review_id)
    app = app.button(key="reopen_review").click().run()
    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    app.session_state["comparison_base_bundle"] = previous.bundle
    app = app.run()
    assert not app.exception
    # The current criterion audit supplies one snapshot; both comparison sides add two more.
    captions = [x.value for x in app.caption]
    text = "\n".join(x.value for x in app.text)
    assert captions.count("Original mappings (retained)") == 3
    assert captions.count("Current effective mappings") == 3
    assert text.count("AC-01: suite-0001-case-0001") == 3
    assert "AC-02: suite-0001-case-0002, suite-0001-case-0003" in text
    assert "AC-03: suite-0001-case-0001, suite-0001-case-0002, suite-0001-case-0003" in text
    assert path.read_bytes() == before
