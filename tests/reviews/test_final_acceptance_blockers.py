import pytest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.resolution_events import current_resolutions
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    can_record_final_acceptance,
    final_acceptance_blockers,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    Criterion,
    HumanDecision,
    IngestionState,
    ResolutionEvent,
    ReviewState,
)
from tests.reviews.test_file_scope_lifecycle import scope_state
from tests.reviews.test_lifecycle import exact_head_state
from tests.reviews.test_runtime_evidence_level import _previous_policy_record


def _set_review_facts(state: ReviewState, **updates: object) -> None:
    assert state.bundle is not None
    state.review = state.review.model_copy(update=updates)
    state.bundle.review = state.review.model_copy(deep=True)
    _recompute_gate(state)


def _recompute_gate(state: ReviewState) -> None:
    bundle = state.bundle
    assert bundle is not None
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, bundle.file_scope_decisions,
    )


def _resolve_criterion(decision: HumanDecision = HumanDecision.ACCEPTED) -> ReviewState:
    return append_resolution(
        exact_head_state(),
        ResolutionEvent(criterion_id="AC-01", decision=decision, comment="Constructed decision."),
    )


def test_failing_checks_do_not_hide_pending_file_scope_or_criterion_decisions() -> None:
    state = scope_state()
    _set_review_facts(
        state, check_state=CheckState.FAILING,
        ci_observation=CIObservation(
            state=CheckState.FAILING, reason="Constructed check failure.",
            total_check_runs=1, failing_check_runs=1,
        ),
    )
    assert state.bundle is not None
    assert "uncited_changed_files" not in state.bundle.gate.reason_codes
    before = state.model_dump_json()

    assert final_acceptance_blockers(state) == (
        "checks_failing", "unresolved_file_scope", "criterion_decisions_required",
    )
    assert not can_record_final_acceptance(state)
    assert state.model_dump_json() == before


def test_unknown_changed_file_inventory_is_distinct_from_pending_scope_decisions() -> None:
    state = _resolve_criterion()
    _set_review_facts(state, changed_file_inventory=None)

    assert final_acceptance_blockers(state) == ("changed_file_inventory_unavailable",)
    assert not can_record_final_acceptance(state)


@pytest.mark.parametrize("ingestion", [IngestionState.PARTIAL, IngestionState.FAILED])
def test_incomplete_ingestion_remains_a_blocker_after_resolving_criteria(
    ingestion: IngestionState,
) -> None:
    state = _resolve_criterion()
    _set_review_facts(state, ingestion_state=ingestion)

    assert final_acceptance_blockers(state) == ("incomplete_ingestion",)
    assert not can_record_final_acceptance(state)


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        (CIObservation(
            state=CheckState.PENDING, reason="Constructed pending checks.",
            total_check_runs=1, pending_check_runs=1,
        ), "checks_pending"),
        (CIObservation(reason="Constructed absence of checks."), "checks_unavailable"),
    ],
)
def test_incomplete_check_states_have_distinct_blockers(
    observation: CIObservation, expected: str,
) -> None:
    state = _resolve_criterion()
    _set_review_facts(state, check_state=observation.state, ci_observation=observation)

    assert final_acceptance_blockers(state) == (expected,)
    assert not can_record_final_acceptance(state)


def test_new_criteria_revision_requires_active_analysis() -> None:
    state = revise_criteria(
        _resolve_criterion(), [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )

    assert final_acceptance_blockers(state) == ("analysis_required",)
    assert not can_record_final_acceptance(state)


def test_legacy_confirmed_flag_without_source_provenance_requires_confirmation() -> None:
    state = _resolve_criterion()
    state.criteria_revision.source_provenance = None
    _set_review_facts(state, criteria_source_provenance=None)

    assert final_acceptance_blockers(state) == ("criteria_confirmation_required",)
    assert not can_record_final_acceptance(state)


@pytest.mark.parametrize("decision", [HumanDecision.ACCEPTED_EXCEPTION, HumanDecision.NOT_IN_SCOPE])
def test_explicit_exception_or_out_of_scope_decision_remains_eligible(
    decision: HumanDecision,
) -> None:
    state = _resolve_criterion(decision)

    assert final_acceptance_blockers(state) == ()
    assert can_record_final_acceptance(state)
    assert append_resolution(state, ResolutionEvent(final_acceptance=True)).review.final_acceptance


@pytest.mark.parametrize(
    "decision", [HumanDecision.REJECTED_FINDING, HumanDecision.CHANGE_REQUIRED],
)
def test_non_accepting_decisions_still_require_criterion_decisions(decision: HumanDecision) -> None:
    state = _resolve_criterion(decision)

    assert final_acceptance_blockers(state) == ("criterion_decisions_required",)
    assert not can_record_final_acceptance(state)


@pytest.mark.parametrize("linked", [True, False], ids=["below-level", "unlinked"])
def test_legacy_manual_verification_distinguishes_level_from_missing_link(linked: bool) -> None:
    state = _previous_policy_record(accepted=False)
    assert state.bundle is not None
    if not linked:
        state.resolution_events[0].runtime_evidence_id = None
        state.bundle.resolutions = current_resolutions(
            state.resolution_events, state.criteria_revision.number,
        )
        _recompute_gate(state)
    expected = "below_required_manual_verification" if linked else "unlinked_manual_verification"
    before = state.model_dump_json()

    assert final_acceptance_blockers(state) == (expected,)
    assert not can_record_final_acceptance(state)
    assert state.model_dump_json() == before


def test_recorded_acceptance_can_still_be_revoked() -> None:
    state = append_resolution(_resolve_criterion(), ResolutionEvent(final_acceptance=True))

    assert final_acceptance_blockers(state) == ("already_recorded",)
    assert not can_record_final_acceptance(state)

    revoked = append_resolution(state, ResolutionEvent(final_acceptance=False))
    assert revoked.resolution_events[:-1] == state.resolution_events
    assert not revoked.review.final_acceptance
    assert final_acceptance_blockers(revoked) == ()
    assert can_record_final_acceptance(revoked)
