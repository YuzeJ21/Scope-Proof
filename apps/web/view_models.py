"""Pure presentation models for the local ScopeProof workbench."""

from __future__ import annotations

from dataclasses import dataclass

from scopeproof_core.schemas.models import (
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    HumanDecision,
    HumanResolution,
    IngestionState,
    ReviewBundle,
)

EXTERNAL_VERIFICATION_LABEL = "Record optional external verification (E3/E4)"


def criterion_next_actions(
    bundle: ReviewBundle, *, suggest_external_verification: bool
) -> dict[str, str]:
    """Derive workbench guidance from findings and current verification decisions."""
    actions = {finding.criterion_id: finding.recommended_action for finding in bundle.findings}
    review = bundle.review
    if (
        review.ingestion_state is not IngestionState.COMPLETE
        or review.ingestion_warnings
        or review.skipped_files
    ):
        return actions

    required_levels = {
        criterion.criterion_id: criterion.required_evidence_level for criterion in bundle.criteria
    }
    # The bundle validates this link at the reviewed head. Legacy observations can
    # have migrated IDs while their decisions still require fresh verification.
    resolutions = {resolution.criterion_id: resolution for resolution in bundle.resolutions}
    for finding in bundle.findings:
        criterion_id = finding.criterion_id
        required_level = required_levels[criterion_id]
        resolution = resolutions.get(criterion_id)
        if required_level is EvidenceLevel.E4:
            actions[criterion_id] = _e4_next_action(
                resolution,
                final_acceptance=review.final_acceptance,
                can_record=suggest_external_verification,
            )
            continue
        if (
            required_level is not EvidenceLevel.E3
            or finding.evidence_level.rank >= EvidenceLevel.E3.rank
        ):
            continue
        if resolution is not None and resolution.runtime_evidence_id is not None:
            actions[criterion_id] = "Review the recorded external verification for this criterion."
        elif suggest_external_verification and not review.final_acceptance:
            actions[criterion_id] = (
                "If external runtime results support verification at the reviewed PR head, "
                f"open {EXTERNAL_VERIFICATION_LABEL} and record them at E3 for this criterion."
            )
    return actions


def _e4_next_action(
    resolution: HumanResolution | None, *, final_acceptance: bool, can_record: bool,
) -> str:
    linked_level = (
        resolution.claimed_evidence_level
        if resolution is not None and resolution.runtime_evidence_id is not None else None
    )
    if linked_level is EvidenceLevel.E4:
        return "Review the recorded E4 verification for this criterion."
    context = (
        f"Recorded {linked_level.value} verification is below the E4 requirement. "
        if linked_level is not None else "No current linked E4 verification is recorded. "
    )
    if not can_record:
        return context + "Follow the workbench recovery guidance before recording E4 verification."
    if final_acceptance:
        if resolution is not None and resolution.decision is HumanDecision.MANUALLY_VERIFIED:
            return context + "Revoke final acceptance before replacing manual verification."
        return context + "Review the recorded criterion decision and final acceptance."
    return (
        context + "If you have explicit human acceptance for the reviewed PR head, open "
        f"{EXTERNAL_VERIFICATION_LABEL} and record it at E4 for this criterion."
    )


@dataclass(frozen=True)
class EvidenceGroup:
    """One display-only group that preserves validated evidence item order."""

    file_path: str
    evidence_type: EvidenceType
    items: tuple[EvidenceItem, ...]


def group_candidate_evidence(items: list[EvidenceItem]) -> list[EvidenceGroup]:
    """Group by path and type without sorting, deduplicating, or rewriting items."""
    grouped: dict[tuple[str, EvidenceType], list[EvidenceItem]] = {}
    for item in items:
        grouped.setdefault((item.file_path, item.evidence_type), []).append(item)
    return [
        EvidenceGroup(file_path=path, evidence_type=evidence_type, items=tuple(group_items))
        for (path, evidence_type), group_items in grouped.items()
    ]


def prioritize_unresolved_criterion_ids(
    *, unresolved_ids: list[str], blocking_ids: set[str]
) -> list[str]:
    """Return blockers first while preserving order within both groups."""
    return [
        *(criterion_id for criterion_id in unresolved_ids if criterion_id in blocking_ids),
        *(criterion_id for criterion_id in unresolved_ids if criterion_id not in blocking_ids),
    ]


def default_criterion_detail_id(
    *,
    criterion_ids: list[str],
    unresolved_ids: list[str],
    blocking_ids: set[str],
    selected_id: str | None,
) -> str | None:
    """Return a reachable detail target without rewriting a valid selection."""
    if selected_id in criterion_ids:
        return selected_id
    return (
        next(
            (
                criterion_id
                for criterion_id in unresolved_ids
                if criterion_id in blocking_ids
            ),
            None,
        )
        or next(iter(unresolved_ids), None)
        or next(iter(criterion_ids), None)
    )
