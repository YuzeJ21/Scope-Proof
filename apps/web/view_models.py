"""Pure presentation models for the local ScopeProof workbench."""

from __future__ import annotations

from dataclasses import dataclass

from scopeproof_core.schemas.models import EvidenceItem, EvidenceType


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
