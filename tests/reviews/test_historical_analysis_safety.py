"""Independent constructed attacks on retained-analysis authority and freshness."""

from __future__ import annotations

import builtins
import io
import json
import os
import socket
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from importlib import import_module
from threading import Event

import pytest
from pydantic import ValidationError

from scopeproof_core.build_identity import CoreSourceIdentity
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    append_runtime_evidence,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    Criterion,
    EvidenceLevel,
    HumanDecision,
    ResolutionEvent,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_reference_audit import withdraw
from tests.reviews.test_selected_references import append, source_state

RECORDED_AT = datetime(2026, 10, 31, 12, tzinfo=UTC)


def api():
    return import_module("scopeproof_core.reviews.historical_analysis")


def renderers():
    module = import_module("scopeproof_core.reporting.historical_analysis")
    return module.export_historical_json, module.export_historical_markdown


def saved_history(tmp_path):
    """Real lifecycle, synthetic actors; no qualifying human review or target run."""
    state, snapshot = source_state()
    state = withdraw(append(state, snapshot))
    criterion_id = state.bundle.criteria[0].criterion_id
    state = append_runtime_evidence(state, RuntimeEvidence(
        runtime_evidence_id="constructed-history-runtime",
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criterion_id=criterion_id,
        artifact_reference="https://example.test/constructed/history-observation",
        scenario="Constructed historical observation; no target execution",
        timestamp=RECORDED_AT,
        environment="Constructed fixture",
        result="Recorded synthetic result",
        reviewer="Constructed automated actor",
        evidence_level=EvidenceLevel.E3,
        limitations=["Synthetic observation; not independent runtime verification."],
    ))
    state = append_resolution(state, ResolutionEvent(
        criterion_id=criterion_id,
        decision=HumanDecision.REJECTED_FINDING,
        comment="Constructed retained resolution",
        reviewer="Constructed automated actor",
        timestamp=RECORDED_AT,
    ))
    state = revise_criteria(
        state,
        [Criterion(criterion_id="AC-98", text="Different pending current requirement")],
        "Different pending current requirement",
    )
    store = JsonReviewStore(tmp_path)
    store.save(state)
    return store, store.load(state.review.review_id)


def selected_report(store, state):
    selection = api().prepare_historical_analysis(store, state, 0)
    with api().locked_historical_analysis(store, selection) as report:
        return report


def record_path(store, state):
    return store.directory / f"{state.review.review_id}.json"


@pytest.mark.parametrize("history_index", [-1, 1, True, False, "0", 0.0, None])
def test_history_selection_never_coerces_or_falls_back_to_another_position(tmp_path, history_index):
    store, state = saved_history(tmp_path)
    with pytest.raises((ValueError, TypeError)):
        api().prepare_historical_analysis(store, state, history_index)


@pytest.mark.parametrize("field", [
    "review_id", "state_fingerprint", "history_index", "analysis_fingerprint",
])
def test_selection_requires_explicit_identity_fields(tmp_path, field):
    store, state = saved_history(tmp_path)
    payload = api().prepare_historical_analysis(store, state, 0).model_dump(mode="json")
    del payload[field]
    with pytest.raises(ValidationError):
        api().HistoricalAnalysisSelection.model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("review_id", "../foreign"), ("review_id", ""),
    ("state_fingerprint", "A" * 64), ("analysis_fingerprint", "a" * 63),
    ("history_index", True), ("history_index", "0"),
])
@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning")
def test_forged_selection_is_revalidated_at_locked_consumer(tmp_path, field, value):
    store, state = saved_history(tmp_path)
    selection = api().prepare_historical_analysis(store, state, 0)
    forged = selection.model_copy(update={field: value})
    with pytest.raises((ValueError, OSError)), api().locked_historical_analysis(store, forged):
        pytest.fail("invalid selection yielded a retained analysis")


@pytest.mark.parametrize("field", [
    "report_kind", "schema_version", "boundary", "selection", "analysis",
    "validation_tool_version", "validation_ruleset_version", "validation_source_identity",
])
def test_report_never_invents_missing_envelope_identity(tmp_path, field):
    store, state = saved_history(tmp_path)
    payload = selected_report(store, state).model_dump(mode="json")
    del payload[field]
    with pytest.raises(ValidationError):
        api().HistoricalAnalysisReport.model_validate(payload)


