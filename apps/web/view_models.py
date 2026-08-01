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
