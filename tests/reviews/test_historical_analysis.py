"""Historical inspection is explicit and never replaces current authority."""

from importlib import import_module

import pytest

from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import Criterion
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.saved_comparison_fixture import saved_comparison_states


def api():
    return import_module("scopeproof_core.reviews.historical_analysis")


def history_only_state():
    current, _ = saved_comparison_states()
    return revise_criteria(
        current, [Criterion(criterion_id="AC-99", text="Constructed new requirement")],
        "Constructed new requirement",
    )


def test_history_only_report_preserves_complete_source_and_current_state(tmp_path):
    state = history_only_state()
    assert state.bundle is None and not state.criteria_revision.confirmed
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    before = state.model_dump_json(), path.read_bytes()
    selection = api().prepare_historical_analysis(store, state, 1)
    assert selection.state_fingerprint == store.state_fingerprint(state)
    assert selection.history_index == 1
    with api().locked_historical_analysis(store, selection) as report:
        assert report.report_kind == "scopeproof_historical_analysis"
        assert report.analysis == state.analysis_history[1]
        assert report.analysis.criteria_revision_number == 2
        assert report.analysis.review.head_sha == state.analysis_history[1].review.head_sha
        report.analysis.source_text = "Constructed detached change"
    assert before == (state.model_dump_json(), path.read_bytes())


def test_historical_unknown_revision_and_original_producer_are_not_defaulted(tmp_path):
    state = history_only_state()
    state.analysis_history[1].criteria_revision_number = "unknown"
    state.analysis_history[1].review.tool_version = "constructed-old-producer"
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    with api().locked_historical_analysis(
        store, api().prepare_historical_analysis(store, state, 1),
    ) as report:
        assert report.analysis.criteria_revision_number == "unknown"
        assert report.analysis.review.tool_version == "constructed-old-producer"
        assert report.validation_tool_version == "0.2.5"
        assert report.analysis.review.analysis_source_identity is not None


@pytest.mark.parametrize("index", [-1, True, 1.0, "1", None, 2, 999])
def test_invalid_or_absent_history_position_never_falls_back(tmp_path, index):
    state = history_only_state()
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    with pytest.raises(ValueError):
        api().prepare_historical_analysis(store, state, index)


def test_changed_record_blocks_prepare_and_previous_report_receipt(tmp_path):
    state = history_only_state()
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    selection = api().prepare_historical_analysis(store, state, 1)
    changed = state.model_copy(deep=True)
    changed.criteria_revision.source_text += " changed"
    store.save(changed)
    with pytest.raises(ValueError):
        api().prepare_historical_analysis(store, state, 1)
    with pytest.raises(ValueError), api().locked_historical_analysis(store, selection):
        pytest.fail("stale history must be unavailable")
