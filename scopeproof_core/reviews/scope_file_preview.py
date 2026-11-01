"""Bounded, read-only loaded diff context before an explicit file-scope decision."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    computed_field,
    model_validator,
)

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import (
    MAX_REFERENCE_LINE_BYTES,
    LineChangeType,
    PullRequestSnapshot,
    ReviewState,
    SelectableReferenceLine,
)

MAX_SCOPE_PREVIEW_LINES = 100


class _PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: StrictStr
    page_index: Annotated[StrictInt, Field(ge=0)]


class ScopePreviewLine(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    change_type: LineChangeType
    line_number: Annotated[StrictInt, Field(gt=0)] | None
    content: StrictStr | None

    @model_validator(mode="after")
    def _bounded_record(self) -> ScopePreviewLine:
        if self.content is not None and (
            "\n" in self.content or len(self.content.encode("utf-8")) > MAX_REFERENCE_LINE_BYTES
        ):
            raise ValueError("preview content must be one bounded diff record")
        return self


class ScopeFilePreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    review_id: StrictStr
    repository: StrictStr
    pr_number: Annotated[StrictInt, Field(gt=0)]
    base_sha: StrictStr
    head_sha: StrictStr
    path: StrictStr
    status: StrictStr
    previous_path: StrictStr | None
    page_index: Annotated[StrictInt, Field(ge=0)]
    total_line_count: Annotated[StrictInt, Field(ge=0)]
    availability: Literal[
        "available", "skipped", "truncated", "unsupported_status",
        "ambiguous_coordinates", "no_lines",
    ]
    lines: tuple[ScopePreviewLine, ...] = Field(max_length=MAX_SCOPE_PREVIEW_LINES)

    @computed_field
    @property
    def page_count(self) -> int:
        if self.availability != "available":
            return 0
        return (self.total_line_count + MAX_SCOPE_PREVIEW_LINES - 1) // MAX_SCOPE_PREVIEW_LINES

    @model_validator(mode="before")
    @classmethod
    def _discard_computed(cls, value: object) -> object:
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key != "page_count"}
        return value

    @model_validator(mode="after")
    def _complete_window(self) -> ScopeFilePreview:
        SelectableReferenceLine.require_canonical_repository_path(self.path)
        if self.previous_path is not None:
            SelectableReferenceLine.require_canonical_repository_path(self.previous_path)
        if self.availability == "available":
            start = self.page_index * MAX_SCOPE_PREVIEW_LINES
            if start >= self.total_line_count or len(self.lines) != min(
                MAX_SCOPE_PREVIEW_LINES, self.total_line_count - start
            ):
                raise ValueError("preview must contain its complete bounded diff window")
        elif self.lines or self.page_index != 0:
            raise ValueError("unavailable preview must not expose source records or pages")
        return self


def build_scope_file_preview(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    path: str,
    *,
    page_index: int = 0,
) -> ScopeFilePreview:
    """Project loaded observations, never fetching source or changing saved review truth."""
    request = _PreviewRequest(path=path, page_index=page_index)
    SelectableReferenceLine.require_canonical_repository_path(request.path)
    state = validated_review_state(state)
    snapshot = PullRequestSnapshot.model_validate(snapshot.model_dump(mode="python"))
    review = state.review
    if (
        state.bundle is None or not state.criteria_revision.confirmed
        or review.criteria_source_provenance is None
        or review.changed_file_inventory is None
    ):
        raise ValueError("diff inspection requires a confirmed active analysis and known inventory")
    expected = (
        review.repository, review.pr_number, review.base_sha, review.head_sha,
        review.repository_visibility, review.ingestion_state, review.check_state,
        review.ci_observation.model_dump(mode="python"),
        review.skipped_files, review.ingestion_warnings,
    )
    observed = (
        snapshot.repository, snapshot.pr_number, snapshot.base_sha, snapshot.head_sha,
        snapshot.repository_visibility, snapshot.ingestion_state, snapshot.check_state,
        snapshot.ci_observation.model_dump(mode="python"),
        snapshot.skipped_files, snapshot.warnings,
    )
    if expected != observed:
        raise ValueError("loaded diff source does not match the active review observations")
    inventory = snapshot.scope_inventory()
    def key(item):
        return item.path, item.status, item.previous_path

    if sorted(map(key, inventory.files)) != sorted(map(key, review.changed_file_inventory.files)):
        raise ValueError("loaded diff inventory does not match the active analysis")
    file = next((item for item in snapshot.files if item.path == request.path), None)
    if file is None:
        raise ValueError("selected changed file is unavailable")
    availability = "available"
    if file.path in snapshot.skipped_files:
        availability = "skipped"
    elif file.truncated:
        availability = "truncated"
    elif file.status.casefold() not in {
        "added", "modified", "changed", "renamed", "copied", "removed",
    }:
        availability = "unsupported_status"
    elif not file.lines:
        availability = "no_lines"
    else:
        coordinates: set[tuple[bool, int]] = set()
        for line in file.lines:
            coordinate = (line.change_type is LineChangeType.REMOVED, line.line_number)
            if "\n" in line.content or (
                line.line_number is not None and coordinate in coordinates
            ):
                availability = "ambiguous_coordinates"
                break
            if line.line_number is not None:
                coordinates.add(coordinate)
    start = request.page_index * MAX_SCOPE_PREVIEW_LINES
    window = (
        file.lines[start:start + MAX_SCOPE_PREVIEW_LINES] if availability == "available" else []
    )
    lines = tuple(ScopePreviewLine(
        change_type=line.change_type, line_number=line.line_number,
        content=(line.content if len(line.content.encode("utf-8")) <= MAX_REFERENCE_LINE_BYTES
                 else None),
    ) for line in window)
    return ScopeFilePreview(
        review_id=review.review_id, repository=review.repository, pr_number=review.pr_number,
        base_sha=review.base_sha, head_sha=review.head_sha, path=file.path,
        status=file.status, previous_path=file.previous_path, page_index=request.page_index,
        total_line_count=len(file.lines), availability=availability, lines=lines,
    )
