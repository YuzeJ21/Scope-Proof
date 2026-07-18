"""Create-only local storage for validated owner rehearsal records."""

from __future__ import annotations

import errno
import json
import os
import re
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from scopeproof_core.alpha.rehearsal import AlphaRehearsalRecord

_REHEARSAL_ID = re.compile(r"^rehearsal-[0-9a-f]{32}$")
_CLOSE_ON_EXEC = getattr(os, "O_CLOEXEC", 0)
_DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | _CLOSE_ON_EXEC
_FILE_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | _CLOSE_ON_EXEC
_TEMP_OPEN_FLAGS = (
    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | _CLOSE_ON_EXEC
)
_UNSAFE_TRAVERSAL_ERRNOS = {errno.ELOOP, errno.ENOTDIR}


def default_alpha_rehearsal_directory() -> Path:
    """Return the app-owned directory for local owner rehearsals."""
    return Path.home() / ".scopeproof" / "alpha-rehearsals"


class UnsafeAlphaRehearsalStore(ValueError):
    """Raised when a rehearsal root is a symlink or non-directory."""


class JsonAlphaRehearsalStore:
    """Create, load, and list separately classified owner rehearsals."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    @staticmethod
    def _raise_if_unsafe_traversal(error: OSError) -> None:
        if error.errno in _UNSAFE_TRAVERSAL_ERRNOS:
            raise UnsafeAlphaRehearsalStore(
                "alpha-rehearsal directory and existing ancestors must not be "
                "symbolic links or non-directories"
            ) from error

    @classmethod
    def _open_child_directory(
        cls,
        parent_fd: int,
        component: str,
        *,
        create: bool,
    ) -> int:
        try:
            return os.open(component, _DIRECTORY_OPEN_FLAGS, dir_fd=parent_fd)
        except FileNotFoundError:
            if not create:
                raise
            with suppress(FileExistsError):
                os.mkdir(component, mode=0o700, dir_fd=parent_fd)
            try:
                return os.open(component, _DIRECTORY_OPEN_FLAGS, dir_fd=parent_fd)
            except OSError as error:
                cls._raise_if_unsafe_traversal(error)
                raise
        except OSError as error:
            cls._raise_if_unsafe_traversal(error)
            raise

    @contextmanager
    def _open_directory(self, *, create: bool) -> Iterator[int]:
        absolute_directory = Path(os.path.abspath(self.directory))
        current_fd = os.open(absolute_directory.anchor, _DIRECTORY_OPEN_FLAGS)
        try:
            for component in absolute_directory.parts[1:]:
                child_fd = self._open_child_directory(
                    current_fd,
                    component,
                    create=create,
                )
                os.close(current_fd)
                current_fd = child_fd
            yield current_fd
        finally:
            os.close(current_fd)

    @staticmethod
    def _validate_rehearsal_id(rehearsal_id: str) -> str:
        if not _REHEARSAL_ID.fullmatch(rehearsal_id):
            raise ValueError(
                "rehearsal_id must be a deterministic local rehearsal identifier"
            )
        return rehearsal_id

    def _target_name(self, rehearsal_id: str) -> str:
        return f"{self._validate_rehearsal_id(rehearsal_id)}.json"

    def list_rehearsal_ids(self) -> list[str]:
        try:
            with self._open_directory(create=False) as directory_fd:
                rehearsal_ids: list[str] = []
                for name in os.listdir(directory_fd):
                    path = Path(name)
                    if path.suffix != ".json" or not _REHEARSAL_ID.fullmatch(
                        path.stem
                    ):
                        continue
                    try:
                        metadata = os.stat(
                            name,
                            dir_fd=directory_fd,
                            follow_symlinks=False,
                        )
                    except FileNotFoundError:
                        continue
                    if stat.S_ISREG(metadata.st_mode):
                        rehearsal_ids.append(path.stem)
                return sorted(rehearsal_ids)
        except FileNotFoundError:
            return []

    def save(self, record: AlphaRehearsalRecord) -> Path:
        validated = AlphaRehearsalRecord.model_validate(
            record.model_dump(mode="python")
        )
        target_name = self._target_name(validated.rehearsal_id)
        with self._open_directory(create=True) as directory_fd:
            self._write(directory_fd, target_name, validated)
        return self.directory / target_name

    def load(self, rehearsal_id: str) -> AlphaRehearsalRecord:
        target_name = self._target_name(rehearsal_id)
        with self._open_directory(create=False) as directory_fd:
            payload = self._read(directory_fd, target_name)
        validated = AlphaRehearsalRecord.model_validate(payload)
        if validated.rehearsal_id != rehearsal_id:
            raise ValueError("stored rehearsal record does not match requested ID")
        return validated

    @staticmethod
    def _read(directory_fd: int, target_name: str) -> object:
        try:
            record_fd = os.open(target_name, _FILE_OPEN_FLAGS, dir_fd=directory_fd)
        except OSError as error:
            if error.errno in _UNSAFE_TRAVERSAL_ERRNOS:
                raise FileNotFoundError(target_name) from error
            raise
        try:
            if not stat.S_ISREG(os.fstat(record_fd).st_mode):
                raise FileNotFoundError(target_name)
            with os.fdopen(record_fd, "r", encoding="utf-8") as handle:
                record_fd = -1
                return json.load(handle)
        finally:
            if record_fd >= 0:
                os.close(record_fd)

    @staticmethod
    def _open_random_temporary(directory_fd: int, target_name: str) -> tuple[str, int]:
        target_stem = Path(target_name).stem
        for _ in range(128):
            temporary_name = f".{target_stem}-{secrets.token_hex(16)}.tmp"
            try:
                temporary_fd = os.open(
                    temporary_name,
                    _TEMP_OPEN_FLAGS,
                    mode=0o600,
                    dir_fd=directory_fd,
                )
            except FileExistsError:
                continue
            return temporary_name, temporary_fd
        raise FileExistsError("could not allocate an exclusive rehearsal temp file")

    def _write(
        self,
        directory_fd: int,
        target_name: str,
        record: AlphaRehearsalRecord,
    ) -> None:
        serialized = (record.model_dump_json(indent=2) + "\n").encode("utf-8")
        temporary_name, temporary_fd = self._open_random_temporary(
            directory_fd,
            target_name,
        )
        published = False
        try:
            remaining = memoryview(serialized)
            while remaining:
                written = os.write(temporary_fd, remaining)
                if written == 0:
                    raise OSError("failed to write rehearsal record")
                remaining = remaining[written:]
            os.fsync(temporary_fd)
            try:
                os.link(
                    temporary_name,
                    target_name,
                    src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                raise FileExistsError(record.rehearsal_id) from None
            published = True
            os.fsync(directory_fd)
        finally:
            os.close(temporary_fd)
            with suppress(FileNotFoundError):
                os.unlink(temporary_name, dir_fd=directory_fd)
            if published:
                os.fsync(directory_fd)
