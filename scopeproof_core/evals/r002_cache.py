"""Descriptor-relative, fail-closed persistence for the local R-002 research cache."""

from __future__ import annotations

import errno
import inspect
import os
import re
import secrets
import stat
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager as ContextManager
from contextlib import contextmanager, suppress
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO, NoReturn, TypeVar

from pydantic import BaseModel, ValidationError

from scopeproof_core.evals.r002_models import (
    R002_ANNOTATION_REVIEW_MAX_BYTES,
    R002_ANNOTATION_UNIVERSE_MAX_BYTES,
    R002AnnotationReview,
    R002AnnotationReviewItem,
    R002AnnotationUniverse,
    R002BenchmarkResult,
    R002CacheIndex,
    R002CandidateLabelProposal,
    R002CandidateLineKey,
    R002CriteriaProposal,
    R002CriteriaSourceIndex,
    R002Error,
    SWEbenchVerifiedRow,
    canonical_json_bytes,
    canonical_sha256,
    r002_annotation_key_order,
)
from scopeproof_core.schemas.models import ReviewBundle

try:
    import fcntl
except ImportError:  # pragma: no cover - fail-closed portability guard
    fcntl = None  # type: ignore[assignment]

T = TypeVar("T", bound=BaseModel)

_SAFE_RELATIVE = re.compile(
    r"^(?:criteria-source-index\.json|cache-index\.json|"
    r"criteria-proposal\.json|criteria-review\.json|"
    r"annotation-universe\.json|annotation-review\.json|"
    r"candidate-label-proposal\.json|result\.json|"
    r"rows/[0-9a-f]{64}|criteria-sources/[0-9a-f]{64}|"
    r"head-files/[0-9a-f]{64}|reviews/R002-(00[1-9]|01\d|020)\.json)$"
)
_RESERVED_MARKERS = frozenset({"criteria-source-index.json", "cache-index.json"})
_RAW_NAMESPACES = ("criteria-sources/", "head-files/")
_CONTENT_NAMESPACES = ("rows/", *_RAW_NAMESPACES)
_STREAMED_ARTIFACTS = frozenset({"annotation-universe.json", "annotation-review.json"})
_CONTROL_MODELS: dict[str, type[BaseModel]] = {
    "criteria-proposal.json": R002CriteriaProposal,
    "criteria-review.json": R002CriteriaProposal,
    "candidate-label-proposal.json": R002CandidateLabelProposal,
    "result.json": R002BenchmarkResult,
}

# Generic control sizes are local engineering bounds, not benchmark evidence claims.
# The largest persisted R-002 collections share the plan's 512 MiB per-file ceiling.
_MAX_CRITERIA_SOURCE_BYTES = 128 * 1024
_MAX_HEAD_FILE_BYTES = 4 * 1024 * 1024
_MAX_ROW_BYTES = 1024 * 1024
_MAX_SMALL_CONTROL_BYTES = 16 * 1024 * 1024
_MAX_LARGE_CONTROL_BYTES = 512 * 1024 * 1024
_TEMP_PREFIX = ".r002-tmp-"
_SCRATCH_PREFIX = ".r002-scratch-"
_ANNOTATION_LOCK = ".r002-annotation.lock"

