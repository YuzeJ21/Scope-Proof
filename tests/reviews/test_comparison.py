import pytest
from pydantic import ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.comparison import (
    EvidenceChange,
    EvidenceChangeKind,
    EvidenceReference,
    compare_reviews,
)
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    Finding,
    FindingStatus,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    IngestionState,
    Review,
    ReviewBundle,
)
from scopeproof_core.verification.service import build_findings


def passing_ci_observation() -> CIObservation:
    return CIObservation(
        state=CheckState.PASSING,
        reason="Fixture",
        total_check_runs=1,
        successful_check_runs=1,
    )


def evidence(
    evidence_id: str,
    *,
    sha: str,
    path: str = "src/export.py",
    line: int = 2,
    excerpt: str = "export_csv()",
    criterion_id: str = "AC-01",
    evidence_type: EvidenceType = EvidenceType.IMPLEMENTATION,
    source_scope: EvidenceSourceScope = EvidenceSourceScope.CHANGED_FILE,
    matching_rule: str = "exact_identifier",
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        criterion_id=criterion_id,
        evidence_type=evidence_type,
        evidence_level=(
            EvidenceLevel.E2 if evidence_type is EvidenceType.TEST else EvidenceLevel.E1
        ),
        source_scope=source_scope,
        file_path=path,
        line_start=line,
        line_end=line,
        commit_sha=sha,
        permalink=f"https://github.com/acme/widget/blob/{sha}/{path}#L{line}-L{line}",
        excerpt=excerpt,
        matching_rule=matching_rule,
        relevance_reason="Matches export criterion",
        relevance_score=1.0,
    )


def bundle_with(*items: EvidenceItem, head_sha: str) -> ReviewBundle:
    criterion_ids = sorted({item.criterion_id for item in items} or {"AC-01"})
    criteria = [
        Criterion(criterion_id=criterion_id, text=f"Requirement {criterion_id}")
        for criterion_id in criterion_ids
    ]
    review = Review(
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha=head_sha,
        check_state=CheckState.PASSING,
        ci_observation=passing_ci_observation(),
        criteria_confirmed=True,
    )
    item_list = list(items)
    findings = build_findings(criteria, item_list, IngestionState.COMPLETE)
    gate = evaluate_gate(review, criteria, findings, [])
    return ReviewBundle(
        review=review,
        source_text="\n".join(criterion.text for criterion in criteria),
        criteria=criteria,
        evidence=item_list,
        findings=findings,
        gate=gate,
    )


