import pytest
from pydantic import ValidationError

from scopeproof_core.alpha.models import (
    AlphaFrictionStage,
    AlphaOutcome,
    ParticipantRole,
)
from scopeproof_core.alpha.service import (
    initialize_alpha_case,
    public_alpha_summary,
    record_alpha_outcome,
)


def initialized_case():
    return initialize_alpha_case(
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.QA,
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
    )


def test_initialize_alpha_case_is_qualified_and_unpublished() -> None:
    record = initialized_case()

    assert record.source_owner_confirmed is True
    assert record.no_confidential_information is True
    assert record.publication_consent.report is False
    assert record.publication_consent.quote is False


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
