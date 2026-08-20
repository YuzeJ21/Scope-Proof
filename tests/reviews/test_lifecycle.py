from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.importers.junit import (
    JUnitMappingSelection,
    build_junit_evidence_import,
)
from scopeproof_core.reviews import attach_analysis
from scopeproof_core.reviews.lifecycle import (
    ResolutionEventStatus,
    acceptance_requires_comment,
    append_external_verification,
    append_junit_evidence_import,
    append_resolution,
    append_runtime_evidence,
    can_record_final_acceptance,
    confirm_criteria,
    current_resolutions,
    new_review_state,
    resolution_event_statuses,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    CriteriaSourceProvenance,
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
    ReviewState,
    RuntimeEvidence,
    normalized_criteria_sha256,
    source_text_sha256,
)


def initial_state():
    review = Review(
        review_id="review-1",
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.PASSING,
            reason="Fixture",
            total_check_runs=1,
            successful_check_runs=1,
        ),
        criteria_confirmed=True,
    )
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    review.criteria_source_provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_text="Export CSV",
        criteria=[criterion],
        confirmed_by="Fixture owner",
        confirmed_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
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


def provenance_for_revision(
    state,
    *,
    source_text: str | None = None,
    criteria: list[Criterion] | None = None,
    confirmed_at: datetime | None = None,
) -> CriteriaSourceProvenance:
    return build_criteria_source_provenance(
        source_uri=(
            f"https://example.test/requirements/{state.criteria_revision.number}"
        ),
        source_revision=f"requirements-v{state.criteria_revision.number}",
        source_text=source_text or state.criteria_revision.source_text,
        criteria=criteria or state.criteria_revision.criteria,
        confirmed_by="Fixture owner",
        confirmed_at=confirmed_at
        or state.criteria_revision.created_at + timedelta(seconds=1),
    )


def confirm_pending_revision(state):
    return confirm_criteria(state, provenance_for_revision(state))


def test_new_review_state_copies_bundle_criteria_source_provenance() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_revision="requirements-v1",
        source_text="Export CSV",
        criteria=[criterion],
        confirmed_by="Product owner",
        confirmed_at=datetime(2026, 8, 2, 12, tzinfo=UTC),
    )
    review = Review(
        review_id="review-provenance",
        repository="acme/widget",
        pr_number=1,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.PASSING,
            reason="Fixture",
            total_check_runs=1,
            successful_check_runs=1,
        ),
        criteria_confirmed=True,
        criteria_source_provenance=provenance,
    )
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

    state = new_review_state(bundle)

    assert state.criteria_revision.source_provenance == provenance
    assert state.criteria_revision.confirmed_at == provenance.confirmed_at


