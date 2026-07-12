"""Atomic local JSON persistence for validated ScopeProof review state."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scopeproof_core.schemas.models import PullRequestSnapshot, ReviewState

RECORD_VERSION = 1
_REVIEW_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def default_local_review_directory() -> Path:
    """Return the app-owned local directory for persisted review records."""
    return Path.home() / ".scopeproof" / "reviews"


class UnsupportedRecordVersion(ValueError):
    """Raised when a review record needs an unavailable migration."""


@dataclass(frozen=True)
class HeadChange:
    changed: bool
    saved_head_sha: str
    current_head_sha: str


class JsonReviewStore:
    """Store only validated review state in a user-selected local directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    @staticmethod
    def _validate_review_id(review_id: str) -> str:
        if not _REVIEW_ID.fullmatch(review_id):
            raise ValueError("review_id must be a simple local record identifier")
        return review_id

    def _path(self, review_id: str) -> Path:
        return self.directory / f"{self._validate_review_id(review_id)}.json"

    def save(self, state: ReviewState) -> Path:
        """Atomically save a versioned record without accepting credential fields."""
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(state.review.review_id)
        payload = {
            "record_version": RECORD_VERSION,
            "saved_at": datetime.now(UTC).isoformat(),
            "state": state.model_dump(mode="json"),
        }
        serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.directory, prefix=f".{target.stem}-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
        temporary.replace(target)
        return target

    def load(self, review_id: str) -> ReviewState:
        """Load a known record format and validate all nested models."""
        payload = json.loads(self._path(review_id).read_text(encoding="utf-8"))
        if payload.get("record_version") != RECORD_VERSION:
            raise UnsupportedRecordVersion(
                f"Unsupported review record version {payload.get('record_version')!r}"
            )
        return ReviewState.model_validate(payload["state"])

    @staticmethod
    def detect_head_change(state: ReviewState, snapshot: PullRequestSnapshot) -> HeadChange:
        """Compare a new snapshot without mutating saved evidence or the original review."""
        saved_head = state.review.head_sha
        return HeadChange(
            changed=saved_head != snapshot.head_sha,
            saved_head_sha=saved_head,
            current_head_sha=snapshot.head_sha,
        )
