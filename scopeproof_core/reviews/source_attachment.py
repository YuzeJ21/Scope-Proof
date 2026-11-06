"""Exact-source continuation for confirmed saved analyses and pending revisions."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.lifecycle import attach_analysis
from scopeproof_core.reviews.reference_audit import active_references
from scopeproof_core.reviews.selected_references import _eligible_reference_lines
from scopeproof_core.schemas.models import (
    CheckState,
    EvidenceSourceScope,
    IngestionState,
    LocalReviewId,
    PullRequestSnapshot,
    RetrievedFile,
    Review,
    ReviewBundle,
    ReviewInputOrigin,
    ReviewState,
    SelectableReferenceLine,
    require_verified_public_origin,
)
from scopeproof_core.storage.json_store import JsonReviewStore

MAX_ATTACHED_CANDIDATE_FILES = 8
MAX_ATTACHED_CANDIDATE_BYTES = 200_000
Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_FULL_SHA_PATTERN = r"^[0-9a-f]{40}$"


class SourceAttachmentUnavailable(ValueError):
    """Reject continuation without changing saved truth or inventing observations."""

    def __init__(
        self, message: str, *, observed_conflict: bool = False,
        observed_head_sha: str | None = None, observed_check_state: CheckState | None = None,
    ) -> None:
        super().__init__(message)
        self.observed_conflict = observed_conflict
        self.observed_head_sha = observed_head_sha
        self.observed_check_state = observed_check_state


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
        not state.criteria_revision.confirmed
        or not review.criteria_confirmed
        or review.criteria_source_provenance is None
        or review.changed_file_inventory is None
    ):
        raise SourceAttachmentUnavailable(
            "A confirmed saved revision with known inventory is required."
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
            re.fullmatch(_FULL_SHA_PATTERN, sha) for sha in (review.base_sha, review.head_sha)
        ):
            raise SourceAttachmentUnavailable("Live reviewed source requires full commit SHAs.")
    _source_path_anchor(state)
    return state


def _source_path_anchor(state: ReviewState) -> ReviewBundle:
    if state.bundle is not None:
        return state.bundle
    if not state.analysis_history:
        raise SourceAttachmentUnavailable(
            "Pending continuation requires a retained source analysis."
        )
    anchor = state.analysis_history[-1]
    source_fields = (
        "repository",
        "pr_number",
        "base_sha",
        "head_sha",
        "repository_visibility",
        "input_origin",
        "changed_file_inventory",
        "ingestion_state",
        "ingestion_warnings",
        "skipped_files",
        "check_state",
        "ci_observation",
    )
    if any(getattr(anchor.review, name) != getattr(state.review, name) for name in source_fields):
        raise SourceAttachmentUnavailable("Latest retained source differs; use explicit re-review.")
    return anchor


def required_source_candidate_paths(state: ReviewState) -> list[str]:
    """Recover only explicitly recorded unchanged paths, never inferred repository scans."""
    state = _attachable_state(state)
    anchor = _source_path_anchor(state)
    paths = sorted(
        {
            item.file_path
            for item in [*anchor.evidence, *active_references(anchor)]
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
    """Check source facts for a review eligible for matching-source continuation."""
    return validate_recorded_review_snapshot(
        _attachable_state(state).review, snapshot, source_origin=source_origin,
    )


def validate_recorded_review_snapshot(
    review: Review,
    snapshot: PullRequestSnapshot,
    *,
    source_origin: ReviewInputOrigin,
) -> PullRequestSnapshot:
    """Check fresh source facts without authorizing a source attachment."""
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
        review.ingestion_warnings,
        review.skipped_files,
    )
    observed = (
        snapshot.repository,
        snapshot.pr_number,
        snapshot.base_sha,
        snapshot.head_sha,
        snapshot.repository_visibility,
        snapshot.ingestion_state,
        snapshot.warnings,
        snapshot.skipped_files,
    )
    checks_differ = (
        review.check_state != snapshot.check_state
        or review.ci_observation.model_dump(mode="python")
        != snapshot.ci_observation.model_dump(mode="python")
    )
    try:
        inventory = snapshot.scope_inventory()
    except ValueError as error:
        raise SourceAttachmentUnavailable(
            "Fresh source inventory is inconsistent.", observed_conflict=True
        ) from error
    recorded_inventory = review.changed_file_inventory
    inventory_differs = recorded_inventory is not None and {
        (f.path, f.status, f.previous_path) for f in recorded_inventory.files
    } != {(f.path, f.status, f.previous_path) for f in inventory.files}
    if (
        expected != observed
        or checks_differ
        or inventory_differs
        or (
            review.ingestion_state is IngestionState.COMPLETE
            and any(f.truncated for f in snapshot.files)
        )
    ):
        exact_public_pr = (
            source_origin is ReviewInputOrigin.LIVE_PUBLIC_GITHUB
            and snapshot.repository.casefold() == review.repository.casefold()
            and snapshot.pr_number == review.pr_number
            and all(
                re.fullmatch(_FULL_SHA_PATTERN, sha)
                for sha in (review.head_sha, snapshot.head_sha)
            )
        )
        head_changed = snapshot.head_sha != review.head_sha
        raise SourceAttachmentUnavailable(
            "Fresh source facts differ from the saved analysis. Use explicit re-review.",
            observed_conflict=True,
            observed_head_sha=snapshot.head_sha if exact_public_pr and head_changed else None,
            observed_check_state=(
                snapshot.check_state if exact_public_pr and not head_changed and checks_differ
                else None
            ),
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
    # Pending revisions use historical references only as explicit path context.
    # New analysis recomputes findings; it never copies or reaffirms old references.
    recorded = {
        (r.source_scope, r.file_path, r.line_number): SelectableReferenceLine.model_validate(
            {name: getattr(r, name) for name in SelectableReferenceLine.model_fields}
        )
        for r in (active_references(state.bundle) if state.bundle is not None else [])
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
            or (
                state.bundle is None
                and receipt.saved_state_fingerprint != JsonReviewStore.state_fingerprint(state)
            )
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


def attach_saved_pending_analysis(
    store: JsonReviewStore,
    current: ReviewState,
    bundle: ReviewBundle,
    *,
    attachment: ReviewSourceAttachment,
    snapshot: PullRequestSnapshot,
    candidate_files: list[RetrievedFile],
) -> ReviewState:
    """Install fresh analysis under the complete source lease and record mutation lock."""
    current = _attachable_state(current)
    if current.bundle is not None:
        raise SourceAttachmentUnavailable("Analysis continuation requires a pending revision.")
    validate_source_attachment(current, attachment, snapshot, candidate_files)
    bundle = ReviewBundle.model_validate(bundle.model_dump(mode="python"))
    if (
        any(
            getattr(bundle, name)
            for name in (
                "resolutions",
                "runtime_evidence",
                "file_scope_decisions",
                "reviewer_selected_references",
                "selected_reference_events",
                "junit_evidence_imports",
                "junit_import_events",
            )
        )
        or bundle.review.final_acceptance
    ):
        raise SourceAttachmentUnavailable("Fresh analysis cannot inherit prior review context.")
    expected = JsonReviewStore.state_fingerprint(current)

    def transition(saved: ReviewState) -> ReviewState:
        if JsonReviewStore.state_fingerprint(saved) != expected:
            raise SourceAttachmentUnavailable(
                "Saved revision changed before analysis was committed."
            )
        validate_source_attachment(saved, attachment, snapshot, candidate_files)
        return attach_analysis(saved, bundle)

    updated, _ = store.mutate(current.review.review_id, transition)
    return updated
