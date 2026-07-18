"""Deterministic contracts for local owner/Codex alpha rehearsals."""

from __future__ import annotations

import hashlib
import ipaddress
import json
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from scopeproof_core.alpha.models import PUBLIC_PR_PATTERN

REHEARSAL_EXCLUSION_REASON = (
    "Owner/Codex rehearsal is engineering evidence only; it is not external "
    "validation and never advances Stage 1."
)


class AlphaRehearsalInput(BaseModel):
    """Validated public-shaped inputs for a local owner rehearsal."""

    model_config = ConfigDict(extra="forbid")

    public_pr_url: str = Field(pattern=PUBLIC_PR_PATTERN)
    requirements_source_url: HttpUrl
    criteria_authority: str
    source_owner_confirmed: Literal[True]
    no_confidential_information: Literal[True]
    confirmed_criteria: list[str] = Field(min_length=1)

    @field_validator("requirements_source_url")
    @classmethod
    def require_public_shaped_https_source(cls, value: HttpUrl) -> HttpUrl:
        parsed = urlsplit(str(value))
        hostname = parsed.hostname
        normalized_hostname = hostname.rstrip(".").lower() if hostname else None
        unsafe = value.scheme != "https" or parsed.username is not None
        if (
            parsed.password is not None
            or normalized_hostname is None
            or normalized_hostname == "localhost"
            or normalized_hostname.endswith(".localhost")
            or normalized_hostname.endswith(".local")
        ):
            unsafe = True
        else:
            try:
                address = ipaddress.ip_address(normalized_hostname)
            except ValueError:
                pass
            else:
                unsafe = unsafe or not address.is_global or address.is_multicast
        if unsafe:
            raise ValueError(
                "requirements source must be a public-shaped HTTPS URL without "
                "credentials, local hosts, or non-public IP literals"
            )
        return value

    @field_validator("criteria_authority")
    @classmethod
    def normalize_criteria_authority(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("criteria authority must contain non-whitespace text")
        return normalized

    @field_validator("confirmed_criteria")
    @classmethod
    def normalize_confirmed_criteria(cls, value: list[str]) -> list[str]:
        normalized = [criterion.strip() for criterion in value]
        if any(not criterion for criterion in normalized):
            raise ValueError("criteria must contain non-whitespace text")
        if len(normalized) != len(set(normalized)):
            raise ValueError("confirmed criteria must be unique")
        return normalized


def _derive_rehearsal_id(validated_input: AlphaRehearsalInput) -> str:
    canonical_input = json.dumps(
        validated_input.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical_input.encode("utf-8")).hexdigest()
    return f"rehearsal-{digest[:32]}"


class AlphaRehearsalRecord(AlphaRehearsalInput):
    """Create-only rehearsal record permanently excluded from genuine alpha."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rehearsal_id: str = Field(pattern=r"^rehearsal-[0-9a-f]{32}$")
    submission_mode: Literal["owner_rehearsal"] = "owner_rehearsal"
    eligible_for_stage_1: Literal[False] = False
    external_participant: Literal[False] = False
    external_validation: Literal[False] = False
    exclusion_reason: Literal[
        "Owner/Codex rehearsal is engineering evidence only; it is not external "
        "validation and never advances Stage 1."
    ] = REHEARSAL_EXCLUSION_REASON

    @model_validator(mode="after")
    def validate_rehearsal_id_derivation(self) -> AlphaRehearsalRecord:
        input_payload = {
            name: getattr(self, name) for name in AlphaRehearsalInput.model_fields
        }
        validated_input = AlphaRehearsalInput.model_validate(input_payload)
        if self.rehearsal_id != _derive_rehearsal_id(validated_input):
            raise ValueError(
                "rehearsal ID must be derived from canonical rehearsal inputs"
            )
        return self


def initialize_alpha_rehearsal(
    *,
    public_pr_url: str,
    requirements_source_url: str,
    criteria_authority: str,
    source_owner_confirmed: bool,
    no_confidential_information: bool,
    confirmed_criteria: list[str],
) -> AlphaRehearsalRecord:
    """Validate owner inputs and derive a deterministic rehearsal record."""
    validated_input = AlphaRehearsalInput(
        public_pr_url=public_pr_url,
        requirements_source_url=requirements_source_url,
        criteria_authority=criteria_authority,
        source_owner_confirmed=source_owner_confirmed,
        no_confidential_information=no_confidential_information,
        confirmed_criteria=confirmed_criteria,
    )
    return AlphaRehearsalRecord(
        **validated_input.model_dump(mode="python"),
        rehearsal_id=_derive_rehearsal_id(validated_input),
    )
