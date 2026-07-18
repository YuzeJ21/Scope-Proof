import hashlib
import json

import pytest
from pydantic import ValidationError

from scopeproof_core.alpha.models import AlphaCaseRecord, AlphaQualification
from scopeproof_core.alpha.rehearsal import (
    REHEARSAL_EXCLUSION_REASON,
    AlphaRehearsalInput,
    AlphaRehearsalRecord,
    initialize_alpha_rehearsal,
)


def valid_rehearsal_data() -> dict[str, object]:
    return {
        "public_pr_url": "https://github.com/acme/repo/pull/7",
        "requirements_source_url": "https://github.com/acme/repo/issues/6",
        "criteria_authority": "Repository owner confirmation for this rehearsal",
        "source_owner_confirmed": True,
        "no_confidential_information": True,
        "confirmed_criteria": ["Export CSV", "Show an error state"],
    }


def initialized_rehearsal() -> AlphaRehearsalRecord:
    return initialize_alpha_rehearsal(**valid_rehearsal_data())


def test_rehearsal_input_normalizes_owner_confirmed_inputs() -> None:
    data = valid_rehearsal_data()
    data["criteria_authority"] = "  Repository owner confirmation  "
    data["confirmed_criteria"] = ["  Export CSV  ", "Show an error state"]

    rehearsal_input = AlphaRehearsalInput(**data)

    assert rehearsal_input.criteria_authority == "Repository owner confirmation"
    assert rehearsal_input.confirmed_criteria == ["Export CSV", "Show an error state"]
    assert rehearsal_input.source_owner_confirmed is True
    assert rehearsal_input.no_confidential_information is True


def test_initialized_rehearsal_has_fixed_exclusion_classification() -> None:
    record = initialized_rehearsal()

    assert record.submission_mode == "owner_rehearsal"
    assert record.eligible_for_stage_1 is False
    assert record.external_participant is False
    assert record.external_validation is False
    assert record.exclusion_reason == REHEARSAL_EXCLUSION_REASON


