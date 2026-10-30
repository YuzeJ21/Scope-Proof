"""Read-only source continuation for an already confirmed, saved analysis."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.reference_audit import active_references
from scopeproof_core.reviews.selected_references import _eligible_reference_lines
from scopeproof_core.schemas.models import (
    EvidenceSourceScope,
    IngestionState,
    LocalReviewId,
    PullRequestSnapshot,
    RetrievedFile,
    ReviewInputOrigin,
    ReviewState,
    SelectableReferenceLine,
    require_verified_public_origin,
)
from scopeproof_core.storage.json_store import JsonReviewStore

MAX_ATTACHED_CANDIDATE_FILES = 8
MAX_ATTACHED_CANDIDATE_BYTES = 200_000
Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SourceAttachmentUnavailable(ValueError):
    """Reject continuation without changing saved truth or inventing observations."""

    def __init__(self, message: str, *, observed_conflict: bool = False) -> None:
        super().__init__(message)
        self.observed_conflict = observed_conflict


class ReviewSourceAttachment(BaseModel):
    """Session-only receipt; hashes establish consistency, not source authenticity."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    review_id: LocalReviewId
    saved_state_fingerprint: Fingerprint
    context_fingerprint: Fingerprint
    source_fingerprint: Fingerprint
    source_origin: ReviewInputOrigin
    snapshot: PullRequestSnapshot
    candidate_files: tuple[RetrievedFile, ...] = Field(max_length=MAX_ATTACHED_CANDIDATE_FILES)


