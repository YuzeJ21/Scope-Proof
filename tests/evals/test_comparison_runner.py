from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from scopeproof_core.evals.comparison_runner import (
    run_bundled_comparison_benchmark,
    run_comparison_benchmark,
)


def test_bundled_comparison_benchmark_executes_constructed_corpus() -> None:
    result = run_bundled_comparison_benchmark()

    assert result.executed_case_count == 2
    assert result.expected_counts.model_dump() == {
        "unchanged": 1,
        "relocated": 1,
        "modified": 1,
        "added": 3,
        "removed": 3,
    }
    assert result.actual_counts == result.expected_counts
    assert result.mismatches == []
    assert [case.case_id for case in result.case_results] == [
        "rereview-evidence-integrity",
        "unchanged-reference",
    ]
    assert result.case_results[1].actual_counts.model_dump() == {
        "unchanged": 1,
        "relocated": 0,
        "modified": 0,
        "added": 0,
        "removed": 0,
    }
    assert result.evidence_boundary == "deliberately constructed engineering evidence"
    assert result.does_not_advance_stage_1 is True


def test_comparison_benchmark_requires_manifest(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"rereview_evidence_integrity\.json"):
        run_comparison_benchmark(tmp_path)


def test_comparison_benchmark_reports_missing_declared_input(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "evals" / "comparisons"
    target = tmp_path / "comparisons"
    shutil.copytree(source, target)
    manifest_path = target / "rereview_evidence_integrity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["current_fixture"] = "missing_pr.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        FileNotFoundError,
        match=r"Comparison benchmark input is missing: missing_pr\.json",
    ):
        run_comparison_benchmark(target)


def test_comparison_benchmark_reports_bounded_count_mismatch(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "evals" / "comparisons"
    target = tmp_path / "comparisons"
    shutil.copytree(source, target)
    manifest_path = target / "rereview_evidence_integrity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["expected_counts"]["modified"] = 2
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_comparison_benchmark(target)

    assert result.executed_case_count == 2
    assert result.mismatches == [
        "rereview-evidence-integrity: modified: expected 2, got 1"
    ]
    assert result.does_not_advance_stage_1 is True


def test_comparison_benchmark_rejects_empty_corpus(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "evals" / "comparisons"
    target = tmp_path / "comparisons"
    shutil.copytree(source, target)
    manifest_path = target / "rereview_evidence_integrity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValidationError, match="at least 1 item"):
        run_comparison_benchmark(target)


def test_comparison_benchmark_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "evals" / "comparisons"
    target = tmp_path / "comparisons"
    shutil.copytree(source, target)
    manifest_path = target / "rereview_evidence_integrity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"] = [manifest["cases"][0], manifest["cases"][0]]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        run_comparison_benchmark(target)