def test_new_review_state_rejects_an_empty_criterion_bundle() -> None:
    state = initial_state()
    assert state.bundle is not None
    source_text = state.bundle.source_text
    empty_provenance = CriteriaSourceProvenance(
        source_uri="https://example.test/requirements",
        source_text_sha256=source_text_sha256(source_text),
        normalized_criteria_sha256=normalized_criteria_sha256([]),
        confirmed_by="Fixture owner",
        confirmed_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    empty_review = state.bundle.review.model_copy(
        update={"criteria_source_provenance": empty_provenance}
    )
    empty_bundle = state.bundle.model_copy(
        update={
            "review": empty_review,
            "criteria": [],
            "evidence": [],
            "retrieval_diagnostics": [],
            "findings": [],
            "gate": evaluate_gate(empty_review, [], [], []),
        }
    )

    with pytest.raises(ValueError, match="at least one criterion"):
        new_review_state(empty_bundle)


def test_revise_criteria_rejects_an_empty_new_revision() -> None:
    with pytest.raises(ValueError, match="at least one criterion"):
        revise_criteria(initial_state(), [], "Requirements remain available")


def test_new_review_state_rejects_bundle_without_criteria_source_provenance() -> None:
    bundle = initial_state().bundle
    assert bundle is not None
    bundle.review = bundle.review.model_copy(
        update={"criteria_source_provenance": None}
    )
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )

    with pytest.raises(
        ValueError,
        match="initial analysis bundle requires criteria source provenance",
    ):
        new_review_state(bundle)


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
    analysis_source_text = source_text or state.criteria_revision.source_text
    analysis_review = review or state.review.model_copy(
        update={
            "review_id": "generated-review",
            "created_at": state.review.created_at + timedelta(seconds=1),
        }
    )
    if analysis_review.criteria_source_provenance is not None:
        current = analysis_review.criteria_source_provenance
        expected_provenance = build_criteria_source_provenance(
            source_uri=current.source_uri,
            source_revision=current.source_revision,
            source_text=analysis_source_text,
            criteria=analysis_criteria,
            confirmed_by=current.confirmed_by,
            confirmed_at=current.confirmed_at,
        )
        if current != expected_provenance:
            analysis_review = analysis_review.model_copy(
                update={"criteria_source_provenance": expected_provenance}
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
        source_text=analysis_source_text,
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


def scoped_runtime_evidence(**updates) -> RuntimeEvidence:
    payload = {
        "runtime_evidence_id": "runtime-001",
        "repository": "acme/widget",
        "pr_number": 1,
        "head_sha": "head",
        "criterion_id": "AC-01",
        "artifact_reference": "https://example.test/run/1",
        "scenario": "Export CSV",
        "environment": "staging",
        "result": "passed",
        "reviewer": "QA",
        "evidence_level": EvidenceLevel.E3,
    }
    payload.update(updates)
    return RuntimeEvidence.model_validate(payload)


def linked_manual_event(**updates) -> ResolutionEvent:
    payload = {
        "event_id": "external-1",
        "criterion_id": "AC-01",
        "decision": HumanDecision.MANUALLY_VERIFIED,
        "comment": "QA observed the export in staging.",
        "reviewer": "QA",
        "claimed_evidence_level": EvidenceLevel.E3,
        "runtime_evidence_id": "runtime-001",
    }
    payload.update(updates)
    return ResolutionEvent.model_validate(payload)


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
    confirmed = confirm_pending_revision(revised)
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
    assert (
        attached.bundle.review.criteria_source_provenance
        == attached.criteria_revision.source_provenance
        == attached.review.criteria_source_provenance
    )

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
    revision_two = confirm_pending_revision(
        revise_criteria(
            revision_one,
            [Criterion(criterion_id="AC-01", text="Export CSV with headers")],
            "Export CSV with headers",
        )
    )
    revision_three = confirm_pending_revision(
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
    confirmed = confirm_pending_revision(revised)
    mismatched = [Criterion(criterion_id="AC-01", text="Export JSON")]

    with pytest.raises(
        ValueError,
        match="attached analysis criteria source provenance must match the active revision",
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
    confirmed = confirm_pending_revision(revised)

    with pytest.raises(
        ValueError,
        match="attached analysis criteria source provenance must match the active revision",
    ):
        attach_analysis(
            confirmed,
            analysis_bundle_for(confirmed, source_text="Export JSON"),
        )


def test_attach_analysis_rejects_mismatched_review_identity() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_pending_revision(revised)
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


def test_attach_analysis_rejects_mismatched_criteria_source_provenance() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_pending_revision(revised)
    mismatched_provenance = build_criteria_source_provenance(
        source_uri="https://example.test/different-requirements",
        source_text=confirmed.criteria_revision.source_text,
        criteria=confirmed.criteria_revision.criteria,
        confirmed_by="Different owner",
        confirmed_at=datetime(2026, 8, 2, 15, tzinfo=UTC),
    )
    mismatched_review = confirmed.review.model_copy(
        update={
            "review_id": "generated-review",
            "criteria_source_provenance": mismatched_provenance,
        }
    )
    incoming = analysis_bundle_for(confirmed, review=mismatched_review)

    with pytest.raises(
        ValueError,
        match="attached analysis criteria source provenance must match the active revision",
    ):
        attach_analysis(confirmed, incoming)


def test_attach_analysis_rejects_preloaded_human_resolutions() -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_pending_revision(revised)
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
    confirmed = confirm_pending_revision(revised)
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
    confirmed = confirm_pending_revision(revised)
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
    assert revised.review.criteria_source_provenance is None
    assert revised.criteria_revision.source_provenance is None
    assert revised.criteria_revision.confirmed_at is None
    assert revised.bundle is None
    assert len(revised.analysis_history) == 1
    assert revised.analysis_history[0].review.criteria_source_provenance == (
        state.review.criteria_source_provenance
    )


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

    provenance = provenance_for_revision(
        revised,
        confirmed_at=revised.criteria_revision.created_at + timedelta(seconds=1),
    )

    confirmed = confirm_criteria(revised, provenance)

    assert confirmed.criteria_revision.number == 2
    assert confirmed.review.criteria_confirmed is True
    assert confirmed.bundle is None
    assert confirmed.criteria_revision.confirmed is True
    assert confirmed.review.criteria_source_provenance == provenance
    assert confirmed.criteria_revision.source_provenance == provenance
    assert confirmed.criteria_revision.confirmed_at == provenance.confirmed_at

    reopened = type(confirmed).model_validate(confirmed.model_dump(mode="python"))

    assert reopened == confirmed


def test_confirmation_rejects_provenance_from_before_active_revision() -> None:
    state = initial_state()
    stale_provenance = state.review.criteria_source_provenance
    assert stale_provenance is not None
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        state.criteria_revision.source_text,
    )
    original = revised.model_dump(mode="python")

    with pytest.raises(
        ValueError,
        match="criteria source confirmation predates the active revision",
    ):
        confirm_criteria(revised, stale_provenance)

    assert revised.model_dump(mode="python") == original


@pytest.mark.parametrize(
    ("digest_field", "message"),
    [
        ("source_text_sha256", "criteria source provenance does not match source text"),
        (
            "normalized_criteria_sha256",
            "criteria source provenance does not match criteria",
        ),
    ],
)
def test_confirmation_rejects_tampered_snapshot_before_mutation(
    digest_field: str,
    message: str,
) -> None:
    revised = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Updated",
    )
    provenance = provenance_for_revision(revised).model_copy(
        update={digest_field: "0" * 64}
    )
    original = revised.model_dump(mode="python")

    with pytest.raises(ValueError, match=message):
        confirm_criteria(revised, provenance)

    assert revised.model_dump(mode="python") == original


def test_confirmation_rejects_an_active_analysis_bundle() -> None:
    with pytest.raises(
        ValueError,
        match="criteria confirmation requires a pending revision without an active bundle",
    ):
        state = initial_state()
        confirm_criteria(state, provenance_for_revision(state))


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
            confirm_criteria(divergent, provenance_for_revision(divergent))
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


@pytest.mark.parametrize(
    ("decision", "observed", "required", "expected"),
    [
        (HumanDecision.ACCEPTED, EvidenceLevel.E1, EvidenceLevel.E2, True),
        (HumanDecision.ACCEPTED, EvidenceLevel.E2, EvidenceLevel.E2, False),
        (HumanDecision.ACCEPTED, EvidenceLevel.E3, EvidenceLevel.E2, False),
        (HumanDecision.CHANGE_REQUIRED, EvidenceLevel.E1, EvidenceLevel.E2, False),
        (HumanDecision.ACCEPTED_EXCEPTION, EvidenceLevel.E1, EvidenceLevel.E2, False),
    ],
)
def test_acceptance_comment_policy(
    decision: HumanDecision,
    observed: EvidenceLevel,
    required: EvidenceLevel,
    expected: bool,
) -> None:
    assert acceptance_requires_comment(decision, observed, required) is expected


def test_append_resolution_requires_comment_for_low_evidence_acceptance() -> None:
    state = initial_state()
    assert state.bundle is not None
    criterion = state.bundle.criteria[0].model_copy(
        update={"required_evidence_level": EvidenceLevel.E2}
    )
    provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_text=state.bundle.source_text,
        criteria=[criterion],
        confirmed_by="Fixture owner",
        confirmed_at=state.review.created_at,
    )
    state.bundle.criteria = [criterion]
    state.bundle.review.criteria_source_provenance = provenance
    state.criteria_revision.criteria = [criterion.model_copy(deep=True)]
    state.criteria_revision.source_provenance = provenance.model_copy(deep=True)
    state.criteria_revision.confirmed_at = provenance.confirmed_at
    state.review.criteria_source_provenance = provenance.model_copy(deep=True)

    with pytest.raises(
        ValueError,
        match="reviewer comment is required when accepting below the required evidence level",
    ):
        append_resolution(
            state,
            ResolutionEvent(
                criterion_id="AC-01",
                decision=HumanDecision.ACCEPTED,
                comment="   ",
            ),
        )
    assert state.resolution_events == []
    assert state.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW


