"""Explicit static source references that never alter automatic or human truth."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from hashlib import sha256
from itertools import islice
from urllib.parse import quote

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.retrieval.engine import classify_changed_path_evidence_type
from scopeproof_core.schemas.models import (
    MAX_REFERENCE_LINE_BYTES,
    MAX_REVIEWER_SELECTED_REFERENCES,
    MAX_SELECTABLE_REFERENCE_LINES,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    LineChangeType,
    PullRequestSnapshot,
    RetrievedFile,
    ReviewerSelectedReference,
    ReviewState,
    SelectableReferenceLine,
)

REVIEWER_SELECTED_REFERENCE_BOUNDARY = (
    "Reviewer-selected references are non-gating static context. They do not change automatic "
    "findings, confidence, file scope, reviewer decisions, runtime verification or final "
    "acceptance. "
    "Test/eval definitions show test intent, not execution. The stored excerpt digest establishes "
    "internal consistency, not independent source authenticity."
)

# M3 deliberately retains its conservative raw-patch guard even though automatic
# ingestion now preserves LF boundaries. This repair does not relax selection policy.
_UNSUPPORTED_LINE_SEPARATORS = frozenset("\v\f\x1c\x1d\x1e\x85\u2028\u2029")


def _ambiguous_patch_lines(patch: str) -> bool:
    normalized = patch.replace("\r\n", "\n")
    return "\r" in normalized or bool(_UNSUPPORTED_LINE_SEPARATORS.intersection(normalized))


def _validated_context(
    state: ReviewState, snapshot: PullRequestSnapshot
) -> tuple[ReviewState, PullRequestSnapshot]:
    state = validated_review_state(state)
    if (
        state.bundle is None
        or not state.criteria_revision.confirmed
        or state.review.criteria_source_provenance is None
    ):
        raise ValueError("selected references require a confirmed active analysis")
    snapshot = PullRequestSnapshot.model_validate(snapshot.model_dump(mode="python"))
    if (snapshot.repository, snapshot.pr_number, snapshot.base_sha, snapshot.head_sha) != (
        state.review.repository,
        state.review.pr_number,
        state.review.base_sha,
        state.review.head_sha,
    ):
        raise ValueError(
            "selected reference source must match the active repository, PR, base and head"
        )
    inventory = state.review.changed_file_inventory
    if inventory is None:
        raise ValueError("selected references require a known exact-head changed-file inventory")
    source_inventory = snapshot.scope_inventory()
    expected_files = {(item.path, item.status, item.previous_path) for item in inventory.files}
    observed_files = {
        (item.path, item.status, item.previous_path) for item in source_inventory.files
    }
    if expected_files != observed_files:
        raise ValueError("selected reference source inventory must match the active analysis")
    return state, snapshot


def _line(
    scope: EvidenceSourceScope, path: str, number: int, excerpt: str
) -> SelectableReferenceLine | None:
    kind = classify_changed_path_evidence_type(path)
    try:
        return SelectableReferenceLine(
            source_scope=scope,
            file_path=path,
            line_number=number,
            excerpt=excerpt,
            evidence_type=kind,
            evidence_level=EvidenceLevel.E2 if kind is EvidenceType.TEST else EvidenceLevel.E1,
        )
    except ValidationError:
        # Bounded selectors expose only usable lines, never partial or normalized text.
        return None


MAX_REFERENCE_PAGE_LINES = 100


class _ReferenceSourceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    source_scope: EvidenceSourceScope
    file_path: str

    @field_validator("file_path")
    @classmethod
    def canonical_path(cls, value: str) -> str:
        return SelectableReferenceLine.require_canonical_repository_path(value)


class SelectableReferenceSource(_ReferenceSourceIdentity):
    """Eligible file metadata without retaining every source excerpt in the catalog."""

    eligible_line_count: StrictInt = Field(ge=1)


class _ReferencePageRequest(_ReferenceSourceIdentity):
    page_index: StrictInt = Field(ge=0)


class SelectableReferencePage(BaseModel):
    """One bounded, ordered page of eligible records, retaining physical Git coordinates."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    source: SelectableReferenceSource
    page_index: StrictInt = Field(ge=0)
    lines: tuple[SelectableReferenceLine, ...] = Field(
        min_length=1, max_length=MAX_REFERENCE_PAGE_LINES
    )

    @property
    def page_count(self) -> int:
        return (
            self.source.eligible_line_count + MAX_REFERENCE_PAGE_LINES - 1
        ) // MAX_REFERENCE_PAGE_LINES

    @model_validator(mode="after")
    def validate_page(self) -> SelectableReferencePage:
        start = self.page_index * MAX_REFERENCE_PAGE_LINES
        if start >= self.source.eligible_line_count:
            raise ValueError("reference page is outside the eligible source")
        if len(self.lines) != min(
            MAX_REFERENCE_PAGE_LINES, self.source.eligible_line_count - start
        ):
            raise ValueError("reference page must contain its complete bounded window")
        numbers = []
        for line in self.lines:
            line = SelectableReferenceLine.model_validate(line.model_dump(mode="python"))
            if (line.source_scope, line.file_path) != (
                self.source.source_scope,
                self.source.file_path,
            ):
                raise ValueError("reference page lines must match their source")
            numbers.append(line.line_number)
        if numbers != sorted(set(numbers)):
            raise ValueError("reference page lines must be unique and ordered")
        return self


