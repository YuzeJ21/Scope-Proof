from datetime import timedelta

import pytest
from pydantic import ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews import attach_analysis
from scopeproof_core.reviews.lifecycle import (
    ResolutionEventStatus,
    append_resolution,
    append_runtime_evidence,
    confirm_criteria,
    current_resolutions,
    new_review_state,
    resolution_event_statuses,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    CheckState,
    Criterion,
    EvidenceLevel,
    Finding,
    FindingStatus,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
    Review,
    ReviewBundle,
    RuntimeEvidence,
)


def initial_state():
    review = Review(
        review_id="review-1",
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        criteria_confirmed=True,
    )
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    finding = Finding(
        criterion_id="AC-01",
        status=FindingStatus.EVIDENCE_FOUND,
        evidence_level=EvidenceLevel.E1,
        reason="Candidate found",
        recommended_action="Review evidence",
    )
    bundle = ReviewBundle(
        review=review,
        source_text="Export CSV",
        criteria=[criterion],
        evidence=[],
        findings=[finding],
        gate=evaluate_gate(review, [criterion], [finding], []),
    )
    return new_review_state(bundle)


def analysis_bundle_for(
    state,
    *,
    criteria: list[Criterion] | None = None,
    source_text: str | None = None,
    review: Review | None = None,
    resolutions: list[HumanResolution] | None = None,
) -> ReviewBundle:
    analysis_criteria = criteria or [
        criterion.model_copy(deep=True) for criterion in state.criteria_revision.criteria
    ]
    analysis_review = review or state.review.model_copy(
        update={
            "review_id": "generated-review",
            "created_at": state.review.created_at + timedelta(seconds=1),
        }
    )
    findings = [
        Finding(
            criterion_id=criterion.criterion_id,
            status=FindingStatus.EVIDENCE_FOUND,
            evidence_level=EvidenceLevel.E1,
            reason="Candidate found for the edited criterion",
            recommended_action="Review evidence",
        )
        for criterion in analysis_criteria
    ]
    analysis_resolutions = resolutions or []
    return ReviewBundle(
        review=analysis_review,
        source_text=source_text or state.criteria_revision.source_text,
        criteria=analysis_criteria,
        evidence=[],
        findings=findings,
        resolutions=analysis_resolutions,
        gate=evaluate_gate(
            analysis_review,
            analysis_criteria,
            findings,
            analysis_resolutions,
        ),
    )


def test_attach_analysis_preserves_reanalysis_lineage() -> None:
    state = append_resolution(
        initial_state(),
        ResolutionEvent(
            event_id="event-1",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Reviewed the original analysis",
        ),
    )
    original_review_id = state.review.review_id
    revised = revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_criteria(revised)
    bundle = analysis_bundle_for(confirmed)
    bundle.criteria_revision_number = 99

    attached = attach_analysis(confirmed, bundle)

    assert attached.review.review_id == original_review_id
    assert attached.criteria_revision.number == 2
    assert attached.criteria_revision == confirmed.criteria_revision
    assert attached.analysis_history == confirmed.analysis_history
    assert attached.resolution_events == confirmed.resolution_events
    assert attached.bundle is not None
    assert attached.bundle.review == attached.review
    assert attached.bundle.criteria == confirmed.criteria_revision.criteria
    assert attached.bundle.source_text == "Export filtered CSV"
    assert attached.bundle.criteria_revision_number == 2
    assert attached.bundle.resolutions == []
    assert attached.review.final_acceptance is False

    bundle.review.review_id = "caller-mutation"
    bundle.criteria[0].text = "Caller mutation"
    bundle.source_text = "Caller mutation"
    bundle.criteria_revision_number = 100

    assert attached.bundle.review.review_id == original_review_id
    assert attached.bundle.criteria[0].text == "Export filtered CSV"
    assert attached.bundle.source_text == "Export filtered CSV"
    assert attached.bundle.criteria_revision_number == 2


