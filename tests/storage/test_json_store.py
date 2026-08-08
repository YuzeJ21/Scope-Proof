from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from threading import Event, Lock
from uuid import NAMESPACE_URL, uuid5

import pytest
from pydantic import ValidationError

import scopeproof_core.storage.json_store as json_store_module
from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import export_html, export_markdown
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    append_resolution,
    append_runtime_evidence,
    attach_analysis,
    can_record_final_acceptance,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    PullRequestSnapshot,
    ResolutionEvent,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import (
    JsonReviewStore,
    UnsafeReviewStore,
    UnsupportedRecordVersion,
    default_local_review_directory,
)

_MISSING_RECORD_VERSION = object()


def review_state(review_id: str = "review-1"):
    bundle = build_demo_review()
    bundle.review.review_id = review_id
    return new_review_state(bundle)


def confirm_pending_revision(state):
    provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_revision=f"requirements-v{state.criteria_revision.number}",
        source_text=state.criteria_revision.source_text,
        criteria=state.criteria_revision.criteria,
        confirmed_by="Fixture owner",
        confirmed_at=state.criteria_revision.created_at + timedelta(seconds=1),
    )
    return confirm_criteria(state, provenance)


def attached_review_state():
    state = new_review_state(build_demo_review())
    updated_criteria = [
        item.model_copy(deep=True) for item in state.criteria_revision.criteria
    ]
    updated_criteria[0] = updated_criteria[0].model_copy(
        update={"text": "Updated AC-01 requirement"}
    )
    revised = confirm_pending_revision(
        revise_criteria(
            state,
            updated_criteria,
            "Updated requirements",
        )
    )
    incoming = build_demo_review()
    incoming.review = incoming.review.model_copy(
        update={
            "repository": revised.review.repository,
            "pr_number": revised.review.pr_number,
            "base_sha": revised.review.base_sha,
            "head_sha": revised.review.head_sha,
            "check_state": revised.review.check_state,
            "criteria_confirmed": True,
            "ingestion_state": revised.review.ingestion_state,
            "ingestion_warnings": revised.review.ingestion_warnings,
            "skipped_files": revised.review.skipped_files,
            "tool_version": revised.review.tool_version,
            "ruleset_version": revised.review.ruleset_version,
            "criteria_source_provenance": revised.review.criteria_source_provenance,
        }
    )
    incoming.source_text = revised.criteria_revision.source_text
    incoming.criteria = [
        item.model_copy(deep=True) for item in revised.criteria_revision.criteria
    ]
    return attach_analysis(revised, incoming)


def downgrade_to_version_one(payload: dict) -> dict:
    payload["record_version"] = 1
    if payload["state"]["bundle"] is not None:
        payload["state"]["bundle"].pop("criteria_revision_number")
    for historical_bundle in payload["state"]["analysis_history"]:
        historical_bundle.pop("criteria_revision_number")
    return payload


def state_with_runtime_history():
    state = review_state()
    assert state.bundle is not None
    historical_evidence = RuntimeEvidence(
        runtime_evidence_id="native-historical-runtime",
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="https://example.test/runs/historical",
        scenario="Export the filtered research list",
        environment="staging",
        result="passed",
        reviewer="QA reviewer",
        evidence_level=EvidenceLevel.E3,
        limitations=["Observed in a controlled staging environment"],
    )
    state = append_external_verification(
        state,
        historical_evidence,
        ResolutionEvent(
            event_id="historical-manual",
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Historical runtime observation",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=historical_evidence.runtime_evidence_id,
            reviewer=historical_evidence.reviewer,
        ),
    )
    for criterion in state.bundle.criteria:
        if criterion.criterion_id == "AC-01":
            continue
        state = append_resolution(
            state,
            ResolutionEvent(
                event_id=f"historical-accepted-{criterion.criterion_id}",
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment=f"Accepted {criterion.criterion_id}",
            ),
        )
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="historical-final-acceptance",
            final_acceptance=True,
            comment="Historical final acceptance note",
        ),
    )

    updated_criteria = [
        item.model_copy(deep=True) for item in state.criteria_revision.criteria
    ]
    updated_criteria[0] = updated_criteria[0].model_copy(
        update={"text": "Updated AC-01 requirement"}
    )
    revised = confirm_pending_revision(
        revise_criteria(state, updated_criteria, "Updated requirements")
    )
    incoming = build_demo_review()
    incoming.review = revised.review.model_copy(deep=True)
    incoming.source_text = revised.criteria_revision.source_text
    incoming.criteria = [
        item.model_copy(deep=True) for item in revised.criteria_revision.criteria
    ]
    incoming.gate = evaluate_gate(
        incoming.review,
        incoming.criteria,
        incoming.findings,
        incoming.resolutions,
    )
    attached = attach_analysis(revised, incoming)
    active_evidence = RuntimeEvidence(
        runtime_evidence_id="native-active-runtime",
        repository=attached.review.repository,
        pr_number=attached.review.pr_number,
        head_sha=attached.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="https://example.test/runs/active",
        scenario="Export the revised research list",
        environment="staging",
        result="passed",
        reviewer="Second QA reviewer",
        evidence_level=EvidenceLevel.E4,
        limitations=["Owner acceptance was recorded outside ScopeProof"],
    )
    return append_runtime_evidence(attached, active_evidence)


