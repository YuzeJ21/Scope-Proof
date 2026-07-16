"""Pydantic contracts for genuine, public-PR alpha evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from scopeproof_core.schemas.models import LocalReviewId

PUBLIC_PR_PATTERN = (
    r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/pull/[1-9][0-9]*$"
)


class ParticipantRole(StrEnum):
    PRODUCT_MANAGER = "product_manager"
    QA = "qa"
    ENGINEERING = "engineering"
    OTHER = "other"


class AlphaOutcome(StrEnum):
    FOUND_USEFUL_GAP = "found_useful_gap"
    SHOWED_ONLY_KNOWN_INFORMATION = "showed_only_known_information"
    CREATED_FRICTION = "created_friction"


class AlphaFrictionStage(StrEnum):
    QUALIFICATION = "qualification"
    CRITERIA = "criteria"
    EVIDENCE = "evidence"
    DECISIONS = "decisions"
    OUTCOME = "outcome"
    EXPORT = "export"
    INTEGRATION = "integration"


class AlphaPublicationConsent(BaseModel):
    """Separate permission boundaries for reports and quotations."""

    model_config = ConfigDict(extra="forbid")

    report: bool = False
    quote: bool = False


class AlphaCaseRecord(BaseModel):
    """Local evidence for one source-owner-confirmed public-alpha case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(
        default_factory=lambda: f"alpha-{uuid4().hex}",
        pattern=r"^alpha-[0-9a-f]{32}$",
    )
    public_pr_url: str = Field(pattern=PUBLIC_PR_PATTERN)
    requirements_source_url: HttpUrl
    participant_role: ParticipantRole
    source_owner_confirmed: Literal[True]
    no_confidential_information: Literal[True]
    confirmed_criteria: list[str] = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    review_id: LocalReviewId | None = None
    reviewed_head_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    outcome: AlphaOutcome | None = None
    friction_stage: AlphaFrictionStage | None = None
    outcome_notes: str | None = Field(default=None, max_length=1000)
    publication_consent: AlphaPublicationConsent = Field(
        default_factory=AlphaPublicationConsent
    )
    completed_at: datetime | None = None

    @field_validator("requirements_source_url")
    @classmethod
    def require_https_source(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("requirements source must use HTTPS")
        return value

    @field_validator("confirmed_criteria")
    @classmethod
    def normalize_confirmed_criteria(cls, value: list[str]) -> list[str]:
        normalized = [criterion.strip() for criterion in value]
        if any(not criterion for criterion in normalized):
            raise ValueError("criteria must contain non-whitespace text")
        if len(normalized) != len(set(normalized)):
            raise ValueError("confirmed criteria must be unique")
        return normalized

    @field_validator("outcome_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("outcome notes must contain non-whitespace text")
        return normalized

    @model_validator(mode="after")
    def validate_outcome_transition(self) -> AlphaCaseRecord:
        completion_values = (
            self.review_id,
            self.reviewed_head_sha,
            self.outcome_notes,
            self.completed_at,
        )
        if self.outcome is None and any(value is not None for value in completion_values):
            raise ValueError("completion fields require an outcome")
        if self.outcome is not None:
            if self.review_id is None or self.reviewed_head_sha is None:
                raise ValueError(
                    "completed alpha outcomes require a review ID and reviewed head SHA"
                )
            if self.completed_at is None:
                raise ValueError("completed alpha outcomes require a completion timestamp")
        if self.outcome is AlphaOutcome.CREATED_FRICTION and self.friction_stage is None:
            raise ValueError("created_friction requires a friction stage")
        if (
            self.friction_stage is not None
            and self.outcome is not AlphaOutcome.CREATED_FRICTION
        ):
            raise ValueError("friction stage is only valid for created_friction")
        return self


class AlphaCasePublicSummary(BaseModel):
    """Reduced, consent-gated report surface with no local notes or quotation."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    public_pr_url: str = Field(pattern=PUBLIC_PR_PATTERN)
    requirements_source_url: HttpUrl
    participant_role: ParticipantRole
    reviewed_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    outcome: AlphaOutcome
    friction_stage: AlphaFrictionStage | None = None
    completed_at: datetime
