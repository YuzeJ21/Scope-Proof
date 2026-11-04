"""Atomic local JSON persistence for validated ScopeProof review state."""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, StrictInt, ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import (
    JUnitImportWithdrawalEvent,
    PullRequestSnapshot,
    ReviewBundle,
    ReviewState,
)
from scopeproof_core.storage.atomic_files import (
    MAX_SAVED_RECORD_BYTES,
    read_bounded_utf8,
    read_text_no_follow,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - fail-closed portability guard
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # pragma: no cover - exercised through the Windows-lock seam
    msvcrt = None  # type: ignore[assignment]

RECORD_VERSION = 9
_SUPPORTED_RECORD_VERSIONS = (1, 2, 3, 4, 5, 6, 7, 8, 9)
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
    and os.scandir in os.supports_fd
    and os.open in os.supports_dir_fd
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
    """Raised when a guarded mutation would change a newer local review state."""


@dataclass(frozen=True)
class HeadChange:
    changed: bool
    saved_head_sha: str
    current_head_sha: str


@dataclass(frozen=True)
class ReviewDeletionTarget:
    """Local file identity observed when a user confirmed deletion."""

    review_id: str
    directory_identity: tuple[int, int]
    record_identity: tuple[int, int, int, int, int]


class JsonReviewStore:
    """Store only validated review state in an app-owned local directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _require_safe_directory(self) -> None:
        if ".." in self.directory.parts:
            raise UnsafeReviewStore("review store path must not contain parent traversal")
        absolute = Path(os.path.abspath(self.directory))
        reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        for component in (absolute, *absolute.parents):
            try:
                metadata = os.lstat(component)
            except (FileNotFoundError, NotADirectoryError):
                continue
            is_link = stat.S_ISLNK(metadata.st_mode) or bool(
                reparse_point & getattr(metadata, "st_file_attributes", 0)
            )
            if is_link:
                if component == absolute:
                    raise UnsafeReviewStore(
                        "review store directory must not be a symbolic link"
                    )
                raise UnsafeReviewStore(
                    "review store path must not traverse a symbolic link or reparse point"
                )
            if not stat.S_ISDIR(metadata.st_mode):
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

        if fcntl is None and msvcrt is None:
            raise OSError("serialized review updates are unsupported on this platform")
        validated_id = self._validate_review_id(review_id)
        self._require_safe_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        lock_name = f".{sha256(validated_id.encode('utf-8')).hexdigest()}.lock"
        try:
            descriptor = os.open(
                self.directory / lock_name,
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
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            else:
                assert msvcrt is not None
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"\0")
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
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

    @contextmanager
    def _locked_deletion_directory(self, review_id: str) -> Iterator[tuple[int, str]]:
        validated_id = self._validate_review_id(review_id)
        self._require_safe_directory()
        if not self.directory.is_dir():
            raise FileNotFoundError(validated_id)
        if not _SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED:
            raise OSError("safe local review deletion is unsupported on this platform")
        with self._mutation_lock(validated_id):
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
                yield directory_fd, f"{validated_id}.json"
            finally:
                os.close(directory_fd)

    @staticmethod
    def _deletion_target(
        directory_fd: int, record_name: str, review_id: str,
    ) -> ReviewDeletionTarget:
        folder = os.fstat(directory_fd)
        # Require an exact name even on case-insensitive volumes. Locks are keyed by ID.
        with os.scandir(directory_fd) as entries:
            entry = next((item for item in entries if item.name == record_name), None)
            if entry is None:
                raise FileNotFoundError(review_id)
            record = entry.stat(follow_symlinks=False)
        if not stat.S_ISREG(record.st_mode):
            raise FileNotFoundError(review_id)
        return ReviewDeletionTarget(
            review_id=review_id,
            directory_identity=(folder.st_dev, folder.st_ino),
            record_identity=(
                record.st_dev, record.st_ino, record.st_size, record.st_mtime_ns,
                record.st_ctime_ns,
            ),
        )

    def capture_deletion_target(self, review_id: str) -> ReviewDeletionTarget:
        """Bind confirmation to a regular file, even if its contents cannot be parsed."""
        with self._locked_deletion_directory(review_id) as (directory_fd, record_name):
            return self._deletion_target(directory_fd, record_name, review_id)

    def delete(
        self,
        review_id: str,
        *,
        expected_fingerprint: str | None = None,
        expected_target: ReviewDeletionTarget | None = None,
    ) -> None:
        """Delete one safe ID, optionally bound to a file and a previewed review state."""
        with self._locked_deletion_directory(review_id) as (directory_fd, record_name):
            current_target = self._deletion_target(directory_fd, record_name, review_id)
            if expected_target is not None and current_target != expected_target:
                raise StaleReviewState("saved review changed after deletion confirmation")
            if expected_fingerprint is not None:
                descriptor = os.open(
                    record_name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd,
                )
                with os.fdopen(descriptor, "rb") as handle:
                    opened = os.fstat(handle.fileno())
                    if (
                        not stat.S_ISREG(opened.st_mode)
                        or (opened.st_dev, opened.st_ino) != current_target.record_identity[:2]
                    ):
                        raise StaleReviewState("saved review changed while opening its preview")
                    current = self.decode_record(read_bounded_utf8(handle))
                if (
                    current.review.review_id != review_id
                    or self.state_fingerprint(current) != expected_fingerprint
                ):
                    raise StaleReviewState(
                        "saved review changed since preview; refresh details before deleting"
                    )
                if self._deletion_target(directory_fd, record_name, review_id) != current_target:
                    raise StaleReviewState("saved review changed while checking its preview")
            os.unlink(record_name, dir_fd=directory_fd)

    @staticmethod
    def state_fingerprint(state: ReviewState) -> str:
        """Return the deterministic identity used for optimistic saved-state checks."""

        validated = validated_review_state(state)
        return sha256(validated.model_dump_json().encode("utf-8")).hexdigest()

    @contextmanager
    def locked_load(self, review_id: str) -> Iterator[ReviewState]:
        """Yield one validated record while excluding concurrent record mutations."""

        validated_id = self._validate_review_id(review_id)
        with self._mutation_lock(validated_id):
            yield self.load(validated_id)

    @contextmanager
    def locked_load_many(
        self, review_ids: Sequence[str]
    ) -> Iterator[tuple[ReviewState, ...]]:
        """Yield validated records from one deadlock-safe mutation snapshot."""

        validated_ids = tuple(self._validate_review_id(item) for item in review_ids)
        unique_ids = sorted(set(validated_ids))
        with ExitStack() as stack:
            for review_id in unique_ids:
                stack.enter_context(self._mutation_lock(review_id))
            states = {review_id: self.load(review_id) for review_id in unique_ids}
            yield tuple(states[review_id] for review_id in validated_ids)

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
        serialized_bytes = serialized.encode("utf-8")
        if len(serialized_bytes) > MAX_SAVED_RECORD_BYTES:
            raise ValueError("saved review record exceeds the byte limit")
        with tempfile.NamedTemporaryFile(
            "wb", dir=self.directory, prefix=f".{target.stem}-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(serialized_bytes)
        temporary.replace(target)
        return target

    def save(
        self,
        state: ReviewState,
        *,
        expected_fingerprint: str | object | None = _UNCONDITIONAL_SAVE,
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
                    bundle.evidence,
                    bundle.file_scope_decisions,
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

    def load(self, review_id: str, *, max_bytes: int | None = None) -> ReviewState:
        """Load a known record format and validate all nested models."""
        try:
            return self._load_record(review_id, max_bytes=max_bytes)
        except RecursionError as error:
            raise ValueError("saved review nesting exceeds validation limits") from error

    def _load_record(self, review_id: str, *, max_bytes: int | None) -> ReviewState:
        """Keep parser, migration and nested-validation failures within the load boundary."""
        limit = MAX_SAVED_RECORD_BYTES if max_bytes is None else max_bytes
        if type(limit) is not int or not 1 <= limit <= MAX_SAVED_RECORD_BYTES:
            raise ValueError(
                "record byte limit must be a positive integer within the store maximum"
            )
        return self.decode_record(read_text_no_follow(
            self._existing_record_path(review_id), max_bytes=limit,
        ))

    @classmethod
    def decode_record(cls, text: str, *, require_recorded_facts: bool = False) -> ReviewState:
        """Validate a detached saved record through the same conservative migrations."""
        if len(text.encode("utf-8")) > MAX_SAVED_RECORD_BYTES:
            raise ValueError("saved review record exceeds the byte limit")
        try:
            return cls._decode_record(text, require_recorded_facts=require_recorded_facts)
        except RecursionError as error:
            raise ValueError("saved review nesting exceeds validation limits") from error

    @classmethod
    def _decode_record(cls, text: str, *, require_recorded_facts: bool) -> ReviewState:
        def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("saved review contains duplicate JSON keys")
                result[key] = value
            return result

        payload = json.loads(text, object_pairs_hook=unique_object)
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
        if isinstance(state_payload, dict):
            audit_bundles = [state_payload.get("bundle")]
            recorded_reviews = [state_payload.get("review")]
            if isinstance(state_payload.get("analysis_history"), list):
                audit_bundles.extend(state_payload["analysis_history"])
            for bundle in audit_bundles:
                if not isinstance(bundle, dict):
                    continue
                recorded_reviews.append(bundle.get("review"))
                if record_version < 7 and bundle.get("selected_reference_events", []) != []:
                    raise ValueError("reference audit events require saved record version 7")
                if record_version >= 7 and "selected_reference_events" not in bundle:
                    raise ValueError("version 7 requires explicit reference audit history")
                if record_version < 8 and bundle.get("junit_import_events", []) != []:
                    raise ValueError("JUnit audit events require saved record version 8")
                if record_version >= 8 and "junit_import_events" not in bundle:
                    raise ValueError("version 8 requires explicit JUnit audit history")
                if record_version == 8:
                    events = bundle.get("junit_import_events", [])
                    if not isinstance(events, list) or any(
                        not isinstance(event, dict)
                        or event.get("action", "withdrawn") != "withdrawn"
                        or event.get("schema_version", "junit-import-withdrawal-v1")
                        != "junit-import-withdrawal-v1"
                        for event in events
                    ):
                        raise ValueError(
                            "JUnit mapping correction events require saved record version 9"
                        )
                    for event in events:
                        try:
                            JUnitImportWithdrawalEvent.model_validate(event)
                        except ValidationError as error:
                            raise ValueError(
                                "Version 8 requires withdrawal-only JUnit audit; "
                                "mapping corrections require saved record version 9"
                            ) from error
            for review in recorded_reviews:
                if isinstance(review, dict):
                    # Constructor defaults describe new reviews, never absent saved facts.
                    review.setdefault("tool_version", "unknown")
                    review.setdefault("ruleset_version", "unknown")
        if record_version < 6 and isinstance(state_payload, dict):
            bundles = [state_payload.get("bundle")]
            history = state_payload.get("analysis_history")
            if isinstance(history, list):
                bundles.extend(history)
            for bundle in bundles:
                if (
                    isinstance(bundle, dict)
                    and "reviewer_selected_references" in bundle
                    and bundle["reviewer_selected_references"] != []
                ):
                    raise ValueError("selected references require saved record version 6")
        if record_version < 5 and isinstance(state_payload, dict):
            # Historical records never carried a complete exact-head file inventory.
            # A newly added field in a downgraded record cannot establish that fact.
            reviews = [state_payload.get("review")]
            bundles = [state_payload.get("bundle")]
            history = state_payload.get("analysis_history")
            if isinstance(history, list):
                bundles.extend(history)
            for bundle in bundles:
                if isinstance(bundle, dict):
                    reviews.append(bundle.get("review"))
                    bundle.pop("file_scope_decisions", None)
            for review in reviews:
                if isinstance(review, dict):
                    review["changed_file_inventory"] = None
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
            cls._migrate_runtime_evidence(state_payload)
            cls._unlink_legacy_manual_runtime_evidence(state_payload)
        migrate_ci_gates = cls._state_payload_needs_ci_gate_migration(state_payload)
        state = ReviewState.model_validate(state_payload)
        if require_recorded_facts:
            cls._require_recorded_facts(state)
        if record_version < 8 or migrate_ci_gates:
            state = cls._recompute_all_gates(state)
        return validated_review_state(state)

    @staticmethod
    def _require_recorded_facts(value: object) -> None:
        """Transfer cannot turn fresh-object UUID/time defaults into historical facts."""
        if isinstance(value, BaseModel):
            for name, field in type(value).model_fields.items():
                if (
                    field.default_factory is not None
                    and field.annotation in (str, datetime)
                    and name not in value.model_fields_set
                ):
                    raise ValueError(f"transfer requires explicitly recorded {name}")
                JsonReviewStore._require_recorded_facts(getattr(value, name))
        elif isinstance(value, list):
            for item in value:
                JsonReviewStore._require_recorded_facts(item)

    @staticmethod
    def detect_head_change(state: ReviewState, snapshot: PullRequestSnapshot) -> HeadChange:
        """Compare a new snapshot without mutating saved evidence or the original review."""
        saved_head = state.review.head_sha
        return HeadChange(
            changed=saved_head != snapshot.head_sha,
            saved_head_sha=saved_head,
            current_head_sha=snapshot.head_sha,
        )