def test_skipped_analysis_history_records_exact_criteria_revisions() -> None:
    revision_one = initial_state()
    revision_two = confirm_criteria(
        revise_criteria(
            revision_one,
            [Criterion(criterion_id="AC-01", text="Export CSV with headers")],
            "Export CSV with headers",
        )
    )
    revision_three = confirm_criteria(
        revise_criteria(
            revision_two,
            [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
            "Export filtered CSV",
        )
    )
    analyzed_revision_three = attach_analysis(
        revision_three, analysis_bundle_for(revision_three)
    )

    revision_four = revise_criteria(
        analyzed_revision_three,
        [Criterion(criterion_id="AC-01", text="Export sorted filtered CSV")],
        "Export sorted filtered CSV",
    )

    assert [
        bundle.criteria_revision_number for bundle in revision_four.analysis_history
    ] == [1, 3]
    assert revision_four.criteria_revision.number == 4
    assert revision_four.bundle is None


def test_attach_analysis_rejects_an_existing_active_bundle() -> None:
    state = initial_state()
    assert state.bundle is not None

    with pytest.raises(
        ValueError,
        match="analysis attachment requires a pending revision without an active bundle",
    ):
        attach_analysis(state, state.bundle)


def test_attach_analysis_rejects_an_unconfirmed_revision() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )

    with pytest.raises(
        ValueError, match="analysis attachment requires a confirmed criteria revision"
    ):
        attach_analysis(revised, analysis_bundle_for(revised))


def test_attach_analysis_rejects_mismatched_criteria() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_criteria(revised)
    mismatched = [Criterion(criterion_id="AC-01", text="Export JSON")]

    with pytest.raises(
        ValueError, match="attached analysis criteria must match the active revision"
    ):
        attach_analysis(
            confirmed,
            analysis_bundle_for(confirmed, criteria=mismatched),
        )


def test_attach_analysis_rejects_mismatched_source_text() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_criteria(revised)

    with pytest.raises(
        ValueError, match="attached analysis source must match the active revision"
    ):
        attach_analysis(
            confirmed,
            analysis_bundle_for(confirmed, source_text="Export JSON"),
        )


def test_attach_analysis_rejects_mismatched_review_provenance() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_criteria(revised)
    mismatched_review = confirmed.review.model_copy(
        update={"review_id": "generated-review", "head_sha": "different-head"}
    )

    with pytest.raises(
        ValueError, match="attached analysis review must match the lifecycle review"
    ):
        attach_analysis(
            confirmed,
            analysis_bundle_for(confirmed, review=mismatched_review),
        )


def test_attach_analysis_rejects_preloaded_human_resolutions() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_criteria(revised)
    resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Preloaded decision",
        )
    ]

    with pytest.raises(
        ValueError, match="attached analysis must not contain human resolutions"
    ):
        attach_analysis(
            confirmed,
            analysis_bundle_for(confirmed, resolutions=resolutions),
        )


def test_attach_analysis_rejects_preloaded_final_acceptance() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_criteria(revised)
    accepted_review = confirmed.review.model_copy(
        update={"review_id": "generated-review", "final_acceptance": True}
    )

    with pytest.raises(
        ValueError, match="attached analysis must not contain final acceptance"
    ):
        attach_analysis(
            confirmed,
            analysis_bundle_for(confirmed, review=accepted_review),
        )


def test_attach_analysis_revalidates_a_mutated_bundle() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_criteria(revised)
    bundle = analysis_bundle_for(confirmed)
    bundle.criteria[0].text = ""

    with pytest.raises(ValidationError, match="String should have at least 1 character"):
        attach_analysis(confirmed, bundle)


def test_new_review_state_revalidates_the_supplied_bundle() -> None:
    bundle = initial_state().bundle
    assert bundle is not None
    bundle.criteria[0].text = ""

    with pytest.raises(ValidationError, match="String should have at least 1 character"):
        new_review_state(bundle)


def test_new_review_state_rejects_a_non_deterministic_gate() -> None:
    bundle = initial_state().bundle
    assert bundle is not None
    assert bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    bundle.gate = bundle.gate.model_copy(update={"verdict": GateVerdict.READY})

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        new_review_state(bundle)


