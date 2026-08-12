"""Portable fail-closed primitives for app-owned local files."""

from __future__ import annotations

import os
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from hashlib import sha256
from pathlib import Path

_CLOSE_ON_EXEC = getattr(os, "O_CLOEXEC", 0)
_NO_FOLLOW = getattr(os, "O_NOFOLLOW", 0)
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


class UnsafeAtomicPath(ValueError):
    """Raised when an app-owned path traverses an unsafe filesystem object."""


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


def read_text_no_follow(path: Path) -> str:
    """Read one regular UTF-8 file without knowingly following a link or reparse point."""

    target = Path(os.path.abspath(path))
    ensure_safe_directory(target.parent, create=False)
    before = _require_regular_file(target)
    descriptor = os.open(target, os.O_RDONLY | _NO_FOLLOW | _CLOSE_ON_EXEC)
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


def list_regular_files(directory: Path) -> list[Path]:
    """List direct regular children without following links or reparse points."""

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
    for _ in range(128):
        temporary = parent / f".{stem}-{secrets.token_hex(16)}.tmp"
        try:
            return temporary, os.open(temporary, flags, 0o600)
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
    descriptor = os.open(
        directory,
        os.O_RDONLY | directory_flag | no_follow_flag | _CLOSE_ON_EXEC,
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_create_text(target: Path, text: str) -> Path:
    """Publish UTF-8 text exactly once without replacing an existing destination."""

    target = Path(os.path.abspath(target))
    parent = ensure_safe_directory(target.parent, create=True)
    try:
        _require_regular_file(target)
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(f"target already exists: {target}")
    temporary, descriptor = _open_private_temporary(parent, target.stem)
    try:
        try:
            _write_all(descriptor, text.encode("utf-8"))
        finally:
            os.close(descriptor)
            descriptor = -1
        try:
            try:
                os.link(temporary, target, follow_symlinks=False)
            except TypeError:  # pragma: no cover - older Windows Python seam
                os.link(temporary, target)
        except FileExistsError:
            raise FileExistsError(f"target already exists: {target}") from None
        _fsync_directory(parent)
        return target
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        with suppress(FileNotFoundError):
            temporary.unlink()


@contextmanager
def exclusive_path_claim(target: Path) -> Iterator[None]:
    """Acquire a fail-closed, process-exclusive claim for one target mutation."""

    target = Path(os.path.abspath(target))
    parent = ensure_safe_directory(target.parent, create=True)
    digest = sha256(target.name.encode("utf-8")).hexdigest()
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
        yield
    finally:
        os.close(descriptor)
        with suppress(FileNotFoundError):
            claim.unlink()
        _fsync_directory(parent)


def atomic_replace_text(target: Path, text: str) -> Path:
    """Replace one existing regular target after its caller acquires a mutation claim."""

    target = Path(os.path.abspath(target))
    parent = ensure_safe_directory(target.parent, create=False)
    _require_regular_file(target)
    temporary, descriptor = _open_private_temporary(parent, target.stem)
    try:
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
            temporary.unlink()
