"""Deterministic comparisons between two validated ScopeProof review bundles."""

from __future__ import annotations

from pydantic import BaseModel

from scopeproof_core.schemas.models import FindingStatus, GateVerdict, HumanDecision, ReviewBundle


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
    added_evidence_ids: list[str]
    removed_evidence_ids: list[str]
    changed_finding_statuses: list[FindingStatusChange]
    changed_human_resolutions: list[ResolutionChange]
    previous_gate: GateVerdict
    current_gate: GateVerdict
    ruleset_version_changed: bool


def _finding_statuses(bundle: ReviewBundle) -> dict[str, FindingStatus]:
    return {finding.criterion_id: finding.status for finding in bundle.findings}


def _resolution_decisions(bundle: ReviewBundle) -> dict[str, HumanDecision]:
    return {resolution.criterion_id: resolution.decision for resolution in bundle.resolutions}


def compare_reviews(previous: ReviewBundle, current: ReviewBundle) -> ReviewComparison:
    """Compare stable review facts without treating timestamps as semantic changes."""

    previous_evidence = {item.evidence_id for item in previous.evidence}
    current_evidence = {item.evidence_id for item in current.evidence}
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
        added_evidence_ids=sorted(current_evidence - previous_evidence),
        removed_evidence_ids=sorted(previous_evidence - current_evidence),
        changed_finding_statuses=changed_findings,
        changed_human_resolutions=changed_resolutions,
        previous_gate=previous.gate.verdict,
        current_gate=current.gate.verdict,
        ruleset_version_changed=(
            previous.review.ruleset_version != current.review.ruleset_version
        ),
    )
