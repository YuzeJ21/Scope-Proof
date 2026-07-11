"""Compare deterministic findings with human-owned fixture labels."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from scopeproof_core.demo import build_demo_review, load_demo_labels
from scopeproof_core.schemas.models import FindingStatus, GateVerdict, Priority


class BenchmarkResult(BaseModel):
    cases: int
    must_have_false_ready: int
    false_blocker: int
    mismatches: list[str] = Field(default_factory=list)
    declared_case_coverage: list[str] = Field(default_factory=list)


def run_bundled_benchmark() -> BenchmarkResult:
    """Evaluate the checked-in demo using the same production analysis path."""
    bundle = build_demo_review()
    labels = load_demo_labels()
    actual = {finding.criterion_id: finding.status.value for finding in bundle.findings}
    expected = labels["expected_statuses"]
    mismatches = [
        f"{criterion_id}: expected {status}, got {actual.get(criterion_id)}"
        for criterion_id, status in expected.items()
        if actual.get(criterion_id) != status
    ]
    if bundle.gate.verdict.value != labels["expected_gate"]:
        mismatches.append(
            f"gate: expected {labels['expected_gate']}, got {bundle.gate.verdict.value}"
        )

    false_ready = 0
    if bundle.gate.verdict is GateVerdict.READY:
        criterion_by_id = {criterion.criterion_id: criterion for criterion in bundle.criteria}
        false_ready = sum(
            1
            for criterion_id, status in expected.items()
            if criterion_by_id[criterion_id].priority is Priority.MUST_HAVE
            and status in {FindingStatus.MISSING.value, FindingStatus.PARTIAL.value}
        )
    false_blocker = int(
        labels["expected_gate"] == GateVerdict.READY.value
        and bundle.gate.verdict is GateVerdict.BLOCKED
    )
    return BenchmarkResult(
        cases=len(expected),
        must_have_false_ready=false_ready,
        false_blocker=false_blocker,
        mismatches=mismatches,
        declared_case_coverage=labels["declared_case_coverage"],
    )


def run_benchmark(fixtures_dir: Path, labels_dir: Path) -> BenchmarkResult:
    """Validate paths, then run the bundled schema-compatible benchmark."""
    if not fixtures_dir.is_dir() or not labels_dir.is_dir():
        raise FileNotFoundError("Both fixture and label directories must exist")
    return run_bundled_benchmark()


def main() -> int:
    result = run_bundled_benchmark()
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return int(bool(result.must_have_false_ready or result.mismatches))


if __name__ == "__main__":
    raise SystemExit(main())