def test_rehearsal_id_uses_canonical_validated_input_json() -> None:
    validated_input = AlphaRehearsalInput(**valid_rehearsal_data())
    canonical = json.dumps(
        validated_input.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    expected_id = f"rehearsal-{hashlib.sha256(canonical.encode()).hexdigest()[:32]}"

    assert initialized_rehearsal().rehearsal_id == expected_id


def test_rehearsal_id_is_stable_after_input_normalization() -> None:
    normalized = initialized_rehearsal()
    data = valid_rehearsal_data()
    data["criteria_authority"] = f"  {data['criteria_authority']}  "
    data["confirmed_criteria"] = [" Export CSV", "Show an error state "]

    assert initialize_alpha_rehearsal(**data) == normalized


def test_rehearsal_record_rejects_well_formed_id_not_derived_from_inputs() -> None:
    payload = initialized_rehearsal().model_dump(mode="json")
    payload["rehearsal_id"] = "rehearsal-" + "0" * 32

    with pytest.raises(ValidationError, match="derived from canonical rehearsal inputs"):
        AlphaRehearsalRecord.model_validate(payload)


@pytest.mark.parametrize("criteria_authority", ["", "   "])
def test_rehearsal_rejects_blank_criteria_authority(criteria_authority: str) -> None:
    data = valid_rehearsal_data()
    data["criteria_authority"] = criteria_authority

    with pytest.raises(ValidationError, match="authority"):
        AlphaRehearsalInput(**data)


@pytest.mark.parametrize(
    "confirmed_criteria",
    [[], [""], ["   "], ["Export CSV", " Export CSV "]],
)
def test_rehearsal_rejects_empty_or_duplicate_criteria(
    confirmed_criteria: list[str],
) -> None:
    data = valid_rehearsal_data()
    data["confirmed_criteria"] = confirmed_criteria

    with pytest.raises(ValidationError, match="criteria"):
        AlphaRehearsalInput(**data)


@pytest.mark.parametrize(
    "requirements_source_url",
    [
        "http://example.com/requirements",
        "https://user:password@example.com/requirements",
        "https://localhost/requirements",
        "https://localhost./requirements",
        "https://requirements.local/criteria",
        "https://127.0.0.1/requirements",
        "https://10.0.0.1/requirements",
        "https://169.254.1.1/requirements",
        "https://100.64.0.1/requirements",
        "https://192.0.2.1/requirements",
        "https://224.0.0.1/requirements",
        "https://0.0.0.0/requirements",
        "https://[::1]/requirements",
        "https://[fe80::1]/requirements",
        "https://[ff00::1]/requirements",
    ],
)
def test_rehearsal_rejects_non_public_shaped_requirements_urls(
    requirements_source_url: str,
) -> None:
    data = valid_rehearsal_data()
    data["requirements_source_url"] = requirements_source_url

    with pytest.raises(ValidationError, match="public-shaped HTTPS"):
        AlphaRehearsalInput(**data)


@pytest.mark.parametrize(
    "requirements_source_url",
    [
        "https://8.8.8.8/requirements",
        "https://[2606:4700:4700::1111]/requirements",
    ],
)
def test_rehearsal_accepts_globally_routable_unicast_ip_literals(
    requirements_source_url: str,
) -> None:
    data = valid_rehearsal_data()
    data["requirements_source_url"] = requirements_source_url

    rehearsal_input = AlphaRehearsalInput(**data)

    assert str(rehearsal_input.requirements_source_url) == requirements_source_url


@pytest.mark.parametrize(
    "public_pr_url",
    [
        "http://github.com/acme/repo/pull/7",
        "https://github.com/acme/repo/issues/7",
        "https://example.com/acme/repo/pull/7",
        "https://github.com/acme/repo/pull/07",
    ],
)
def test_rehearsal_requires_canonical_public_pr_shape(public_pr_url: str) -> None:
    data = valid_rehearsal_data()
    data["public_pr_url"] = public_pr_url

    with pytest.raises(ValidationError):
        AlphaRehearsalInput(**data)


@pytest.mark.parametrize(
    "field",
    ["source_owner_confirmed", "no_confidential_information"],
)
def test_rehearsal_requires_explicit_true_confirmations(field: str) -> None:
    data = valid_rehearsal_data()
    data[field] = False

    with pytest.raises(ValidationError):
        AlphaRehearsalInput(**data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("participant_role", "engineering"),
        ("outcome", "found_useful_gap"),
        ("review_id", "review-7"),
        ("reviewed_head_sha", "a" * 40),
        ("publication_consent", {"report": False, "quote": False}),
        ("outcome_notes", "constructed result"),
        ("completed_at", "2026-07-18T12:00:00Z"),
        ("notes", "free-form rehearsal note"),
    ],
)
def test_rehearsal_forbids_genuine_case_and_free_form_fields(
    field: str, value: object
) -> None:
    data = valid_rehearsal_data()
    data[field] = value

    with pytest.raises(ValidationError, match="extra"):
        AlphaRehearsalInput(**data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("submission_mode", "public_alpha"),
        ("eligible_for_stage_1", True),
        ("external_participant", True),
        ("external_validation", True),
        ("exclusion_reason", "Eligible after rehearsal"),
    ],
)
def test_rehearsal_rejects_fixed_classification_overrides(
    field: str, value: object
) -> None:
    payload = initialized_rehearsal().model_dump(mode="json")
    payload[field] = value

    with pytest.raises(ValidationError):
        AlphaRehearsalRecord.model_validate(payload)


@pytest.mark.parametrize("genuine_model", [AlphaQualification, AlphaCaseRecord])
def test_genuine_alpha_models_reject_rehearsal_payload(genuine_model: type) -> None:
    payload = initialized_rehearsal().model_dump(mode="json")

    with pytest.raises(ValidationError):
        genuine_model.model_validate(payload)
