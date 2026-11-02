"""Independent fail-closed regressions for retained JUnit import withdrawal."""

from datetime import UTC, datetime, timedelta, timezone
from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.importers.junit import JUnitMappingSelection, build_junit_evidence_import
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    append_junit_evidence_import,
    append_resolution,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    ResolutionEvent,
    ReviewBundle,
    ReviewState,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import JUNIT_AUDIT_XML, junit_audit_state


def audit_api():
    try:
        return import_module("scopeproof_core.reviews.junit_audit")
    except ModuleNotFoundError as error:
        if error.name != "scopeproof_core.reviews.junit_audit":
            raise
        pytest.fail("JUnit import withdrawal is not implemented yet", pytrace=False)


def withdraw(state, **changes):
    if "expected_state_fingerprint" in changes:
        fingerprint = changes["expected_state_fingerprint"]
    else:
        fingerprint = JsonReviewStore.state_fingerprint(state)
    parameters = {
        "import_id": "constructed-junit-import",
        "reviewer": "CONSTRUCTED withdrawal actor",
        "reason": "CONSTRUCTED incorrect mapping",
        "expected_state_fingerprint": fingerprint,
        "occurred_at": datetime(2026, 11, 1, 13, tzinfo=UTC),
    }
    parameters.update(changes)
    return audit_api().withdraw_junit_evidence_import(state, **parameters)


def without_audit(state):
    payload = state.model_dump(mode="python")
    if payload["bundle"] is not None:
        payload["bundle"].pop("junit_import_events", None)
        payload["bundle"].pop("active_junit_import_ids", None)
    return payload


def test_withdrawal_preserves_all_original_model_data_and_both_criterion_mappings() -> None:
    state = junit_audit_state()
    before = state.model_dump_json()
    updated = withdraw(state)

    assert state.model_dump_json() == before
    assert without_audit(updated) == without_audit(state)
    assert updated.bundle is not None
    assert updated.bundle.active_junit_import_ids == []
    assert state.bundle.active_junit_import_ids == ["constructed-junit-import"]
    mappings = updated.bundle.junit_evidence_imports[0].criterion_mappings
    assert [m.criterion_id for m in mappings] == [
        "AC-01", "AC-02",
    ]
    event = updated.bundle.junit_import_events[0]
    assert event.import_id == "constructed-junit-import"
    assert event.artifact_sha256 == updated.bundle.junit_evidence_imports[0].artifact_sha256
    assert event.evidence_boundary == updated.bundle.junit_evidence_imports[0].evidence_boundary
    assert event.schema_version == "junit-import-withdrawal-v1"
    assert event.action == "withdrawn"


def test_withdrawal_preserves_already_recorded_final_acceptance_and_decision_events() -> None:
    state = junit_audit_state()
    runtime = RuntimeEvidence(
        runtime_evidence_id="constructed-runtime-record",
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="https://example.test/constructed-runtime-record",
        scenario="CONSTRUCTED external verification scenario",
        environment="CONSTRUCTED isolated automation data",
        result="CONSTRUCTED result, not genuine runtime verification",
        reviewer="CONSTRUCTED runtime actor",
        evidence_level=EvidenceLevel.E3,
        limitations=["Synthetic schema exercise, not personal testing or a qualifying review"],
    )
    state = append_external_verification(
        state, runtime,
        ResolutionEvent(
            criterion_id="AC-01", decision=HumanDecision.MANUALLY_VERIFIED,
            reviewer=runtime.reviewer, comment="CONSTRUCTED paired runtime record",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=runtime.runtime_evidence_id,
        ),
    )
    for criterion in state.bundle.criteria:
        if criterion.criterion_id == "AC-01":
            continue
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                reviewer="CONSTRUCTED decision actor",
                comment="CONSTRUCTED evidence gap acknowledged; not a qualifying review",
            ),
        )
    state = append_resolution(
        state,
        ResolutionEvent(
            final_acceptance=True,
            reviewer="CONSTRUCTED decision actor",
            comment="CONSTRUCTED acceptance record only",
        ),
    )
    assert state.review.final_acceptance is True
    updated = withdraw(state)
    assert updated.review.final_acceptance is True
    assert updated.bundle.review.final_acceptance is True
    assert without_audit(updated) == without_audit(state)


