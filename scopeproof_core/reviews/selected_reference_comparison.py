"""Informational full-record context, independent of automatic evidence matching."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, computed_field, model_validator

from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    MAX_REVIEWER_SELECTED_REFERENCES,
    CriteriaSourceProvenance,
    ReviewBundle,
    ReviewerSelectedReference,
)

SELECTED_REFERENCE_COMPARISON_BOUNDARY = (
    "Recorded reviewer-selected references are non-gating static context. "
    "Full-record identity does not establish cross-head equivalence, source authenticity, "
    "criterion satisfaction, execution, or acceptance. Test/eval definitions are intent, "
    "not execution. No prior decision is carried forward."
)


def _record_identity(reference: ReviewerSelectedReference) -> str:
    return json.dumps(reference.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _sort_key(reference: ReviewerSelectedReference) -> tuple:
    return (
        reference.criterion_id,
        reference.file_path,
        reference.line_number,
        reference.reference_id,
        _record_identity(reference),
    )


class SelectedReferenceRecordChange(BaseModel):
    """A derived record-presence distinction, never semantic source matching."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["identical_record", "only_previous", "only_current"]
    previous: ReviewerSelectedReference | None = None
    current: ReviewerSelectedReference | None = None

    @model_validator(mode="after")
    def _record_presence_matches_kind(self) -> SelectedReferenceRecordChange:
        if self.kind == "identical_record":
            if (
                self.previous is None
                or self.current is None
                or _record_identity(self.previous) != _record_identity(self.current)
            ):
                raise ValueError("identical records require two complete matching references")
        elif self.kind == "only_previous":
            if self.previous is None or self.current is not None:
                raise ValueError("only_previous requires only a previous reference")
        elif self.current is None or self.previous is not None:
            raise ValueError("only_current requires only a current reference")
        return self


class SelectedReferenceChangeCounts(BaseModel):
    identical_record: int = Field(ge=0)
    only_previous: int = Field(ge=0)
    only_current: int = Field(ge=0)


class SelectedReferenceComparison(BaseModel):
    """Canonical recorded snapshots; derived deltas cannot supply gate evidence."""

    model_config = ConfigDict(extra="forbid")

    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    previous_criteria_source_provenance: CriteriaSourceProvenance
    current_criteria_source_provenance: CriteriaSourceProvenance
    previous: list[ReviewerSelectedReference] = Field(max_length=MAX_REVIEWER_SELECTED_REFERENCES)
    current: list[ReviewerSelectedReference] = Field(max_length=MAX_REVIEWER_SELECTED_REFERENCES)

    @model_validator(mode="before")
    @classmethod
    def _discard_derived_values(cls, value: object) -> object:
        if isinstance(value, dict):
            return {
                key: item
                for key, item in value.items()
                if key not in {"record_changes", "change_counts"}
            }
        return value

    @model_validator(mode="after")
    def _canonical_owned_records(self) -> SelectedReferenceComparison:
        source_identities: set[tuple] = set()
        for side in ("previous", "current"):
            references = getattr(self, side)
            owner_provenance = getattr(self, f"{side}_criteria_source_provenance")
            source_identities.add(
                (
                    owner_provenance.source_uri,
                    owner_provenance.source_revision,
                    owner_provenance.source_text_sha256,
                    owner_provenance.normalized_criteria_sha256,
                )
            )
            ids = [item.reference_id for item in references]
            locations = [
                (item.criterion_id, item.source_scope, item.file_path, item.line_number)
                for item in references
            ]
            if len(ids) != len(set(ids)) or len(locations) != len(set(locations)):
                raise ValueError("selected comparison records require unique IDs and locations")
            for item in references:
                if (item.repository, item.pr_number) != (self.repository, self.pr_number):
                    raise ValueError("selected comparison references must match repository and PR")
                if item.criteria_source_provenance != owner_provenance:
                    raise ValueError("selected comparison reference must match owning provenance")
                provenance = item.criteria_source_provenance
                source_identities.add(
                    (
                        provenance.source_uri,
                        provenance.source_revision,
                        provenance.source_text_sha256,
                        provenance.normalized_criteria_sha256,
                    )
                )
            references.sort(key=_sort_key)
        if len(source_identities) > 1:
            raise ValueError("selected comparison requires compatible criteria-source identity")
        return self

    @computed_field
    @property
    def record_changes(self) -> list[SelectedReferenceRecordChange]:
        previous = {_record_identity(item): item for item in self.previous}
        current = {_record_identity(item): item for item in self.current}
        changes = []
        for identity in sorted(set(previous) | set(current)):
            old, new = previous.get(identity), current.get(identity)
            kind = (
                "identical_record"
                if old is not None and new is not None
                else "only_previous"
                if old is not None
                else "only_current"
            )
            changes.append(SelectedReferenceRecordChange(kind=kind, previous=old, current=new))
        return changes

    @computed_field
    @property
    def change_counts(self) -> SelectedReferenceChangeCounts:
        changes = self.record_changes
        return SelectedReferenceChangeCounts(
            **{
                kind: sum(change.kind == kind for change in changes)
                for kind in ("identical_record", "only_previous", "only_current")
            }
        )

    @classmethod
    def from_bundles(
        cls,
        previous: ReviewBundle,
        current: ReviewBundle,
    ) -> SelectedReferenceComparison:
        # Local import keeps the comparison's single relationship validator authoritative.
        from scopeproof_core.reviews.comparison import validate_comparison_relationship

        previous, current = validate_comparison_relationship(previous, current)
        return cls(
            repository=current.review.repository,
            pr_number=current.review.pr_number,
            previous_criteria_source_provenance=(
                previous.review.criteria_source_provenance.model_copy(deep=True)
            ),
            current_criteria_source_provenance=(
                current.review.criteria_source_provenance.model_copy(deep=True)
            ),
            previous=[item.model_copy(deep=True) for item in previous.reviewer_selected_references],
            current=[item.model_copy(deep=True) for item in current.reviewer_selected_references],
        )