def test_resolution_event_requires_an_active_analysis_bundle() -> None:
    pending = revise_criteria(
        initial_state(),
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Updated requirements",
    )
    confirmed = confirm_pending_revision(pending)

    with pytest.raises(
        ValueError, match="Run a confirmed analysis before recording a resolution"
    ):
        append_resolution(
            confirmed,
            ResolutionEvent(final_acceptance=True, comment="Premature acceptance"),
        )


def test_resolution_event_rejects_ineligible_positive_final_acceptance() -> None:
    state = initial_state()

    assert can_record_final_acceptance(state) is False

    with pytest.raises(
        ValueError, match="final acceptance prerequisites are not satisfied"
    ):
        append_resolution(
            state,
            ResolutionEvent(final_acceptance=True, comment="Premature acceptance"),
        )


def test_resolution_event_rejects_unpaired_manual_verification() -> None:
    with pytest.raises(
        ValueError, match="append_external_verification"
    ):
        append_resolution(
            initial_state(),
            ResolutionEvent(
                criterion_id="AC-01",
                decision=HumanDecision.MANUALLY_VERIFIED,
                claimed_evidence_level=EvidenceLevel.E3,
                reviewer="QA",
                comment="Observed the scenario",
            ),
        )


def test_current_resolutions_preserves_runtime_evidence_link() -> None:
    event = ResolutionEvent(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment="Observed",
        reviewer="QA",
        claimed_evidence_level=EvidenceLevel.E3,
        runtime_evidence_id="runtime-001",
        criteria_revision_number=1,
    )

    assert current_resolutions([event], 1)[0].runtime_evidence_id == "runtime-001"


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
    state = initial_state()
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


