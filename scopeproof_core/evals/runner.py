"""Execute every labelled ScopeProof fixture through the product review path."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from scopeproof_core.demo import build_review_from_paths
from scopeproof_core.schemas.models import (
    EvidenceSourceScope,
    FindingStatus,
    GateVerdict,
    Priority,
)

REQUIRED_CATEGORIES = frozenset(
    {
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
)


class BenchmarkCaseResult(BaseModel):
    case_id: str
    category: str
    criterion_count: int
    expected_gate: str
    historical_expected_gate: str | None = None
    actual_gate: str
    human_review_required: bool
    expected_status_count: int = Field(ge=0)
    status_mismatch_count: int = Field(ge=0)
    evidence_link_count: int = Field(ge=0)
    mismatches: list[str] = Field(default_factory=list)
    evidence_link_errors: list[str] = Field(default_factory=list)
    unmapped_changed_files: list[str] = Field(default_factory=list)


class BenchmarkResult(BaseModel):
    cases: int
    executed_case_count: int
    executed_criterion_count: int
    must_have_false_ready: int
    uncited_file_false_ready: int = 0
    false_blocker: int
    mismatches: list[str] = Field(default_factory=list)
    declared_case_coverage: list[str] = Field(default_factory=list)
    unexecuted_declared_categories: list[str] = Field(default_factory=list)
    case_results: list[BenchmarkCaseResult] = Field(default_factory=list)


def _load_label(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_permalink(
    repository: str, head_sha: str, path: str, line_start: int, line_end: int
) -> str:
    return f"https://github.com/{repository}/blob/{head_sha}/{path}#L{line_start}-L{line_end}"


class CurrentGateExpectation(BaseModel):
    """Versioned correction alongside, never in place of, a historical label."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    historical_expected_gate: GateVerdict
    current_expected_gate: GateVerdict
    historical_label_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1)