def _eligible_reference_lines(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    unchanged_files: list[RetrievedFile] | None = None,
    *,
    source: tuple[EvidenceSourceScope, str] | None = None,
) -> Iterator[SelectableReferenceLine]:
    """Apply the same source policy to discovery, pages, legacy views and saves."""
    state, snapshot = _validated_context(state, snapshot)
    unchanged = [
        RetrievedFile.model_validate(item.model_dump(mode="python"))
        for item in unchanged_files or []
    ]
    assert state.review.changed_file_inventory is not None
    blocked_paths = {
        *state.review.skipped_files,
        *snapshot.skipped_files,
        *(item.path for item in snapshot.files),
        *(item.previous_path for item in snapshot.files if item.previous_path is not None),
    }
    for file in sorted(snapshot.files, key=lambda item: item.path):
        if source is not None and source != (EvidenceSourceScope.CHANGED_FILE, file.path):
            continue
        if (
            file.status.casefold() not in {"added", "modified", "renamed", "copied", "changed"}
            or file.truncated
            or file.path in state.review.skipped_files
            or file.path in snapshot.skipped_files
            or _ambiguous_patch_lines(file.patch)
        ):
            continue
        current_lines = [
            line
            for line in file.lines
            if line.change_type in {LineChangeType.ADDED, LineChangeType.CONTEXT}
            and line.line_number is not None
        ]
        numbers = [line.line_number for line in current_lines]
        if len(numbers) != len(set(numbers)):
            continue
        for source_line in sorted(current_lines, key=lambda item: item.line_number):
            assert source_line.line_number is not None
            selected = _line(
                EvidenceSourceScope.CHANGED_FILE,
                file.path,
                source_line.line_number,
                source_line.content,
            )
            if selected is not None:
                yield selected

    unchanged_path_counts = Counter(file.path for file in unchanged)
    for file in sorted(unchanged, key=lambda item: item.path):
        if source is not None and source != (EvidenceSourceScope.UNCHANGED_CANDIDATE, file.path):
            continue
        if (
            file.source_scope is not EvidenceSourceScope.UNCHANGED_CANDIDATE
            or file.commit_sha != state.review.head_sha
            or file.path in blocked_paths
            or unchanged_path_counts[file.path] != 1
        ):
            continue
        source_lines = file.content.split("\n")
        for number, excerpt in enumerate(source_lines, start=1):
            # Strip CR only when it belongs to a CRLF delimiter, never an embedded
            # or final lone CR. Unsupported separator-bearing lines are rejected
            # by the raw-line model without shifting subsequent Git line numbers.
            if number < len(source_lines) and excerpt.endswith("\r"):
                excerpt = excerpt[:-1]
            selected = _line(EvidenceSourceScope.UNCHANGED_CANDIDATE, file.path, number, excerpt)
            if selected is not None:
                yield selected


def selectable_reference_sources(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    unchanged_files: list[RetrievedFile] | None = None,
) -> list[SelectableReferenceSource]:
    """List every eligible already-ingested file, without a global line cutoff."""
    counts = Counter(
        (line.source_scope, line.file_path)
        for line in _eligible_reference_lines(state, snapshot, unchanged_files)
    )
    return [
        SelectableReferenceSource(source_scope=scope, file_path=path, eligible_line_count=count)
        for (scope, path), count in counts.items()
    ]


