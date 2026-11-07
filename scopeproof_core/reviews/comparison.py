"""Deterministic comparisons between two validated ScopeProof review bundles."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from scopeproof_core.gates.validation import validated_review_bundle
from scopeproof_core.reviews.decision_context_comparison import DecisionContextComparison
from scopeproof_core.reviews.final_acceptance_comparison import FinalAcceptanceComparison
from scopeproof_core.reviews.scope_comparison import FileScopeComparison, FileScopeSnapshot
from scopeproof_core.reviews.selected_reference_comparison import SelectedReferenceComparison
from scopeproof_core.schemas.models import (
    MAX_JUNIT_MAPPING_CORRECTIONS_PER_REVIEW,
    EvidenceItem,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    FindingStatus,
    GateVerdict,
    HumanDecision,
    JUnitCriterionMapping,
    JUnitEvidenceBoundary,
    JUnitEvidenceImport,
    JUnitImportEvent,
    JUnitImportWithdrawalEvent,
    JUnitMappingCorrectionEvent,
    ReviewBundle,
    ReviewInputOrigin,
    junit_mapping_sha256,
    replay_junit_mapping_events,
)

_EXACT_GIT_HEAD = re.compile(r"^[0-9a-f]{40}$")
GATE_REASON_COMPARISON_BOUNDARY = (
    "These are the reasons reported for each analysis under the installed policy. "
    "A reason may stop appearing when another condition takes priority."
)
GATE_REASON_COMPARISON_UNAVAILABLE = "Gate reasons are unavailable in this older comparison."


class ComparisonRejectionReason(StrEnum):
    DIFFERENT_REPOSITORY = "different_repository"
    DIFFERENT_PULL_REQUEST = "different_pull_request"
    MISSING_EXACT_HEAD = "missing_exact_head"
    DIFFERENT_CRITERIA = "different_criteria"
    MISSING_CRITERIA_SOURCE = "missing_criteria_source"
    DIFFERENT_CRITERIA_SOURCE = "different_criteria_source"


class ComparisonIncompatible(ValueError):
    """A validated pair failed an explicit evidence comparison requirement."""

    def __init__(self, reason: ComparisonRejectionReason, message: str) -> None:
        super().__init__(message)
        self.reason = reason


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

    @field_validator("criterion_id")
    @classmethod
    def _criterion_id_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence change criterion ID must contain non-whitespace text")
        return value

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


class JUnitImportChangeKind(StrEnum):
    """Relationship between one bounded imported artifact across reviews."""

    UNCHANGED = "unchanged"
    MAPPING_MODIFIED = "mapping_modified"
    CONTEXT_MODIFIED = "context_modified"
    MAPPING_AND_CONTEXT_MODIFIED = "mapping_and_context_modified"
    ADDED = "added"
    REMOVED = "removed"


class JUnitMappingReference(BaseModel):
    """Validated comparison projection of an explicit human mapping."""

    criterion_id: str = Field(min_length=1)
    test_case_ids: list[str] = Field(min_length=1)

    @field_validator("test_case_ids")
    @classmethod
    def _case_ids_are_canonical(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("JUnit comparison case IDs must be sorted and unique")
        return value


class JUnitImportReference(BaseModel):
    """Sanitized immutable reference used only for comparison reporting."""

    import_id: str = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    asserted_importer: str = Field(min_length=1)
    context_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_boundary: JUnitEvidenceBoundary = Field(default_factory=JUnitEvidenceBoundary)
    mappings: list[JUnitMappingReference] = Field(min_length=1)
    status: Literal["active", "withdrawn"] | None = None
    withdrawal_event: JUnitImportWithdrawalEvent | None = None
    original_mappings: list[JUnitMappingReference] | None = None
    retained_test_case_ids: list[str] | None = None
    confirmed_criterion_ids: list[str] | None = None
    mapping_correction_events: list[JUnitMappingCorrectionEvent] = Field(
        default_factory=list, max_length=20,
    )

    @model_validator(mode="after")
    def _withdrawal_matches_reference(self) -> JUnitImportReference:
        if (self.status == "withdrawn") != (self.withdrawal_event is not None):
            raise ValueError("withdrawn JUnit comparison requires its explicit audit event")
        event = self.withdrawal_event
        if event is not None and (event.import_id, event.artifact_sha256, event.head_sha) != (
            self.import_id, self.artifact_sha256, self.head_sha,
        ):
            raise ValueError("JUnit withdrawal event must match its comparison reference")
        if self.mapping_correction_events and (
            self.original_mappings is None or self.retained_test_case_ids is None
            or self.confirmed_criterion_ids is None
        ):
            raise ValueError("JUnit correction comparison requires original mappings and catalogs")
        for correction in self.mapping_correction_events:
            if (correction.import_id, correction.artifact_sha256, correction.head_sha) != (
                self.import_id, self.artifact_sha256, self.head_sha,
            ):
                raise ValueError("JUnit correction event must match its comparison reference")
        if self.original_mappings is not None:
            original = [JUnitCriterionMapping.model_validate(x.model_dump(mode="python"))
                        for x in self.original_mappings]
            effective = [JUnitCriterionMapping.model_validate(x.model_dump(mode="python"))
                         for x in self.mappings]
            junit_mapping_sha256(original)
            junit_mapping_sha256(effective)
            for catalog in (self.retained_test_case_ids, self.confirmed_criterion_ids):
                if catalog is not None and (not catalog or catalog != sorted(set(catalog))):
                    raise ValueError("JUnit comparison catalogs must be nonempty canonical IDs")
            for mapping in (*original, *effective):
                if self.retained_test_case_ids is not None and any(
                    case_id not in self.retained_test_case_ids for case_id in mapping.test_case_ids
                ):
                    raise ValueError("JUnit comparison mappings must use retained test cases")
                if (self.confirmed_criterion_ids is not None
                    and mapping.criterion_id not in self.confirmed_criterion_ids):
                    raise ValueError("JUnit comparison mappings must use confirmed criteria")
            replayed = replay_junit_mapping_events(
                original, self.mapping_correction_events,
                known_case_ids=set(self.retained_test_case_ids or []),
                known_criterion_ids=set(self.confirmed_criterion_ids or []),
            )
            if replayed != effective:
                raise ValueError("JUnit comparison effective mappings must match correction replay")
        return self

    @classmethod
    def from_import(
        cls, evidence_import: JUnitEvidenceImport,
        withdrawal_event: JUnitImportWithdrawalEvent | None = None,
        mapping_correction_events: list[JUnitMappingCorrectionEvent] | None = None,
        confirmed_criterion_ids: list[str] | None = None,
    ) -> JUnitImportReference:
        """Project only sanitized identity and explicit mappings."""

        sanitized_context = evidence_import.model_dump(mode="json", exclude={"criterion_mappings"})
        if withdrawal_event is not None:
            sanitized_context["withdrawal_event"] = withdrawal_event.model_dump(mode="json")
        corrections = mapping_correction_events or []
        if corrections:
            sanitized_context["mapping_correction_events"] = [
                event.model_dump(mode="json") for event in corrections
            ]
        context_sha256 = sha256(
            json.dumps(sanitized_context, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        return cls(
            status="withdrawn" if withdrawal_event is not None else "active",
            withdrawal_event=withdrawal_event.model_copy(deep=True) if withdrawal_event else None,
            import_id=evidence_import.import_id,
            artifact_sha256=evidence_import.artifact_sha256,
            head_sha=evidence_import.head_sha,
            asserted_importer=evidence_import.imported_by,
            context_sha256=context_sha256,
            evidence_boundary=evidence_import.evidence_boundary.model_copy(deep=True),
            original_mappings=[JUnitMappingReference(
                criterion_id=mapping.criterion_id, test_case_ids=list(mapping.test_case_ids),
            ) for mapping in evidence_import.criterion_mappings],
            retained_test_case_ids=[x.test_case_id for x in evidence_import.test_cases],
            confirmed_criterion_ids=confirmed_criterion_ids,
            mapping_correction_events=[event.model_copy(deep=True) for event in corrections],
            mappings=[
                JUnitMappingReference(
                    criterion_id=mapping.criterion_id,
                    test_case_ids=mapping.test_case_ids,
                )
                for mapping in replay_junit_mapping_events(
                    evidence_import.criterion_mappings, corrections,
                    known_case_ids={x.test_case_id for x in evidence_import.test_cases},
                    known_criterion_ids=set(confirmed_criterion_ids or []),
                )
            ],
        )


class JUnitImportChange(BaseModel):
    """One artifact-digest relationship with explicit mapping projections."""

    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: JUnitImportChangeKind
    previous: JUnitImportReference | None = None
    current: JUnitImportReference | None = None

    @model_validator(mode="after")
    def _references_match_kind_and_digest(self) -> JUnitImportChange:
        if self.kind in {
            JUnitImportChangeKind.UNCHANGED,
            JUnitImportChangeKind.MAPPING_MODIFIED,
            JUnitImportChangeKind.CONTEXT_MODIFIED,
            JUnitImportChangeKind.MAPPING_AND_CONTEXT_MODIFIED,
        } and (self.previous is None or self.current is None):
            raise ValueError("paired JUnit import changes require both references")
        if self.kind is JUnitImportChangeKind.ADDED and (
            self.previous is not None or self.current is None
        ):
            raise ValueError("added JUnit import changes require only a current reference")
        if self.kind is JUnitImportChangeKind.REMOVED and (
            self.previous is None or self.current is not None
        ):
            raise ValueError("removed JUnit import changes require only a previous reference")
        for reference in (self.previous, self.current):
            if reference is not None and reference.artifact_sha256 != self.artifact_sha256:
                raise ValueError("JUnit import change digest must match its references")
        if self.previous is not None and self.current is not None:
            mapping_changed = self.previous.mappings != self.current.mappings
            context_changed = self.previous.context_sha256 != self.current.context_sha256
            expected = {
                (False, False): JUnitImportChangeKind.UNCHANGED,
                (True, False): JUnitImportChangeKind.MAPPING_MODIFIED,
                (False, True): JUnitImportChangeKind.CONTEXT_MODIFIED,
                (True, True): JUnitImportChangeKind.MAPPING_AND_CONTEXT_MODIFIED,
            }[(mapping_changed, context_changed)]
            if self.kind is not expected:
                raise ValueError(
                    "JUnit import change kind must match sanitized context and mapping"
                )
        return self


class GateReasonComparison(BaseModel):
    """Reason codes from two validated gates, with deterministic differences."""

    previous_reason_codes: list[str]
    current_reason_codes: list[str]

    @computed_field
    @property
    def newly_reported(self) -> list[str]:
        return sorted(set(self.current_reason_codes).difference(self.previous_reason_codes))

    @computed_field
    @property
    def no_longer_reported(self) -> list[str]:
        return sorted(set(self.previous_reason_codes).difference(self.current_reason_codes))

    @computed_field
    @property
    def still_reported(self) -> list[str]:
        return sorted(set(self.previous_reason_codes).intersection(self.current_reason_codes))

    def reason_groups(self) -> tuple[tuple[str, list[str]], ...]:
        return (
            ("Newly reported", self.newly_reported),
            ("No longer reported", self.no_longer_reported),
            ("Still reported", self.still_reported),
        )


class ReviewComparison(BaseModel):
    previous_head_sha: str
    current_head_sha: str
    evidence_changes: list[EvidenceChange]
    changed_finding_statuses: list[FindingStatusChange]
    changed_human_resolutions: list[ResolutionChange]
    junit_import_changes: list[JUnitImportChange] = Field(default_factory=list)
    file_scope: FileScopeComparison | None = None
    selected_reference_comparison: SelectedReferenceComparison | None = None
    decision_context_comparison: DecisionContextComparison | None = None
    final_acceptance_comparison: FinalAcceptanceComparison | None = None
    previous_gate: GateVerdict
    current_gate: GateVerdict
    gate_reason_comparison: GateReasonComparison | None = None
    ruleset_version_changed: bool
    criteria_requiring_decision_review: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _junit_audit_matches_owning_context(self) -> ReviewComparison:
        audit_ids: dict[str, set[str]] = {"previous": set(), "current": set()}
        correction_counts = {"previous": 0, "current": 0}
        for change in self.junit_import_changes:
            for side in ("previous", "current"):
                reference = getattr(change, side)
                if reference is None:
                    continue
                correction_counts[side] += len(reference.mapping_correction_events)
                if correction_counts[side] > MAX_JUNIT_MAPPING_CORRECTIONS_PER_REVIEW:
                    raise ValueError("JUnit comparison correction history exceeds its owning limit")
                events = [*reference.mapping_correction_events]
                if reference.withdrawal_event is not None:
                    events.append(reference.withdrawal_event)
                for event in events:
                    if event.event_id in audit_ids[side]:
                        raise ValueError("JUnit comparison audit event IDs must be unique per side")
                    audit_ids[side].add(event.event_id)
                    if self.decision_context_comparison is None:
                        raise ValueError("JUnit audit requires owning decision-context identities")
                    context = self.decision_context_comparison
                    owner = getattr(context, side)
                    if (reference.mapping_correction_events
                        and reference.confirmed_criterion_ids != owner.criterion_ids):
                        raise ValueError("JUnit correction criteria catalog must match its owner")
                    if (
                        event.review_id, event.repository, event.pr_number, event.head_sha,
                        event.criteria_revision_number, event.confirmed_criteria_sha256,
                        event.criteria_source_provenance,
                    ) != (
                        owner.review_id, context.repository, context.pr_number, owner.head_sha,
                        owner.criteria_revision_number,
                        owner.criteria_source_provenance.normalized_criteria_sha256,
                        owner.criteria_source_provenance,
                    ):
                        raise ValueError("JUnit audit must match the full owning analysis identity")
        return self

    @computed_field
    @property
    def reviewer_selected_references_compared(self) -> bool:
        """Missing historical projections remain unavailable rather than empty."""
        return self.selected_reference_comparison is not None

    @computed_field
    @property
    def decision_context_compared(self) -> bool:
        return self.decision_context_comparison is not None

    @computed_field
    @property
    def final_acceptance_compared(self) -> bool:
        return self.final_acceptance_comparison is not None

    @model_validator(mode="before")
    @classmethod
    def _discard_context_availability(cls, value: object) -> object:
        if isinstance(value, dict):
            return {key: item for key, item in value.items()
                    if key not in {"decision_context_compared", "final_acceptance_compared"}}
        return value

    @model_validator(mode="after")
    def _final_acceptance_matches_owner(self) -> ReviewComparison:
        context = self.final_acceptance_comparison
        if context is None:
            return self
        if self.decision_context_comparison is None:
            raise ValueError("final-acceptance context requires owning decision-context identities")
        for side in ("previous", "current"):
            snapshot = getattr(context, side)
            owner = getattr(self.decision_context_comparison, side)
            for field in ("repository", "pr_number", "review_id", "head_sha",
                          "criteria_revision_number", "input_origin"):
                if getattr(snapshot, field) != getattr(owner, field):
                    raise ValueError("final-acceptance context must match its owning analysis")
            if (
                snapshot.criterion_ids != tuple(owner.criterion_ids)
                or snapshot.normalized_criteria_sha256
                != owner.criteria_source_provenance.normalized_criteria_sha256
            ):
                raise ValueError("final-acceptance context must match owning confirmed criteria")
            if getattr(self, f"{side}_gate") is GateVerdict.READY and not (
                snapshot.recorded_final_acceptance
            ):
                raise ValueError("Ready comparison requires recorded final acceptance")
        return self

    @model_validator(mode="after")
    def _decision_context_matches_comparison(self) -> ReviewComparison:
        context = self.decision_context_comparison
        if context is None:
            return self
        if self.file_scope is None:
            raise ValueError("decision context requires owning scope snapshots")
        for side in ("previous", "current"):
            snapshot = getattr(context, side)
            owner = getattr(self.file_scope, side)
            if (
                snapshot.head_sha != getattr(self, f"{side}_head_sha")
                or snapshot.review_id != owner.review_id
                or snapshot.head_sha != owner.head_sha
                or snapshot.criteria_revision_number != owner.criteria_revision_number
                or snapshot.criterion_ids != owner.criterion_ids
                or snapshot.criteria_source_provenance.normalized_criteria_sha256
                != owner.normalized_criteria_sha256
            ):
                raise ValueError("decision context must match its owning scope identity")
            selected = self.selected_reference_comparison
            if selected is not None and (
                (context.repository, context.pr_number) != (selected.repository, selected.pr_number)
                or snapshot.criteria_source_provenance
                != getattr(selected, f"{side}_criteria_source_provenance")
            ):
                raise ValueError("decision context must match owning repository and provenance")
        old = {item.criterion_id: item.decision for item in context.previous.resolutions}
        new = {item.criterion_id: item.decision for item in context.current.resolutions}
        expected = [
            ResolutionChange(
                criterion_id=criterion_id, previous_decision=old.get(criterion_id),
                current_decision=new.get(criterion_id),
            )
            for criterion_id in sorted(old.keys() | new.keys())
            if old.get(criterion_id) != new.get(criterion_id)
        ]
        if self.changed_human_resolutions != expected:
            raise ValueError("decision context must match the existing decision enum deltas")
        return self

    @model_validator(mode="after")
    def _scope_heads_match_comparison(self) -> ReviewComparison:
        if self.selected_reference_comparison is not None:
            if self.file_scope is None:
                raise ValueError("selected comparison context requires owning scope snapshots")
            for side in ("previous", "current"):
                owner = getattr(self.file_scope, side)
                provenance = getattr(
                    self.selected_reference_comparison, f"{side}_criteria_source_provenance"
                )
                if provenance.normalized_criteria_sha256 != owner.normalized_criteria_sha256:
                    raise ValueError("selected comparison provenance must match owning criteria")
                for reference in getattr(self.selected_reference_comparison, side):
                    if (
                        reference.review_id != owner.review_id
                        or reference.head_sha != owner.head_sha
                        or reference.criteria_revision_number != owner.criteria_revision_number
                        or reference.confirmed_criteria_sha256 != owner.normalized_criteria_sha256
                        or reference.criterion_id not in owner.criterion_ids
                    ):
                        raise ValueError("selected comparison reference must match owning scope")
                    if owner.inventory is None or reference.file_path in owner.skipped_files:
                        raise ValueError("selected comparison requires an inspected source")
                    source = next((
                        item for item in owner.inventory.files
                        if item.path == reference.file_path
                    ), None)
                    if reference.source_scope is EvidenceSourceScope.CHANGED_FILE:
                        if source is None or source.status.casefold() not in {
                            "added", "modified", "renamed", "copied", "changed"
                        }:
                            raise ValueError(
                                "selected comparison requires an inspected current path"
                            )
                    elif source is not None or any(
                        item.previous_path == reference.file_path for item in owner.inventory.files
                    ):
                        raise ValueError("selected unchanged context cannot cite changed paths")
        if self.file_scope is not None and (
            self.file_scope.previous.head_sha != self.previous_head_sha
            or self.file_scope.current.head_sha != self.current_head_sha
        ):
            raise ValueError("scope snapshots must match comparison heads")
        if self.file_scope is not None:
            for side in ("previous", "current"):
                snapshot = getattr(self.file_scope, side)
                references = {
                    reference.evidence_id: reference
                    for change in self.evidence_changes
                    if (reference := getattr(change, side)) is not None
                }
                cited_paths: set[str] = set()
                inventory_paths = (
                    {item.path for item in snapshot.inventory.files}
                    if snapshot.inventory is not None else set()
                )
                for criterion_id, evidence_ids in snapshot.finding_evidence_ids.items():
                    for evidence_id in evidence_ids:
                        reference = references.get(evidence_id)
                        if reference is None or reference.criterion_id != criterion_id:
                            raise ValueError(
                                "scope finding links require matching evidence references"
                            )
                        if (
                            reference.commit_sha == snapshot.head_sha
                            and reference.source_scope is EvidenceSourceScope.CHANGED_FILE
                            and reference.file_path in inventory_paths
                        ):
                            cited_paths.add(reference.file_path)
                if snapshot.cited_paths != sorted(cited_paths):
                    raise ValueError(
                        "scope citations must match linked exact-head changed evidence"
                    )
        return self

    @field_validator("criteria_requiring_decision_review")
    @classmethod
    def _decision_review_ids_are_canonical(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)) or any(not item.strip() for item in value):
            raise ValueError("criteria requiring decision review must be sorted unique IDs")
        return value

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


def _pair_unique(
    previous: list[EvidenceReference],
    current: list[EvidenceReference],
    consumed_previous: set[int],
    consumed_current: set[int],
    signature,
    kind: EvidenceChangeKind,
) -> list[EvidenceChange]:
    changes: list[EvidenceChange] = []
    previous_by_signature: dict[tuple, list[int]] = {}
    current_by_signature: dict[tuple, list[int]] = {}
    for index, reference in enumerate(previous):
        if index not in consumed_previous:
            previous_by_signature.setdefault(signature(reference), []).append(index)
    for index, reference in enumerate(current):
        if index not in consumed_current:
            current_by_signature.setdefault(signature(reference), []).append(index)
    for candidate_signature in sorted(
        set(previous_by_signature) & set(current_by_signature), key=repr
    ):
        previous_indexes = previous_by_signature[candidate_signature]
        current_indexes = current_by_signature[candidate_signature]
        if len(previous_indexes) != 1 or len(current_indexes) != 1:
            continue
        previous_index = previous_indexes[0]
        current_index = current_indexes[0]
        consumed_previous.add(previous_index)
        consumed_current.add(current_index)
        changes.append(
            _change(kind, previous=previous[previous_index], current=current[current_index])
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
            _pair_unique(
                previous,
                current,
                consumed_previous,
                consumed_current,
                _exact_signature,
                EvidenceChangeKind.UNCHANGED,
            )
        )
        changes.extend(
            _pair_unique(
                previous,
                current,
                consumed_previous,
                consumed_current,
                _relocated_signature,
                EvidenceChangeKind.RELOCATED,
            )
        )
        changes.extend(
            _pair_unique(
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


def _compare_junit_imports(
    previous_items: list[JUnitEvidenceImport],
    current_items: list[JUnitEvidenceImport],
    previous_events: list[JUnitImportEvent] | None = None,
    current_events: list[JUnitImportEvent] | None = None,
    previous_criterion_ids: list[str] | None = None,
    current_criterion_ids: list[str] | None = None,
) -> list[JUnitImportChange]:
    previous_by_digest = {item.artifact_sha256: item for item in previous_items}
    current_by_digest = {item.artifact_sha256: item for item in current_items}
    previous_audit = {event.import_id: event for event in previous_events or []
                      if event.action == "withdrawn"}
    current_audit = {event.import_id: event for event in current_events or []
                     if event.action == "withdrawn"}
    changes: list[JUnitImportChange] = []
    for digest in sorted(set(previous_by_digest) | set(current_by_digest)):
        previous_item = previous_by_digest.get(digest)
        current_item = current_by_digest.get(digest)
        previous_reference = (
            JUnitImportReference.from_import(
                previous_item, previous_audit.get(previous_item.import_id),
                [event for event in previous_events or [] if event.action == "mapping_corrected"
                 and event.import_id == previous_item.import_id], previous_criterion_ids,
            )
            if previous_item is not None else None
        )
        current_reference = (
            JUnitImportReference.from_import(
                current_item, current_audit.get(current_item.import_id),
                [event for event in current_events or [] if event.action == "mapping_corrected"
                 and event.import_id == current_item.import_id], current_criterion_ids,
            )
            if current_item is not None else None
        )
        if previous_reference is None:
            kind = JUnitImportChangeKind.ADDED
        elif current_reference is None:
            kind = JUnitImportChangeKind.REMOVED
        else:
            mapping_changed = previous_reference.mappings != current_reference.mappings
            context_changed = previous_reference.context_sha256 != current_reference.context_sha256
            kind = {
                (False, False): JUnitImportChangeKind.UNCHANGED,
                (True, False): JUnitImportChangeKind.MAPPING_MODIFIED,
                (False, True): JUnitImportChangeKind.CONTEXT_MODIFIED,
                (True, True): JUnitImportChangeKind.MAPPING_AND_CONTEXT_MODIFIED,
            }[(mapping_changed, context_changed)]
        changes.append(
            JUnitImportChange(
                artifact_sha256=digest,
                kind=kind,
                previous=previous_reference,
                current=current_reference,
            )
        )
    return changes


def _changed_junit_criteria(changes: list[JUnitImportChange]) -> set[str]:
    return {
        mapping.criterion_id
        for change in changes
        if change.kind is not JUnitImportChangeKind.UNCHANGED
        for reference in (change.previous, change.current)
        if reference is not None
        for mapping in (
            *reference.mappings, *(reference.original_mappings or []),
            *(mapping for event in reference.mapping_correction_events
              for mapping in event.criterion_mappings),
        )
    }


def _criteria_source_identity(bundle: ReviewBundle) -> tuple[str, str | None, str, str]:
    provenance = bundle.review.criteria_source_provenance
    if provenance is None:
        raise ComparisonIncompatible(
            ComparisonRejectionReason.MISSING_CRITERIA_SOURCE,
            "comparison requires confirmed criteria-source provenance",
        )
    return (
        provenance.source_uri,
        provenance.source_revision,
        provenance.source_text_sha256,
        provenance.normalized_criteria_sha256,
    )


def _validate_review_head_identity(bundle: ReviewBundle) -> None:
    review = bundle.review
    if (
        review.input_origin
        not in {
            ReviewInputOrigin.LOCAL_FIXTURE,
            ReviewInputOrigin.CONSTRUCTED_DEMO,
        }
        and _EXACT_GIT_HEAD.fullmatch(review.head_sha) is None
    ):
        raise ComparisonIncompatible(
            ComparisonRejectionReason.MISSING_EXACT_HEAD,
            "comparison live or unknown-origin reviews require exact head SHAs",
        )
    if any(item.commit_sha != review.head_sha for item in bundle.evidence):
        raise ValueError("comparison evidence candidates must match the reviewed head")


def validate_comparison_relationship(
    previous: ReviewBundle, current: ReviewBundle
) -> tuple[ReviewBundle, ReviewBundle]:
    """Validate that two review snapshots describe one comparable relationship."""

    previous = validated_review_bundle(previous)
    current = validated_review_bundle(current)
    if previous.review.repository != current.review.repository:
        raise ComparisonIncompatible(
            ComparisonRejectionReason.DIFFERENT_REPOSITORY,
            "comparison requires the same repository",
        )
    if previous.review.pr_number != current.review.pr_number:
        raise ComparisonIncompatible(
            ComparisonRejectionReason.DIFFERENT_PULL_REQUEST,
            "comparison requires the same pull request",
        )
    _validate_review_head_identity(previous)
    _validate_review_head_identity(current)
    if previous.criteria != current.criteria:
        raise ComparisonIncompatible(
            ComparisonRejectionReason.DIFFERENT_CRITERIA,
            "comparison requires identical ordered criterion definitions",
        )
    if _criteria_source_identity(previous) != _criteria_source_identity(current):
        raise ComparisonIncompatible(
            ComparisonRejectionReason.DIFFERENT_CRITERIA_SOURCE,
            "comparison requires compatible criteria-source provenance",
        )
    return previous, current


def compare_reviews(previous: ReviewBundle, current: ReviewBundle) -> ReviewComparison:
    """Compare stable review facts without treating evidence IDs as semantic identity."""

    previous, current = validate_comparison_relationship(previous, current)
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
    evidence_changes = _compare_evidence(previous.evidence, current.evidence)
    junit_import_changes = _compare_junit_imports(
        previous.junit_evidence_imports, current.junit_evidence_imports,
        previous.junit_import_events, current.junit_import_events,
        sorted(x.criterion_id for x in previous.criteria),
        sorted(x.criterion_id for x in current.criteria),
    )
    changed_criterion_ids = {
        change.criterion_id
        for change in evidence_changes
        if change.kind is not EvidenceChangeKind.UNCHANGED
    }
    changed_criterion_ids.update(change.criterion_id for change in changed_findings)
    changed_criterion_ids.update(_changed_junit_criteria(junit_import_changes))
    if (
        previous.review.head_sha != current.review.head_sha
        or previous.review.ruleset_version != current.review.ruleset_version
    ):
        changed_criterion_ids.update(previous_resolutions)
    return ReviewComparison(
        previous_head_sha=previous.review.head_sha,
        current_head_sha=current.review.head_sha,
        selected_reference_comparison=SelectedReferenceComparison.from_bundles(previous, current),
        decision_context_comparison=DecisionContextComparison.from_bundles(previous, current),
        final_acceptance_comparison=FinalAcceptanceComparison.from_bundles(previous, current),
        file_scope=FileScopeComparison(
            previous=FileScopeSnapshot.from_bundle(previous),
            current=FileScopeSnapshot.from_bundle(current),
        ),
        evidence_changes=evidence_changes,
        changed_finding_statuses=changed_findings,
        changed_human_resolutions=changed_resolutions,
        junit_import_changes=junit_import_changes,
        previous_gate=previous.gate.verdict,
        current_gate=current.gate.verdict,
        gate_reason_comparison=GateReasonComparison(
            previous_reason_codes=list(previous.gate.reason_codes),
            current_reason_codes=list(current.gate.reason_codes),
        ),
        ruleset_version_changed=(previous.review.ruleset_version != current.review.ruleset_version),
        criteria_requiring_decision_review=sorted(
            set(previous_resolutions) & changed_criterion_ids
        ),
    )
