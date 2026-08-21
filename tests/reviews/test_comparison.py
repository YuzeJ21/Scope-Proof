from datetime import timedelta

import pytest
from pydantic import ValidationError

from scopeproof_core.criteria.confirmation import (
    build_criteria_source_provenance,
    normalized_criteria_sha256,
)
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
    JUnitEvidenceBoundary,
    JUnitEvidenceImport,
    RepositoryVisibility,
    Review,
    ReviewBundle,
    ReviewInputOrigin,
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
    source_text = "\n".join(criterion.text for criterion in criteria)
    review = Review(
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha=head_sha,
        input_origin=ReviewInputOrigin.CONSTRUCTED_DEMO,
        check_state=CheckState.PASSING,
        ci_observation=passing_ci_observation(),
        criteria_confirmed=True,
    )
    review.criteria_source_provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_text=source_text,
        criteria=criteria,
        confirmed_by="Fixture owner",
        confirmed_at=review.created_at,
    )
    item_list = list(items)
    findings = build_findings(criteria, item_list, IngestionState.COMPLETE)
    gate = evaluate_gate(review, criteria, findings, [])
    return ReviewBundle(
        review=review,
        source_text=source_text,
        criteria=criteria,
        evidence=item_list,
        findings=findings,
        gate=gate,
    )


def with_junit_import(
    bundle: ReviewBundle,
    *,
    artifact_digest: str,
    mapped_case_ids: list[str],
) -> ReviewBundle:
    bundle = bundle.model_copy(deep=True)
    bundle.criteria_revision_number = 1
    provenance = bundle.review.criteria_source_provenance
    assert provenance is not None
    bundle.junit_evidence_imports = [
        JUnitEvidenceImport(
            schema_version="junit-import-v1",
            evidence_boundary=JUnitEvidenceBoundary(),
            import_id=f"import-{artifact_digest[0]}",
            repository=bundle.review.repository,
            pr_number=bundle.review.pr_number,
            head_sha=bundle.review.head_sha,
            criteria_revision_number=1,
            confirmed_criteria_sha256=normalized_criteria_sha256(bundle.criteria),
            criteria_source_provenance=provenance,
            artifact_sha256=artifact_digest,
            imported_by="Fixture owner",
            imported_at=bundle.review.created_at,
            totals={
                "total": 2,
                "passed": 1,
                "failures": 1,
                "errors": 0,
                "skipped": 0,
            },
            test_cases=[
                {
                    "test_case_id": "suite-0001-case-0001",
                    "suite_id": "suite-0001",
                    "suite_name": "unit",
                    "class_name": None,
                    "test_name": "test_one",
                    "status": "passed",
                },
                {
                    "test_case_id": "suite-0001-case-0002",
                    "suite_id": "suite-0001",
                    "suite_name": "unit",
                    "class_name": None,
                    "test_name": "test_two",
                    "status": "failure",
                },
            ],
            criterion_mappings=[
                {
                    "criterion_id": "AC-01",
                    "test_case_ids": mapped_case_ids,
                }
            ],
            limitations=["External non-gating context."],
        )
    ]
    return ReviewBundle.model_validate(bundle.model_dump(mode="python"))


def test_comparison_preserves_legacy_unlinked_manual_verification_as_needs_review() -> None:
    previous = bundle_with(head_sha="old")
    current = bundle_with(head_sha="new")
    current.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            claimed_evidence_level=EvidenceLevel.E3,
            reviewer="QA",
            comment="Observed the scenario",
        )
    ]
    current.gate = evaluate_gate(
        current.review,
        current.criteria,
        current.findings,
        current.resolutions,
    )

    comparison = compare_reviews(previous, current)

    assert current.runtime_evidence == []
    assert current.resolutions[0].runtime_evidence_id is None
    assert current.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert "runtime_verification_reconfirmation_required" in current.gate.reason_codes
    assert comparison.current_gate is GateVerdict.NEEDS_REVIEW


