from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scopeproof_core.evals.comparison_runner import (
    run_bundled_comparison_benchmark,
    run_comparison_benchmark,
)


def test_bundled_comparison_benchmark_executes_constructed_case() -> None:
    result = run_bundled_comparison_benchmark()

    assert result.executed_case_count == 1
    assert result.expected_counts.model_dump() == {
        "unchanged": 0,
        "relocated": 1,
        "modified": 1,
        "added": 3,
        "removed": 3,
    }
    assert result.actual_counts == result.expected_counts
    assert result.mismatches == []
    assert result.evidence_boundary == "deliberately constructed engineering evidence"
    assert result.does_not_advance_stage_1 is True


def test_comparison_benchmark_requires_manifest(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"rereview_evidence_integrity\.json"):
        run_comparison_benchmark(tmp_path)


def test_comparison_benchmark_reports_bounded_count_mismatch(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "evals" / "comparisons"
    target = tmp_path / "comparisons"
    shutil.copytree(source, target)
    manifest_path = target / "rereview_evidence_integrity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_counts"]["modified"] = 2
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = run_comparison_benchmark(target)

    assert result.executed_case_count == 1
    assert result.mismatches == [
        "rereview-evidence-integrity: modified: expected 2, got 1"
    ]
    assert result.does_not_advance_stage_1 is True
