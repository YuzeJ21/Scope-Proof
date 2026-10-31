"""Historical handoff has its own scope, identity and export eligibility."""

import json
from importlib import import_module

import pytest

from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_historical_analysis import api, history_only_state


def renderers():
    return import_module("scopeproof_core.reporting.historical_analysis")


@pytest.mark.parametrize("revision", [2, "unknown"])
def test_historical_json_markdown_keep_revision_data_and_policy_scope(tmp_path, revision):
    state = history_only_state()
    state.analysis_history[1].criteria_revision_number = revision
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    before = path.read_bytes()
    with api().locked_historical_analysis(
        store, api().prepare_historical_analysis(store, state, 1),
    ) as report:
        data = json.loads(renderers().export_historical_json(report))
        assert data["analysis"] == state.analysis_history[1].model_dump(mode="json")
        assert data["report_kind"] == "scopeproof_historical_analysis"
        assert data["selection"]["history_index"] == 1
        assert data["analysis"]["criteria_revision_number"] == revision
        markdown = renderers().export_historical_markdown(report)
        assert markdown.startswith("# ScopeProof Historical Analysis")
        assert f"Criteria revision: {revision}" in markdown
        assert "Historical review status (installed policy)" in markdown
        assert "not current-head verification" in markdown
        assert state.analysis_history[1].review.head_sha in markdown
        assert "## Criteria Source" in markdown and "## Evidence" in markdown
        assert "# ScopeProof Acceptance Review" not in markdown
    assert path.read_bytes() == before


def test_missing_legacy_source_provenance_still_blocks_both_report_downloads(tmp_path):
    state = history_only_state()
    state.analysis_history[1].review.criteria_source_provenance = None
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    with api().locked_historical_analysis(
        store, api().prepare_historical_analysis(store, state, 1),
    ) as report:
        assert report.analysis.review.criteria_source_provenance is None
        for renderer in (
            renderers().export_historical_json, renderers().export_historical_markdown,
        ):
            with pytest.raises(ValueError, match="provenance"):
                renderer(report)


def test_mutated_report_cannot_export_changed_historical_facts(tmp_path):
    state = history_only_state()
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    with api().locked_historical_analysis(
        store, api().prepare_historical_analysis(store, state, 1),
    ) as report:
        report.analysis.review.tool_version = "forged historical producer"
        for renderer in (
            renderers().export_historical_json, renderers().export_historical_markdown,
        ):
            with pytest.raises(ValueError):
                renderer(report)
