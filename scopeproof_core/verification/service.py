"""Derive provisional findings without converting candidates into proof."""

from collections import defaultdict

from scopeproof_core.schemas.models import (
    ConfidenceBand,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    Finding,
    FindingStatus,
    IngestionState,
)


def _confidence(score: float) -> ConfidenceBand:
    if score >= 0.8:
        return ConfidenceBand.HIGH
    if score >= 0.5:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


def build_findings(
    criteria: list[Criterion],
    evidence: list[EvidenceItem],
    ingestion_state: IngestionState,
) -> list[Finding]:
    """Summarize candidates and missing evidence using deterministic thresholds."""
    evidence_by_criterion: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        evidence_by_criterion[item.criterion_id].append(item)

    findings: list[Finding] = []
    for criterion in criteria:
        candidates = evidence_by_criterion[criterion.criterion_id]
        if not candidates:
            if ingestion_state is IngestionState.COMPLETE:
                status = FindingStatus.MISSING
                reason = "No candidate evidence was found in the complete changed-file analysis."
                action = "Add implementation evidence or identify evidence for reviewer inspection."
            else:
                status = FindingStatus.NEEDS_REVIEW
                reason = "No candidate was found, but the analysis was partial or failed."
                action = "Review skipped content before deciding whether evidence is missing."
            findings.append(
                Finding(
                    criterion_id=criterion.criterion_id,
                    status=status,
                    evidence_level=EvidenceLevel.E0,
                    confidence_band=ConfidenceBand.LOW,
                    reason=reason,
                    missing_evidence=[
                        f"Required evidence level {criterion.required_evidence_level.value}"
                    ],
                    recommended_action=action,
                )
            )
            continue

        score = max(item.relevance_score for item in candidates)
        best_level = max((item.evidence_level for item in candidates), key=lambda level: level.rank)
        level_sufficient = best_level.rank >= criterion.required_evidence_level.rank
        if score >= 0.75 and level_sufficient:
            status = FindingStatus.EVIDENCE_FOUND
            reason = "Strong candidate evidence was found; a reviewer must still judge sufficiency."
            missing: list[str] = []
            action = (
                "Open the cited lines and accept, reject, or supplement the candidate evidence."
            )
        else:
            status = FindingStatus.PARTIAL
            reason = (
                "Candidate evidence covers only part of the wording or is below the required level."
            )
            missing = []
            if not level_sufficient:
                required_level = criterion.required_evidence_level.value
                missing.append(f"Evidence at required level {required_level}")
            else:
                missing.append("Stronger evidence covering the remaining criterion terms")
            action = "Review the candidate and provide stronger or additional evidence."
        findings.append(
            Finding(
                criterion_id=criterion.criterion_id,
                status=status,
                evidence_level=best_level,
                confidence_band=_confidence(score),
                reason=reason,
                evidence_ids=[item.evidence_id for item in candidates],
                missing_evidence=missing,
                recommended_action=action,
            )
        )
    return findings
