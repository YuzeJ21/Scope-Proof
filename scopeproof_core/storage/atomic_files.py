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
    directory_fd: int | None = None


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(_REPARSE_POINT and attributes & _REPARSE_POINT)


def _raise_if_link_or_reparse(path: Path, metadata: os.stat_result) -> None:
    if stat.S_ISLNK(metadata.st_mode) or _is_reparse_point(metadata):
        raise UnsafeAtomicPath(
            f"app-owned path must not traverse a symbolic link or reparse point: {path}"
        )


def ensure_safe_directory(directory: Path, *, create: bool) -> Path:
    """Validate every existing component and optionally create missing directories."""

    absolute = Path(os.path.abspath(directory))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            if not create:
                raise
            with suppress(FileExistsError):
                current.mkdir(mode=0o700)
            metadata = os.lstat(current)
        _raise_if_link_or_reparse(current, metadata)
        if not stat.S_ISDIR(metadata.st_mode):
            raise UnsafeAtomicPath(f"app-owned path component must be a directory: {current}")
    return absolute


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


def read_text_no_follow(path: Path) -> str:
    """Read one regular UTF-8 file without knowingly following a link or reparse point."""

    target = Path(os.path.abspath(path))
    if _DESCRIPTOR_BACKEND_SUPPORTED:
        with _open_directory_descriptor(target.parent, create=False) as directory_fd:
            _require_regular_at(directory_fd, target.name)
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
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise UnsafeAtomicPath(f"app-owned record must be a regular file: {target}")
                with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                    descriptor = -1
                    return handle.read()
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
    ensure_safe_directory(target.parent, create=False)
    parent_identity = _directory_identity(target.parent)
    before = _require_regular_file(target)
    descriptor = os.open(target, os.O_RDONLY | _NO_FOLLOW | _CLOSE_ON_EXEC)
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
        root = ensure_safe_directory(directory, create=False)
    except FileNotFoundError:
        return []
    result: list[Path] = []
    with os.scandir(root) as entries:
        for entry in entries:
            try:
                metadata = entry.stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            if stat.S_ISREG(metadata.st_mode) and not _is_reparse_point(metadata):
                result.append(root / entry.name)
    return result


def _open_private_temporary(parent: Path, stem: str) -> tuple[Path, int]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOSE_ON_EXEC
    bounded_stem = sha256(os.fsencode(stem)).hexdigest()[:16]
    for _ in range(128):
        temporary = parent / f".{bounded_stem}-{secrets.token_hex(16)}.tmp"
        try:
            return temporary, os.open(temporary, flags, 0o600)
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate an exclusive temporary file")


def _open_private_temporary_at(directory_fd: int, stem: str) -> tuple[str, int]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOSE_ON_EXEC
    bounded_stem = sha256(os.fsencode(stem)).hexdigest()[:16]
    for _ in range(128):
        name = f".{bounded_stem}-{secrets.token_hex(16)}.tmp"
        try:
            return name, os.open(name, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate an exclusive temporary file")


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written == 0:
            raise OSError("failed to write complete local record")
        remaining = remaining[written:]
    os.fsync(descriptor)


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


def atomic_create_text(target: Path, text: str) -> Path:
    """Publish UTF-8 text exactly once without replacing an existing destination."""

    target = Path(os.path.abspath(target))
    if _DESCRIPTOR_BACKEND_SUPPORTED:
        with _open_directory_descriptor(target.parent, create=True) as directory_fd:
            try:
                _require_regular_at(directory_fd, target.name)
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError(f"target already exists: {target}")
            temporary, descriptor = _open_private_temporary_at(directory_fd, target.stem)
            try:
                _write_all(descriptor, text.encode("utf-8"))
                expected = os.fstat(descriptor)
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
                published = _require_regular_at(directory_fd, target.name)
                if (expected.st_dev, expected.st_ino) != (published.st_dev, published.st_ino):
                    raise UnsafeAtomicPath("private temporary file changed before publication")
                with suppress(OSError):
                    os.fsync(directory_fd)
                return target
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                with suppress(FileNotFoundError):
                    os.unlink(temporary, dir_fd=directory_fd)
    parent = ensure_safe_directory(target.parent, create=True)
    parent_identity = _directory_identity(parent)
    try:
        _require_regular_file(target)
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(f"target already exists: {target}")
    temporary, descriptor = _open_private_temporary(parent, target.stem)
    try:
        _assert_directory_identity(parent, parent_identity)
        _write_all(descriptor, text.encode("utf-8"))
        expected = os.fstat(descriptor)
        try:
            try:
                os.link(temporary, target, follow_symlinks=False)
            except TypeError:  # pragma: no cover - older Windows Python seam
                os.link(temporary, target)
        except FileExistsError:
            raise FileExistsError(f"target already exists: {target}") from None
        published = _require_regular_file(target)
        if (expected.st_dev, expected.st_ino) != (published.st_dev, published.st_ino):
            raise UnsafeAtomicPath("private temporary file changed before publication")
        _fsync_directory(parent)
        return target
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary)


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
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise UnsafeAtomicPath("mutation claim must be a regular local file")
                _write_all(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
                metadata = os.fstat(directory_fd)
                yield MutationClaim(
                    target=target,
                    parent=target.parent,
                    identity=(metadata.st_dev, metadata.st_ino),
                    directory_fd=directory_fd,
                )
            finally:
                os.close(descriptor)
                with suppress(FileNotFoundError):
                    os.unlink(claim_name, dir_fd=directory_fd)
                with suppress(OSError):
                    os.fsync(directory_fd)
        return
    parent = ensure_safe_directory(target.parent, create=False)
    parent_identity = _directory_identity(parent)
    digest = sha256(os.fsencode(target.name)).hexdigest()
    claim = parent / f".{digest}.claim"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NO_FOLLOW | _CLOSE_ON_EXEC
    try:
        descriptor = os.open(claim, flags, 0o600)
    except FileExistsError:
        raise FileExistsError(f"another process is updating {target.name}") from None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise UnsafeAtomicPath("mutation claim must be a regular local file")
        _write_all(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        _assert_directory_identity(parent, parent_identity)
        yield MutationClaim(target=target, parent=parent, identity=parent_identity)
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(claim)
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
        _require_regular_at(directory_fd, target.name)
        temporary, descriptor = _open_private_temporary_at(directory_fd, target.stem)
        try:
            try:
                _write_all(descriptor, text.encode("utf-8"))
            finally:
                os.close(descriptor)
                descriptor = -1
            _require_regular_at(directory_fd, target.name)
            os.rename(
                temporary,
                target.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            with suppress(OSError):
                os.fsync(directory_fd)
            return target
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=directory_fd)
    parent = ensure_safe_directory(target.parent, create=False)
    parent_identity = claim.identity if claim is not None else _directory_identity(parent)
    _assert_directory_identity(parent, parent_identity)
    _require_regular_file(target)
    temporary, descriptor = _open_private_temporary(parent, target.stem)
    try:
        _assert_directory_identity(parent, parent_identity)
        try:
            _write_all(descriptor, text.encode("utf-8"))
        finally:
            os.close(descriptor)
            descriptor = -1
        _require_regular_file(target)
        os.replace(temporary, target)
        _fsync_directory(parent)
        return target
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        with suppress(FileNotFoundError):
            os.unlink(temporary)
