"""Recorded acceptance is inert information, without implied event attribution."""

import pytest
from streamlit.testing.v1 import AppTest


def _render(previous, current, unknown=False, unsafe=False):
    from apps.web.final_acceptance_comparison import render_final_acceptance_comparison
    from scopeproof_core.reviews.comparison import compare_reviews
    from tests.final_acceptance_fixture import acceptance_comparison_states

    current_state, previous_state = acceptance_comparison_states(previous=previous, current=current)
    if unknown:
        from scopeproof_core.gates.evaluator import evaluate_gate

        bundle = previous_state.bundle
        bundle.criteria_revision_number = "unknown"
        bundle.file_scope_decisions = []
        bundle.gate = evaluate_gate(
            bundle.review, bundle.criteria, bundle.findings, bundle.resolutions, bundle.evidence, []
        )
    if unsafe:
        current_state.bundle.review.review_id = "<img src=x> **Ready** [bad](javascript:bad)"
        for decision in current_state.bundle.file_scope_decisions:
            decision.review_id = current_state.bundle.review.review_id
    render_final_acceptance_comparison(
        compare_reviews(previous_state.bundle, current_state.bundle).final_acceptance_comparison
    )


def _render_missing():
    from apps.web.final_acceptance_comparison import render_final_acceptance_comparison

    render_final_acceptance_comparison(None)


def _values(elements):
    return "\n".join(item.value for item in elements)


@pytest.mark.parametrize(
    "previous,current", [(False, False), (False, True), (True, False), (True, True)]
)
def test_explicit_values_both_owners_and_unavailable_attribution_are_visible(previous, current):
    app = AppTest.from_function(_render, args=(previous, current)).run()
    assert not app.exception
    assert "Recorded final acceptance" in _values(app.markdown)
    assert f"Recorded value changed: {'Yes' if previous != current else 'No'}" in _values(app.text)
    for value in (previous, current):
        assert f"Recorded final acceptance: {'Yes' if value else 'No'}" in _values(app.text)
    assert len(app.expander) == 2
    assert "acme/widget" in _values(app.text) and "PR #7" in _values(app.text)
    assert "Criteria revision:" in _values(app.text)
    assert "unavailable" in _values(app.caption)
    assert not app.button and not app.text_input and not app.checkbox


def test_missing_context_is_unavailable_and_never_a_negative_value():
    app = AppTest.from_function(_render_missing).run()
    assert not app.exception
    assert "not included in this older comparison" in _values(app.info)
    assert "Recorded final acceptance: No" not in _values(app.text)


def test_unknown_revision_and_untrusted_owner_are_inert_text():
    app = AppTest.from_function(_render, args=(False, True, True, True)).run()
    assert not app.exception
    assert "Criteria revision: unknown" in _values(app.text)
    assert "<img src=x> **Ready** [bad](javascript:bad)" in _values(app.text)
    assert "<img" not in _values(app.markdown)
    assert "javascript:" not in _values(app.markdown)