_DIRECTORY_FLAGS = (
    getattr(os, "O_RDONLY", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_READ_FLAGS = (
    getattr(os, "O_RDONLY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NONBLOCK", 0)
)
_CREATE_FLAGS = (
    getattr(os, "O_WRONLY", 0)
    | getattr(os, "O_CREAT", 0)
    | getattr(os, "O_EXCL", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_SCRATCH_CREATE_FLAGS = (
    getattr(os, "O_RDWR", 0)
    | getattr(os, "O_CREAT", 0)
    | getattr(os, "O_EXCL", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_BASE_DIRFD_SUPPORT = (
    all(function in os.supports_dir_fd for function in (os.open, os.mkdir, os.unlink, os.link))
    and os.link in os.supports_follow_symlinks
)
try:
    _REPLACE_HAS_DIRFD = {
        "src_dir_fd",
        "dst_dir_fd",
    }.issubset(inspect.signature(os.replace).parameters)
except (TypeError, ValueError):
    _REPLACE_HAS_DIRFD = False


class R002CacheError(R002Error):
    """A closed, sanitized cache failure with no native diagnostic payload."""

    allowed_reason_codes = frozenset(
        {
            "annotation_pair_limit",
            "annotation_pair_mismatch",
            "annotation_stream_invalid",
            "cache_directory_security",
            "cache_file_security",
            "cache_fsync_failed",
            "cache_read_failed",
            "cache_replace_failed",
            "cache_state_unknown",
            "cache_write_failed",
            "completion_marker_missing",
            "completion_marker_requires_publish",
            "content_address_collision",
            "content_address_digest_mismatch",
            "control_already_exists",
            "criteria_source_index_mismatch",
            "model_type_mismatch",
            "model_validation_failed",
            "raw_write_requires_content_namespace",
            "referenced_object_mismatch",
            "referenced_object_missing",
            "scratch_failed",
            "streamed_annotation_requires_writer",
            "symlink_or_nondirectory",
            "temp_collision",
            "unsafe_relative_name",
            "unsupported_filesystem_primitives",
            "writer_lock_failed",
        }
    )


_CANONICAL_CACHE_REASONS = {reason: reason for reason in R002CacheError.allowed_reason_codes}


def _caught_reason(caught: R002CacheError, fallback: str) -> str:
    try:
        args = BaseException.args.__get__(caught, type(caught))
    except Exception:
        return fallback
    if type(args) is not tuple or len(args) != 1 or type(args[0]) is not str:
        return fallback
    return _CANONICAL_CACHE_REASONS.get(args[0], fallback)


def _close_fd(fd: int) -> bool:
    try:
        os.close(fd)
        return True
    except OSError:
        # close(2) leaves descriptor state unspecified on error. Retrying could
        # close an unrelated descriptor if this number was already reused.
        return False


def _close_all(fds: Iterator[int] | tuple[int, ...] | list[int]) -> bool:
    closed = True
    for fd in fds:
        if not _close_fd(fd):
            closed = False
    return closed


def _raise_public(reason_code: str) -> NoReturn:
    raise R002CacheError(reason_code) from None


def _validate_relative_name(relative_name: str) -> str:
    if type(relative_name) is not str or _SAFE_RELATIVE.fullmatch(relative_name) is None:
        raise R002CacheError("unsafe_relative_name")
    return relative_name


def _model_for_name(relative_name: str) -> type[BaseModel] | None:
    if relative_name.startswith("reviews/"):
        return ReviewBundle
    return _CONTROL_MODELS.get(relative_name)


def _byte_limit(relative_name: str) -> int:
    if relative_name.startswith("criteria-sources/"):
        return _MAX_CRITERIA_SOURCE_BYTES
    if relative_name.startswith("head-files/"):
        return _MAX_HEAD_FILE_BYTES
    if relative_name.startswith("rows/"):
        return _MAX_ROW_BYTES
    if relative_name == "annotation-universe.json":
        return R002_ANNOTATION_UNIVERSE_MAX_BYTES
    if relative_name == "annotation-review.json":
        return R002_ANNOTATION_REVIEW_MAX_BYTES
    if relative_name in {"cache-index.json", "candidate-label-proposal.json", "result.json"}:
        return _MAX_LARGE_CONTROL_BYTES
    if relative_name.startswith("reviews/"):
        return _MAX_LARGE_CONTROL_BYTES
    return _MAX_SMALL_CONTROL_BYTES


def _fixed_canonical_bytes(value: BaseModel, model_type: type[BaseModel]) -> bytes:
    try:
        serializer = type.__getattribute__(model_type, "__pydantic_serializer__")
        payload = serializer.to_python(value, mode="json", warnings="error")
        if type(payload) is not dict:
            raise TypeError("model serializer did not produce an object")
        return canonical_json_bytes(payload)
    except Exception:
        raise R002CacheError("model_validation_failed") from None


def _revalidate_instance(value: BaseModel, model_type: type[T]) -> tuple[T, bytes]:
    if type(value) is not model_type:
        raise R002CacheError("model_type_mismatch")
    try:
        initial = _fixed_canonical_bytes(value, model_type)
        validated = model_type.model_validate_json(initial, strict=True)
        data = _fixed_canonical_bytes(validated, model_type)
    except (TypeError, ValueError, ValidationError, UnicodeError):
        raise R002CacheError("model_validation_failed") from None
    return validated, data


def _decode_canonical_model(data: bytes, model_type: type[T]) -> T:
    try:
        value = model_type.model_validate_json(data, strict=True)
        if _fixed_canonical_bytes(value, model_type) != data:
            raise ValueError("noncanonical")
    except (TypeError, ValueError, ValidationError, UnicodeError):
        raise R002CacheError("model_validation_failed") from None
    return value


class R002Cache:
    """A cache rooted by a fresh descriptor walk for every public operation."""

    def __init__(self, root: Path) -> None:
        self._display_root = Path(root)
        self._root_is_absolute = self._display_root.is_absolute()
        anchor = self._display_root.anchor
        self._root_parts = tuple(part for part in self._display_root.parts if part != anchor)

    @staticmethod
    def _require_primitives() -> None:
        required_flags = (
            getattr(os, "O_DIRECTORY", 0),
            getattr(os, "O_NOFOLLOW", 0),
            getattr(os, "O_EXCL", 0),
        )
        required_functions = (
            os.open,
            os.mkdir,
            os.unlink,
            os.link,
            os.replace,
            os.fchmod,
            os.fstat,
            os.fsync,
            os.read,
            os.write,
            os.dup,
            os.fdopen,
        )
        if (
            not all(required_flags)
            or not all(callable(function) for function in required_functions)
            or not _BASE_DIRFD_SUPPORT
            or not _REPLACE_HAS_DIRFD
            or not callable(getattr(os, "geteuid", None))
            or fcntl is None
            or not callable(getattr(fcntl, "flock", None))
        ):
            raise R002CacheError("unsupported_filesystem_primitives")

    @staticmethod
    def _verify_directory(fd: int, *, owned: bool) -> None:
        try:
            metadata = os.fstat(fd)
        except OSError:
            raise R002CacheError("cache_directory_security") from None
        if not stat.S_ISDIR(metadata.st_mode):
            raise R002CacheError("symlink_or_nondirectory")
        if owned and (metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700):
            raise R002CacheError("cache_directory_security")

    @staticmethod
    def _verify_file(fd: int, *, allow_unlinked: bool = False) -> os.stat_result:
        try:
            metadata = os.fstat(fd)
        except OSError:
            raise R002CacheError("cache_file_security") from None
        expected_links = 0 if allow_unlinked else 1
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != expected_links
        ):
            raise R002CacheError("cache_file_security")
        return metadata

    @contextmanager
    def _open_root(self) -> Iterator[int]:
        self._require_primitives()
        if not self._root_parts or any(
            part in {"", ".", ".."} or "\x00" in part for part in self._root_parts
        ):
            raise R002CacheError("cache_directory_security")
        start = "/" if self._root_is_absolute else "."
        try:
            current = os.open(start, _DIRECTORY_FLAGS)
        except OSError:
            raise R002CacheError("cache_directory_security") from None
        try:
            for index, component in enumerate(self._root_parts):
                created = False
                try:
                    next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=current)
                except FileNotFoundError:
                    try:
                        os.mkdir(component, 0o700, dir_fd=current)
                        created = True
                    except FileExistsError:
                        pass
                    except OSError:
                        raise R002CacheError("cache_directory_security") from None
                    try:
                        next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=current)
                    except OSError as error:
                        reason = (
                            "symlink_or_nondirectory"
                            if error.errno in {errno.ELOOP, errno.ENOTDIR}
                            else "cache_directory_security"
                        )
                        raise R002CacheError(reason) from None
                except OSError as error:
                    reason = (
                        "symlink_or_nondirectory"
                        if error.errno in {errno.ELOOP, errno.ENOTDIR}
                        else "cache_directory_security"
                    )
                    raise R002CacheError(reason) from None
                previous = current
                current = next_fd
                if not _close_fd(previous):
                    _close_fd(current)
                    raise R002CacheError("cache_directory_security") from None
                is_root = index == len(self._root_parts) - 1
                if created:
                    try:
                        os.fchmod(current, 0o700)
                    except OSError:
                        raise R002CacheError("cache_directory_security") from None
                self._verify_directory(current, owned=created or is_root)
            yield current
        finally:
            if not _close_fd(current):
                raise R002CacheError("cache_state_unknown")

    @contextmanager
    def _open_parent(
        self, root_fd: int, relative_name: str, *, create: bool
    ) -> Iterator[tuple[int, str]]:
        parts = relative_name.split("/")
        current = root_fd
        opened: list[int] = []
        try:
            for component in parts[:-1]:
                created = False
                try:
                    next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=current)
                except FileNotFoundError:
                    if not create:
                        raise R002CacheError("referenced_object_missing") from None
                    try:
                        os.mkdir(component, 0o700, dir_fd=current)
                        created = True
                    except FileExistsError:
                        pass
                    except OSError:
                        raise R002CacheError("cache_directory_security") from None
                    try:
                        next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=current)
                    except OSError as error:
                        reason = (
                            "symlink_or_nondirectory"
                            if error.errno in {errno.ELOOP, errno.ENOTDIR}
                            else "cache_directory_security"
                        )
                        raise R002CacheError(reason) from None
                except OSError as error:
                    reason = (
                        "symlink_or_nondirectory"
                        if error.errno in {errno.ELOOP, errno.ENOTDIR}
                        else "cache_directory_security"
                    )
                    raise R002CacheError(reason) from None
                if created:
                    try:
                        os.fchmod(next_fd, 0o700)
                    except OSError:
                        reason = (
                            "cache_directory_security"
                            if _close_fd(next_fd)
                            else "cache_state_unknown"
                        )
                        raise R002CacheError(reason) from None
                opened.append(next_fd)
                current = next_fd
                self._verify_directory(next_fd, owned=True)
            yield current, parts[-1]
        finally:
            if not _close_all(iter(reversed(opened))):
                raise R002CacheError("cache_state_unknown")

    @staticmethod
    def _read_checked(
        parent_fd: int,
        name: str,
        *,
        max_bytes: int,
        missing_reason: str = "cache_read_failed",
    ) -> bytes:
        try:
            fd = os.open(name, _READ_FLAGS, dir_fd=parent_fd)
        except FileNotFoundError:
            raise R002CacheError(missing_reason) from None
        except OSError:
            raise R002CacheError("cache_file_security") from None
        try:
            before = R002Cache._verify_file(fd)
            if before.st_size > max_bytes:
                raise R002CacheError("cache_file_security")
            chunks: list[bytes] = []
            remaining = max_bytes + 1
            while remaining:
                try:
                    chunk = os.read(fd, min(64 * 1024, remaining))
                except OSError:
                    raise R002CacheError("cache_read_failed") from None
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            after = R002Cache._verify_file(fd)
            if (
                len(data) > max_bytes
                or len(data) != before.st_size
                or (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                    before.st_ctime_ns,
                )
                != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                )
            ):
                raise R002CacheError("cache_file_security")
            return data
        finally:
            if not _close_fd(fd):
                raise R002CacheError("cache_state_unknown")

    @staticmethod
    def _preflight_replace_destination(parent_fd: int, name: str) -> tuple[int, int] | None:
        try:
            fd = os.open(name, _READ_FLAGS, dir_fd=parent_fd)
        except FileNotFoundError:
            return None
        except OSError:
            raise R002CacheError("cache_file_security") from None
        try:
            metadata = R002Cache._verify_file(fd)
            return metadata.st_dev, metadata.st_ino
        finally:
            if not _close_fd(fd):
                raise R002CacheError("cache_state_unknown")

    def _replace_failure_reason(
        self,
        parent_fd: int,
        name: str,
        temp_name: str,
        initial_destination: tuple[int, int] | None,
    ) -> str:
        try:
            current_destination = self._preflight_replace_destination(parent_fd, name)
        except R002CacheError:
            current_destination = object()
        reason = (
            "cache_replace_failed"
            if current_destination == initial_destination
            else "cache_state_unknown"
        )
        try:
            self._unlink_created(parent_fd, temp_name)
        except R002CacheError:
            reason = "cache_state_unknown"
        return reason

    @staticmethod
    def _new_temp(parent_fd: int, *, prefix: str = _TEMP_PREFIX) -> tuple[str, int]:
        name = prefix + secrets.token_hex(16)
        try:
            flags = _SCRATCH_CREATE_FLAGS if prefix == _SCRATCH_PREFIX else _CREATE_FLAGS
            fd = os.open(name, flags, 0o600, dir_fd=parent_fd)
        except FileExistsError:
            raise R002CacheError("temp_collision") from None
        except OSError:
            raise R002CacheError("cache_write_failed") from None
        try:
            os.fchmod(fd, 0o600)
            R002Cache._verify_file(fd)
        except (OSError, R002CacheError):
            closed = _close_fd(fd)
            try:
                os.unlink(name, dir_fd=parent_fd)
            except OSError:
                raise R002CacheError("cache_state_unknown") from None
            if not closed:
                raise R002CacheError("cache_state_unknown") from None
            raise R002CacheError("cache_file_security") from None
        return name, fd

    @staticmethod
    def _unlink_created(parent_fd: int, name: str) -> None:
        try:
            os.unlink(name, dir_fd=parent_fd)
        except FileNotFoundError:
            return
        except OSError:
            raise R002CacheError("cache_state_unknown") from None

    @staticmethod
    def _write_all(fd: int, data: bytes) -> None:
        view = memoryview(data)
        written = 0
        while written < len(view):
            try:
                count = os.write(fd, view[written:])
            except OSError:
                raise R002CacheError("cache_write_failed") from None
            if count <= 0:
                raise R002CacheError("cache_write_failed")
            written += count

    @staticmethod
    def _fsync(fd: int, reason: str = "cache_fsync_failed") -> None:
        try:
            os.fsync(fd)
        except OSError:
            raise R002CacheError(reason) from None

    def _prepare_temp(self, parent_fd: int, data: bytes, max_bytes: int) -> str:
        if len(data) > max_bytes:
            raise R002CacheError("cache_file_security")
        name, fd = self._new_temp(parent_fd)
        try:
            self._write_all(fd, data)
            self._fsync(fd)
            if not _close_fd(fd):
                raise R002CacheError("cache_state_unknown")
            fd = -1
            observed = self._read_checked(parent_fd, name, max_bytes=max_bytes)
            if observed != data:
                raise R002CacheError("cache_write_failed")
            return name
        except BaseException:
            closed = _close_fd(fd) if fd >= 0 else True
            try:
                self._unlink_created(parent_fd, name)
            except R002CacheError:
                raise R002CacheError("cache_state_unknown") from None
            if not closed:
                raise R002CacheError("cache_state_unknown") from None
            raise

    def _publish_no_overwrite(self, parent_fd: int, temp_name: str, final_name: str) -> bool:
        try:
            os.link(
                temp_name,
                final_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            self._unlink_created(parent_fd, temp_name)
            self._fsync(parent_fd, "cache_state_unknown")
            return False
        except OSError:
            self._unlink_created(parent_fd, temp_name)
            raise R002CacheError("cache_write_failed") from None
        try:
            self._unlink_created(parent_fd, temp_name)
            self._fsync(parent_fd, "cache_state_unknown")
        except R002CacheError:
            raise
        return True

    def _immutable_bytes(self, relative_name: str, data: bytes) -> Path:
        limit = _byte_limit(relative_name)
        if len(data) > limit:
            raise R002CacheError("cache_file_security")
        with (
            self._open_root() as root_fd,
            self._open_parent(root_fd, relative_name, create=True) as (parent_fd, name),
        ):
            try:
                existing = self._read_checked(
                    parent_fd, name, max_bytes=limit, missing_reason="referenced_object_missing"
                )
            except R002CacheError as error:
                if error.reason_code != "referenced_object_missing":
                    raise
            else:
                if existing != data:
                    raise R002CacheError("content_address_collision")
                if name != sha256(data).hexdigest():
                    raise R002CacheError("content_address_digest_mismatch")
                return self._display_root / relative_name
            if name != sha256(data).hexdigest():
                raise R002CacheError("content_address_digest_mismatch")
            temp_name = self._prepare_temp(parent_fd, data, limit)
            published = self._publish_no_overwrite(parent_fd, temp_name, name)
            observed = self._read_checked(
                parent_fd, name, max_bytes=limit, missing_reason="cache_state_unknown"
            )
            if observed != data:
                raise R002CacheError(
                    "cache_state_unknown" if published else "content_address_collision"
                )
            return self._display_root / relative_name

    def _replace_bytes(
        self,
        relative_name: str,
        data: bytes,
        *,
        create_only: bool,
    ) -> Path:
        limit = _byte_limit(relative_name)
        if len(data) > limit:
            raise R002CacheError("cache_file_security")
        with (
            self._open_root() as root_fd,
            self._open_parent(root_fd, relative_name, create=True) as (parent_fd, name),
        ):
            initial_destination = self._preflight_replace_destination(parent_fd, name)
            temp_name = self._prepare_temp(parent_fd, data, limit)
            if create_only:
                published = self._publish_no_overwrite(parent_fd, temp_name, name)
                if not published:
                    self._preflight_replace_destination(parent_fd, name)
                    raise R002CacheError("control_already_exists")
                observed = self._read_checked(
                    parent_fd, name, max_bytes=limit, missing_reason="cache_state_unknown"
                )
                if observed != data:
                    raise R002CacheError("cache_state_unknown")
                return self._display_root / relative_name
            replaced = False
            try:
                try:
                    current_destination = self._preflight_replace_destination(parent_fd, name)
                except R002CacheError:
                    self._unlink_created(parent_fd, temp_name)
                    raise
                if current_destination != initial_destination:
                    self._unlink_created(parent_fd, temp_name)
                    raise R002CacheError("cache_replace_failed")
                try:
                    os.replace(
                        temp_name,
                        name,
                        src_dir_fd=parent_fd,
                        dst_dir_fd=parent_fd,
                    )
                    replaced = True
                except OSError:
                    reason = self._replace_failure_reason(
                        parent_fd, name, temp_name, initial_destination
                    )
                    raise R002CacheError(reason) from None
                observed = self._read_checked(
                    parent_fd, name, max_bytes=limit, missing_reason="cache_state_unknown"
                )
                if observed != data:
                    raise R002CacheError("cache_state_unknown")
                self._fsync(parent_fd, "cache_state_unknown")
            except R002CacheError as error:
                if replaced and error.reason_code != "cache_replace_failed":
                    raise R002CacheError("cache_state_unknown") from None
                raise
            return self._display_root / relative_name

    def _read_bytes_internal(
        self,
        relative_name: str,
        *,
        expected_sha256: str | None = None,
        missing_reason: str = "cache_read_failed",
    ) -> bytes:
        with (
            self._open_root() as root_fd,
            self._open_parent(root_fd, relative_name, create=False) as (parent_fd, name),
        ):
            data = self._read_checked(
                parent_fd,
                name,
                max_bytes=_byte_limit(relative_name),
                missing_reason=missing_reason,
            )
        observed_sha256 = sha256(data).hexdigest()
        if relative_name.startswith(_CONTENT_NAMESPACES) and (
            observed_sha256 != relative_name.rsplit("/", maxsplit=1)[-1]
        ):
            raise R002CacheError("referenced_object_mismatch")
        if expected_sha256 is not None and observed_sha256 != expected_sha256:
            raise R002CacheError("referenced_object_mismatch")
        return data

    def _read_model_internal(
        self,
        relative_name: str,
        model_type: type[T],
        *,
        missing_reason: str = "cache_read_failed",
    ) -> T:
        data = self._read_bytes_internal(relative_name, missing_reason=missing_reason)
        value = _decode_canonical_model(data, model_type)
        if relative_name.startswith("reviews/"):
            expected_case_id = relative_name.removeprefix("reviews/").removesuffix(".json")
            if (
                not isinstance(value, ReviewBundle)
                or value.research_context is None
                or value.research_context.case_id != expected_case_id
            ):
                raise R002CacheError("model_validation_failed")
        return value

    def write_bytes(self, relative_name: str, data: bytes) -> Path:
        try:
            relative = _validate_relative_name(relative_name)
            if relative in _RESERVED_MARKERS:
                raise R002CacheError("completion_marker_requires_publish")
            if not relative.startswith(_RAW_NAMESPACES):
                raise R002CacheError("raw_write_requires_content_namespace")
            if type(data) is not bytes:
                raise R002CacheError("cache_write_failed")
            return self._immutable_bytes(relative, data)
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_write_failed")
        except Exception:
            reason = "cache_write_failed"
        del relative_name, data
        _raise_public(reason)

    def write_content_addressed_model(
        self, relative_name: str, value: T, model_type: type[T]
    ) -> Path:
        try:
            relative = _validate_relative_name(relative_name)
            if not relative.startswith("rows/") or model_type is not SWEbenchVerifiedRow:
                raise R002CacheError("model_type_mismatch")
            _, data = _revalidate_instance(value, SWEbenchVerifiedRow)
            path = self._immutable_bytes(relative, data)
            reopened = self._read_model_internal(relative, SWEbenchVerifiedRow)
            if _fixed_canonical_bytes(reopened, SWEbenchVerifiedRow) != data:
                raise R002CacheError("referenced_object_mismatch")
            return path
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_write_failed")
        except Exception:
            reason = "cache_write_failed"
        del relative_name, value, model_type
        _raise_public(reason)

    def _validated_control_bytes(self, relative_name: str, value: BaseModel) -> bytes:
        expected = _model_for_name(relative_name)
        if expected is None:
            if relative_name in _STREAMED_ARTIFACTS:
                raise R002CacheError("streamed_annotation_requires_writer")
            raise R002CacheError("model_type_mismatch")
        validated, data = _revalidate_instance(value, expected)
        if relative_name.startswith("reviews/"):
            expected_case_id = relative_name.removeprefix("reviews/").removesuffix(".json")
            if (
                not isinstance(validated, ReviewBundle)
                or validated.research_context is None
                or validated.research_context.case_id != expected_case_id
            ):
                raise R002CacheError("model_validation_failed")
        return data

    def write_model(self, relative_name: str, value: BaseModel) -> Path:
        """Create one typed control without overwriting any existing control."""
        try:
            relative = _validate_relative_name(relative_name)
            if relative in _RESERVED_MARKERS:
                raise R002CacheError("completion_marker_requires_publish")
            data = self._validated_control_bytes(relative, value)
            path = self._replace_bytes(relative, data, create_only=True)
            try:
                reopened = self._read_model_internal(relative, type(value))
            except R002CacheError:
                raise R002CacheError("cache_state_unknown") from None
            if _fixed_canonical_bytes(reopened, type(value)) != data:
                raise R002CacheError("cache_state_unknown")
            return path
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_write_failed")
        except Exception:
            reason = "cache_write_failed"
        del relative_name, value
        _raise_public(reason)

    def replace_model(self, relative_name: str, value: BaseModel) -> Path:
        """Atomically replace one typed local control, never a completion marker."""
        try:
            relative = _validate_relative_name(relative_name)
            if relative in _RESERVED_MARKERS:
                raise R002CacheError("completion_marker_requires_publish")
            data = self._validated_control_bytes(relative, value)
            path = self._replace_bytes(relative, data, create_only=False)
            expected = _model_for_name(relative)
            if expected is None:
                raise R002CacheError("model_type_mismatch")
            try:
                reopened = self._read_model_internal(relative, expected)
            except R002CacheError:
                raise R002CacheError("cache_state_unknown") from None
            if _fixed_canonical_bytes(reopened, expected) != data:
                raise R002CacheError("cache_state_unknown")
            return path
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_write_failed")
        except Exception:
            reason = "cache_write_failed"
        del relative_name, value
        _raise_public(reason)

    def read_bytes(self, relative_name: str, *, expected_sha256: str | None = None) -> bytes:
        try:
            relative = _validate_relative_name(relative_name)
            if relative in _RESERVED_MARKERS:
                raise R002CacheError("completion_marker_requires_publish")
            if relative in _STREAMED_ARTIFACTS:
                raise R002CacheError("model_type_mismatch")
            if expected_sha256 is not None and (
                type(expected_sha256) is not str
                or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
            ):
                raise R002CacheError("referenced_object_mismatch")
            return self._read_bytes_internal(relative, expected_sha256=expected_sha256)
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_read_failed")
        except Exception:
            reason = "cache_read_failed"
        del relative_name, expected_sha256
        _raise_public(reason)

    def read_model(self, relative_name: str, model_type: type[T]) -> T:
        try:
            relative = _validate_relative_name(relative_name)
            if relative in _RESERVED_MARKERS:
                raise R002CacheError("completion_marker_requires_publish")
            expected: type[BaseModel] | None
            if relative.startswith("rows/"):
                expected = SWEbenchVerifiedRow
            elif relative == "annotation-universe.json":
                expected = R002AnnotationUniverse
            elif relative == "annotation-review.json":
                expected = R002AnnotationReview
            else:
                expected = _model_for_name(relative)
            if model_type is not expected:
                raise R002CacheError("model_type_mismatch")
            if relative == "annotation-review.json":
                with self._annotation_lock():
                    review = self._read_model_internal(relative, R002AnnotationReview)
                    universe = self._read_model_internal(
                        "annotation-universe.json", R002AnnotationUniverse
                    )
                    if (
                        canonical_sha256(universe) != review.annotation_universe_sha256
                        or universe.source_manifest_sha256 != review.source_manifest_sha256
                        or universe.criteria_set_sha256 != review.criteria_set_sha256
                        or universe.candidate_count != len(review.items)
                        or tuple(universe.candidate_keys)
                        != tuple(item.key for item in review.items)
                    ):
                        raise R002CacheError("annotation_pair_mismatch")
                    return review  # type: ignore[return-value]
            return self._read_model_internal(relative, model_type)
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_read_failed")
        except Exception:
            reason = "cache_read_failed"
        del relative_name, model_type
        _raise_public(reason)

    def _verify_criteria_source_index(self, index: R002CriteriaSourceIndex) -> None:
        for case in index.cases:
            relative = f"criteria-sources/{case.problem_statement_sha256}"
            try:
                data = self._read_bytes_internal(
                    relative,
                    expected_sha256=case.problem_statement_sha256,
                    missing_reason="referenced_object_missing",
                )
            except R002CacheError as error:
                if error.reason_code == "referenced_object_missing":
                    raise
                raise R002CacheError("referenced_object_mismatch") from None
            if len(data) != case.byte_length:
                raise R002CacheError("referenced_object_mismatch")

    def _load_criteria_source_index_internal(self) -> R002CriteriaSourceIndex:
        try:
            index = self._read_model_internal(
                "criteria-source-index.json",
                R002CriteriaSourceIndex,
                missing_reason="completion_marker_missing",
            )
        except R002CacheError as error:
            if error.reason_code == "completion_marker_missing":
                raise
            raise R002CacheError("criteria_source_index_mismatch") from None
        self._verify_criteria_source_index(index)
        return index

    def publish_criteria_source_index(self, index: R002CriteriaSourceIndex) -> Path:
        try:
            validated, data = _revalidate_instance(index, R002CriteriaSourceIndex)
            self._verify_criteria_source_index(validated)
            path = self._replace_bytes("criteria-source-index.json", data, create_only=False)
            try:
                reopened = self._load_criteria_source_index_internal()
            except R002CacheError:
                raise R002CacheError("cache_state_unknown") from None
            if reopened != validated:
                raise R002CacheError("cache_state_unknown")
            return path
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_write_failed")
        except Exception:
            reason = "cache_write_failed"
        del index
        _raise_public(reason)

    def load_criteria_source_index(self) -> R002CriteriaSourceIndex:
        try:
            return self._load_criteria_source_index_internal()
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_read_failed")
        except Exception:
            reason = "cache_read_failed"
        _raise_public(reason)

    def _verify_cache_index(self, index: R002CacheIndex) -> None:
        criteria_index = self._load_criteria_source_index_internal()
        if (
            criteria_index.source_sha256 != index.source_sha256
            or criteria_index.manifest_sha256 != index.manifest_sha256
            or tuple((case.case_id, case.problem_statement_sha256) for case in criteria_index.cases)
            != tuple((case.case_id, case.problem_statement_sha256) for case in index.cases)
        ):
            raise R002CacheError("criteria_source_index_mismatch")
        for case in index.cases:
            try:
                row = self._read_model_internal(
                    f"rows/{case.row_sha256}",
                    SWEbenchVerifiedRow,
                    missing_reason="referenced_object_missing",
                )
            except R002CacheError as error:
                if error.reason_code == "referenced_object_missing":
                    raise
                raise R002CacheError("referenced_object_mismatch") from None
            if (
                canonical_sha256(row) != case.row_sha256
                or sha256(row.problem_statement.encode()).hexdigest()
                != case.problem_statement_sha256
                or sha256(row.patch.encode()).hexdigest() != case.patch_sha256
                or sha256(row.test_patch.encode()).hexdigest() != case.test_patch_sha256
            ):
                raise R002CacheError("referenced_object_mismatch")
            for head_file in case.head_files:
                try:
                    data = self._read_bytes_internal(
                        f"head-files/{head_file.content_sha256}",
                        expected_sha256=head_file.content_sha256,
                        missing_reason="referenced_object_missing",
                    )
                except R002CacheError as error:
                    if error.reason_code == "referenced_object_missing":
                        raise
                    raise R002CacheError("referenced_object_mismatch") from None
                if len(data) != head_file.byte_length:
                    raise R002CacheError("referenced_object_mismatch")

    def _load_index_internal(self) -> R002CacheIndex:
        try:
            index = self._read_model_internal(
                "cache-index.json", R002CacheIndex, missing_reason="completion_marker_missing"
            )
        except R002CacheError as error:
            if error.reason_code == "completion_marker_missing":
                raise
            raise R002CacheError("referenced_object_mismatch") from None
        self._verify_cache_index(index)
        return index

    def publish_index(self, index: R002CacheIndex) -> Path:
        try:
            validated, data = _revalidate_instance(index, R002CacheIndex)
            self._verify_cache_index(validated)
            path = self._replace_bytes("cache-index.json", data, create_only=False)
            try:
                reopened = self._load_index_internal()
            except R002CacheError:
                raise R002CacheError("cache_state_unknown") from None
            if reopened != validated:
                raise R002CacheError("cache_state_unknown")
            return path
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_write_failed")
        except Exception:
            reason = "cache_write_failed"
        del index
        _raise_public(reason)

    def load_index(self) -> R002CacheIndex:
        try:
            return self._load_index_internal()
        except R002CacheError as caught:
            reason = _caught_reason(caught, "cache_read_failed")
        except Exception:
            reason = "cache_read_failed"
        _raise_public(reason)

    @contextmanager
    def _annotation_lock(self) -> Iterator[None]:
        with self._open_root() as root_fd:
            fd = -1
            created = False
            try:
                try:
                    fd = os.open(
                        _ANNOTATION_LOCK,
                        os.O_RDWR
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_NOFOLLOW
                        | os.O_CLOEXEC
                        | os.O_NONBLOCK,
                        0o600,
                        dir_fd=root_fd,
                    )
                except FileExistsError:
                    fd = os.open(
                        _ANNOTATION_LOCK,
                        os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                        dir_fd=root_fd,
                    )
                else:
                    created = True
                    os.fchmod(fd, 0o600)
                self._verify_file(fd)
                if created:
                    self._fsync(fd, "writer_lock_failed")
                    self._fsync(root_fd, "writer_lock_failed")
                fcntl.flock(fd, fcntl.LOCK_EX)
            except (OSError, R002CacheError):
                if fd >= 0:
                    _close_fd(fd)
                raise R002CacheError("writer_lock_failed") from None
            try:
                yield
            finally:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    unlocked = False
                else:
                    unlocked = True
                closed = _close_fd(fd)
                if not unlocked or not closed:
                    raise R002CacheError("cache_state_unknown")

    @staticmethod
    def _stream_piece(fd: int, piece: bytes, *, size: int, limit: int) -> int:
        if len(piece) > limit - size:
            raise R002CacheError("annotation_pair_limit")
        R002Cache._write_all(fd, piece)
        return size + len(piece)

    def _stream_replace(
        self,
        relative_name: str,
        model_type: type[T],
        writer: Callable[[int, int], None],
        limit: int,
    ) -> T:
        with self._open_root() as root_fd:
            initial_destination = self._preflight_replace_destination(root_fd, relative_name)
            temp_name, fd = self._new_temp(root_fd)
            created = True
            try:
                writer(fd, limit)
                self._fsync(fd)
                if not _close_fd(fd):
                    raise R002CacheError("cache_state_unknown")
                fd = -1
                data = self._read_checked(root_fd, temp_name, max_bytes=limit)
                value = _decode_canonical_model(data, model_type)
                current_destination = self._preflight_replace_destination(root_fd, relative_name)
                if current_destination != initial_destination:
                    raise R002CacheError("cache_replace_failed")
                try:
                    os.replace(
                        temp_name,
                        relative_name,
                        src_dir_fd=root_fd,
                        dst_dir_fd=root_fd,
                    )
                    created = False
                except OSError:
                    reason = self._replace_failure_reason(
                        root_fd, relative_name, temp_name, initial_destination
                    )
                    created = False
                    raise R002CacheError(reason) from None
                try:
                    reopened_data = self._read_checked(
                        root_fd,
                        relative_name,
                        max_bytes=limit,
                        missing_reason="cache_state_unknown",
                    )
                    reopened = _decode_canonical_model(reopened_data, model_type)
                    self._fsync(root_fd, "cache_state_unknown")
                except R002CacheError:
                    raise R002CacheError("cache_state_unknown") from None
                if reopened != value:
                    raise R002CacheError("cache_state_unknown")
                return reopened
            finally:
                closed = _close_fd(fd) if fd >= 0 else True
                if created:
                    try:
                        self._unlink_created(root_fd, temp_name)
                    except R002CacheError:
                        raise R002CacheError("cache_state_unknown") from None
                if not closed:
                    raise R002CacheError("cache_state_unknown")

    def _write_annotation_universe_internal(
        self,
        *,
        source_manifest_sha256: str,
        criteria_set_sha256: str,
        candidate_count: int,
        ordered_key_factory: Callable[[], Iterator[R002CandidateLineKey]],
    ) -> R002AnnotationUniverse:
        if (
            type(source_manifest_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256) is None
            or type(criteria_set_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", criteria_set_sha256) is None
            or type(candidate_count) is not int
            or not callable(ordered_key_factory)
        ):
            raise R002CacheError("annotation_stream_invalid")
        if candidate_count < 1 or candidate_count > 250000:
            raise R002CacheError("annotation_pair_limit")
        empty = {
            "pack_id": "R-002",
            "classification": "public_engineering_research",
            "eligible_for_stage_1": False,
            "does_not_advance_stage_1": True,
            "target_repository_code_executed": False,
            "source_manifest_sha256": source_manifest_sha256,
            "criteria_set_sha256": criteria_set_sha256,
            "candidate_count": candidate_count,
            "candidate_keys": [],
        }
        template = canonical_json_bytes(empty)
        empty_array = template.index(b"[]")
        prefix = template[: empty_array + 1]
        suffix = template[empty_array + 1 :]

        def writer(fd: int, limit: int) -> None:
            size = self._stream_piece(fd, prefix, size=0, limit=limit)
            previous: tuple[str, str, str, str, int, str] | None = None
            count = 0
            try:
                iterator = iter(ordered_key_factory())
            except BaseException:
                raise R002CacheError("annotation_stream_invalid") from None
            while True:
                try:
                    raw_key = next(iterator)
                except StopIteration:
                    break
                except BaseException:
                    raise R002CacheError("annotation_stream_invalid") from None
                count += 1
                if count > candidate_count:
                    raise R002CacheError("annotation_stream_invalid")
                try:
                    key, data = _revalidate_instance(raw_key, R002CandidateLineKey)
                    order = r002_annotation_key_order(key)
                except R002CacheError:
                    raise R002CacheError("annotation_stream_invalid") from None
                if previous is not None and order <= previous:
                    raise R002CacheError("annotation_stream_invalid")
                if count > 1:
                    size = self._stream_piece(fd, b",", size=size, limit=limit)
                size = self._stream_piece(fd, data, size=size, limit=limit)
                previous = order
            if count != candidate_count:
                raise R002CacheError("annotation_stream_invalid")
            self._stream_piece(fd, suffix, size=size, limit=limit)

        with self._annotation_lock():
            universe = self._stream_replace(
                "annotation-universe.json",
                R002AnnotationUniverse,
                writer,
                R002_ANNOTATION_UNIVERSE_MAX_BYTES,
            )
            reopened = self._read_model_internal("annotation-universe.json", R002AnnotationUniverse)
            if reopened != universe:
                raise R002CacheError("annotation_pair_mismatch")
            return reopened

    def write_annotation_universe(
        self,
        *,
        source_manifest_sha256: str,
        criteria_set_sha256: str,
        candidate_count: int,
        ordered_key_factory: Callable[[], Iterator[R002CandidateLineKey]],
    ) -> R002AnnotationUniverse:
        try:
            return self._write_annotation_universe_internal(
                source_manifest_sha256=source_manifest_sha256,
                criteria_set_sha256=criteria_set_sha256,
                candidate_count=candidate_count,
                ordered_key_factory=ordered_key_factory,
            )
        except R002CacheError as caught:
            reason = _caught_reason(caught, "annotation_stream_invalid")
        except Exception:
            reason = "annotation_stream_invalid"
        del source_manifest_sha256, criteria_set_sha256, candidate_count, ordered_key_factory
        _raise_public(reason)

    def _write_annotation_review_internal(
        self,
        *,
        source_manifest_sha256: str,
        criteria_set_sha256: str,
        annotation_universe_sha256: str,
        candidate_count: int,
        ordered_item_factory: Callable[[], Iterator[R002AnnotationReviewItem]],
    ) -> R002AnnotationReview:
        if (
            type(source_manifest_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", source_manifest_sha256) is None
            or type(criteria_set_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", criteria_set_sha256) is None
            or type(annotation_universe_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", annotation_universe_sha256) is None
            or type(candidate_count) is not int
            or not callable(ordered_item_factory)
        ):
            raise R002CacheError("annotation_pair_mismatch")
        if candidate_count < 1 or candidate_count > 250000:
            raise R002CacheError("annotation_pair_limit")
        with self._annotation_lock():
            universe = self._read_model_internal(
                "annotation-universe.json",
                R002AnnotationUniverse,
                missing_reason="completion_marker_missing",
            )
            if (
                canonical_sha256(universe) != annotation_universe_sha256
                or universe.source_manifest_sha256 != source_manifest_sha256
                or universe.criteria_set_sha256 != criteria_set_sha256
                or universe.candidate_count != candidate_count
            ):
                raise R002CacheError("annotation_pair_mismatch")
            empty = {
                "pack_id": "R-002",
                "classification": "public_engineering_research",
                "eligible_for_stage_1": False,
                "does_not_advance_stage_1": True,
                "target_repository_code_executed": False,
                "source_manifest_sha256": source_manifest_sha256,
                "criteria_set_sha256": criteria_set_sha256,
                "annotation_universe_sha256": annotation_universe_sha256,
                "items": [],
            }
            template = canonical_json_bytes(empty)
            empty_array = template.index(b"[]")
            prefix = template[: empty_array + 1]
            suffix = template[empty_array + 1 :]

            def writer(fd: int, limit: int) -> None:
                size = self._stream_piece(fd, prefix, size=0, limit=limit)
                count = 0
                try:
                    iterator = iter(ordered_item_factory())
                except BaseException:
                    raise R002CacheError("annotation_pair_mismatch") from None
                while True:
                    try:
                        raw_item = next(iterator)
                    except StopIteration:
                        break
                    except BaseException:
                        raise R002CacheError("annotation_pair_mismatch") from None
                    count += 1
                    if count > candidate_count:
                        raise R002CacheError("annotation_pair_mismatch")
                    try:
                        item, data = _revalidate_instance(raw_item, R002AnnotationReviewItem)
                    except R002CacheError:
                        raise R002CacheError("annotation_pair_mismatch") from None
                    if (
                        item.key != universe.candidate_keys[count - 1]
                        or item.relevant is not None
                        or item.reason_code is not None
                    ):
                        raise R002CacheError("annotation_pair_mismatch")
                    if count > 1:
                        size = self._stream_piece(fd, b",", size=size, limit=limit)
                    size = self._stream_piece(fd, data, size=size, limit=limit)
                if count != candidate_count:
                    raise R002CacheError("annotation_pair_mismatch")
                self._stream_piece(fd, suffix, size=size, limit=limit)

            review = self._stream_replace(
                "annotation-review.json",
                R002AnnotationReview,
                writer,
                R002_ANNOTATION_REVIEW_MAX_BYTES,
            )
            current_universe = self._read_model_internal(
                "annotation-universe.json", R002AnnotationUniverse
            )
            current_review = self._read_model_internal(
                "annotation-review.json", R002AnnotationReview
            )
            if (
                canonical_sha256(current_universe) != current_review.annotation_universe_sha256
                or current_universe.candidate_count != len(current_review.items)
                or tuple(current_universe.candidate_keys)
                != tuple(item.key for item in current_review.items)
                or current_review != review
            ):
                raise R002CacheError("annotation_pair_mismatch")
            return current_review

    def write_annotation_review(
        self,
        *,
        source_manifest_sha256: str,
        criteria_set_sha256: str,
        annotation_universe_sha256: str,
        candidate_count: int,
        ordered_item_factory: Callable[[], Iterator[R002AnnotationReviewItem]],
    ) -> R002AnnotationReview:
        try:
            return self._write_annotation_review_internal(
                source_manifest_sha256=source_manifest_sha256,
                criteria_set_sha256=criteria_set_sha256,
                annotation_universe_sha256=annotation_universe_sha256,
                candidate_count=candidate_count,
                ordered_item_factory=ordered_item_factory,
            )
        except R002CacheError as caught:
            reason = _caught_reason(caught, "annotation_pair_mismatch")
        except Exception:
            reason = "annotation_pair_mismatch"
        del (
            source_manifest_sha256,
            criteria_set_sha256,
            annotation_universe_sha256,
            candidate_count,
            ordered_item_factory,
        )
        _raise_public(reason)

    def _open_scratch_internal(self) -> BinaryIO:
        with self._open_root() as root_fd:
            name, fd = self._new_temp(root_fd, prefix=_SCRATCH_PREFIX)
            duplicate = -1
            try:
                self._unlink_created(root_fd, name)
                self._fsync(root_fd, "scratch_failed")
                self._verify_file(fd, allow_unlinked=True)
                duplicate = os.dup(fd)
            except (OSError, R002CacheError):
                closed = _close_fd(fd)
                if duplicate >= 0:
                    closed = _close_fd(duplicate) and closed
                if not closed:
                    raise R002CacheError("scratch_failed") from None
                raise R002CacheError("scratch_failed") from None
            if not _close_fd(fd):
                _close_fd(duplicate)
                raise R002CacheError("scratch_failed") from None
        try:
            return os.fdopen(duplicate, "w+b", buffering=0)
        except Exception:
            _close_fd(duplicate)
            raise R002CacheError("scratch_failed") from None

    @contextmanager
    def open_unlinked_scratch(self) -> ContextManager[BinaryIO]:
        try:
            handle = self._open_scratch_internal()
        except R002CacheError as caught:
            reason = _caught_reason(caught, "scratch_failed")
        except Exception:
            reason = "scratch_failed"
        else:
            try:
                yield handle
            except BaseException:
                with suppress(OSError):
                    handle.close()
                raise
            else:
                try:
                    handle.close()
                except OSError:
                    close_failed = True
                else:
                    close_failed = False
                if close_failed:
                    _raise_public("scratch_failed")
            return
        _raise_public(reason)