@pytest.mark.parametrize("envelope", ["selection", "report"])
def test_serialized_historical_contracts_reject_unrecognized_fields(tmp_path, envelope):
    store, state = saved_history(tmp_path)
    report = selected_report(store, state)
    value = report.selection if envelope == "selection" else report
    payload = value.model_dump(mode="json")
    payload["current_head_authority"] = True
    with pytest.raises(ValidationError):
        type(value).model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("report_kind", "scopeproof_review"), ("schema_version", 2),
    ("schema_version", True), ("schema_version", "1"),
    ("boundary", "Current analysis ready for acceptance"),
    ("validation_tool_version", "forged-tool"),
    ("validation_ruleset_version", "forged-rules"),
    ("validation_source_identity", {"sha256": "f" * 64}),
])
@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning")
def test_exporters_revalidate_mutated_historical_envelope(tmp_path, field, value):
    store, state = saved_history(tmp_path)
    report = selected_report(store, state).model_copy(update={field: value})
    for exporter in renderers():
        with pytest.raises(ValueError):
            exporter(report)


@pytest.mark.parametrize("path", [
    ("review", "created_at"),
    ("resolutions", 0, "timestamp"),
    ("runtime_evidence", 0, "timestamp"),
    ("reviewer_selected_references", 0, "selected_at"),
])
def test_missing_recorded_timestamps_cannot_be_replaced_by_generated_defaults(tmp_path, path):
    store, state = saved_history(tmp_path)
    payload = selected_report(store, state).model_dump(mode="json")
    target = payload["analysis"]
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    with pytest.raises(ValidationError):
        api().HistoricalAnalysisReport.model_validate(payload)


@pytest.mark.parametrize("mutation", [
    "runtime", "resolution", "reference", "audit", "revision", "owner", "gate",
])
def test_every_recorded_bundle_change_invalidates_export_fingerprint(tmp_path, mutation):
    store, state = saved_history(tmp_path)
    report = selected_report(store, state)
    bundle = report.analysis
    if mutation == "runtime":
        bundle.runtime_evidence[0].limitations.append("Forged extra limitation")
    elif mutation == "resolution":
        bundle.resolutions[0].comment = "Forged retained decision context"
    elif mutation == "reference":
        bundle.reviewer_selected_references[0] = (
            bundle.reviewer_selected_references[0].model_copy(
                update={"rationale": "Forged rationale"},
            )
        )
    elif mutation == "audit":
        bundle.selected_reference_events[0] = bundle.selected_reference_events[0].model_copy(
            update={"reason": "Forged withdrawal explanation"},
        )
    elif mutation == "revision":
        bundle.criteria_revision_number = "unknown"
    elif mutation == "owner":
        bundle.review.review_id = "constructed-foreign-owner"
    else:
        bundle.gate.blocking_criteria.append("AC-FORGED")
    for exporter in renderers():
        with pytest.raises(ValueError):
            exporter(report)


@pytest.mark.parametrize("mutation", [
    "pending_source", "runtime", "reference", "audit", "remove_history", "replace_history",
    "unselected_history",
])
def test_receipt_binds_complete_saved_state_including_unselected_data(tmp_path, mutation):
    store, state = saved_history(tmp_path)
    # A reference-free unknown revision does not invent ownership for known references.
    state.analysis_history.append(state.analysis_history[0].model_copy(deep=True))
    state.analysis_history[1].criteria_revision_number = "unknown"
    state.analysis_history[1].reviewer_selected_references = []
    state.analysis_history[1].selected_reference_events = []
    state.analysis_history[1].review.created_at += timedelta(seconds=1)
    store.save(state)
    state = store.load(state.review.review_id)
    selection = api().prepare_historical_analysis(store, state, 0)
    if mutation == "pending_source":
        state.criteria_revision.source_text = "Changed pending source only"
    elif mutation == "runtime":
        state.analysis_history[0].runtime_evidence[0].limitations.append("Changed runtime only")
    elif mutation == "reference":
        state.analysis_history[0].reviewer_selected_references[0] = (
            state.analysis_history[0].reviewer_selected_references[0].model_copy(
                update={"rationale": "Changed reference only"},
            )
        )
    elif mutation == "audit":
        state.analysis_history[0].selected_reference_events[0] = (
            state.analysis_history[0].selected_reference_events[0].model_copy(
                update={"reason": "Changed audit only"},
            )
        )
    elif mutation == "remove_history":
        state.analysis_history.clear()
        state.resolution_events.clear()
    elif mutation == "replace_history":
        state.analysis_history.reverse()
    else:
        state.analysis_history[1].runtime_evidence[0].result = "Changed unselected history only"
    store.save(state)
    before = record_path(store, state).read_bytes()
    with pytest.raises(ValueError), api().locked_historical_analysis(store, selection):
        pytest.fail("stale receipt yielded a report")
    assert record_path(store, state).read_bytes() == before