def _hash(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _validated_state(state: ReviewState) -> ReviewState:
    try:
        return validated_review_state(state)
    except ValueError as error:
        raise SourceAttachmentUnavailable("Saved review could not be revalidated.") from error


def review_source_context_fingerprint(state: ReviewState) -> str:
    """Bind immutable analysis/source identity while allowing explicit neutral appends."""
    state = _validated_state(state)
    return _hash(
        {
            "review": state.review.model_dump(mode="json", exclude={"final_acceptance"}),
            "criteria_revision": state.criteria_revision.model_dump(mode="json"),
        }
    )


def _attachable_state(state: ReviewState) -> ReviewState:
    state = _validated_state(state)
    review = state.review
    if (
        state.bundle is None
        or not state.criteria_revision.confirmed
        or not review.criteria_confirmed
        or review.criteria_source_provenance is None
        or review.changed_file_inventory is None
    ):
        raise SourceAttachmentUnavailable(
            "A confirmed active analysis with known inventory is required."
        )
    if (
        review.ingestion_state is not IngestionState.COMPLETE
        or review.skipped_files
        or review.ingestion_warnings
    ):
        raise SourceAttachmentUnavailable("Source continuation requires a complete saved analysis.")
    if review.input_origin not in {
        ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
        ReviewInputOrigin.CONSTRUCTED_DEMO,
    }:
        raise SourceAttachmentUnavailable("This saved source origin does not support continuation.")
    if review.input_origin is ReviewInputOrigin.LIVE_PUBLIC_GITHUB:
        require_verified_public_origin(review.repository_visibility, review.input_origin)
        if not all(
            re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (review.base_sha, review.head_sha)
        ):
            raise SourceAttachmentUnavailable("Live reviewed source requires full commit SHAs.")
    return state


def required_source_candidate_paths(state: ReviewState) -> list[str]:
    """Recover only explicitly recorded unchanged paths, never inferred repository scans."""
    state = _attachable_state(state)
    assert state.bundle is not None
    paths = sorted(
        {
            item.file_path
            for item in [*state.bundle.evidence, *active_references(state.bundle)]
            if item.source_scope is EvidenceSourceScope.UNCHANGED_CANDIDATE
        }
    )
    if len(paths) > MAX_ATTACHED_CANDIDATE_FILES:
        raise SourceAttachmentUnavailable(
            "Recorded unchanged paths exceed the eight-file source limit."
        )
    try:
        for path in paths:
            SelectableReferenceLine.require_canonical_repository_path(path)
    except ValueError as error:
        raise SourceAttachmentUnavailable("Recorded source path is noncanonical.") from error
    return paths


def validate_review_source_snapshot(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    *,
    source_origin: ReviewInputOrigin,
) -> PullRequestSnapshot:
    """Check fresh observations before a later candidate fetch can fail or time out."""
    state = _attachable_state(state)
    review = state.review
    try:
        snapshot = PullRequestSnapshot.model_validate(snapshot.model_dump(mode="python"))
    except ValueError as error:
        raise SourceAttachmentUnavailable(
            "Fetched source is inconsistent.", observed_conflict=True
        ) from error
    if source_origin is not review.input_origin:
        raise SourceAttachmentUnavailable("Source loading must preserve its recorded origin.")
    if source_origin is ReviewInputOrigin.LIVE_PUBLIC_GITHUB:
        try:
            require_verified_public_origin(snapshot.repository_visibility, source_origin)
        except ValueError as error:
            raise SourceAttachmentUnavailable(
                "Fresh public provenance is unavailable.", observed_conflict=True
            ) from error
    expected = (
        review.repository,
        review.pr_number,
        review.base_sha,
        review.head_sha,
        review.repository_visibility,
        review.ingestion_state,
        review.check_state,
        review.ci_observation.model_dump(mode="python"),
    )
    observed = (
        snapshot.repository,
        snapshot.pr_number,
        snapshot.base_sha,
        snapshot.head_sha,
        snapshot.repository_visibility,
        snapshot.ingestion_state,
        snapshot.check_state,
        snapshot.ci_observation.model_dump(mode="python"),
    )
    try:
        inventory = snapshot.scope_inventory()
    except ValueError as error:
        raise SourceAttachmentUnavailable(
            "Fresh source inventory is inconsistent.", observed_conflict=True
        ) from error
    assert review.changed_file_inventory is not None
    expected_files = {
        (f.path, f.status, f.previous_path) for f in review.changed_file_inventory.files
    }
    observed_files = {(f.path, f.status, f.previous_path) for f in inventory.files}
    if (
        expected != observed
        or expected_files != observed_files
        or snapshot.warnings
        or snapshot.skipped_files
        or any(f.truncated for f in snapshot.files)
    ):
        raise SourceAttachmentUnavailable(
            "Fresh source facts differ from the saved analysis. Use explicit re-review.",
            observed_conflict=True,
        )
    return snapshot


def _validated_source(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    candidate_files: list[RetrievedFile] | tuple[RetrievedFile, ...],
    source_origin: ReviewInputOrigin,
    *,
    allow_retained_candidates: bool = False,
) -> tuple[PullRequestSnapshot, tuple[RetrievedFile, ...]]:
    snapshot = validate_review_source_snapshot(state, snapshot, source_origin=source_origin)
    review = state.review
    try:
        candidates = tuple(
            RetrievedFile.model_validate(f.model_dump(mode="python")) for f in candidate_files
        )
        paths = required_source_candidate_paths(state)
        observed_paths = [f.path for f in candidates]
        coverage_matches = (
            set(paths).issubset(observed_paths)
            if allow_retained_candidates
            else sorted(observed_paths) == paths
        )
        if (
            len(candidates) > MAX_ATTACHED_CANDIDATE_FILES
            or len(observed_paths) != len(set(observed_paths))
            or not coverage_matches
        ):
            raise ValueError(
                "Candidate responses must match every recorded requested path exactly once."
            )
        blocked = {
            *review.skipped_files,
            *(f.path for f in snapshot.files),
            *(f.previous_path for f in snapshot.files if f.previous_path is not None),
        }
        for file in candidates:
            SelectableReferenceLine.require_canonical_repository_path(file.path)
            if (
                file.source_scope is not EvidenceSourceScope.UNCHANGED_CANDIDATE
                or file.commit_sha != review.head_sha
                or file.path in blocked
            ):
                raise ValueError("Candidate source is not an eligible exact-head unchanged file.")
        if sum(len(f.content.encode("utf-8")) for f in candidates) > MAX_ATTACHED_CANDIDATE_BYTES:
            raise ValueError("Candidate source bytes exceed the existing bound.")
    except ValueError as error:
        raise SourceAttachmentUnavailable(str(error)) from error
    assert state.bundle is not None
    recorded = {
        (r.source_scope, r.file_path, r.line_number): SelectableReferenceLine.model_validate(
            {name: getattr(r, name) for name in SelectableReferenceLine.model_fields}
        )
        for r in active_references(state.bundle)
    }
    if recorded:
        for line in _eligible_reference_lines(state, snapshot, list(candidates)):
            key = (line.source_scope, line.file_path, line.line_number)
            if recorded.get(key) == line:
                del recorded[key]
        if recorded:
            raise SourceAttachmentUnavailable(
                "Fresh source does not reproduce the recorded selected references.",
                observed_conflict=True,
            )
    return snapshot, tuple(sorted(candidates, key=lambda f: f.path))


def _source_fingerprint(
    snapshot: PullRequestSnapshot, candidates: list[RetrievedFile] | tuple[RetrievedFile, ...]
) -> str:
    return _hash(
        {
            "snapshot": snapshot.model_dump(mode="json"),
            "candidate_files": [
                f.model_dump(mode="json") for f in sorted(candidates, key=lambda f: f.path)
            ],
        }
    )


def prepare_saved_source_attachment(
    store: JsonReviewStore,
    current: ReviewState,
    *,
    snapshot: PullRequestSnapshot,
    candidate_files: list[RetrievedFile],
    source_origin: ReviewInputOrigin,
    expected_state_fingerprint: str,
) -> ReviewSourceAttachment:
    """Compare saved/current state after fetching; never write or hold a lock over network IO."""
    current = _attachable_state(current)
    if JsonReviewStore.state_fingerprint(current) != expected_state_fingerprint:
        raise SourceAttachmentUnavailable("The current review changed while source was loading.")
    try:
        with store.locked_load(current.review.review_id) as saved:
            if JsonReviewStore.state_fingerprint(saved) != expected_state_fingerprint:
                raise SourceAttachmentUnavailable(
                    "The saved review changed while source was loading."
                )
            snapshot, candidates = _validated_source(
                saved, snapshot, candidate_files, source_origin
            )
            return ReviewSourceAttachment(
                review_id=saved.review.review_id,
                saved_state_fingerprint=expected_state_fingerprint,
                context_fingerprint=review_source_context_fingerprint(saved),
                source_fingerprint=_source_fingerprint(snapshot, candidates),
                source_origin=source_origin,
                snapshot=snapshot,
                candidate_files=candidates,
            )
    except SourceAttachmentUnavailable:
        raise
    except (OSError, ValueError) as error:
        raise SourceAttachmentUnavailable(
            "Saved source continuation could not be revalidated."
        ) from error


def validate_source_attachment(
    state: ReviewState,
    attachment: ReviewSourceAttachment,
    snapshot: PullRequestSnapshot,
    candidate_files: list[RetrievedFile],
) -> None:
    """Revalidate the context and source, without expiring on neutral state transitions."""
    state = _attachable_state(state)
    try:
        receipt = ReviewSourceAttachment.model_validate(attachment.model_dump(mode="python"))
        if (
            receipt.review_id != state.review.review_id
            or receipt.context_fingerprint != review_source_context_fingerprint(state)
            or receipt.source_fingerprint
            != _source_fingerprint(receipt.snapshot, receipt.candidate_files)
            or receipt.source_fingerprint != _source_fingerprint(snapshot, candidate_files)
        ):
            raise ValueError("Source attachment expired because its context or source changed.")
        # Neutral audit actions may retire a manual-only path. Keep the already
        # bound source intact; this permits no new fetch or changed candidate bytes.
        # Initial preparation still requires the exact requested path set.
        _validated_source(
            state,
            snapshot,
            candidate_files,
            receipt.source_origin,
            allow_retained_candidates=True,
        )
    except SourceAttachmentUnavailable:
        raise
    except ValueError as error:
        raise SourceAttachmentUnavailable(str(error)) from error