def test_final_acceptance_must_be_revoked_before_invalidating_a_decision() -> None:
    accepted = append_resolution(
        initial_state(),
        ResolutionEvent(
            event_id="criterion-accepted",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
        ),
    )
    accepted = append_resolution(
        accepted,
        ResolutionEvent(event_id="review-accepted", final_acceptance=True),
    )

    with pytest.raises(
        ValueError, match="final acceptance requires accepted current resolutions"
    ):
        append_resolution(
            accepted,
            ResolutionEvent(
                event_id="decision-invalidated-too-early",
                criterion_id="AC-01",
                decision=HumanDecision.CHANGE_REQUIRED,
            ),
        )

    revoked = append_resolution(
        accepted,
        ResolutionEvent(event_id="review-revoked", final_acceptance=False),
    )
    changed = append_resolution(
        revoked,
        ResolutionEvent(
            event_id="decision-invalidated",
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
        ),
    )

    assert changed.review.final_acceptance is False
    assert changed.bundle is not None
    assert changed.bundle.gate.verdict is GateVerdict.BLOCKED


def test_runtime_evidence_is_append_only_and_does_not_change_gate() -> None:
    state = initial_state()
    updated = append_runtime_evidence(
        state,
        scoped_runtime_evidence(),
    )

    assert state.bundle is not None and state.bundle.runtime_evidence == []
    assert updated.bundle is not None
    assert updated.bundle.runtime_evidence[0].artifact_reference.endswith("/1")
    assert updated.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW


@pytest.mark.parametrize(
    ("evidence", "message"),
    [
        (
            scoped_runtime_evidence(repository="other/widget"),
            "runtime evidence must match the active review identity",
        ),
        (
            scoped_runtime_evidence(pr_number=2),
            "runtime evidence must match the active review identity",
        ),
        (
            scoped_runtime_evidence(head_sha="different-head"),
            "runtime evidence must match the active review identity",
        ),
        (
            RuntimeEvidence(
                criterion_id="AC-01",
                artifact_reference="https://example.test/run/1",
                scenario="Export CSV",
                environment="staging",
                result="passed",
                reviewer="QA",
                evidence_level=EvidenceLevel.E3,
            ),
            "runtime evidence must include the active review identity",
        ),
    ],
)
def test_append_runtime_evidence_rejects_invalid_identity_atomically(
    evidence: RuntimeEvidence,
    message: str,
) -> None:
    state = initial_state()
    original = state.model_dump(mode="python")

    with pytest.raises(ValueError, match=message):
        append_runtime_evidence(state, evidence)

    assert state.model_dump(mode="python") == original


def test_external_verification_atomically_appends_evidence_and_resolution() -> None:
    state = initial_state()
    evidence = scoped_runtime_evidence()
    event = linked_manual_event()

    updated = append_external_verification(state, evidence, event)

    assert state.bundle is not None and state.bundle.runtime_evidence == []
    assert state.resolution_events == []
    assert updated.bundle is not None
    assert updated.bundle.runtime_evidence == [evidence]
    assert updated.resolution_events[-1].event_id == "external-1"
    assert updated.resolution_events[-1].runtime_evidence_id == "runtime-001"
    assert updated.bundle.resolutions[0].decision is HumanDecision.MANUALLY_VERIFIED
    assert updated.bundle.resolutions[0].runtime_evidence_id == "runtime-001"


@pytest.mark.parametrize(
    ("evidence", "event", "message"),
    [
        (
            scoped_runtime_evidence(repository="other/widget"),
            linked_manual_event(),
            "runtime evidence must match the active review identity",
        ),
        (
            scoped_runtime_evidence(pr_number=2),
            linked_manual_event(),
            "runtime evidence must match the active review identity",
        ),
        (
            scoped_runtime_evidence(head_sha="different-head"),
            linked_manual_event(),
            "runtime evidence must match the active review identity",
        ),
        (
            RuntimeEvidence(
                criterion_id="AC-01",
                artifact_reference="https://example.test/run/1",
                scenario="Export CSV",
                environment="staging",
                result="passed",
                reviewer="QA",
                evidence_level=EvidenceLevel.E3,
            ),
            linked_manual_event(),
            "runtime evidence must include the active review identity",
        ),
        (
            scoped_runtime_evidence(),
            linked_manual_event(runtime_evidence_id="runtime-002"),
            "external verification inputs must use the same runtime evidence ID",
        ),
    ],
)
def test_external_verification_rejects_invalid_runtime_identity_atomically(
    evidence: RuntimeEvidence,
    event: ResolutionEvent,
    message: str,
) -> None:
    state = initial_state()
    original = state.model_dump(mode="python")

    with pytest.raises(ValueError, match=message):
        append_external_verification(state, evidence, event)

    assert state.model_dump(mode="python") == original


@pytest.mark.parametrize("operation", ["runtime", "external_verification"])
def test_runtime_operations_reject_duplicate_runtime_id_atomically(
    operation: str,
) -> None:
    state = append_runtime_evidence(initial_state(), scoped_runtime_evidence())
    original = state.model_dump(mode="python")
    duplicate = scoped_runtime_evidence(
        artifact_reference="https://example.test/run/duplicate"
    )

    with pytest.raises(ValueError, match="runtime evidence ID must be unique"):
        if operation == "runtime":
            append_runtime_evidence(state, duplicate)
        else:
            append_external_verification(state, duplicate, linked_manual_event())

    assert state.model_dump(mode="python") == original


def test_external_verification_requires_final_acceptance_revocation_before_replacement() -> (
    None
):
    verified = append_external_verification(
        initial_state(), scoped_runtime_evidence(), linked_manual_event()
    )
    accepted = append_resolution(
        verified,
        ResolutionEvent(event_id="final-accepted", final_acceptance=True),
    )
    original = accepted.model_dump(mode="python")

    with pytest.raises(
        ValueError,
        match="final acceptance must be revoked before replacing manual verification",
    ):
        append_external_verification(
            accepted,
            scoped_runtime_evidence(
                runtime_evidence_id="runtime-002",
                artifact_reference="https://example.test/run/2",
            ),
            linked_manual_event(
                event_id="external-2", runtime_evidence_id="runtime-002"
            ),
        )

    assert accepted.model_dump(mode="python") == original


