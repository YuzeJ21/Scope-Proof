"""Comparison recipients can distinguish acceptance flags from gate verdicts."""

import json

import pytest

from scopeproof_core.reporting.exporters import export_comparison_json, export_comparison_markdown
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews


@pytest.mark.parametrize(
    "previous,current", [(False, False), (False, True), (True, False), (True, True)]
)
def test_reports_show_recorded_values_separately_from_identical_conditional_gates(
    previous, current
):
    from tests.final_acceptance_fixture import acceptance_comparison_states

    current_state, previous_state = acceptance_comparison_states(previous=previous, current=current)
    before = current_state.model_dump_json(), previous_state.model_dump_json()
    comparison = compare_reviews(previous_state.bundle, current_state.bundle)
    markdown = export_comparison_markdown(comparison)
    section = markdown.split("## Recorded final acceptance", 1)[1].split("## Evidence Changes", 1)[
        0
    ]
    assert "Previous recorded final acceptance" in section
    assert "Current recorded final acceptance" in section
    assert f"Recorded value changed: {'Yes' if previous != current else 'No'}" in section
    for state, value in ((previous_state, previous), (current_state, current)):
        assert f"Recorded final acceptance: {'Yes' if value else 'No'}" in section
        assert state.review.review_id in section
        assert state.review.head_sha in section
        assert f"Criteria revision: {state.bundle.criteria_revision_number}" in section
    assert "unavailable" in section and "attribution" in section
    assert "revocation" in section and "never" in section
    assert "**Previous review status:** <code>conditional</code>" in markdown
    assert "**Current review status:** <code>conditional</code>" in markdown
    payload = json.loads(export_comparison_json(comparison))
    assert payload["final_acceptance_compared"] is True
    assert (
        payload["final_acceptance_comparison"]["previous"]["recorded_final_acceptance"] is previous
    )
    assert payload["final_acceptance_comparison"]["current"]["recorded_final_acceptance"] is current
    assert before == (current_state.model_dump_json(), previous_state.model_dump_json())


def test_old_comparison_does_not_invent_false_acceptance_values():
    from tests.final_acceptance_fixture import acceptance_comparison_states

    current, previous = acceptance_comparison_states()
    data = compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")
    data.pop("final_acceptance_comparison", None)
    old = ReviewComparison.model_validate(data)
    section = (
        export_comparison_markdown(old)
        .split("## Recorded final acceptance", 1)[1]
        .split("## Evidence Changes", 1)[0]
    )
    assert "not included in this older comparison" in section
    assert "Recorded final acceptance: No" not in section
    assert "Recorded final acceptance: Yes" not in section
    assert json.loads(export_comparison_json(old))["final_acceptance_compared"] is False


def test_unknown_revision_and_untrusted_identity_stay_literal_in_markdown():
    from tests.final_acceptance_fixture import acceptance_comparison_states

    current, previous = acceptance_comparison_states()
    from scopeproof_core.gates.evaluator import evaluate_gate

    previous.bundle.criteria_revision_number = "unknown"
    previous.bundle.file_scope_decisions = []
    previous.bundle.gate = evaluate_gate(
        previous.bundle.review,
        previous.bundle.criteria,
        previous.bundle.findings,
        previous.bundle.resolutions,
        previous.bundle.evidence,
        [],
    )
    current.bundle.review.review_id = "<img src=x> **Ready** [bad](javascript:bad)"
    for decision in current.bundle.file_scope_decisions:
        decision.review_id = current.bundle.review.review_id
    markdown = export_comparison_markdown(compare_reviews(previous.bundle, current.bundle))
    section = markdown.split("## Recorded final acceptance", 1)[1].split("## Evidence Changes", 1)[
        0
    ]
    assert "Criteria revision: unknown" in section
    assert "<img" not in section
    assert "<code>&lt;img src=x&gt; **Ready** [bad](javascript:bad)</code>" in section


def test_installed_recipe_retains_explicit_acceptance_values_for_each_baseline(tmp_path):
    from scopeproof_core.reviews.saved_comparison import (
        locked_saved_comparison,
        prepare_saved_comparison,
    )
    from scopeproof_core.storage.json_store import JsonReviewStore
    from tests.saved_comparison_fixture import saved_comparison_states

    current, previous = saved_comparison_states(foreign_history=True, final_acceptance_context=True)
    store = JsonReviewStore(tmp_path)
    store.save(current)
    store.save(previous)
    for owner, index in ((previous, None), (current, 0), (previous, 0)):
        selection = prepare_saved_comparison(
            store, current, owner.review.review_id, history_index=index
        )
        with locked_saved_comparison(store, selection) as result:
            assert result.previous_gate.value == result.current_gate.value == "conditional"
            context = result.final_acceptance_comparison
            assert context.previous.recorded_final_acceptance is False
            assert context.current.recorded_final_acceptance is True
