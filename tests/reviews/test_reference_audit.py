"""Constructed audit histories preserve original references and deterministic truth."""

from importlib import import_module

import pytest

from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_selected_references import append, source_state


def api():
    return import_module("scopeproof_core.reviews.reference_audit")


def withdraw(state, reference_id=None, **kwargs):
    return api().withdraw_reviewer_selected_reference(
        state,
        reference_id=reference_id or state.bundle.reviewer_selected_references[-1].reference_id,
        reviewer=kwargs.pop("reviewer", "Constructed audit actor"),
        reason=kwargs.pop("reason", "Constructed wrong context withdrawn."),
        expected_state_fingerprint=kwargs.pop(
            "expected_state_fingerprint", JsonReviewStore.state_fingerprint(state)
        ),
        **kwargs,
    )


def correct(state, snapshot, reference_id=None, **kwargs):
    from scopeproof_core.reviews.selected_references import selectable_reference_lines

    return api().correct_reviewer_selected_reference(
        state,
        reference_id=reference_id or state.bundle.reviewer_selected_references[-1].reference_id,
        snapshot=snapshot,
        selected=kwargs.pop("selected", selectable_reference_lines(state, snapshot)[0]),
        reviewer=kwargs.pop("reviewer", "Constructed correction actor"),
        rationale=kwargs.pop("rationale", "Corrected constructed rationale."),
        reason=kwargs.pop("reason", "Original rationale described the wrong purpose."),
        expected_state_fingerprint=kwargs.pop(
            "expected_state_fingerprint", JsonReviewStore.state_fingerprint(state)
        ),
        **kwargs,
    )


def test_correction_then_withdrawal_retains_original_and_nongating_truth():
    state, snapshot = source_state()
    state = append(state, snapshot)
    before = state.model_dump(mode="json")
    corrected = correct(state, snapshot)
    original, replacement = corrected.bundle.reviewer_selected_references
    assert original == state.bundle.reviewer_selected_references[0]
    assert replacement.reference_id != original.reference_id
    assert replacement.rationale == "Corrected constructed rationale."
    assert corrected.bundle.active_reviewer_selected_reference_ids == [replacement.reference_id]
    event = corrected.bundle.selected_reference_events[0]
    assert event.action == "corrected" and event.reference_id == original.reference_id
    assert event.replacement_reference_id == replacement.reference_id
    withdrawn = withdraw(corrected)
    assert withdrawn.bundle.active_reviewer_selected_reference_ids == []
    assert len(withdrawn.bundle.selected_reference_events) == 2
    assert len(withdrawn.bundle.reviewer_selected_references) == 2
    after = withdrawn.model_dump(mode="json")
    for payload in (before, after):
        for key in (
            "reviewer_selected_references",
            "selected_reference_events",
            "active_reviewer_selected_reference_ids",
        ):
            payload["bundle"].pop(key, None)
    assert after == before


def test_withdrawal_needs_no_snapshot_and_cannot_be_repeated():
    state, snapshot = source_state()
    state = append(state, snapshot)
    updated = withdraw(state)
    with pytest.raises(ValueError, match="active"):
        withdraw(updated)
    with pytest.raises(ValueError, match="active"):
        correct(updated, snapshot)


def test_correction_can_chain_without_changing_original_source_records():
    state, snapshot = source_state()
    state = append(state, snapshot)
    first = correct(state, snapshot)
    second = correct(first, snapshot, rationale="Second constructed rationale")
    assert (
        second.bundle.reviewer_selected_references[:2] == first.bundle.reviewer_selected_references
    )
    assert len(second.bundle.active_reviewer_selected_reference_ids) == 1
    assert len(second.bundle.selected_reference_events) == 2


@pytest.mark.parametrize("transition", [withdraw, correct])
def test_stale_audit_does_not_mutate_state(transition):
    state, snapshot = source_state()
    state = append(state, snapshot)
    before = state.model_dump_json()
    args = (state, snapshot) if transition is correct else (state,)
    with pytest.raises(ValueError, match="stale"):
        transition(*args, expected_state_fingerprint="0" * 64)
    assert state.model_dump_json() == before
