"""Old comparison download callbacks must never outlive either selected record."""

import json
from importlib import import_module
from pathlib import Path

import pytest

from apps.web.deferred_exports import DeferredExportUnavailable
from scopeproof_core.reporting.exporters import export_comparison_json
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.reviews.saved_comparison import prepare_saved_comparison
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from tests.reviews.test_saved_comparison import record_bytes, saved_pair


def callback(store, previous, current):
    api = import_module("apps.web.deferred_exports")
    selection = prepare_saved_comparison(store, current, previous.review.review_id)
    lease = api.SavedComparisonExportLease(selection)
    return lease, api.deferred_saved_comparison_export(
        selection,
        export_comparison_json,
        store=store,
        lease=lease,
    )


def test_deferred_saved_comparison_validates_both_records_and_preserves_saved_bytes(
    tmp_path: Path,
) -> None:
    store, previous, current = saved_pair(tmp_path)
    _, render = callback(store, previous, current)
    before = record_bytes(store)
    result = json.loads(render())
    assert result["previous_head_sha"] == "a" * 40
    assert result["current_head_sha"] == "b" * 40
    assert result["file_scope"]["current"]["unresolved_paths"] == ["src/unrelated.py"]
    assert record_bytes(store) == before


@pytest.mark.parametrize("change", ["current", "baseline", "delete", "selection"])
def test_deferred_saved_comparison_rejects_stale_record_or_selection(
    tmp_path: Path,
    change: str,
) -> None:
    store, previous, current = saved_pair(tmp_path)
    lease, render = callback(store, previous, current)
    if change == "selection":
        lease.selection = None
    elif change == "delete":
        store.delete(previous.review.review_id)
    else:
        target = current if change == "current" else previous
        store.mutate(
            target.review.review_id,
            lambda state: append_resolution(
                state,
                ResolutionEvent(
                    criterion_id="AC-01",
                    decision=HumanDecision.REJECTED_FINDING,
                    reviewer="Constructed reviewer",
                    comment="Changed before download",
                ),
            ),
        )
    before = record_bytes(store)
    with pytest.raises(DeferredExportUnavailable):
        render()
    assert record_bytes(store) == before


def test_selection_change_during_export_rejects_completed_old_render(tmp_path: Path) -> None:
    store, previous, current = saved_pair(tmp_path)
    api = import_module("apps.web.deferred_exports")
    selection = prepare_saved_comparison(store, current, previous.review.review_id)
    lease = api.SavedComparisonExportLease(selection)

    def renderer(comparison):
        lease.selection = None
        return export_comparison_json(comparison)

    render = api.deferred_saved_comparison_export(
        selection,
        renderer,
        store=store,
        lease=lease,
    )
    with pytest.raises(DeferredExportUnavailable):
        render()
