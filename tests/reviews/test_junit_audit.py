"""A withdrawal retires whole imported context without rewriting review truth."""

from datetime import UTC, datetime
from importlib import import_module

import pytest

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state, revise_criteria
from scopeproof_core.schemas.models import Criterion, HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_lifecycle import exact_head_state, junit_import_for


def imported_state():
    from scopeproof_core.reviews.lifecycle import append_junit_evidence_import

    state = exact_head_state()
    return append_junit_evidence_import(state, junit_import_for(state))


def withdraw(state, **kwargs):
    return import_module("scopeproof_core.reviews.junit_audit").withdraw_junit_evidence_import(
        state,
        import_id=state.bundle.junit_evidence_imports[0].import_id,
        reviewer="  Constructed audit reviewer  ",
        reason="  Wrong context retired.  ",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        **kwargs,
    )


def without_audit(state):
    data = state.model_dump(mode="json")
    data["bundle"].pop("junit_import_events", None)
    data["bundle"].pop("active_junit_import_ids", None)
    return data


def test_withdrawal_retains_every_original_fact_and_normalizes_asserted_attribution():
    state = imported_state()
    before = state.model_dump_json()
    when = datetime(2026, 11, 1, 15, tzinfo=UTC)
    updated = withdraw(state, occurred_at=when)
    assert state.model_dump_json() == before
    assert without_audit(updated) == without_audit(state)
    assert updated.bundle.active_junit_import_ids == []
    event = updated.bundle.junit_import_events[0]
    target = state.bundle.junit_evidence_imports[0]
    assert event.action == "withdrawn" and event.import_id == target.import_id
    assert event.reviewer == "Constructed audit reviewer"
    assert event.reason == "Wrong context retired."
    assert event.occurred_at == when
    assert event.review_id == state.review.review_id
    assert event.artifact_sha256 == target.artifact_sha256
    assert event.criteria_source_provenance == target.criteria_source_provenance
    api = import_module("scopeproof_core.reviews.junit_audit")
    assert api.junit_import_status(updated.bundle, target.import_id) == "withdrawn"
    assert api.junit_import_status(state.bundle, target.import_id) == "active"
    assert validated_review_state(updated) == updated


def test_withdrawal_is_terminal_and_does_not_permit_same_artifact_reimport():
    from scopeproof_core.reviews.lifecycle import append_junit_evidence_import

    original = imported_state()
    updated = withdraw(original)
    before = updated.model_dump_json()
    with pytest.raises(ValueError, match=r"active|withdrawn"):
        withdraw(updated)
    duplicate = original.bundle.junit_evidence_imports[0].model_copy(update={"import_id": "new-id"})
    with pytest.raises(ValueError, match="already imported"):
        append_junit_evidence_import(updated, duplicate)
    assert updated.model_dump_json() == before


def test_accepted_review_keeps_its_explicit_acceptance_after_nongating_withdrawal():
    state = imported_state()
    for criterion in state.criteria_revision.criteria:
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment="Constructed acceptance remains separate from imported context",
            ),
        )
    state = append_resolution(state, ResolutionEvent(final_acceptance=True))
    assert state.review.final_acceptance
    updated = withdraw(state)
    assert updated.review.final_acceptance
    assert without_audit(updated) == without_audit(state)


def test_withdrawal_stays_in_archived_owner_and_requires_a_confirmed_active_analysis():
    from scopeproof_core.demo import build_demo_review

    state = withdraw(imported_state())
    archived = revise_criteria(
        state, [Criterion(criterion_id="AC-01", text="New requirement")], "New requirement"
    )
    assert archived.bundle is None
    assert archived.analysis_history[-1].junit_import_events == state.bundle.junit_import_events
    api = import_module("scopeproof_core.reviews.junit_audit")
    with pytest.raises(ValueError, match=r"active|analysis|confirmed"):
        api.withdraw_junit_evidence_import(
            archived,
            import_id=state.bundle.junit_evidence_imports[0].import_id,
            reviewer="Constructed actor",
            reason="No active analysis",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(archived),
        )
    fresh = build_demo_review()
    fresh.junit_import_events = state.bundle.junit_import_events
    with pytest.raises(ValueError):
        new_review_state(fresh)


def test_withdrawal_survives_save_load_without_load_time_record_writes(tmp_path):
    state = withdraw(imported_state())
    store = JsonReviewStore(tmp_path / "reviews")
    path = store.save(state)
    before = path.read_bytes()
    assert store.load(state.review.review_id) == state
    assert path.read_bytes() == before
