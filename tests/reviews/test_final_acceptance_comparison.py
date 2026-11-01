"""Recorded flags explain equal gate labels without adding acceptance authority."""

import json
from importlib import import_module

import pytest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from tests.final_acceptance_fixture import acceptance_comparison_states


@pytest.mark.parametrize("previous,current", [(False, False), (False, True),
                                              (True, False), (True, True)])
def test_all_flags_are_explicit_even_under_equal_conditional_gates(previous, current):
    new, old = acceptance_comparison_states(previous=previous, current=current)
    before = old.model_dump_json(), new.model_dump_json()
    comparison = compare_reviews(old.bundle, new.bundle)
    assert comparison.previous_gate.value == comparison.current_gate.value == "conditional"
    assert comparison.final_acceptance_compared is True
    context = comparison.final_acceptance_comparison
    assert context.previous.recorded_final_acceptance is previous
    assert context.current.recorded_final_acceptance is current
    assert context.recorded_value_changed is (previous != current)
    assert context.previous.review_id == old.review.review_id
    assert context.current.head_sha == new.review.head_sha
    assert context.current.event_context_status == "unavailable_in_analysis_snapshot"
    assert "revocation" in context.boundary
    assert before == (old.model_dump_json(), new.model_dump_json())


def test_old_comparison_has_unavailable_context_never_false_defaults():
    new, old = acceptance_comparison_states()
    payload = compare_reviews(old.bundle, new.bundle).model_dump(mode="json")
    payload.pop("final_acceptance_comparison")
    payload["final_acceptance_compared"] = True
    loaded = ReviewComparison.model_validate(payload)
    assert loaded.final_acceptance_comparison is None
    assert loaded.final_acceptance_compared is False


def test_derived_change_and_availability_are_recomputed_on_json_roundtrip():
    new, old = acceptance_comparison_states()
    payload = json.loads(compare_reviews(old.bundle, new.bundle).model_dump_json())
    payload["final_acceptance_comparison"]["recorded_value_changed"] = False
    payload["final_acceptance_compared"] = False
    loaded = ReviewComparison.model_validate(payload)
    assert loaded.final_acceptance_compared is True
    assert loaded.final_acceptance_comparison.recorded_value_changed is True


def test_projection_is_detached_and_unknown_revision_stays_unknown():
    new, old = acceptance_comparison_states()
    legacy = old.bundle.model_copy(deep=True)
    legacy.criteria_revision_number = "unknown"
    legacy.file_scope_decisions = []
    legacy.gate = evaluate_gate(legacy.review, legacy.criteria, legacy.findings,
                               legacy.resolutions, legacy.evidence, [])
    comparison = compare_reviews(legacy, new.bundle)
    context = comparison.final_acceptance_comparison
    assert context.previous.criteria_revision_number == "unknown"
    changed = context.previous.model_copy(update={"review_id": "CONSTRUCTED detached"})
    assert old.bundle.review.review_id != changed.review_id
    assert context.previous.review_id == old.bundle.review.review_id


@pytest.mark.parametrize("value", [None, 0, 1, "false", "true"])
def test_snapshot_requires_an_explicit_strict_boolean(value):
    new, old = acceptance_comparison_states()
    data = compare_reviews(old.bundle, new.bundle).final_acceptance_comparison.previous.model_dump()
    data["recorded_final_acceptance"] = value
    api = import_module("scopeproof_core.reviews.final_acceptance_comparison")
    with pytest.raises(ValueError):
        api.FinalAcceptanceSnapshot.model_validate(data)
