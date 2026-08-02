"""Pure transitions for public-alpha case records."""

from __future__ import annotations

from datetime import UTC, datetime

from scopeproof_core.alpha.models import (
    AlphaCasePublicSummary,
    AlphaCaseRecord,
    AlphaFrictionStage,
    AlphaOutcome,
    AlphaPublicationConsent,
    ParticipantRole,
)
from scopeproof_core.alpha.storage import JsonAlphaCaseStore
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.github.client import parse_pr_url
from scopeproof_core.schemas.models import (
    CriteriaSourceProvenance,
    Criterion,
    ReviewInputOrigin,
    ReviewState,
    normalize_public_https_source_uri,
)

_NEW_CASE_PROVENANCE_REQUIRED = "criteria source provenance is required for a new alpha case"
_LEGACY_RECONFIRMATION_REQUIRED = (
    "legacy alpha case must reconfirm criteria source provenance before recording an outcome"
)
_NEW_CASE_CRITERIA_SNAPSHOT_REQUIRED = (
    "confirmed criterion snapshot is required for a new alpha case"
)
_LEGACY_CRITERIA_SNAPSHOT_REQUIRED = (
    "legacy alpha case must reconfirm a criteria snapshot before recording an outcome"
)


def _require_genuine_alpha_case_record(record: object) -> AlphaCaseRecord:
    """Reject rehearsal or other unqualified records before genuine transitions."""
    if not isinstance(record, AlphaCaseRecord):
        raise ValueError("a genuine alpha-case record is required")
    return AlphaCaseRecord.model_validate(record.model_dump(mode="python"))


def initialize_alpha_case(
    *,
    public_pr_url: str,
    requirements_source_url: str,
    participant_role: ParticipantRole,
    source_owner_confirmed: bool,
    no_confidential_information: bool,
    confirmed_criteria: list[str],
    confirmed_criterion_snapshot: list[Criterion] | None = None,
    criteria_source_provenance: CriteriaSourceProvenance | None = None,
) -> AlphaCaseRecord:
    """Create a qualified local case without claiming an outcome."""
    if criteria_source_provenance is None:
        raise ValueError(_NEW_CASE_PROVENANCE_REQUIRED)
    if confirmed_criterion_snapshot is None:
        raise ValueError(_NEW_CASE_CRITERIA_SNAPSHOT_REQUIRED)
    return AlphaCaseRecord(
        public_pr_url=public_pr_url,
        requirements_source_url=normalize_public_https_source_uri(
            requirements_source_url
        ),
        participant_role=participant_role,
        source_owner_confirmed=source_owner_confirmed,
        no_confidential_information=no_confidential_information,
        confirmed_criteria=confirmed_criteria,
        confirmed_criterion_snapshot=confirmed_criterion_snapshot,
        criteria_source_provenance=criteria_source_provenance,
    )


def ensure_alpha_case(
    *,
    store: JsonAlphaCaseStore,
    public_pr_url: str,
    requirements_source_url: str,
    participant_role: ParticipantRole,
    source_owner_confirmed: bool,
    no_confidential_information: bool,
    confirmed_criteria: list[str],
    confirmed_criterion_snapshot: list[Criterion] | None = None,
    criteria_source_provenance: CriteriaSourceProvenance | None = None,
    case_id: str | None = None,
) -> AlphaCaseRecord:
    """Create one validated case or return the matching case already named by the caller."""

    candidate = initialize_alpha_case(
        public_pr_url=public_pr_url,
        requirements_source_url=requirements_source_url,
        participant_role=participant_role,
        source_owner_confirmed=source_owner_confirmed,
        no_confidential_information=no_confidential_information,
        confirmed_criteria=confirmed_criteria,
        confirmed_criterion_snapshot=confirmed_criterion_snapshot,
        criteria_source_provenance=criteria_source_provenance,
    )
    if case_id is None:
        store.save(candidate)
        return candidate

    existing = store.load(case_id)
    comparable_fields = (
        "public_pr_url",
        "requirements_source_url",
        "participant_role",
        "source_owner_confirmed",
        "no_confidential_information",
        "confirmed_criteria",
        "confirmed_criterion_snapshot",
        "criteria_source_provenance",
    )
    if any(getattr(existing, field) != getattr(candidate, field) for field in comparable_fields):
        raise ValueError("existing alpha case does not match the supplied qualification")
    return existing


