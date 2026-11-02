"""Append-only withdrawal of external JUnit context, independent of UI or execution."""

from datetime import datetime
from typing import Literal

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import (
    JUnitImportWithdrawalEvent,
    ReviewBundle,
    ReviewState,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def junit_import_withdrawal_event(
    bundle: ReviewBundle,
    import_id: str,
) -> JUnitImportWithdrawalEvent | None:
    """Project one terminal event from a validated owning bundle."""
    if import_id not in {item.import_id for item in bundle.junit_evidence_imports}:
        raise ValueError("unknown retained JUnit import")
    return next(
        (event for event in bundle.junit_import_events if event.import_id == import_id),
        None,
    )


def junit_import_status(bundle: ReviewBundle, import_id: str) -> Literal["active", "withdrawn"]:
    return "withdrawn" if junit_import_withdrawal_event(bundle, import_id) else "active"


def junit_withdrawal_fields(event: JUnitImportWithdrawalEvent) -> list[tuple[str, str]]:
    """Plain recorded audit fields shared by UI and readable reports."""
    provenance = event.criteria_source_provenance
    return [
        ("Withdrawal event ID", event.event_id),
        ("Withdrawal schema", event.schema_version),
        ("Withdrawal action", event.action),
        ("Withdrawn import ID", event.import_id),
        ("Withdrawal artifact SHA-256", event.artifact_sha256),
        ("Owning review ID", event.review_id),
        ("Bound repository", event.repository),
        ("Bound PR", str(event.pr_number)),
        ("Bound head", event.head_sha),
        ("Criteria revision", str(event.criteria_revision_number)),
        ("Confirmed criteria SHA-256", event.confirmed_criteria_sha256),
        ("Criteria source URI", provenance.source_uri),
        ("Criteria source revision", provenance.source_revision or "Not recorded"),
        ("Criteria source text SHA-256", provenance.source_text_sha256),
        ("Criteria source normalized SHA-256", provenance.normalized_criteria_sha256),
        ("Criteria confirmer", provenance.confirmed_by),
        ("Criteria confirmed at (UTC)", provenance.confirmed_at.isoformat()),
        ("Withdrawal reviewer", event.reviewer),
        ("Withdrawal reason", event.reason),
        ("Withdrawn at (UTC)", event.occurred_at.isoformat()),
        ("Withdrawal evidence boundary", event.evidence_boundary.model_dump_json()),
    ]


def _without_audit(state: ReviewState) -> dict:
    data = state.model_dump(mode="python")
    if data["bundle"] is not None:
        data["bundle"].pop("junit_import_events", None)
        data["bundle"].pop("active_junit_import_ids", None)
    return data


def withdraw_junit_evidence_import(
    state: ReviewState,
    *,
    import_id: str,
    reviewer: str,
    reason: str,
    expected_state_fingerprint: str,
    occurred_at: datetime | None = None,
) -> ReviewState:
    """Retire a complete saved import while preserving all non-audit review truth."""
    state = validated_review_state(state)
    if JsonReviewStore.state_fingerprint(state) != expected_state_fingerprint:
        raise ValueError("JUnit withdrawal request is stale; reopen the saved review")
    if state.bundle is None or not state.criteria_revision.confirmed:
        raise ValueError("JUnit withdrawal requires a confirmed active analysis")
    target = next(
        (item for item in state.bundle.junit_evidence_imports if item.import_id == import_id), None
    )
    if target is None or import_id not in state.bundle.active_junit_import_ids:
        raise ValueError("JUnit withdrawal target must be an active retained import")
    data = dict(
        import_id=target.import_id,
        artifact_sha256=target.artifact_sha256,
        review_id=state.review.review_id,
        repository=target.repository,
        pr_number=target.pr_number,
        head_sha=target.head_sha,
        criteria_revision_number=target.criteria_revision_number,
        confirmed_criteria_sha256=target.confirmed_criteria_sha256,
        criteria_source_provenance=target.criteria_source_provenance.model_copy(deep=True),
        reviewer=reviewer,
        reason=reason,
    )
    if occurred_at is not None:
        data["occurred_at"] = occurred_at
    event = JUnitImportWithdrawalEvent(**data)
    updated = state.model_copy(deep=True)
    updated.bundle.junit_import_events.append(event)
    updated = validated_review_state(updated)
    if _without_audit(updated) != _without_audit(state):
        raise ValueError("JUnit withdrawal must not alter deterministic or reviewer truth")
    return updated
