"""Independent constructed regressions for append-only JUnit mapping corrections."""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.junit_audit import withdraw_junit_evidence_import
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    append_resolution,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    JUnitCriterionMapping,
    ResolutionEvent,
    ReviewBundle,
    ReviewState,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import junit_audit_state

IMPORT_ID = "constructed-junit-import"
CASE_1 = "suite-0001-case-0001"
CASE_2 = "suite-0001-case-0002"
WHEN = datetime(2026, 11, 1, 13, tzinfo=UTC)


def api():
    try:
        return import_module("scopeproof_core.reviews.junit_correction")
    except ModuleNotFoundError as error:
        if error.name != "scopeproof_core.reviews.junit_correction":
            raise
        pytest.fail("saved JUnit mapping correction is not implemented", pytrace=False)


def group(criterion="AC-02", cases=(CASE_1, CASE_2)):
    return JUnitCriterionMapping(criterion_id=criterion, test_case_ids=list(cases))


def correct(state, **changes):
    fingerprint = (
        changes["expected_state_fingerprint"]
        if "expected_state_fingerprint" in changes
        else JsonReviewStore.state_fingerprint(state)
    )
    parameters = {
        "import_id": IMPORT_ID,
        "criterion_mappings": [group()],
        "reviewer": " CONSTRUCTED correction actor ",
        "reason": " CONSTRUCTED wrong organizational grouping ",
        "confirm_whole_import": True,
        "expected_state_fingerprint": fingerprint,
        "occurred_at": WHEN,
    }
    parameters.update(changes)
    return api().correct_junit_mappings(state, **parameters)


def non_audit(state):
    payload = state.model_dump(mode="python")
    if payload["bundle"] is not None:
        for field in ("junit_import_events", "active_junit_import_ids", "effective_junit_mappings"):
            payload["bundle"].pop(field, None)
    return payload


def validate_payload(state, mutate):
    payload = state.model_dump(mode="python")
    mutate(payload)
    with pytest.raises(ValueError):
        validated_review_state(ReviewState.model_validate(payload))


def test_correction_preserves_original_full_state_and_retains_explicit_snapshot():
    state = junit_audit_state()
    before = state.model_dump_json()
    updated = correct(state)
    assert state.model_dump_json() == before
    assert non_audit(updated) == non_audit(state)
    assert updated.bundle.junit_evidence_imports == state.bundle.junit_evidence_imports
    assert updated.bundle.active_junit_import_ids == [IMPORT_ID]
    event = updated.bundle.junit_import_events[0]
    assert event.schema_version == "junit-mapping-correction-v1"
    assert event.action == "mapping_corrected"
    assert event.previous_correction_event_id is None
    assert event.criterion_mappings == [group()]
    assert event.reviewer == "CONSTRUCTED correction actor"
    assert event.reason == "CONSTRUCTED wrong organizational grouping"
    assert event.occurred_at == WHEN
    original = state.bundle.junit_evidence_imports[0]
    for field in (
        "import_id",
        "artifact_sha256",
        "repository",
        "pr_number",
        "head_sha",
        "criteria_revision_number",
        "confirmed_criteria_sha256",
        "criteria_source_provenance",
        "evidence_boundary",
    ):
        assert getattr(event, field) == getattr(original, field)
    assert event.review_id == state.review.review_id
    assert updated.bundle.effective_junit_mappings[IMPORT_ID] == [group()]


def test_previous_mapping_digest_is_canonical_and_independently_reproducible():
    state = junit_audit_state()
    mappings = state.bundle.junit_evidence_imports[0].criterion_mappings
    canonical_json = json.dumps(
        [mapping.model_dump(mode="json") for mapping in mappings],
        sort_keys=True,
        separators=(",", ":"),
    )
    expected = sha256(canonical_json.encode("utf-8")).hexdigest()
    event = correct(state).bundle.junit_import_events[0]
    assert event.previous_mapping_sha256 == expected
    digest = import_module("scopeproof_core.schemas.models").junit_mapping_sha256
    assert digest(mappings) == expected
    with pytest.raises(ValueError):
        digest(list(reversed(mappings)))


