"""Constructed decision audit; product imports only, no storage or application IO."""

from datetime import UTC, datetime, timedelta, timezone

from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    attach_analysis,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent, ReviewState


def resolution_audit_state() -> ReviewState:
    bundle = build_demo_review()
    bundle.review.review_id = "constructed-resolution-audit-review"
    state = new_review_state(bundle)
    state = append_resolution(state, ResolutionEvent(
        event_id="r1-old-accept", criterion_id="AC-01", decision=HumanDecision.ACCEPTED,
        reviewer="Constructed prior reviewer", comment="Prior revision candidate review",
        timestamp=datetime(2027, 1, 1, tzinfo=UTC),
    ))
    state = revise_criteria(
        state, state.criteria_revision.criteria, "Constructed revised requirements",
    )
    provenance = build_criteria_source_provenance(
        source_uri="https://example.test/constructed-audit-requirements",
        source_revision="constructed-requirements-v2",
        source_text=state.criteria_revision.source_text,
        criteria=state.criteria_revision.criteria,
        confirmed_by="Constructed criteria owner",
        confirmed_at=state.criteria_revision.created_at + timedelta(seconds=1),
    )
    state = confirm_criteria(state, provenance)
    incoming = build_demo_review()
    incoming.review = state.review.model_copy(deep=True)
    incoming.source_text = state.criteria_revision.source_text
    incoming.criteria = [item.model_copy(deep=True) for item in state.criteria_revision.criteria]
    state = attach_analysis(state, incoming)
    state = append_resolution(state, ResolutionEvent(
        event_id="r2-old-change", criterion_id="AC-01", decision=HumanDecision.CHANGE_REQUIRED,
        reviewer="Constructed earlier reviewer", comment="Earlier request for changes",
        evidence_url="https://example.test/earlier-observation",
        timestamp=datetime(2026, 10, 31, 16, tzinfo=UTC),
    ))
    state = append_resolution(state, ResolutionEvent(
        event_id="r2-current-accept", criterion_id="AC-01", decision=HumanDecision.ACCEPTED,
        reviewer="Constructed current reviewer", comment="Current candidate accepted with note",
        evidence_url="https://example.test/current-observation?case=1&mode=recorded",
        timestamp=datetime(2026, 10, 31, 10, tzinfo=timezone(timedelta(hours=-4))),
    ))
    for position, criterion in enumerate(state.criteria_revision.criteria[1:], start=2):
        state = append_resolution(state, ResolutionEvent(
            event_id=f"r2-ac{position:02d}-accept", criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED, reviewer="Constructed current reviewer",
            comment="Constructed candidate review; not independent runtime proof",
            timestamp=datetime(2026, 10, 31, 10 + position, tzinfo=UTC),
        ))
    state = append_resolution(state, ResolutionEvent(
        event_id="r2-final-true", final_acceptance=True,
        reviewer="Constructed final reviewer", comment="Constructed final flag true",
        timestamp=datetime(2026, 10, 31, 15, tzinfo=UTC),
    ))
    return append_resolution(state, ResolutionEvent(
        event_id="r2-final-false", final_acceptance=False,
        reviewer="Constructed final reviewer", comment="Constructed final flag false",
        timestamp=datetime(2026, 10, 31, 9, tzinfo=UTC),
    ))


def mixed_legacy_resolution_audit_state() -> ReviewState:
    """A supported legacy mixed field shape; the review-level false flag applies."""
    bundle = build_demo_review()
    bundle.review.review_id = "constructed-mixed-resolution-audit-review"
    return append_resolution(new_review_state(bundle), ResolutionEvent(
        event_id="constructed-mixed-final-false", final_acceptance=False,
        decision=HumanDecision.ACCEPTED, reviewer="Constructed legacy recorder 测试",
        timestamp=datetime(2026, 10, 31, 12, tzinfo=UTC),
    ))
