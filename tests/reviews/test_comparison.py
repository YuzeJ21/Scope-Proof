from scopeproof_core.reviews.comparison import compare_reviews
from scopeproof_core.schemas.models import (
    CheckState,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    Finding,
    FindingStatus,
    GateDecision,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    Review,
    ReviewBundle,
)


def bundle(*, head_sha: str, status: FindingStatus, with_evidence: bool) -> ReviewBundle:
    review = Review(
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha=head_sha,
        check_state=CheckState.PASSING,
        criteria_confirmed=True,
        final_acceptance=True,
    )
    evidence = []
    if with_evidence:
        evidence.append(
            EvidenceItem(
                evidence_id="EV-new",
                criterion_id="AC-01",
                evidence_type=EvidenceType.IMPLEMENTATION,
                evidence_level=EvidenceLevel.E1,
                file_path="src/export.py",
                line_start=2,
                line_end=2,
                commit_sha=head_sha,
                permalink=f"https://github.com/acme/widget/blob/{head_sha}/src/export.py#L2-L2",
                excerpt="export_csv()",
                matching_rule="exact_identifier",
                relevance_reason="Matches export criterion",
                relevance_score=1.0,
            )
        )
    return ReviewBundle(
        review=review,
        source_text="Export CSV",
        criteria=[Criterion(criterion_id="AC-01", text="Export CSV")],
        evidence=evidence,
        findings=[
            Finding(
                criterion_id="AC-01",
                status=status,
                reason="Result",
                recommended_action="Review",
            )
        ],
        resolutions=[
            HumanResolution(
                criterion_id="AC-01",
                decision=(
                    HumanDecision.ACCEPTED if with_evidence else HumanDecision.CHANGE_REQUIRED
                ),
            )
        ],
        gate=GateDecision(
            verdict=GateVerdict.READY if with_evidence else GateVerdict.BLOCKED
        ),
    )


def test_comparison_reports_evidence_status_resolution_and_gate_changes() -> None:
    comparison = compare_reviews(
        bundle(head_sha="oldsha", status=FindingStatus.MISSING, with_evidence=False),
        bundle(head_sha="newsha", status=FindingStatus.EVIDENCE_FOUND, with_evidence=True),
    )

    assert comparison.previous_head_sha == "oldsha"
    assert comparison.current_head_sha == "newsha"
    assert comparison.added_evidence_ids == ["EV-new"]
    assert comparison.removed_evidence_ids == []
    assert comparison.changed_finding_statuses[0].criterion_id == "AC-01"
    assert comparison.changed_human_resolutions[0].current_decision is HumanDecision.ACCEPTED
    assert comparison.previous_gate is GateVerdict.BLOCKED
    assert comparison.current_gate is GateVerdict.READY