def test_runtime_manual_verification_requires_revocation_before_decision_replacement() -> (
    None
):
    verified = append_external_verification(
        initial_state(), scoped_runtime_evidence(), linked_manual_event()
    )
    accepted = append_resolution(
        verified,
        ResolutionEvent(event_id="final-accepted", final_acceptance=True),
    )
    original = accepted.model_dump(mode="python")

    with pytest.raises(
        ValueError,
        match="final acceptance must be revoked before replacing manual verification",
    ):
        append_resolution(
            accepted,
            ResolutionEvent(
                event_id="replace-manual",
                criterion_id="AC-01",
                decision=HumanDecision.ACCEPTED,
            ),
        )

    assert accepted.model_dump(mode="python") == original


@pytest.mark.parametrize(
    ("evidence_update", "event_update", "message"),
    [
        ({"criterion_id": "AC-99"}, {}, "same active criterion"),
        ({}, {"criterion_id": "AC-99"}, "same active criterion"),
        ({"reviewer": "QA one"}, {"reviewer": "QA two"}, "same reviewer"),
        (
            {"evidence_level": EvidenceLevel.E3},
            {"claimed_evidence_level": EvidenceLevel.E4},
            "same evidence level",
        ),
    ],
)
def test_external_verification_rejects_mismatched_atomic_inputs(
    evidence_update, event_update, message
) -> None:
    evidence = scoped_runtime_evidence().model_copy(update=evidence_update)
    event = linked_manual_event().model_copy(update=event_update)

    with pytest.raises(ValueError, match=message):
        append_external_verification(initial_state(), evidence, event)


def test_final_acceptance_requires_complete_passing_resolved_review() -> None:
    state = initial_state()
    assert can_record_final_acceptance(state) is False

    resolved = append_resolution(
        state,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Reviewed candidate evidence",
        ),
    )

    assert can_record_final_acceptance(resolved) is True


def test_final_acceptance_is_unavailable_for_an_unvalidated_empty_criterion_state() -> None:
    state = initial_state()
    source_text = state.criteria_revision.source_text
    empty_provenance = CriteriaSourceProvenance(
        source_uri="https://example.test/requirements",
        source_text_sha256=source_text_sha256(source_text),
        normalized_criteria_sha256=normalized_criteria_sha256([]),
        confirmed_by="Fixture owner",
        confirmed_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    empty_review = state.review.model_copy(
        update={"criteria_source_provenance": empty_provenance}
    )
    assert state.bundle is not None
    empty_bundle = state.bundle.model_copy(
        update={
            "review": empty_review,
            "criteria": [],
            "evidence": [],
            "retrieval_diagnostics": [],
            "findings": [],
            "resolutions": [],
            "gate": evaluate_gate(empty_review, [], [], []),
        }
    )
    empty_revision = state.criteria_revision.model_copy(
        update={"criteria": [], "source_provenance": empty_provenance}
    )
    empty_state = state.model_copy(
        update={
            "review": empty_review,
            "criteria_revision": empty_revision,
            "bundle": empty_bundle,
        }
    )

    assert can_record_final_acceptance(empty_state) is False


def test_final_acceptance_is_unavailable_without_criteria_source_provenance() -> None:
    resolved = append_resolution(
        initial_state(),
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Reviewed candidate evidence",
        ),
    )
    payload = resolved.model_dump(mode="python")
    payload["review"]["criteria_source_provenance"] = None
    payload["criteria_revision"]["source_provenance"] = None
    payload["bundle"]["review"]["criteria_source_provenance"] = None
    bundle = ReviewBundle.model_validate(payload["bundle"])
    payload["bundle"]["gate"] = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    ).model_dump(mode="python")
    legacy_state = type(resolved).model_validate(payload)

    assert can_record_final_acceptance(legacy_state) is False


