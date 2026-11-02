"""Saved corrections change explicit organizational mappings, never review truth."""

from importlib import import_module

import pytest

from scopeproof_core.schemas.models import JUnitCriterionMapping
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import junit_audit_state


def api():
    return import_module("scopeproof_core.reviews.junit_correction")


def swapped():
    return [
        JUnitCriterionMapping(criterion_id="AC-01", test_case_ids=["suite-0001-case-0002"]),
        JUnitCriterionMapping(criterion_id="AC-02", test_case_ids=["suite-0001-case-0001"]),
    ]


def correction(state, mappings=None, **kwargs):
    return api().correct_junit_mappings(
        state, import_id="constructed-junit-import", criterion_mappings=mappings or swapped(),
        reviewer="  CONSTRUCTED correction actor  ", reason="  Misassigned cases  ",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        confirm_whole_import=True, **kwargs,
    )


def without_audit(state):
    data = state.model_dump(mode="json")
    for field in ("junit_import_events", "active_junit_import_ids", "effective_junit_mappings"):
        data["bundle"].pop(field, None)
    return data


def test_saved_correction_preserves_originals_and_every_nonaudit_fact():
    state = junit_audit_state()
    before = state.model_dump_json()
    updated = correction(state)
    assert state.model_dump_json() == before
    assert without_audit(updated) == without_audit(state)
    assert updated.bundle.effective_junit_mappings["constructed-junit-import"] == swapped()
    event = updated.bundle.junit_import_events[-1]
    assert event.action == "mapping_corrected"
    assert event.previous_correction_event_id is None
    assert event.reviewer == "CONSTRUCTED correction actor"
    assert event.reason == "Misassigned cases"
    assert updated.bundle.active_junit_import_ids == ["constructed-junit-import"]


def test_effective_mapping_projection_is_detached_from_history():
    state = correction(junit_audit_state())
    before = state.model_dump_json()
    projected = state.bundle.effective_junit_mappings
    projected["constructed-junit-import"][0].test_case_ids.clear()
    assert state.model_dump_json() == before


def test_full_state_fingerprint_rejects_other_saved_action():
    state = junit_audit_state()
    stale = JsonReviewStore.state_fingerprint(state)
    state = correction(state)
    with pytest.raises(ValueError, match="stale"):
        api().correct_junit_mappings(
            state, import_id="constructed-junit-import",
            criterion_mappings=state.bundle.junit_evidence_imports[0].criterion_mappings,
            reviewer="CONSTRUCTED actor", reason="Old request",
            expected_state_fingerprint=stale, confirm_whole_import=True,
        )


def test_noop_cannot_consume_correction_history():
    state = junit_audit_state()
    with pytest.raises(ValueError, match=r"change|identical|unchanged"):
        correction(state, state.bundle.junit_evidence_imports[0].criterion_mappings)
    assert state.bundle.junit_import_events == []


def test_draft_requires_explicit_group_removal_before_case_reassignment():
    state = junit_audit_state()
    draft = api().new_junit_correction_draft(state, "constructed-junit-import")
    original = state.bundle.junit_evidence_imports[0].criterion_mappings
    assert list(draft.criterion_mappings) == original
    with pytest.raises(ValueError, match=r"multiple|overlap|one JUnit"):
        api().replace_junit_correction_group(state, draft, "AC-01", ["suite-0001-case-0002"])
    removed = api().remove_junit_correction_group(state, draft, "AC-02")
    moved = api().replace_junit_correction_group(
        state, removed, "AC-01", ["suite-0001-case-0002"],
    )
    assert [(x.criterion_id, x.test_case_ids) for x in moved.criterion_mappings] == [
        ("AC-01", ["suite-0001-case-0002"]),
    ]
    assert state.bundle.junit_import_events == []


def test_draft_can_be_empty_temporarily_but_cannot_save_empty_final_mapping():
    state = junit_audit_state()
    draft = api().new_junit_correction_draft(state, "constructed-junit-import")
    for criterion in ("AC-01", "AC-02"):
        draft = api().remove_junit_correction_group(state, draft, criterion)
    assert draft.criterion_mappings == ()
    with pytest.raises(ValueError):
        api().correct_junit_mappings(
            state, import_id=draft.import_id, criterion_mappings=[], reviewer="CONSTRUCTED actor",
            reason="Empty final is withdrawal", expected_state_fingerprint=draft.state_fingerprint,
            confirm_whole_import=True,
        )


def test_draft_does_not_survive_unrelated_current_state_change():
    state = junit_audit_state()
    draft = api().new_junit_correction_draft(state, "constructed-junit-import")
    state = correction(state)
    with pytest.raises(ValueError, match=r"stale|changed"):
        api().remove_junit_correction_group(state, draft, "AC-01")