def record_alpha_outcome(
    record: AlphaCaseRecord,
    *,
    review_state: ReviewState,
    outcome: AlphaOutcome,
    friction_stage: AlphaFrictionStage | None = None,
    outcome_notes: str | None = None,
    report_consent: bool = False,
    quote_consent: bool = False,
) -> AlphaCaseRecord:
    """Return a validated completed copy while preserving qualification inputs."""
    record = _require_genuine_alpha_case_record(record)
    if record.outcome is not None:
        raise ValueError("alpha outcome may be recorded only once")
    if record.criteria_source_provenance is None:
        raise ValueError(_LEGACY_RECONFIRMATION_REQUIRED)
    if record.confirmed_criterion_snapshot is None:
        raise ValueError(_LEGACY_CRITERIA_SNAPSHOT_REQUIRED)
    review_state = validated_review_state(review_state)
    if review_state.bundle is None:
        raise ValueError("alpha outcome requires a completed review analysis")
    if review_state.bundle.research_context is not None:
        raise ValueError("engineering research reviews cannot record alpha outcomes")
    if review_state.review.input_origin is not ReviewInputOrigin.LIVE_PUBLIC_GITHUB:
        raise ValueError("alpha outcome requires live public GitHub ingestion")
    owner, repository, pr_number = parse_pr_url(record.public_pr_url)
    if (
        review_state.review.repository != f"{owner}/{repository}"
        or review_state.review.pr_number != pr_number
    ):
        raise ValueError("alpha outcome review must match the qualified public PR")
    if (
        review_state.review.criteria_source_provenance
        != record.criteria_source_provenance
        or review_state.criteria_revision.source_provenance
        != record.criteria_source_provenance
        or review_state.bundle.review.criteria_source_provenance
        != record.criteria_source_provenance
    ):
        raise ValueError("alpha outcome review must match criteria source provenance")
    if (
        review_state.criteria_revision.criteria
        != record.confirmed_criterion_snapshot
        or review_state.bundle.criteria != record.confirmed_criterion_snapshot
    ):
        raise ValueError("alpha outcome review must match confirmed criteria")
    payload = record.model_dump(mode="python")
    payload.update(
        {
            "review_id": review_state.review.review_id,
            "reviewed_head_sha": review_state.review.head_sha,
            "outcome": outcome,
            "friction_stage": friction_stage,
            "outcome_notes": outcome_notes,
            "publication_consent": AlphaPublicationConsent(
                report=report_consent,
                quote=quote_consent,
            ),
            "completed_at": datetime.now(UTC),
        }
    )
    return AlphaCaseRecord.model_validate(payload)


def public_alpha_summary(record: AlphaCaseRecord) -> AlphaCasePublicSummary:
    """Create the reduced report surface only after explicit report consent."""
    record = _require_genuine_alpha_case_record(record)
    if not record.publication_consent.report:
        raise ValueError("public summary requires report publication consent")
    if record.outcome is None or record.reviewed_head_sha is None or record.completed_at is None:
        raise ValueError("public summary requires a completed alpha outcome")
    if (
        record.criteria_source_provenance is None
        or record.confirmed_criterion_snapshot is None
    ):
        raise ValueError("public summary requires criteria-bound alpha evidence")
    requirements_source_url = normalize_public_https_source_uri(
        str(record.requirements_source_url)
    )
    return AlphaCasePublicSummary(
        case_id=record.case_id,
        public_pr_url=record.public_pr_url,
        requirements_source_url=requirements_source_url,
        participant_role=record.participant_role,
        reviewed_head_sha=record.reviewed_head_sha,
        outcome=record.outcome,
        friction_stage=record.friction_stage,
        completed_at=record.completed_at,
    )
