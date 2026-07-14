"""Derive current human review state from append-only resolution events."""

from scopeproof_core.schemas.models import HumanResolution, ResolutionEvent


def current_resolutions(
    events: list[ResolutionEvent], criteria_revision_number: int | None = None
) -> list[HumanResolution]:
    """Return the latest criterion decision for the selected criteria revision."""
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


def final_acceptance(events: list[ResolutionEvent], criteria_revision_number: int) -> bool:
    """Return the latest final-acceptance decision for a criteria revision."""
    final_events = [
        event
        for event in events
        if event.criteria_revision_number == criteria_revision_number
        and event.criterion_id is None
    ]
    return final_events[-1].final_acceptance if final_events else False
