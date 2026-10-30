"""Adversarial lifecycle records must not alter source or automatic review truth."""

from __future__ import annotations

from datetime import timedelta
from importlib import import_module

import pytest

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    Criterion,
    LineChangeType,
    ReviewBundle,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_selected_references import append, source_state


def audit():
    return import_module("scopeproof_core.reviews.reference_audit")


def prepared():
    state, snapshot = source_state()
    return append(state, snapshot), snapshot


def withdraw(state, reference_id=None, **updates):
    return audit().withdraw_reviewer_selected_reference(
        state,
        **{
            "reference_id": (
                reference_id or state.bundle.reviewer_selected_references[-1].reference_id
            ),
            "reviewer": "Amending reviewer",
            "reason": "This static reference was selected in error.",
            "expected_state_fingerprint": JsonReviewStore.state_fingerprint(state),
            **updates,
        },
    )


def correct(state, snapshot, reference_id=None, **updates):
    selected = import_module(
        "scopeproof_core.reviews.selected_references"
    ).selectable_reference_lines(state, snapshot)[-1]
    return audit().correct_reviewer_selected_reference(
        state,
        **{
            "snapshot": snapshot,
            "selected": selected,
            "reference_id": (
                reference_id or state.bundle.reviewer_selected_references[-1].reference_id
            ),
            "reviewer": "Amending reviewer",
            "reason": "The later line is the intended static context.",
            "rationale": "This replacement supplies more precise static context.",
            "expected_state_fingerprint": JsonReviewStore.state_fingerprint(state),
            **updates,
        },
    )


def non_audit_payload(state):
    payload = state.model_dump(mode="python")
    for bundle in [payload["bundle"], *payload["analysis_history"]]:
        if bundle is not None:
            for key in (
                "reviewer_selected_references", "selected_reference_events",
                "active_reviewer_selected_reference_ids",
            ):
                bundle.pop(key, None)
    return payload


def test_withdrawal_preserves_original_and_every_automatic_field_without_source():
    state, _ = prepared()
    before = state.model_dump_json()
    original = state.bundle.reviewer_selected_references[0].model_dump()
    updated = withdraw(state)
    assert state.model_dump_json() == before
    assert non_audit_payload(updated) == non_audit_payload(state)
    assert updated.bundle.reviewer_selected_references[0].model_dump() == original
    assert updated.bundle.active_reviewer_selected_reference_ids == []
    event = updated.bundle.selected_reference_events[0]
    assert event.action == "withdrawn"
    assert event.replacement_reference_id is None
    assert event.reviewer == "Amending reviewer"
    assert validated_review_state(updated) == updated


def test_correction_chain_preserves_history_and_only_latest_is_active():
    state, snapshot = prepared()
    original = state.bundle.reviewer_selected_references[0]
    first = correct(state, snapshot)
    second = correct(first, snapshot, rationale="A corrected rationale for the same source line.")
    refs = second.bundle.reviewer_selected_references
    assert refs[0] == original
    assert len(refs) == 3
    assert len({ref.reference_id for ref in refs}) == 3
    assert second.bundle.active_reviewer_selected_reference_ids == [refs[-1].reference_id]
    assert [(event.reference_id, event.replacement_reference_id) for event in
            second.bundle.selected_reference_events] == [
        (refs[0].reference_id, refs[1].reference_id),
        (refs[1].reference_id, refs[2].reference_id),
    ]
    assert non_audit_payload(second) == non_audit_payload(state)
    terminal = withdraw(second)
    assert terminal.bundle.active_reviewer_selected_reference_ids == []
    assert terminal.bundle.reviewer_selected_references == refs


@pytest.mark.parametrize("operation", ["correct", "withdraw"])
def test_missing_inactive_and_stale_targets_fail_without_mutating_state(operation):
    state, snapshot = prepared()
    inactive = withdraw(state)
    fingerprint = JsonReviewStore.state_fingerprint(state)
    before = inactive.model_dump_json()
    run = (lambda target, **kwargs: correct(inactive, snapshot, target, **kwargs)) if (
        operation == "correct"
    ) else (lambda target, **kwargs: withdraw(inactive, target, **kwargs))
    for target, overrides in [
        ("missing-reference", {}),
        (state.bundle.reviewer_selected_references[0].reference_id, {}),
        (state.bundle.reviewer_selected_references[0].reference_id,
         {"expected_state_fingerprint": fingerprint}),
    ]:
        with pytest.raises(ValueError):
            run(target, **overrides)
    assert inactive.model_dump_json() == before


@pytest.mark.parametrize("field,value", [
    ("reviewer", " \t"), ("reviewer", "x" * 201),
    ("reason", " \t"), ("reason", "x" * 2001),
])
@pytest.mark.parametrize("operation", ["correct", "withdraw"])
def test_required_audit_attribution_is_bounded(operation, field, value):
    state, snapshot = prepared()
    with pytest.raises(ValueError):
        if operation == "correct":
            correct(state, snapshot, **{field: value})
        else:
            withdraw(state, **{field: value})


