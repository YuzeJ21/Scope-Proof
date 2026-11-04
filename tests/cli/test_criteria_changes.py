"""CONSTRUCTED requirements handoff; no criteria confirmation or evidence equivalence."""

import json

import pytest

from scopeproof_core.cli import main
from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.version import __version__
from tests.historical_analysis_fixture import historical_analysis_state


def saved(tmp_path, state=None):
    state = historical_analysis_state() if state is None else state
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    return state, store, path


def args(state, store, *, position="1"):
    return ["export-criteria-changes", state.review.review_id,
            "--history-position", position,
            "--expected-state-fingerprint", store.state_fingerprint(state),
            "--storage-dir", str(store.directory)]


def test_pending_requirements_json_preserves_exact_source_and_complete_fields(tmp_path, capsys):
    state = historical_analysis_state()
    state.criteria_revision.source_text = "  CONSTRUCTED saved\r\n\tcriterion\u2028text  \n"
    state, store, path = saved(tmp_path, state)
    before = path.read_bytes()
    assert state.bundle is None and not state.criteria_revision.confirmed
    assert main(args(state, store)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["report_kind"] == "scopeproof_criteria_revision_comparison"
    assert report["previous"]["revision_number"] == 1
    assert report["current"]["revision_number"] == 3
    assert report["current"]["confirmed"] is False
    assert report["previous"]["source_text"] == "CONSTRUCTED export CSV"
    assert report["current"]["source_text"] == "  CONSTRUCTED saved\r\n\tcriterion\u2028text  \n"
    assert report["previous"]["criteria"] == [
        item.model_dump(mode="json") for item in state.analysis_history[0].criteria
    ]
    assert report["current"]["criteria"] == [
        item.model_dump(mode="json") for item in state.criteria_revision.criteria
    ]
    assert report["selection"]["historical"]["history_index"] == 0
    assert report["selection"]["historical"]["state_fingerprint"] == store.state_fingerprint(state)
    assert report["validation_tool_version"] == __version__
    assert "not evidence comparison" in report["boundary"]
    assert "gate" not in report and "evidence" not in report and "resolutions" not in report
    assert {row["kind"] for row in report["criterion_changes"]} == {"only_previous", "only_current"}
    assert path.read_bytes() == before


@pytest.mark.parametrize("format", ["json", "markdown"])
def test_requirements_stdout_and_atomic_file_are_identical(tmp_path, capsys, format):
    state, store, path = saved(tmp_path)
    before = path.read_bytes()
    command = [*args(state, store), "--format", format]
    assert main(command) == 0
    output = capsys.readouterr().out
    if format == "markdown":
        assert output.startswith("# ScopeProof Criteria Revision Changes\n")
        assert "Unconfirmed" in output
        assert "No evidence or decision is carried forward" in output
    target = tmp_path / "criteria-report.txt"
    assert main([*command, "--output", str(target)]) == 0
    assert capsys.readouterr().out == ""
    assert target.read_text(encoding="utf-8") == output
    assert path.read_bytes() == before


def test_unknown_provenance_is_requirements_only_and_never_relaxes_acceptance(tmp_path, capsys):
    state = historical_analysis_state()
    state.analysis_history[0].review.criteria_source_provenance = None
    state.analysis_history[0].reviewer_selected_references = []
    state.analysis_history[0].selected_reference_events = []
    # Construct a consistent hypothetical legacy input before its first save; never rewrite history.
    old = state.analysis_history[0]
    old.gate = evaluate_gate(old.review, old.criteria, old.findings, old.resolutions,
                             old.evidence, old.file_scope_decisions)
    state, store, path = saved(tmp_path, state)
    before = path.read_bytes()
    command = args(state, store)
    assert main(command) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["previous"]["source_provenance"] is None
    assert report["current"]["source_provenance"] is None
    assert report["current"]["confirmed"] is False
    command[0] = "export-history"
    with pytest.raises(SystemExit) as error:
        main(command)
    assert error.value.code == 2
    assert capsys.readouterr().out == ""
    assert path.read_bytes() == before


def test_duplicate_heads_use_exact_position_and_keep_unknown_revision(tmp_path, capsys):
    state = historical_analysis_state()
    other = state.analysis_history[0].model_copy(deep=True)
    other.criteria_revision_number = "unknown"
    other.reviewer_selected_references = []
    other.selected_reference_events = []
    state.analysis_history.append(other)
    state, store, path = saved(tmp_path, state)
    before = path.read_bytes()
    assert main(args(state, store, position="2")) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["selection"]["historical"]["history_index"] == 1
    assert report["previous"]["revision_number"] == "unknown"
    assert report["current"]["revision_number"] == 3
    assert report["previous"]["head_sha"] == "f" * 40
    assert path.read_bytes() == before


def test_no_history_does_not_fall_back_to_active_analysis(tmp_path, capsys):
    state, store, path = saved(tmp_path, new_review_state(build_demo_review()))
    before = path.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(args(state, store))
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == "" and "invalid choice" not in output.err
    assert path.read_bytes() == before
