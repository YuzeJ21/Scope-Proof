"""Typed, informational changed-file scope facts for a re-review comparison."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, computed_field, model_validator

from scopeproof_core.schemas.models import (
    ChangedFileInventory,
    ChangedFileScope,
    FileScopeDecision,
    IngestionState,
    ReviewBundle,
)


class FileScopeSnapshot(BaseModel):
    """One head's inspected scope; no acceptance or content-equality claim."""

    model_config = ConfigDict(extra="forbid")

    review_id: str
    head_sha: str
    criteria_revision_number: Annotated[StrictInt, Field(gt=0)] | Literal["unknown"]
    normalized_criteria_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None
    criterion_ids: list[str]
    finding_evidence_ids: dict[str, list[str]]
    inventory: ChangedFileInventory | None
    cited_paths: list[str]
    latest_decisions: list[FileScopeDecision]
    ingestion_state: IngestionState
    skipped_files: list[str]
    ingestion_warnings: list[str]

    @model_validator(mode="before")
    @classmethod
    def _discard_derived_fields(cls, value: object) -> object:
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key != "unresolved_paths"}
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> FileScopeSnapshot:
        if not self.head_sha.strip() or not self.review_id.strip():
            raise ValueError("scope snapshot requires nonblank review and head identity")
        if self.criterion_ids != sorted(set(self.criterion_ids)) or any(
            not item.strip() for item in self.criterion_ids
        ):
            raise ValueError("scope criterion IDs must be canonical")
        if set(self.finding_evidence_ids) != set(self.criterion_ids) or any(
            values != sorted(set(values)) for values in self.finding_evidence_ids.values()
        ):
            raise ValueError("scope finding links must match the confirmed criteria")
        if self.ingestion_state is IngestionState.COMPLETE and (
            self.skipped_files or self.ingestion_warnings
        ):
            raise ValueError("complete scope ingestion cannot include limitations")
        if self.inventory is not None and self.inventory.head_sha != self.head_sha:
            raise ValueError("scope inventory must match snapshot head")
        paths = {item.path for item in self.inventory.files} if self.inventory else set()
        if self.cited_paths != sorted(set(self.cited_paths)) or not set(self.cited_paths) <= paths:
            raise ValueError("cited scope paths must be canonical inspected paths")
        decision_paths = [item.path for item in self.latest_decisions]
        if decision_paths != sorted(set(decision_paths)):
            raise ValueError("latest scope decisions must use canonical unique paths")
        for decision in self.latest_decisions:
            if (
                decision.review_id != self.review_id
                or decision.head_sha != self.head_sha
                or decision.criteria_revision_number != self.criteria_revision_number
                or decision.normalized_criteria_sha256 != self.normalized_criteria_sha256
                or decision.path not in paths
                or (
                    decision.criterion_id is not None
                    and decision.criterion_id not in self.criterion_ids
                )
            ):
                raise ValueError("scope decision must match its owning snapshot identity")
        return self

    @computed_field
    @property
    def unresolved_paths(self) -> list[str] | None:
        """Mirror scope gate rules using only the retained exact-head facts."""
        if self.inventory is None:
            return None
        outside = {
            item.path for item in self.latest_decisions
            if item.disposition == "outside_confirmed_criteria"
        }
        return sorted(
            {item.path for item in self.inventory.files} - set(self.cited_paths) - outside
        )

    @classmethod
    def from_bundle(cls, bundle: ReviewBundle) -> FileScopeSnapshot:
        """Project an already validated bundle; copies detach mutable source objects."""
        review = bundle.review
        inventory = review.changed_file_inventory
        linked = {item for finding in bundle.findings for item in finding.evidence_ids}
        paths = {item.path for item in inventory.files} if inventory else set()
        cited = {
            item.file_path for item in bundle.evidence
            if item.source_scope.value == "changed_file"
            and item.commit_sha == review.head_sha and item.evidence_id in linked
            and item.file_path in paths
        }
        latest = {item.path: item for item in bundle.file_scope_decisions}
        provenance = review.criteria_source_provenance
        copied_inventory = inventory.model_copy(deep=True) if inventory is not None else None
        if copied_inventory is not None:
            copied_inventory.files.sort(key=lambda item: item.path)
        return cls(
            review_id=review.review_id, head_sha=review.head_sha,
            criteria_revision_number=bundle.criteria_revision_number,
            normalized_criteria_sha256=(
                provenance.normalized_criteria_sha256 if provenance else None
            ),
            criterion_ids=sorted(item.criterion_id for item in bundle.criteria),
            finding_evidence_ids={
                item.criterion_id: sorted(set(item.evidence_ids)) for item in bundle.findings
            },
            inventory=copied_inventory,
            cited_paths=sorted(cited),
            latest_decisions=[latest[path].model_copy(deep=True) for path in sorted(latest)],
            ingestion_state=review.ingestion_state,
            skipped_files=sorted(set(review.skipped_files)),
            ingestion_warnings=list(review.ingestion_warnings),
        )


class FileInventoryChange(BaseModel):
    """A difference in recorded inventory metadata, never a file-content comparison."""

    model_config = ConfigDict(extra="forbid")

    path: str
    kind: Literal["added_to_inventory", "absent_from_current_inventory", "metadata_changed"]
    previous: ChangedFileScope | None
    current: ChangedFileScope | None


class FileScopeComparison(BaseModel):
    """Both immutable-head projections and deterministic, informational differences."""

    model_config = ConfigDict(extra="forbid")

    previous: FileScopeSnapshot
    current: FileScopeSnapshot

    @model_validator(mode="after")
    def _criteria_identity_matches(self) -> FileScopeComparison:
        if (
            self.previous.normalized_criteria_sha256 != self.current.normalized_criteria_sha256
            or self.previous.criterion_ids != self.current.criterion_ids
        ):
            raise ValueError("scope snapshots require matching confirmed criteria identity")
        return self

    @model_validator(mode="before")
    @classmethod
    def _discard_derived_fields(cls, value: object) -> object:
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key not in {
                "inventory_changes", "previously_decided_paths_now_unresolved",
            }}
        return value

    @computed_field
    @property
    def inventory_changes(self) -> list[FileInventoryChange] | None:
        if self.previous.inventory is None or self.current.inventory is None:
            return None
        previous = {item.path: item for item in self.previous.inventory.files}
        current = {item.path: item for item in self.current.inventory.files}
        changes = []
        for path in sorted(previous.keys() | current.keys()):
            before, after = previous.get(path), current.get(path)
            if before == after:
                continue
            kind = (
                "added_to_inventory" if before is None else
                "absent_from_current_inventory" if after is None else "metadata_changed"
            )
            changes.append(FileInventoryChange(
                path=path, kind=kind, previous=before, current=after,
            ))
        return changes

    @computed_field
    @property
    def previously_decided_paths_now_unresolved(self) -> list[str] | None:
        unresolved = self.current.unresolved_paths
        if unresolved is None:
            return None
        return sorted({item.path for item in self.previous.latest_decisions} & set(unresolved))
