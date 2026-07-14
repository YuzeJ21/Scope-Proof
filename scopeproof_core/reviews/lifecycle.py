"""Append-only review lifecycle operations independent of Streamlit state."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import (
    validated_review_bundle,
    validated_review_state,
)
from scopeproof_core.resolution_events import current_resolutions, final_acceptance
from scopeproof_core.schemas.models import (
    CriteriaRevision,
    Criterion,
    ResolutionEvent,
    ReviewBundle,
    ReviewState,
    RuntimeEvidence,
)


class ResolutionEventStatus(StrEnum):
    """Whether an append-only event currently supplies active-revision state."""

    CURRENT = "current"
    SUPERSEDED = "superseded"
    PRIOR_REVISION = "prior_revision"


def _validated_state(state: ReviewState) -> ReviewState:
    """Revalidate mutable model input before applying a lifecycle transition."""
    return validated_review_state(state)


def new_review_state(bundle: ReviewBundle) -> ReviewState:
    """Initialize lifecycle state from a revalidated analysis bundle."""
    bundle = validated_review_bundle(bundle)
    if bundle.resolutions:
        raise ValueError("initial analysis bundle must not contain human resolutions")
    if bundle.review.final_acceptance:
        raise ValueError("initial analysis bundle must not contain final acceptance")
    active_bundle = bundle.model_copy(deep=True)
    revision = CriteriaRevision(
        number=1,
        criteria=[criterion.model_copy(deep=True) for criterion in bundle.criteria],
        source_text=bundle.source_text,
        confirmed=bundle.review.criteria_confirmed,
        confirmed_at=datetime.now(UTC) if bundle.review.criteria_confirmed else None,
    )
    return ReviewState(
        review=bundle.review.model_copy(deep=True),
        criteria_revision=revision,
        bundle=active_bundle,
    )


def revise_criteria(
    state: ReviewState, criteria: list[Criterion], source_text: str
) -> ReviewState:
    """Create an unconfirmed revision and preserve the superseded analysis."""
    state = _validated_state(state)
    history = [*state.analysis_history]
    if state.bundle is not None:
        history.append(state.bundle)
    validated_criteria = [
        Criterion.model_validate(criterion.model_dump(mode="python")) for criterion in criteria
    ]
    revision = CriteriaRevision(
        number=state.criteria_revision.number + 1,
        criteria=validated_criteria,
        source_text=source_text,
    )
    review = state.review.model_copy(
        update={"criteria_confirmed": False, "final_acceptance": False}
    )
    return state.model_copy(
        update={
            "review": review,
            "criteria_revision": revision,
            "bundle": None,
            "analysis_history": history,
        }
    )


def confirm_criteria(state: ReviewState) -> ReviewState:
    """Mark the active revision confirmed without manufacturing an analysis."""
    state = _validated_state(state)
    if state.bundle is not None:
        raise ValueError(
            "criteria confirmation requires a pending revision without an active bundle"
        )
    now = datetime.now(UTC)
    revision = state.criteria_revision.model_copy(update={"confirmed": True, "confirmed_at": now})
    review = state.review.model_copy(update={"criteria_confirmed": True, "final_acceptance": False})
    return state.model_copy(update={"criteria_revision": revision, "review": review})


def attach_analysis(state: ReviewState, bundle: ReviewBundle) -> ReviewState:
    """Attach validated static analysis to a confirmed pending revision."""
    state = _validated_state(state)
    bundle = validated_review_bundle(bundle)
    if state.bundle is not None:
        raise ValueError(
            "analysis attachment requires a pending revision without an active bundle"
        )
    if not state.criteria_revision.confirmed:
        raise ValueError("analysis attachment requires a confirmed criteria revision")
    if bundle.resolutions:
        raise ValueError("attached analysis must not contain human resolutions")
    if bundle.review.final_acceptance:
        raise ValueError("attached analysis must not contain final acceptance")
    if bundle.criteria != state.criteria_revision.criteria:
        raise ValueError("attached analysis criteria must match the active revision")
    if bundle.source_text != state.criteria_revision.source_text:
        raise ValueError("attached analysis source must match the active revision")
    rebound_review = bundle.review.model_copy(
        update={
            "review_id": state.review.review_id,
            "created_at": state.review.created_at,
        }
    )
    if rebound_review != state.review:
        raise ValueError("attached analysis review must match the lifecycle review")
    active_bundle = bundle.model_copy(deep=True)
    active_bundle.review = state.review.model_copy(deep=True)
    return validated_review_state(state.model_copy(update={"bundle": active_bundle}))


def resolution_event_statuses(
    events: list[ResolutionEvent], active_revision_number: int
) -> list[ResolutionEventStatus]:
    """Classify events without changing their append-only order or gate semantics."""
    latest_by_target: dict[tuple[bool, str | None], int] = {}
    for index, event in enumerate(events):
        if event.criteria_revision_number != active_revision_number:
            continue
        target = (event.criterion_id is None, event.criterion_id)
        latest_by_target[target] = index

    statuses: list[ResolutionEventStatus] = []
    for index, event in enumerate(events):
        if event.criteria_revision_number != active_revision_number:
            statuses.append(ResolutionEventStatus.PRIOR_REVISION)
            continue
        target = (event.criterion_id is None, event.criterion_id)
        status = (
            ResolutionEventStatus.CURRENT
            if latest_by_target[target] == index
            else ResolutionEventStatus.SUPERSEDED
        )
        statuses.append(status)
    return statuses


def _recalculate(state: ReviewState) -> ReviewState:
    if state.bundle is None:
        return state
    revision_number = state.criteria_revision.number
    review = state.review.model_copy(
        update={"final_acceptance": final_acceptance(state.resolution_events, revision_number)}
    )
    resolutions = current_resolutions(state.resolution_events, revision_number)
    bundle = state.bundle.model_copy(deep=True)
    bundle.review = review
    bundle.resolutions = resolutions
    bundle.gate = evaluate_gate(bundle.review, bundle.criteria, bundle.findings, resolutions)
    return state.model_copy(update={"review": review, "bundle": bundle})


def append_resolution(state: ReviewState, event: ResolutionEvent) -> ReviewState:
    """Append an event, bind it to the active revision, and rerun the deterministic gate."""
    state = _validated_state(state)
    event = ResolutionEvent.model_validate(event.model_dump())
    if any(existing.event_id == event.event_id for existing in state.resolution_events):
        raise ValueError("resolution event ID must be unique")
    if state.bundle is None:
        raise ValueError("Run a confirmed analysis before recording a resolution")
    if event.criterion_id is not None and event.criterion_id not in {
        criterion.criterion_id for criterion in state.bundle.criteria
    }:
        raise ValueError("resolution event must reference a criterion in the active review")
    bound_event = ResolutionEvent.model_validate(
        {
            **event.model_dump(),
            "criteria_revision_number": state.criteria_revision.number,
        }
    )
    updated_events = [*state.resolution_events, bound_event]
    updated = state.model_copy(update={"resolution_events": updated_events})
    return _recalculate(updated)


def append_runtime_evidence(state: ReviewState, evidence: RuntimeEvidence) -> ReviewState:
    """Append a manual runtime record without upgrading static findings or gate truth."""

    state = _validated_state(state)
    evidence = RuntimeEvidence.model_validate(evidence.model_dump())
    if state.bundle is None:
        raise ValueError("Run a confirmed analysis before recording runtime evidence")
    if evidence.criterion_id not in {criterion.criterion_id for criterion in state.bundle.criteria}:
        raise ValueError("runtime evidence must reference a criterion in the active review")
    bundle = state.bundle.model_copy(deep=True)
    bundle.runtime_evidence.append(evidence)
    return state.model_copy(update={"bundle": bundle})
