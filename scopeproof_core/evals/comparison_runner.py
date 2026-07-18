"""Run the deliberately constructed re-review evidence-integrity benchmark."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from scopeproof_core.demo import build_review_from_paths
from scopeproof_core.reviews.comparison import (
    EvidenceChangeCounts,
    EvidenceChangeKind,
    compare_reviews,
)

_MANIFEST_NAME = "rereview_evidence_integrity.json"
_EVIDENCE_BOUNDARY = "deliberately constructed engineering evidence"


class _ComparisonBenchmarkCaseManifest(BaseModel):
    case_id: str = Field(min_length=1)
    previous_fixture: str = Field(min_length=1)
    previous_labels: str = Field(min_length=1)
    current_fixture: str = Field(min_length=1)
    current_labels: str = Field(min_length=1)
    expected_counts: EvidenceChangeCounts


class _ComparisonBenchmarkManifest(BaseModel):
    cases: list[_ComparisonBenchmarkCaseManifest] = Field(min_length=1)
    evidence_boundary: Literal["deliberately constructed engineering evidence"]
    does_not_advance_stage_1: Literal[True]

    @model_validator(mode="after")
    def _case_ids_are_unique(self) -> _ComparisonBenchmarkManifest:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("comparison benchmark case IDs must be unique")
        return self


class ComparisonBenchmarkCaseResult(BaseModel):
    """Expected and observed counts for one executed comparison case."""

    case_id: str
    expected_counts: EvidenceChangeCounts
    actual_counts: EvidenceChangeCounts
    mismatches: list[str] = Field(default_factory=list)


class ComparisonBenchmarkResult(BaseModel):
    """Validated aggregate result with an explicit research-evidence boundary."""

    executed_case_count: int = Field(ge=0)
    expected_counts: EvidenceChangeCounts
    actual_counts: EvidenceChangeCounts
    mismatches: list[str] = Field(default_factory=list)
    evidence_boundary: Literal["deliberately constructed engineering evidence"]
    does_not_advance_stage_1: Literal[True]
    case_results: list[ComparisonBenchmarkCaseResult] = Field(default_factory=list)


def _load_manifest(path: Path) -> _ComparisonBenchmarkManifest:
    if not path.is_file():
        raise FileNotFoundError(f"Comparison benchmark manifest is missing: {path.name}")
    return _ComparisonBenchmarkManifest.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def _required_file(root: Path, name: str) -> Path:
    path = root / name
    if not path.is_file():
        raise FileNotFoundError(f"Comparison benchmark input is missing: {name}")
    return path


def _sum_counts(counts: list[EvidenceChangeCounts]) -> EvidenceChangeCounts:
    return EvidenceChangeCounts(
        **{
            kind.value: sum(getattr(item, kind.value) for item in counts)
            for kind in EvidenceChangeKind
        }
    )


def run_comparison_benchmark(root: Path) -> ComparisonBenchmarkResult:
    """Execute local paired reviews without running any fixture repository code."""

    manifest = _load_manifest(root / _MANIFEST_NAME)
    case_results: list[ComparisonBenchmarkCaseResult] = []
    aggregate_mismatches: list[str] = []
    for case_manifest in manifest.cases:
        previous = build_review_from_paths(
            _required_file(root, case_manifest.previous_fixture),
            _required_file(root, case_manifest.previous_labels),
        )
        current = build_review_from_paths(
            _required_file(root, case_manifest.current_fixture),
            _required_file(root, case_manifest.current_labels),
        )
        actual = compare_reviews(previous, current).evidence_change_counts
        mismatches = [
            f"{kind.value}: expected "
            f"{getattr(case_manifest.expected_counts, kind.value)}, "
            f"got {getattr(actual, kind.value)}"
            for kind in EvidenceChangeKind
            if getattr(case_manifest.expected_counts, kind.value)
            != getattr(actual, kind.value)
        ]
        case_results.append(
            ComparisonBenchmarkCaseResult(
                case_id=case_manifest.case_id,
                expected_counts=case_manifest.expected_counts,
                actual_counts=actual,
                mismatches=mismatches,
            )
        )
        aggregate_mismatches.extend(
            f"{case_manifest.case_id}: {message}" for message in mismatches
        )
    return ComparisonBenchmarkResult(
        executed_case_count=len(case_results),
        expected_counts=_sum_counts(
            [case.expected_counts for case in case_results]
        ),
        actual_counts=_sum_counts([case.actual_counts for case in case_results]),
        mismatches=aggregate_mismatches,
        evidence_boundary=_EVIDENCE_BOUNDARY,
        does_not_advance_stage_1=True,
        case_results=case_results,
    )


def run_bundled_comparison_benchmark() -> ComparisonBenchmarkResult:
    """Run the checked-in comparison corpus from the installed project tree."""

    root = Path(__file__).resolve().parents[2]
    return run_comparison_benchmark(root / "evals" / "comparisons")


def main() -> int:
    result = run_bundled_comparison_benchmark()
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return int(bool(result.mismatches or result.executed_case_count == 0))


if __name__ == "__main__":
    raise SystemExit(main())
