"""Informational decision comparison details use literal workbench rendering."""

import pytest
from streamlit.testing.v1 import AppTest


def _render_context():
    from apps.web.decision_context_comparison import render_decision_context_comparison
    from scopeproof_core.reviews.comparison import compare_reviews
    from tests.reviews.test_decision_context_comparison import decision_bundle

    previous = decision_bundle()
    current = previous.model_copy(deep=True)
    current.resolutions[0].comment = "Constructed new note, same decision label"
    current.runtime_evidence[0].limitations = ["Constructed newly observed limitation"]
    render_decision_context_comparison(
        compare_reviews(previous, current).decision_context_comparison
    )


def _render_missing():
    from apps.web.decision_context_comparison import render_decision_context_comparison

    render_decision_context_comparison(None)


def _render_empty():
    from apps.web.decision_context_comparison import render_decision_context_comparison
    from scopeproof_core.reviews.comparison import compare_reviews
    from tests.saved_comparison_fixture import saved_comparison_states

    state, _ = saved_comparison_states()
    render_decision_context_comparison(
        compare_reviews(state.bundle, state.bundle).decision_context_comparison
    )


def _render_unlinked_and_unsafe():
    from apps.web.decision_context_comparison import render_decision_context_comparison
    from scopeproof_core.reviews.comparison import compare_reviews
    from tests.reviews.test_decision_context_comparison import decision_bundle

    bundle = decision_bundle(linked=False)
    bundle.resolutions[0].reviewer = "**Accepted** <script>bad</script>"
    bundle.resolutions[0].comment = "<img src=x onerror=bad>"
    bundle.resolutions[0].evidence_url = "javascript:bad"
    bundle.runtime_evidence[0].artifact_reference = "data:text/html,<script>bad</script>"
    bundle.runtime_evidence[0].result = "<img src=x> **Ready**"
    render_decision_context_comparison(compare_reviews(bundle, bundle).decision_context_comparison)


def _values(elements):
    return "\n".join(item.value for item in elements)


def test_both_sides_show_same_enum_notes_full_identity_and_observation_limitations():
    app = AppTest.from_function(_render_context).run()
    assert not app.exception
    assert "Recorded decision and runtime context" in _values(app.markdown)
    assert "Changed recorded context: 1" in _values(app.markdown)
    assert "Previous decision context" in [item.label for item in app.expander]
    assert "Current decision context" in [item.label for item in app.expander]
    text = _values(app.text)
    for expected in (
        "saved-comparison-current", "acme/widget", "PR #7", "Criteria revision: 2",
        "Constructed new note, same decision label", "Constructed external observation",
        "Constructed passed result", "Constructed newly observed limitation",
        "Constructed automatic actor", "E3", "2026-10-30T12:00:00+00:00",
    ):
        assert expected in text
    assert "b" * 40 in _values(app.code)
    assert "ScopeProof did not execute" in _values(app.caption)
    assert not app.button and not app.text_input and not app.checkbox


def test_missing_projection_and_known_empty_snapshots_have_different_messages():
    missing = AppTest.from_function(_render_missing).run()
    assert not missing.exception
    assert "not included in this older comparison" in _values(missing.info)
    empty = AppTest.from_function(_render_empty).run()
    assert not empty.exception
    assert "No criterion decisions or runtime observations recorded on either side" in (
        _values(empty.info)
    )
    assert "not included" not in _values(empty.info)


def test_legacy_link_unknown_and_untrusted_text_remain_inert():
    app = AppTest.from_function(_render_unlinked_and_unsafe).run()
    assert not app.exception
    text = _values(app.text)
    assert "Legacy unlinked" in text
    assert "**Accepted** <script>bad</script>" in text
    assert "<img src=x onerror=bad>" in text
    assert "<img src=x> **Ready**" in text
    markdown = _values(app.markdown)
    assert "<script>" not in markdown and "<img" not in markdown
    assert "[" not in markdown.split("Recorded decision and runtime context", 1)[0]
    assert all("<script>" not in item.label for item in app.expander)


@pytest.mark.parametrize("target", ["current", "baseline", "own_history", "foreign_history"])
def test_runtime_only_saved_mutation_invalidates_render_and_old_download_callback(tmp_path, target):
    from apps.web.deferred_exports import (
        DeferredExportUnavailable,
        SavedComparisonExportLease,
        deferred_saved_comparison_export,
    )
    from scopeproof_core.reporting.exporters import export_comparison_json
    from scopeproof_core.reviews.saved_comparison import (
        SavedComparisonUnavailable,
        locked_saved_comparison,
        prepare_saved_comparison,
    )
    from scopeproof_core.storage.json_store import JsonReviewStore
    from tests.saved_comparison_fixture import saved_comparison_states

    current, baseline = saved_comparison_states(foreign_history=True, decision_context=True)
    store = JsonReviewStore(tmp_path / "reviews")
    for state in (current, baseline):
        store.save(state)
    owner = current if target in {"current", "own_history"} else baseline
    history_index = 0 if "history" in target else None
    selection = prepare_saved_comparison(
        store, current,
        current.review.review_id if target == "own_history" else baseline.review.review_id,
        history_index=history_index,
    )
    lease = SavedComparisonExportLease(selection=selection)
    download = deferred_saved_comparison_export(
        selection, export_comparison_json, store=store, lease=lease,
    )
    assert '"recorded_context_changed"' in download()
    changed = owner.model_copy(deep=True)
    analysis = changed.analysis_history[0] if history_index is not None else changed.bundle
    gate_before = analysis.gate.model_dump_json()
    analysis.runtime_evidence[0].limitations.append("Constructed later recorded limitation")
    store.save(changed)
    bytes_after_mutation = {
        path.name: path.read_bytes() for path in store.directory.glob("*.json")
    }
    with pytest.raises(SavedComparisonUnavailable), locked_saved_comparison(store, selection):
        pytest.fail("changed runtime context must invalidate the applied comparison")
    with pytest.raises(DeferredExportUnavailable):
        download()
    assert analysis.gate.model_dump_json() == gate_before
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == (
        bytes_after_mutation
    )
