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


def _require_genuine_alpha_case_record(record: object) -> AlphaCaseRecord:
    """Reject rehearsal or other unqualified records before genuine transitions."""
    if not isinstance(record, AlphaCaseRecord):
        raise ValueError("a genuine alpha-case record is required")
    return record


def initialize_alpha_case(
    *,
    public_pr_url: str,
    requirements_source_url: str,
    participant_role: ParticipantRole,
    source_owner_confirmed: bool,
    no_confidential_information: bool,
    confirmed_criteria: list[str],
) -> AlphaCaseRecord:
    """Create a qualified local case without claiming an outcome."""
    return AlphaCaseRecord(
        public_pr_url=public_pr_url,
        requirements_source_url=requirements_source_url,
        participant_role=participant_role,
        source_owner_confirmed=source_owner_confirmed,
        no_confidential_information=no_confidential_information,
        confirmed_criteria=confirmed_criteria,
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
    )
    if any(
        getattr(existing, field) != getattr(candidate, field)
        for field in comparable_fields
    ):
        raise ValueError("existing alpha case does not match the supplied qualification")
    return existing


def record_alpha_outcome(
    record: AlphaCaseRecord,
    *,
    review_id: str,
    reviewed_head_sha: str,
    outcome: AlphaOutcome,
    friction_stage: AlphaFrictionStage | None = None,
    outcome_notes: str | None = None,
    report_consent: bool = False,
    quote_consent: bool = False,
) -> AlphaCaseRecord:
    """Return a validated completed copy while preserving qualification inputs."""
    record = _require_genuine_alpha_case_record(record)
    payload = record.model_dump(mode="python")
    payload.update(
        {
            "review_id": review_id,
            "reviewed_head_sha": reviewed_head_sha,
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
    return AlphaCasePublicSummary(
        case_id=record.case_id,
        public_pr_url=record.public_pr_url,
        requirements_source_url=record.requirements_source_url,
        participant_role=record.participant_role,
        reviewed_head_sha=record.reviewed_head_sha,
        outcome=record.outcome,
        friction_stage=record.friction_stage,
        completed_at=record.completed_at,
    )