@pytest.mark.parametrize("field,value", [
    ("reviewer", " "), ("reviewer", "x" * 201),
    ("reason", "\n\t"), ("reason", "x" * 2001),
    ("occurred_at", datetime(2026, 11, 1)),
    ("import_id", "missing-import"),
])
def test_invalid_withdrawal_request_leaves_input_unchanged(field, value) -> None:
    state = junit_audit_state()
    before = state.model_dump_json()
    with pytest.raises(ValueError):
        withdraw(state, **{field: value})
    assert state.model_dump_json() == before


def test_attribution_normalizes_and_aware_time_converts_to_utc_without_clock_ordering() -> None:
    state = junit_audit_state()
    time = datetime(2026, 10, 31, 5, tzinfo=timezone(timedelta(hours=-5)))
    updated = withdraw(state, reviewer="  CONSTRUCTED actor  ", reason="  Retire context  ",
                       occurred_at=time)
    event = updated.bundle.junit_import_events[0]
    assert event.reviewer == "CONSTRUCTED actor"
    assert event.reason == "Retire context"
    assert event.occurred_at == datetime(2026, 10, 31, 10, tzinfo=UTC)
    assert event.occurred_at.tzinfo is UTC


@pytest.mark.parametrize("field,value", [
    ("schema_version", "junit-import-v1"), ("action", "reactivated"),
    ("event_id", "../foreign"), ("import_id", ""),
    ("artifact_sha256", "bad"), ("head_sha", "short"),
    ("criteria_revision_number", True), ("criteria_revision_number", "1"),
    ("reviewer", "x" * 201), ("reason", "x" * 2001),
    ("occurred_at", datetime(2026, 11, 1)), ("verified", True),
])
def test_withdrawal_event_schema_rejects_forged_fields(field, value) -> None:
    updated = withdraw(junit_audit_state())
    event = updated.bundle.junit_import_events[0]
    payload = event.model_dump(mode="python")
    payload[field] = value
    with pytest.raises(ValidationError):
        type(event).model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("gate_effect", "gating"), ("execution", "executed_by_scopeproof"),
    ("importer_identity", "authenticated"), ("criterion_mapping", "proof"),
])
def test_withdrawal_cannot_forge_the_fixed_evidence_boundary(field, value) -> None:
    updated = withdraw(junit_audit_state())
    event = updated.bundle.junit_import_events[0]
    payload = event.model_dump(mode="python")
    payload["evidence_boundary"][field] = value
    with pytest.raises(ValidationError):
        type(event).model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("review_id", "foreign-review"), ("repository", "foreign/repository"),
    ("pr_number", 99), ("head_sha", "c" * 40),
    ("criteria_revision_number", 2), ("confirmed_criteria_sha256", "c" * 64),
    ("artifact_sha256", "c" * 64), ("import_id", "foreign-import"),
])
def test_bundle_rejects_foreign_withdrawal_owner_or_target(field, value) -> None:
    updated = withdraw(junit_audit_state())
    payload = updated.bundle.model_dump(mode="python")
    payload["junit_import_events"][0][field] = value
    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)


def test_bundle_rejects_foreign_complete_provenance_and_orphan_events() -> None:
    updated = withdraw(junit_audit_state())
    payload = updated.bundle.model_dump(mode="python")
    payload["junit_import_events"][0]["criteria_source_provenance"]["source_revision"] = "foreign"
    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)
    payload = updated.bundle.model_dump(mode="python")
    payload["junit_evidence_imports"] = []
    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)


def test_duplicate_withdrawal_is_rejected_by_service_and_aggregate_schema() -> None:
    updated = withdraw(junit_audit_state())
    before = updated.model_dump_json()
    with pytest.raises(ValueError):
        withdraw(updated)
    assert updated.model_dump_json() == before
    payload = updated.bundle.model_dump(mode="python")
    duplicate = dict(payload["junit_import_events"][0], event_id="second-event")
    payload["junit_import_events"].append(duplicate)
    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)


def test_duplicate_event_ids_for_different_imports_are_rejected() -> None:
    state = junit_audit_state()
    other = build_junit_evidence_import(
        state, JUNIT_AUDIT_XML.replace(b"CONSTRUCTED pass", b"CONSTRUCTED other"),
        [JUnitMappingSelection(scope_id="suite-0001", criterion_id="AC-01")],
        importer="CONSTRUCTED actor", import_id="other-import",
    )
    state = append_junit_evidence_import(state, other)
    state = withdraw(state)
    state = withdraw(state, import_id="other-import")
    payload = state.bundle.model_dump(mode="python")
    payload["junit_import_events"][1]["event_id"] = payload["junit_import_events"][0]["event_id"]
    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)


