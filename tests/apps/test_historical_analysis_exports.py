"""Historical callbacks reload saved truth and cannot survive invalid leases."""

from importlib import import_module

import pytest

from scopeproof_core.reporting.historical_analysis import export_historical_json
from scopeproof_core.reviews.historical_analysis import prepare_historical_analysis
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.historical_analysis_fixture import historical_analysis_state


def deferred():
    return import_module("apps.web.deferred_exports")


def setup_callback(tmp_path):
    state = historical_analysis_state()
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    selection = prepare_historical_analysis(store, state, 0)
    lease = deferred().HistoricalAnalysisExportLease(selection=selection)
    callback = deferred().deferred_historical_export(
        selection, export_historical_json, store=store, lease=lease,
    )
    return state, store, selection, lease, callback


def test_historical_download_is_explicit_and_rejects_whole_record_changes(tmp_path):
    state, store, _, _, callback = setup_callback(tmp_path)
    assert '"scopeproof_historical_analysis"' in callback()
    state.criteria_revision.source_text += " Constructed changed pending source"
    store.save(state)
    with pytest.raises(deferred().DeferredExportUnavailable):
        callback()


def test_historical_lease_invalidation_blocks_before_reading_old_store(tmp_path, monkeypatch):
    _, store, _, lease, callback = setup_callback(tmp_path)
    lease.invalidate()

    def forbidden(*args, **kwargs):
        pytest.fail("expired lease must fail before touching the old record")

    monkeypatch.setattr(store, "locked_load", forbidden)
    with pytest.raises(deferred().DeferredExportUnavailable):
        callback()


def test_historical_lease_is_checked_again_after_renderer(tmp_path):
    _, store, selection, lease, _ = setup_callback(tmp_path)

    def changed_while_rendering(report):
        lease.invalidate()
        return export_historical_json(report)

    callback = deferred().deferred_historical_export(
        selection, changed_while_rendering, store=store, lease=lease,
    )
    with pytest.raises(deferred().DeferredExportUnavailable):
        callback()
