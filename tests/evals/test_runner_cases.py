from __future__ import annotations

import json
import shutil
from pathlib import Path

from scopeproof_core.evals.runner import REQUIRED_CATEGORIES, run_benchmark, run_bundled_benchmark


def test_runner_executes_every_required_category() -> None:
    result = run_bundled_benchmark()

    assert result.executed_case_count == len(REQUIRED_CATEGORIES) == 12
    assert result.executed_criterion_count >= 12
    assert {case.category for case in result.case_results} == REQUIRED_CATEGORIES
    assert result.unexecuted_declared_categories == []
    assert result.mismatches == []


def test_runner_reports_case_level_expected_and_actual_gate() -> None:
    result = run_bundled_benchmark()
    case = next(item for item in result.case_results if item.category == "active_filter_omitted")

    assert case.case_id == "active-filter-omitted"
    assert case.expected_gate == "blocked"
    assert case.actual_gate == "blocked"
    assert case.human_review_required is True


def test_runner_reports_bad_permalink_with_case_and_criterion(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    fixtures = tmp_path / "fixtures"
    labels = tmp_path / "labels"
    shutil.copytree(root / "evals" / "fixtures", fixtures)
    shutil.copytree(root / "evals" / "labels", labels)

    fixture_path = fixtures / "complete_implementation_pr.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture["head_sha"] = "changed-head"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    result = run_benchmark(fixtures, labels)
    case = next(item for item in result.case_results if item.case_id == "complete-implementation")

    assert case.evidence_link_errors == ["AC-01: invalid immutable permalink"]
    assert "complete-implementation: AC-01: invalid immutable permalink" in result.mismatches


def test_runner_counts_false_ready_only_for_expected_must_have_gaps() -> None:
    result = run_bundled_benchmark()

    assert result.must_have_false_ready == 0
    assert result.false_blocker == 0
