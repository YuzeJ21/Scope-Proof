"""Validate a repository-owned confirmation record for Action requirements."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from scopeproof_core.schemas.models import (
    CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
    CriteriaSourceProvenance,
    Criterion,
    normalized_criteria_sha256,
    source_text_sha256,
)

__all__ = [
    "CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI",
    "RequirementsConfirmation",
    "build_criteria_source_provenance",
    "canonical_criteria_sha256",
    "source_text_sha256",
    "validate_requirements_confirmation",
]


def canonical_criteria_sha256(criteria: Sequence[Criterion]) -> str:
    """Hash the ordered, JSON-compatible criterion payload without mutating it."""

    return normalized_criteria_sha256(criteria)


def build_criteria_source_provenance(
    *,
    source_uri: str,
    source_revision: str | None = None,
    source_text: str,
    criteria: Sequence[Criterion],
    confirmed_by: str,
    confirmed_at: datetime,
) -> CriteriaSourceProvenance:
    """Create an immutable confirmation record for an observed source snapshot."""

    return CriteriaSourceProvenance(
        source_uri=source_uri,
        source_revision=source_revision,
        source_text_sha256=source_text_sha256(source_text),
        normalized_criteria_sha256=canonical_criteria_sha256(criteria),
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
    )


class RequirementsConfirmation(BaseModel):
    """A human confirmation bound to the exact bytes of a requirements file."""

    model_config = ConfigDict(extra="forbid")

    requirements_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed_by: str = Field(min_length=1)
    confirmed_at: datetime

    @field_validator("confirmed_by", mode="before")
    @classmethod
    def require_non_blank_confirmer(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("confirmed_by must contain non-whitespace text")
        return value


def validate_requirements_confirmation(
    requirements_path: Path, confirmation_path: Path
) -> RequirementsConfirmation:
    """Load validated confirmation metadata and reject a changed requirements file."""

    requirements_digest = hashlib.sha256(requirements_path.read_bytes()).hexdigest()
    confirmation = RequirementsConfirmation.model_validate_json(
        confirmation_path.read_text(encoding="utf-8")
    )
    if confirmation.requirements_sha256 != requirements_digest:
        raise ValueError("confirmation requirements_sha256 does not match the requirements file")
    return confirmation