def test_active_correction_does_not_rewrite_prior_revision_history():
    state = junit_audit_state()
    payload = state.model_dump(mode="python")
    payload["analysis_history"] = [state.bundle.model_dump(mode="python")]
    payload["criteria_revision"]["number"] = 2
    payload["bundle"]["criteria_revision_number"] = 2
    payload["bundle"]["junit_evidence_imports"][0]["criteria_revision_number"] = 2
    state = validated_review_state(ReviewState.model_validate(payload))
    history_before = state.analysis_history[0].model_dump_json()
    updated = correct(state)
    assert non_audit(updated) == non_audit(state)
    assert updated.analysis_history[0].model_dump_json() == history_before
    assert updated.bundle.junit_import_events[0].criteria_revision_number == 2


def test_explicit_acceptance_decisions_and_archived_owner_are_preserved():
    state = junit_audit_state()
    runtime = RuntimeEvidence(
        runtime_evidence_id="constructed-correction-runtime",
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="https://example.test/constructed-runtime",
        scenario="CONSTRUCTED external scenario",
        environment="CONSTRUCTED isolated fixture",
        result="CONSTRUCTED schema exercise, no genuine verification asserted",
        reviewer="CONSTRUCTED runtime actor",
        evidence_level=EvidenceLevel.E3,
        limitations=["Constructed automated test, no personal testing or qualifying review"],
    )
    state = append_external_verification(
        state,
        runtime,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            reviewer=runtime.reviewer,
            comment="CONSTRUCTED paired runtime fixture",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=runtime.runtime_evidence_id,
        ),
    )
    for criterion in state.criteria_revision.criteria:
        if criterion.criterion_id == "AC-01":
            continue
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                reviewer="CONSTRUCTED decision actor",
                comment="CONSTRUCTED evidence gap accepted; no qualifying review",
            ),
        )
    state = append_resolution(
        state,
        ResolutionEvent(
            final_acceptance=True,
            reviewer="CONSTRUCTED decision actor",
            comment="CONSTRUCTED acceptance flag",
        ),
    )
    updated = correct(state)
    assert updated.review.final_acceptance is True
    assert non_audit(updated) == non_audit(state)
    archived = revise_criteria(
        updated, updated.criteria_revision.criteria, "CONSTRUCTED next revision"
    )
    frozen_history = archived.model_dump_json()
    with pytest.raises(ValueError):
        correct(archived)
    assert archived.model_dump_json() == frozen_history
    assert archived.analysis_history[-1] == updated.bundle


@pytest.mark.parametrize("confirmation", [False, None, 0, 1, "true", "yes", [], {}])
def test_whole_import_confirmation_requires_actual_boolean_true(confirmation):
    state = junit_audit_state()
    before = state.model_dump_json()
    with pytest.raises((ValueError, TypeError)):
        correct(state, confirm_whole_import=confirmation)
    assert state.model_dump_json() == before


@pytest.mark.parametrize(
    "changes",
    [
        {"criterion_mappings": []},
        {"criterion_mappings": [group("AC-99")]},
        {"criterion_mappings": [group(cases=("suite-9999-case-9999",))]},
        {"criterion_mappings": [group("AC-01", (CASE_1,)), group("AC-02", (CASE_1,))]},
        {"criterion_mappings": [group("AC-02", (CASE_2,)), group("AC-01", (CASE_1,))]},
        {"reviewer": " \t "},
        {"reason": " \n "},
        {"reason": "x" * 2001},
        {"import_id": "unknown-import"},
        {"expected_state_fingerprint": "0" * 64},
        {"occurred_at": datetime(2026, 11, 1, 13)},
    ],
)
def test_invalid_request_fails_without_mutating_input(changes):
    state = junit_audit_state()
    before = state.model_dump_json()
    with pytest.raises((ValueError, TypeError)):
        correct(state, **changes)
    assert state.model_dump_json() == before


def test_noop_and_empty_snapshots_reject_but_partial_assignment_is_permitted():
    state = junit_audit_state()
    with pytest.raises(ValueError):
        correct(state, criterion_mappings=state.bundle.junit_evidence_imports[0].criterion_mappings)
    partial = correct(state, criterion_mappings=[group(cases=(CASE_1,))])
    assert partial.bundle.effective_junit_mappings[IMPORT_ID] == [group(cases=(CASE_1,))]