def downgrade_runtime_provenance(
    payload: dict,
    record_version: int = 2,
    *,
    remove_manual_links: bool = True,
) -> dict:
    payload["record_version"] = record_version
    bundles = [payload["state"]["bundle"], *payload["state"]["analysis_history"]]
    for bundle in bundles:
        if bundle is None:
            continue
        for runtime_item in bundle["runtime_evidence"]:
            for field_name in (
                "runtime_evidence_id",
                "repository",
                "pr_number",
                "head_sha",
            ):
                runtime_item.pop(field_name, None)
        if remove_manual_links:
            for resolution in bundle["resolutions"]:
                resolution.pop("runtime_evidence_id", None)
    if remove_manual_links:
        for event in payload["state"]["resolution_events"]:
            event.pop("runtime_evidence_id", None)
    if record_version == 1:
        downgrade_to_version_one(payload)
    return payload


def remove_criteria_source_provenance(
    payload: dict,
    record_version: int,
) -> dict:
    payload["record_version"] = record_version
    state_payload = payload["state"]
    state_payload["review"].pop("criteria_source_provenance", None)
    state_payload["criteria_revision"].pop("source_provenance", None)
    bundles = [
        state_payload["bundle"],
        *state_payload["analysis_history"],
    ]
    for bundle in bundles:
        if bundle is not None:
            bundle["review"].pop("criteria_source_provenance", None)
    return payload


