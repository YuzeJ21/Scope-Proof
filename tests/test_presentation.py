from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.presentation import (
    EvidenceStatus,
    criterion_coverage_rows,
    review_status_label,
)
from scopeproof_core.schemas.models import (
    CheckState,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    Finding,
    FindingStatus,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    Review,
    ReviewBundle,
)


def _bundle(
    *,
    finding_status: FindingStatus = FindingStatus.EVIDENCE_FOUND,
    resolution: HumanResolution | None = None,
    evidence: list[EvidenceItem] | None = None,
) -> ReviewBundle:
    review = Review(
        repository="acme/widget",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        criteria_confirmed=True,
    )
    criterion = Criterion(criterion_id="AC-01", text="Export filtered rows")
    candidates = evidence or [
        EvidenceItem(
            evidence_id="EV-AC-01-01",
            criterion_id="AC-01",
            evidence_type=EvidenceType.IMPLEMENTATION,
            evidence_level=EvidenceLevel.E1,
            file_path="src/export.py",
            line_start=4,
            line_end=4,
            commit_sha="head",
            permalink="https://github.com/acme/widget/blob/head/src/export.py#L4-L4",
            excerpt="return filtered_rows",
            matching_rule="keyword_overlap",
            relevance_reason="Matched terms: filtered, rows",
            relevance_score=0.8,
        )
    ]
    finding = Finding(
        criterion_id="AC-01",
        status=finding_status,
        evidence_level=EvidenceLevel.E1,
        reason="Candidate requires reviewer judgment.",
        evidence_ids=[item.evidence_id for item in candidates],
        recommended_action="Review the cited line.",
    )
    resolutions = [resolution] if resolution else []
    return ReviewBundle(
        review=review,
        source_text=criterion.text,
        criteria=[criterion],
        evidence=candidates,
        findings=[finding],
        resolutions=resolutions,
        gate=evaluate_gate(review, [criterion], [finding], resolutions),
    )


def test_presentation_separates_candidate_status_from_human_decision() -> None:
    row = criterion_coverage_rows(_bundle())[0]

    assert row.evidence_status is EvidenceStatus.STRONG_CANDIDATE
    assert row.reviewer_decision == "Unresolved"
    assert row.evidence_types == ["Implementation"]
    assert row.candidate_count == 1


def test_manual_verification_changes_presentation_without_rewriting_static_finding() -> None:
    resolution = HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment="Verified in the public preview.",
        claimed_evidence_level=EvidenceLevel.E3,
    )
    bundle = _bundle(resolution=resolution)

    row = criterion_coverage_rows(bundle)[0]

    assert bundle.findings[0].status is FindingStatus.EVIDENCE_FOUND
    assert row.evidence_status is EvidenceStatus.REVIEWER_VERIFIED
    assert row.reviewer_decision == "Manually verified"


def test_rejected_finding_is_a_separate_presentation_status() -> None:
    resolution = HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.REJECTED_FINDING,
        comment="The matching identifier is unrelated.",
    )

    row = criterion_coverage_rows(_bundle(resolution=resolution))[0]

    assert row.evidence_status is EvidenceStatus.REJECTED
    assert row.reviewer_decision == "Rejected finding"


def test_candidate_status_labels_are_conservative() -> None:
    assert (
        criterion_coverage_rows(_bundle(finding_status=FindingStatus.PARTIAL))[0].evidence_status
        is EvidenceStatus.WEAK_CANDIDATE
    )
    assert (
        criterion_coverage_rows(_bundle(finding_status=FindingStatus.MISSING))[0].evidence_status
        is EvidenceStatus.NO_CANDIDATE
    )
    assert (
        criterion_coverage_rows(_bundle(finding_status=FindingStatus.NEEDS_REVIEW))[0].evidence_status
        is EvidenceStatus.ANALYSIS_INCOMPLETE
    )


def test_review_status_does_not_claim_release_readiness() -> None:
    assert review_status_label(GateVerdict.READY) == "Review complete"
    assert review_status_label(GateVerdict.CONDITIONAL) == "Accepted with exceptions"
    assert review_status_label(GateVerdict.BLOCKED) == "Action required"
    assert review_status_label(GateVerdict.NEEDS_REVIEW) == "Review incomplete"
