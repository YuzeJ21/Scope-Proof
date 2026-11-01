"""Recorded acceptance flags, separate from gate outcomes and unavailable event history."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    computed_field,
    model_validator,
)

from scopeproof_core.gates.validation import validated_review_bundle
from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    ReviewBundle,
    ReviewInputOrigin,
)

FINAL_ACCEPTANCE_COMPARISON_BOUNDARY = (
    "Recorded local final-acceptance flags are informational, asserted and unauthenticated; "
    "they are not correctness or runtime verification. Actor, timestamp, rationale and event "
    "association are unavailable in analysis snapshots. False does not establish revocation "
    "or that acceptance never happened. No acceptance or decision is carried forward."
)


class FinalAcceptanceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    repository: StrictStr = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: Annotated[StrictInt, Field(gt=0)]
    review_id: StrictStr = Field(min_length=1)
    head_sha: StrictStr = Field(min_length=1)
    criteria_revision_number: Annotated[StrictInt, Field(gt=0)] | Literal["unknown"]
    input_origin: ReviewInputOrigin
    normalized_criteria_sha256: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    criterion_ids: tuple[StrictStr, ...]
    recorded_final_acceptance: StrictBool
    event_context_status: Literal["unavailable_in_analysis_snapshot"]

    @model_validator(mode="after")
    def _canonical_identity(self) -> FinalAcceptanceSnapshot:
        if not self.review_id.strip() or not self.head_sha.strip():
            raise ValueError("final-acceptance snapshot requires nonblank owning identities")
        if self.criterion_ids != tuple(sorted(set(self.criterion_ids))) or any(
            not item.strip() for item in self.criterion_ids
        ):
            raise ValueError("final-acceptance criterion IDs must be canonical")
        return self

    @classmethod
    def from_bundle(cls, bundle: ReviewBundle) -> FinalAcceptanceSnapshot:
        bundle = validated_review_bundle(bundle)
        provenance = bundle.review.criteria_source_provenance
        if provenance is None:
            raise ValueError("final-acceptance comparison requires recorded criteria provenance")
        return cls(
            repository=bundle.review.repository, pr_number=bundle.review.pr_number,
            review_id=bundle.review.review_id, head_sha=bundle.review.head_sha,
            criteria_revision_number=bundle.criteria_revision_number,
            input_origin=bundle.review.input_origin,
            normalized_criteria_sha256=provenance.normalized_criteria_sha256,
            criterion_ids=tuple(sorted(item.criterion_id for item in bundle.criteria)),
            recorded_final_acceptance=bundle.review.final_acceptance,
            event_context_status="unavailable_in_analysis_snapshot",
        )


class FinalAcceptanceComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    context_kind: Literal["scopeproof_recorded_final_acceptance_comparison"]
    schema_version: Annotated[StrictInt, Field(ge=1, le=1)]
    boundary: Literal[FINAL_ACCEPTANCE_COMPARISON_BOUNDARY]
    previous: FinalAcceptanceSnapshot
    current: FinalAcceptanceSnapshot

    @model_validator(mode="before")
    @classmethod
    def _discard_derived(cls, value: object) -> object:
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key != "recorded_value_changed"}
        return value

    @model_validator(mode="after")
    def _shared_criteria(self) -> FinalAcceptanceComparison:
        if (
            self.previous.repository, self.previous.pr_number,
            self.previous.normalized_criteria_sha256, self.previous.criterion_ids,
        ) != (
            self.current.repository, self.current.pr_number,
            self.current.normalized_criteria_sha256, self.current.criterion_ids,
        ):
            raise ValueError("final-acceptance sides require the same repository/PR and criteria")
        return self

    @computed_field
    @property
    def recorded_value_changed(self) -> bool:
        return self.previous.recorded_final_acceptance != self.current.recorded_final_acceptance

    @classmethod
    def from_bundles(
        cls, previous: ReviewBundle, current: ReviewBundle,
    ) -> FinalAcceptanceComparison:
        return cls(
            context_kind="scopeproof_recorded_final_acceptance_comparison", schema_version=1,
            boundary=FINAL_ACCEPTANCE_COMPARISON_BOUNDARY,
            previous=FinalAcceptanceSnapshot.from_bundle(previous),
            current=FinalAcceptanceSnapshot.from_bundle(current),
        )
