"""Recipient-visible audit metadata and authority distinctions in readable reports."""

import html
import re
from datetime import datetime

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.resolution_audit_fixture import resolution_audit_state


def audit_text(report: str, kind: str) -> str:
    marker = "## Resolution History" if kind == "markdown" else "<h2>Resolution History</h2>"
    assert marker in report
    section = report.split(marker, 1)[1]
    section = section.split("\n## " if kind == "markdown" else "<h2>", 1)[0]
    visible = html.unescape(re.sub(r"<[^>]*>", " ", section))
    return " ".join(re.sub(r"\\(.)", r"\1", visible).replace("**", "").split())


@pytest.mark.parametrize(
    ("kind", "exporter"), [("markdown", export_markdown), ("html", export_html)],
)
def test_readable_history_retains_all_recorded_metadata_in_append_order(kind, exporter):
    state = resolution_audit_state()
    text = audit_text(exporter(state), kind)
    ids = ["r1-old-accept", "r2-old-change", "r2-current-accept", "r2-ac02-accept",
           "r2-ac03-accept", "r2-ac04-accept", "r2-final-true", "r2-final-false"]
    positions = [text.index(event_id) for event_id in ids]
    assert positions == sorted(positions)
    for value in (
        "Event ID", "Event status", "Criteria revision", "Target", "Recorded outcome",
        "Asserted reviewer", "Recorded at (as recorded)", "Reviewer note",
        "Evidence URL (as recorded)", "Claimed evidence level", "Runtime evidence link",
        "Constructed prior reviewer", "Constructed current reviewer", "2027-01-01T00:00:00+00:00",
        "2026-10-31T10:00:00-04:00",
        "https://example.test/current-observation?case=1&mode=recorded",
        "final_acceptance=true", "final_acceptance=false",
    ):
        assert value in text


@pytest.mark.parametrize(
    ("kind", "exporter"), [("markdown", export_markdown), ("html", export_html)],
)
def test_status_follows_target_revision_and_append_order_instead_of_time(kind, exporter):
    text = audit_text(exporter(resolution_audit_state()), kind)
    blocks = re.split(r"Event ID:?\s+", text)[1:]
    assert len(blocks) == 8
    expected = [
        ("r1-old-accept", "Prior revision", "1"),
        ("r2-old-change", "Superseded", "2"),
        ("r2-current-accept", "Current", "2"),
        ("r2-ac02-accept", "Current", "2"),
        ("r2-ac03-accept", "Current", "2"),
        ("r2-ac04-accept", "Current", "2"),
        ("r2-final-true", "Superseded", "2"),
        ("r2-final-false", "Current", "2"),
    ]
    for block, (event_id, status, revision) in zip(blocks, expected, strict=True):
        assert block.startswith(event_id + " ")
        assert re.search(rf"Event status:?\s+{status}\b", block)
        assert re.search(rf"Criteria revision:?\s+{revision}\b", block)


@pytest.mark.parametrize(
    ("kind", "exporter"), [("markdown", export_markdown), ("html", export_html)],
)
def test_empty_saved_history_is_distinct_from_unavailable_bundle_history(kind, exporter):
    state = new_review_state(build_demo_review())
    empty = audit_text(exporter(state), kind)
    unavailable = audit_text(exporter(state.bundle), kind)
    assert "No resolution events were recorded" in empty
    assert "unavailable" not in empty
    assert "Full resolution history is unavailable" in unavailable
    assert "No resolution events were recorded" not in unavailable


@pytest.mark.parametrize(
    ("kind", "exporter"), [("markdown", export_markdown), ("html", export_html)],
)
def test_historical_bundle_does_not_borrow_parent_resolution_history(kind, exporter):
    state = resolution_audit_state()
    text = audit_text(exporter(state.analysis_history[0]), kind)
    assert "Full resolution history is unavailable" in text
    assert "r1-old-accept" not in text
    assert "r2-current-accept" not in text


@pytest.mark.parametrize(
    ("kind", "exporter"), [("markdown", export_markdown), ("html", export_html)],
)
def test_naive_legacy_time_and_explicit_empty_optional_value_remain_visible(kind, exporter):
    state = append_resolution(new_review_state(build_demo_review()), ResolutionEvent(
        event_id="constructed-naive-empty", criterion_id="AC-01",
        decision=HumanDecision.CHANGE_REQUIRED, reviewer="Constructed timezone-unknown actor",
        timestamp=datetime(2025, 1, 2, 3, 4, 5), evidence_url="",
    ))
    text = audit_text(exporter(state), kind)
    assert "2025-01-02T03:04:05 (timezone not recorded)" in text
    assert re.search(r"Evidence URL \(as recorded\):?\s+Empty value recorded", text)
    assert re.search(r"Claimed evidence level:?\s+Not recorded", text)
    assert re.search(r"Runtime evidence link:?\s+Not recorded", text)


def test_readable_exports_preserve_full_state_machine_formats_and_saved_bytes(tmp_path):
    state = resolution_audit_state()
    store = JsonReviewStore(tmp_path)
    store.save(state)
    path = tmp_path / f"{state.review.review_id}.json"
    before = state.model_dump(mode="json")
    saved = path.read_bytes()
    json_text, csv_text = export_json(state), export_csv(state)
    export_markdown(state)
    export_html(state)
    assert state.model_dump(mode="json") == before
    assert path.read_bytes() == saved
    assert export_json(state) == json_text
    assert export_csv(state) == csv_text
