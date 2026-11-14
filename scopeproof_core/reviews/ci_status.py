"""Read-only criterion status from an externally supplied CI manifest."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scopeproof_core.reporting.references import is_linkable_artifact_reference
from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    ReviewBundle,
    normalized_criteria_sha256,
)

MAX_CI_STATUS_BYTES = 1_048_576
EXACT_HEAD_PATTERN = r"^[0-9a-f]{40}$"
_MAX_TEST_MAPPINGS = 4096

_Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,159}$")]
_CriterionId = Annotated[str, Field(pattern=r"^AC-[0-9]{2,}$", max_length=40)]
_ReportedOutcome = Literal["passed", "failed", "skipped"]
_Status = Literal["passed", "failed", "skipped", "stale", "unknown"]


class CIStatusRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: _Identifier
    head_sha: str = Field(pattern=EXACT_HEAD_PATTERN)
    source_url: str = Field(max_length=2048)
    outcomes: dict[_Identifier, _ReportedOutcome] = Field(max_length=512)

    @field_validator("source_url")
    @classmethod
    def validate_run_reference(cls, value: str) -> str:
        if not is_linkable_artifact_reference(value) or "\\" in value:
            raise ValueError("run reference must be an absolute HTTPS URL")
        url = urlsplit(value)
        if url.scheme != "https" or url.username is not None:
            raise ValueError("run reference must use HTTPS without user information")
        return value


class CIStatusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["criterion-ci-status-v1"]
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN, max_length=255)
    pr_number: int = Field(gt=0)
    criteria_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_tests: dict[
        _CriterionId, Annotated[list[_Identifier], Field(min_length=1, max_length=512)]
    ] = Field(min_length=1, max_length=512)
    runs: list[CIStatusRun] = Field(max_length=100)

    @model_validator(mode="after")
    def require_unambiguous_manifest(self) -> CIStatusManifest:
        if sum(map(len, self.expected_tests.values())) > _MAX_TEST_MAPPINGS:
            raise ValueError("CI status manifest exceeds 4,096 criterion-to-test mappings")
        if len({run.run_id for run in self.runs}) != len(self.runs):
            raise ValueError("duplicate CI run IDs")
        expected: set[str] = set()
        for tests in self.expected_tests.values():
            if len(set(tests)) != len(tests):
                raise ValueError("duplicate expected test for a criterion")
            expected.update(tests)
        if any(run.outcomes.keys() - expected for run in self.runs):
            raise ValueError("run outcome references an undeclared test")
        return self


class CITestStatus(BaseModel, frozen=True):
    test_id: str
    status: _Status
    run_ids: tuple[str, ...] = ()
    reason: str


class CriterionCIStatus(BaseModel, frozen=True):
    criterion_id: str
    status: _Status
    tests: tuple[CITestStatus, ...] = ()


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("duplicate JSON keys in CI status manifest")
    return obj


def load_ci_status_manifest(payload: bytes) -> CIStatusManifest:
    """Parse one bounded UTF-8 manifest without following any references."""
    if len(payload) > MAX_CI_STATUS_BYTES:
        raise ValueError("CI status manifest exceeds the 1 MiB limit")
    try:
        obj = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("CI status manifest must be valid UTF-8 JSON") from exc
    return CIStatusManifest.model_validate(obj)


def _test_status(test_id: str, head: str, runs: Sequence[CIStatusRun]) -> CITestStatus:
    passed, failed, skipped, stale = [], [], [], []
    for run in runs:
        outcome = run.outcomes.get(test_id)
        if outcome is None:
            continue
        if run.head_sha != head:
            if outcome != "skipped":
                stale.append(run.run_id)
        elif outcome == "passed":
            passed.append(run.run_id)
        elif outcome == "failed":
            failed.append(run.run_id)
        else:
            skipped.append(run.run_id)
    # A targeted run can omit a test that already ran on this exact build.
    if passed and failed:
        status, ids, reason = "unknown", passed + failed, "Exact-build results conflict."
    elif failed:
        status, ids, reason = "failed", failed, "CI reports failure for the reviewed build."
    elif passed:
        status, ids, reason = "passed", passed, "CI reports a pass for the reviewed build."
    elif skipped:
        status, ids, reason = "skipped", skipped, "CI explicitly skipped this test on this build."
    elif stale:
        status, ids, reason = "stale", stale, "CI reports a result for a different build."
    else:
        status, ids, reason = "unknown", [], "The manifest supplies no result or explicit skip."
    return CITestStatus(test_id=test_id, status=status, run_ids=tuple(sorted(ids)), reason=reason)


def _criterion_status(tests: tuple[CITestStatus, ...]) -> _Status:
    statuses = {test.status for test in tests}
    if "failed" in statuses:
        return "failed"
    if statuses == {"passed"}:
        return "passed"
    if "skipped" in statuses and statuses <= {"passed", "skipped"}:
        return "skipped"
    if "stale" in statuses and statuses <= {"passed", "stale"}:
        return "stale"
    return "unknown"


def criterion_ci_statuses(
    bundle: ReviewBundle, manifest: CIStatusManifest | None = None,
) -> list[CriterionCIStatus]:
    """Project supplied CI context onto the confirmed analysis without updating it."""
    review = bundle.review
    if not review.criteria_confirmed or not re.fullmatch(EXACT_HEAD_PATTERN, review.head_sha):
        raise ValueError("CI status requires confirmed criteria and an exact reviewed head")
    if manifest is None:
        return [
            CriterionCIStatus(criterion_id=criterion.criterion_id, status="unknown")
            for criterion in bundle.criteria
        ]
    criterion_ids = {criterion.criterion_id for criterion in bundle.criteria}
    if (
        manifest.repository.casefold() != review.repository.casefold()
        or manifest.pr_number != review.pr_number
        or manifest.criteria_sha256 != normalized_criteria_sha256(bundle.criteria)
        or manifest.expected_tests.keys() - criterion_ids
    ):
        raise ValueError("CI status manifest does not match the confirmed review context")
    test_statuses = {
        test_id: _test_status(test_id, review.head_sha, manifest.runs)
        for test_id in {test_id for tests in manifest.expected_tests.values() for test_id in tests}
    }
    results = []
    for criterion in bundle.criteria:
        tests = tuple(
            test_statuses[test_id]
            for test_id in manifest.expected_tests.get(criterion.criterion_id, ())
        )
        results.append(
            CriterionCIStatus(
                criterion_id=criterion.criterion_id, status=_criterion_status(tests), tests=tests,
            )
        )
    return results