def test_new_review_state_rejects_preloaded_human_resolutions() -> None:
    bundle = initial_state().bundle
    assert bundle is not None
    bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Preloaded decision",
        )
    ]
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="initial analysis bundle must not contain human resolutions"
    ):
        new_review_state(bundle)


def test_new_review_state_rejects_preloaded_final_acceptance() -> None:
    bundle = initial_state().bundle
    assert bundle is not None
    bundle.review.final_acceptance = True
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )

    with pytest.raises(
        ValueError, match="initial analysis bundle must not contain final acceptance"
    ):
        new_review_state(bundle)


def test_new_review_state_does_not_alias_the_supplied_bundle() -> None:
    bundle = initial_state().bundle
    assert bundle is not None
    bundle.criteria_revision_number = 99

    state = new_review_state(bundle)
    bundle.review.review_id = "caller-mutation"
    bundle.criteria[0].text = "Caller mutation"
    bundle.source_text = "Caller mutation"

    assert state.review.review_id == "review-1"
    assert state.criteria_revision.criteria[0].text == "Export CSV"
    assert state.criteria_revision.source_text == "Export CSV"
    assert state.bundle is not None
    assert state.bundle.review.review_id == "review-1"
    assert state.bundle.criteria[0].text == "Export CSV"
    assert state.bundle.source_text == "Export CSV"
    assert state.bundle.criteria_revision_number == 1

    bundle.criteria_revision_number = 99

    assert state.bundle.criteria_revision_number == 1


def test_editing_confirmed_criteria_creates_revision_and_invalidates_analysis() -> None:
    state = initial_state()
    revised = revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )

    assert revised.criteria_revision.number == 2
    assert revised.criteria_revision.criteria[0].text == "Export filtered CSV"
    assert revised.review.criteria_confirmed is False
    assert revised.bundle is None
    assert len(revised.analysis_history) == 1


@pytest.mark.parametrize("source_text", ["", "   ", "\t", "\n\r"])
def test_revise_criteria_rejects_blank_requirements_source(source_text: str) -> None:
    state = initial_state()

    with pytest.raises(
        ValidationError, match="requirements source must contain non-whitespace text"
    ):
        revise_criteria(state, state.criteria_revision.criteria, source_text)


def test_revise_criteria_preserves_valid_requirements_source() -> None:
    source_text = "  Export filtered CSV\n"

    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        source_text,
    )

    assert revised.criteria_revision.source_text == source_text


def test_revise_criteria_revalidates_supplied_criteria() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export filtered CSV")
    criterion.text = ""

    with pytest.raises(ValidationError, match="String should have at least 1 character"):
        revise_criteria(initial_state(), [criterion], "Updated requirements")


def test_revised_criteria_do_not_alias_supplied_objects() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export filtered CSV")

    revised = revise_criteria(initial_state(), [criterion], "Updated requirements")
    criterion.text = "Caller mutation"

    assert revised.criteria_revision.criteria[0].text == "Export filtered CSV"


def test_confirmation_keeps_revision_and_unblocks_future_analysis() -> None:
    revised = revise_criteria(
        initial_state(), [Criterion(criterion_id="AC-01", text="Export filtered CSV")], "Updated"
    )

    confirmed = confirm_criteria(revised)

    assert confirmed.criteria_revision.number == 2
    assert confirmed.review.criteria_confirmed is True
    assert confirmed.bundle is None
    assert confirmed.criteria_revision.confirmed is True
    assert confirmed.criteria_revision.confirmed_at is not None

    reopened = type(confirmed).model_validate(confirmed.model_dump(mode="python"))

    assert reopened == confirmed


def test_confirmation_rejects_an_active_analysis_bundle() -> None:
    with pytest.raises(
        ValueError,
        match="criteria confirmation requires a pending revision without an active bundle",
    ):
        confirm_criteria(initial_state())


