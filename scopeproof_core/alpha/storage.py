"""Atomic local storage for validated alpha-case records."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scopeproof_core.alpha.models import AlphaCaseRecord
from scopeproof_core.storage.atomic_files import (
    PORTABLE_HARD_LINK_REQUIRED,
    UnsafeAtomicPath,
    atomic_create_text,
    atomic_replace_text,
    ensure_safe_directory,
    exclusive_path_claim,
    list_regular_files,
    read_text_no_follow,
)

_CASE_ID = re.compile(r"^alpha-[0-9a-f]{32}$")


def default_alpha_case_directory() -> Path:
    """Return the app-owned directory for local alpha evidence."""
    return Path.home() / ".scopeproof" / "alpha-cases"


class UnsafeAlphaCaseStore(ValueError):
    """Raised when an alpha-case root is a symlink or non-directory."""


def _store_error_message(error: UnsafeAtomicPath, fallback: str) -> str:
    if str(error) == PORTABLE_HARD_LINK_REQUIRED:
        return PORTABLE_HARD_LINK_REQUIRED
    return fallback


class JsonAlphaCaseStore:
    """Store one Pydantic-validated JSON record per public-alpha case."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _require_safe_directory(self) -> None:
        try:
            ensure_safe_directory(self.directory, create=False)
        except FileNotFoundError:
            return
        except UnsafeAtomicPath as error:
            raise UnsafeAlphaCaseStore(
                _store_error_message(
                    error,
                    "alpha-case directory and existing ancestors must not be symbolic links, "
                    "reparse points, or non-directories",
                )
            ) from error

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
        try:
            read_text_no_follow(target)
        except FileNotFoundError:
            raise FileNotFoundError(case_id) from None
        except UnsafeAtomicPath as error:
            raise UnsafeAlphaCaseStore("alpha-case record must be a regular local file") from error
        return target

    def list_case_ids(self) -> list[str]:
        self._require_safe_directory()
        return sorted(
            path.stem
            for path in list_regular_files(self.directory)
            if path.suffix == ".json" and _CASE_ID.fullmatch(path.stem)
        )

    def save(self, record: AlphaCaseRecord) -> Path:
        validated = AlphaCaseRecord.model_validate(record.model_dump(mode="python"))
        self._require_safe_directory()
        target = self._path(validated.case_id)
        try:
            return self._write(target, validated)
        except UnsafeAtomicPath as error:
            raise UnsafeAlphaCaseStore(
                _store_error_message(
                    error,
                    "alpha-case directory and existing ancestors must not be symbolic links, "
                    "reparse points, or non-directories",
                )
            ) from error

    def update(self, record: AlphaCaseRecord) -> Path:
        validated = AlphaCaseRecord.model_validate(record.model_dump(mode="python"))
        target = self._path(validated.case_id)
        try:
            with exclusive_path_claim(target) as claim:
                payload = json.loads(read_text_no_follow(target, claim=claim))
                existing = AlphaCaseRecord.model_validate(payload)
                if existing.case_id != validated.case_id:
                    raise ValueError("stored alpha-case record does not match requested ID")
                self._validate_update(existing, validated)
                serialized = validated.model_dump_json(indent=2) + "\n"
                try:
                    atomic_replace_text(target, serialized, claim=claim)
                    return target
                except UnsafeAtomicPath as error:
                    raise UnsafeAlphaCaseStore(
                        _store_error_message(
                            error,
                            "alpha-case record must remain a regular local file",
                        )
                    ) from error
        except FileExistsError:
            raise ValueError("alpha-case update is already in progress") from None
        except UnsafeAtomicPath as error:
            raise UnsafeAlphaCaseStore(
                _store_error_message(
                    error,
                    "alpha-case directory and existing ancestors must not be symbolic links, "
                    "reparse points, or non-directories",
                )
            ) from error

    @staticmethod
    def _validate_update(existing: AlphaCaseRecord, validated: AlphaCaseRecord) -> None:
        if existing.case_id != validated.case_id:
            raise ValueError("alpha-case update must preserve case ID")
        if existing.criteria_source_provenance != validated.criteria_source_provenance:
            raise ValueError("alpha-case update must preserve criteria source provenance")
        immutable_fields = (
            "public_pr_url",
            "repository_visibility",
            "requirements_source_url",
            "participant_role",
            "source_owner_confirmed",
            "no_confidential_information",
            "confirmed_criteria",
            "confirmed_criterion_snapshot",
            "created_at",
        )
        if any(
            getattr(existing, field) != getattr(validated, field)
            for field in immutable_fields
        ):
            raise ValueError("alpha-case update must preserve qualification evidence")
        if existing.outcome is not None:
            raise ValueError("alpha-case outcome is immutable once recorded")
        if validated.outcome is None:
            raise ValueError("alpha-case update must record one outcome")

    def load(self, case_id: str) -> AlphaCaseRecord:
        validated_id = self._validate_case_id(case_id)
        target = self._existing_path(validated_id)
        try:
            payload = json.loads(read_text_no_follow(target))
        except UnsafeAtomicPath as error:
            raise UnsafeAlphaCaseStore("alpha-case record must be a regular local file") from error
        validated = AlphaCaseRecord.model_validate(payload)
        if validated.case_id != validated_id:
            raise ValueError("stored alpha-case record does not match requested ID")
        return validated

    def _write(self, target: Path, record: AlphaCaseRecord) -> Path:
        serialized = record.model_dump_json(indent=2) + "\n"
        atomic_create_text(target, serialized)
        return target
