"""Append-only review lifecycle operations independent of Streamlit state."""

from __future__ import annotations

from datetime import UTC, datetime

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.schemas.models import (
    CriteriaRevision,
    Criterion,
    HumanResolution,
    ResolutionEvent,
    ReviewBundle,
    ReviewState,
)


def new_review_state(bundle: ReviewBundle) -> ReviewState:
    """Initialize lifecycle state from an already validated analysis bundle."""
    revision = CriteriaRevision(
        number=1,
        criteria=bundle.criteria,
        source_text=bundle.source_text,
        confirmed=bundle.review.criteria_confirmed,
        confirmed_at=datetime.now(UTC) if bundle.review.criteria_confirmed else None,
    )
    return ReviewState(review=bundle.review, criteria_revision=revision, bundle=bundle)


def revise_criteria(
    state: ReviewState, criteria: list[Criterion], source_text: str
) -> ReviewState:
    """Create an unconfirmed revision and preserve the superseded analysis."""
    history = [*state.analysis_history]
    if state.bundle is not None:
        history.append(state.bundle)
    revision = CriteriaRevision(
        number=state.criteria_revision.number + 1,
        criteria=criteria,
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
    now = datetime.now(UTC)
    revision = state.criteria_revision.model_copy(update={"confirmed": True, "confirmed_at": now})
    review = state.review.model_copy(update={"criteria_confirmed": True, "final_acceptance": False})
    return state.model_copy(update={"criteria_revision": revision, "review": review})


def current_resolutions(
    events: list[ResolutionEvent], criteria_revision_number: int | None = None
) -> list[HumanResolution]:
    """Return the latest criterion decision in each revision, preserving event history elsewhere."""
    if criteria_revision_number is None:
        revision_numbers = [event.criteria_revision_number for event in events]
        criteria_revision_number = max(revision_numbers, default=1)
    latest: dict[str, ResolutionEvent] = {}
    for event in events:
        if event.criteria_revision_number != criteria_revision_number or event.criterion_id is None:
            continue
        latest[event.criterion_id] = event
    return [
        HumanResolution(
            criterion_id=event.criterion_id,
            decision=event.decision,
            comment=event.comment,
            evidence_url=event.evidence_url,
            claimed_evidence_level=event.claimed_evidence_level,
            reviewer=event.reviewer,
            timestamp=event.timestamp,
        )
        for _, event in sorted(latest.items())
    ]


def _final_acceptance(events: list[ResolutionEvent], revision_number: int) -> bool:
    final_events = [
        event
        for event in events
        if event.criteria_revision_number == revision_number and event.criterion_id is None
    ]
    return final_events[-1].final_acceptance if final_events else False


def _recalculate(state: ReviewState) -> ReviewState:
    if state.bundle is None:
        return state
    revision_number = state.criteria_revision.number
    review = state.review.model_copy(
        update={"final_acceptance": _final_acceptance(state.resolution_events, revision_number)}
    )
    resolutions = current_resolutions(state.resolution_events, revision_number)
    bundle = state.bundle.model_copy(deep=True)
    bundle.review = review
    bundle.resolutions = resolutions
    bundle.gate = evaluate_gate(bundle.review, bundle.criteria, bundle.findings, resolutions)
    return state.model_copy(update={"review": review, "bundle": bundle})


def append_resolution(state: ReviewState, event: ResolutionEvent) -> ReviewState:
    """Append an event, bind it to the active revision, and rerun the deterministic gate."""
    bound_event = event.model_copy(
        update={"criteria_revision_number": state.criteria_revision.number}
    )
    updated_events = [*state.resolution_events, bound_event]
    updated = state.model_copy(update={"resolution_events": updated_events})
    return _recalculate(updated)
