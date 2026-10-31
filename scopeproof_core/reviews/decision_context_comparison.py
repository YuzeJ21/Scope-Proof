"""Recorded criterion decisions and observations, never new gate evidence."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, computed_field, model_validator

from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    CriteriaSourceProvenance,
    HumanDecision,
    HumanResolution,
    ReviewBundle,
    ReviewInputOrigin,
    RuntimeEvidence,
)

DECISION_CONTEXT_COMPARISON_BOUNDARY = (
    "Recorded latest criterion decisions and retained runtime observations are informational "
    "comparison context. Reviewers and results are asserted; ScopeProof did not execute, fetch, "
    "authenticate or re-verify these observations. Record equality does not establish cross-head "
    "equivalence or acceptance. Only an explicit runtime ID links a decision to an observation; "
    "legacy unlinked records remain unlinked. No decision is carried forward; gates are unchanged."
)


def _identity(record: BaseModel) -> str:
    return json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _complete_record(value: object, model: type[BaseModel]) -> dict:
    """Projection records must supply recorded facts rather than model defaults."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if not isinstance(value, dict) or set(value) != set(model.model_fields):
        raise ValueError("comparison context requires complete explicit recorded fields")
    return value


def _complete_records(value: object) -> object:
    if isinstance(value, dict):
        value = dict(value)
        if isinstance(value.get("resolutions"), list):
            value["resolutions"] = [
                _complete_record(item, HumanResolution) for item in value["resolutions"]
            ]
        if value.get("resolution") is not None:
            value["resolution"] = _complete_record(value["resolution"], HumanResolution)
        if isinstance(value.get("runtime_evidence"), list):
            value["runtime_evidence"] = [
                _complete_record(item, RuntimeEvidence) for item in value["runtime_evidence"]
            ]
    return value


def _require_runtime_link(resolution: HumanResolution, observations: list[RuntimeEvidence]) -> None:
    if resolution.runtime_evidence_id is None:
        return
    matches = [
        item for item in observations
        if item.runtime_evidence_id == resolution.runtime_evidence_id
    ]
    if len(matches) != 1 or (
        matches[0].criterion_id, matches[0].reviewer, matches[0].evidence_level
    ) != (resolution.criterion_id, resolution.reviewer, resolution.claimed_evidence_level):
        raise ValueError("recorded decision requires its exact criterion, reviewer and level link")


def _provenance_identity(value: CriteriaSourceProvenance) -> tuple:
    return (
        value.source_uri, value.source_revision, value.source_text_sha256,
        value.normalized_criteria_sha256,
    )


class DecisionContextSnapshot(BaseModel):
    """One validated analysis's latest resolutions and retained observations."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    review_id: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    criteria_revision_number: StrictInt | Literal["unknown"]
    input_origin: ReviewInputOrigin
    criteria_source_provenance: CriteriaSourceProvenance
    criterion_ids: list[str]
    resolutions: list[HumanResolution]
    runtime_evidence: list[RuntimeEvidence]

    @model_validator(mode="before")
    @classmethod
    def _explicit_records(cls, value: object) -> object:
        return _complete_records(value)

    @model_validator(mode="after")
    def _owned_records(self) -> DecisionContextSnapshot:
        if not self.review_id.strip() or not self.head_sha.strip():
            raise ValueError("decision context requires nonblank owning identity")
        if isinstance(self.criteria_revision_number, int) and self.criteria_revision_number <= 0:
            raise ValueError("decision context requires a positive revision or unknown")
        if self.criterion_ids != sorted(set(self.criterion_ids)) or any(
            not item.strip() for item in self.criterion_ids
        ):
            raise ValueError("decision context criterion IDs must be canonical")
        resolution_ids = [item.criterion_id for item in self.resolutions]
        if len(resolution_ids) != len(set(resolution_ids)):
            raise ValueError("decision context requires unique criterion resolutions")
        runtime_ids = [
            item.runtime_evidence_id for item in self.runtime_evidence
            if item.runtime_evidence_id is not None
        ]
        if len(runtime_ids) != len(set(runtime_ids)):
            raise ValueError("decision context requires unique runtime IDs")
        if any(
            item.criterion_id not in self.criterion_ids
            for item in [*self.resolutions, *self.runtime_evidence]
        ):
            raise ValueError("decision context records must use known criteria")
        for item in self.runtime_evidence:
            if item.runtime_evidence_id is None:
                if self.input_origin is ReviewInputOrigin.LIVE_PUBLIC_GITHUB:
                    raise ValueError("live runtime context requires exact owning identity")
            elif (item.repository, item.pr_number, item.head_sha) != (
                self.repository, self.pr_number, self.head_sha
            ):
                raise ValueError("runtime context must match its owning review")
        for resolution in self.resolutions:
            _require_runtime_link(resolution, self.runtime_evidence)
        self.resolutions.sort(key=lambda item: item.criterion_id)
        self.runtime_evidence.sort(key=_identity)
        return self

    @classmethod
    def from_bundle(cls, bundle: ReviewBundle) -> DecisionContextSnapshot:
        return cls(
            repository=bundle.review.repository, pr_number=bundle.review.pr_number,
            review_id=bundle.review.review_id, head_sha=bundle.review.head_sha,
            criteria_revision_number=bundle.criteria_revision_number,
            input_origin=bundle.review.input_origin,
            criteria_source_provenance=bundle.review.criteria_source_provenance.model_copy(deep=True),
            criterion_ids=sorted(item.criterion_id for item in bundle.criteria),
            resolutions=[item.model_copy(deep=True) for item in bundle.resolutions],
            runtime_evidence=[item.model_copy(deep=True) for item in bundle.runtime_evidence],
        )


class CriterionDecisionContext(BaseModel):
    """Retained observations share a criterion; only an explicit ID supplies a link."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    criterion_id: str = Field(min_length=1)
    resolution: HumanResolution | None
    runtime_evidence: list[RuntimeEvidence]

    @model_validator(mode="before")
    @classmethod
    def _explicit_records(cls, value: object) -> object:
        if isinstance(value, dict):
            value = {key: item for key, item in value.items() if key != "runtime_link_status"}
        return _complete_records(value)

    @model_validator(mode="after")
    def _criterion_records(self) -> CriterionDecisionContext:
        if self.resolution is None and not self.runtime_evidence:
            raise ValueError("a decision context row requires recorded content")
        if any(item.criterion_id != self.criterion_id for item in self.runtime_evidence) or (
            self.resolution is not None and self.resolution.criterion_id != self.criterion_id
        ):
            raise ValueError("decision context row records must share the criterion")
        if self.resolution is not None:
            _require_runtime_link(self.resolution, self.runtime_evidence)
        self.runtime_evidence.sort(key=_identity)
        return self

    @computed_field
    @property
    def runtime_link_status(self) -> Literal["linked", "legacy_unlinked", "no_link"]:
        if self.resolution is not None:
            if self.resolution.runtime_evidence_id is not None:
                return "linked"
            if self.resolution.decision is HumanDecision.MANUALLY_VERIFIED:
                return "legacy_unlinked"
        return "no_link"


class DecisionContextRecordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    kind: Literal[
        "identical_recorded_context", "only_previous", "only_current", "recorded_context_changed"
    ]
    previous: CriterionDecisionContext | None
    current: CriterionDecisionContext | None

    @model_validator(mode="after")
    def _record_presence(self) -> DecisionContextRecordChange:
        expected = (
            "only_current" if self.previous is None else
            "only_previous" if self.current is None else
            "identical_recorded_context" if _identity(self.previous) == _identity(self.current) else
            "recorded_context_changed"
        )
        if (self.previous is None and self.current is None) or self.kind != expected or any(
            item.criterion_id != self.criterion_id
            for item in (self.previous, self.current) if item is not None
        ):
            raise ValueError("decision context change must match its complete recorded rows")
        return self


class DecisionContextComparison(BaseModel):
    """Informational context; derived distinctions never modify gate decisions."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    previous: DecisionContextSnapshot
    current: DecisionContextSnapshot

    @model_validator(mode="before")
    @classmethod
    def _discard_derived(cls, value: object) -> object:
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key != "record_changes"}
        return value

    @model_validator(mode="after")
    def _compatible_owners(self) -> DecisionContextComparison:
        for snapshot in (self.previous, self.current):
            if (snapshot.repository, snapshot.pr_number) != (self.repository, self.pr_number):
                raise ValueError("decision context must match repository and pull request")
        if self.previous.criterion_ids != self.current.criterion_ids or _provenance_identity(
            self.previous.criteria_source_provenance
        ) != _provenance_identity(self.current.criteria_source_provenance):
            raise ValueError("decision context requires compatible confirmed criteria identity")
        return self

    @staticmethod
    def _rows(snapshot: DecisionContextSnapshot) -> dict[str, CriterionDecisionContext]:
        resolutions = {item.criterion_id: item for item in snapshot.resolutions}
        return {
            criterion_id: CriterionDecisionContext(
                criterion_id=criterion_id,
                resolution=resolutions.get(criterion_id),
                runtime_evidence=[
                    item for item in snapshot.runtime_evidence if item.criterion_id == criterion_id
                ],
            )
            for criterion_id in sorted(
                resolutions.keys() | {item.criterion_id for item in snapshot.runtime_evidence}
            )
        }

    @computed_field
    @property
    def record_changes(self) -> list[DecisionContextRecordChange]:
        previous, current = self._rows(self.previous), self._rows(self.current)
        return [
            DecisionContextRecordChange(
                criterion_id=criterion_id, previous=previous.get(criterion_id),
                current=current.get(criterion_id),
                kind=(
                    "only_current" if criterion_id not in previous else
                    "only_previous" if criterion_id not in current else
                    "identical_recorded_context"
                    if _identity(previous[criterion_id]) == _identity(current[criterion_id]) else
                    "recorded_context_changed"
                ),
            )
            for criterion_id in sorted(previous.keys() | current.keys())
        ]

    @classmethod
    def from_bundles(
        cls, previous: ReviewBundle, current: ReviewBundle,
    ) -> DecisionContextComparison:
        from scopeproof_core.reviews.comparison import validate_comparison_relationship

        previous, current = validate_comparison_relationship(previous, current)
        return cls(
            repository=current.review.repository, pr_number=current.review.pr_number,
            previous=DecisionContextSnapshot.from_bundle(previous),
            current=DecisionContextSnapshot.from_bundle(current),
        )
