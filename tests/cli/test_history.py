"""CONSTRUCTED saved-history handoff; removing explicit selection must break these tests."""

import json
from importlib import import_module

import pytest

from scopeproof_core.cli import main
from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.version import __version__
from tests.historical_analysis_fixture import HISTORICAL_PRODUCER_VERSION, historical_analysis_state


def saved(tmp_path):
    state = historical_analysis_state()
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    return state, store, path


def test_catalog_pending_record_is_metadata_only_and_preserves_bytes(tmp_path, capsys):
    state, store, path = saved(tmp_path)
    before = path.read_bytes()
    assert main(["history", state.review.review_id, "--storage-dir", str(store.directory)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["report_kind"] == "scopeproof_retained_analysis_catalog"
    assert data["review_id"] == state.review.review_id
    assert data["repository"] == "acme/constructed-history"
    assert data["pr_number"] == 17
    assert data["state_fingerprint"] == store.state_fingerprint(state)
    assert data["current_criteria_revision_number"] == 3
    assert data["current_criteria_confirmed"] is False
    assert data["has_active_analysis"] is False
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["history_position"] == 1
    assert entry["head_sha"] == "f" * 40
    assert entry["criteria_revision_number"] == 1
    assert entry["tool_version"] == HISTORICAL_PRODUCER_VERSION
    assert len(entry["analysis_fingerprint"]) == 64
    assert "findings" not in entry and "review_status" not in entry
    assert "not current-head verification" in data["boundary"]
    assert path.read_bytes() == before


def test_catalog_empty_history_has_no_implicit_active_entry(tmp_path, capsys):
    state = new_review_state(build_demo_review())
    store = JsonReviewStore(tmp_path)
    store.save(state)
    main(["history", state.review.review_id, "--storage-dir", str(tmp_path)])
    data = json.loads(capsys.readouterr().out)
    assert data["entries"] == [] and data["has_active_analysis"] is True


def test_catalog_preserves_duplicate_heads_and_unknown_revision(tmp_path, capsys):
    state, store, _ = saved(tmp_path)
    second = state.analysis_history[0].model_copy(deep=True)
    second.criteria_revision_number = "unknown"
    second.review.tool_version = "CONSTRUCTED legacy producer"
    second.review.analysis_source_identity = None
    second.reviewer_selected_references = []
    second.selected_reference_events = []
    state.analysis_history.append(second)
    store.save(state)
    main(["history", state.review.review_id, "--storage-dir", str(store.directory)])
    entries = json.loads(capsys.readouterr().out)["entries"]
    assert [row["history_position"] for row in entries] == [1, 2]
    assert entries[0]["head_sha"] == entries[1]["head_sha"]
    assert entries[1]["criteria_revision_number"] == "unknown"
    assert entries[1]["analysis_source_identity"] is None
    assert entries[0]["analysis_fingerprint"] != entries[1]["analysis_fingerprint"]


@pytest.mark.parametrize("report_format", ["json", "markdown"])
def test_export_history_stdout_and_file_preserve_record(tmp_path, capsys, report_format):
    state, store, path = saved(tmp_path)
    before = path.read_bytes()
    args = ["export-history", state.review.review_id, "--history-position", "1",
            "--expected-state-fingerprint", store.state_fingerprint(state),
            "--storage-dir", str(store.directory), "--format", report_format]
    assert main(args) == 0
    output = capsys.readouterr().out
    if report_format == "json":
        data = json.loads(output)
        assert data["report_kind"] == "scopeproof_historical_analysis"
        assert data["selection"]["history_index"] == 0
        assert data["analysis"]["criteria_revision_number"] == 1
        assert data["analysis"]["review"]["tool_version"] == HISTORICAL_PRODUCER_VERSION
        assert data["validation_tool_version"] == __version__
    else:
        assert output.startswith("# ScopeProof Historical Analysis\n")
        assert "Retained history position: 1" in output
        assert "not current-head verification or acceptance" in output
    target = tmp_path / "report.txt"
    assert main([*args, "--output", str(target)]) == 0
    assert capsys.readouterr().out == ""
    assert target.read_text(encoding="utf-8") == output
    assert path.read_bytes() == before


@pytest.mark.parametrize("position", ["0", "-1", "2", "true", "1.0"])
def test_export_invalid_position_no_fallback(tmp_path, capsys, position):
    state, store, _ = saved(tmp_path)
    with pytest.raises(SystemExit) as error:
        main(["export-history", state.review.review_id, "--history-position", position,
              "--expected-state-fingerprint", store.state_fingerprint(state),
              "--storage-dir", str(store.directory)])
    assert error.value.code == 2
    assert capsys.readouterr().out == ""


def test_catalog_and_request_revalidate_constructed_instances(tmp_path):
    state, _, _ = saved(tmp_path)
    api = import_module("scopeproof_core.reviews.history_catalog")
    report = api.build_history_catalog(state)
    data = report.model_dump(mode="python")
    data["entries"][0]["history_position"] = 2
    with pytest.raises(ValueError):
        api.RetainedAnalysisCatalog.model_validate(data)
    request = api.HistoricalExportRequest(
        review_id=state.review.review_id, history_position=1,
        expected_state_fingerprint="a" * 64,
    )
    for updates in ({"history_position": True}, {"history_position": "1"},
                    {"expected_state_fingerprint": "A" * 64}):
        with pytest.raises(ValueError):
            api.HistoricalExportRequest.model_validate(request.model_copy(update=updates))
