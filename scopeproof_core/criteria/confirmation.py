"""Validate a repository-owned confirmation record for Action requirements."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RequirementsConfirmation(BaseModel):
    """A human confirmation bound to the exact bytes of a requirements file."""

    model_config = ConfigDict(extra="forbid")

    requirements_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed_by: str = Field(min_length=1)
    confirmed_at: datetime


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