def _evaluate_case(
    fixture_path: Path,
    label_path: Path,
    current_expectation: CurrentGateExpectation | None = None,
) -> tuple[BenchmarkCaseResult, int, int]:
    labels = _load_label(label_path)
    expected_gate = labels["expected_gate"]
    historical_expected_gate = None
    if current_expectation is not None:
        if current_expectation.case_id != labels["case_id"]:
            raise ValueError("current gate expectation case ID does not match historical label")
        if current_expectation.historical_expected_gate.value != expected_gate:
            raise ValueError("historical gate expectation changed")
        # Git may check out this frozen JSON label with CRLF on Windows.
        # Canonicalize only that newline conversion before comparing its pinned hash.
        if (
            sha256(label_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            != current_expectation.historical_label_sha256
        ):
            raise ValueError("historical gate label changed")
        historical_expected_gate = expected_gate
        expected_gate = current_expectation.current_expected_gate.value
    bundle = build_review_from_paths(fixture_path, label_path)
    actual_statuses = {finding.criterion_id: finding.status.value for finding in bundle.findings}
    expected_statuses = labels["expected_statuses"]
    status_mismatches = [
        f"{criterion_id}: expected {expected}, got {actual_statuses.get(criterion_id)}"
        for criterion_id, expected in expected_statuses.items()
        if actual_statuses.get(criterion_id) != expected
    ]
    case_mismatches = [*status_mismatches]
    if bundle.gate.verdict.value != expected_gate:
        case_mismatches.append(
            f"gate: expected {expected_gate}, got {bundle.gate.verdict.value}"
        )

    expected_ids = labels.get("expected_evidence_ids", {})
    evidence_by_criterion: dict[str, set[str]] = {}
    evidence_link_errors: list[str] = []
    expected_head = labels.get("expected_head_sha", bundle.review.head_sha)
    for item in bundle.evidence:
        evidence_by_criterion.setdefault(item.criterion_id, set()).add(item.evidence_id)
        expected_link = _expected_permalink(
            bundle.review.repository,
            expected_head,
            item.file_path,
            item.line_start,
            item.line_end,
        )
        if item.commit_sha != expected_head or item.permalink != expected_link:
            evidence_link_errors.append(f"{item.criterion_id}: invalid immutable permalink")
    for criterion_id, ids in expected_ids.items():
        actual_ids = evidence_by_criterion.get(criterion_id, set())
        if not set(ids).issubset(actual_ids):
            case_mismatches.append(
                f"{criterion_id}: expected evidence IDs {sorted(ids)}, got {sorted(actual_ids)}"
            )

    linked_evidence_ids = {
        evidence_id for finding in bundle.findings for evidence_id in finding.evidence_ids
    }
    evidence_paths = {
        item.file_path for item in bundle.evidence
        if item.source_scope is EvidenceSourceScope.CHANGED_FILE
        and item.evidence_id in linked_evidence_ids
    }
    snapshot_data = json.loads(fixture_path.read_text(encoding="utf-8"))
    changed_paths = {file["path"] for file in snapshot_data.get("files", [])}
    actual_unmapped = sorted(changed_paths - evidence_paths)
    expected_unmapped = sorted(labels.get("expected_unmapped_files", []))
    if "expected_unmapped_files" in labels and actual_unmapped != expected_unmapped:
        case_mismatches.append(
            f"unmapped files: expected {expected_unmapped}, got {actual_unmapped}"
        )

    criterion_by_id = {criterion.criterion_id: criterion for criterion in bundle.criteria}
    false_ready = 0
    if bundle.gate.verdict is GateVerdict.READY:
        false_ready = sum(
            1
            for criterion_id, expected in expected_statuses.items()
            if criterion_by_id[criterion_id].priority is Priority.MUST_HAVE
            and expected in {FindingStatus.MISSING.value, FindingStatus.PARTIAL.value}
        )
    false_blocker = int(
        expected_gate == GateVerdict.READY.value
        and bundle.gate.verdict is GateVerdict.BLOCKED
    )
    result = BenchmarkCaseResult(
        case_id=labels["case_id"],
        category=labels["category"],
        criterion_count=len(bundle.criteria),
        expected_gate=expected_gate,
        historical_expected_gate=historical_expected_gate,
        actual_gate=bundle.gate.verdict.value,
        human_review_required=labels["human_review_required"],
        expected_status_count=len(expected_statuses),
        status_mismatch_count=len(status_mismatches),
        evidence_link_count=len(bundle.evidence),
        mismatches=case_mismatches,
        evidence_link_errors=sorted(set(evidence_link_errors)),
        unmapped_changed_files=actual_unmapped,
    )
    return result, false_ready, false_blocker


def run_benchmark(
    fixtures_dir: Path,
    labels_dir: Path,
    current_expectations: list[CurrentGateExpectation] | None = None,
) -> BenchmarkResult:
    """Execute every label file against its referenced immutable fixture."""
    if not fixtures_dir.is_dir() or not labels_dir.is_dir():
        raise FileNotFoundError("Both fixture and label directories must exist")
    case_results: list[BenchmarkCaseResult] = []
    false_ready = 0
    false_blocker = 0
    expectation_by_case = {
        item.case_id: item for item in (current_expectations or [])
    }
    if len(expectation_by_case) != len(current_expectations or []):
        raise ValueError("current gate expectation case IDs must be unique")
    used_expectations: set[str] = set()
    for label_path in sorted(labels_dir.glob("*.json")):
        labels = _load_label(label_path)
        if not labels.get("benchmark", False):
            continue
        fixture_path = fixtures_dir / labels["fixture"]
        if not fixture_path.is_file():
            message = f"Fixture {fixture_path.name} referenced by {label_path.name} is missing"
            raise FileNotFoundError(message)
        expectation = expectation_by_case.get(labels["case_id"])
        if expectation is not None:
            used_expectations.add(expectation.case_id)
        case, case_false_ready, case_false_blocker = _evaluate_case(
            fixture_path, label_path, expectation
        )
        case_results.append(case)
        false_ready += case_false_ready
        false_blocker += case_false_blocker

    categories = {case.category for case in case_results}
    if used_expectations != set(expectation_by_case):
        raise ValueError("current gate expectation references an unknown benchmark case")
    unexecuted = sorted(REQUIRED_CATEGORIES - categories)
    mismatches = [
        f"{case.case_id}: {message}"
        for case in case_results
        for message in [*case.mismatches, *case.evidence_link_errors]
    ]
    return BenchmarkResult(
        cases=len(case_results),
        executed_case_count=len(case_results),
        executed_criterion_count=sum(case.criterion_count for case in case_results),
        must_have_false_ready=false_ready,
        uncited_file_false_ready=sum(
            case.actual_gate == GateVerdict.READY.value and bool(case.unmapped_changed_files)
            for case in case_results
        ),
        false_blocker=false_blocker,
        mismatches=mismatches,
        declared_case_coverage=sorted(categories),
        unexecuted_declared_categories=unexecuted,
        case_results=case_results,
    )


def run_bundled_benchmark() -> BenchmarkResult:
    """Run every checked-in benchmark fixture, not a declared category list."""
    root = Path(__file__).resolve().parents[2]
    expectations = TypeAdapter(list[CurrentGateExpectation]).validate_json(
        (root / "evals" / "constructed_scope" / "current_gate_expectations.json")
        .read_text(encoding="utf-8")
    )
    return run_benchmark(
        root / "evals" / "fixtures", root / "evals" / "labels", expectations
    )


def main() -> int:
    result = run_bundled_benchmark()
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return int(
        bool(
            result.must_have_false_ready
            or result.uncited_file_false_ready
            or result.false_blocker
            or result.mismatches
            or result.unexecuted_declared_categories
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
