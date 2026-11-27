"""Read-only comparison of supplied CI assertions for one confirmed reviewed commit."""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from scopeproof_core.gates.validation import validated_review_bundle
from scopeproof_core.reporting.ci_snapshot import CIStatusSnapshot, build_ci_status_snapshot
from scopeproof_core.reviews.ci_status import (
    MAX_CI_STATUS_BYTES,
    CIStatusManifest,
    CIStatusRun,
    CITestStatus,
    load_ci_status_manifest,
)
from scopeproof_core.schemas.models import ReviewBundle

_Payload = Annotated[bytes, Field(min_length=1, max_length=MAX_CI_STATUS_BYTES)]
_Change = Literal["added", "removed", "changed", "unchanged"]
CI_COMPARISON_BOUNDARY = (
    "Externally supplied CI context. Previous/current reflect supplied file order, "
    "not verified chronology. ScopeProof does not authenticate these manifests, run tests, "
    "or change the saved review, evidence or acceptance decision."
)


class CITestComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    test_id: str
    change: _Change
    previous_criterion_ids: tuple[str, ...]
    current_criterion_ids: tuple[str, ...]
    previous: CITestStatus | None
    current: CITestStatus | None


class CIRunComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    run_id: str
    change: _Change
    previous: CIStatusRun | None
    current: CIStatusRun | None


def _change(previous: object | None, current: object | None) -> _Change:
    if previous is None:
        return "added"
    if current is None:
        return "removed"
    return "unchanged" if previous == current else "changed"


def _parse_manifest(payload: bytes) -> CIStatusManifest:
    try:
        return load_ci_status_manifest(payload)
    except ValidationError:
        raise ValueError("CI comparison input does not match the manifest format") from None


def _tests(
    snapshot: CIStatusSnapshot,
) -> tuple[dict[str, CITestStatus], dict[str, tuple[str, ...]]]:
    tests: dict[str, CITestStatus] = {}
    criteria: dict[str, list[str]] = {}
    for criterion in snapshot.criteria:
        for test in criterion.tests:
            if test != tests.setdefault(test.test_id, test):
                raise ValueError("inconsistent supplied status for a shared test")
            criteria.setdefault(test.test_id, []).append(criterion.criterion_id)
    return tests, {test: tuple(ids) for test, ids in criteria.items()}


class CIStatusComparison(BaseModel):
    """Validated inputs; all comparison rows are derived rather than trusted on import."""

    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True,
    )

    schema_version: Literal["criterion-ci-comparison-v1"] = "criterion-ci-comparison-v1"
    bundle: ReviewBundle
    previous_manifest: CIStatusManifest
    current_manifest: CIStatusManifest
    previous_payload: _Payload
    current_payload: _Payload

    @field_validator("bundle")
    @classmethod
    def validate_bundle(cls, value: ReviewBundle) -> ReviewBundle:
        return validated_review_bundle(value)

    @field_validator("previous_manifest", "current_manifest", mode="before")
    @classmethod
    def revalidate_manifest(cls, value: object) -> object:
        if isinstance(value, CIStatusManifest):
            return CIStatusManifest.model_validate(value.model_dump(mode="python"))
        return value

    @model_validator(mode="after")
    def validate_both_contexts(self) -> CIStatusComparison:
        previous, current = self._bound_manifests()
        build_ci_status_snapshot(
            self.bundle, previous, manifest_sha256=self.previous_sha256, source="local-file",
        )
        build_ci_status_snapshot(
            self.bundle, current, manifest_sha256=self.current_sha256, source="local-file",
        )
        return self

    def _bound_manifests(self) -> tuple[CIStatusManifest, CIStatusManifest]:
        previous = _parse_manifest(self.previous_payload)
        current = _parse_manifest(self.current_payload)
        if previous != self.previous_manifest or current != self.current_manifest:
            raise ValueError("CI comparison assertions differ from their supplied input bytes")
        return previous, current

    @property
    def previous_sha256(self) -> str:
        return sha256(self.previous_payload).hexdigest()

    @property
    def current_sha256(self) -> str:
        return sha256(self.current_payload).hexdigest()

    @property
    def previous_snapshot(self) -> CIStatusSnapshot:
        previous, _ = self._bound_manifests()
        return build_ci_status_snapshot(
            self.bundle, previous,
            manifest_sha256=self.previous_sha256, source="local-file",
        )

    @property
    def current_snapshot(self) -> CIStatusSnapshot:
        _, current = self._bound_manifests()
        return build_ci_status_snapshot(
            self.bundle, current,
            manifest_sha256=self.current_sha256, source="local-file",
        )

    def run_changes(self) -> tuple[CIRunComparison, ...]:
        previous_manifest, current_manifest = self._bound_manifests()
        previous = {run.run_id: run for run in previous_manifest.runs}
        current = {run.run_id: run for run in current_manifest.runs}
        return tuple(
            CIRunComparison(
                run_id=run_id, previous=previous.get(run_id), current=current.get(run_id),
                change=_change(previous.get(run_id), current.get(run_id)),
            )
            for run_id in sorted(previous.keys() | current.keys())
        )

    def test_changes(self) -> tuple[CITestComparison, ...]:
        previous_manifest, current_manifest = self._bound_manifests()
        previous, previous_criteria = _tests(self.previous_snapshot)
        current, current_criteria = _tests(self.current_snapshot)
        previous_runs = {run.run_id: run for run in previous_manifest.runs}
        current_runs = {run.run_id: run for run in current_manifest.runs}
        rows = []
        for test_id in sorted(previous.keys() | current.keys()):
            before, after = previous.get(test_id), current.get(test_id)
            change = _change(before, after)
            before_ids = previous_criteria.get(test_id, ())
            after_ids = current_criteria.get(test_id, ())
            if (
                before is not None and after is not None and change == "unchanged"
                and (before_ids != after_ids or (
                    tuple(previous_runs[run_id] for run_id in before.run_ids)
                    != tuple(current_runs[run_id] for run_id in after.run_ids)
                ))
            ):
                change = "changed"
            rows.append(CITestComparison(
                test_id=test_id, change=change,
                previous_criterion_ids=before_ids, current_criterion_ids=after_ids,
                previous=before, current=after,
            ))
        return tuple(rows)


def compare_ci_status(
    bundle: ReviewBundle, previous_payload: bytes, current_payload: bytes,
) -> CIStatusComparison:
    return CIStatusComparison(
        bundle=bundle,
        previous_manifest=_parse_manifest(previous_payload),
        current_manifest=_parse_manifest(current_payload),
        previous_payload=previous_payload, current_payload=current_payload,
    )
