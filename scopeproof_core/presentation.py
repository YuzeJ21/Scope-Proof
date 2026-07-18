"""Honest, UI-independent labels for deterministic acceptance coverage."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from scopeproof_core.gates.validation import validated_review_bundle
from scopeproof_core.schemas.models import (
    Finding,
    FindingStatus,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    ReviewBundle,
)


class EvidenceStatus(StrEnum):
    """Candidate or reviewer state without implying criterion satisfaction."""

    STRONG_CANDIDATE = "strong_candidate"
    WEAK_CANDIDATE = "weak_candidate"
    NO_CANDIDATE = "no_candidate"
    ANALYSIS_INCOMPLETE = "analysis_incomplete"
    REVIEWER_VERIFIED = "reviewer_verified"
    REJECTED = "rejected"


class CriterionCoverageRow(BaseModel):
    """Validated human-facing view of one criterion's current coverage."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1)
    criterion_text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    priority: str = Field(min_length=1)
    evidence_status: EvidenceStatus
    evidence_types: list[str]
    reviewer_decision: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)
    concern: str = Field(min_length=1)


_FINDING_STATUS = {
    FindingStatus.EVIDENCE_FOUND: EvidenceStatus.STRONG_CANDIDATE,
    FindingStatus.PARTIAL: EvidenceStatus.WEAK_CANDIDATE,
    FindingStatus.MISSING: EvidenceStatus.NO_CANDIDATE,
    FindingStatus.NEEDS_REVIEW: EvidenceStatus.ANALYSIS_INCOMPLETE,
    FindingStatus.ACCEPTED: EvidenceStatus.REVIEWER_VERIFIED,
    FindingStatus.ACCEPTED_EXCEPTION: EvidenceStatus.REVIEWER_VERIFIED,
}

_REVIEW_STATUS = {
    GateVerdict.READY: "Review complete",
    GateVerdict.CONDITIONAL: "Accepted with exceptions",
    GateVerdict.BLOCKED: "Action required",
    GateVerdict.NEEDS_REVIEW: "Review incomplete",
}


def _label(value: str) -> str:
    return value.replace("_", " ").capitalize()


def evidence_status_label(
    finding: Finding, resolution: HumanResolution | None = None
) -> EvidenceStatus:
    """Return the current presentation status without rewriting static evidence."""

    if resolution is not None:
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED:
            return EvidenceStatus.REVIEWER_VERIFIED
        if resolution.decision is HumanDecision.REJECTED_FINDING:
            return EvidenceStatus.REJECTED
    return _FINDING_STATUS[finding.status]


def review_status_label(verdict: GateVerdict) -> str:
    """Translate an internal deterministic gate into reviewer-owned language."""

    return _REVIEW_STATUS[verdict]


def evidence_status_text(status: EvidenceStatus) -> str:
    """Return sentence-case evidence language for human-facing surfaces."""

    return status.value.replace("_", " ").capitalize()


def criterion_coverage_rows(bundle: ReviewBundle) -> list[CriterionCoverageRow]:
    """Build stable presentation rows from a revalidated review bundle."""

    bundle = validated_review_bundle(bundle)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    resolution_by_id = {
        resolution.criterion_id: resolution for resolution in bundle.resolutions
    }
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    rows: list[CriterionCoverageRow] = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        resolution = resolution_by_id.get(criterion.criterion_id)
        evidence_types = sorted(
            {
                _label(evidence_by_id[evidence_id].evidence_type.value)
                for evidence_id in finding.evidence_ids
            }
        )
        rows.append(
            CriterionCoverageRow(
                criterion_id=criterion.criterion_id,
                criterion_text=criterion.text,
                source=_label(criterion.criterion_source.value),
                priority=_label(criterion.priority.value),
                evidence_status=evidence_status_label(finding, resolution),
                evidence_types=evidence_types,
                reviewer_decision=(
                    _label(resolution.decision.value) if resolution else "Unresolved"
                ),
                candidate_count=len(finding.evidence_ids),
                concern=finding.reason,
            )
        )
    return rows
