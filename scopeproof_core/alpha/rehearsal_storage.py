"""Create-only local storage for validated owner rehearsal records."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from scopeproof_core.alpha.rehearsal import AlphaRehearsalRecord

_REHEARSAL_ID = re.compile(r"^rehearsal-[0-9a-f]{32}$")


def default_alpha_rehearsal_directory() -> Path:
    """Return the app-owned directory for local owner rehearsals."""
    return Path.home() / ".scopeproof" / "alpha-rehearsals"


class UnsafeAlphaRehearsalStore(ValueError):
    """Raised when a rehearsal root is a symlink or non-directory."""


class JsonAlphaRehearsalStore:
    """Create, load, and list separately classified owner rehearsals."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _require_safe_directory(self) -> None:
        absolute_directory = Path(os.path.abspath(self.directory))
        if any(
            component.is_symlink()
            for component in (absolute_directory, *absolute_directory.parents)
        ):
            raise UnsafeAlphaRehearsalStore(
                "alpha-rehearsal directory and existing ancestors must not be "
                "symbolic links"
            )
        if self.directory.exists() and not self.directory.is_dir():
            raise UnsafeAlphaRehearsalStore(
                "alpha-rehearsal path must be a directory"
            )

    @staticmethod
    def _validate_rehearsal_id(rehearsal_id: str) -> str:
        if not _REHEARSAL_ID.fullmatch(rehearsal_id):
            raise ValueError(
                "rehearsal_id must be a deterministic local rehearsal identifier"
            )
        return rehearsal_id

    def _path(self, rehearsal_id: str) -> Path:
        return self.directory / f"{self._validate_rehearsal_id(rehearsal_id)}.json"

    def _existing_path(self, rehearsal_id: str) -> Path:
        self._require_safe_directory()
        target = self._path(rehearsal_id)
        if target.is_symlink() or not target.is_file():
            raise FileNotFoundError(rehearsal_id)
        return target

    def list_rehearsal_ids(self) -> list[str]:
        self._require_safe_directory()
        if not self.directory.is_dir():
            return []
        return sorted(
            path.stem
            for path in self.directory.glob("rehearsal-*.json")
            if path.is_file()
            and not path.is_symlink()
            and _REHEARSAL_ID.fullmatch(path.stem)
        )

    def save(self, record: AlphaRehearsalRecord) -> Path:
        validated = AlphaRehearsalRecord.model_validate(
            record.model_dump(mode="python")
        )
        self._require_safe_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(validated.rehearsal_id)
        if target.exists() or target.is_symlink():
            raise FileExistsError(validated.rehearsal_id)
        return self._write(target, validated)

    def load(self, rehearsal_id: str) -> AlphaRehearsalRecord:
        payload = json.loads(
            self._existing_path(rehearsal_id).read_text(encoding="utf-8")
        )
        validated = AlphaRehearsalRecord.model_validate(payload)
        if validated.rehearsal_id != rehearsal_id:
            raise ValueError("stored rehearsal record does not match requested ID")
        return validated

    def _write(self, target: Path, record: AlphaRehearsalRecord) -> Path:
        serialized = record.model_dump_json(indent=2) + "\n"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.directory,
                prefix=f".{target.stem}-",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(serialized)
            try:
                os.link(temporary, target)
            except FileExistsError:
                raise FileExistsError(record.rehearsal_id) from None
            return target
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