@pytest.mark.parametrize("damage", ["delete", "corrupt", "symlink", "owner"])
def test_changed_storage_cannot_retarget_saved_receipt(tmp_path, damage):
    store, state = saved_history(tmp_path)
    selection = api().prepare_historical_analysis(store, state, 0)
    path = record_path(store, state)
    original = path.read_bytes()
    if damage == "delete":
        path.unlink()
    elif damage == "corrupt":
        path.write_text("{broken record", encoding="utf-8")
    elif damage == "symlink":
        target = tmp_path / "constructed-target-record.txt"
        target.write_bytes(original)
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            pytest.skip("symbolic link creation unavailable on this platform")
    else:
        payload = json.loads(original)
        payload["state"]["review"]["review_id"] = "constructed-other-owner"
        for bundle in payload["state"]["analysis_history"]:
            bundle["review"]["review_id"] = "constructed-other-owner"
        path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises((OSError, ValueError)), api().locked_historical_analysis(store, selection):
        pytest.fail("unavailable or mismatched record yielded a report")
    if damage == "symlink":
        assert target.read_bytes() == original


def test_unsaved_open_state_cannot_select_saved_history(tmp_path):
    store, state = saved_history(tmp_path)
    state.criteria_revision.source_text = "Unsaved current draft"
    with pytest.raises(ValueError):
        api().prepare_historical_analysis(store, state, 0)


def test_history_only_exports_preserve_full_record_and_old_producer(tmp_path):
    store, state = saved_history(tmp_path)
    historical = state.analysis_history[0]
    historical.review.tool_version = "0.0.1-constructed-old-producer"
    historical.review.ruleset_version = "constructed-old-rules"
    historical.review.analysis_source_identity = CoreSourceIdentity(sha256="c" * 64)
    store.save(state)
    state = store.load(state.review.review_id)
    before, saved_before = state.model_dump_json(), record_path(store, state).read_bytes()
    assert state.bundle is None and not state.criteria_revision.confirmed
    report = selected_report(store, state)
    assert report.analysis.criteria_revision_number == 1
    assert report.analysis.review.tool_version == "0.0.1-constructed-old-producer"
    assert report.analysis.review.ruleset_version == "constructed-old-rules"
    assert report.analysis.review.analysis_source_identity.sha256 == "c" * 64
    assert report.analysis.model_dump(mode="json") == historical.model_dump(mode="json")
    expected_hash = sha256(historical.model_dump_json().encode("utf-8")).hexdigest()
    assert report.selection.analysis_fingerprint == expected_hash
    assert api().historical_analysis_fingerprint(historical) == expected_hash
    encoded, markdown = (renderer(report) for renderer in renderers())
    payload = json.loads(encoded)
    assert payload["report_kind"] == "scopeproof_historical_analysis"
    assert payload["analysis"]["criteria_revision_number"] == 1
    assert "historical" in markdown.lower()
    assert report.selection.state_fingerprint in markdown
    assert report.selection.analysis_fingerprint in markdown
    assert "0.0.1-constructed-old-producer" in markdown
    assert before == state.model_dump_json()
    assert record_path(store, state).read_bytes() == saved_before
    report.analysis.runtime_evidence[0].limitations.append("Detached mutation")
    report.analysis.reviewer_selected_references[0] = (
        report.analysis.reviewer_selected_references[0].model_copy(
            update={"rationale": "Detached rationale"},
        )
    )
    assert before == state.model_dump_json()
    assert store.load(state.review.review_id).model_dump_json() == before