def bundle(*, head_sha: str, status: FindingStatus, with_evidence: bool) -> ReviewBundle:
    review = Review(
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha=head_sha,
        input_origin=ReviewInputOrigin.CONSTRUCTED_DEMO,
        check_state=CheckState.PASSING,
        ci_observation=passing_ci_observation(),
        criteria_confirmed=True,
        final_acceptance=with_evidence,
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
            comment="Reviewed candidate evidence" if with_evidence else "",
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
    criteria = [Criterion(criterion_id="AC-01", text="Export CSV")]
    review.criteria_source_provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_text="Export CSV",
        criteria=criteria,
        confirmed_by="Fixture owner",
        confirmed_at=review.created_at,
    )
    gate = evaluate_gate(
        review,
        criteria,
        findings,
        resolutions,
    )
    return ReviewBundle(
        review=review,
        source_text="Export CSV",
        criteria=criteria,
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
    assert comparison.criteria_requiring_decision_review == ["AC-01"]


def test_unchanged_evidence_does_not_require_prior_decision_review() -> None:
    previous = bundle(
        head_sha="same-head",
        status=FindingStatus.EVIDENCE_FOUND,
        with_evidence=True,
    )
    current = previous.model_copy(deep=True)

    comparison = compare_reviews(previous, current)

    assert comparison.criteria_requiring_decision_review == []


def test_changed_evidence_requires_review_even_when_decision_text_is_unchanged() -> None:
    previous = bundle(
        head_sha="old-head",
        status=FindingStatus.EVIDENCE_FOUND,
        with_evidence=True,
    )
    current = bundle(
        head_sha="new-head",
        status=FindingStatus.EVIDENCE_FOUND,
        with_evidence=True,
    )

    comparison = compare_reviews(previous, current)

    assert comparison.changed_human_resolutions == []
    assert comparison.criteria_requiring_decision_review == ["AC-01"]


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


def test_change_model_rejects_blank_reason() -> None:
    reference = EvidenceReference.from_item(evidence("EV-1", sha="head"))

    with pytest.raises(ValidationError, match="non-whitespace text"):
        EvidenceChange(
            criterion_id="AC-01",
            kind=EvidenceChangeKind.ADDED,
            current=reference,
            reason=" ",
        )


def test_change_model_rejects_reference_for_a_different_criterion() -> None:
    reference = EvidenceReference.from_item(evidence("EV-1", sha="head"))

    with pytest.raises(ValidationError, match="change criterion ID"):
        EvidenceChange(
            criterion_id="AC-02",
            kind=EvidenceChangeKind.ADDED,
            current=reference,
            reason="Candidate appears only in the current review.",
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        ("repository", "acme/other", "same repository"),
        ("pr_number", 2, "same pull request"),
    ],
)
def test_comparison_relationship_rejects_different_pull_request_identity(
    field_name: str, field_value: str | int, message: str
) -> None:
    previous = bundle(head_sha="old-head", status=FindingStatus.MISSING, with_evidence=False)
    current = bundle(head_sha="new-head", status=FindingStatus.MISSING, with_evidence=False)
    current.review = current.review.model_copy(update={field_name: field_value})

    with pytest.raises(ValueError, match=message):
        compare_reviews(previous, current)


def test_comparison_relationship_rejects_changed_ordered_criteria() -> None:
    previous = bundle_with(
        evidence("EV-AC-01", sha="old-head", criterion_id="AC-01"),
        evidence("EV-AC-02", sha="old-head", criterion_id="AC-02"),
        head_sha="old-head",
    )
    current = bundle_with(
        evidence("EV-AC-01", sha="new-head", criterion_id="AC-01"),
        evidence("EV-AC-02", sha="new-head", criterion_id="AC-02"),
        head_sha="new-head",
    )
    current.criteria = list(reversed(current.criteria))
    current.review = current.review.model_copy(
        update={
            "criteria_source_provenance": build_criteria_source_provenance(
                source_uri="https://example.test/requirements",
                source_text=current.source_text,
                criteria=current.criteria,
                confirmed_by="Fixture owner",
                confirmed_at=current.review.created_at,
            )
        }
    )

    with pytest.raises(ValueError, match="identical ordered criterion definitions"):
        compare_reviews(previous, current)


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("source_uri", "https://example.test/other-requirements"),
        ("source_revision", "revision-2"),
    ],
)
def test_comparison_relationship_rejects_incompatible_criteria_source_provenance(
    field_name: str, field_value: str
) -> None:
    previous = bundle(head_sha="old-head", status=FindingStatus.MISSING, with_evidence=False)
    current = bundle(head_sha="new-head", status=FindingStatus.MISSING, with_evidence=False)
    provenance = current.review.criteria_source_provenance
    assert provenance is not None
    current.review = current.review.model_copy(
        update={
            "criteria_source_provenance": provenance.model_copy(
                update={field_name: field_value}
            )
        }
    )

    with pytest.raises(ValueError, match="compatible criteria-source provenance"):
        compare_reviews(previous, current)


def test_comparison_relationship_rejects_missing_criteria_source_provenance() -> None:
    previous = bundle(head_sha="old-head", status=FindingStatus.MISSING, with_evidence=False)
    current = bundle(head_sha="new-head", status=FindingStatus.MISSING, with_evidence=False)
    current.review = current.review.model_copy(update={"criteria_source_provenance": None})

    with pytest.raises(ValueError, match="criteria-source provenance"):
        compare_reviews(previous, current)


def test_comparison_relationship_allows_new_confirmation_attestation() -> None:
    previous = bundle(head_sha="old-head", status=FindingStatus.MISSING, with_evidence=False)
    current = bundle(head_sha="new-head", status=FindingStatus.MISSING, with_evidence=False)
    provenance = current.review.criteria_source_provenance
    assert provenance is not None
    current.review = current.review.model_copy(
        update={
            "criteria_source_provenance": provenance.model_copy(
                update={
                    "confirmed_by": "Second fixture owner",
                    "confirmed_at": provenance.confirmed_at + timedelta(minutes=5),
                }
            )
        }
    )

    comparison = compare_reviews(previous, current)

    assert comparison.current_head_sha == "new-head"