def bundle(*, head_sha: str, status: FindingStatus, with_evidence: bool) -> ReviewBundle:
    review = Review(
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha=head_sha,
        check_state=CheckState.PASSING,
        ci_observation=passing_ci_observation(),
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
    resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=(
                HumanDecision.ACCEPTED if with_evidence else HumanDecision.CHANGE_REQUIRED
            ),
        )
    ]
    findings = [
        Finding(
            criterion_id="AC-01",
            status=status,
            reason="Result",
            recommended_action="Review",
            evidence_ids=[item.evidence_id for item in evidence],
        )
    ]
    gate = evaluate_gate(
        review,
        [Criterion(criterion_id="AC-01", text="Export CSV")],
        findings,
        resolutions,
    )
    return ReviewBundle(
        review=review,
        source_text="Export CSV",
        criteria=[Criterion(criterion_id="AC-01", text="Export CSV")],
        evidence=evidence,
        findings=findings,
        resolutions=resolutions,
        gate=gate,
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


def test_exact_candidate_reference_is_unchanged() -> None:
    item = evidence("EV-AC-01-01", sha="same-head")

    comparison = compare_reviews(
        bundle_with(item, head_sha="same-head"),
        bundle_with(item.model_copy(deep=True), head_sha="same-head"),
    )

    assert [change.kind for change in comparison.evidence_changes] == [
        EvidenceChangeKind.UNCHANGED
    ]


def test_sha_only_change_is_relocated() -> None:
    comparison = compare_reviews(
        bundle_with(evidence("EV-AC-01-01", sha="old"), head_sha="old"),
        bundle_with(evidence("EV-AC-01-01", sha="new"), head_sha="new"),
    )

    change = comparison.evidence_changes[0]
    assert change.kind is EvidenceChangeKind.RELOCATED
    assert change.previous is not None
    assert change.current is not None
    assert change.previous.commit_sha == "old"
    assert change.current.commit_sha == "new"


def test_line_only_change_is_relocated() -> None:
    comparison = compare_reviews(
        bundle_with(evidence("EV-old", sha="head", line=2), head_sha="head"),
        bundle_with(evidence("EV-new", sha="head", line=8), head_sha="head"),
    )

    assert comparison.evidence_changes[0].kind is EvidenceChangeKind.RELOCATED


def test_path_only_change_is_relocated() -> None:
    comparison = compare_reviews(
        bundle_with(
            evidence("EV-old", sha="head", path="src/export.py"), head_sha="head"
        ),
        bundle_with(
            evidence("EV-new", sha="head", path="src/csv/export.py"), head_sha="head"
        ),
    )

    assert comparison.evidence_changes[0].kind is EvidenceChangeKind.RELOCATED


def test_same_positional_id_with_changed_excerpt_is_modified() -> None:
    comparison = compare_reviews(
        bundle_with(
            evidence("EV-AC-01-01", sha="old", excerpt="return csv"), head_sha="old"
        ),
        bundle_with(
            evidence("EV-AC-01-01", sha="new", excerpt="return safe_csv"), head_sha="new"
        ),
    )

    change = comparison.evidence_changes[0]
    assert change.kind is EvidenceChangeKind.MODIFIED
    assert change.previous is not None
    assert change.current is not None
    assert change.previous.excerpt == "return csv"
    assert change.current.excerpt == "return safe_csv"


def test_unmatched_candidates_are_added_and_removed_with_compatibility_ids() -> None:
    comparison = compare_reviews(
        bundle_with(
            evidence("EV-removed", sha="old", path="src/removed.py"), head_sha="old"
        ),
        bundle_with(
            evidence("EV-added", sha="new", path="src/added.py", excerpt="new_candidate()"),
            head_sha="new",
        ),
    )

    assert [change.kind for change in comparison.evidence_changes] == [
        EvidenceChangeKind.ADDED,
        EvidenceChangeKind.REMOVED,
    ]
    assert comparison.added_evidence_ids == ["EV-added"]
    assert comparison.removed_evidence_ids == ["EV-removed"]
    assert comparison.evidence_change_counts.added == 1
    assert comparison.evidence_change_counts.removed == 1


def test_ambiguous_relocation_falls_back_to_removed_and_added() -> None:
    previous = bundle_with(
        evidence("EV-old-1", sha="old", path="src/a.py"),
        evidence("EV-old-2", sha="old", path="src/b.py"),
        head_sha="old",
    )
    current = bundle_with(
        evidence("EV-new-1", sha="new", path="src/c.py", line=4),
        evidence("EV-new-2", sha="new", path="src/d.py", line=4),
        head_sha="new",
    )

    kinds = [change.kind for change in compare_reviews(previous, current).evidence_changes]

    assert kinds.count(EvidenceChangeKind.REMOVED) == 2
    assert kinds.count(EvidenceChangeKind.ADDED) == 2
    assert EvidenceChangeKind.RELOCATED not in kinds


def test_ambiguous_modification_falls_back_to_removed_and_added() -> None:
    previous = bundle_with(
        evidence("EV-old-1", sha="old", excerpt="first old"),
        evidence("EV-old-2", sha="old", excerpt="second old"),
        head_sha="old",
    )
    current = bundle_with(
        evidence("EV-new-1", sha="new", excerpt="first new"),
        evidence("EV-new-2", sha="new", excerpt="second new"),
        head_sha="new",
    )

    kinds = [change.kind for change in compare_reviews(previous, current).evidence_changes]

    assert kinds.count(EvidenceChangeKind.REMOVED) == 2
    assert kinds.count(EvidenceChangeKind.ADDED) == 2
    assert EvidenceChangeKind.MODIFIED not in kinds


def test_comparison_output_is_stable_when_evidence_input_order_changes() -> None:
    old_items = [
        evidence("EV-old-1", sha="old", path="src/a.py"),
        evidence("EV-old-2", sha="old", path="src/b.py", excerpt="removed()"),
    ]
    new_items = [
        evidence("EV-new-1", sha="new", path="src/a.py", excerpt="changed()"),
        evidence("EV-new-2", sha="new", path="src/c.py", excerpt="added()"),
    ]

    ordered = compare_reviews(
        bundle_with(*old_items, head_sha="old"),
        bundle_with(*new_items, head_sha="new"),
    )
    reversed_input = compare_reviews(
        bundle_with(*reversed(old_items), head_sha="old"),
        bundle_with(*reversed(new_items), head_sha="new"),
    )

    assert ordered.model_dump(mode="json") == reversed_input.model_dump(mode="json")


@pytest.mark.parametrize(
    ("kind", "previous_present", "current_present"),
    [
        (EvidenceChangeKind.UNCHANGED, False, True),
        (EvidenceChangeKind.RELOCATED, True, False),
        (EvidenceChangeKind.MODIFIED, False, False),
        (EvidenceChangeKind.ADDED, True, True),
        (EvidenceChangeKind.REMOVED, True, True),
    ],
)
def test_change_model_rejects_references_that_do_not_match_kind(
    kind: EvidenceChangeKind, previous_present: bool, current_present: bool
) -> None:
    reference = EvidenceReference.from_item(evidence("EV-1", sha="head"))

    with pytest.raises(ValidationError):
        EvidenceChange(
            criterion_id="AC-01",
            kind=kind,
            previous=reference if previous_present else None,
            current=reference if current_present else None,
            reason="Observable change",
        )


def test_change_model_rejects_blank_criterion_identity() -> None:
    reference = EvidenceReference.from_item(
        evidence("EV-1", sha="head")
    ).model_copy(update={"criterion_id": " "})

    with pytest.raises(ValidationError, match="criterion ID"):
        EvidenceChange(
            criterion_id=" ",
            kind=EvidenceChangeKind.ADDED,
            current=reference,
            reason="Candidate appears only in the current review.",
        )
