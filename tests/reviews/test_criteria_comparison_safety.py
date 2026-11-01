"""Independent constructed attacks on saved requirements-only comparisons."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from threading import Event

import pytest
from pydantic import ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.schemas.models import (
    Criterion,
    CriterionSource,
    CriterionType,
    EvidenceLevel,
    Priority,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.historical_analysis_fixture import historical_analysis_state
from tests.reviews.test_historical_analysis import history_only_state


def api():
    return import_module("scopeproof_core.reviews.criteria_comparison")


def saved_comparison(tmp_path, *, state=None):
    state = historical_analysis_state() if state is None else state
    store = JsonReviewStore(tmp_path / "records")
    path = store.save(state)
    return store, store.load(state.review.review_id), path


def selected_report(store, state, index=0):
    selection = api().prepare_criteria_comparison(store, state, index)
    with api().locked_criteria_comparison(store, selection) as report:
        return report


def payload(model):
    return model.model_dump(mode="json", round_trip=True)


def test_requirements_report_is_detached_and_cannot_carry_analysis_authority(tmp_path):
    store, state, path = saved_comparison(tmp_path)
    before = state.model_dump_json(), path.read_bytes()
    report = selected_report(store, state)
    assert report.previous.revision_number == 1
    assert report.current.revision_number == 3
    assert report.previous.confirmed is True and report.current.confirmed is False
    assert state.bundle is None
    assert report.current.criteria == state.criteria_revision.criteria
    assert report.previous.criteria == state.analysis_history[0].criteria
    assert report.current.source_text == state.criteria_revision.source_text
    assert not {
        "analysis", "evidence", "evidence_changes", "gate", "previous_gate", "current_gate",
        "resolutions", "runtime_evidence", "final_acceptance",
    } & payload(report).keys()
    report.current.criteria[0].text = "Detached constructed alteration"
    report.previous.criteria.clear()
    assert before == (state.model_dump_json(), path.read_bytes())
    assert store.load(state.review.review_id).model_dump_json() == before[0]


def test_reused_id_reports_every_changed_field_without_inferring_continuity(tmp_path):
    state = historical_analysis_state()
    previous = state.analysis_history[0].criteria[0]
    state.criteria_revision.criteria = [Criterion(
        criterion_id=previous.criterion_id,
        text="Completely unrelated constructed permission requirement",
        priority=Priority.SHOULD_HAVE,
        criterion_type=CriterionType.PERMISSION,
        criterion_source=CriterionSource.IMPLICIT_RULE_PACK,
        source_span="Exact unrelated source span",
        required_evidence_level=EvidenceLevel.E3,
    )]
    store, state, _ = saved_comparison(tmp_path, state=state)
    report = selected_report(store, state)
    assert len(report.criterion_changes) == 1
    change = report.criterion_changes[0]
    assert change.criterion_id == previous.criterion_id
    assert change.kind == "fields_changed"
    assert change.previous == previous
    assert change.current == state.criteria_revision.criteria[0]
    assert change.previous_position == change.current_position == 1
    assert set(change.changed_fields) == {
        "text", "priority", "criterion_type", "criterion_source", "source_span",
        "required_evidence_level",
    }


def test_equal_text_under_different_ids_stays_two_unpaired_records(tmp_path):
    state = historical_analysis_state()
    previous = state.analysis_history[0].criteria[0]
    state.criteria_revision.criteria = [previous.model_copy(update={"criterion_id": "AC-99"})]
    store, state, _ = saved_comparison(tmp_path, state=state)
    changes = {row.criterion_id: row for row in selected_report(store, state).criterion_changes}
    assert set(changes) == {"AC-01", "AC-99"}
    assert changes["AC-01"].kind == "only_previous"
    assert changes["AC-01"].current is None
    assert changes["AC-01"].current_position is None
    assert changes["AC-99"].kind == "only_current"
    assert changes["AC-99"].previous is None
    assert changes["AC-99"].previous_position is None


def test_unknown_historical_revision_and_absent_provenance_are_not_defaulted(tmp_path):
    state = historical_analysis_state()
    old = state.analysis_history[0]
    old.criteria_revision_number = "unknown"
    old.reviewer_selected_references = []
    old.selected_reference_events = []
    old.review.criteria_source_provenance = None
    old.gate = evaluate_gate(
        old.review, old.criteria, old.findings, old.resolutions, old.evidence,
        old.file_scope_decisions,
    )
    store, state, path = saved_comparison(tmp_path, state=state)
    before = path.read_bytes()
    report = selected_report(store, state)
    assert report.previous.revision_number == "unknown"
    assert report.previous.source_provenance is None
    assert report.current.source_provenance is None
    assert report.source_provenance_changed is False
    assert path.read_bytes() == before


def test_empty_unconfirmed_saved_criteria_remain_empty_without_history_fallback(tmp_path):
    state = historical_analysis_state()
    state.criteria_revision.criteria = []
    store, state, _ = saved_comparison(tmp_path, state=state)
    report = selected_report(store, state)
    assert report.current.criteria == []
    assert report.current.confirmed is False
    assert [row.kind for row in report.criterion_changes] == ["only_previous"]


@pytest.mark.parametrize("index", [-1, 1, True, False, "0", 0.0, None])
def test_history_position_is_explicit_and_never_coerced(tmp_path, index):
    store, state, _ = saved_comparison(tmp_path)
    with pytest.raises((ValueError, TypeError)):
        api().prepare_criteria_comparison(store, state, index)


@pytest.mark.parametrize("field", [
    "head_sha", "revision_number", "confirmed", "source_text", "criteria", "source_provenance",
])
def test_snapshot_does_not_supply_missing_recorded_fields(tmp_path, field):
    store, state, _ = saved_comparison(tmp_path)
    data = payload(selected_report(store, state).previous)
    del data[field]
    with pytest.raises(ValidationError):
        api().CriteriaSnapshot.model_validate(data)


@pytest.mark.parametrize("field", [
    "priority", "criterion_type", "criterion_source", "source_span", "required_evidence_level",
])
def test_snapshot_requires_complete_criterion_records_including_default_valued_fields(
    tmp_path, field,
):
    store, state, _ = saved_comparison(tmp_path)
    data = payload(selected_report(store, state).previous)
    del data["criteria"][0][field]
    with pytest.raises(ValidationError):
        api().CriteriaSnapshot.model_validate(data)


@pytest.mark.parametrize("field", [
    "source_uri", "source_revision", "source_text_sha256", "normalized_criteria_sha256",
    "confirmed_by", "confirmed_at",
])
def test_snapshot_requires_complete_recorded_provenance(tmp_path, field):
    store, state, _ = saved_comparison(tmp_path)
    data = payload(selected_report(store, state).previous)
    assert data["source_provenance"] is not None
    del data["source_provenance"][field]
    with pytest.raises(ValidationError):
        api().CriteriaSnapshot.model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("head_sha", ""), ("head_sha", "  "), ("revision_number", True),
    ("revision_number", "1"), ("revision_number", 0), ("confirmed", "false"),
])
def test_snapshot_rejects_unsafe_identity_coercions(tmp_path, field, value):
    store, state, _ = saved_comparison(tmp_path)
    data = payload(selected_report(store, state).current)
    data[field] = value
    with pytest.raises(ValidationError):
        api().CriteriaSnapshot.model_validate(data)


@pytest.mark.parametrize("recorded_head", ["main", "A" * 40])
def test_noncanonical_saved_head_is_preserved_only_as_recorded_context(tmp_path, recorded_head):
    store, state, _ = saved_comparison(tmp_path)
    report = selected_report(store, state)
    data = payload(report.current)
    data["head_sha"] = recorded_head
    snapshot = api().CriteriaSnapshot.model_validate(data)
    assert snapshot.head_sha == recorded_head
    assert "not evidence comparison or current-head verification" in report.boundary


@pytest.mark.parametrize("mutation", ["duplicate_id", "source_digest", "criteria_digest"])
def test_snapshot_rejects_ambiguous_ids_and_mismatched_provenance(tmp_path, mutation):
    store, state, _ = saved_comparison(tmp_path)
    data = payload(selected_report(store, state).previous)
    if mutation == "duplicate_id":
        data["criteria"].append(data["criteria"][0].copy())
    elif mutation == "source_digest":
        data["source_text"] += " Tampered constructed source"
    else:
        data["criteria"][0]["text"] += " Tampered constructed requirement"
    with pytest.raises(ValidationError):
        api().CriteriaSnapshot.model_validate(data)


@pytest.mark.parametrize("field", [
    "historical", "previous_criteria_fingerprint", "current_criteria_fingerprint",
])
def test_selection_requires_all_binding_fields(tmp_path, field):
    store, state, _ = saved_comparison(tmp_path)
    data = payload(api().prepare_criteria_comparison(store, state, 0))
    del data[field]
    with pytest.raises(ValidationError):
        api().CriteriaComparisonSelection.model_validate(data)


@pytest.mark.parametrize("field", [
    "report_kind", "schema_version", "boundary", "selection", "previous", "current",
    "validation_tool_version", "validation_ruleset_version", "validation_source_identity",
])
def test_report_never_generates_missing_envelope_identity(tmp_path, field):
    store, state, _ = saved_comparison(tmp_path)
    data = payload(selected_report(store, state))
    del data[field]
    with pytest.raises(ValidationError):
        api().CriteriaRevisionComparison.model_validate(data)


@pytest.mark.parametrize("envelope", ["snapshot", "selection", "report"])
def test_saved_comparison_contracts_reject_injected_authority_fields(tmp_path, envelope):
    store, state, _ = saved_comparison(tmp_path)
    report = selected_report(store, state)
    value = {
        "snapshot": report.current, "selection": report.selection, "report": report,
    }[envelope]
    data = payload(value)
    data["current_acceptance_verified"] = True
    with pytest.raises(ValidationError):
        type(value).model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("review_id", "../foreign"), ("history_index", True),
    ("analysis_fingerprint", "f" * 64), ("state_fingerprint", "e" * 64),
])
@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning")
def test_nested_selection_instances_are_revalidated_before_locked_use(tmp_path, field, value):
    store, state, path = saved_comparison(tmp_path)
    selection = api().prepare_criteria_comparison(store, state, 0)
    forged = selection.model_copy(update={
        "historical": selection.historical.model_copy(update={field: value}),
    })
    before = path.read_bytes()
    with pytest.raises((ValueError, OSError)), api().locked_criteria_comparison(store, forged):
        pytest.fail("forged nested history identity yielded a comparison")
    assert path.read_bytes() == before


@pytest.mark.parametrize("mutation", ["criteria", "confirmation", "provenance", "selection"])
def test_report_revalidation_rejects_tampered_nested_model_instances(tmp_path, mutation):
    store, state, _ = saved_comparison(tmp_path)
    report = selected_report(store, state)
    if mutation == "criteria":
        report.current.criteria[0].text += " Forged current criterion"
    elif mutation == "confirmation":
        object.__setattr__(report.current, "confirmed", True)
    elif mutation == "provenance":
        object.__setattr__(report.previous.source_provenance, "confirmed_by", "Forged actor")
    else:
        object.__setattr__(report.selection, "current_criteria_fingerprint", "a" * 64)
    with pytest.raises(ValidationError):
        api().CriteriaRevisionComparison.model_validate(report)


@pytest.mark.parametrize("mutation", ["source", "criterion", "revision", "history", "unselected"])
def test_receipt_binds_complete_saved_state_and_current_only_edits(tmp_path, mutation):
    store, state, path = saved_comparison(tmp_path, state=history_only_state())
    selection = api().prepare_criteria_comparison(store, state, 1)
    if mutation == "source":
        state.criteria_revision.source_text += " Saved source-only edit"
    elif mutation == "criterion":
        state.criteria_revision.criteria[0].text += " Saved criteria-only edit"
    elif mutation == "revision":
        state.criteria_revision.number += 1
    elif mutation == "history":
        state.analysis_history.reverse()
    else:
        state.analysis_history[0].review.tool_version = "constructed-unselected-change"
    if mutation == "history":
        # Simulate corrupt persisted ordering without asking the writer to bypass chronology.
        data = json.loads(path.read_bytes())
        data["state"] = state.model_dump(mode="json")
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        store.save(state)
    before = path.read_bytes()
    with pytest.raises(ValueError), api().locked_criteria_comparison(store, selection):
        pytest.fail("stale saved-state receipt yielded a comparison")
    assert path.read_bytes() == before


def test_unsaved_current_state_cannot_select_a_saved_comparison(tmp_path):
    store, state, path = saved_comparison(tmp_path)
    before = path.read_bytes()
    state.criteria_revision.source_text += " Unsaved draft"
    with pytest.raises(ValueError):
        api().prepare_criteria_comparison(store, state, 0)
    assert path.read_bytes() == before


@pytest.mark.parametrize("damage", ["delete", "corrupt", "owner", "symlink"])
def test_deleted_or_retargeted_record_fails_without_fallback(tmp_path, damage):
    store, state, path = saved_comparison(tmp_path)
    selection = api().prepare_criteria_comparison(store, state, 0)
    original = path.read_bytes()
    if damage == "delete":
        path.unlink()
    elif damage == "corrupt":
        path.write_text("{damaged record", encoding="utf-8")
    elif damage == "owner":
        data = json.loads(original)
        data["state"]["review"]["review_id"] = "constructed-other-owner"
        for historical in data["state"]["analysis_history"]:
            historical["review"]["review_id"] = "constructed-other-owner"
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        target = tmp_path / "constructed-retarget.json"
        target.write_bytes(original)
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            pytest.skip("symbolic links unavailable on this platform")
    with pytest.raises((OSError, ValueError)), api().locked_criteria_comparison(store, selection):
        pytest.fail("unavailable or retargeted record yielded a comparison")
    if damage == "symlink":
        assert target.read_bytes() == original


def test_comparison_retains_record_lock_through_consumer(tmp_path):
    store, state, _ = saved_comparison(tmp_path)
    selection = api().prepare_criteria_comparison(store, state, 0)
    entered, release, started, finished = Event(), Event(), Event(), Event()

    def consume():
        with api().locked_criteria_comparison(store, selection) as report:
            entered.set()
            assert release.wait(5)
            return report.current.source_text

    def mutate():
        started.set()
        changed = state.model_copy(deep=True)
        changed.criteria_revision.source_text += " Concurrent saved mutation"
        store.save(changed)
        finished.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        consumer = pool.submit(consume)
        assert entered.wait(5)
        writer = pool.submit(mutate)
        try:
            assert started.wait(5)
            assert not finished.wait(0.1)
        finally:
            release.set()
        assert consumer.result(5) == state.criteria_revision.source_text
        writer.result(5)


def test_source_text_and_recorded_artifact_never_trigger_network_or_execution(
    tmp_path, monkeypatch,
):
    state = historical_analysis_state()
    state.criteria_revision.source_text = (
        "https://example.invalid/untrusted.py\n"
        "__import__('os').system('must never execute')\n"
        "<img src=x onerror=untrusted()>"
    )
    state.analysis_history[0].runtime_evidence[0].artifact_reference = (
        "https://example.invalid/untrusted-runtime.py"
    )
    store, state, path = saved_comparison(tmp_path, state=state)
    before = state.model_dump_json(), path.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Requirements comparison fetched or executed untrusted input")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    report = selected_report(store, state)
    assert report.current.source_text == state.criteria_revision.source_text
    assert before == (state.model_dump_json(), path.read_bytes())
