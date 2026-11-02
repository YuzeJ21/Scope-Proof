"""Explicit, byte-preserving saved-review transfer without new evidence authority."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.atomic_files import (
    MAX_SAVED_RECORD_BYTES,
    atomic_create_text,
    read_text_no_follow,
)
from scopeproof_core.storage.json_store import JsonReviewStore, _ReviewRecordEnvelope

BOUNDARY_NOTE = (
    "Preserves recorded claims and history; no actor authentication, renewed verification, "
    "or independent-use evidence. Reopening applies the installed reader's validation policy."
)


class ReviewTransferReceipt(BaseModel):
    """Content identity for a completed transfer, not an authenticity certificate."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal[1] = 1
    action: Literal["exported", "imported"]
    review_id: str
    head_sha: str
    record_version: int
    saved_at: str | None
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_bytes: int = Field(gt=0, le=MAX_SAVED_RECORD_BYTES)
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    analysis_history_count: int = Field(ge=0)
    boundary_note: Literal[BOUNDARY_NOTE] = BOUNDARY_NOTE


def _read_record(path: Path) -> tuple[str, ReviewState]:
    text = read_text_no_follow(
        path, max_bytes=MAX_SAVED_RECORD_BYTES, preserve_newlines=True,
    )
    state = JsonReviewStore.decode_record(text, require_recorded_facts=True)
    JsonReviewStore._validate_review_id(state.review.review_id)
    return text, state


def _receipt(
    text: str, state: ReviewState, action: Literal["exported", "imported"],
) -> ReviewTransferReceipt:
    envelope = _ReviewRecordEnvelope.model_validate_json(text)
    raw = text.encode("utf-8")
    return ReviewTransferReceipt(
        action=action, review_id=state.review.review_id, head_sha=state.review.head_sha,
        record_version=envelope.record_version, saved_at=envelope.saved_at,
        record_sha256=sha256(raw).hexdigest(), record_bytes=len(raw),
        state_fingerprint=JsonReviewStore.state_fingerprint(state),
        analysis_history_count=len(state.analysis_history),
    )


def export_review(store: JsonReviewStore, review_id: str, output: Path) -> ReviewTransferReceipt:
    """Copy one validated saved record, retaining its exact original serialization."""
    # Hold the existing per-record lock through snapshot validation and publication.
    with store._mutation_lock(review_id):
        text, state = _read_record(store._existing_record_path(review_id))
        if state.review.review_id != review_id:
            raise ValueError("saved filename and review identity differ")
        receipt = _receipt(text, state, "exported")
        atomic_create_text(output, text)
    return receipt


def import_review(store: JsonReviewStore, source: Path) -> ReviewTransferReceipt:
    """Install one explicit portable record under its original ID, never overwriting."""
    text, state = _read_record(source)
    receipt = _receipt(text, state, "imported")
    with store._mutation_lock(state.review.review_id):
        atomic_create_text(store._path(state.review.review_id), text)
    return receipt
