import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import (
    validated_review_bundle,
    validated_review_state,
)
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
    RuntimeEvidence,
)


def test_validated_review_bundle_rejects_a_non_deterministic_gate() -> None:
    bundle = build_demo_review()
    bundle.gate = bundle.gate.model_copy(update={"verdict": GateVerdict.READY})

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        validated_review_bundle(bundle)


def test_validated_review_state_rejects_a_non_deterministic_historical_gate() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.analysis_history[0].gate = revised.analysis_history[0].gate.model_copy(
        update={"verdict": GateVerdict.READY}
    )

    with pytest.raises(
        ValueError,
        match="analysis history bundle gate must match deterministic evaluation",
    ):
        validated_review_state(revised)


def test_validated_review_state_rejects_forged_ready_historical_projection_without_events() -> (
    None
):
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    historical = revised.analysis_history[0]
    historical.review.final_acceptance = True
    historical.resolutions = [
        HumanResolution(
            criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Forged historical acceptance",
        )
        for criterion in historical.criteria
    ]
    historical.gate = evaluate_gate(
        historical.review,
        historical.criteria,
        historical.findings,
        historical.resolutions,
    )
    assert historical.gate.verdict is GateVerdict.READY

    with pytest.raises(
        ValueError,
        match="historical bundle resolutions must match historical resolution events",
    ):
        validated_review_state(revised)


def test_validated_review_state_rejects_forged_historical_final_acceptance_without_event() -> (
    None
):
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    historical = revised.analysis_history[0]
    historical.review.final_acceptance = True
    historical.gate = evaluate_gate(
        historical.review,
        historical.criteria,
        historical.findings,
        historical.resolutions,
    )

    with pytest.raises(
        ValueError,
        match=(
            "historical bundle final acceptance must match historical "
            "resolution events"
        ),
    ):
        validated_review_state(revised)


def test_validated_review_state_rejects_resolutions_without_active_events() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Forged acceptance",
        )
        for criterion in state.bundle.criteria
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="active bundle resolutions must match active resolution events"
    ):
        validated_review_state(state)


def test_validated_review_bundle_rejects_final_acceptance_without_resolutions() -> None:
    bundle = build_demo_review()
    bundle.review.final_acceptance = True
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="final acceptance requires accepted current resolutions"
    ):
        validated_review_bundle(bundle)


def test_validated_review_bundle_rejects_unpaired_manual_verification() -> None:
    bundle = build_demo_review()
    bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            claimed_evidence_level=EvidenceLevel.E3,
            reviewer="QA",
            comment="Observed the scenario",
        )
    ]
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="manually verified resolutions require matching runtime evidence"
    ):
        validated_review_bundle(bundle)


def test_validated_review_bundle_accepts_paired_manual_verification() -> None:
    bundle = build_demo_review()
    bundle.runtime_evidence = [
        RuntimeEvidence(
            criterion_id="AC-01",
            artifact_reference="https://example.test/run/1",
            scenario="Export CSV",
            environment="staging",
            result="passed",
            reviewer="QA",
            evidence_level=EvidenceLevel.E3,
        )
    ]
    bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            claimed_evidence_level=EvidenceLevel.E3,
            reviewer="QA",
            comment="Observed the scenario",
        )
    ]
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )

    assert validated_review_bundle(bundle) == bundle


def test_validated_review_state_rejects_unpaired_manual_verification_event() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    event = ResolutionEvent(
        event_id="manual-without-runtime",
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        claimed_evidence_level=EvidenceLevel.E3,
        reviewer="QA",
        comment="Observed the scenario",
        criteria_revision_number=1,
    )
    state.resolution_events = [event]
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            claimed_evidence_level=EvidenceLevel.E3,
            reviewer="QA",
            comment="Observed the scenario",
            timestamp=event.timestamp,
        )
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match=r"manual.*verifi.*matching runtime evidence"
    ):
        validated_review_state(state)


def test_validated_review_state_rejects_final_acceptance_recorded_too_early() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    final_event = ResolutionEvent(
        event_id="premature-final",
        final_acceptance=True,
        criteria_revision_number=1,
    )
    criterion_events = [
        ResolutionEvent(
            event_id=f"accepted-{criterion.criterion_id}",
            criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED,
            criteria_revision_number=1,
        )
        for criterion in state.bundle.criteria
    ]
    state.resolution_events = [final_event, *criterion_events]
    state.review.final_acceptance = True
    state.bundle.review.final_acceptance = True
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id=event.criterion_id,
            decision=HumanDecision.ACCEPTED,
            timestamp=event.timestamp,
        )
        for event in criterion_events
        if event.criterion_id is not None
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )
    assert state.bundle.gate.verdict is GateVerdict.READY

    with pytest.raises(
        ValueError, match="positive final acceptance event was recorded before prerequisites"
    ):
        validated_review_state(state)


def test_validated_review_state_rejects_superseded_unpaired_manual_event() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    manual_event = ResolutionEvent(
        event_id="unpaired-manual",
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        claimed_evidence_level=EvidenceLevel.E3,
        reviewer="QA",
        comment="Observed the scenario",
        criteria_revision_number=1,
    )
    accepted_event = ResolutionEvent(
        event_id="superseding-acceptance",
        criterion_id="AC-01",
        decision=HumanDecision.ACCEPTED,
        criteria_revision_number=1,
    )
    state.resolution_events = [manual_event, accepted_event]
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            timestamp=accepted_event.timestamp,
        )
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="manual verification events require matching runtime evidence"
    ):
        validated_review_state(state)


def test_validated_review_state_rejects_final_acceptance_without_active_event() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    state.review.final_acceptance = True
    state.bundle.review.final_acceptance = True
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="final acceptance must match active resolution events"
    ):
        validated_review_state(state)


def test_validated_review_state_rejects_active_events_without_analysis() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.resolution_events.append(
        ResolutionEvent(
            final_acceptance=True,
            comment="Forged bundleless acceptance",
            criteria_revision_number=revised.criteria_revision.number,
        )
    )

    with pytest.raises(
        ValueError, match="active resolution events require an active analysis bundle"
    ):
        validated_review_state(revised)


def test_validated_review_state_rejects_duplicate_resolution_event_ids() -> None:
    state = new_review_state(build_demo_review())
    state.resolution_events = [
        ResolutionEvent(
            event_id="duplicate-event",
            final_acceptance=False,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="duplicate-event",
            final_acceptance=False,
            criteria_revision_number=1,
        ),
    ]

    with pytest.raises(ValueError, match="resolution event IDs must be unique"):
        validated_review_state(state)


@pytest.mark.parametrize("revision_number", [0, 2])
def test_validated_review_state_rejects_events_outside_revision_lineage(
    revision_number: int,
) -> None:
    state = new_review_state(build_demo_review())
    state.resolution_events.append(
        ResolutionEvent(
            event_id=f"revision-{revision_number}",
            final_acceptance=False,
            criteria_revision_number=revision_number,
        )
    )

    with pytest.raises(
        ValueError,
        match="resolution event revisions must reference an existing criteria revision",
    ):
        validated_review_state(state)


def test_validated_review_state_preserves_prior_revision_events() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.resolution_events.append(
        ResolutionEvent(
            event_id="prior-acceptance",
            final_acceptance=False,
            criteria_revision_number=1,
        )
    )

    validated = validated_review_state(revised)

    assert validated.resolution_events[0].event_id == "prior-acceptance"
    assert validated.review.final_acceptance is False
