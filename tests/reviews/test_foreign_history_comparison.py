"""Constructed foreign-history characterization and expected-receipt race regressions."""

from pathlib import Path

import pytest
from pydantic import ValidationError

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
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_saved_comparison import record_bytes
from tests.saved_comparison_fixture import (
    HISTORY_HEAD,
    PREVIOUS_HEAD,
    PREVIOUS_REVIEW_ID,
    _constructed_state,
    saved_comparison_states,
)


def foreign_pair(tmp_path: Path):
    current, _ = saved_comparison_states(selected_references=True)
    baseline = _constructed_state(
        PREVIOUS_REVIEW_ID, PREVIOUS_HEAD, added_path=False, revision_number=3,
        selected_context="foreign-active",
    )
    historical = _constructed_state(
        PREVIOUS_REVIEW_ID, HISTORY_HEAD, added_path=False,
        selected_context="foreign-historical",
    )
    baseline.analysis_history = [historical.bundle]
    baseline = ReviewState.model_validate(baseline.model_dump(mode="python"))
    store = JsonReviewStore(tmp_path)
    store.save(current)
    store.save(baseline)
    return store, current, baseline


def incompatible_active(state):
    """Keep a valid record whose active source differs from its retained history."""
    # These callers use a record without selected references on the active analysis.
    state.bundle.reviewer_selected_references = []
    provenance = state.review.criteria_source_provenance.model_copy(update={
        "source_uri": "https://example.test/constructed-incompatible-source",
    })
    state.review.criteria_source_provenance = provenance
    state.bundle.review.criteria_source_provenance = provenance
    state.criteria_revision.source_provenance = provenance
    return ReviewState.model_validate(state.model_dump(mode="python"))


@pytest.mark.parametrize("active_state", ["compatible", "missing", "incompatible"])
def test_baseline_characterization_foreign_history_is_independent_of_active(
    tmp_path: Path, active_state: str,
) -> None:
    store, current, baseline = foreign_pair(tmp_path)
    if active_state == "missing":
        baseline.bundle = None
    elif active_state == "incompatible":
        baseline = incompatible_active(baseline)
    store.save(baseline)
    before = record_bytes(store)
    selection = prepare_saved_comparison(
        store, current, PREVIOUS_REVIEW_ID, history_index=0,
    )
    with locked_saved_comparison(store, selection) as result:
        assert result.previous_head_sha == HISTORY_HEAD
        assert result.file_scope.previous.criteria_revision_number == 1
        assert result.selected_reference_comparison.previous[0].reviewer == (
            "Constructed foreign-historical reference reviewer"
        )
    assert selection.baseline_review_id == PREVIOUS_REVIEW_ID
    assert record_bytes(store) == before


def test_baseline_characterization_incompatible_history_rejects_compatible_active(
    tmp_path: Path,
) -> None:
    store, current, baseline = foreign_pair(tmp_path)
    historical_state = _constructed_state(
        PREVIOUS_REVIEW_ID, HISTORY_HEAD, added_path=False,
    )
    baseline.analysis_history = [incompatible_active(historical_state).bundle]
    store.save(baseline)
    before = record_bytes(store)
    active = prepare_saved_comparison(store, current, PREVIOUS_REVIEW_ID)
    assert active.history_index is None
    with pytest.raises(ValueError, match="criteria-source provenance"):
        prepare_saved_comparison(store, current, PREVIOUS_REVIEW_ID, history_index=0)
    assert record_bytes(store) == before


def test_expected_receipt_accepts_displayed_foreign_history(tmp_path: Path) -> None:
    store, current, baseline = foreign_pair(tmp_path)
    before = record_bytes(store)
    selection = prepare_saved_comparison(
        store, current, PREVIOUS_REVIEW_ID, history_index=0,
        expected_baseline_fingerprint=store.state_fingerprint(baseline),
    )
    with locked_saved_comparison(store, selection) as result:
        assert result.previous_head_sha == HISTORY_HEAD
    assert record_bytes(store) == before


@pytest.mark.parametrize("receipt", ["invalid", "A" * 64, True, 7])
def test_invalid_expected_receipt_rejects_through_schema(
    tmp_path: Path, receipt,
) -> None:
    store, current, _ = foreign_pair(tmp_path)
    before = record_bytes(store)
    with pytest.raises(ValidationError):
        prepare_saved_comparison(
            store, current, PREVIOUS_REVIEW_ID, history_index=0,
            expected_baseline_fingerprint=receipt,
        )
    assert record_bytes(store) == before


@pytest.mark.parametrize("change", ["replacement", "removal", "reference", "reorder"])
def test_discovered_receipt_rejects_changed_foreign_record_before_index_resolution(
    tmp_path: Path, change: str,
) -> None:
    store, current, baseline = foreign_pair(tmp_path)
    if change == "reorder":
        baseline = with_reorderable_history(baseline)
        store.save(baseline)
    receipt = store.state_fingerprint(baseline)
    store.mutate(PREVIOUS_REVIEW_ID, lambda state: change_history(state, change))
    before = record_bytes(store)
    with pytest.raises(SavedComparisonUnavailable):
        prepare_saved_comparison(
            store, current, PREVIOUS_REVIEW_ID, history_index=0,
            expected_baseline_fingerprint=receipt,
        )
    assert record_bytes(store) == before


def with_reorderable_history(state):
    second = _constructed_state(
        PREVIOUS_REVIEW_ID, "f" * 40, added_path=False,
        selected_context="foreign-second-historical",
    ).bundle
    state.analysis_history.append(second)
    for historical in state.analysis_history:
        historical.criteria_revision_number = "unknown"
        historical.reviewer_selected_references = []
    return ReviewState.model_validate(state.model_dump(mode="python"))


def change_history(state, change):
    if change == "replacement":
        state.analysis_history[0] = _constructed_state(
            PREVIOUS_REVIEW_ID, "e" * 40, added_path=False,
            selected_context="foreign-replacement-historical",
        ).bundle
    elif change == "removal":
        state.analysis_history.clear()
    elif change == "reference":
        reference = state.analysis_history[0].reviewer_selected_references[0]
        state.analysis_history[0].reviewer_selected_references[0] = reference.model_copy(
            update={"rationale": "Constructed changed historical context; no execution evidence."},
        )
    else:
        assert change == "reorder"
        state.analysis_history.reverse()
    return ReviewState.model_validate(state.model_dump(mode="python"))


@pytest.mark.parametrize("change", ["replacement", "removal", "reference", "reorder"])
def test_baseline_characterization_changed_foreign_history_expires_applied_and_download(
    tmp_path: Path, change: str,
) -> None:
    store, current, baseline = foreign_pair(tmp_path)
    if change == "reorder":
        baseline = with_reorderable_history(baseline)
        store.save(baseline)
    selection = prepare_saved_comparison(
        store, current, PREVIOUS_REVIEW_ID, history_index=0,
    )
    download = deferred_saved_comparison_export(
        selection, export_comparison_json, store=store,
        lease=SavedComparisonExportLease(selection),
    )
    assert HISTORY_HEAD in download()
    store.mutate(PREVIOUS_REVIEW_ID, lambda state: change_history(state, change))
    before = record_bytes(store)
    with pytest.raises(SavedComparisonUnavailable), locked_saved_comparison(store, selection):
        pytest.fail("changed foreign history yielded an applied comparison")
    with pytest.raises(DeferredExportUnavailable):
        download()
    assert record_bytes(store) == before
