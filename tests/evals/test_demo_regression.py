from scopeproof_core.demo import build_demo_review, load_demo_snapshot
from scopeproof_core.evals.runner import run_bundled_benchmark
from scopeproof_core.schemas.models import (
    CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
    FindingStatus,
    GateVerdict,
)


def test_demo_fixture_is_disclosed_as_deliberately_constructed() -> None:
    snapshot = load_demo_snapshot()
    assert "Deliberately constructed demo" in snapshot.description


def test_demo_is_deliberately_blocked_for_missing_must_haves() -> None:
    bundle = build_demo_review()
    statuses = {finding.criterion_id: finding.status for finding in bundle.findings}
    assert statuses == {
        "AC-01": FindingStatus.EVIDENCE_FOUND,
        "AC-02": FindingStatus.PARTIAL,
        "AC-03": FindingStatus.MISSING,
        "AC-04": FindingStatus.MISSING,
    }
    assert bundle.gate.verdict is GateVerdict.BLOCKED


def test_demo_uses_named_constructed_criteria_source_provenance() -> None:
    bundle = build_demo_review()

    assert bundle.review.criteria_source_provenance is not None
    assert (
        bundle.review.criteria_source_provenance.source_uri
        == CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI
    )


def test_demo_records_one_retrieval_diagnostic_per_criterion() -> None:
    bundle = build_demo_review()

    assert [item.criterion_id for item in bundle.retrieval_diagnostics] == [
        criterion.criterion_id for criterion in bundle.criteria
    ]
    assert {
        item.criterion_id: item.accepted_candidate_count
        for item in bundle.retrieval_diagnostics
    } == {
        criterion.criterion_id: sum(
            evidence.criterion_id == criterion.criterion_id
            for evidence in bundle.evidence
        )
        for criterion in bundle.criteria
    }


def test_benchmark_reports_zero_must_have_false_ready() -> None:
    result = run_bundled_benchmark()
    assert result.must_have_false_ready == 0
    assert result.false_blocker == 0
    assert result.mismatches == []


def test_benchmark_declares_required_case_coverage() -> None:
    result = run_bundled_benchmark()
    assert set(result.declared_case_coverage) == {
        "complete_implementation",
        "implementation_without_tests",
        "happy_path_only",
        "missing_error_state",
        "active_filter_omitted",
        "analytics_omitted",
        "permission_without_authorization_test",
        "description_claim_not_in_code",
        "test_checks_wrong_behavior",
        "scope_expansion",
        "ambiguous_criterion",
        "unchanged_file_evidence",
    }
