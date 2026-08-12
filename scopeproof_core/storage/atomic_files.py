"""Portable fail-closed primitives for app-owned local files."""

from __future__ import annotations

import errno
import os
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

_CLOSE_ON_EXEC = getattr(os, "O_CLOEXEC", 0)
_NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_DESCRIPTOR_BACKEND_SUPPORTED = (
    os.name != "nt"
    and bool(_DIRECTORY)
    and bool(_NO_FOLLOW)
    and os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
    and os.stat in os.supports_follow_symlinks
    and os.unlink in os.supports_dir_fd
    and os.link in os.supports_dir_fd
    and os.link in os.supports_follow_symlinks
    and os.rename in os.supports_dir_fd
)


class UnsafeAtomicPath(ValueError):
    """Raised when an app-owned path traverses an unsafe filesystem object."""


@dataclass(frozen=True)
class MutationClaim:
    """Bind one mutation claim to the directory object in which it was acquired."""

    target: Path
    parent: Path
    identity: tuple[int, int]
    record_identity: tuple[int, int]
    directory_fd: int | None = None
    portable_ancestors: tuple[tuple[Path, tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class CreatedFileReceipt:
    """Bind a newly published file to the exact object eligible for rollback."""

    path: Path
    identity: tuple[int, int]
    content_sha256: str
    descriptor_backend: bool
    portable_ancestors: tuple[tuple[Path, tuple[int, int]], ...] = ()


@dataclass(frozen=True)
class _PortableDirectory:
    path: Path
    ancestors: tuple[tuple[Path, tuple[int, int]], ...]


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(_REPARSE_POINT and attributes & _REPARSE_POINT)


def _raise_if_link_or_reparse(path: Path, metadata: os.stat_result) -> None:
    if stat.S_ISLNK(metadata.st_mode) or _is_reparse_point(metadata):
        raise UnsafeAtomicPath(
            f"app-owned path must not traverse a symbolic link or reparse point: {path}"
        )


def _capture_safe_directory(directory: Path, *, create: bool) -> _PortableDirectory:
    absolute = Path(os.path.abspath(directory))
    current = Path(absolute.anchor)
    root_metadata = os.lstat(current)
    _raise_if_link_or_reparse(current, root_metadata)
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise UnsafeAtomicPath(f"app-owned path component must be a directory: {current}")
    ancestors: list[tuple[Path, tuple[int, int]]] = [
        (current, (root_metadata.st_dev, root_metadata.st_ino))
    ]
    created: list[tuple[Path, tuple[int, int]]] = []
    try:
        for component in absolute.parts[1:]:
            current /= component
            try:
                metadata = os.lstat(current)
            except FileNotFoundError:
                if not create:
                    raise
                created_here = False
                try:
                    current.mkdir(mode=0o700)
                    created_here = True
                except FileExistsError:
                    pass
                metadata = os.lstat(current)
                if created_here:
                    created.append((current, (metadata.st_dev, metadata.st_ino)))
            _raise_if_link_or_reparse(current, metadata)
            if not stat.S_ISDIR(metadata.st_mode):
                raise UnsafeAtomicPath(f"app-owned path component must be a directory: {current}")
            ancestors.append((current, (metadata.st_dev, metadata.st_ino)))
        captured = _PortableDirectory(path=absolute, ancestors=tuple(ancestors))
        _assert_portable_directory(captured)
        return captured
    except BaseException:
        for created_path, expected in reversed(created):
            try:
                metadata = os.lstat(created_path)
                _raise_if_link_or_reparse(created_path, metadata)
                if (metadata.st_dev, metadata.st_ino) == expected:
                    created_path.rmdir()
            except (OSError, UnsafeAtomicPath):
                pass
        raise


def _assert_portable_directory(directory: _PortableDirectory) -> None:
    for component, expected in directory.ancestors:
        metadata = os.lstat(component)
        _raise_if_link_or_reparse(component, metadata)
        if not stat.S_ISDIR(metadata.st_mode):
            raise UnsafeAtomicPath(f"app-owned path component must be a directory: {component}")
        if (metadata.st_dev, metadata.st_ino) != expected:
            raise UnsafeAtomicPath("app-owned directory changed during storage operation")


def ensure_safe_directory(directory: Path, *, create: bool) -> Path:
    """Validate every existing component and optionally create missing directories."""

    return _capture_safe_directory(directory, create=create).path


def _require_regular_file(path: Path) -> os.stat_result:
    metadata = os.lstat(path)
    _raise_if_link_or_reparse(path, metadata)
    if not stat.S_ISREG(metadata.st_mode):
        raise UnsafeAtomicPath(f"app-owned record must be a regular file: {path}")
    return metadata


def _directory_identity(directory: Path) -> tuple[int, int]:
    metadata = os.lstat(directory)
    _raise_if_link_or_reparse(directory, metadata)
    if not stat.S_ISDIR(metadata.st_mode):
        raise UnsafeAtomicPath(f"app-owned path component must be a directory: {directory}")
    return metadata.st_dev, metadata.st_ino


def _assert_directory_identity(directory: Path, expected: tuple[int, int]) -> None:
    if _directory_identity(directory) != expected:
        raise UnsafeAtomicPath("app-owned directory changed during storage operation")


def _open_child_directory(parent_fd: int, component: str, *, create: bool) -> int:
    flags = os.O_RDONLY | _DIRECTORY | _NO_FOLLOW | _CLOSE_ON_EXEC
    try:
        return os.open(component, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
        with suppress(FileExistsError):
            os.mkdir(component, mode=0o700, dir_fd=parent_fd)
        try:
            return os.open(component, flags, dir_fd=parent_fd)
        except OSError as error:
            raise UnsafeAtomicPath("app-owned directory changed during creation") from error
    except OSError as error:
        raise UnsafeAtomicPath(
            "app-owned path must not traverse a symbolic link, reparse point, "
            "or non-directory"
        ) from error


@contextmanager
def _open_directory_descriptor(directory: Path, *, create: bool) -> Iterator[int]:
    absolute = Path(os.path.abspath(directory))
    flags = os.O_RDONLY | _DIRECTORY | _NO_FOLLOW | _CLOSE_ON_EXEC
    current_fd = os.open(absolute.anchor, flags)
    try:
        for component in absolute.parts[1:]:
            child_fd = _open_child_directory(current_fd, component, create=create)
            os.close(current_fd)
            current_fd = child_fd
        yield current_fd
    finally:
        os.close(current_fd)


def _require_regular_at(directory_fd: int, name: str) -> os.stat_result:
    metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    _raise_if_link_or_reparse(Path(name), metadata)
    if not stat.S_ISREG(metadata.st_mode):
        raise UnsafeAtomicPath(f"app-owned record must be a regular file: {name}")
    return metadata


def read_text_no_follow(path: Path, *, claim: MutationClaim | None = None) -> str:
    """Read one regular UTF-8 file without knowingly following a link or reparse point."""

    target = Path(os.path.abspath(path))
    if claim is not None and claim.target != target:
        raise UnsafeAtomicPath("mutation claim does not match read target")
    if claim is not None and claim.directory_fd is not None:
        directory_fd = claim.directory_fd
        before = _require_regular_at(directory_fd, target.name)
        if (before.st_dev, before.st_ino) != claim.record_identity:
            raise UnsafeAtomicPath("existing record changed after mutation claim")
        descriptor = os.open(
            target.name,
            os.O_RDONLY | _NO_FOLLOW | _NONBLOCK | _CLOSE_ON_EXEC,
            dir_fd=directory_fd,
        )
        try:
            after = os.fstat(descriptor)
            if not stat.S_ISREG(after.st_mode):
                raise UnsafeAtomicPath(f"app-owned record must be a regular file: {target}")
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise UnsafeAtomicPath("app-owned record changed while it was being opened")
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                descriptor = -1
                return handle.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    if claim is not None:
        _assert_directory_identity(target.parent, claim.identity)
    if _DESCRIPTOR_BACKEND_SUPPORTED:
        with _open_directory_descriptor(target.parent, create=False) as directory_fd:
            before = _require_regular_at(directory_fd, target.name)
            try:
                descriptor = os.open(
                    target.name,
                    os.O_RDONLY | _NO_FOLLOW | _NONBLOCK | _CLOSE_ON_EXEC,
                    dir_fd=directory_fd,
                )
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise UnsafeAtomicPath(
                        f"app-owned record must not be a symbolic link or reparse point: {target}"
                    ) from error
                raise
            try:
                after = os.fstat(descriptor)
                if not stat.S_ISREG(after.st_mode):
                    raise UnsafeAtomicPath(f"app-owned record must be a regular file: {target}")
                if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                    raise UnsafeAtomicPath("app-owned record changed while it was being opened")
                with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                    descriptor = -1
                    return handle.read()
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
    portable_directory = _capture_safe_directory(target.parent, create=False)
    parent_identity = claim.identity if claim is not None else _directory_identity(target.parent)
    _assert_portable_directory(portable_directory)
    _assert_directory_identity(target.parent, parent_identity)
    before = _require_regular_file(target)
    if claim is not None and (before.st_dev, before.st_ino) != claim.record_identity:
        raise UnsafeAtomicPath("existing record changed after mutation claim")
    descriptor = os.open(target, os.O_RDONLY | _NO_FOLLOW | _NONBLOCK | _CLOSE_ON_EXEC)
    try:
        _assert_directory_identity(target.parent, parent_identity)
        after = os.fstat(descriptor)
        if not stat.S_ISREG(after.st_mode):
            raise UnsafeAtomicPath(f"app-owned record must be a regular file: {target}")
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise UnsafeAtomicPath("app-owned record changed while it was being opened")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def list_regular_files(directory: Path) -> list[Path]:
    """List direct regular children without following links or reparse points."""

    absolute = Path(os.path.abspath(directory))
    if _DESCRIPTOR_BACKEND_SUPPORTED:
        try:
            with _open_directory_descriptor(absolute, create=False) as directory_fd:
                result: list[Path] = []
                for name in os.listdir(directory_fd):
                    try:
                        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    if stat.S_ISREG(metadata.st_mode) and not _is_reparse_point(metadata):
                        result.append(absolute / name)
                return result
        except FileNotFoundError:
            return []
    try:
        portable_directory = _capture_safe_directory(directory, create=False)
    except FileNotFoundError:
        return []
    root = portable_directory.path
    _assert_portable_directory(portable_directory)
    result: list[Path] = []
    with os.scandir(root) as entries:
        for entry in entries:
            try:
                metadata = entry.stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISREG(metadata.st_mode) and not _is_reparse_point(metadata):
                result.append(root / entry.name)
    _assert_portable_directory(portable_directory)
    return result


def _open_private_temporary(
    parent: Path, stem: str
) -> tuple[Path, int, tuple[int, int]]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOSE_ON_EXEC
    bounded_stem = sha256(os.fsencode(stem)).hexdigest()[:16]
    for _ in range(128):
        temporary = parent / f".{bounded_stem}-{secrets.token_hex(16)}.tmp"
        try:
            descriptor = os.open(temporary, flags, 0o600)
        except FileExistsError:
            continue
        try:
            metadata = os.fstat(descriptor)
        except BaseException:
            try:
                interrupted = _require_regular_file(temporary)
            except (OSError, UnsafeAtomicPath):
                os.close(descriptor)
            else:
                identity = (interrupted.st_dev, interrupted.st_ino)
                os.close(descriptor)
                _quarantine_and_remove_path(
                    temporary,
                    identity,
                    changed_message="private temporary changed during failed setup cleanup",
                )
            raise
        return temporary, descriptor, (metadata.st_dev, metadata.st_ino)
    raise FileExistsError("could not allocate an exclusive temporary file")


def _open_private_temporary_at(
    directory_fd: int, stem: str
) -> tuple[str, int, tuple[int, int]]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOSE_ON_EXEC
    bounded_stem = sha256(os.fsencode(stem)).hexdigest()[:16]
    for _ in range(128):
        name = f".{bounded_stem}-{secrets.token_hex(16)}.tmp"
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            continue
        try:
            metadata = os.fstat(descriptor)
        except BaseException:
            try:
                interrupted = _require_regular_at(directory_fd, name)
            except (OSError, UnsafeAtomicPath):
                os.close(descriptor)
            else:
                identity = (interrupted.st_dev, interrupted.st_ino)
                os.close(descriptor)
                _quarantine_and_remove_at(
                    directory_fd,
                    name,
                    identity,
                    changed_message="private temporary changed during failed setup cleanup",
                )
            raise
        return name, descriptor, (metadata.st_dev, metadata.st_ino)
    raise FileExistsError("could not allocate an exclusive temporary file")


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written == 0:
            raise OSError("failed to write complete local record")
        remaining = remaining[written:]
    os.fsync(descriptor)


def _same_file(metadata: os.stat_result, expected: tuple[int, int]) -> bool:
    return (metadata.st_dev, metadata.st_ino) == expected


def _quarantine_name(stem: str) -> str:
    bounded_stem = sha256(os.fsencode(stem)).hexdigest()[:16]
    return f".{bounded_stem}-{secrets.token_hex(16)}.rollback"


def _create_backup_at(
    directory_fd: int, target: str, expected: tuple[int, int]
) -> str:
    for _ in range(128):
        backup = _quarantine_name(target)
        try:
            os.link(
                target,
                backup,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            continue
        except BaseException:
            try:
                metadata = _require_regular_at(directory_fd, backup)
            except (OSError, UnsafeAtomicPath):
                pass
            else:
                if _same_file(metadata, expected):
                    _quarantine_and_remove_at(
                        directory_fd,
                        backup,
                        expected,
                        changed_message=(
                            "existing record changed during failed backup cleanup"
                        ),
                    )
            raise
        try:
            metadata = _require_regular_at(directory_fd, backup)
        except BaseException:
            try:
                interrupted = _require_regular_at(directory_fd, backup)
            except (OSError, UnsafeAtomicPath):
                pass
            else:
                if _same_file(interrupted, expected):
                    _quarantine_and_remove_at(
                        directory_fd,
                        backup,
                        expected,
                        changed_message=(
                            "existing record changed during failed backup cleanup"
                        ),
                    )
            raise
        if not _same_file(metadata, expected):
            _quarantine_and_remove_at(
                directory_fd,
                backup,
                expected,
                changed_message="existing record changed while backup was created",
            )
        return backup
    raise FileExistsError("could not allocate replacement backup")


def _create_backup_path(target: Path, expected: tuple[int, int]) -> Path:
    for _ in range(128):
        backup = target.parent / _quarantine_name(target.name)
        try:
            try:
                os.link(target, backup, follow_symlinks=False)
            except (TypeError, NotImplementedError):  # pragma: no cover - platform seam
                os.link(target, backup)
        except FileExistsError:
            continue
        except BaseException:
            try:
                metadata = _require_regular_file(backup)
            except (OSError, UnsafeAtomicPath):
                pass
            else:
                if _same_file(metadata, expected):
                    _quarantine_and_remove_path(
                        backup,
                        expected,
                        changed_message=(
                            "existing record changed during failed backup cleanup"
                        ),
                    )
            raise
        try:
            metadata = _require_regular_file(backup)
        except BaseException:
            try:
                interrupted = _require_regular_file(backup)
            except (OSError, UnsafeAtomicPath):
                pass
            else:
                if _same_file(interrupted, expected):
                    _quarantine_and_remove_path(
                        backup,
                        expected,
                        changed_message=(
                            "existing record changed during failed backup cleanup"
                        ),
                    )
            raise
        if not _same_file(metadata, expected):
            _quarantine_and_remove_path(
                backup,
                expected,
                changed_message="existing record changed while backup was created",
            )
        return backup
    raise FileExistsError("could not allocate replacement backup")


def _restore_quarantined_at(directory_fd: int, quarantine: str, target: str) -> None:
    try:
        os.link(
            quarantine,
            target,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except FileExistsError:
        return
    os.unlink(quarantine, dir_fd=directory_fd)


def _sha256_regular_at(
    directory_fd: int, name: str, expected: tuple[int, int]
) -> str:
    metadata = _require_regular_at(directory_fd, name)
    if not _same_file(metadata, expected):
        raise UnsafeAtomicPath("app-owned record changed while its content was verified")
    descriptor = os.open(
        name,
        os.O_RDONLY | _NO_FOLLOW | _NONBLOCK | _CLOSE_ON_EXEC,
        dir_fd=directory_fd,
    )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not _same_file(opened, expected):
            raise UnsafeAtomicPath("app-owned record changed while its content was verified")
        digest = sha256()
        while chunk := os.read(descriptor, 65536):
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise UnsafeAtomicPath("app-owned record changed while its content was verified")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _quarantine_and_remove_at(
    directory_fd: int,
    target: str,
    expected: tuple[int, int],
    *,
    changed_message: str,
    expected_sha256: str | None = None,
) -> None:
    for _ in range(128):
        quarantine = _quarantine_name(target)
        try:
            os.rename(
                target,
                quarantine,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
        except FileExistsError:
            continue
        except BaseException:
            try:
                interrupted = _require_regular_at(directory_fd, quarantine)
                owned = _same_file(interrupted, expected)
                if owned and expected_sha256 is not None:
                    owned = (
                        _sha256_regular_at(directory_fd, quarantine, expected)
                        == expected_sha256
                    )
            except (OSError, UnsafeAtomicPath):
                owned = False
            if owned:
                os.unlink(quarantine, dir_fd=directory_fd)
            raise
        break
    else:
        raise FileExistsError("could not allocate rollback quarantine")
    metadata = _require_regular_at(directory_fd, quarantine)
    if not _same_file(metadata, expected):
        _restore_quarantined_at(directory_fd, quarantine, target)
        raise UnsafeAtomicPath(changed_message)
    if expected_sha256 is not None:
        try:
            if _sha256_regular_at(directory_fd, quarantine, expected) != expected_sha256:
                raise UnsafeAtomicPath(changed_message)
        except BaseException:
            _restore_quarantined_at(directory_fd, quarantine, target)
            raise
    os.unlink(quarantine, dir_fd=directory_fd)


def _restore_quarantined_path(quarantine: Path, target: Path) -> None:
    try:
        try:
            os.link(quarantine, target, follow_symlinks=False)
        except (TypeError, NotImplementedError):  # pragma: no cover - platform seam
            os.link(quarantine, target)
    except FileExistsError:
        return
    os.unlink(quarantine)


def _sha256_regular_path(path: Path, expected: tuple[int, int]) -> str:
    metadata = _require_regular_file(path)
    if not _same_file(metadata, expected):
        raise UnsafeAtomicPath("app-owned record changed while its content was verified")
    descriptor = os.open(path, os.O_RDONLY | _NO_FOLLOW | _NONBLOCK | _CLOSE_ON_EXEC)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not _same_file(opened, expected):
            raise UnsafeAtomicPath("app-owned record changed while its content was verified")
        digest = sha256()
        while chunk := os.read(descriptor, 65536):
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise UnsafeAtomicPath("app-owned record changed while its content was verified")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _quarantine_and_remove_path(
    target: Path,
    expected: tuple[int, int],
    *,
    changed_message: str,
    expected_sha256: str | None = None,
) -> None:
    for _ in range(128):
        quarantine = target.parent / _quarantine_name(target.name)
        try:
            os.rename(target, quarantine)
        except FileExistsError:
            continue
        except BaseException:
            try:
                interrupted = _require_regular_file(quarantine)
                owned = _same_file(interrupted, expected)
                if owned and expected_sha256 is not None:
                    owned = (
                        _sha256_regular_path(quarantine, expected)
                        == expected_sha256
                    )
            except (OSError, UnsafeAtomicPath):
                owned = False
            if owned:
                os.unlink(quarantine)
            raise
        break
    else:
        raise FileExistsError("could not allocate rollback quarantine")
    metadata = _require_regular_file(quarantine)
    if not _same_file(metadata, expected):
        _restore_quarantined_path(quarantine, target)
        raise UnsafeAtomicPath(changed_message)
    if expected_sha256 is not None:
        try:
            if _sha256_regular_path(quarantine, expected) != expected_sha256:
                raise UnsafeAtomicPath(changed_message)
        except BaseException:
            _restore_quarantined_path(quarantine, target)
            raise
    os.unlink(quarantine)


def _fsync_directory(directory: Path) -> None:
    directory_flag = getattr(os, "O_DIRECTORY", None)
    no_follow_flag = getattr(os, "O_NOFOLLOW", None)
    if directory_flag is None or no_follow_flag is None:
        return
    try:
        descriptor = os.open(
            directory,
            os.O_RDONLY | directory_flag | no_follow_flag | _CLOSE_ON_EXEC,
        )
    except OSError:
        return
    try:
        with suppress(OSError):
            os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_create_text_with_receipt(target: Path, text: str) -> CreatedFileReceipt:
    """Publish UTF-8 text exactly once and return its rollback identity."""

    target = Path(os.path.abspath(target))
    payload = text.encode("utf-8")
    content_sha256 = sha256(payload).hexdigest()
    if _DESCRIPTOR_BACKEND_SUPPORTED:
        with _open_directory_descriptor(target.parent, create=True) as directory_fd:
            committed = False
            try:
                _require_regular_at(directory_fd, target.name)
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError(f"target already exists: {target}")
            temporary, descriptor, temporary_identity = _open_private_temporary_at(
                directory_fd, target.stem
            )
            published_identity: tuple[int, int] | None = None
            try:
                _write_all(descriptor, payload)
                expected = os.fstat(descriptor)
                try:
                    os.close(descriptor)
                finally:
                    descriptor = -1
                try:
                    os.link(
                        temporary,
                        target.name,
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                except FileExistsError:
                    raise FileExistsError(f"target already exists: {target}") from None
                except BaseException:
                    try:
                        interrupted_publication = _require_regular_at(
                            directory_fd, target.name
                        )
                    except (OSError, UnsafeAtomicPath):
                        pass
                    else:
                        interrupted_identity = (
                            interrupted_publication.st_dev,
                            interrupted_publication.st_ino,
                        )
                        if interrupted_identity == (expected.st_dev, expected.st_ino):
                            published_identity = interrupted_identity
                    raise
                published_identity = (expected.st_dev, expected.st_ino)
                published = _require_regular_at(directory_fd, target.name)
                if (expected.st_dev, expected.st_ino) != (published.st_dev, published.st_ino):
                    raise UnsafeAtomicPath("private temporary file changed before publication")
                committed = True
                with suppress(OSError):
                    os.fsync(directory_fd)
                return CreatedFileReceipt(
                    path=target,
                    identity=(published.st_dev, published.st_ino),
                    content_sha256=content_sha256,
                    descriptor_backend=True,
                )
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                publication_cleanup_error: OSError | UnsafeAtomicPath | None = None
                if not committed and published_identity is not None:
                    try:
                        _quarantine_and_remove_at(
                            directory_fd,
                            target.name,
                            published_identity,
                            changed_message=(
                                "published file changed during failed create cleanup"
                            ),
                        )
                    except FileNotFoundError:
                        pass
                    except (OSError, UnsafeAtomicPath) as error:
                        publication_cleanup_error = error
                try:
                    _quarantine_and_remove_at(
                        directory_fd,
                        temporary,
                        temporary_identity,
                        changed_message="private temporary file changed before cleanup",
                    )
                except FileNotFoundError:
                    pass
                except (OSError, UnsafeAtomicPath):
                    if not committed:
                        raise
                if publication_cleanup_error is not None:
                    raise publication_cleanup_error
    portable_directory = _capture_safe_directory(target.parent, create=True)
    parent = portable_directory.path
    parent_identity = _directory_identity(parent)
    committed = False
    try:
        _require_regular_file(target)
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(f"target already exists: {target}")
    temporary, descriptor, temporary_identity = _open_private_temporary(parent, target.stem)
    published_identity: tuple[int, int] | None = None
    try:
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        _write_all(descriptor, payload)
        expected = os.fstat(descriptor)
        try:
            os.close(descriptor)
        finally:
            descriptor = -1
        try:
            try:
                _assert_portable_directory(portable_directory)
                _assert_directory_identity(parent, parent_identity)
                os.link(temporary, target, follow_symlinks=False)
            except (TypeError, NotImplementedError):  # pragma: no cover - platform seam
                os.link(temporary, target)
        except FileExistsError:
            raise FileExistsError(f"target already exists: {target}") from None
        except BaseException:
            try:
                interrupted_publication = _require_regular_file(target)
            except (OSError, UnsafeAtomicPath):
                pass
            else:
                interrupted_identity = (
                    interrupted_publication.st_dev,
                    interrupted_publication.st_ino,
                )
                if interrupted_identity == (expected.st_dev, expected.st_ino):
                    published_identity = interrupted_identity
            raise
        published_identity = (expected.st_dev, expected.st_ino)
        published = _require_regular_file(target)
        if (expected.st_dev, expected.st_ino) != (published.st_dev, published.st_ino):
            raise UnsafeAtomicPath("private temporary file changed before publication")
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        committed = True
        _fsync_directory(parent)
        return CreatedFileReceipt(
            path=target,
            identity=(published.st_dev, published.st_ino),
            content_sha256=content_sha256,
            descriptor_backend=False,
            portable_ancestors=portable_directory.ancestors,
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        publication_cleanup_error: OSError | UnsafeAtomicPath | None = None
        if not committed and published_identity is not None:
            try:
                _quarantine_and_remove_path(
                    target,
                    published_identity,
                    changed_message="published file changed during failed create cleanup",
                )
            except FileNotFoundError:
                pass
            except (OSError, UnsafeAtomicPath) as error:
                publication_cleanup_error = error
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        try:
            _quarantine_and_remove_path(
                temporary,
                temporary_identity,
                changed_message="private temporary file changed before cleanup",
            )
        except FileNotFoundError:
            pass
        except (OSError, UnsafeAtomicPath):
            if not committed:
                raise
        if publication_cleanup_error is not None:
            raise publication_cleanup_error


def atomic_create_text(target: Path, text: str) -> Path:
    """Publish UTF-8 text exactly once without replacing an existing destination."""

    return atomic_create_text_with_receipt(target, text).path


def rollback_created_file(receipt: CreatedFileReceipt) -> None:
    """Remove only the exact file published by a prior create receipt."""

    target = Path(os.path.abspath(receipt.path))
    if target != receipt.path:
        raise UnsafeAtomicPath("created-file receipt path is not absolute")
    if receipt.descriptor_backend:
        with _open_directory_descriptor(target.parent, create=False) as directory_fd:
            metadata = _require_regular_at(directory_fd, target.name)
            if (metadata.st_dev, metadata.st_ino) != receipt.identity:
                raise UnsafeAtomicPath("published file changed before rollback")
            _quarantine_and_remove_at(
                directory_fd,
                target.name,
                receipt.identity,
                changed_message="published file changed before rollback",
                expected_sha256=receipt.content_sha256,
            )
            with suppress(OSError):
                os.fsync(directory_fd)
        return
    portable_directory = _PortableDirectory(
        path=target.parent,
        ancestors=receipt.portable_ancestors,
    )
    _assert_portable_directory(portable_directory)
    metadata = _require_regular_file(target)
    if (metadata.st_dev, metadata.st_ino) != receipt.identity:
        raise UnsafeAtomicPath("published file changed before rollback")
    _assert_portable_directory(portable_directory)
    _quarantine_and_remove_path(
        target,
        receipt.identity,
        changed_message="published file changed before rollback",
        expected_sha256=receipt.content_sha256,
    )
    _fsync_directory(target.parent)


@contextmanager
def exclusive_path_claim(target: Path) -> Iterator[MutationClaim]:
    """Acquire a fail-closed, process-exclusive claim for one target mutation."""

    target = Path(os.path.abspath(target))
    if _DESCRIPTOR_BACKEND_SUPPORTED:
        with _open_directory_descriptor(target.parent, create=False) as directory_fd:
            digest = sha256(os.fsencode(target.name)).hexdigest()
            claim_name = f".{digest}.claim"
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOSE_ON_EXEC
            try:
                descriptor = os.open(claim_name, flags, 0o600, dir_fd=directory_fd)
            except FileExistsError:
                raise FileExistsError(f"another process is updating {target.name}") from None
            claim_identity: tuple[int, int] | None = None
            try:
                try:
                    claim_metadata = os.fstat(descriptor)
                except BaseException:
                    try:
                        interrupted_claim = _require_regular_at(directory_fd, claim_name)
                    except (OSError, UnsafeAtomicPath):
                        pass
                    else:
                        claim_identity = (
                            interrupted_claim.st_dev,
                            interrupted_claim.st_ino,
                        )
                    raise
                claim_identity = (claim_metadata.st_dev, claim_metadata.st_ino)
                record_metadata = _require_regular_at(directory_fd, target.name)
                record_identity = (record_metadata.st_dev, record_metadata.st_ino)
                if not stat.S_ISREG(claim_metadata.st_mode):
                    raise UnsafeAtomicPath("mutation claim must be a regular local file")
                _write_all(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
                metadata = os.fstat(directory_fd)
                yield MutationClaim(
                    target=target,
                    parent=target.parent,
                    identity=(metadata.st_dev, metadata.st_ino),
                    record_identity=record_identity,
                    directory_fd=directory_fd,
                )
            finally:
                os.close(descriptor)
                if claim_identity is not None:
                    with suppress(OSError):
                        _quarantine_and_remove_at(
                            directory_fd,
                            claim_name,
                            claim_identity,
                            changed_message="mutation claim changed before cleanup",
                        )
                with suppress(OSError):
                    os.fsync(directory_fd)
        return
    portable_directory = _capture_safe_directory(target.parent, create=False)
    parent = portable_directory.path
    parent_identity = _directory_identity(parent)
    digest = sha256(os.fsencode(target.name)).hexdigest()
    claim = parent / f".{digest}.claim"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOSE_ON_EXEC
    try:
        descriptor = os.open(claim, flags, 0o600)
    except FileExistsError:
        raise FileExistsError(f"another process is updating {target.name}") from None
    claim_identity = None
    try:
        try:
            claim_metadata = os.fstat(descriptor)
        except BaseException:
            try:
                interrupted_claim = _require_regular_file(claim)
            except (OSError, UnsafeAtomicPath):
                pass
            else:
                claim_identity = (interrupted_claim.st_dev, interrupted_claim.st_ino)
            raise
        claim_identity = (claim_metadata.st_dev, claim_metadata.st_ino)
        record_metadata = _require_regular_file(target)
        record_identity = (record_metadata.st_dev, record_metadata.st_ino)
        if not stat.S_ISREG(claim_metadata.st_mode):
            raise UnsafeAtomicPath("mutation claim must be a regular local file")
        _write_all(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        yield MutationClaim(
            target=target,
            parent=parent,
            identity=parent_identity,
            record_identity=record_identity,
            portable_ancestors=portable_directory.ancestors,
        )
    finally:
        os.close(descriptor)
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        if claim_identity is not None:
            with suppress(OSError):
                _quarantine_and_remove_path(
                    claim,
                    claim_identity,
                    changed_message="mutation claim changed before cleanup",
                )
        _fsync_directory(parent)


def atomic_replace_text(
    target: Path, text: str, *, claim: MutationClaim | None = None
) -> Path:
    """Replace one existing regular target after its caller acquires a mutation claim."""

    target = Path(os.path.abspath(target))
    if claim is not None and claim.target != target:
        raise UnsafeAtomicPath("mutation claim does not match replacement target")
    if claim is not None and claim.directory_fd is not None:
        directory_fd = claim.directory_fd
        existing = _require_regular_at(directory_fd, target.name)
        existing_identity = (existing.st_dev, existing.st_ino)
        if existing_identity != claim.record_identity:
            raise UnsafeAtomicPath("existing record changed after mutation claim")
        temporary, descriptor, temporary_identity = _open_private_temporary_at(
            directory_fd, target.stem
        )
        backup = ""
        published = False
        committed = False
        preserve_backup = False
        try:
            backup = _create_backup_at(directory_fd, target.name, existing_identity)
            _write_all(descriptor, text.encode("utf-8"))
            expected = os.fstat(descriptor)
            try:
                os.close(descriptor)
            finally:
                descriptor = -1
            current = _require_regular_at(directory_fd, target.name)
            if not _same_file(current, existing_identity):
                preserve_backup = True
                raise UnsafeAtomicPath("existing record changed before replacement")
            os.rename(
                temporary,
                target.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            published = True
            replacement = _require_regular_at(directory_fd, target.name)
            if not _same_file(replacement, (expected.st_dev, expected.st_ino)):
                raise UnsafeAtomicPath("private temporary file changed before replacement")
            committed = True
            with suppress(OSError):
                os.fsync(directory_fd)
            return target
        except BaseException:
            if not published:
                try:
                    interrupted_replacement = _require_regular_at(
                        directory_fd, target.name
                    )
                except (OSError, UnsafeAtomicPath):
                    pass
                else:
                    published = _same_file(interrupted_replacement, temporary_identity)
            if published and backup:
                try:
                    backup_metadata = _require_regular_at(directory_fd, backup)
                    if not _same_file(backup_metadata, existing_identity):
                        preserve_backup = True
                        raise UnsafeAtomicPath("replacement backup changed before rollback")
                    _quarantine_and_remove_at(
                        directory_fd,
                        target.name,
                        temporary_identity,
                        changed_message="replacement changed before rollback",
                    )
                except BaseException:
                    preserve_backup = True
                    raise
                try:
                    os.rename(
                        backup,
                        target.name,
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                    )
                except BaseException:
                    preserve_backup = True
                    raise
                backup = ""
            raise
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                _quarantine_and_remove_at(
                    directory_fd,
                    temporary,
                    temporary_identity,
                    changed_message="private temporary file changed before cleanup",
                )
            except FileNotFoundError:
                pass
            except (OSError, UnsafeAtomicPath):
                if not committed:
                    raise
            if backup and not preserve_backup:
                try:
                    _quarantine_and_remove_at(
                        directory_fd,
                        backup,
                        existing_identity,
                        changed_message="replacement backup changed before cleanup",
                    )
                except (OSError, UnsafeAtomicPath):
                    if not committed:
                        raise
    portable_directory = _capture_safe_directory(target.parent, create=False)
    if claim is not None and claim.portable_ancestors:
        portable_directory = _PortableDirectory(
            path=claim.parent,
            ancestors=claim.portable_ancestors,
        )
    parent = portable_directory.path
    parent_identity = claim.identity if claim is not None else _directory_identity(parent)
    _assert_directory_identity(parent, parent_identity)
    existing = _require_regular_file(target)
    existing_identity = (existing.st_dev, existing.st_ino)
    if claim is not None and existing_identity != claim.record_identity:
        raise UnsafeAtomicPath("existing record changed after mutation claim")
    temporary, descriptor, temporary_identity = _open_private_temporary(parent, target.stem)
    backup: Path | None = None
    published = False
    committed = False
    preserve_backup = False
    try:
        backup = _create_backup_path(target, existing_identity)
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        try:
            _write_all(descriptor, text.encode("utf-8"))
        finally:
            try:
                os.close(descriptor)
            finally:
                descriptor = -1
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        current = _require_regular_file(target)
        if not _same_file(current, existing_identity):
            preserve_backup = True
            raise UnsafeAtomicPath("existing record changed before replacement")
        expected = _require_regular_file(temporary)
        if not _same_file(expected, temporary_identity):
            raise UnsafeAtomicPath("private temporary file changed before replacement")
        os.replace(temporary, target)
        published = True
        replacement = _require_regular_file(target)
        if not _same_file(replacement, (expected.st_dev, expected.st_ino)):
            raise UnsafeAtomicPath("private temporary file changed before replacement")
        _assert_portable_directory(portable_directory)
        _assert_directory_identity(parent, parent_identity)
        committed = True
        _fsync_directory(parent)
        return target
    except BaseException:
        if not published:
            try:
                interrupted_replacement = _require_regular_file(target)
            except (OSError, UnsafeAtomicPath):
                pass
            else:
                published = _same_file(interrupted_replacement, temporary_identity)
        if published and backup is not None:
            _assert_portable_directory(portable_directory)
            _assert_directory_identity(parent, parent_identity)
            try:
                backup_metadata = _require_regular_file(backup)
                if not _same_file(backup_metadata, existing_identity):
                    preserve_backup = True
                    raise UnsafeAtomicPath("replacement backup changed before rollback")
                _quarantine_and_remove_path(
                    target,
                    temporary_identity,
                    changed_message="replacement changed before rollback",
                )
            except BaseException:
                preserve_backup = True
                raise
            try:
                os.replace(backup, target)
            except BaseException:
                preserve_backup = True
                raise
            backup = None
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        cleanup_safe = True
        try:
            _assert_portable_directory(portable_directory)
            _assert_directory_identity(parent, parent_identity)
        except (OSError, UnsafeAtomicPath):
            cleanup_safe = False
        if cleanup_safe:
            temporary_cleanup_error: OSError | UnsafeAtomicPath | None = None
            try:
                _quarantine_and_remove_path(
                    temporary,
                    temporary_identity,
                    changed_message="private temporary file changed before cleanup",
                )
            except FileNotFoundError:
                pass
            except (OSError, UnsafeAtomicPath) as error:
                if not committed:
                    temporary_cleanup_error = error
            if backup is not None and not preserve_backup:
                try:
                    _quarantine_and_remove_path(
                        backup,
                        existing_identity,
                        changed_message="replacement backup changed before cleanup",
                    )
                except FileNotFoundError:
                    pass
                except (OSError, UnsafeAtomicPath):
                    if not committed:
                        raise
            if temporary_cleanup_error is not None:
                raise temporary_cleanup_error
