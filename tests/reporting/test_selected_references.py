"""Selected references export attribution without inflating automatic evidence."""

import csv
import io
import json

import pytest

from scopeproof_core.demo import build_review, load_demo_labels, load_demo_snapshot
from scopeproof_core.reporting.exporters import (
    export_comparison_json,
    export_comparison_markdown,
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.comparison import compare_reviews
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.saved_comparison_fixture import saved_comparison_states


def selected_state():
    from scopeproof_core.reviews.selected_references import (
        append_reviewer_selected_reference,
        selectable_reference_lines,
    )

    snapshot = load_demo_snapshot()
    snapshot.files.append(
        ChangedFile(
            path="src/selected.py",
            status="modified",
            lines=[
                ChangedLine(
                    change_type=LineChangeType.ADDED,
                    line_number=9,
                    content="    return '<script>bad</script>'",
                )
            ],
        )
    )
    labels = {**load_demo_labels(), "resolutions": [], "final_acceptance": False}
    state = new_review_state(build_review(snapshot, labels))
    line = next(
        item
        for item in selectable_reference_lines(state, snapshot)
        if item.file_path == "src/selected.py"
    )
    return append_reviewer_selected_reference(
        state,
        snapshot=snapshot,
        selected=line,
        criterion_id="AC-01",
        reviewer="=Actor <script>bad</script>",
        rationale="=SUM(1,1) <img src=x>",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
    )


def test_comparison_empty_selected_context_is_explicitly_available() -> None:
    current, previous = saved_comparison_states()
    comparison = compare_reviews(previous.bundle, current.bundle)
    payload = json.loads(export_comparison_json(comparison))
    assert payload["reviewer_selected_references_compared"] is True
    assert payload["selected_reference_comparison"]["previous"] == []
    assert payload["selected_reference_comparison"]["current"] == []
    report = export_comparison_markdown(comparison)
    assert "No selected references recorded in either analysis" in report
    assert "excluded from this comparison" not in report


def test_comparison_preserves_both_attributed_records_with_safe_markdown() -> None:
    state = selected_state()
    comparison = compare_reviews(state.bundle, state.bundle)
    payload = json.loads(export_comparison_json(comparison))
    context = payload["selected_reference_comparison"]
    reference = state.bundle.reviewer_selected_references[0]
    assert context["previous"] == context["current"] == [reference.model_dump(mode="json")]
    assert context["change_counts"] == {
        "identical_record": 1, "only_previous": 0, "only_current": 0,
    }
    report = export_comparison_markdown(comparison)
    assert "Previous selected reference" in report and "Current selected reference" in report
    for expected in (reference.reference_id, reference.head_sha, reference.excerpt_sha256):
        assert expected in report
    assert "&lt;script&gt;" in report and "<script>" not in report
    assert "&lt;img src=x&gt;" in report and "<img src=x>" not in report
    assert "non-gating static context" in report and "intent, not execution" in report


def test_legacy_comparison_does_not_invent_empty_selected_snapshots() -> None:
    from scopeproof_core.reviews.comparison import ReviewComparison

    current, previous = saved_comparison_states()
    data = compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")
    data.pop("selected_reference_comparison")
    legacy = ReviewComparison.model_validate(data)
    payload = json.loads(export_comparison_json(legacy))
    assert payload["reviewer_selected_references_compared"] is False
    assert payload["selected_reference_comparison"] is None
    assert "Selected-reference context was not included" in export_comparison_markdown(legacy)


def test_all_report_formats_preserve_attribution_source_and_non_gating_boundary() -> None:
    state = selected_state()
    reference = state.bundle.reviewer_selected_references[0]
    parsed = json.loads(export_json(state))
    assert parsed["bundle"]["reviewer_selected_references"] == [reference.model_dump(mode="json")]
    markdown = export_markdown(state)
    page = export_html(state)
    rows = list(csv.DictReader(io.StringIO(export_csv(state))))
    for text in (markdown, page):
        assert "Reviewer-selected" in text and "non-gating" in text
        assert "src/selected.py" in text and reference.head_sha in text
        assert "AC-01" in text and reference.excerpt_sha256 in text
        assert "&lt;script&gt;" in text and "<script>" not in text
        assert "&lt;img src=x&gt;" in text and "<img src=x>" not in text
        assert "intent, not execution" in text
    selected = next(row for row in rows if row["criterion_id"] == "AC-01")
    assert json.loads(selected["reviewer_selected_references"]) == [
        reference.model_dump(mode="json")
    ]
    assert "non-gating" in selected["reviewer_selected_reference_boundary"]
    for row in rows:
        assert row["evidence_count"] == str(
            len(
                next(
                    f for f in state.bundle.findings if f.criterion_id == row["criterion_id"]
                ).evidence_ids
            )
        )
        if row["criterion_id"] != "AC-01":
            assert json.loads(row["reviewer_selected_references"]) == []
            assert row["reviewer_selected_reference_boundary"] == ""


@pytest.mark.parametrize("renderer", [export_json, export_markdown, export_csv, export_html])
def test_exports_revalidate_tampered_selected_reference_digest(renderer) -> None:
    state = selected_state()
    state.bundle.reviewer_selected_references[0] = state.bundle.reviewer_selected_references[
        0
    ].model_copy(update={"excerpt": "forged different source"})
    with pytest.raises(ValueError):
        renderer(state)
