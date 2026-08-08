"""Atomic local JSON persistence for validated ScopeProof review state."""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import PullRequestSnapshot, ReviewBundle, ReviewState

try:
    import fcntl
except ImportError:  # pragma: no cover - fail-closed portability guard
    fcntl = None  # type: ignore[assignment]

RECORD_VERSION = 4
_SUPPORTED_RECORD_VERSIONS = (1, 2, 3, 4)
_REVIEW_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_LEGACY_CI_CATEGORIES = {
    "successful_legacy_statuses",
    "pending_legacy_statuses",
    "failing_legacy_statuses",
    "neutral_legacy_statuses",
}
_SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED = (
    hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and os.stat in os.supports_dir_fd
    and os.stat in os.supports_follow_symlinks
    and os.unlink in os.supports_dir_fd
)
_UNCONDITIONAL_SAVE = object()


class _ReviewRecordEnvelope(BaseModel):
    """Strict outer contract around versioned, migratable review state."""

    model_config = ConfigDict(extra="forbid", strict=True)

    record_version: StrictInt
    saved_at: str | None = None
    state: object


def default_local_review_directory() -> Path:
    """Return the app-owned local directory for persisted review records."""
    return Path.home() / ".scopeproof" / "reviews"


class UnsupportedRecordVersion(ValueError):
    """Raised when a review record needs an unavailable migration."""


class UnsafeReviewStore(ValueError):
    """Raised when the configured store root is an unsafe filesystem object."""


