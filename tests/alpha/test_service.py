from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.alpha.models import (
    AlphaCaseRecord,
    AlphaFrictionStage,
    AlphaOutcome,
    ParticipantRole,
)
from scopeproof_core.alpha.rehearsal import initialize_alpha_rehearsal
from scopeproof_core.alpha.service import (
    ensure_alpha_case,
    initialize_alpha_case,
    public_alpha_summary,
    record_alpha_outcome,
)
from scopeproof_core.alpha.storage import JsonAlphaCaseStore
from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.schemas.models import Criterion


def criteria_source_provenance(*, source_uri: str = "https://github.com/acme/repo/issues/6"):
    return build_criteria_source_provenance(
        source_uri=source_uri,
        source_revision="issue-6@abc123",
        source_text="Export CSV\n",
        criteria=[Criterion(criterion_id="AC-01", text="Export CSV")],
        confirmed_by="Repository owner",
        confirmed_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


def initialized_case():
    return initialize_alpha_case(
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.QA,
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
        criteria_source_provenance=criteria_source_provenance(),
    )


def test_initialize_alpha_case_is_qualified_and_unpublished() -> None:
    record = initialized_case()

    assert record.source_owner_confirmed is True
    assert record.no_confidential_information is True
    assert record.publication_consent.report is False
    assert record.publication_consent.quote is False


def test_ensure_alpha_case_creates_once_and_returns_matching_existing(tmp_path) -> None:
    store = JsonAlphaCaseStore(tmp_path)
    inputs = {
        "public_pr_url": "https://github.com/acme/repo/pull/7",
        "requirements_source_url": "https://github.com/acme/repo/issues/6",
        "participant_role": ParticipantRole.QA,
        "source_owner_confirmed": True,
        "no_confidential_information": True,
        "confirmed_criteria": ["Export CSV"],
        "criteria_source_provenance": criteria_source_provenance(),
    }

    created = ensure_alpha_case(store=store, **inputs)
    reused = ensure_alpha_case(store=store, case_id=created.case_id, **inputs)

    assert reused == created
    assert store.list_case_ids() == [created.case_id]


def test_ensure_alpha_case_rejects_reusing_id_for_different_case(tmp_path) -> None:
    store = JsonAlphaCaseStore(tmp_path)
    created = ensure_alpha_case(
        store=store,
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.QA,
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
        criteria_source_provenance=criteria_source_provenance(),
    )

    with pytest.raises(ValueError, match="does not match"):
        ensure_alpha_case(
            store=store,
            case_id=created.case_id,
            public_pr_url="https://github.com/acme/repo/pull/8",
            requirements_source_url="https://github.com/acme/repo/issues/6",
            participant_role=ParticipantRole.QA,
            source_owner_confirmed=True,
            no_confidential_information=True,
            confirmed_criteria=["Export CSV"],
            criteria_source_provenance=criteria_source_provenance(),
        )


@pytest.mark.parametrize(
    ("source_owner_confirmed", "no_confidential_information"),
    [(False, True), (True, False)],
)
def test_initialize_alpha_case_requires_explicit_safe_confirmations(
    source_owner_confirmed: bool, no_confidential_information: bool
) -> None:
    with pytest.raises(ValidationError):
        initialize_alpha_case(
            public_pr_url="https://github.com/acme/repo/pull/7",
            requirements_source_url="https://github.com/acme/repo/issues/6",
            participant_role=ParticipantRole.QA,
            source_owner_confirmed=source_owner_confirmed,
            no_confidential_information=no_confidential_information,
            confirmed_criteria=["Export CSV"],
            criteria_source_provenance=criteria_source_provenance(),
        )


def test_record_alpha_outcome_returns_completed_validated_copy() -> None:
    original = initialized_case()

    completed = record_alpha_outcome(
        original,
        review_id="review-7",
        reviewed_head_sha="a" * 40,
        outcome=AlphaOutcome.CREATED_FRICTION,
        friction_stage=AlphaFrictionStage.EVIDENCE,
        outcome_notes="The evidence explanation required a second read.",
        report_consent=True,
        quote_consent=False,
    )

    assert original.outcome is None
    assert completed.case_id == original.case_id
    assert completed.outcome is AlphaOutcome.CREATED_FRICTION
    assert completed.completed_at is not None
    assert completed.publication_consent.report is True
    assert completed.publication_consent.quote is False
    assert completed.criteria_source_provenance == original.criteria_source_provenance


def test_initialize_alpha_case_requires_criteria_source_provenance() -> None:
    with pytest.raises(
        ValueError, match="criteria source provenance is required for a new alpha case"
    ):
        initialize_alpha_case(
            public_pr_url="https://github.com/acme/repo/pull/7",
            requirements_source_url="https://github.com/acme/repo/issues/6",
            participant_role=ParticipantRole.QA,
            source_owner_confirmed=True,
            no_confidential_information=True,
            confirmed_criteria=["Export CSV"],
            criteria_source_provenance=None,
        )


def test_record_alpha_outcome_rejects_legacy_case_until_source_is_reconfirmed() -> None:
    payload = initialized_case().model_dump(mode="python")
    payload["criteria_source_provenance"] = None
    legacy = AlphaCaseRecord.model_validate(payload)

    with pytest.raises(
        ValueError,
        match=(
            "legacy alpha case must reconfirm criteria source provenance before "
            "recording an outcome"
        ),
    ):
        record_alpha_outcome(
            legacy,
            review_id="review-7",
            reviewed_head_sha="a" * 40,
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


def test_public_summary_requires_report_consent() -> None:
    completed = record_alpha_outcome(
        initialized_case(),
        review_id="review-7",
        reviewed_head_sha="a" * 40,
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        outcome_notes="A missing error state was useful.",
    )

    try:
        public_alpha_summary(completed)
    except ValueError as error:
        assert "report publication consent" in str(error)
    else:
        raise AssertionError("summary unexpectedly bypassed consent")


def test_public_summary_omits_local_notes_and_consent_fields() -> None:
    completed = record_alpha_outcome(
        initialized_case(),
        review_id="review-7",
        reviewed_head_sha="a" * 40,
        outcome=AlphaOutcome.SHOWED_ONLY_KNOWN_INFORMATION,
        outcome_notes="This note remains local.",
        report_consent=True,
        quote_consent=True,
    )

    payload = public_alpha_summary(completed).model_dump(mode="json")

    assert payload["outcome"] == "showed_only_known_information"
    assert "outcome_notes" not in payload
    assert "publication_consent" not in payload
    assert "criteria_source_provenance" not in payload


def initialized_rehearsal():
    return initialize_alpha_rehearsal(
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://example.com/requirements.txt",
        criteria_authority="Repository owner approval",
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
    )


def test_record_alpha_outcome_rejects_owner_rehearsal_record() -> None:
    rehearsal = initialized_rehearsal()

    with pytest.raises(ValueError, match="genuine alpha-case record is required"):
        record_alpha_outcome(  # type: ignore[arg-type]
            rehearsal,
            review_id="review-7",
            reviewed_head_sha="a" * 40,
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


def test_public_alpha_summary_rejects_owner_rehearsal_record() -> None:
    rehearsal = initialized_rehearsal()

    with pytest.raises(ValueError, match="genuine alpha-case record is required"):
        public_alpha_summary(rehearsal)  # type: ignore[arg-type]
