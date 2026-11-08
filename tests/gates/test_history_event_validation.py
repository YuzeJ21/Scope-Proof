"""CONSTRUCTED histories: ordered projections and bounded validation work."""

from itertools import zip_longest

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates import validation
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.resolution_events import current_resolutions, final_acceptance
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent


def mixed_history():
    """Revision 2 has no decisions; revision 4 revokes an earlier acceptance."""
    state = new_review_state(build_demo_review())
    template = state.bundle
    groups = []
    for revision in range(1, 5):
        events = []
        if revision != 2:
            events = [ResolutionEvent(
                event_id=f"constructed-{revision}-initial",
                criterion_id="AC-03", decision=HumanDecision.CHANGE_REQUIRED,
                criteria_revision_number=revision,
                comment="CONSTRUCTED initial decision; no human testing.",
            )]
            events.extend(ResolutionEvent(
                event_id=f"constructed-{revision}-{criterion.criterion_id}",
                criterion_id=criterion.criterion_id, decision=HumanDecision.ACCEPTED,
                criteria_revision_number=revision,
                comment=f"CONSTRUCTED revision {revision} acceptance; no human evidence.",
            ) for criterion in template.criteria)
            events.append(ResolutionEvent(
                event_id=f"constructed-{revision}-final", final_acceptance=True,
                criteria_revision_number=revision,
            ))
            if revision == 4:
                events.extend([
                    ResolutionEvent(
                        event_id="constructed-4-revocation", final_acceptance=False,
                        criteria_revision_number=revision,
                    ),
                    ResolutionEvent(
                        event_id="constructed-4-replacement", criterion_id="AC-03",
                        decision=HumanDecision.CHANGE_REQUIRED,
                        criteria_revision_number=revision,
                        comment="CONSTRUCTED replacement after revocation.",
                    ),
                ])
        for event in events:
            event.reviewer = "CONSTRUCTED automatic test actor"
        groups.append(events)
    # Cross-revision interleaving is legal; only each revision's list order matters.
    state.resolution_events = [
        event for row in zip_longest(*groups) for event in row if event is not None
    ]
    bundles = []
    for revision in range(1, 5):
        bundle = template.model_copy(deep=True)
        bundle.criteria_revision_number = revision
        bundle.resolutions = current_resolutions(state.resolution_events, revision)
        bundle.review.final_acceptance = final_acceptance(state.resolution_events, revision)
        bundle.gate = evaluate_gate(
            bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
            bundle.evidence, bundle.file_scope_decisions,
        )
        bundles.append(bundle)
    state.criteria_revision.number = 4
    state.analysis_history = bundles[:-1]
    state.bundle = bundles[-1]
    state.review = state.bundle.review.model_copy(deep=True)
    return state


def test_projection_work_is_linear_in_retained_events(monkeypatch):
    state = mixed_history()
    before = state.model_dump_json()
    elements = 0

    def counted(original):
        def project(events, revision):
            nonlocal elements
            elements += len(events)
            return original(events, revision)
        return project

    monkeypatch.setattr(validation, "current_resolutions", counted(current_resolutions))
    monkeypatch.setattr(validation, "final_acceptance", counted(final_acceptance))
    result = validation.validated_review_state(state)

    assert result.model_dump_json() == before
    assert state.model_dump_json() == before
    # Each event may participate in both projections, never once per retained bundle.
    assert elements <= 2 * len(state.resolution_events)


def test_interleaved_history_preserves_latest_decisions_and_revocation():
    state = mixed_history()
    before = state.model_dump_json()
    result = validation.validated_review_state(state)

    assert result.model_dump_json() == before
    assert [b.review.final_acceptance for b in result.analysis_history] == [True, False, True]
    assert result.analysis_history[1].resolutions == []
    assert result.review.final_acceptance is False
    active = {r.criterion_id: r for r in result.bundle.resolutions}
    historical = {r.criterion_id: r for r in result.analysis_history[0].resolutions}
    assert active["AC-03"].decision is HumanDecision.CHANGE_REQUIRED
    assert active["AC-03"].comment == "CONSTRUCTED replacement after revocation."
    assert historical["AC-03"].decision is HumanDecision.ACCEPTED
    # A subsequent validation must not reuse an index of this previously valid state.
    state.resolution_events.pop()
    with pytest.raises(ValueError, match="active bundle resolutions must match"):
        validation.validated_review_state(state)


def test_unknown_history_preserves_unattributed_events_without_inventing_ownership():
    state = mixed_history()
    state.analysis_history[0].criteria_revision_number = "unknown"
    before = state.model_dump_json()

    assert validation.validated_review_state(state).model_dump_json() == before
    assert state.model_dump_json() == before


def test_unmatched_known_revision_events_remain_rejected():
    state = mixed_history()
    state.analysis_history.pop(0)

    with pytest.raises(ValueError, match="event history requires its matching analysis bundle"):
        validation.validated_review_state(state)