@pytest.mark.parametrize("field,value", [
    ("action", "restore"), ("event_id", " "), ("reference_id", " "),
    ("reviewer", " "), ("reason", " "), ("pr_number", True),
    ("criteria_revision_number", True), ("occurred_at", "2026-10-30T00:00:00"),
    ("replacement_reference_id", "nonexistent"), ("unexpected", True),
])
def test_event_schema_rejects_malformed_and_withdrawal_replacement(field, value):
    state, _ = prepared()
    event = withdraw(state).bundle.selected_reference_events[0]
    payload = {**event.model_dump(mode="python"), field: value}
    with pytest.raises(ValueError):
        type(event).model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("review_id", "foreign-review"), ("repository", "foreign/repo"),
    ("pr_number", 987), ("head_sha", "foreign-head"),
    ("criteria_revision_number", 2), ("confirmed_criteria_sha256", "0" * 64),
    ("reference_id", "unknown-reference"),
])
def test_bundle_rejects_foreign_or_missing_event_bindings(field, value):
    state, _ = prepared()
    payload = withdraw(state).bundle.model_dump(mode="python")
    payload["selected_reference_events"][0][field] = value
    with pytest.raises(ValueError):
        ReviewBundle.model_validate(payload)


def test_bundle_rejects_duplicate_terminal_event_even_with_fresh_event_id():
    state, _ = prepared()
    payload = withdraw(state).bundle.model_dump(mode="python")
    event = payload["selected_reference_events"][0]
    for duplicate in [event, {**event, "event_id": "another-event"}]:
        forged = {**payload, "selected_reference_events": [event, duplicate]}
        with pytest.raises(ValueError):
            ReviewBundle.model_validate(forged)


@pytest.mark.parametrize("mutation", [
    "cycle", "same_target", "missing_replacement", "earlier_replacement",
    "wrong_criterion", "wrong_reviewer", "wrong_time",
])
def test_correction_graph_and_replacement_attribution_cannot_be_tampered(mutation):
    state, snapshot = prepared()
    corrected = correct(state, snapshot)
    payload = correct(
        corrected, snapshot, rationale="Another explicitly corrected source rationale."
    ).bundle.model_dump(mode="python")
    refs = payload["reviewer_selected_references"]
    events = payload["selected_reference_events"]
    if mutation == "cycle":
        events[1]["replacement_reference_id"] = refs[0]["reference_id"]
    elif mutation == "same_target":
        events[1]["reference_id"] = refs[0]["reference_id"]
    elif mutation == "missing_replacement":
        events[0]["replacement_reference_id"] = "missing"
    elif mutation == "earlier_replacement":
        refs[0], refs[1] = refs[1], refs[0]
    elif mutation == "wrong_criterion":
        refs[1]["criterion_id"] = state.bundle.criteria[1].criterion_id
    elif mutation == "wrong_reviewer":
        refs[1]["reviewer"] = "Different replacement author"
    else:
        refs[1]["selected_at"] += timedelta(seconds=1)
    with pytest.raises(ValueError):
        ReviewBundle.model_validate(payload)


def test_derived_active_ids_cannot_resurrect_a_withdrawn_reference():
    state, _ = prepared()
    payload = withdraw(state).bundle.model_dump(mode="python")
    payload["active_reviewer_selected_reference_ids"] = [
        state.bundle.reviewer_selected_references[0].reference_id
    ]
    assert ReviewBundle.model_validate(payload).active_reviewer_selected_reference_ids == []


def test_clock_rollback_cannot_prevent_withdrawal_of_a_valid_saved_reference():
    state, _ = prepared()
    payload = state.model_dump(mode="python")
    reference = payload["bundle"]["reviewer_selected_references"][0]
    reference["selected_at"] += timedelta(days=365)
    future_selected = type(state).model_validate(payload)
    updated = withdraw(future_selected)
    assert updated.bundle.active_reviewer_selected_reference_ids == []
    assert updated.bundle.reviewer_selected_references == (
        future_selected.bundle.reviewer_selected_references
    )
    assert updated.bundle.selected_reference_events[0].occurred_at < reference["selected_at"]
    assert validated_review_state(updated) == updated


