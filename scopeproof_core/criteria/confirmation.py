"""Validate a repository-owned confirmation record for Action requirements."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from scopeproof_core.criteria.service import parse_criteria
from scopeproof_core.schemas.models import (
    CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
    CriteriaSourceProvenance,
    Criterion,
    normalized_criteria_sha256,
    source_text_sha256,
)

__all__ = [
    "CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI",
    "build_criteria_source_provenance",
    "canonical_criteria_sha256",
    "read_exact_utf8_text",
    "source_text_sha256",
    "validate_criteria_source_confirmation",
    "validate_requirements_confirmation",
]


def canonical_criteria_sha256(criteria: Sequence[Criterion]) -> str:
    """Hash the ordered, JSON-compatible criterion payload without mutating it."""

    return normalized_criteria_sha256(criteria)


def read_exact_utf8_text(path: Path) -> str:
    """Decode exact UTF-8 bytes without universal-newline translation."""

    return path.read_bytes().decode("utf-8")


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

    if not criteria:
        raise ValueError("criteria source confirmation requires at least one criterion")
    return CriteriaSourceProvenance(
        source_uri=source_uri,
        source_revision=source_revision,
        source_text_sha256=source_text_sha256(source_text),
        normalized_criteria_sha256=canonical_criteria_sha256(criteria),
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
    )


def validate_requirements_confirmation(
    requirements_path: Path,
    confirmation_path: Path,
) -> CriteriaSourceProvenance:
    """Load a typed snapshot and bind it to exact text plus ordered criteria."""

    source_text = read_exact_utf8_text(requirements_path)
    criteria = [
        Criterion(criterion_id=draft.criterion_id, text=draft.text)
        for draft in parse_criteria(source_text)
    ]
    return validate_criteria_source_confirmation(
        confirmation_path,
        source_text=source_text,
        criteria=criteria,
    )


def validate_criteria_source_confirmation(
    confirmation_path: Path,
    *,
    source_text: str,
    criteria: Sequence[Criterion],
) -> CriteriaSourceProvenance:
    """Validate one typed artifact against an already parsed source snapshot."""

    confirmation = CriteriaSourceProvenance.model_validate_json(
        confirmation_path.read_text(encoding="utf-8")
    )
    if confirmation.source_text_sha256 != source_text_sha256(source_text):
        raise ValueError(
            "confirmation source_text_sha256 does not match the requirements file"
        )
    if confirmation.normalized_criteria_sha256 != canonical_criteria_sha256(
        criteria
    ):
        raise ValueError(
            "confirmation normalized_criteria_sha256 does not match normalized criteria"
        )
    return confirmation
