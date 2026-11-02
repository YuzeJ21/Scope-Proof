"""Withdrawal changes recorded context while retaining artifact and review truth."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.reviews.comparison import (
    JUnitImportReference,
    ReviewComparison,
    compare_reviews,
)
from scopeproof_core.reviews.junit_audit import withdraw_junit_evidence_import
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import junit_audit_state

_ACTIVE_CONTEXT_SHA256 = "3a3f316e7bcebe7ce6e8ede90290d2f2f728362587c37e1a61dc4d45df79ff15"
_OCCURRED_AT = datetime(2026, 11, 1, 13, 14, 15, tzinfo=UTC)


def _withdraw(state, *, reason="CONSTRUCTED mapping was assigned to the wrong criterion"):
    return withdraw_junit_evidence_import(
        state,
        import_id="constructed-junit-import",
        reviewer="CONSTRUCTED withdrawal actor",
        reason=reason,
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        occurred_at=_OCCURRED_AT,
    )


def test_fresh_active_reference_retains_the_pre_audit_context_hash():
    imported = junit_audit_state().bundle.junit_evidence_imports[0]

    reference = JUnitImportReference.from_import(imported)

    assert reference.status == "active"
    assert reference.withdrawal_event is None
    # This literal was recorded before withdrawal projections were implemented.
    assert reference.context_sha256 == _ACTIVE_CONTEXT_SHA256
    assert [(item.criterion_id, item.test_case_ids) for item in reference.mappings] == [
        ("AC-01", ["suite-0001-case-0001"]),
        ("AC-02", ["suite-0001-case-0002"]),
    ]


def test_withdrawal_is_context_modified_and_never_removes_the_retained_artifact():
    previous = junit_audit_state()
    current = _withdraw(previous)
    previous_before = previous.model_dump(mode="json")
    current_before = current.model_dump(mode="json")

    comparison = compare_reviews(previous.bundle, current.bundle)

    assert len(comparison.junit_import_changes) == 1
    change = comparison.junit_import_changes[0]
    assert change.kind.value == "context_modified"
    assert change.artifact_sha256 == (
        "4ade313a449dfcc98c02a483c8adcddfc5edddf9e2a10b16f9e44e2820ed1ccc"
    )
    assert change.previous.import_id == change.current.import_id == "constructed-junit-import"
    assert change.previous.status == "active"
    assert change.previous.withdrawal_event is None
    assert change.previous.context_sha256 == _ACTIVE_CONTEXT_SHA256
    assert change.current.status == "withdrawn"
    assert change.current.withdrawal_event == current.bundle.junit_import_events[0]
    assert change.current.withdrawal_event.review_id == "constructed-junit-audit-review"
    assert change.current.withdrawal_event.criteria_revision_number == 1
    assert change.current.context_sha256 != _ACTIVE_CONTEXT_SHA256
    assert change.previous.mappings == change.current.mappings
    assert comparison.previous_gate == comparison.current_gate == previous.bundle.gate.verdict
    assert comparison.evidence_changes == []
    assert comparison.changed_finding_statuses == []
    assert comparison.changed_human_resolutions == []
    assert comparison.criteria_requiring_decision_review == []
    assert previous.model_dump(mode="json") == previous_before
    assert current.model_dump(mode="json") == current_before


def test_explicit_withdrawn_projection_matches_the_complete_owned_event():
    state = _withdraw(junit_audit_state())
    event = state.bundle.junit_import_events[0]

    reference = JUnitImportReference.from_import(
        state.bundle.junit_evidence_imports[0], withdrawal_event=event,
    )

    assert reference.status == "withdrawn"
    assert reference.withdrawal_event == event
    assert reference.withdrawal_event.reviewer == "CONSTRUCTED withdrawal actor"
    assert reference.withdrawal_event.occurred_at == _OCCURRED_AT
    assert reference.withdrawal_event.criteria_source_provenance.source_revision == (
        "constructed-junit-audit-v1"
    )
    assert reference.context_sha256 != _ACTIVE_CONTEXT_SHA256


def test_withdrawal_review_guidance_does_not_change_existing_human_decisions():
    previous = junit_audit_state()
    previous = append_resolution(
        previous,
        ResolutionEvent(
            criterion_id="AC-02", decision=HumanDecision.ACCEPTED,
            reviewer="CONSTRUCTED criterion actor", comment="CONSTRUCTED explicit decision",
        ),
    )
    current = _withdraw(previous)

    comparison = compare_reviews(previous.bundle, current.bundle)

    # Both mappings retire, but only the already-resolved criterion needs decision review.
    assert comparison.criteria_requiring_decision_review == ["AC-02"]
    assert comparison.changed_human_resolutions == []
    assert current.bundle.resolutions == previous.bundle.resolutions
    assert current.resolution_events == previous.resolution_events
    assert current.review.final_acceptance == previous.review.final_acceptance
    assert current.bundle.gate == previous.bundle.gate


def test_identical_withdrawn_context_is_unchanged_but_changed_event_is_not():
    withdrawn = _withdraw(junit_audit_state())
    unchanged = compare_reviews(withdrawn.bundle, withdrawn.bundle.model_copy(deep=True))
    assert unchanged.junit_import_changes[0].kind.value == "unchanged"
    assert unchanged.junit_import_changes[0].current.status == "withdrawn"

    changed = withdrawn.bundle.model_copy(deep=True)
    changed.junit_import_events[0] = changed.junit_import_events[0].model_copy(
        update={"reason": "CONSTRUCTED alternate recorded attribution"},
    )
    comparison = compare_reviews(withdrawn.bundle, changed)
    assert comparison.junit_import_changes[0].kind.value == "context_modified"
    assert comparison.junit_import_changes[0].previous.status == "withdrawn"
    assert comparison.junit_import_changes[0].current.status == "withdrawn"


def test_legacy_comparison_references_keep_unavailable_status_instead_of_inventing_active():
    state = junit_audit_state()
    payload = compare_reviews(state.bundle, state.bundle).model_dump(mode="json")
    for side in ("previous", "current"):
        reference = payload["junit_import_changes"][0][side]
        reference.pop("status", None)
        reference.pop("withdrawal_event", None)

    legacy = ReviewComparison.model_validate(payload)

    for reference in (
        legacy.junit_import_changes[0].previous,
        legacy.junit_import_changes[0].current,
    ):
        assert reference.status is None
        assert reference.withdrawal_event is None
        assert reference.context_sha256 == _ACTIVE_CONTEXT_SHA256
    assert legacy.junit_import_changes[0].kind.value == "unchanged"


@pytest.mark.parametrize("status", ["active", None])
def test_a_withdrawal_event_cannot_be_serialized_as_active_or_unavailable(status):
    state = _withdraw(junit_audit_state())
    reference = JUnitImportReference.from_import(
        state.bundle.junit_evidence_imports[0],
        withdrawal_event=state.bundle.junit_import_events[0],
    ).model_dump(mode="json")
    reference["status"] = status

    with pytest.raises(ValidationError):
        JUnitImportReference.model_validate(reference)


def test_withdrawn_status_requires_its_event_instead_of_a_bare_label():
    reference = JUnitImportReference.from_import(
        junit_audit_state().bundle.junit_evidence_imports[0],
    ).model_dump(mode="json")
    reference["status"] = "withdrawn"

    with pytest.raises(ValidationError):
        JUnitImportReference.model_validate(reference)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("import_id", "foreign-import"),
        ("artifact_sha256", "c" * 64),
        ("head_sha", "b" * 40),
        ("review_id", "foreign-review"),
        ("repository", "foreign/repository"),
        ("pr_number", 88),
        ("criteria_revision_number", 2),
        ("confirmed_criteria_sha256", "d" * 64),
    ],
)
def test_comparison_export_contract_rejects_a_foreign_withdrawal_owner(field, value):
    previous = junit_audit_state()
    current = _withdraw(previous)
    payload = compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")
    payload["junit_import_changes"][0]["current"]["withdrawal_event"][field] = value

    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_revision", "foreign-source-revision"),
        ("source_text_sha256", "e" * 64),
        ("confirmed_by", "CONSTRUCTED foreign criteria actor"),
    ],
)
def test_comparison_rejects_different_complete_withdrawal_provenance(field, value):
    previous = junit_audit_state()
    current = _withdraw(previous)
    payload = compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")
    event = payload["junit_import_changes"][0]["current"]["withdrawal_event"]
    event["criteria_source_provenance"][field] = value

    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


def test_withdrawn_comparison_cannot_discard_owning_context_and_keep_the_event():
    previous = junit_audit_state()
    current = _withdraw(previous)
    payload = compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")
    # Older comparisons may lack these projections; an owner-bound new audit may not.
    for field in (
        "decision_context_comparison", "final_acceptance_comparison",
        "selected_reference_comparison", "file_scope",
    ):
        payload.pop(field, None)

    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)