def test_serialized_active_ids_are_discarded_and_status_is_derived() -> None:
    updated = withdraw(junit_audit_state())
    payload = updated.bundle.model_dump(mode="python")
    payload["active_junit_import_ids"] = ["constructed-junit-import", "invented-import"]
    assert ReviewBundle.model_validate(payload).active_junit_import_ids == []


@pytest.mark.parametrize("change", ["note", "provenance"])
def test_full_state_fingerprint_rejects_same_head_and_criteria_but_changed_context(change) -> None:
    state = junit_audit_state()
    fingerprint = JsonReviewStore.state_fingerprint(state)
    changed = state.model_copy(deep=True)
    if change == "note":
        changed.bundle.junit_evidence_imports[0].limitations.append("CONSTRUCTED later note")
    else:
        provenance = changed.review.criteria_source_provenance.model_copy(
            update={"source_revision": "CONSTRUCTED changed provenance"}
        )
        changed.review.criteria_source_provenance = provenance
        changed.criteria_revision.source_provenance = provenance
        changed.bundle.review.criteria_source_provenance = provenance
        changed.bundle.junit_evidence_imports = [
            changed.bundle.junit_evidence_imports[0].model_copy(
                update={"criteria_source_provenance": provenance}
            )
        ]
    changed = ReviewState.model_validate(changed.model_dump(mode="python"))
    before = changed.model_dump_json()
    assert changed.review.head_sha == state.review.head_sha
    with pytest.raises(ValueError):
        withdraw(changed, expected_state_fingerprint=fingerprint)
    assert changed.model_dump_json() == before


def test_mutable_or_constructed_state_is_revalidated_before_withdrawal() -> None:
    state = junit_audit_state()
    fingerprint = JsonReviewStore.state_fingerprint(state)
    state.bundle.junit_evidence_imports[0].criterion_mappings[0].test_case_ids.append(
        "suite-9999-case-9999"
    )
    with pytest.raises(ValueError):
        withdraw(state, expected_state_fingerprint=fingerprint)


def test_pending_revision_cannot_withdraw_a_historical_import() -> None:
    state = junit_audit_state()
    pending = revise_criteria(state, state.criteria_revision.criteria, "CONSTRUCTED revised text")
    before = pending.model_dump_json()
    with pytest.raises(ValueError):
        withdraw(pending)
    assert pending.model_dump_json() == before
    assert pending.analysis_history[0].junit_evidence_imports == state.bundle.junit_evidence_imports


def test_withdrawn_digest_and_id_remain_reserved_at_builder_and_lifecycle() -> None:
    original = junit_audit_state()
    state = withdraw(original)
    before = state.model_dump_json()
    with pytest.raises(ValueError):
        build_junit_evidence_import(
            state, JUNIT_AUDIT_XML,
            [JUnitMappingSelection(scope_id="suite-0001", criterion_id="AC-01")],
            importer="CONSTRUCTED actor", import_id="replacement-import",
        )
    with pytest.raises(ValueError):
        append_junit_evidence_import(state, original.bundle.junit_evidence_imports[0])
    assert state.model_dump_json() == before


def test_withdrawal_does_not_release_any_of_twenty_retained_import_slots() -> None:
    state = junit_audit_state()
    original = state.bundle.junit_evidence_imports[0]
    state.bundle.junit_evidence_imports.extend(
        original.model_copy(update={"import_id": f"retained-{i}", "artifact_sha256": f"{i:064x}"})
        for i in range(1, 20)
    )
    state = ReviewState.model_validate(state.model_dump(mode="python"))
    updated = withdraw(state)
    assert len(updated.bundle.junit_evidence_imports) == 20
    assert len(updated.bundle.active_junit_import_ids) == 19
    before = updated.model_dump_json()
    with pytest.raises(ValueError):
        append_junit_evidence_import(
            updated,
            original.model_copy(update={"import_id": "overflow", "artifact_sha256": "f" * 64}),
        )
    assert updated.model_dump_json() == before


def test_returned_models_do_not_alias_original_mutable_lists() -> None:
    original = junit_audit_state()
    updated = withdraw(original)
    before = updated.model_dump_json()
    original.bundle.junit_evidence_imports[0].limitations.append("Caller mutation")
    assert updated.model_dump_json() == before


def test_event_is_frozen_and_unknown_status_target_is_rejected() -> None:
    updated = withdraw(junit_audit_state())
    event = updated.bundle.junit_import_events[0]
    with pytest.raises(ValidationError):
        event.reason = "Changed in place"
    with pytest.raises(ValueError):
        audit_api().junit_import_status(updated.bundle, "unknown-import")