def test_cycles_and_interleaved_imports_follow_append_order_despite_reversed_clock():
    state = junit_audit_state()
    original = state.bundle.junit_evidence_imports[0]
    state.bundle.junit_evidence_imports.append(
        original.model_copy(
            deep=True,
            update={
                "import_id": "constructed-second-import",
                "artifact_sha256": "1" * 64,
            },
        )
    )
    state = validated_review_state(state)
    first = correct(state)
    second = correct(
        first, import_id="constructed-second-import", occurred_at=WHEN - timedelta(days=1)
    )
    third = correct(
        second, criterion_mappings=original.criterion_mappings, occurred_at=WHEN - timedelta(days=2)
    )
    fourth = correct(third, occurred_at=WHEN - timedelta(days=3))
    events = fourth.bundle.junit_import_events
    assert events[2].previous_correction_event_id == events[0].event_id
    assert events[3].previous_correction_event_id == events[2].event_id
    assert events[1].previous_correction_event_id is None
    assert events[0].previous_mapping_sha256 == events[3].previous_mapping_sha256
    assert fourth.bundle.effective_junit_mappings[IMPORT_ID] == [group()]
    assert fourth.bundle.effective_junit_mappings["constructed-second-import"] == [group()]
    validate_payload(
        fourth,
        lambda payload: payload["bundle"]["junit_import_events"].__setitem__(
            slice(None),
            [events[i].model_dump(mode="python") for i in (3, 1, 2, 0)],
        ),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("event_id", "../foreign"),
        ("import_id", "foreign-import"),
        ("review_id", "foreign-review"),
        ("repository", "foreign/repository"),
        ("pr_number", 18),
        ("pr_number", True),
        ("criteria_revision_number", True),
        ("criteria_revision_number", 2),
        ("head_sha", "b" * 40),
        ("artifact_sha256", "c" * 64),
        ("confirmed_criteria_sha256", "d" * 64),
        ("previous_mapping_sha256", "e" * 64),
        ("previous_correction_event_id", "nonexistent-event"),
        ("schema_version", "junit-import-withdrawal-v1"),
        ("action", "withdrawn"),
        ("extra_approval", True),
    ],
)
def test_event_or_aggregate_rejects_forged_identity_chain_and_types(field, value):
    state = correct(junit_audit_state())
    validate_payload(
        state, lambda payload: payload["bundle"]["junit_import_events"][0].__setitem__(field, value)
    )


def test_nullable_previous_event_id_is_required_and_complete_provenance_is_bound():
    state = correct(junit_audit_state())
    validate_payload(
        state, lambda p: p["bundle"]["junit_import_events"][0].pop("previous_correction_event_id")
    )
    validate_payload(
        state,
        lambda p: p["bundle"]["junit_import_events"][0]["criteria_source_provenance"].__setitem__(
            "source_revision",
            "forged-assertion",
        ),
    )
    validate_payload(
        state,
        lambda p: p["bundle"]["junit_import_events"][0]["evidence_boundary"].__setitem__(
            "gate_effect",
            "gating",
        ),
    )


@pytest.mark.parametrize(
    "mappings",
    [
        [],
        [{"criterion_id": "AC-99", "test_case_ids": [CASE_1]}],
        [{"criterion_id": "AC-02", "test_case_ids": ["suite-9999-case-9999"]}],
        [
            {"criterion_id": "AC-01", "test_case_ids": [CASE_1]},
            {"criterion_id": "AC-02", "test_case_ids": [CASE_1]},
        ],
        [
            {"criterion_id": "AC-01", "test_case_ids": [CASE_1]},
            {"criterion_id": "AC-02", "test_case_ids": [CASE_2]},
        ],
    ],
)
def test_saved_event_snapshot_cannot_bypass_mapping_or_noop_validation(mappings):
    state = correct(junit_audit_state())
    validate_payload(
        state,
        lambda payload: payload["bundle"]["junit_import_events"][0].__setitem__(
            "criterion_mappings",
            mappings,
        ),
    )


def test_replay_rejects_duplicate_event_ids_and_stale_branches():
    first = correct(junit_audit_state())
    second = correct(first, criterion_mappings=[group("AC-01")])
    validate_payload(
        second,
        lambda p: p["bundle"]["junit_import_events"][1].__setitem__(
            "event_id",
            p["bundle"]["junit_import_events"][0]["event_id"],
        ),
    )
    validate_payload(
        second,
        lambda p: p["bundle"]["junit_import_events"][1].__setitem__(
            "previous_correction_event_id",
            None,
        ),
    )
    validate_payload(second, lambda p: p["bundle"]["junit_import_events"].reverse())


