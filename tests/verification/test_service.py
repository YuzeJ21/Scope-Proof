from scopeproof_core.schemas.models import (
    ConfidenceBand,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    FindingStatus,
    IngestionState,
)
from scopeproof_core.verification.service import build_findings


def evidence(score: float, level: EvidenceLevel = EvidenceLevel.E1) -> EvidenceItem:
    return EvidenceItem(
        evidence_id="EV-AC-01-1",
        criterion_id="AC-01",
        evidence_type=EvidenceType.IMPLEMENTATION,
        evidence_level=level,
        file_path="src/export.py",
        line_start=42,
        line_end=42,
        commit_sha="head123",
        permalink="https://github.com/acme/widget/blob/head123/src/export.py#L42-L42",
        excerpt="def export_csv(rows):",
        matching_rule="keyword_overlap",
        relevance_reason="Matched export and csv",
        relevance_score=score,
    )


def test_partial_ingestion_forces_needs_review_when_evidence_is_absent() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    finding = build_findings([criterion], [], IngestionState.PARTIAL)[0]
    assert finding.status is FindingStatus.NEEDS_REVIEW
    assert "analysis was partial" in finding.reason.lower()


def test_complete_ingestion_without_evidence_is_missing() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    finding = build_findings([criterion], [], IngestionState.COMPLETE)[0]
    assert finding.status is FindingStatus.MISSING
    assert finding.evidence_level is EvidenceLevel.E0


def test_medium_score_is_partial_and_explains_limit() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export respects all active filters")
    finding = build_findings([criterion], [evidence(0.62)], IngestionState.COMPLETE)[0]
    assert finding.status is FindingStatus.PARTIAL
    assert finding.confidence_band is ConfidenceBand.MEDIUM
    assert "stronger" in finding.recommended_action.lower()


def test_high_score_at_required_level_is_evidence_found_not_verified() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    finding = build_findings([criterion], [evidence(0.9)], IngestionState.COMPLETE)[0]
    assert finding.status is FindingStatus.EVIDENCE_FOUND
    assert "candidate" in finding.reason.lower()


def test_e1_below_required_e2_is_partial() -> None:
    criterion = Criterion(
        criterion_id="AC-01",
        text="Export CSV has an automated test",
        required_evidence_level=EvidenceLevel.E2,
    )
    finding = build_findings([criterion], [evidence(0.9)], IngestionState.COMPLETE)[0]
    assert finding.status is FindingStatus.PARTIAL
    assert "E2" in finding.missing_evidence[0]
