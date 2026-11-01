"""Read-only resolution-event presentation shared by workbench and readable reports."""

from scopeproof_core.reviews.lifecycle import ResolutionEventStatus
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent

LEGACY_RUNTIME_LINK = "Legacy unlinked; re-record at the active head"
RESOLUTION_HISTORY_EMPTY = "No resolution events were recorded for this saved review."
RESOLUTION_HISTORY_BOUNDARY = (
    "Current events are the latest recorded inputs for their target in the active criteria "
    "revision. Superseded and prior-revision events remain audit history and do not "
    "independently control the gate. Reviewer names and timestamps are recorded assertions, "
    "not authenticated identity or runtime verification. Events do not record historical "
    "heads or criteria-source provenance; none is inferred here. Review-level flags are "
    "shown only as recorded values."
)


def _recorded_resolution_value(value: str | None) -> str:
    if value is None:
        return "Not recorded"
    return value if value else "Empty value recorded"


def resolution_history_event_fields(
    event: ResolutionEvent, status: ResolutionEventStatus,
) -> list[tuple[str, str]]:
    """Project only recorded fields from events in an already validated review state."""
    recorded_at = event.timestamp.isoformat()
    if event.timestamp.utcoffset() is None:
        recorded_at += " (timezone not recorded)"
    criterion_target = event.criterion_id is not None
    if criterion_target:
        assert event.decision is not None  # Guaranteed by the validated event kind.
        outcome = event.decision.value
    else:
        outcome = f"final_acceptance={str(event.final_acceptance).lower()}"
    additional_fields: list[tuple[str, str]] = []
    if not criterion_target and event.decision is not None:
        additional_fields.append((
            "Additional decision field (not applied to this target)", event.decision.value,
        ))
    if criterion_target and event.final_acceptance is not None:
        additional_fields.append((
            "Additional final-acceptance field (not applied to this target)",
            str(event.final_acceptance).lower(),
        ))
    context_suffix = (
        " (not applied to this target)"
        if not criterion_target and event.decision is HumanDecision.MANUALLY_VERIFIED else ""
    )
    runtime_link = (
        LEGACY_RUNTIME_LINK
        if criterion_target and event.decision is HumanDecision.MANUALLY_VERIFIED
        and event.runtime_evidence_id is None
        else _recorded_resolution_value(event.runtime_evidence_id)
    )
    status_label = {
        ResolutionEventStatus.CURRENT: "Current",
        ResolutionEventStatus.SUPERSEDED: "Superseded",
        ResolutionEventStatus.PRIOR_REVISION: "Prior revision",
    }[status]
    return [
        ("Event ID", event.event_id),
        ("Event status", status_label),
        ("Criteria revision", str(event.criteria_revision_number)),
        ("Target", event.criterion_id if event.criterion_id is not None else "Final acceptance"),
        ("Recorded outcome", outcome),
        *additional_fields,
        ("Asserted reviewer", event.reviewer),
        ("Recorded at (as recorded)", recorded_at),
        ("Reviewer note", _recorded_resolution_value(event.comment)),
        ("Evidence URL (as recorded)", _recorded_resolution_value(event.evidence_url)),
        ("Claimed evidence level" + context_suffix, _recorded_resolution_value(
            event.claimed_evidence_level.value
            if event.claimed_evidence_level is not None else None,
        )),
        ("Runtime evidence link" + context_suffix, runtime_link),
    ]


