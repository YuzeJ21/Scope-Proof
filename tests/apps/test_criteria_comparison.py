"""Explicit requirements inspection and click-time saved selection guards."""

from importlib import import_module

import pytest
from streamlit.testing.v1 import AppTest

from tests.apps.test_historical_analysis import _panel, inspect, seeded, values
from tests.reviews.test_criteria_comparison import report_for


def compare(app):
    return app.button(key="compare_saved_criteria").click().run()


def test_saved_pending_requirements_comparison_is_explicit_and_read_only(tmp_path):
    store, state, path = seeded(tmp_path)
    before = path.read_bytes()
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run())
    assert not app.exception
    assert "Saved criteria revision changes" not in values(app.markdown)
    assert len(app.get("download_button")) == 2
    app = compare(app)
    assert not app.exception
    text = values(app.markdown)
    assert "Saved criteria revision changes" in text
    assert "Current saved criteria" in text and "Unconfirmed" in text
    assert "CONSTRUCTED changed requirement: export JSON instead of CSV" in text
    assert len(app.get("download_button")) == 4
    assert app.session_state["opened"].bundle is None
    assert not app.session_state["opened"].criteria_revision.confirmed
    assert path.read_bytes() == before


def test_unsaved_draft_never_becomes_saved_comparison(tmp_path):
    store, state, path = seeded(tmp_path)
    before = path.read_bytes()
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run())
    app.text_input(key="current_draft").set_value("DRAFT-MUST-NOT-ENTER-REQUIREMENTS").run()
    app = compare(app)
    assert not app.exception
    assert "DRAFT-MUST-NOT-ENTER-REQUIREMENTS" not in values(app.markdown)
    assert path.read_bytes() == before


def test_reopen_and_changed_saved_current_requirements_clear_comparison(tmp_path):
    store, state, _ = seeded(tmp_path)
    app = compare(inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run()))
    lease = app.session_state["criteria_comparison_export_lease"]
    generation = lease.generation
    app.button[0].click().run()
    assert not app.exception
    assert "Saved criteria revision changes" not in values(app.markdown)
    assert not app.get("download_button")
    assert lease.selection is None and lease.generation > generation
    app = compare(inspect(app))
    changed = store.load(state.review.review_id)
    changed.criteria_revision.source_text += " CONSTRUCTED saved later"
    store.save(changed)
    app.run()
    assert not app.exception and not app.get("download_button")
    assert "Saved criteria revision changes" not in values(app.markdown)
    assert lease.selection is None


def test_requirements_only_legacy_view_does_not_enable_full_history_report(tmp_path):
    from tests.reviews.test_historical_analysis import history_only_state

    state = history_only_state()
    old = state.analysis_history[1]
    old.review.criteria_source_provenance = None
    store, state, _ = seeded(tmp_path, state)
    app = compare(inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run(), index=1))
    assert not app.exception
    assert "Saved criteria revision changes" in values(app.markdown)
    assert "provenance remains unknown" in values(app.markdown)
    labels = [item.label for item in app.get("download_button")]
    assert labels == ["Download criteria changes JSON", "Download criteria changes Markdown"]


@pytest.mark.parametrize("change", ["record", "lease_before", "lease_during"])
def test_deferred_requirements_export_rechecks_record_and_session(tmp_path, change):
    store, state, _, selection, _ = report_for(tmp_path)
    exports = import_module("apps.web.deferred_exports")
    reporting = import_module("scopeproof_core.reporting.criteria_comparison")
    lease = exports.CriteriaComparisonExportLease(selection=selection)

    def render(report):
        if change == "lease_during":
            lease.invalidate()
        return reporting.export_criteria_comparison_json(report)

    callback = exports.deferred_criteria_comparison_export(
        selection, render, store=store, lease=lease,
    )
    if change == "record":
        state.criteria_revision.source_text += " CONSTRUCTED changed"
        store.save(state)
    if change == "lease_before":
        lease.invalidate()
    with pytest.raises(exports.DeferredExportUnavailable):
        callback()


def test_deferred_requirements_export_returns_fresh_validated_json(tmp_path):
    import json

    store, _, _, selection, _ = report_for(tmp_path)
    exports = import_module("apps.web.deferred_exports")
    reporting = import_module("scopeproof_core.reporting.criteria_comparison")
    lease = exports.CriteriaComparisonExportLease(selection=selection)
    callback = exports.deferred_criteria_comparison_export(
        selection, reporting.export_criteria_comparison_json, store=store, lease=lease,
    )
    assert json.loads(callback())["current"]["revision_number"] == 3
