"""Explicit normalized intent for handoff, without confirmation or evidence claims."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from scopeproof_core.schemas.models import Criterion, source_text_sha256

MAX_CRITERIA_DOCUMENT_BYTES = 1_048_576


class NormalizedCriteriaDocument(BaseModel):
    """Bind ordered editable criteria to their exact original requirements source."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    source_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    criteria: list[Criterion] = Field(min_length=1)

    @field_validator("criteria")
    @classmethod
    def unique_criterion_ids(cls, criteria: list[Criterion]) -> list[Criterion]:
        identifiers = [criterion.criterion_id for criterion in criteria]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("normalized criteria must have unique criterion IDs")
        return criteria

    def criteria_for_source(self, source_text: str) -> list[Criterion]:
        """Fail closed on source changes; never reinterpret normalized intent as lines."""

        if self.source_text_sha256 != source_text_sha256(source_text):
            raise ValueError("criteria document source_text_sha256 does not match requirements")
        return self.criteria