class StaleReviewState(ValueError):
    """Raised when a guarded save would replace a newer local review state."""


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

    @contextmanager
    def _mutation_lock(self, review_id: str) -> Iterator[None]:
        """Serialize one record's read-transition-write lifecycle."""

        if fcntl is None:
            raise OSError("serialized review updates are unsupported on this platform")
        validated_id = self._validate_review_id(review_id)
        self._require_safe_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(
                self.directory / f".{validated_id}.lock",
                flags,
                0o600,
            )
        except OSError:
            raise UnsafeReviewStore("review mutation lock must be a regular local file") from None
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise UnsafeReviewStore(
                    "review mutation lock must be a regular local file"
                )
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

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

    def delete(self, review_id: str) -> None:
        """Delete one exact safe local record without parsing its contents."""
        validated_id = self._validate_review_id(review_id)
        self._require_safe_directory()
        if not _SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED:
            raise OSError("safe local review deletion is unsupported on this platform")
        try:
            directory_fd = os.open(
                self.directory,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
        except FileNotFoundError:
            raise FileNotFoundError(validated_id) from None
        except NotADirectoryError:
            raise UnsafeReviewStore("review store path must be a directory") from None
        try:
            record_name = f"{validated_id}.json"
            with os.scandir(directory_fd) as entries:
                matching_entry = next(
                    (
                        entry
                        for entry in entries
                        if entry.name == record_name
                        and entry.is_file(follow_symlinks=False)
                        and stat.S_ISREG(entry.stat(follow_symlinks=False).st_mode)
                    ),
                    None,
                )
            if matching_entry is None:
                raise FileNotFoundError(validated_id) from None
            os.unlink(matching_entry.name, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)

    @staticmethod
    def state_fingerprint(state: ReviewState) -> str:
        """Return the deterministic identity used for optimistic saved-state checks."""

        validated = validated_review_state(state)
        return sha256(validated.model_dump_json().encode("utf-8")).hexdigest()

    def _save_unlocked(self, validated: ReviewState) -> Path:
        """Replace one validated record while its mutation lock is already held."""

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

    def save(
        self,
        state: ReviewState,
        *,
        expected_fingerprint: str | None | object = _UNCONDITIONAL_SAVE,
    ) -> Path:
        """Atomically save, optionally rejecting a stale read-derived state."""

        validated = validated_review_state(state)
        review_id = validated.review.review_id
        with self._mutation_lock(review_id):
            if expected_fingerprint is not _UNCONDITIONAL_SAVE:
                try:
                    current = self.load(review_id)
                except FileNotFoundError:
                    current_fingerprint = None
                else:
                    current_fingerprint = self.state_fingerprint(current)
                if current_fingerprint != expected_fingerprint:
                    raise StaleReviewState(
                        "saved review changed since it was loaded; reopen it before saving"
                    )
            return self._save_unlocked(validated)

    def mutate(
        self,
        review_id: str,
        transition: Callable[[ReviewState], ReviewState],
    ) -> tuple[ReviewState, Path]:
        """Apply one validated transition while holding the record mutation lock."""

        validated_id = self._validate_review_id(review_id)
        with self._mutation_lock(validated_id):
            current = self.load(validated_id)
            updated = validated_review_state(transition(current))
            if updated.review.review_id != current.review.review_id:
                raise ValueError("review mutation cannot change the record identity")
            return updated, self._save_unlocked(updated)

    @staticmethod
    def _review_payload_needs_ci_gate_migration(review_payload: object) -> bool:
        if not isinstance(review_payload, dict):
            return False
        observation = review_payload.get("ci_observation")
        if not isinstance(observation, dict):
            return True
        concrete_count = observation.get("concrete_legacy_status_count", 0)
        return (
            isinstance(concrete_count, int)
            and concrete_count > 0
            and not _LEGACY_CI_CATEGORIES.issubset(observation)
        )

    @classmethod
    def _state_payload_needs_ci_gate_migration(cls, state_payload: object) -> bool:
        if not isinstance(state_payload, dict):
            return False
        review_payloads = [state_payload.get("review")]
        active_bundle = state_payload.get("bundle")
        if isinstance(active_bundle, dict):
            review_payloads.append(active_bundle.get("review"))
        history = state_payload.get("analysis_history")
        if isinstance(history, list):
            review_payloads.extend(
                bundle.get("review") for bundle in history if isinstance(bundle, dict)
            )
        return any(cls._review_payload_needs_ci_gate_migration(item) for item in review_payloads)

    @staticmethod
    def _with_recomputed_gate(bundle: ReviewBundle) -> ReviewBundle:
        return bundle.model_copy(
            update={
                "gate": evaluate_gate(
                    bundle.review,
                    bundle.criteria,
                    bundle.findings,
                    bundle.resolutions,
                )
            }
        )

    @classmethod
    def _recompute_all_gates(cls, state: ReviewState) -> ReviewState:
        bundle = (
            cls._with_recomputed_gate(state.bundle)
            if state.bundle is not None
            else None
        )
        history = [cls._with_recomputed_gate(item) for item in state.analysis_history]
        return state.model_copy(update={"bundle": bundle, "analysis_history": history})

    @staticmethod
    def _migrate_runtime_bundle(bundle_payload: object, bundle_key: str) -> bool:
        if not isinstance(bundle_payload, dict):
            return False
        runtime_evidence = bundle_payload.get("runtime_evidence")
        review_payload = bundle_payload.get("review")
        if not isinstance(runtime_evidence, list) or not isinstance(review_payload, dict):
            return False

        migrated = False
        for item_index, runtime_item in enumerate(runtime_evidence):
            if not isinstance(runtime_item, dict):
                continue
            canonical_original_payload = json.dumps(
                runtime_item,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            review_id = review_payload.get("review_id")
            seed = (
                f"scopeproof-runtime-evidence:{review_id}:{bundle_key}:"
                f"{item_index}:{canonical_original_payload}"
            )
            runtime_item.update(
                {
                    "runtime_evidence_id": str(uuid5(NAMESPACE_URL, seed)),
                    "repository": review_payload.get("repository"),
                    "pr_number": review_payload.get("pr_number"),
                    "head_sha": review_payload.get("head_sha"),
                }
            )
            migrated = True
        return migrated

    @staticmethod
    def _bundle_has_legacy_manual_resolution(bundle_payload: object) -> bool:
        if not isinstance(bundle_payload, dict):
            return False
        resolutions = bundle_payload.get("resolutions")
        return isinstance(resolutions, list) and any(
            isinstance(resolution, dict)
            and resolution.get("decision") == "manually_verified"
            for resolution in resolutions
        )

    @classmethod
    def _migrate_runtime_evidence(
        cls, state_payload: object
    ) -> tuple[bool, set[int]]:
        if not isinstance(state_payload, dict):
            return False, set()
        active_bundle = state_payload.get("bundle")
        active_gate_affected = False
        if isinstance(active_bundle, dict):
            active_gate_affected = (
                cls._migrate_runtime_bundle(
                    active_bundle,
                    f"active:{active_bundle.get('criteria_revision_number')}",
                )
                or cls._bundle_has_legacy_manual_resolution(active_bundle)
            )

        gate_affected_history: set[int] = set()
        history = state_payload.get("analysis_history")
        if isinstance(history, list):
            for history_index, historical_bundle in enumerate(history):
                runtime_migrated = cls._migrate_runtime_bundle(
                    historical_bundle, f"history:{history_index}"
                )
                if runtime_migrated or cls._bundle_has_legacy_manual_resolution(
                    historical_bundle
                ):
                    gate_affected_history.add(history_index)
        return active_gate_affected, gate_affected_history

    @staticmethod
    def _unlink_legacy_manual_runtime_evidence(state_payload: object) -> None:
        if not isinstance(state_payload, dict):
            return
        bundles = [state_payload.get("bundle")]
        history = state_payload.get("analysis_history")
        if isinstance(history, list):
            bundles.extend(history)
        for bundle in bundles:
            if not isinstance(bundle, dict):
                continue
            resolutions = bundle.get("resolutions")
            if not isinstance(resolutions, list):
                continue
            for resolution in resolutions:
                if (
                    isinstance(resolution, dict)
                    and resolution.get("decision") == "manually_verified"
                ):
                    resolution.pop("runtime_evidence_id", None)

        resolution_events = state_payload.get("resolution_events")
        if not isinstance(resolution_events, list):
            return
        for event in resolution_events:
            if (
                isinstance(event, dict)
                and event.get("decision") == "manually_verified"
            ):
                event.pop("runtime_evidence_id", None)

    def load(self, review_id: str) -> ReviewState:
        """Load a known record format and validate all nested models."""
        payload = json.loads(self._existing_record_path(review_id).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid review record envelope")
        record_version = payload.get("record_version")
        if (
            type(record_version) is not int
            or record_version not in _SUPPORTED_RECORD_VERSIONS
        ):
            raise UnsupportedRecordVersion(
                f"Unsupported review record version {record_version!r}"
            )
        try:
            envelope = _ReviewRecordEnvelope.model_validate(payload)
        except ValidationError as error:
            raise ValueError("invalid review record envelope") from error
        state_payload = deepcopy(envelope.state)
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
        if record_version in {1, 2}:
            self._migrate_runtime_evidence(state_payload)
            self._unlink_legacy_manual_runtime_evidence(state_payload)
        migrate_ci_gates = self._state_payload_needs_ci_gate_migration(state_payload)
        state = ReviewState.model_validate(state_payload)
        if record_version < RECORD_VERSION or migrate_ci_gates:
            state = self._recompute_all_gates(state)
        return validated_review_state(state)

    @staticmethod
    def detect_head_change(state: ReviewState, snapshot: PullRequestSnapshot) -> HeadChange:
        """Compare a new snapshot without mutating saved evidence or the original review."""
        saved_head = state.review.head_sha
        return HeadChange(
            changed=saved_head != snapshot.head_sha,
            saved_head_sha=saved_head,
            current_head_sha=snapshot.head_sha,
        )
