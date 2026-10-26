import json
from pathlib import Path

import pytest

from scopeproof_core.demo import build_demo_review, build_review_from_paths, load_demo_snapshot
from scopeproof_core.evals.runner import (
    CurrentGateExpectation,
    _evaluate_case,
    run_bundled_benchmark,
)
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
    assert result.uncited_file_false_ready == 0
    assert result.false_blocker == 0
    assert result.mismatches == []
    scope_case = next(item for item in result.case_results if item.case_id == "scope-expansion")
    assert scope_case.historical_expected_gate == "ready"
    assert scope_case.expected_gate == "needs_review"
    assert scope_case.actual_gate == "needs_review"


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


def test_scope_expansion_uncited_changed_file_cannot_be_ready() -> None:
    root = Path(__file__).resolve().parents[2] / "evals"
    bundle = build_review_from_paths(
        root / "fixtures/scope_expansion_pr.json",
        root / "labels/benchmark_scope_expansion.json",
    )

    assert bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert "uncited_changed_files" in bundle.gate.reason_codes


def test_historical_scope_label_hash_allows_windows_line_endings_only(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2] / "evals"
    original = (
        root / "labels/benchmark_scope_expansion.json"
    ).read_bytes().replace(b"\r\n", b"\n")
    copied_label = tmp_path / "benchmark_scope_expansion.json"
    copied_label.write_bytes(original.replace(b"\n", b"\r\n"))
    assert b"\r\r\n" not in copied_label.read_bytes()
    expectation = CurrentGateExpectation.model_validate(
        json.loads((root / "constructed_scope/current_gate_expectations.json").read_text())[0]
    )
    fixture = root / "fixtures/scope_expansion_pr.json"

    result, _, _ = _evaluate_case(fixture, copied_label, expectation)
    assert result.actual_gate == "needs_review"
    assert result.mismatches == []

    copied_label.write_bytes(original.replace(b"Export reviewed", b"Export was reviewed"))
    with pytest.raises(ValueError, match="historical gate label changed"):
        _evaluate_case(fixture, copied_label, expectation)