def test_unknown_revision_never_invents_known_reference_ownership(tmp_path):
    store, state = saved_history(tmp_path)
    historical = state.analysis_history[0]
    historical.criteria_revision_number = "unknown"
    historical.reviewer_selected_references = []
    historical.selected_reference_events = []
    store.save(state)
    state = store.load(state.review.review_id)
    report = selected_report(store, state)
    encoded, markdown = (renderer(report) for renderer in renderers())
    assert report.analysis.criteria_revision_number == "unknown"
    assert json.loads(encoded)["analysis"]["criteria_revision_number"] == "unknown"
    assert "unknown" in markdown.lower()


def test_legacy_missing_provenance_is_inspectable_but_both_exports_stay_blocked(tmp_path):
    store, state = saved_history(tmp_path)
    state.analysis_history[0].reviewer_selected_references = []
    state.analysis_history[0].selected_reference_events = []
    state.analysis_history[0].review.criteria_source_provenance = None
    state.analysis_history[0].review.analysis_source_identity = None
    store.save(state)
    state = store.load(state.review.review_id)
    before = record_path(store, state).read_bytes()
    report = selected_report(store, state)
    assert report.analysis.review.criteria_source_provenance is None
    assert report.analysis.review.analysis_source_identity is None
    for renderer in renderers():
        with pytest.raises(ValueError, match="provenance"):
            renderer(report)
    assert record_path(store, state).read_bytes() == before


def test_consumer_holds_record_lock_until_rendering_finishes(tmp_path):
    store, state = saved_history(tmp_path)
    selection = api().prepare_historical_analysis(store, state, 0)
    entered, release, started, completed = Event(), Event(), Event(), Event()

    def render():
        with api().locked_historical_analysis(store, selection) as report:
            entered.set()
            assert release.wait(5)
            return renderers()[0](report)

    def mutate():
        started.set()
        changed = state.model_copy(deep=True)
        changed.criteria_revision.source_text = "Concurrent saved source change"
        store.save(changed)
        completed.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        rendered = pool.submit(render)
        assert entered.wait(5)
        changed = pool.submit(mutate)
        try:
            assert started.wait(5)
            assert not completed.wait(0.1)
        finally:
            release.set()
        assert json.loads(rendered.result(5))["report_kind"] == "scopeproof_historical_analysis"
        changed.result(5)


@pytest.mark.parametrize("reference_kind", ["local", "windows", "https"])
def test_inspection_and_export_never_access_or_execute_recorded_artifact(
    tmp_path, monkeypatch, reference_kind,
):
    store, state = saved_history(tmp_path)
    artifact = tmp_path / "constructed-untrusted.py"
    artifact.write_text("raise AssertionError('Must never execute')\n", encoding="utf-8")
    reference = {
        "local": str(artifact), "windows": r"C:\constructed\untrusted.py",
        "https": "https://example.invalid/constructed-untrusted.py",
    }[reference_kind]
    state.analysis_history[0].runtime_evidence[0].artifact_reference = reference
    store.save(state)
    # Permit actual app-owned record and installed-source reads; reject artifact access.
    original_open, original_io_open = builtins.open, io.open
    original_os_open = os.open

    def checked_open(original, file, *args, **kwargs):
        if not isinstance(file, int) and str(file) in {str(artifact), reference}:
            raise AssertionError("Historical inspection accessed recorded artifact")
        return original(file, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Historical inspection fetched or executed target content")

    with monkeypatch.context() as guard:
        guard.setattr(
            builtins, "open", lambda file, *a, **k: checked_open(original_open, file, *a, **k),
        )
        guard.setattr(
            io, "open", lambda file, *a, **k: checked_open(original_io_open, file, *a, **k),
        )
        guard.setattr(
            os, "open", lambda file, *a, **k: checked_open(original_os_open, file, *a, **k),
        )
        guard.setattr(socket.socket, "connect", forbidden)
        guard.setattr(urllib.request, "urlopen", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(os, "system", forbidden)
        report = selected_report(store, state)
        encoded, _ = (renderer(report) for renderer in renderers())
    assert json.loads(encoded)["analysis"]["runtime_evidence"][0]["artifact_reference"] == reference