def test_final_acceptance_ignores_superseded_and_prior_revision_decisions() -> None:
    state = append_resolution(
        initial_state(),
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Original revision accepted",
        ),
    )
    pending = revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    confirmed = confirm_pending_revision(pending)
    reanalyzed = attach_analysis(confirmed, analysis_bundle_for(confirmed))

    assert can_record_final_acceptance(reanalyzed) is False


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
    confirmed = confirm_pending_revision(pending)

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
    evidence = scoped_runtime_evidence(limitations=["Browser only"])

    updated = append_runtime_evidence(initial_state(), evidence)
    evidence.result = ""
    evidence.limitations.append("Caller mutation")

    assert updated.bundle is not None
    assert updated.bundle.runtime_evidence[0].result == "passed"
    assert updated.bundle.runtime_evidence[0].limitations == ["Browser only"]


def exact_head_state() -> ReviewState:
    state = initial_state().model_copy(deep=True)
    state.review.head_sha = "a" * 40
    assert state.bundle is not None
    state.bundle.review.head_sha = "a" * 40
    return ReviewState.model_validate(state.model_dump(mode="python"))


def junit_import_for(state: ReviewState, *, import_id: str = "import-001"):
    return build_junit_evidence_import(
        state,
        b'<testsuite name="unit"><testcase name="test_export"/></testsuite>',
        [
            JUnitMappingSelection(
                scope_id="suite-0001",
                criterion_id="AC-01",
            )
        ],
        importer="QA owner",
        imported_at=datetime(2026, 8, 20, tzinfo=UTC),
        import_id=import_id,
    )


def test_junit_import_append_is_non_gating_and_does_not_alias_input() -> None:
    state = exact_head_state()
    record = junit_import_for(state)
    assert state.bundle is not None
    original_gate = state.bundle.gate.model_copy(deep=True)
    original_findings = [item.model_copy(deep=True) for item in state.bundle.findings]
    original_resolutions = list(state.bundle.resolutions)
    original_runtime = list(state.bundle.runtime_evidence)
    original_events = list(state.resolution_events)
    original_final_acceptance = state.review.final_acceptance

    updated = append_junit_evidence_import(state, record)
    record.limitations.append("Caller mutation")

    assert updated.bundle is not None
    assert len(updated.bundle.junit_evidence_imports) == 1
    assert "Caller mutation" not in updated.bundle.junit_evidence_imports[0].limitations
    assert state.bundle.junit_evidence_imports == []
    assert updated.bundle.gate == original_gate
    assert updated.bundle.findings == original_findings
    assert updated.bundle.resolutions == original_resolutions
    assert updated.bundle.runtime_evidence == original_runtime
    assert updated.resolution_events == original_events
    assert updated.review.final_acceptance is original_final_acceptance


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("repository", "other/repository", "active review identity"),
        ("pr_number", 2, "active review identity"),
        ("head_sha", "b" * 40, "active review identity"),
        ("criteria_revision_number", 2, "criteria revision"),
        ("confirmed_criteria_sha256", "f" * 64, "criteria digest"),
    ],
)
def test_junit_import_append_rejects_stale_or_foreign_relationship_atomically(
    field: str, value: object, message: str
) -> None:
    state = exact_head_state()
    record = junit_import_for(state).model_copy(update={field: value})

    with pytest.raises(ValueError, match=message):
        append_junit_evidence_import(state, record)

    assert state.bundle is not None
    assert state.bundle.junit_evidence_imports == []


def test_junit_import_append_rejects_duplicate_id_or_artifact_atomically() -> None:
    state = exact_head_state()
    record = junit_import_for(state)
    imported = append_junit_evidence_import(state, record)
    assert imported.bundle is not None

    with pytest.raises(ValueError, match="already imported"):
        append_junit_evidence_import(imported, record)

    conflicting_id = record.model_copy(
        update={"artifact_sha256": "e" * 64}
    )
    with pytest.raises(ValueError, match="import ID"):
        append_junit_evidence_import(imported, conflicting_id)

    assert len(imported.bundle.junit_evidence_imports) == 1


def test_junit_import_append_requires_active_analysis() -> None:
    state = exact_head_state()
    record = junit_import_for(state)
    pending = revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )

    with pytest.raises(ValueError, match="active analysis"):
        append_junit_evidence_import(pending, record)

    assert pending.bundle is None
