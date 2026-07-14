"""Atomic local JSON persistence for validated ScopeProof review state."""

from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import PullRequestSnapshot, ReviewState

RECORD_VERSION = 2
_SUPPORTED_RECORD_VERSIONS = (1, RECORD_VERSION)
_REVIEW_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def default_local_review_directory() -> Path:
    """Return the app-owned local directory for persisted review records."""
    return Path.home() / ".scopeproof" / "reviews"


class UnsupportedRecordVersion(ValueError):
    """Raised when a review record needs an unavailable migration."""


class UnsafeReviewStore(ValueError):
    """Raised when the configured store root is an unsafe filesystem object."""


@dataclass(frozen=True)
class HeadChange:
    changed: bool
    saved_head_sha: str
    current_head_sha: str


class JsonReviewStore:
    """Store only validated review state in an app-owned local directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _require_safe_directory(self) -> None:
        if self.directory.is_symlink():
            raise UnsafeReviewStore("review store directory must not be a symbolic link")
        if self.directory.exists() and not self.directory.is_dir():
            raise UnsafeReviewStore("review store path must be a directory")

    @staticmethod
    def _validate_review_id(review_id: str) -> str:
        basename = os.path.basename(review_id)
        if basename != review_id or not _REVIEW_ID.fullmatch(basename):
            raise ValueError("review_id must be a simple local record identifier")
        return basename

    def _path(self, review_id: str) -> Path:
        return self.directory / f"{self._validate_review_id(review_id)}.json"

    def _existing_record_path(self, review_id: str) -> Path:
        """Return a validated regular record file without following symlinks."""
        validated_id = self._validate_review_id(review_id)
        self._require_safe_directory()
        if not self.directory.is_dir():
            raise FileNotFoundError(validated_id)
        for candidate in self.directory.glob("*.json"):
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if candidate.stem == validated_id and _REVIEW_ID.fullmatch(candidate.stem):
                return candidate
        raise FileNotFoundError(validated_id)

    def list_review_ids(self) -> list[str]:
        """Return deterministic candidate record IDs without parsing record contents."""
        self._require_safe_directory()
        if not self.directory.is_dir():
            return []
        return sorted(
            candidate.stem
            for candidate in self.directory.glob("*.json")
            if not candidate.is_symlink()
            and candidate.is_file()
            and _REVIEW_ID.fullmatch(candidate.stem)
        )

    def save(self, state: ReviewState) -> Path:
        """Atomically save a versioned record without accepting credential fields."""
        validated = validated_review_state(state)
        self._require_safe_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(validated.review.review_id)
        payload = {
            "record_version": RECORD_VERSION,
            "saved_at": datetime.now(UTC).isoformat(),
            "state": validated.model_dump(mode="json"),
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
        payload = json.loads(self._existing_record_path(review_id).read_text(encoding="utf-8"))
        record_version = payload.get("record_version")
        if (
            type(record_version) is not int
            or record_version not in _SUPPORTED_RECORD_VERSIONS
        ):
            raise UnsupportedRecordVersion(
                f"Unsupported review record version {record_version!r}"
            )
        state_payload = deepcopy(payload["state"])
        if record_version == 1 and isinstance(state_payload, dict):
            active_bundle = state_payload.get("bundle")
            criteria_revision = state_payload.get("criteria_revision")
            if (
                isinstance(active_bundle, dict)
                and isinstance(criteria_revision, dict)
                and "number" in criteria_revision
            ):
                active_bundle["criteria_revision_number"] = criteria_revision["number"]
            analysis_history = state_payload.get("analysis_history")
            if isinstance(analysis_history, list):
                for historical_bundle in analysis_history:
                    if isinstance(historical_bundle, dict):
                        historical_bundle["criteria_revision_number"] = "unknown"
        return validated_review_state(ReviewState.model_validate(state_payload))

    @staticmethod
    def detect_head_change(state: ReviewState, snapshot: PullRequestSnapshot) -> HeadChange:
        """Compare a new snapshot without mutating saved evidence or the original review."""
        saved_head = state.review.head_sha
        return HeadChange(
            changed=saved_head != snapshot.head_sha,
            saved_head_sha=saved_head,
            current_head_sha=snapshot.head_sha,
        )
