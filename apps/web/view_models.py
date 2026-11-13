"""Pure presentation models for the local ScopeProof workbench."""

from __future__ import annotations

from dataclasses import dataclass

from scopeproof_core.reviews.lifecycle import FinalAcceptanceBlocker
from scopeproof_core.schemas.models import (
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    IngestionState,
    ReviewBundle,
)

EXTERNAL_VERIFICATION_LABEL = "Record optional external verification (E3/E4)"

FINAL_ACCEPTANCE_BLOCKER_GUIDANCE = {
    FinalAcceptanceBlocker.ANALYSIS_REQUIRED: (
        "Confirm criteria and run analysis before recording final acceptance."
    ),
    FinalAcceptanceBlocker.CRITERIA_CONFIRMATION_REQUIRED: (
        "Confirm the criteria and their source before recording final acceptance."
    ),
    FinalAcceptanceBlocker.INCOMPLETE_INGESTION: (
        "The reviewed source is incomplete. Reload the pull request and run a confirmed analysis."
    ),
    FinalAcceptanceBlocker.CHECKS_FAILING: (
        "Observed GitHub checks are failing. Review them on the pull request, "
        "then check the current head."
    ),
    FinalAcceptanceBlocker.CHECKS_PENDING: (
        "Observed GitHub checks are pending. Wait for them to finish, then check the current head."
    ),
    FinalAcceptanceBlocker.CHECKS_UNAVAILABLE: (
        "Passing GitHub checks could not be confirmed. Check the current head when results "
        "are available."
    ),
    FinalAcceptanceBlocker.CHANGED_FILE_INVENTORY_UNAVAILABLE: (
        "The changed-file inventory is unavailable. Check the current head and run "
        "a new confirmed analysis."
    ),
    FinalAcceptanceBlocker.UNRESOLVED_FILE_SCOPE: (
        "Changed-file scope is unresolved. Review the uncited files and record their scope "
        "or obtain criterion evidence."
    ),
    FinalAcceptanceBlocker.CRITERION_DECISIONS_REQUIRED: (
        "Review criteria without a decision or marked Change required or Rejected finding "
        "before recording final acceptance."
    ),
    FinalAcceptanceBlocker.UNLINKED_MANUAL_VERIFICATION: (
        "Record external verification at the required level for criteria with unlinked "
        "manual verification."
    ),
}


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

    e3_ids = {
        criterion.criterion_id
        for criterion in bundle.criteria
        if criterion.required_evidence_level is EvidenceLevel.E3
    }
    # The bundle validates this link at the reviewed head. Legacy observations can
    # have migrated IDs while their decisions still require fresh verification.
    verified_ids = {
        resolution.criterion_id
        for resolution in bundle.resolutions
        if resolution.runtime_evidence_id is not None
    }
    for finding in bundle.findings:
        criterion_id = finding.criterion_id
        if criterion_id not in e3_ids or finding.evidence_level.rank >= EvidenceLevel.E3.rank:
            continue
        if criterion_id in verified_ids:
            actions[criterion_id] = "Review the recorded external verification for this criterion."
        elif suggest_external_verification and not review.final_acceptance:
            actions[criterion_id] = (
                "If external runtime results support verification at the reviewed PR head, "
                f"open {EXTERNAL_VERIFICATION_LABEL} and record them at E3 for this criterion."
            )
    return actions


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