def test_comparison_relationship_rejects_candidate_from_unrelated_head() -> None:
    previous = bundle_with(
        evidence("EV-old", sha="old-head"),
        head_sha="old-head",
    )
    current = bundle_with(
        evidence("EV-new", sha="unrelated-head"),
        head_sha="new-head",
    )

    with pytest.raises(ValueError, match="evidence candidates must match the reviewed head"):
        compare_reviews(previous, current)


def test_comparison_relationship_rejects_non_exact_live_public_head() -> None:
    previous = bundle(head_sha="old-head", status=FindingStatus.MISSING, with_evidence=False)
    current = bundle(head_sha="new-head", status=FindingStatus.MISSING, with_evidence=False)
    for review_bundle in (previous, current):
        review_bundle.review = review_bundle.review.model_copy(
            update={
                "input_origin": ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
                "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            }
        )

    with pytest.raises(ValueError, match="exact head SHAs"):
        compare_reviews(previous, current)


def test_comparison_relationship_rejects_non_exact_legacy_unknown_head() -> None:
    previous = bundle(head_sha="old-head", status=FindingStatus.MISSING, with_evidence=False)
    current = bundle(head_sha="new-head", status=FindingStatus.MISSING, with_evidence=False)
    for review_bundle in (previous, current):
        review_bundle.review = review_bundle.review.model_copy(
            update={"input_origin": ReviewInputOrigin.LEGACY_UNKNOWN}
        )

    with pytest.raises(ValueError, match="exact head SHAs"):
        compare_reviews(previous, current)


def test_comparison_projects_unchanged_added_removed_and_mapping_modified_junit_imports() -> None:
    head = "a" * 40
    base = bundle_with(head_sha=head)
    unchanged_previous = with_junit_import(
        base, artifact_digest="b" * 64, mapped_case_ids=["suite-0001-case-0001"]
    )
    unchanged_current = with_junit_import(
        base, artifact_digest="b" * 64, mapped_case_ids=["suite-0001-case-0001"]
    )

    unchanged = compare_reviews(unchanged_previous, unchanged_current)
    assert [item.kind.value for item in unchanged.junit_import_changes] == [
        "unchanged"
    ]
    assert unchanged.junit_import_changes[0].artifact_sha256 == "b" * 64

    modified_current = with_junit_import(
        base,
        artifact_digest="b" * 64,
        mapped_case_ids=["suite-0001-case-0001", "suite-0001-case-0002"],
    )
    modified = compare_reviews(unchanged_previous, modified_current)
    assert [item.kind.value for item in modified.junit_import_changes] == [
        "mapping_modified"
    ]
    assert modified.junit_import_changes[0].previous is not None
    assert modified.junit_import_changes[0].current is not None

    different_current = with_junit_import(
        base, artifact_digest="c" * 64, mapped_case_ids=["suite-0001-case-0001"]
    )
    different = compare_reviews(unchanged_previous, different_current)
    assert [item.kind.value for item in different.junit_import_changes] == [
        "removed",
        "added",
    ]


def test_changed_junit_mapping_requires_review_only_for_previously_resolved_criteria() -> None:
    head = "a" * 40
    base = bundle_with(
        evidence("EV-AC-01", sha=head, criterion_id="AC-01"),
        evidence("EV-AC-02", sha=head, criterion_id="AC-02"),
        head_sha=head,
    )
    base.resolutions = [
        HumanResolution(
            criterion_id=criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Owner reviewed existing evidence.",
        )
        for criterion_id in ("AC-01", "AC-02")
    ]
    base.gate = evaluate_gate(
        base.review, base.criteria, base.findings, base.resolutions
    )
    previous = with_junit_import(
        base, artifact_digest="d" * 64, mapped_case_ids=["suite-0001-case-0001"]
    )
    current = with_junit_import(
        base,
        artifact_digest="d" * 64,
        mapped_case_ids=["suite-0001-case-0001", "suite-0001-case-0002"],
    )

    comparison = compare_reviews(previous, current)

    assert comparison.criteria_requiring_decision_review == ["AC-01"]
    assert previous.resolutions == current.resolutions
    assert previous.gate == current.gate


def test_comparison_revalidates_junit_import_relationships_before_projection() -> None:
    head = "a" * 40
    valid = with_junit_import(
        bundle_with(head_sha=head),
        artifact_digest="e" * 64,
        mapped_case_ids=["suite-0001-case-0001"],
    )
    tampered = valid.model_copy(deep=True)
    imported = tampered.junit_evidence_imports[0]
    object.__setattr__(imported, "head_sha", "f" * 40)

    with pytest.raises(ValidationError, match="JUnit import identity"):
        compare_reviews(valid, tampered)
