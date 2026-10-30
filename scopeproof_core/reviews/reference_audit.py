"""Append-only selected-reference lifecycle; no UI, fetching or execution."""

from __future__ import annotations

from datetime import UTC, datetime

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import (
    MAX_REVIEWER_SELECTED_REFERENCES,
    MAX_SELECTED_REFERENCE_EVENTS,
    MAX_SELECTED_REFERENCE_RECORDS,
    PullRequestSnapshot,
    RetrievedFile,
    ReviewBundle,
    ReviewerSelectedReference,
    ReviewState,
    SelectableReferenceLine,
    SelectedReferenceEvent,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def _owner(item: ReviewerSelectedReference | SelectedReferenceEvent) -> tuple:
    return (
        item.review_id,
        item.repository,
        item.pr_number,
        item.head_sha,
        item.criteria_revision_number,
        item.confirmed_criteria_sha256,
    )


def validate_reference_audit(
    references: list[ReviewerSelectedReference], events: list[SelectedReferenceEvent]
) -> None:
    """Validate terminal links in append order, independently of presentation fields."""
    if (
        len(references) > MAX_SELECTED_REFERENCE_RECORDS
        or len(events) > MAX_SELECTED_REFERENCE_EVENTS
    ):
        raise ValueError("selected reference audit history limit exceeded")
    positions = {item.reference_id: index for index, item in enumerate(references)}
    if len(positions) != len(references):
        raise ValueError("selected reference IDs must be unique")
    by_id = {item.reference_id: item for item in references}
    event_ids: set[str] = set()
    terminal: set[str] = set()
    incoming: set[str] = set()
    for event in events:
        target = by_id.get(event.reference_id)
        if event.event_id in event_ids:
            raise ValueError("selected reference event IDs must be unique")
        event_ids.add(event.event_id)
        if target is None or _owner(event) != _owner(target):
            raise ValueError("reference audit target must match its owning analysis")
        if event.reference_id in terminal:
            raise ValueError("reference audit target must be active")
        terminal.add(event.reference_id)
        if event.action == "corrected":
            replacement = by_id.get(event.replacement_reference_id)
            if (
                replacement is None
                or replacement.reference_id in incoming
                or replacement.reference_id in terminal
                or positions[replacement.reference_id] <= positions[target.reference_id]
                or _owner(replacement) != _owner(target)
                or replacement.criterion_id != target.criterion_id
                or replacement.criteria_source_provenance != target.criteria_source_provenance
                or replacement.reviewer != event.reviewer
                or replacement.selected_at != event.occurred_at
            ):
                raise ValueError("correction requires a later unique matching replacement")
            incoming.add(replacement.reference_id)
    active = [item for item in references if item.reference_id not in terminal]
    if len(active) > MAX_REVIEWER_SELECTED_REFERENCES:
        raise ValueError(
            f"analysis may contain at most {MAX_REVIEWER_SELECTED_REFERENCES} active references"
        )
    locations = [(r.criterion_id, r.source_scope, r.file_path, r.line_number) for r in active]
    if len(locations) != len(set(locations)):
        raise ValueError("active selected reference criterion locations must be unique")


def reference_status(
    references: list[ReviewerSelectedReference],
    events: list[SelectedReferenceEvent],
    reference_id: str,
) -> str:
    """Status from a validated collection; originals are retained for all outcomes."""
    validate_reference_audit(references, events)
    if reference_id not in {item.reference_id for item in references}:
        raise ValueError("unknown selected reference")
    return next((event.action for event in events if event.reference_id == reference_id), "active")


def active_references(bundle: ReviewBundle) -> list[ReviewerSelectedReference]:
    """Internal projection on an already validated owning bundle."""
    ids = set(bundle.active_reviewer_selected_reference_ids)
    return [item for item in bundle.reviewer_selected_references if item.reference_id in ids]


def _target(
    state: ReviewState, reference_id: str, expected: str
) -> tuple[ReviewState, ReviewerSelectedReference]:
    state = validated_review_state(state)
    if JsonReviewStore.state_fingerprint(state) != expected:
        raise ValueError("reference audit request is stale; refresh the active review")
    if state.review.final_acceptance:
        raise ValueError("revoke final acceptance before changing selected references")
    if state.bundle is None or not state.criteria_revision.confirmed:
        raise ValueError("reference audit requires a confirmed active analysis")
    target = next(
        (r for r in active_references(state.bundle) if r.reference_id == reference_id), None
    )
    if target is None:
        raise ValueError("reference audit target must be an active selected reference")
    return state, target


def _event(
    target: ReviewerSelectedReference,
    *,
    action: str,
    reviewer: str,
    reason: str,
    replacement: str | None = None,
    occurred_at: datetime | None = None,
) -> SelectedReferenceEvent:
    return SelectedReferenceEvent(
        action=action,
        reference_id=target.reference_id,
        replacement_reference_id=replacement,
        review_id=target.review_id,
        repository=target.repository,
        pr_number=target.pr_number,
        head_sha=target.head_sha,
        criteria_revision_number=target.criteria_revision_number,
        confirmed_criteria_sha256=target.confirmed_criteria_sha256,
        reviewer=reviewer,
        reason=reason,
        occurred_at=occurred_at or datetime.now(UTC),
    )


def withdraw_reviewer_selected_reference(
    state: ReviewState,
    *,
    reference_id: str,
    reviewer: str,
    reason: str,
    expected_state_fingerprint: str,
) -> ReviewState:
    state, target = _target(state, reference_id, expected_state_fingerprint)
    bundle = state.bundle.model_copy(deep=True)
    bundle.selected_reference_events.append(
        _event(target, action="withdrawn", reviewer=reviewer, reason=reason)
    )
    return validated_review_state(state.model_copy(update={"bundle": bundle}))


def correct_reviewer_selected_reference(
    state: ReviewState,
    *,
    reference_id: str,
    snapshot: PullRequestSnapshot,
    selected: SelectableReferenceLine,
    reviewer: str,
    rationale: str,
    reason: str,
    expected_state_fingerprint: str,
    unchanged_files: list[RetrievedFile] | None = None,
) -> ReviewState:
    from scopeproof_core.reviews.selected_references import _validated_selected_reference

    state, target = _target(state, reference_id, expected_state_fingerprint)
    replacement = _validated_selected_reference(
        state,
        snapshot=snapshot,
        selected=selected,
        criterion_id=target.criterion_id,
        reviewer=reviewer,
        rationale=rationale,
        unchanged_files=unchanged_files,
    )
    if (
        selected.model_dump(mode="python")
        == {key: getattr(target, key) for key in SelectableReferenceLine.model_fields}
        and replacement.reviewer == target.reviewer
        and replacement.rationale == target.rationale
    ):
        raise ValueError("correction must change the selected context or rationale")
    bundle = state.bundle.model_copy(deep=True)
    bundle.reviewer_selected_references.append(replacement)
    bundle.selected_reference_events.append(
        _event(
            target,
            action="corrected",
            reviewer=replacement.reviewer,
            reason=reason,
            replacement=replacement.reference_id,
            occurred_at=replacement.selected_at,
        )
    )
    return validated_review_state(state.model_copy(update={"bundle": bundle}))
