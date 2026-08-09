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
from scopeproof_core.cli import _build_bundle
from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import (
    Criterion,
    PullRequestSnapshot,
    RepositoryVisibility,
    ReviewInputOrigin,
)


def criteria_source_provenance(*, source_uri: str = "https://github.com/acme/repo/issues/6"):
    return build_criteria_source_provenance(
        source_uri=source_uri,
        source_revision="issue-6@abc123",
        source_text="Export CSV\n",
        criteria=[Criterion(criterion_id="AC-01", text="Export CSV")],
        confirmed_by="Repository owner",
        confirmed_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


def confirmed_criterion_snapshot() -> list[Criterion]:
    return [Criterion(criterion_id="AC-01", text="Export CSV")]


def initialized_case():
    return initialize_alpha_case(
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.QA,
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
        confirmed_criterion_snapshot=confirmed_criterion_snapshot(),
        criteria_source_provenance=criteria_source_provenance(),
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
    )


def matching_review_state(
    *,
    repository: str = "acme/repo",
    pr_number: int = 7,
    input_origin: ReviewInputOrigin = ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
    research_case_id: str | None = None,
):
    criteria = confirmed_criterion_snapshot()
    provenance = criteria_source_provenance()
    snapshot = PullRequestSnapshot(
        repository=repository,
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        pr_number=pr_number,
        title="Export CSV",
        html_url=f"https://github.com/{repository}/pull/{pr_number}",
        base_sha="b" * 40,
        head_sha="a" * 40,
    )
    return new_review_state(
        _build_bundle(
            snapshot,
            criteria,
            "Export CSV\n",
            provenance,
            research_case_id,
            input_origin,
        )
    )


def test_initialize_alpha_case_requires_verified_public_visibility() -> None:
    with pytest.raises(
        ValueError,
        match="alpha qualification requires verified public repository visibility",
    ):
        initialize_alpha_case(
            public_pr_url="https://github.com/acme/repo/pull/7",
            requirements_source_url="https://github.com/acme/repo/issues/6",
            participant_role=ParticipantRole.QA,
            source_owner_confirmed=True,
            no_confidential_information=True,
            confirmed_criteria=["Export CSV"],
            confirmed_criterion_snapshot=confirmed_criterion_snapshot(),
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
        "confirmed_criterion_snapshot": confirmed_criterion_snapshot(),
        "criteria_source_provenance": criteria_source_provenance(),
        "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
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
        confirmed_criterion_snapshot=confirmed_criterion_snapshot(),
        criteria_source_provenance=criteria_source_provenance(),
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
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
            confirmed_criterion_snapshot=confirmed_criterion_snapshot(),
            criteria_source_provenance=criteria_source_provenance(),
            repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
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
            confirmed_criterion_snapshot=confirmed_criterion_snapshot(),
            criteria_source_provenance=criteria_source_provenance(),
            repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        )


def test_record_alpha_outcome_returns_completed_validated_copy() -> None:
    original = initialized_case()

    completed = record_alpha_outcome(
        original,
        review_state=matching_review_state(),
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
            confirmed_criterion_snapshot=confirmed_criterion_snapshot(),
            criteria_source_provenance=None,
        )


def test_initialize_alpha_case_rejects_criteria_provenance_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match="confirmed criterion snapshot must match criteria source provenance",
    ):
        initialize_alpha_case(
            public_pr_url="https://github.com/acme/repo/pull/7",
            requirements_source_url="https://github.com/acme/repo/issues/6",
            participant_role=ParticipantRole.QA,
            source_owner_confirmed=True,
            no_confidential_information=True,
            confirmed_criteria=["Delete production data"],
            confirmed_criterion_snapshot=[
                Criterion(criterion_id="AC-01", text="Delete production data")
            ],
            criteria_source_provenance=criteria_source_provenance(),
            repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        )