@pytest.mark.parametrize("mutation", ["excerpt", "head", "criteria_provenance"])
def test_correction_cannot_establish_new_source_or_criteria_truth(mutation):
    state, snapshot = prepared()
    selected = import_module(
        "scopeproof_core.reviews.selected_references"
    ).selectable_reference_lines(state, snapshot)[-1]
    before = state.model_dump_json()
    if mutation == "excerpt":
        selected = selected.model_copy(update={"excerpt": "invented_source()"})
    elif mutation == "head":
        snapshot = snapshot.model_copy(update={"head_sha": "foreign-head"})
    else:
        state = state.model_copy(deep=True)
        provenance = state.review.criteria_source_provenance
        state.review.criteria_source_provenance = provenance.model_copy(
            update={"normalized_criteria_sha256": "0" * 64}
        )
    with pytest.raises(ValueError):
        correct(state, snapshot, selected=selected)
    if mutation != "criteria_provenance":
        assert state.model_dump_json() == before


def test_revision_archives_exact_original_records_and_terminal_audit_events():
    state, snapshot = prepared()
    corrected = correct(state, snapshot)
    updated = withdraw(corrected)
    before = updated.bundle.model_dump_json()
    revised = revise_criteria(
        updated, [Criterion(criterion_id="AC-01", text="New criterion")], "New criterion"
    )
    assert revised.bundle is None
    assert revised.analysis_history[-1].model_dump_json() == before
    assert revised.analysis_history[-1].active_reviewer_selected_reference_ids == []
    assert validated_review_state(revised) == revised


def test_correction_cannot_duplicate_another_active_criterion_location():
    state, snapshot = prepared()
    selected = import_module(
        "scopeproof_core.reviews.selected_references"
    ).selectable_reference_lines(state, snapshot)[-1]
    state = append(state, snapshot, selected)
    original_id = state.bundle.reviewer_selected_references[0].reference_id
    before = state.model_dump_json()
    with pytest.raises(ValueError):
        correct(state, snapshot, original_id, selected=selected)
    assert state.model_dump_json() == before


def test_same_location_correction_at_32_active_limit_preserves_capacity():
    state, snapshot = source_state([
        ChangedFile(
            path="src/export.py",
            status="modified",
            lines=[
                ChangedLine(
                    change_type=LineChangeType.ADDED,
                    line_number=index + 1,
                    content=f"static_context_{index}()",
                )
                for index in range(32)
            ],
        )
    ])
    lines = import_module(
        "scopeproof_core.reviews.selected_references"
    ).selectable_reference_lines(state, snapshot)
    for selected in lines:
        state = append(state, snapshot, selected)
    original = state.bundle.reviewer_selected_references[0]
    updated = correct(state, snapshot, original.reference_id, selected=lines[0])
    assert len(state.bundle.active_reviewer_selected_reference_ids) == 32
    assert len(updated.bundle.active_reviewer_selected_reference_ids) == 32
    assert len(updated.bundle.reviewer_selected_references) == 33
    assert original.reference_id not in updated.bundle.active_reviewer_selected_reference_ids
    assert updated.bundle.reviewer_selected_references[0] == original
    assert non_audit_payload(updated) == non_audit_payload(state)


@pytest.mark.parametrize("count", [33, 129])
def test_bundle_rejects_excess_active_or_total_references(count):
    state, _ = prepared()
    payload = state.bundle.model_dump(mode="python")
    original = payload["reviewer_selected_references"][0]
    payload["reviewer_selected_references"] = [
        {
            **original,
            "reference_id": f"bounded-reference-{index}",
            "line_number": index + 1,
            "permalink": original["permalink"].split("#")[0] + f"#L{index + 1}-L{index + 1}",
        }
        for index in range(count)
    ]
    with pytest.raises(ValueError):
        ReviewBundle.model_validate(payload)


def test_retained_history_limit_still_allows_terminal_withdrawal():
    state, snapshot = prepared()
    corrected = correct(state, snapshot)
    payload = corrected.model_dump(mode="python")
    bundle = payload["bundle"]
    root = bundle["reviewer_selected_references"][0]
    replacement = bundle["reviewer_selected_references"][1]
    event = bundle["selected_reference_events"][0]
    bundle["reviewer_selected_references"] = [root] + [
        {
            **replacement,
            "reference_id": f"replacement-{index}",
            "selected_at": event["occurred_at"] + timedelta(seconds=index),
        }
        for index in range(127)
    ]
    refs = bundle["reviewer_selected_references"]
    bundle["selected_reference_events"] = [
        {
            **event,
            "event_id": f"correction-{index}",
            "reference_id": refs[index]["reference_id"],
            "replacement_reference_id": refs[index + 1]["reference_id"],
            "occurred_at": refs[index + 1]["selected_at"],
        }
        for index in range(127)
    ]
    saturated = type(state).model_validate(payload)
    with pytest.raises(ValueError):
        correct(saturated, snapshot)
    withdrawn = withdraw(saturated)
    assert len(withdrawn.bundle.reviewer_selected_references) == 128
    assert len(withdrawn.bundle.selected_reference_events) == 128
    assert withdrawn.bundle.active_reviewer_selected_reference_ids == []
