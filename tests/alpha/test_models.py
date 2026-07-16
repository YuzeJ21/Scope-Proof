from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.alpha.models import (
    AlphaCaseRecord,
    AlphaFrictionStage,
    AlphaOutcome,
    AlphaPublicationConsent,
    AlphaQualification,
    ParticipantRole,
)


def valid_record_data() -> dict[str, object]:
    return {
        "public_pr_url": "https://github.com/acme/repo/pull/7",
        "requirements_source_url": "https://github.com/acme/repo/issues/6",
        "participant_role": ParticipantRole.QA,
        "source_owner_confirmed": True,
        "no_confidential_information": True,
        "confirmed_criteria": ["Export CSV", "Show an error state"],
    }


def test_alpha_qualification_accepts_only_confirmed_public_safe_inputs() -> None:
    qualification = AlphaQualification(
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.PRODUCT_MANAGER,
        source_owner_confirmed=True,
        no_confidential_information=True,
    )

    assert qualification.source_owner_confirmed is True
    assert qualification.no_confidential_information is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("public_pr_url", "https://github.com/acme/repo/issues/7"),
        ("requirements_source_url", "http://example.com/requirements"),
        ("source_owner_confirmed", False),
        ("no_confidential_information", False),
    ],
)
def test_alpha_qualification_rejects_unqualified_inputs(
    field: str, value: object
) -> None:
    data: dict[str, object] = {
        "public_pr_url": "https://github.com/acme/repo/pull/7",
        "requirements_source_url": "https://github.com/acme/repo/issues/6",
        "participant_role": ParticipantRole.QA,
        "source_owner_confirmed": True,
        "no_confidential_information": True,
    }
    data[field] = value

    with pytest.raises(ValidationError):
        AlphaQualification(**data)


def test_alpha_record_has_privacy_safe_defaults() -> None:
    record = AlphaCaseRecord(**valid_record_data())

    assert record.case_id.startswith("alpha-")
    assert record.publication_consent == AlphaPublicationConsent()
    assert record.outcome is None
    assert record.completed_at is None
    schema_fields = {field.lower() for field in AlphaCaseRecord.model_fields}
    for prohibited in ("name", "email", "profile", "dm"):
        assert all(prohibited not in field for field in schema_fields)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("public_pr_url", "https://example.com/acme/repo/pull/7"),
        ("requirements_source_url", "http://example.com/ticket/7"),
        ("source_owner_confirmed", False),
        ("no_confidential_information", False),
        ("confirmed_criteria", []),
        ("confirmed_criteria", ["Export CSV", " Export CSV "]),
    ],
)
def test_alpha_record_rejects_unqualified_or_unsafe_inputs(
    field: str, value: object
) -> None:
    data = valid_record_data()
    data[field] = value

    with pytest.raises(ValidationError):
        AlphaCaseRecord(**data)


def test_alpha_record_forbids_extra_participant_data() -> None:
    with pytest.raises(ValidationError, match="extra"):
        AlphaCaseRecord(**valid_record_data(), participant_email="person@example.com")


def test_completed_alpha_record_requires_review_linkage() -> None:
    with pytest.raises(ValidationError, match="review ID and reviewed head SHA"):
        AlphaCaseRecord(
            **valid_record_data(),
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
            completed_at=datetime.now(UTC),
        )


def test_friction_outcome_requires_stage() -> None:
    with pytest.raises(ValidationError, match="friction stage"):
        AlphaCaseRecord(
            **valid_record_data(),
            review_id="review-7",
            reviewed_head_sha="a" * 40,
            outcome=AlphaOutcome.CREATED_FRICTION,
            completed_at=datetime.now(UTC),
        )


def test_non_friction_outcome_forbids_stage() -> None:
    with pytest.raises(ValidationError, match="only valid for created_friction"):
        AlphaCaseRecord(
            **valid_record_data(),
            review_id="review-7",
            reviewed_head_sha="a" * 40,
            outcome=AlphaOutcome.SHOWED_ONLY_KNOWN_INFORMATION,
            friction_stage=AlphaFrictionStage.EVIDENCE,
            completed_at=datetime.now(UTC),
        )


def test_incomplete_record_forbids_completion_fields() -> None:
    with pytest.raises(ValidationError, match="require an outcome"):
        AlphaCaseRecord(
            **valid_record_data(),
            review_id="review-7",
            reviewed_head_sha="a" * 40,
            completed_at=datetime.now(UTC),
        )