@pytest.mark.parametrize(
    "operation",
    [
        "revise_criteria",
        "confirm_criteria",
        "attach_analysis",
        "append_resolution",
        "append_runtime_evidence",
    ],
)
def test_lifecycle_operations_revalidate_active_review_identity(operation: str) -> None:
    state = initial_state()
    divergent = state.model_copy(
        update={
            "review": state.review.model_copy(update={"head_sha": "different-head"})
        }
    )

    with pytest.raises(
        ValueError, match="active bundle review must match lifecycle review"
    ):
        if operation == "revise_criteria":
            revise_criteria(
                divergent,
                divergent.criteria_revision.criteria,
                divergent.criteria_revision.source_text,
            )
        elif operation == "confirm_criteria":
            confirm_criteria(divergent)
        elif operation == "attach_analysis":
            assert state.bundle is not None
            attach_analysis(divergent, state.bundle)
        elif operation == "append_resolution":
            append_resolution(
                divergent,
                ResolutionEvent(event_id="identity-probe", final_acceptance=False),
            )
        else:
            append_runtime_evidence(
                divergent,
                RuntimeEvidence(
                    criterion_id="AC-01",
                    artifact_reference="local-identity-probe",
                    scenario="Reject contradictory lifecycle state",
                    environment="local",
                    result="observed",
                    reviewer="Codex",
                    evidence_level=EvidenceLevel.E3,
                ),
            )


def test_resolution_events_preserve_history_and_latest_decision_controls_gate() -> None:
    state = initial_state()
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="event-1",
            criterion_id="AC-01",
            decision=HumanDecision.REJECTED_FINDING,
            comment="Evidence is elsewhere",
        ),
    )
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="event-2",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Reviewed candidate evidence",
        ),
    )

    current = current_resolutions(state.resolution_events)
    assert len(state.resolution_events) == 2
    assert current[0].decision is HumanDecision.ACCEPTED
    assert state.bundle is not None
    assert state.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW


def test_resolution_event_requires_an_active_analysis_bundle() -> None:
    pending = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Updated requirements",
    )
    confirmed = confirm_criteria(pending)

    with pytest.raises(
        ValueError, match="Run a confirmed analysis before recording a resolution"
    ):
        append_resolution(
            confirmed,
            ResolutionEvent(final_acceptance=True, comment="Premature acceptance"),
        )


def test_resolution_event_must_reference_an_active_criterion() -> None:
    with pytest.raises(
        ValueError, match="resolution event must reference a criterion in the active review"
    ):
        append_resolution(
            initial_state(),
            ResolutionEvent(
                criterion_id="AC-99",
                decision=HumanDecision.ACCEPTED,
                comment="Unknown criterion",
            ),
        )


def test_resolution_event_is_revalidated_before_it_can_make_gate_ready() -> None:
    state = append_resolution(
        initial_state(),
        ResolutionEvent(final_acceptance=True, comment="Final review complete"),
    )
    event = ResolutionEvent(
        criterion_id="AC-01",
        decision=HumanDecision.ACCEPTED,
        comment="Reviewed candidate evidence",
    )
    event.claimed_evidence_level = EvidenceLevel.E4

    with pytest.raises(
        ValidationError,
        match="claimed evidence level is reserved for manually verified decisions",
    ):
        append_resolution(state, event)

    assert state.bundle is not None
    assert state.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW


def test_resolution_event_statuses_identify_latest_event_for_each_target() -> None:
    events = [
        ResolutionEvent(
            event_id="criterion-old",
            criterion_id="AC-01",
            decision=HumanDecision.REJECTED_FINDING,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="acceptance-old",
            final_acceptance=False,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="criterion-current",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="acceptance-current",
            final_acceptance=True,
            criteria_revision_number=1,
        ),
    ]

    assert resolution_event_statuses(events, active_revision_number=1) == [
        ResolutionEventStatus.SUPERSEDED,
        ResolutionEventStatus.SUPERSEDED,
        ResolutionEventStatus.CURRENT,
        ResolutionEventStatus.CURRENT,
    ]


def test_resolution_event_statuses_separate_prior_revisions() -> None:
    events = [
        ResolutionEvent(
            event_id="revision-1",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            criteria_revision_number=1,
        ),
        ResolutionEvent(
            event_id="revision-2",
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            criteria_revision_number=2,
        ),
    ]

    assert resolution_event_statuses(events, active_revision_number=2) == [
        ResolutionEventStatus.PRIOR_REVISION,
        ResolutionEventStatus.CURRENT,
    ]


