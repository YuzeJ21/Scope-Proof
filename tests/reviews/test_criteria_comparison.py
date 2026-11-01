"""Requirements changes are recorded facts, never cross-revision acceptance."""

from importlib import import_module

import pytest

from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import Criterion, EvidenceLevel, Priority
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.historical_analysis_fixture import historical_analysis_state


def api():
    return import_module("scopeproof_core.reviews.criteria_comparison")


def report_for(tmp_path, state=None):
    state = state or historical_analysis_state()
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    selection = api().prepare_criteria_comparison(store, state, 0)
    with api().locked_criteria_comparison(store, selection) as report:
        return store, state, path, selection, report


def test_pending_saved_revision_compares_without_creating_analysis_or_confirmation(tmp_path):
    store, state, path, selection, report = report_for(tmp_path)
    before = path.read_bytes(), state.model_dump_json()
    assert report.previous.revision_number == 1
    assert report.current.revision_number == 3
    assert report.previous.confirmed is True and report.current.confirmed is False
    assert report.previous.criteria[0].text == "CONSTRUCTED export CSV"
    assert report.current.criteria[0].text == (
        "CONSTRUCTED changed requirement: export JSON instead of CSV"
    )
    assert report.source_text_changed
    assert report.source_provenance_changed
    assert selection.historical.state_fingerprint == store.state_fingerprint(state)
    assert state.bundle is None and not state.review.criteria_confirmed
    assert before == (path.read_bytes(), state.model_dump_json())


def test_added_removed_and_same_key_field_changes_are_literal_records(tmp_path):
    state = historical_analysis_state()
    previous = state.analysis_history[0].criteria[0]
    state = revise_criteria(state, [
        Criterion(criterion_id="AC-02", text=previous.text),
        Criterion(criterion_id="AC-01", text="Entirely different constructed requirement",
                  priority=Priority.SHOULD_HAVE, required_evidence_level=EvidenceLevel.E4),
    ], "Constructed changed source")
    _, _, _, _, report = report_for(tmp_path, state)
    rows = report.criterion_changes
    assert [r.criterion_id for r in rows] == ["AC-01", "AC-02"]
    assert rows[0].kind == "fields_changed"
    assert rows[0].changed_fields == ["priority", "required_evidence_level", "text"]
    assert (rows[0].previous_position, rows[0].current_position) == (1, 2)
    assert rows[1].kind == "only_current"
    state = revise_criteria(state, [Criterion(criterion_id="AC-99", text=previous.text)],
                            previous.text)
    _, _, _, _, report = report_for(tmp_path / "removed", state)
    assert [(r.criterion_id, r.kind) for r in report.criterion_changes] == [
        ("AC-01", "only_previous"), ("AC-99", "only_current"),
    ]


def test_order_only_and_identical_recorded_requirements_are_distinct(tmp_path):
    state = historical_analysis_state()
    old = state.analysis_history[0]
    state = revise_criteria(state, old.criteria, old.source_text)
    _, _, _, _, report = report_for(tmp_path, state)
    assert [r.kind for r in report.criterion_changes] == ["identical"]
    assert report.criterion_changes[0].changed_fields == []
    assert not report.source_text_changed and not report.criterion_order_changed
    # A second criterion can be added to both snapshots without adding evidence authority.
    from scopeproof_core.gates.evaluator import evaluate_gate
    from scopeproof_core.schemas.models import ConfidenceBand, Finding, FindingStatus

    second = Criterion(criterion_id="AC-02", text="Constructed second requirement")
    old = state.analysis_history[0]
    old.criteria.append(second)
    old.findings.append(Finding(
        criterion_id="AC-02", status=FindingStatus.MISSING,
        evidence_level=EvidenceLevel.E0, confidence_band=ConfidenceBand.LOW,
        reason="Constructed missing evidence", missing_evidence=["Not provided"],
        recommended_action="Review the constructed requirement",
    ))
    old.retrieval_diagnostics = []
    old.reviewer_selected_references = []
    old.selected_reference_events = []
    old.review.criteria_source_provenance = None
    old.gate = evaluate_gate(old.review, old.criteria, old.findings, old.resolutions, old.evidence)
    state = revise_criteria(state, list(reversed(old.criteria)), old.source_text)
    _, _, _, _, report = report_for(tmp_path / "ordered", state)
    assert report.criterion_order_changed
    assert [r.kind for r in report.criterion_changes] == ["identical", "identical"]
    assert [(r.previous_position, r.current_position) for r in report.criterion_changes] == [
        (1, 2), (2, 1),
    ]


@pytest.mark.parametrize("index", [-1, True, 1.0, "0", 999])
def test_invalid_history_selection_never_defaults(tmp_path, index):
    state = historical_analysis_state()
    store = JsonReviewStore(tmp_path)
    store.save(state)
    with pytest.raises(ValueError):
        api().prepare_criteria_comparison(store, state, index)


def test_current_only_edit_rejects_prepared_selection(tmp_path):
    store, state, _, selection, _ = report_for(tmp_path)
    changed = state.model_copy(deep=True)
    changed.criteria_revision.source_text += " CONSTRUCTED later change"
    store.save(changed)
    with pytest.raises(ValueError), api().locked_criteria_comparison(store, selection):
        pytest.fail("stale current revision must not render")
    with pytest.raises(ValueError):
        api().prepare_criteria_comparison(store, state, 0)


def test_report_rejects_mutated_snapshot_and_non_recorded_defaults(tmp_path):
    _, _, _, _, report = report_for(tmp_path)
    report.current.criteria[0].text = "Tampered requirement"
    with pytest.raises(ValueError):
        api().CriteriaRevisionComparison.model_validate(report.model_dump(mode="python"))
    _, _, _, _, report = report_for(tmp_path / "fresh")
    payload = report.model_dump(mode="python")
    del payload["previous"]["criteria"][0]["priority"]
    with pytest.raises(ValueError):
        api().CriteriaRevisionComparison.model_validate(payload)
