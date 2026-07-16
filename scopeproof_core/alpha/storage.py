"""Atomic local storage for validated alpha-case records."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from scopeproof_core.alpha.models import AlphaCaseRecord

_CASE_ID = re.compile(r"^alpha-[0-9a-f]{32}$")


def default_alpha_case_directory() -> Path:
    """Return the app-owned directory for local alpha evidence."""
    return Path.home() / ".scopeproof" / "alpha-cases"


class UnsafeAlphaCaseStore(ValueError):
    """Raised when an alpha-case root is a symlink or non-directory."""


class JsonAlphaCaseStore:
    """Store one Pydantic-validated JSON record per public-alpha case."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _require_safe_directory(self) -> None:
        if self.directory.is_symlink():
            raise UnsafeAlphaCaseStore("alpha-case directory must not be a symbolic link")
        if self.directory.exists() and not self.directory.is_dir():
            raise UnsafeAlphaCaseStore("alpha-case path must be a directory")

    @staticmethod
    def _validate_case_id(case_id: str) -> str:
        if not _CASE_ID.fullmatch(case_id):
            raise ValueError("case_id must be a generated local alpha identifier")
        return case_id

    def _path(self, case_id: str) -> Path:
        return self.directory / f"{self._validate_case_id(case_id)}.json"

    def _existing_path(self, case_id: str) -> Path:
        self._require_safe_directory()
        target = self._path(case_id)
        if target.is_symlink() or not target.is_file():
            raise FileNotFoundError(case_id)
        return target

    def list_case_ids(self) -> list[str]:
        self._require_safe_directory()
        if not self.directory.is_dir():
            return []
        return sorted(
            path.stem
            for path in self.directory.glob("alpha-*.json")
            if path.is_file() and not path.is_symlink() and _CASE_ID.fullmatch(path.stem)
        )

    def save(self, record: AlphaCaseRecord) -> Path:
        validated = AlphaCaseRecord.model_validate(record.model_dump(mode="python"))
        self._require_safe_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(validated.case_id)
        if target.exists() or target.is_symlink():
            raise FileExistsError(validated.case_id)
        return self._write(target, validated)

    def update(self, record: AlphaCaseRecord) -> Path:
        validated = AlphaCaseRecord.model_validate(record.model_dump(mode="python"))
        target = self._existing_path(validated.case_id)
        existing = self.load(validated.case_id)
        if existing.case_id != validated.case_id:
            raise ValueError("alpha-case update must preserve case ID")
        return self._write(target, validated)

    def load(self, case_id: str) -> AlphaCaseRecord:
        payload = json.loads(self._existing_path(case_id).read_text(encoding="utf-8"))
        return AlphaCaseRecord.model_validate(payload)

    def _write(self, target: Path, record: AlphaCaseRecord) -> Path:
        serialized = record.model_dump_json(indent=2) + "\n"
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.directory,
            prefix=f".{target.stem}-",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
        temporary.replace(target)
        return target