def test_append_resolution_rejects_an_existing_event_id() -> None:
    state = append_resolution(
        initial_state(),
        ResolutionEvent(
            event_id="event-1",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
        ),
    )

    with pytest.raises(ValueError, match="resolution event ID must be unique"):
        append_resolution(
            state,
            ResolutionEvent(
                event_id="event-1",
                final_acceptance=True,
                comment="Release approved",
            ),
        )


def test_final_acceptance_event_allows_ready_after_criterion_resolution() -> None:
    state = append_resolution(
        initial_state(),
        ResolutionEvent(
            event_id="event-1",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
        ),
    )
    state = append_resolution(
        state,
        ResolutionEvent(event_id="event-2", final_acceptance=True, comment="Release approved"),
    )

    assert state.review.final_acceptance is True
    assert state.bundle is not None
    assert state.bundle.gate.verdict is GateVerdict.READY


def test_runtime_evidence_is_append_only_and_does_not_change_gate() -> None:
    state = initial_state()
    updated = append_runtime_evidence(
        state,
        RuntimeEvidence(
            criterion_id="AC-01",
            artifact_reference="https://example.test/run/1",
            scenario="Export CSV",
            environment="staging",
            result="passed",
            reviewer="QA",
            evidence_level=EvidenceLevel.E3,
        ),
    )

    assert state.bundle is not None and state.bundle.runtime_evidence == []
    assert updated.bundle is not None
    assert updated.bundle.runtime_evidence[0].artifact_reference.endswith("/1")
    assert updated.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW


def test_runtime_evidence_is_revalidated_before_append() -> None:
    evidence = RuntimeEvidence(
        criterion_id="AC-01",
        artifact_reference="https://example.test/run/1",
        scenario="Export CSV",
        environment="staging",
        result="passed",
        reviewer="QA",
        evidence_level=EvidenceLevel.E3,
    )
    evidence.evidence_level = EvidenceLevel.E1

    with pytest.raises(ValidationError, match="runtime evidence requires E3 or E4"):
        append_runtime_evidence(initial_state(), evidence)


def test_runtime_evidence_requires_an_active_analysis_bundle() -> None:
    pending = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Updated requirements",
    )
    confirmed = confirm_criteria(pending)

    with pytest.raises(
        ValueError, match="Run a confirmed analysis before recording runtime evidence"
    ):
        append_runtime_evidence(
            confirmed,
            RuntimeEvidence(
                criterion_id="AC-01",
                artifact_reference="https://example.test/run/1",
                scenario="Export CSV",
                environment="staging",
                result="passed",
                reviewer="QA",
                evidence_level=EvidenceLevel.E3,
            ),
        )


def test_runtime_evidence_must_reference_an_active_criterion() -> None:
    with pytest.raises(
        ValueError, match="runtime evidence must reference a criterion in the active review"
    ):
        append_runtime_evidence(
            initial_state(),
            RuntimeEvidence(
                criterion_id="AC-99",
                artifact_reference="https://example.test/run/1",
                scenario="Export CSV",
                environment="staging",
                result="passed",
                reviewer="QA",
                evidence_level=EvidenceLevel.E3,
            ),
        )


def test_appended_runtime_evidence_does_not_alias_the_supplied_object() -> None:
    evidence = RuntimeEvidence(
        criterion_id="AC-01",
        artifact_reference="https://example.test/run/1",
        scenario="Export CSV",
        environment="staging",
        result="passed",
        reviewer="QA",
        evidence_level=EvidenceLevel.E3,
        limitations=["Browser only"],
    )

    updated = append_runtime_evidence(initial_state(), evidence)
    evidence.result = ""
    evidence.limitations.append("Caller mutation")

    assert updated.bundle is not None
    assert updated.bundle.runtime_evidence[0].result == "passed"
    assert updated.bundle.runtime_evidence[0].limitations == ["Browser only"]