def write_legacy_runtime_record(
    store: JsonReviewStore,
    *,
    record_version: int = 2,
) -> tuple[Path, dict]:
    state = state_with_runtime_history()
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    historical = payload["state"]["analysis_history"][0]
    historical["review"]["head_sha"] = "historical-head"
    historical["runtime_evidence"][0]["head_sha"] = "historical-head"
    downgrade_runtime_provenance(payload, record_version)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def write_version_two_runtime_record_retaining_links(
    store: JsonReviewStore,
) -> tuple[Path, dict]:
    state = state_with_runtime_history()
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    historical = payload["state"]["analysis_history"][0]
    historical["review"]["head_sha"] = "historical-head"
    historical["runtime_evidence"][0]["head_sha"] = "historical-head"
    downgrade_runtime_provenance(payload, remove_manual_links=False)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def test_saved_review_round_trips_without_token(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()

    path = store.save(state)
    loaded = store.load("review-1")

    assert path.name == "review-1.json"
    assert loaded.model_dump(mode="json") == state.model_dump(mode="json")
    assert "ghp_" not in path.read_text(encoding="utf-8")
    assert "authorization" not in path.read_text(encoding="utf-8").lower()


def test_mutate_serializes_concurrent_append_only_lifecycle_updates(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    store.save(review_state())
    first_entered = Event()
    second_started = Event()
    second_entered = Event()
    release_first = Event()
    call_lock = Lock()
    call_count = 0

    def append_distinct_resolution(state):
        nonlocal call_count
        with call_lock:
            call_index = call_count
            call_count += 1
        if call_index == 0:
            first_entered.set()
            assert release_first.wait(timeout=2)
        else:
            second_entered.set()
        return append_resolution(
            state,
            ResolutionEvent(
                event_id=f"concurrent-event-{call_index}",
                criterion_id=f"AC-0{call_index + 1}",
                decision=HumanDecision.ACCEPTED,
                comment="Concurrent lifecycle regression fixture",
                reviewer="Concurrency fixture",
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(store.mutate, "review-1", append_distinct_resolution)
        try:
            assert first_entered.wait(timeout=2)
            def run_second_mutation():
                second_started.set()
                return store.mutate("review-1", append_distinct_resolution)

            second = executor.submit(run_second_mutation)
            assert second_started.wait(timeout=2)
            assert not second_entered.wait(timeout=0.2)
        finally:
            release_first.set()
        first.result(timeout=2)
        second.result(timeout=2)

    saved = store.load("review-1")
    assert {event.event_id for event in saved.resolution_events} == {
        "concurrent-event-0",
        "concurrent-event-1",
    }


def test_attached_analysis_round_trip_preserves_reanalysis_lineage(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    attached = attached_review_state()
    original = build_demo_review()
    stable_review_id = attached.review.review_id

    store.save(attached)
    loaded = store.load(stable_review_id)

    assert loaded == attached
    assert loaded.criteria_revision.number == 2
    assert len(loaded.analysis_history) == 1
    assert loaded.review.review_id == stable_review_id
    assert loaded.bundle is not None
    assert loaded.bundle.review.review_id == stable_review_id
    assert loaded.bundle.source_text == "Updated requirements"
    assert loaded.bundle.criteria == loaded.criteria_revision.criteria
    historical = loaded.analysis_history[0]
    assert historical.source_text == original.source_text
    assert historical.criteria == original.criteria
    assert historical.source_text != loaded.bundle.source_text
    assert historical.criteria != loaded.bundle.criteria


def test_new_save_writes_version_four_with_exact_analysis_lineage_and_provenance(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()

    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["record_version"] == 4
    assert payload["state"]["bundle"]["criteria_revision_number"] == 2
    assert [
        bundle["criteria_revision_number"]
        for bundle in payload["state"]["analysis_history"]
    ] == [1]
    expected = state.review.criteria_source_provenance
    assert expected is not None
    assert payload["state"]["review"]["criteria_source_provenance"] == (
        expected.model_dump(mode="json")
    )
    assert payload["state"]["criteria_revision"]["source_provenance"] == (
        expected.model_dump(mode="json")
    )
    assert payload["state"]["bundle"]["review"][
        "criteria_source_provenance"
    ] == expected.model_dump(mode="json")


@pytest.mark.parametrize("record_version", [1, 2, 3])
def test_legacy_criteria_provenance_migration_preserves_facts_and_fails_closed(
    record_version: int,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = append_resolution(
        state_with_runtime_history(),
        ResolutionEvent(
            event_id="active-final-not-accepted",
            final_acceptance=False,
            comment="Active revision still needs owner acceptance",
            reviewer="Active reviewer",
        ),
    )
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if record_version in {1, 2}:
        downgrade_runtime_provenance(payload, record_version)
    remove_criteria_source_provenance(payload, record_version)
    for bundle in [
        payload["state"]["bundle"],
        *payload["state"]["analysis_history"],
    ]:
        bundle["gate"]["verdict"] = GateVerdict.READY.value
    original = deepcopy(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    first = store.load(state.review.review_id)
    second = store.load(state.review.review_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.review.criteria_source_provenance is None
    assert first.criteria_revision.source_provenance is None
    assert first.bundle is not None
    loaded_bundles = [first.bundle, *first.analysis_history]
    original_bundles = [
        original["state"]["bundle"],
        *original["state"]["analysis_history"],
    ]
    for loaded_bundle, original_bundle in zip(
        loaded_bundles,
        original_bundles,
        strict=True,
    ):
        assert loaded_bundle.review.criteria_source_provenance is None
        assert loaded_bundle.source_text == original_bundle["source_text"]
        assert loaded_bundle.model_dump(mode="json")["criteria"] == original_bundle[
            "criteria"
        ]
        assert loaded_bundle.model_dump(mode="json")["evidence"] == original_bundle[
            "evidence"
        ]
        assert [
            (item.artifact_reference, item.scenario, item.result, item.reviewer)
            for item in loaded_bundle.runtime_evidence
        ] == [
            (
                item["artifact_reference"],
                item["scenario"],
                item["result"],
                item["reviewer"],
            )
            for item in original_bundle["runtime_evidence"]
        ]
        assert loaded_bundle.gate == evaluate_gate(
            loaded_bundle.review,
            loaded_bundle.criteria,
            loaded_bundle.findings,
            loaded_bundle.resolutions,
        )
        if loaded_bundle.gate.verdict is not GateVerdict.BLOCKED:
            assert loaded_bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
            assert (
                "criteria_source_provenance_missing"
                in loaded_bundle.gate.reason_codes
            )


    loaded_event_facts = [
        (
            event.event_id,
            event.decision.value if event.decision is not None else None,
            event.final_acceptance,
            event.comment,
            event.reviewer,
        )
        for event in first.resolution_events
    ]
    original_event_facts = [
        (
            event["event_id"],
            event["decision"],
            event["final_acceptance"],
            event["comment"],
            event["reviewer"],
        )
        for event in original["state"]["resolution_events"]
    ]
    assert loaded_event_facts == original_event_facts
    assert first.review.final_acceptance is False
    assert first.analysis_history[0].review.final_acceptance is True
    assert any(event.final_acceptance is True for event in first.resolution_events)
    assert any(event.final_acceptance is False for event in first.resolution_events)

    resaved_path = store.save(first)
    resaved = json.loads(resaved_path.read_text(encoding="utf-8"))
    assert resaved["record_version"] == 4
    assert resaved["state"]["review"]["criteria_source_provenance"] is None
    assert resaved["state"]["criteria_revision"]["source_provenance"] is None
    assert resaved["state"]["bundle"]["review"][
        "criteria_source_provenance"
    ] is None
    assert store.load(state.review.review_id) == first


@pytest.mark.parametrize("record_version", [1, 2, 3])
def test_legacy_empty_criteria_records_remain_readable_and_fail_closed(
    record_version: int,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    remove_criteria_source_provenance(payload, record_version)
    if record_version == 1:
        downgrade_to_version_one(payload)
    state_payload = payload["state"]
    state_payload["criteria_revision"]["criteria"] = []
    state_payload["resolution_events"] = []
    active_bundle = state_payload["bundle"]
    active_bundle["criteria"] = []
    active_bundle["evidence"] = []
    active_bundle["retrieval_diagnostics"] = []
    active_bundle["findings"] = []
    active_bundle["runtime_evidence"] = []
    active_bundle["resolutions"] = []
    active_bundle["gate"] = {
        "verdict": "ready",
        "blocking_criteria": [],
        "conditional_criteria": [],
        "unresolved_criteria": [],
        "resolved_exceptions": [],
        "reason_codes": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(state.review.review_id)

    assert loaded.criteria_revision.criteria == []
    assert loaded.bundle is not None
    assert loaded.bundle.criteria == []
    assert loaded.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert "criteria_missing" in loaded.bundle.gate.reason_codes
    assert can_record_final_acceptance(loaded) is False

    store.save(loaded)
    reloaded = store.load(state.review.review_id)
    assert reloaded.bundle is not None
    assert reloaded.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert reloaded.criteria_revision.criteria == []


def test_version_one_record_migrates_active_revision_and_unknown_history(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    payload["state"]["analysis_history"].append(
        json.loads(json.dumps(payload["state"]["analysis_history"][0]))
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(state.review.review_id)

    assert loaded.bundle is not None
    assert loaded.bundle.criteria_revision_number == 2
    assert [
        bundle.criteria_revision_number for bundle in loaded.analysis_history
    ] == ["unknown", "unknown"]


def test_saving_migrated_version_one_state_preserves_unknown_history(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    migrated = store.load(state.review.review_id)
    migrated_path = store.save(migrated)
    migrated_payload = json.loads(migrated_path.read_text(encoding="utf-8"))

    assert migrated_payload["record_version"] == 4
    assert migrated_payload["state"]["bundle"]["criteria_revision_number"] == 2
    assert [
        bundle["criteria_revision_number"]
        for bundle in migrated_payload["state"]["analysis_history"]
    ] == ["unknown"]


def test_legacy_runtime_migration_is_deterministic_and_uses_owning_bundle_identity(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    _, payload = write_legacy_runtime_record(store)
    active_original = deepcopy(payload["state"]["bundle"]["runtime_evidence"][0])
    historical_original = deepcopy(
        payload["state"]["analysis_history"][0]["runtime_evidence"][0]
    )
    review_id = payload["state"]["review"]["review_id"]
    active_canonical = json.dumps(
        active_original,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    historical_canonical = json.dumps(
        historical_original,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    expected_active_id = str(
        uuid5(
            NAMESPACE_URL,
            f"scopeproof-runtime-evidence:{review_id}:active:2:"
            f"0:{active_canonical}",
        )
    )
    expected_historical_id = str(
        uuid5(
            NAMESPACE_URL,
            f"scopeproof-runtime-evidence:{review_id}:history:0:"
            f"0:{historical_canonical}",
        )
    )

    first = store.load(review_id)
    second = store.load(review_id)

    assert first.model_dump_json() == second.model_dump_json()
    assert first.bundle is not None
    active_runtime = first.bundle.runtime_evidence[0]
    historical_bundle = first.analysis_history[0]
    historical_runtime = historical_bundle.runtime_evidence[0]
    assert active_runtime.runtime_evidence_id == expected_active_id
    assert historical_runtime.runtime_evidence_id == expected_historical_id
    assert expected_active_id != expected_historical_id
    assert (
        active_runtime.repository,
        active_runtime.pr_number,
        active_runtime.head_sha,
    ) == (
        first.bundle.review.repository,
        first.bundle.review.pr_number,
        first.bundle.review.head_sha,
    )
    assert (
        historical_runtime.repository,
        historical_runtime.pr_number,
        historical_runtime.head_sha,
    ) == (
        historical_bundle.review.repository,
        historical_bundle.review.pr_number,
        "historical-head",
    )


def test_version_one_runtime_migration_runs_after_lineage_migration(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    runtime_item = RuntimeEvidence(
        criterion_id="AC-01",
        artifact_reference="https://example.test/runs/version-one",
        scenario="Reopen a version one review",
        environment="staging",
        result="passed",
        reviewer="QA reviewer",
        evidence_level=EvidenceLevel.E3,
    ).model_dump(mode="json")
    payload["state"]["bundle"]["runtime_evidence"] = [deepcopy(runtime_item)]
    payload["state"]["analysis_history"][0]["runtime_evidence"] = [
        deepcopy(runtime_item)
    ]
    downgrade_to_version_one(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(state.review.review_id)

    assert loaded.bundle is not None
    assert loaded.bundle.criteria_revision_number == 2
    assert loaded.bundle.runtime_evidence[0].runtime_evidence_id is not None
    assert loaded.analysis_history[0].criteria_revision_number == "unknown"
    assert loaded.analysis_history[0].runtime_evidence[0].runtime_evidence_id is not None


def test_version_one_unknown_history_preserves_legacy_verification_audit(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    _, payload = write_legacy_runtime_record(store, record_version=1)
    review_id = payload["state"]["review"]["review_id"]
    original_history = deepcopy(payload["state"]["analysis_history"][0])
    original_events = deepcopy(payload["state"]["resolution_events"])

    first = store.load(review_id)
    second = store.load(review_id)

    assert first.model_dump_json() == second.model_dump_json()
    assert len(first.analysis_history) == 1
    historical = first.analysis_history[0]
    assert historical.criteria_revision_number == "unknown"
    assert len(historical.runtime_evidence) == len(
        original_history["runtime_evidence"]
    )
    assert historical.runtime_evidence[0].artifact_reference == (
        original_history["runtime_evidence"][0]["artifact_reference"]
    )
    assert historical.runtime_evidence[0].reviewer == (
        original_history["runtime_evidence"][0]["reviewer"]
    )
    manual_resolution = next(
        resolution
        for resolution in historical.resolutions
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED
    )
    manual_event = next(
        event
        for event in first.resolution_events
        if event.decision is HumanDecision.MANUALLY_VERIFIED
    )
    assert manual_resolution.runtime_evidence_id is None
    assert manual_event.runtime_evidence_id is None
    assert historical.review.final_acceptance is True
    assert first.resolution_events[-1].final_acceptance is True
    assert first.resolution_events[-1].comment == "Historical final acceptance note"
    assert [event.comment for event in first.resolution_events] == [
        event["comment"] for event in original_events
    ]
    assert historical.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert (
        "runtime_verification_reconfirmation_required"
        in historical.gate.reason_codes
    )

    resaved_path = store.save(first)
    resaved = json.loads(resaved_path.read_text(encoding="utf-8"))
    assert resaved["record_version"] == 4
    assert resaved["state"]["analysis_history"][0][
        "criteria_revision_number"
    ] == "unknown"
    assert [
        event["comment"] for event in resaved["state"]["resolution_events"]
    ] == [event["comment"] for event in original_events]


def test_version_two_runtime_migration_preserves_legacy_links_as_unlinked_and_fails_closed(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    _, payload = write_legacy_runtime_record(store)
    old_events = deepcopy(payload["state"]["resolution_events"])

    loaded = store.load(payload["state"]["review"]["review_id"])

    assert loaded.analysis_history[0].resolutions[0].runtime_evidence_id is None
    assert all(event.runtime_evidence_id is None for event in loaded.resolution_events)
    loaded_events = [event.model_dump(mode="json") for event in loaded.resolution_events]
    for event in loaded_events:
        event.pop("runtime_evidence_id")
    assert loaded_events == old_events
    assert loaded.analysis_history[0].review.final_acceptance is True
    assert loaded.resolution_events[-1].final_acceptance is True
    assert loaded.analysis_history[0].gate.verdict is GateVerdict.NEEDS_REVIEW
    assert (
        "runtime_verification_reconfirmation_required"
        in loaded.analysis_history[0].gate.reason_codes
    )


def test_legacy_manual_history_without_runtime_items_recomputes_gate(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path, payload = write_legacy_runtime_record(store)
    payload["state"]["analysis_history"][0]["runtime_evidence"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(payload["state"]["review"]["review_id"])

    historical = loaded.analysis_history[0]
    assert historical.runtime_evidence == []
    assert historical.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert (
        "runtime_verification_reconfirmation_required"
        in historical.gate.reason_codes
    )


def test_version_two_migration_unlinks_preexisting_task_one_manual_ids(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    _, payload = write_version_two_runtime_record_retaining_links(store)
    old_events = deepcopy(payload["state"]["resolution_events"])

    loaded = store.load(payload["state"]["review"]["review_id"])

    historical = loaded.analysis_history[0]
    manual_resolution = next(
        resolution
        for resolution in historical.resolutions
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED
    )
    manual_event = next(
        event
        for event in loaded.resolution_events
        if event.decision is HumanDecision.MANUALLY_VERIFIED
    )
    assert manual_resolution.runtime_evidence_id is None
    assert manual_event.runtime_evidence_id is None
    loaded_events = [event.model_dump(mode="json") for event in loaded.resolution_events]
    for event in [*old_events, *loaded_events]:
        event.pop("runtime_evidence_id", None)
    assert loaded_events == old_events
    assert historical.review.final_acceptance is True
    assert loaded.resolution_events[-1].comment == "Historical final acceptance note"
    assert loaded.resolution_events[-1].final_acceptance is True
    assert historical.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert (
        "runtime_verification_reconfirmation_required"
        in historical.gate.reason_codes
    )


def test_version_two_migration_unlinks_predictable_migrated_manual_ids(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path, payload = write_version_two_runtime_record_retaining_links(store)
    historical_payload = payload["state"]["analysis_history"][0]
    canonical_original_payload = json.dumps(
        historical_payload["runtime_evidence"][0],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    review_id = historical_payload["review"]["review_id"]
    predictable_migrated_id = str(
        uuid5(
            NAMESPACE_URL,
            f"scopeproof-runtime-evidence:{review_id}:history:0:"
            f"0:{canonical_original_payload}",
        )
    )
    historical_payload["resolutions"][0]["runtime_evidence_id"] = (
        predictable_migrated_id
    )
    for event in payload["state"]["resolution_events"]:
        if event["decision"] == HumanDecision.MANUALLY_VERIFIED.value:
            event["runtime_evidence_id"] = predictable_migrated_id
    old_events = deepcopy(payload["state"]["resolution_events"])
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(review_id)

    historical = loaded.analysis_history[0]
    manual_resolution = next(
        resolution
        for resolution in historical.resolutions
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED
    )
    manual_event = next(
        event
        for event in loaded.resolution_events
        if event.decision is HumanDecision.MANUALLY_VERIFIED
    )
    assert manual_resolution.runtime_evidence_id is None
    assert manual_event.runtime_evidence_id is None
    loaded_events = [event.model_dump(mode="json") for event in loaded.resolution_events]
    for event in [*old_events, *loaded_events]:
        event.pop("runtime_evidence_id", None)
    assert loaded_events == old_events
    assert historical.review.final_acceptance is True
    assert loaded.resolution_events[-1].comment == "Historical final acceptance note"
    assert loaded.resolution_events[-1].final_acceptance is True
    assert historical.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert (
        "runtime_verification_reconfirmation_required"
        in historical.gate.reason_codes
    )


def test_version_two_runtime_migration_does_not_mutate_parsed_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    _, legacy_payload = write_legacy_runtime_record(store)
    original_payload = deepcopy(legacy_payload)
    monkeypatch.setattr(
        "scopeproof_core.storage.json_store.json.loads",
        lambda _: legacy_payload,
    )

    store.load(legacy_payload["state"]["review"]["review_id"])

    assert legacy_payload == original_payload


def test_resaving_migrated_runtime_record_writes_version_four_without_history_loss(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    _, payload = write_legacy_runtime_record(store)
    old_notes = [event["comment"] for event in payload["state"]["resolution_events"]]
    old_event_ids = [event["event_id"] for event in payload["state"]["resolution_events"]]

    migrated = store.load(payload["state"]["review"]["review_id"])
    migrated_path = store.save(migrated)
    resaved = json.loads(migrated_path.read_text(encoding="utf-8"))

    assert resaved["record_version"] == 4
    assert [
        event["comment"] for event in resaved["state"]["resolution_events"]
    ] == old_notes
    assert [
        event["event_id"] for event in resaved["state"]["resolution_events"]
    ] == old_event_ids
    assert resaved["state"]["analysis_history"][0]["review"]["final_acceptance"] is True


def test_version_three_runtime_ids_are_not_rewritten(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = state_with_runtime_history()

    store.save(state)
    loaded = store.load(state.review.review_id)

    assert loaded.bundle is not None
    assert loaded.bundle.runtime_evidence[0].runtime_evidence_id == "native-active-runtime"
    assert (
        loaded.analysis_history[0].runtime_evidence[0].runtime_evidence_id
        == "native-historical-runtime"
    )


def test_bundleless_version_one_record_preserves_unknown_history(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    pending = revise_criteria(
        review_state(),
        review_state().criteria_revision.criteria,
        "Updated requirements",
    )
    path = store.save(pending)
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(pending.review.review_id)

    assert loaded.bundle is None
    assert [
        bundle.criteria_revision_number for bundle in loaded.analysis_history
    ] == ["unknown"]


def test_version_one_migration_does_not_mutate_parsed_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    legacy_payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    original_payload = json.loads(json.dumps(legacy_payload))
    monkeypatch.setattr(
        "scopeproof_core.storage.json_store.json.loads",
        lambda _: legacy_payload,
    )

    store.load(state.review.review_id)

    assert legacy_payload == original_payload


def test_malformed_version_one_nested_content_is_rejected_by_pydantic(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    payload["state"]["bundle"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        store.load("review-1")


def test_version_one_migration_recomputes_non_deterministic_gate(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    payload["state"]["bundle"]["gate"]["verdict"] = GateVerdict.READY.value
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load("review-1")

    assert loaded.bundle is not None
    assert loaded.bundle.gate == evaluate_gate(
        loaded.bundle.review,
        loaded.bundle.criteria,
        loaded.bundle.findings,
        loaded.bundle.resolutions,
    )


def test_historical_review_state_loads_without_ingestion_limitation_fields(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    for review in (
        payload["state"]["review"],
        payload["state"]["bundle"]["review"],
    ):
        review.pop("ingestion_warnings", None)
        review.pop("skipped_files", None)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load("review-1")

    assert loaded.review.ingestion_warnings == []
    assert loaded.review.skipped_files == []
    assert loaded.bundle is not None
    assert loaded.bundle.review.ingestion_warnings == []
    assert loaded.bundle.review.skipped_files == []


def test_version_two_missing_ci_observation_recomputes_stale_ready_gate_fail_closed(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["review"].pop("ci_observation")
    payload["state"]["bundle"]["review"].pop("ci_observation")
    payload["state"]["bundle"]["gate"]["verdict"] = GateVerdict.READY.value
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load("review-1")

    assert loaded.review.check_state.value == "unavailable"
    assert loaded.bundle is not None
    assert loaded.bundle.review.check_state.value == "unavailable"
    assert loaded.bundle.gate == evaluate_gate(
        loaded.bundle.review,
        loaded.bundle.criteria,
        loaded.bundle.findings,
        loaded.bundle.resolutions,
    )
    assert loaded.bundle.gate.verdict is GateVerdict.BLOCKED
    assert loaded.resolution_events == []
    assert loaded.review.final_acceptance is False


def test_version_two_missing_history_ci_observation_recomputes_stale_conditional_gate(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    historical = payload["state"]["analysis_history"][0]
    historical["review"].pop("ci_observation")
    historical["gate"]["verdict"] = GateVerdict.CONDITIONAL.value
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(state.review.review_id)

    assert loaded.analysis_history[0].review.check_state.value == "unavailable"
    assert loaded.analysis_history[0].gate == evaluate_gate(
        loaded.analysis_history[0].review,
        loaded.analysis_history[0].criteria,
        loaded.analysis_history[0].findings,
        loaded.analysis_history[0].resolutions,
    )
    assert loaded.analysis_history[0].gate.verdict is GateVerdict.BLOCKED
    assert loaded.resolution_events == state.resolution_events
    assert loaded.review.final_acceptance is state.review.final_acceptance


def test_load_rejects_mismatched_active_bundle_review(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["review"]["head_sha"] = "different-head"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match="active bundle review must match lifecycle review"
    ):
        store.load("review-1")


def test_save_revalidates_mismatched_active_bundle_review(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    divergent = state.model_copy(
        update={
            "review": state.review.model_copy(update={"head_sha": "different-head"})
        }
    )

    with pytest.raises(
        ValueError, match="active bundle review must match lifecycle review"
    ):
        store.save(divergent)

    assert list(tmp_path.iterdir()) == []


def test_save_rejects_a_non_deterministic_active_gate(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    assert state.bundle is not None
    state.bundle.gate = state.bundle.gate.model_copy(update={"verdict": GateVerdict.READY})

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        store.save(state)

    assert list(tmp_path.iterdir()) == []


def test_load_rejects_a_non_deterministic_active_gate(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["bundle"]["gate"]["verdict"] = GateVerdict.READY.value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        store.load("review-1")


def test_save_rejects_forged_ready_state_without_resolution_events(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    assert state.bundle is not None
    state.review.final_acceptance = True
    state.bundle.review.final_acceptance = True
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Forged acceptance",
        )
        for criterion in state.bundle.criteria
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )
    assert state.bundle.gate.verdict is GateVerdict.READY
    assert state.resolution_events == []

    with pytest.raises(
        ValueError, match="active bundle resolutions must match active resolution events"
    ):
        store.save(state)

    assert list(tmp_path.iterdir()) == []


def test_save_preserves_recoverable_legacy_manual_verification_without_link(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    assert state.bundle is not None
    event = ResolutionEvent(
        event_id="manual-without-runtime",
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        claimed_evidence_level=EvidenceLevel.E3,
        reviewer="QA",
        comment="Observed the scenario",
        criteria_revision_number=1,
    )
    state.resolution_events = [event]
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            claimed_evidence_level=EvidenceLevel.E3,
            reviewer="QA",
            comment="Observed the scenario",
            timestamp=event.timestamp,
        )
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )

    path = store.save(state)
    loaded = store.load("review-1")

    assert path.exists()
    assert loaded.bundle is not None
    assert loaded.bundle.resolutions[0].runtime_evidence_id is None
    assert loaded.bundle.gate.verdict is not GateVerdict.READY
    assert (
        "runtime_verification_reconfirmation_required"
        in loaded.bundle.gate.reason_codes
    )


def test_save_rejects_foreign_historical_review_lineage(tmp_path: Path) -> None:
    state = review_state()
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.analysis_history[0].review.repository = "other/repository"

    with pytest.raises(
        ValueError,
        match="historical bundle review lineage must match lifecycle review",
    ):
        JsonReviewStore(tmp_path).save(revised)

    assert list(tmp_path.iterdir()) == []


def test_version_one_record_with_legacy_permalink_loads_and_exports_inertly(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    legacy_permalink = "javascript:alert(1)"
    payload["state"]["bundle"]["evidence"][0]["permalink"] = legacy_permalink
    downgrade_to_version_one(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load("review-1")

    assert loaded.bundle is not None
    assert loaded.bundle.evidence[0].permalink == legacy_permalink
    assert f"]({legacy_permalink})" not in export_markdown(loaded)
    assert f'href="{legacy_permalink}"' not in export_html(loaded)


def test_list_review_ids_returns_empty_when_store_does_not_exist(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path / "reviews")

    assert store.list_review_ids() == []


def test_list_review_ids_is_sorted_bounded_and_does_not_parse_records(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    (tmp_path / "z-review.json").write_text("not parsed during discovery", encoding="utf-8")
    (tmp_path / "a-review.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bad id.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("{}", encoding="utf-8")
    (tmp_path / "directory.json").mkdir()
    (tmp_path / "linked-review.json").symlink_to(tmp_path / "a-review.json")

    assert store.list_review_ids() == ["a-review", "z-review"]


def test_delete_removes_only_the_exact_review_and_preserves_its_neighbor(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    first_state = review_state("review-1")
    second_state = review_state("review-2")
    store.save(first_state)
    store.save(second_state)

    store.delete("review-1")

    assert not (tmp_path / "review-1.json").exists()
    assert store.load("review-2") == second_state


def test_delete_removes_a_corrupt_regular_record_without_parsing_it(
    tmp_path: Path,
) -> None:
    corrupt_record = tmp_path / "corrupt.json"
    corrupt_record.write_text("not valid JSON", encoding="utf-8")

    JsonReviewStore(tmp_path).delete("corrupt")

    assert not corrupt_record.exists()


def test_delete_pins_store_directory_when_root_is_replaced_at_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_root = tmp_path / "reviews"
    store = JsonReviewStore(store_root)
    target = store.save(review_state("review-1"))
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()
    opened_store_root = tmp_path / "opened-reviews"
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_target = outside / target.name
    outside_target.write_text("keep external", encoding="utf-8")
    real_unlink = os.unlink
    root_replaced = False

    def replace_root_then_unlink(path, *args, **kwargs):
        nonlocal root_replaced
        if not root_replaced:
            store_root.rename(opened_store_root)
            store_root.symlink_to(outside, target_is_directory=True)
            root_replaced = True
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", replace_root_then_unlink)

    store.delete("review-1")

    assert root_replaced is True
    assert outside_target.read_text(encoding="utf-8") == "keep external"
    assert not (opened_store_root / target.name).exists()
    assert (opened_store_root / neighbor.name).read_bytes() == neighbor_contents


def test_delete_fails_closed_when_safe_directory_descriptor_operations_are_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = JsonReviewStore(tmp_path)
    target = store.save(review_state("review-1"))
    monkeypatch.setattr(
        json_store_module, "_SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED", False
    )

    with pytest.raises(OSError, match="safe local review deletion is unsupported"):
        store.delete("review-1")

    assert target.exists()


@pytest.mark.parametrize("review_id", ["../review-1", "review-1.json", "/tmp/review-1"])
def test_delete_rejects_invalid_review_ids_without_changing_any_files(
    review_id: str,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    first_path = store.save(review_state("review-1"))
    second_path = store.save(review_state("review-2"))
    before = {path.name: path.read_bytes() for path in (first_path, second_path)}

    with pytest.raises(ValueError):
        store.delete(review_id)

    assert {path.name: path.read_bytes() for path in (first_path, second_path)} == before


def test_delete_missing_record_raises_without_changing_its_neighbor(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()

    with pytest.raises(FileNotFoundError):
        store.delete("missing")

    assert neighbor.read_bytes() == neighbor_contents


def test_delete_rejects_a_symlinked_store_root_without_changing_external_files(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_store = JsonReviewStore(outside)
    target = outside_store.save(review_state("review-1"))
    neighbor = outside_store.save(review_state("review-2"))
    external = outside / "external.txt"
    external.write_text("keep external", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in (target, neighbor, external)}
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).delete("review-1")

    assert store_root.is_symlink()
    assert {path.name: path.read_bytes() for path in (target, neighbor, external)} == before


def test_delete_rejects_a_record_symlink_without_changing_any_files(
    tmp_path: Path,
) -> None:
    store_root = tmp_path / "reviews"
    store_root.mkdir()
    store = JsonReviewStore(store_root)
    external = tmp_path / "external-review.json"
    external.write_text("keep external", encoding="utf-8")
    target = store_root / "review-1.json"
    target.symlink_to(external)
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()

    with pytest.raises(FileNotFoundError):
        store.delete("review-1")

    assert target.is_symlink()
    assert neighbor.read_bytes() == neighbor_contents
    assert external.read_text(encoding="utf-8") == "keep external"


def test_delete_rejects_a_directory_named_like_a_record_without_changing_files(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    target = tmp_path / "review-1.json"
    target.mkdir()
    external = target / "external.txt"
    external.write_text("keep external", encoding="utf-8")
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()

    with pytest.raises(FileNotFoundError):
        store.delete("review-1")

    assert target.is_dir()
    assert neighbor.read_bytes() == neighbor_contents
    assert external.read_text(encoding="utf-8") == "keep external"


def test_list_review_ids_rejects_a_symlinked_store_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "outside-review.json").write_text("{}", encoding="utf-8")
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).list_review_ids()


def test_load_rejects_a_symlinked_store_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_store = JsonReviewStore(outside)
    outside_store.save(review_state())
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).load("review-1")


def test_save_rejects_a_symlinked_store_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).save(review_state())

    assert list(outside.iterdir()) == []


def test_list_review_ids_rejects_a_regular_file_store_root(tmp_path: Path) -> None:
    store_root = tmp_path / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(UnsafeReviewStore, match="review store path must be a directory"):
        JsonReviewStore(store_root).list_review_ids()


def test_load_rejects_a_regular_file_store_root(tmp_path: Path) -> None:
    store_root = tmp_path / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(UnsafeReviewStore, match="review store path must be a directory"):
        JsonReviewStore(store_root).load("review-1")


def test_save_rejects_a_regular_file_store_root(tmp_path: Path) -> None:
    store_root = tmp_path / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(UnsafeReviewStore, match="review store path must be a directory"):
        JsonReviewStore(store_root).save(review_state())

    assert store_root.read_text(encoding="utf-8") == "not a directory"


def test_head_change_is_reported_without_mutating_old_evidence(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    snapshot = PullRequestSnapshot.model_validate(
        {
            **build_demo_review().review.model_dump(mode="json"),
            "title": "Updated demo",
            "html_url": "https://github.com/scopeproof/demo-stock-research/pull/17",
            "head_sha": "new-head",
            "files": [],
        }
    )

    change = store.detect_head_change(state, snapshot)

    assert change.changed is True
    assert change.saved_head_sha == "head-demo-002"
    assert change.current_head_sha == "new-head"
    assert state.bundle is not None
    assert state.bundle.review.head_sha == "head-demo-002"


@pytest.mark.parametrize(
    "record_version",
    [
        pytest.param(999, id="unknown-integer"),
        pytest.param(True, id="true"),
        pytest.param(False, id="false"),
        pytest.param(1.0, id="float-one"),
        pytest.param(2.0, id="float-two"),
        pytest.param(3.0, id="float-three"),
        pytest.param(4.0, id="float-four"),
        pytest.param("1", id="string-one"),
        pytest.param("2", id="string-two"),
        pytest.param("3", id="string-three"),
        pytest.param("4", id="string-four"),
        pytest.param(None, id="null"),
        pytest.param(_MISSING_RECORD_VERSION, id="missing"),
    ],
)
def test_unsupported_or_coercive_record_version_is_rejected(
    record_version: object,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    if record_version is _MISSING_RECORD_VERSION:
        payload.pop("record_version")
    else:
        payload["record_version"] = record_version
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(UnsupportedRecordVersion):
        store.load("review-1")


def test_load_rejects_record_missing_state_without_key_error(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    path.write_text(json.dumps({"record_version": 4}), encoding="utf-8")

    with pytest.raises(ValueError, match="record envelope") as error:
        store.load("review-1")

    assert not isinstance(error.value, KeyError)


def test_review_id_cannot_escape_store_directory(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)

    with pytest.raises(ValueError):
        store.load("../outside")


def test_default_local_review_directory_is_confined_to_the_user_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert default_local_review_directory() == tmp_path / ".scopeproof" / "reviews"


def test_load_rejects_a_review_record_symlink_that_escapes_the_store(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    saved_path = store.save(review_state())
    outside_record = tmp_path.parent / "outside-review.json"
    outside_record.write_text(saved_path.read_text(encoding="utf-8"), encoding="utf-8")
    saved_path.unlink()
    saved_path.symlink_to(outside_record)

    with pytest.raises(FileNotFoundError):
        store.load("review-1")