def selectable_reference_page(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    *,
    source_scope: EvidenceSourceScope,
    file_path: str,
    page_index: int = 0,
    unchanged_files: list[RetrievedFile] | None = None,
) -> SelectableReferencePage:
    """Select one explicit file window; invalid requests never fall back to other source."""
    request = _ReferencePageRequest(
        source_scope=source_scope, file_path=file_path, page_index=page_index
    )
    start = request.page_index * MAX_REFERENCE_PAGE_LINES
    lines = []
    count = 0
    for line in _eligible_reference_lines(
        state, snapshot, unchanged_files, source=(request.source_scope, request.file_path)
    ):
        if start <= count < start + MAX_REFERENCE_PAGE_LINES:
            lines.append(line)
        count += 1
    if not lines:
        raise ValueError("reference source or page is unavailable")
    return SelectableReferencePage(
        source=SelectableReferenceSource(
            source_scope=request.source_scope,
            file_path=request.file_path,
            eligible_line_count=count,
        ),
        page_index=request.page_index,
        lines=tuple(lines),
    )


def selectable_reference_lines(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    unchanged_files: list[RetrievedFile] | None = None,
) -> list[SelectableReferenceLine]:
    """Legacy deterministic global prefix; use file pages to reach later source."""
    return list(
        islice(
            _eligible_reference_lines(state, snapshot, unchanged_files),
            MAX_SELECTABLE_REFERENCE_LINES,
        )
    )


def append_reviewer_selected_reference(
    state: ReviewState,
    *,
    snapshot: PullRequestSnapshot,
    selected: SelectableReferenceLine,
    criterion_id: str,
    reviewer: str,
    rationale: str,
    expected_state_fingerprint: str,
    unchanged_files: list[RetrievedFile] | None = None,
) -> ReviewState:
    """Append source-derived attributable context without changing gate or acceptance truth."""
    state = validated_review_state(state)
    fingerprint = sha256(state.model_dump_json().encode("utf-8")).hexdigest()
    if fingerprint != expected_state_fingerprint:
        raise ValueError("selected reference request is stale; refresh the active review")
    if state.review.final_acceptance:
        raise ValueError("revoke final acceptance before adding selected references")
    selected = SelectableReferenceLine.model_validate(selected.model_dump(mode="python"))
    available = _eligible_reference_lines(
        state, snapshot, unchanged_files, source=(selected.source_scope, selected.file_path)
    )
    source = next((line for line in available if line == selected), None)
    if source is None:
        raise ValueError("selected reference must equal an available exact-head source line")
    assert state.bundle is not None
    if criterion_id not in {item.criterion_id for item in state.bundle.criteria}:
        raise ValueError("selected reference must map to an active confirmed criterion")
    if len(state.bundle.reviewer_selected_references) >= MAX_REVIEWER_SELECTED_REFERENCES:
        raise ValueError(
            f"analysis may contain at most {MAX_REVIEWER_SELECTED_REFERENCES} references"
        )
    if any(
        (item.criterion_id, item.source_scope, item.file_path, item.line_number)
        == (criterion_id, source.source_scope, source.file_path, source.line_number)
        for item in state.bundle.reviewer_selected_references
    ):
        raise ValueError("selected reference already exists for this criterion and source location")
    assert state.review.criteria_source_provenance is not None
    reference = ReviewerSelectedReference(
        **source.model_dump(mode="python"),
        review_id=state.review.review_id,
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criteria_revision_number=state.criteria_revision.number,
        confirmed_criteria_sha256=(
            state.review.criteria_source_provenance.normalized_criteria_sha256
        ),
        criteria_source_provenance=state.review.criteria_source_provenance,
        criterion_id=criterion_id,
        excerpt_sha256=sha256(source.excerpt.encode("utf-8")).hexdigest(),
        permalink=(
            f"https://github.com/{quote(state.review.repository, safe='/')}/blob/"
            f"{quote(state.review.head_sha, safe='')}/{quote(source.file_path, safe='/')}"
            f"#L{source.line_number}-L{source.line_number}"
        ),
        reviewer=reviewer,
        rationale=rationale,
    )
    bundle = state.bundle.model_copy(deep=True)
    bundle.reviewer_selected_references.append(reference)
    return validated_review_state(state.model_copy(update={"bundle": bundle}))


__all__ = [
    "MAX_REFERENCE_LINE_BYTES",
    "MAX_REFERENCE_PAGE_LINES",
    "MAX_REVIEWER_SELECTED_REFERENCES",
    "MAX_SELECTABLE_REFERENCE_LINES",
    "REVIEWER_SELECTED_REFERENCE_BOUNDARY",
    "ReviewerSelectedReference",
    "SelectableReferenceLine",
    "SelectableReferencePage",
    "SelectableReferenceSource",
    "append_reviewer_selected_reference",
    "selectable_reference_lines",
    "selectable_reference_page",
    "selectable_reference_sources",
]
