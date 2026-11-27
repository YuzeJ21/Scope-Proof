"""Offline comparison reports expose supplied context and retain acceptance boundaries."""

import re
from hashlib import sha256

import pytest

from scopeproof_core.reporting.ci_comparison import export_ci_comparison_html
from scopeproof_core.reviews.ci_comparison import CI_COMPARISON_BOUNDARY, compare_ci_status
from tests.ci_comparison_fixture import ci_comparison_inputs
from tests.test_offline_handoff_sample import ReportParser


def comparison():
    state, _, _, before, after = ci_comparison_inputs()
    result = compare_ci_status(state.bundle, before, after)
    return result


def test_report_cites_both_contexts_and_unchanged_recorded_gate():
    value = comparison()
    original = value.model_dump(mode="python")
    html = export_ci_comparison_html(value)
    assert "ScopeProof CI Context Comparison" in html
    assert CI_COMPARISON_BOUNDARY in html
    assert value.previous_sha256 in html and value.current_sha256 in html
    assert value.bundle.review.head_sha in html
    assert "Action required" in html and "Recorded final acceptance" in html
    assert "No" in html
    assert "Explicitly skipped" in html and "Failed" in html
    assert "Retained effective result" in html
    assert "Introduced in current manifest" in html
    assert "not verified chronology" in html
    assert "does not erase" in html
    assert "AC-01" in html and "AC-02" in html and "AC-03" in html
    assert value.model_dump(mode="python") == original
    assert html == export_ci_comparison_html(value)


def test_report_has_one_test_row_and_resolving_citations_for_every_source():
    html = export_ci_comparison_html(comparison())
    for test_id in ("category_filter", "row_entitlement", "csv_header"):
        assert html.count(f'data-test-id="{test_id}"') == 1
    links = re.findall(r'href="(#[^"]+)"', html)
    assert links
    for link in links:
        assert f'id="{link[1:]}"' in html
    for label in ("A", "B", "B-targeted"):
        assert f"https://ci.example.invalid/builds/{label}" in html


def test_report_is_self_contained_and_tables_are_keyboard_scrollable():
    html = export_ci_comparison_html(comparison())
    parser = ReportParser()
    parser.feed(html)
    assert parser.resources == []
    assert not {"script", "iframe", "form", "object", "embed"}.intersection(parser.tags)
    assert 'aria-label="CI result comparison"' in html
    assert 'aria-label="CI run comparison"' in html
    assert html.count('tabindex="0"') == 2
    assert "overflow-x:auto" in html


def test_report_revalidates_context_after_nested_input_mutation():
    value = comparison()
    value.current_manifest.repository = "different/repository"
    with pytest.raises(ValueError):
        export_ci_comparison_html(value)


@pytest.mark.parametrize("change", ["outcome", "reference"])
def test_valid_nested_edits_cannot_reuse_the_original_manifest_digest(change):
    value = comparison()
    if change == "outcome":
        value.current_manifest.runs[-1].outcomes["row_entitlement"] = "passed"
    else:
        value.current_manifest.runs[-1].source_url += "?different=assertion"
    with pytest.raises(ValueError):
        export_ci_comparison_html(value)


def test_identical_inputs_still_disclose_both_digests_and_no_effective_changes():
    state, _, _, before, _ = ci_comparison_inputs()
    differently_formatted = before + b"\n"
    value = compare_ci_status(state.bundle, before, differently_formatted)
    html = export_ci_comparison_html(value)
    assert "No changes to effective test rows" in html
    assert sha256(before).hexdigest() in html
    assert sha256(differently_formatted).hexdigest() in html


def test_run_reference_query_parameters_are_escaped():
    state, _, current, before, _ = ci_comparison_inputs()
    current.runs[-1].source_url += "?task=one&scope=two"
    after = (current.model_dump_json(indent=2) + "\n").encode()
    value = compare_ci_status(state.bundle, before, after)
    html = export_ci_comparison_html(value)
    assert "?task=one&amp;scope=two" in html
    assert "?task=one&scope=two" not in html
    assert sha256(after).hexdigest() in html