def test_record_alpha_outcome_is_append_once() -> None:
    completed = record_alpha_outcome(
        initialized_case(),
        review_state=matching_review_state(),
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
    )

    with pytest.raises(ValueError, match="alpha outcome may be recorded only once"):
        record_alpha_outcome(
            completed,
            review_state=matching_review_state(),
            outcome=AlphaOutcome.CREATED_FRICTION,
            friction_stage=AlphaFrictionStage.OUTCOME,
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
            review_state=matching_review_state(),
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


def test_record_alpha_outcome_rejects_unrelated_review() -> None:
    with pytest.raises(
        ValueError,
        match="alpha outcome review must match the qualified public PR",
    ):
        record_alpha_outcome(
            initialized_case(),
            review_state=matching_review_state(repository="acme/other", pr_number=9),
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


@pytest.mark.parametrize(
    ("input_origin", "research_case_id", "message"),
    [
        (
            ReviewInputOrigin.LOCAL_FIXTURE,
            None,
            "alpha outcome requires live public GitHub ingestion",
        ),
        (
            ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
            "R-003",
            "engineering research reviews cannot record alpha outcomes",
        ),
    ],
)
def test_record_alpha_outcome_rejects_engineering_only_review_sources(
    input_origin: ReviewInputOrigin,
    research_case_id: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        record_alpha_outcome(
            initialized_case(),
            review_state=matching_review_state(
                input_origin=input_origin,
                research_case_id=research_case_id,
            ),
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


def test_record_alpha_outcome_rejects_unverified_legacy_review() -> None:
    state = matching_review_state()
    assert state.bundle is not None
    unverified_review = state.review.model_copy(
        update={"repository_visibility": RepositoryVisibility.UNVERIFIED}
    )
    state = state.model_copy(
        update={
            "review": unverified_review,
            "bundle": state.bundle.model_copy(update={"review": unverified_review}),
        }
    )

    with pytest.raises(
        ValueError,
        match="alpha outcome requires verified public repository visibility",
    ):
        record_alpha_outcome(
            initialized_case(),
            review_state=state,
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


def test_record_alpha_outcome_rejects_legacy_case_without_verified_visibility() -> None:
    payload = initialized_case().model_dump(mode="python")
    payload["repository_visibility"] = RepositoryVisibility.UNVERIFIED
    legacy = AlphaCaseRecord.model_validate(payload)

    with pytest.raises(
        ValueError,
        match="legacy alpha case must be re-fetched before recording an outcome",
    ):
        record_alpha_outcome(
            legacy,
            review_state=matching_review_state(),
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


def test_public_summary_requires_report_consent() -> None:
    completed = record_alpha_outcome(
        initialized_case(),
        review_state=matching_review_state(),
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
        review_state=matching_review_state(),
        outcome=AlphaOutcome.SHOWED_ONLY_KNOWN_INFORMATION,
        outcome_notes="This note remains local.",
        report_consent=True,
        quote_consent=True,
    )

    payload = public_alpha_summary(completed).model_dump(mode="json")

    assert payload["outcome"] == "showed_only_known_information"
    assert payload["repository_visibility"] == "verified_public"
    assert "outcome_notes" not in payload
    assert "publication_consent" not in payload
    assert "criteria_source_provenance" not in payload


def test_public_summary_refuses_legacy_secret_bearing_source_url() -> None:
    completed = record_alpha_outcome(
        initialized_case(),
        review_state=matching_review_state(),
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        report_consent=True,
    )
    payload = completed.model_dump(mode="python")
    payload.update(
        {
            "requirements_source_url": "https://user:secret@example.com/requirements",
            "criteria_source_provenance": None,
            "confirmed_criterion_snapshot": None,
        }
    )
    legacy = AlphaCaseRecord.model_validate(payload)

    with pytest.raises(ValueError) as error:
        public_alpha_summary(legacy)

    assert "secret" not in str(error.value)


def test_public_summary_revalidates_mutated_alpha_record() -> None:
    completed = record_alpha_outcome(
        initialized_case(),
        review_state=matching_review_state(),
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        report_consent=True,
    )
    completed.source_owner_confirmed = False  # type: ignore[assignment]

    with pytest.raises(ValidationError):
        public_alpha_summary(completed)


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
            review_state=matching_review_state(),
            outcome=AlphaOutcome.FOUND_USEFUL_GAP,
        )


def test_public_alpha_summary_rejects_owner_rehearsal_record() -> None:
    rehearsal = initialized_rehearsal()

    with pytest.raises(ValueError, match="genuine alpha-case record is required"):
        public_alpha_summary(rehearsal)  # type: ignore[arg-type]
