"""Pydantic and deterministic-gate validation for trusted review boundaries."""

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.resolution_events import current_resolutions, final_acceptance
from scopeproof_core.schemas.models import (
    CheckState,
    HumanDecision,
    IngestionState,
    ReviewBundle,
    ReviewState,
)

_FINAL_ACCEPTANCE_DECISIONS = {
    HumanDecision.ACCEPTED,
    HumanDecision.ACCEPTED_EXCEPTION,
    HumanDecision.MANUALLY_VERIFIED,
    HumanDecision.NOT_IN_SCOPE,
}


def _require_deterministic_gate(bundle: ReviewBundle, location: str) -> None:
    expected_gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )
    if bundle.gate != expected_gate:
        raise ValueError(f"{location} gate must match deterministic evaluation")


def _require_manual_verification_evidence(
    bundle: ReviewBundle, location: str
) -> None:
    runtime_keys = {
        (item.criterion_id, item.reviewer, item.evidence_level)
        for item in bundle.runtime_evidence
    }
    unpaired = [
        resolution.criterion_id
        for resolution in bundle.resolutions
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED
        and (
            resolution.criterion_id,
            resolution.reviewer,
            resolution.claimed_evidence_level,
        )
        not in runtime_keys
    ]
    if unpaired:
        raise ValueError(
            f"{location} manually verified resolutions require matching runtime evidence"
        )


def _require_final_acceptance_prerequisites(
    bundle: ReviewBundle, location: str
) -> None:
    if not bundle.review.final_acceptance:
        return
    review = bundle.review
    if (
        not review.criteria_confirmed
        or review.ingestion_state is not IngestionState.COMPLETE
        or review.ingestion_warnings
        or review.skipped_files
        or review.check_state is not CheckState.PASSING
    ):
        raise ValueError(
            f"{location} final acceptance requires complete confirmed analysis and passing CI"
        )
    accepted_by_criterion = {
        resolution.criterion_id: resolution.decision
        for resolution in bundle.resolutions
    }
    if any(
        accepted_by_criterion.get(criterion.criterion_id)
        not in _FINAL_ACCEPTANCE_DECISIONS
        for criterion in bundle.criteria
    ):
        raise ValueError(
            f"{location} final acceptance requires accepted current resolutions"
        )


def _require_evidence_integrity(bundle: ReviewBundle, location: str) -> None:
    _require_manual_verification_evidence(bundle, location)
    _require_final_acceptance_prerequisites(bundle, location)


def _review_allows_final_acceptance(bundle: ReviewBundle) -> bool:
    review = bundle.review
    return (
        review.criteria_confirmed
        and review.ingestion_state is IngestionState.COMPLETE
        and not review.ingestion_warnings
        and not review.skipped_files
        and review.check_state is CheckState.PASSING
    )


def _require_event_history_integrity(state: ReviewState) -> None:
    bundles_by_revision = {
        bundle.criteria_revision_number: bundle
        for bundle in [*state.analysis_history, *([state.bundle] if state.bundle else [])]
        if bundle.criteria_revision_number != "unknown"
    }
    events_by_revision: dict[int, list] = {}
    for event in state.resolution_events:
        events_by_revision.setdefault(event.criteria_revision_number, []).append(event)

    for revision_number, events in events_by_revision.items():
        bundle = bundles_by_revision.get(revision_number)
        if bundle is None:
            raise ValueError(
                "resolution event history requires its matching analysis bundle"
            )
        runtime_keys = {
            (item.criterion_id, item.reviewer, item.evidence_level)
            for item in bundle.runtime_evidence
        }
        decisions: dict[str, HumanDecision] = {}
        for event in events:
            if event.criterion_id is not None and event.decision is not None:
                if event.decision is HumanDecision.MANUALLY_VERIFIED and (
                    event.criterion_id,
                    event.reviewer,
                    event.claimed_evidence_level,
                ) not in runtime_keys:
                    raise ValueError(
                        "manual verification events require matching runtime evidence"
                    )
                decisions[event.criterion_id] = event.decision
                continue
            if event.final_acceptance is True and (
                not _review_allows_final_acceptance(bundle)
                or any(
                    decisions.get(criterion.criterion_id)
                    not in _FINAL_ACCEPTANCE_DECISIONS
                    for criterion in bundle.criteria
                )
            ):
                raise ValueError(
                    "positive final acceptance event was recorded before prerequisites"
                )


def validated_review_bundle(bundle: ReviewBundle) -> ReviewBundle:
    """Return an independently validated bundle with reproducible gate truth."""
    validated = ReviewBundle.model_validate(bundle.model_dump(mode="python"))
    _require_deterministic_gate(validated, "analysis bundle")
    _require_evidence_integrity(validated, "analysis bundle")
    return validated


def validated_review_state(state: ReviewState) -> ReviewState:
    """Return validated lifecycle state with deterministic active and historical gates."""
    validated = ReviewState.model_validate(state.model_dump(mode="python"))
    if validated.bundle is not None:
        _require_deterministic_gate(validated.bundle, "analysis bundle")
    for historical_bundle in validated.analysis_history:
        _require_deterministic_gate(historical_bundle, "analysis history bundle")
        revision_number = historical_bundle.criteria_revision_number
        if revision_number != "unknown":
            expected_resolutions = current_resolutions(
                validated.resolution_events, revision_number
            )
            if historical_bundle.resolutions != expected_resolutions:
                raise ValueError(
                    "historical bundle resolutions must match historical resolution events"
                )
            expected_final_acceptance = final_acceptance(
                validated.resolution_events, revision_number
            )
            if (
                historical_bundle.review.final_acceptance
                != expected_final_acceptance
            ):
                raise ValueError(
                    "historical bundle final acceptance must match historical "
                    "resolution events"
                )
        _require_evidence_integrity(historical_bundle, "analysis history bundle")
    active_revision = validated.criteria_revision.number
    active_events = [
        event
        for event in validated.resolution_events
        if event.criteria_revision_number == active_revision
    ]
    if validated.bundle is None and active_events:
        raise ValueError("active resolution events require an active analysis bundle")
    if validated.bundle is not None:
        expected_resolutions = current_resolutions(
            validated.resolution_events, active_revision
        )
        if validated.bundle.resolutions != expected_resolutions:
            raise ValueError(
                "active bundle resolutions must match active resolution events"
            )
    expected_final_acceptance = final_acceptance(
        validated.resolution_events, active_revision
    )
    if validated.review.final_acceptance != expected_final_acceptance:
        raise ValueError("final acceptance must match active resolution events")
    _require_event_history_integrity(validated)
    if validated.bundle is not None:
        _require_evidence_integrity(validated.bundle, "analysis bundle")
    return validated