def test_projection_and_transition_do_not_alias_mutable_mapping_lists():
    state = junit_audit_state()
    requested = [group()]
    updated = correct(state, criterion_mappings=requested)
    before = updated.model_dump_json()
    requested[0].test_case_ids.append("suite-9999-case-9999")
    state.bundle.junit_evidence_imports[0].criterion_mappings[0].test_case_ids.clear()
    projected = api().effective_junit_mappings(updated.bundle, IMPORT_ID)
    projected[0].test_case_ids.clear()
    computed = updated.bundle.effective_junit_mappings
    computed[IMPORT_ID][0].test_case_ids.clear()
    events = api().junit_mapping_correction_events(updated.bundle, IMPORT_ID)
    events[0].criterion_mappings[0].test_case_ids.clear()
    assert updated.model_dump_json() == before
    with pytest.raises(ValidationError):
        updated.bundle.junit_import_events[0].reason = "overwrite"


def test_mutated_nested_history_is_revalidated_even_with_a_previously_valid_fingerprint():
    state = correct(junit_audit_state())
    fingerprint = JsonReviewStore.state_fingerprint(state)
    state.bundle.junit_import_events[0].criterion_mappings[0].test_case_ids.append(
        "suite-9999-case-9999"
    )
    with pytest.raises(ValueError):
        correct(state, expected_state_fingerprint=fingerprint, criterion_mappings=[group("AC-01")])


def test_serialized_effective_mapping_projection_cannot_override_replay():
    state = correct(junit_audit_state())
    payload = state.model_dump(mode="python")
    payload["bundle"]["effective_junit_mappings"] = {IMPORT_ID: []}
    rebuilt = validated_review_state(ReviewState.model_validate(payload))
    assert rebuilt.bundle.effective_junit_mappings[IMPORT_ID] == [group()]


def test_withdrawal_remains_terminal_and_legacy_defaulted_tags_load():
    state = correct(junit_audit_state())
    withdrawn = withdraw_junit_evidence_import(
        state,
        import_id=IMPORT_ID,
        reviewer="CONSTRUCTED withdrawal actor",
        reason="CONSTRUCTED retire context",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
    )
    before = withdrawn.model_dump_json()
    with pytest.raises(ValueError):
        correct(withdrawn, criterion_mappings=[group("AC-01")])
    assert withdrawn.model_dump_json() == before
    payload = withdrawn.model_dump(mode="python")
    terminal = payload["bundle"]["junit_import_events"][-1]
    terminal.pop("schema_version")
    terminal.pop("action")
    rebuilt = validated_review_state(ReviewState.model_validate(payload))
    assert rebuilt.bundle.active_junit_import_ids == []
    validate_payload(withdrawn, lambda p: p["bundle"]["junit_import_events"].reverse())


def test_twenty_corrections_reserve_twenty_terminal_withdrawals_without_freeing_slots():
    state = junit_audit_state()
    original = state.bundle.junit_evidence_imports[0]
    state.bundle.junit_evidence_imports.extend(
        original.model_copy(
            deep=True,
            update={
                "import_id": f"retained-{i}",
                "artifact_sha256": f"{i:064x}",
            },
        )
        for i in range(1, 20)
    )
    state = validated_review_state(state)
    for imported in state.bundle.junit_evidence_imports:
        state = correct(state, import_id=imported.import_id)
    before = state.model_dump_json()
    with pytest.raises(ValueError):
        correct(state, criterion_mappings=[group("AC-01")])
    assert state.model_dump_json() == before
    overflow = state.bundle.junit_import_events[-1].model_dump(mode="python")
    overflow.update(
        event_id="constructed-overflow-correction",
        previous_correction_event_id=overflow["event_id"],
        previous_mapping_sha256=import_module(
            "scopeproof_core.schemas.models"
        ).junit_mapping_sha256(
            [group()],
        ),
        criterion_mappings=[group("AC-01").model_dump(mode="python")],
    )
    validate_payload(
        state, lambda payload: payload["bundle"]["junit_import_events"].append(overflow)
    )
    for imported in state.bundle.junit_evidence_imports:
        state = withdraw_junit_evidence_import(
            state,
            import_id=imported.import_id,
            reviewer="CONSTRUCTED actor",
            reason="CONSTRUCTED terminal retirement",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        )
    assert len(state.bundle.junit_import_events) == 40
    assert len(state.bundle.junit_evidence_imports) == 20
    assert state.bundle.active_junit_import_ids == []
    assert (
        len(ReviewBundle.model_validate(state.bundle.model_dump(mode="python")).junit_import_events)
        == 40
    )
