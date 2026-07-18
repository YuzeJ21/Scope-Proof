"""Deterministic comparisons between two validated ScopeProof review bundles."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from scopeproof_core.gates.validation import validated_review_bundle
from scopeproof_core.schemas.models import (
    EvidenceItem,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    FindingStatus,
    GateVerdict,
    HumanDecision,
    ReviewBundle,
)


class EvidenceChangeKind(StrEnum):
    """Observable relationship between previous and current evidence candidates."""

    UNCHANGED = "unchanged"
    RELOCATED = "relocated"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


class EvidenceReference(BaseModel):
    """Validated comparison projection of one immutable evidence candidate."""

    evidence_id: str
    criterion_id: str
    commit_sha: str
    file_path: str
    line_start: int
    line_end: int
    excerpt: str
    context_excerpt: str | None = None
    permalink: str
    evidence_type: EvidenceType
    evidence_level: EvidenceLevel
    source_scope: EvidenceSourceScope
    matching_rule: str
    relevance_reason: str

    @classmethod
    def from_item(cls, item: EvidenceItem) -> EvidenceReference:
        """Project a validated evidence item without adapter or credential state."""

        return cls.model_validate(
            item.model_dump(
                include={
                    "evidence_id",
                    "criterion_id",
                    "commit_sha",
                    "file_path",
                    "line_start",
                    "line_end",
                    "excerpt",
                    "context_excerpt",
                    "permalink",
                    "evidence_type",
                    "evidence_level",
                    "source_scope",
                    "matching_rule",
                    "relevance_reason",
                }
            )
        )


class EvidenceChange(BaseModel):
    """One fail-closed evidence relationship across two review bundles."""

    criterion_id: str
    kind: EvidenceChangeKind
    previous: EvidenceReference | None = None
    current: EvidenceReference | None = None
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def _reason_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence change reason must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def _references_match_kind_and_criterion(self) -> EvidenceChange:
        paired = {
            EvidenceChangeKind.UNCHANGED,
            EvidenceChangeKind.RELOCATED,
            EvidenceChangeKind.MODIFIED,
        }
        if self.kind in paired and (self.previous is None or self.current is None):
            raise ValueError("paired evidence changes require previous and current references")
        if self.kind is EvidenceChangeKind.ADDED and (
            self.previous is not None or self.current is None
        ):
            raise ValueError("added evidence changes require only a current reference")
        if self.kind is EvidenceChangeKind.REMOVED and (
            self.previous is None or self.current is not None
        ):
            raise ValueError("removed evidence changes require only a previous reference")
        for reference in (self.previous, self.current):
            if reference is not None and reference.criterion_id != self.criterion_id:
                raise ValueError("evidence change references must use the change criterion ID")
        return self


class EvidenceChangeCounts(BaseModel):
    unchanged: int = Field(ge=0)
    relocated: int = Field(ge=0)
    modified: int = Field(ge=0)
    added: int = Field(ge=0)
    removed: int = Field(ge=0)


class FindingStatusChange(BaseModel):
    criterion_id: str
    previous_status: FindingStatus | None
    current_status: FindingStatus | None


class ResolutionChange(BaseModel):
    criterion_id: str
    previous_decision: HumanDecision | None
    current_decision: HumanDecision | None


class ReviewComparison(BaseModel):
    previous_head_sha: str
    current_head_sha: str
    evidence_changes: list[EvidenceChange]
    changed_finding_statuses: list[FindingStatusChange]
    changed_human_resolutions: list[ResolutionChange]
    previous_gate: GateVerdict
    current_gate: GateVerdict
    ruleset_version_changed: bool

    @computed_field
    @property
    def evidence_change_counts(self) -> EvidenceChangeCounts:
        return EvidenceChangeCounts(
            **{
                kind.value: sum(change.kind is kind for change in self.evidence_changes)
                for kind in EvidenceChangeKind
            }
        )

    @property
    def added_evidence_ids(self) -> list[str]:
        return sorted(
            change.current.evidence_id
            for change in self.evidence_changes
            if change.kind is EvidenceChangeKind.ADDED and change.current is not None
        )

    @property
    def removed_evidence_ids(self) -> list[str]:
        return sorted(
            change.previous.evidence_id
            for change in self.evidence_changes
            if change.kind is EvidenceChangeKind.REMOVED and change.previous is not None
        )


def _normalized_excerpt(value: str) -> str:
    return "\n".join(
        line.strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    )


def _reference_sort_key(reference: EvidenceReference) -> tuple:
    return (
        reference.criterion_id,
        reference.evidence_type.value,
        reference.source_scope.value,
        reference.file_path,
        reference.line_start,
        reference.line_end,
        _normalized_excerpt(reference.excerpt),
        reference.commit_sha,
        reference.permalink,
        reference.evidence_id,
    )


def _exact_signature(reference: EvidenceReference) -> tuple:
    return (
        reference.commit_sha,
        reference.file_path,
        reference.line_start,
        reference.line_end,
        _normalized_excerpt(reference.excerpt),
        reference.evidence_type,
        reference.source_scope,
        reference.matching_rule,
        reference.permalink,
    )


def _relocated_signature(reference: EvidenceReference) -> tuple:
    return (
        _normalized_excerpt(reference.excerpt),
        reference.evidence_type,
        reference.source_scope,
        reference.matching_rule,
    )


def _modified_signature(reference: EvidenceReference) -> tuple:
    return (
        reference.file_path,
        reference.evidence_type,
        reference.source_scope,
        reference.matching_rule,
    )


def _relocation_reason(previous: EvidenceReference, current: EvidenceReference) -> str:
    changed: list[str] = []
    if previous.commit_sha != current.commit_sha:
        changed.append("commit")
    if previous.file_path != current.file_path:
        changed.append("path")
    if (previous.line_start, previous.line_end) != (current.line_start, current.line_end):
        changed.append("line range")
    fields = ", ".join(changed) or "immutable reference"
    return f"Candidate {fields} changed; review the current evidence before a new decision."


def _change(
    kind: EvidenceChangeKind,
    *,
    previous: EvidenceReference | None = None,
    current: EvidenceReference | None = None,
) -> EvidenceChange:
    reference = current or previous
    if reference is None:
        raise ValueError("an evidence change requires at least one reference")
    reasons = {
        EvidenceChangeKind.UNCHANGED: "Candidate reference is unchanged between the two reviews.",
        EvidenceChangeKind.MODIFIED: (
            "Candidate excerpt changed at the same deterministic file identity; review the "
            "current evidence before a new decision."
        ),
        EvidenceChangeKind.ADDED: "Candidate appears only in the current review.",
        EvidenceChangeKind.REMOVED: "Candidate appears only in the previous review.",
    }
    reason = (
        _relocation_reason(previous, current)
        if kind is EvidenceChangeKind.RELOCATED and previous is not None and current is not None
        else reasons[kind]
    )
    return EvidenceChange(
        criterion_id=reference.criterion_id,
        kind=kind,
        previous=previous,
        current=current,
        reason=reason,
    )


def _pair_first(
    previous: list[EvidenceReference],
    current: list[EvidenceReference],
    consumed_previous: set[int],
    consumed_current: set[int],
    signature,
    kind: EvidenceChangeKind,
) -> list[EvidenceChange]:
    changes: list[EvidenceChange] = []
    for previous_index, previous_reference in enumerate(previous):
        if previous_index in consumed_previous:
            continue
        previous_signature = signature(previous_reference)
        current_index = next(
            (
                index
                for index, reference in enumerate(current)
                if index not in consumed_current and signature(reference) == previous_signature
            ),
            None,
        )
        if current_index is None:
            continue
        consumed_previous.add(previous_index)
        consumed_current.add(current_index)
        changes.append(
            _change(kind, previous=previous_reference, current=current[current_index])
        )
    return changes


_KIND_ORDER = {
    EvidenceChangeKind.MODIFIED: 0,
    EvidenceChangeKind.RELOCATED: 1,
    EvidenceChangeKind.ADDED: 2,
    EvidenceChangeKind.REMOVED: 3,
    EvidenceChangeKind.UNCHANGED: 4,
}


def _change_sort_key(change: EvidenceChange) -> tuple:
    reference = change.current or change.previous
    if reference is None:
        raise ValueError("an evidence change requires at least one reference")
    return (
        change.criterion_id,
        _KIND_ORDER[change.kind],
        reference.file_path,
        reference.line_start,
        reference.line_end,
        reference.evidence_id,
    )


def _compare_evidence(
    previous_items: list[EvidenceItem], current_items: list[EvidenceItem]
) -> list[EvidenceChange]:
    changes: list[EvidenceChange] = []
    criteria = sorted(
        {item.criterion_id for item in previous_items}
        | {item.criterion_id for item in current_items}
    )
    for criterion_id in criteria:
        previous = sorted(
            (
                EvidenceReference.from_item(item)
                for item in previous_items
                if item.criterion_id == criterion_id
            ),
            key=_reference_sort_key,
        )
        current = sorted(
            (
                EvidenceReference.from_item(item)
                for item in current_items
                if item.criterion_id == criterion_id
            ),
            key=_reference_sort_key,
        )
        consumed_previous: set[int] = set()
        consumed_current: set[int] = set()
        changes.extend(
            _pair_first(
                previous,
                current,
                consumed_previous,
                consumed_current,
                _exact_signature,
                EvidenceChangeKind.UNCHANGED,
            )
        )
        changes.extend(
            _pair_first(
                previous,
                current,
                consumed_previous,
                consumed_current,
                _relocated_signature,
                EvidenceChangeKind.RELOCATED,
            )
        )
        changes.extend(
            _pair_first(
                previous,
                current,
                consumed_previous,
                consumed_current,
                _modified_signature,
                EvidenceChangeKind.MODIFIED,
            )
        )
        changes.extend(
            _change(EvidenceChangeKind.REMOVED, previous=reference)
            for index, reference in enumerate(previous)
            if index not in consumed_previous
        )
        changes.extend(
            _change(EvidenceChangeKind.ADDED, current=reference)
            for index, reference in enumerate(current)
            if index not in consumed_current
        )
    return sorted(changes, key=_change_sort_key)


def _finding_statuses(bundle: ReviewBundle) -> dict[str, FindingStatus]:
    return {finding.criterion_id: finding.status for finding in bundle.findings}


def _resolution_decisions(bundle: ReviewBundle) -> dict[str, HumanDecision]:
    return {resolution.criterion_id: resolution.decision for resolution in bundle.resolutions}


def compare_reviews(previous: ReviewBundle, current: ReviewBundle) -> ReviewComparison:
    """Compare stable review facts without treating evidence IDs as semantic identity."""

    previous = validated_review_bundle(previous)
    current = validated_review_bundle(current)
    previous_findings = _finding_statuses(previous)
    current_findings = _finding_statuses(current)
    previous_resolutions = _resolution_decisions(previous)
    current_resolutions = _resolution_decisions(current)
    changed_findings = [
        FindingStatusChange(
            criterion_id=criterion_id,
            previous_status=previous_findings.get(criterion_id),
            current_status=current_findings.get(criterion_id),
        )
        for criterion_id in sorted(set(previous_findings) | set(current_findings))
        if previous_findings.get(criterion_id) != current_findings.get(criterion_id)
    ]
    changed_resolutions = [
        ResolutionChange(
            criterion_id=criterion_id,
            previous_decision=previous_resolutions.get(criterion_id),
            current_decision=current_resolutions.get(criterion_id),
        )
        for criterion_id in sorted(set(previous_resolutions) | set(current_resolutions))
        if previous_resolutions.get(criterion_id) != current_resolutions.get(criterion_id)
    ]
    return ReviewComparison(
        previous_head_sha=previous.review.head_sha,
        current_head_sha=current.review.head_sha,
        evidence_changes=_compare_evidence(previous.evidence, current.evidence),
        changed_finding_statuses=changed_findings,
        changed_human_resolutions=changed_resolutions,
        previous_gate=previous.gate.verdict,
        current_gate=current.gate.verdict,
        ruleset_version_changed=(
            previous.review.ruleset_version != current.review.ruleset_version
        ),
    )
