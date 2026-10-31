"""Missing persisted producer identity must never become today's producer."""

import json

import pytest

from scopeproof_core.reporting.historical_analysis import (
    export_historical_json,
    export_historical_markdown,
)
from scopeproof_core.reviews.historical_analysis import (
    HistoricalAnalysisReport,
    locked_historical_analysis,
    prepare_historical_analysis,
)
from scopeproof_core.schemas.models import RULESET_VERSION, Review
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.version import __version__
from tests.reviews.test_historical_analysis import history_only_state
from tests.saved_comparison_fixture import saved_comparison_states


@pytest.mark.parametrize("record_version", range(1, 8))
@pytest.mark.parametrize("missing", [
    ("tool_version",), ("ruleset_version",), ("tool_version", "ruleset_version"),
])
def test_missing_saved_producer_stays_unknown_without_rewriting(tmp_path, record_version, missing):
    state = history_only_state()
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    payload = json.loads(path.read_text())
    payload["record_version"] = record_version
    reviews = [payload["state"]["review"], *[
        item["review"] for item in payload["state"]["analysis_history"]
    ]]
    expected = []
    for review in reviews:
        expected.append({name: "unknown" if name in missing else review[name]
                         for name in ("tool_version", "ruleset_version")})
        for name in missing:
            review.pop(name)
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    loaded = store.load(state.review.review_id)
    for review, identity in zip([loaded.review, *[
        item.review for item in loaded.analysis_history
    ]], expected, strict=True):
        for name, value in identity.items():
            assert getattr(review, name) == value
    with locked_historical_analysis(
        store, prepare_historical_analysis(store, loaded, 1),
    ) as report:
        historical = json.loads(export_historical_json(report))["analysis"]["review"]
        for name, value in expected[-1].items():
            assert historical[name] == value
        assert "unknown" in export_historical_markdown(report)
        assert report.validation_tool_version == __version__
        assert report.validation_ruleset_version == RULESET_VERSION
    assert path.read_bytes() == before


@pytest.mark.parametrize("missing", ["tool_version", "ruleset_version"])
def test_historical_envelope_rejects_omitted_producer_even_if_default_matches(tmp_path, missing):
    state = history_only_state()
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    with locked_historical_analysis(
        store, prepare_historical_analysis(store, state, 1),
    ) as report:
        payload = report.model_dump(mode="json")
    payload["analysis"]["review"].pop(missing)
    with pytest.raises(ValueError, match="producer"):
        HistoricalAnalysisReport.model_validate(payload)


def test_new_review_construction_keeps_current_producer_defaults():
    review = Review(repository="acme/constructed", pr_number=1, base_sha="a", head_sha="b")
    assert review.tool_version == __version__
    assert review.ruleset_version == RULESET_VERSION


def test_missing_active_producer_preserves_other_recorded_producers(tmp_path):
    state, _ = saved_comparison_states()
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    payload = json.loads(path.read_text())
    for name in ("tool_version", "ruleset_version"):
        payload["state"]["bundle"]["review"].pop(name)
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    loaded = store.load(state.review.review_id)
    assert loaded.bundle.review.tool_version == "unknown"
    assert loaded.bundle.review.ruleset_version == "unknown"
    assert loaded.review == state.review
    assert loaded.analysis_history == state.analysis_history
    assert path.read_bytes() == before
