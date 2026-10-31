"""Comparison handoff retains complete asserted context and safe boundaries."""

import json

import pytest
from pydantic import ValidationError

from scopeproof_core.reporting.exporters import export_comparison_json, export_comparison_markdown
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from tests.reviews.test_decision_context_comparison import decision_bundle


def test_json_round_trip_retains_complete_same_label_context_and_no_source_mutation():
    previous = decision_bundle()
    current = previous.model_copy(deep=True)
    current.resolutions[0].comment = "Constructed new note, same decision label"
    current.runtime_evidence[0].limitations = ["Constructed newly observed limitation"]
    before = previous.model_dump_json(), current.model_dump_json()
    result = compare_reviews(previous, current)
    rendered = export_comparison_json(result)
    payload = json.loads(rendered)
    assert payload["changed_human_resolutions"] == []
    context = payload["decision_context_comparison"]
    assert context["current"]["resolutions"][0] == current.resolutions[0].model_dump(mode="json")
    assert context["current"]["runtime_evidence"][0] == current.runtime_evidence[0].model_dump(
        mode="json"
    )
    assert context["record_changes"][0]["kind"] == "recorded_context_changed"
    assert ReviewComparison.model_validate_json(rendered) == result
    assert before == (previous.model_dump_json(), current.model_dump_json())


def test_markdown_shows_both_owners_decision_notes_and_complete_recorded_runtime_fields():
    previous = decision_bundle()
    current = previous.model_copy(deep=True)
    current.resolutions[0].comment = "Constructed new note, same decision label"
    current.runtime_evidence[0].limitations = ["Constructed newly observed limitation"]
    markdown = export_comparison_markdown(compare_reviews(previous, current))
    assert "## Recorded decision and runtime context" in markdown
    assert "Previous decision context" in markdown and "Current decision context" in markdown
    assert "recorded context changed" in markdown
    assert "Constructed new note\\, same decision label" in markdown
    assert "Constructed external observation" in markdown
    for value in (
        previous.review.review_id, previous.review.head_sha, "Criteria revision: 2",
        "Constructed automatic actor", "constructed-runtime-1",
        "Constructed CSV scenario", "Constructed disposable environment",
        "Constructed passed result", "Constructed newly observed limitation",
        "https://example.test/constructed-observation", "E3", "2026-10-30T12:00:00+00:00",
    ):
        assert value in markdown
    assert "ScopeProof did not execute" in markdown
    assert "asserted" in markdown and "gates are unchanged" in markdown


def test_legacy_missing_context_known_empty_and_legacy_unlinked_are_distinct_in_markdown():
    bundle = decision_bundle(linked=False)
    result = compare_reviews(bundle, bundle)
    assert "Legacy unlinked" in export_comparison_markdown(result)
    data = result.model_dump(mode="json")
    data.pop("decision_context_comparison")
    old = ReviewComparison.model_validate(data)
    assert "Decision context was not included in this older comparison" in (
        export_comparison_markdown(old)
    )
    for snapshot in (data["file_scope"]["previous"], data["file_scope"]["current"]):
        assert snapshot["review_id"] == bundle.review.review_id
    empty = decision_bundle(decision=False)
    empty.runtime_evidence = []
    markdown = export_comparison_markdown(compare_reviews(empty, empty))
    assert "No criterion decisions or runtime observations recorded on either side" in markdown


def test_notes_results_and_unsafe_artifact_references_are_inert_in_markdown():
    bundle = decision_bundle()
    bundle.resolutions[0].comment = '<script>alert(1)</script> **Accepted** [click](javascript:bad)'
    bundle.resolutions[0].evidence_url = "javascript:alert(1)"
    bundle.runtime_evidence[0].artifact_reference = "data:text/html,<img src=x onerror=bad>"
    bundle.runtime_evidence[0].result = '<img src=x onerror=bad>\n# False Ready'
    markdown = export_comparison_markdown(compare_reviews(bundle, bundle))
    section = markdown.split("## Recorded decision and runtime context", 1)[1].split(
        "## Evidence Changes", 1
    )[0]
    assert "<script>" not in section and "<img" not in section
    assert "**Accepted**" not in section and "\n# False Ready" not in section
    assert "[click](javascript:" not in section and "](data:" not in section
    assert "&lt;script&gt;" in section and "&lt;img" in section


@pytest.mark.parametrize("renderer", [export_comparison_json, export_comparison_markdown])
def test_all_comparison_exports_revalidate_changed_nested_runtime_links(renderer):
    bundle = decision_bundle()
    result = compare_reviews(bundle, bundle)
    result.decision_context_comparison.current.resolutions[0].runtime_evidence_id = "not-recorded"
    with pytest.raises(ValidationError):
        renderer(result)
