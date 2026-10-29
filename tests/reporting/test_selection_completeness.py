"""Exports disclose bounded candidate selection without upgrading evidence."""

import csv
import io
import json
from pathlib import Path

from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import ReviewBundle
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.candidate_selection_fixture import selection_bundle

COUNTERS = ("eligible_candidate_count", "candidate_limit", "omitted_candidate_count")
SELECTION = (
    "8 of 12 candidates passing search filters shown; "
    "4 omitted during selection (limit: 8)."
)
UNKNOWN = "Candidate selection completeness was not recorded for this review."
BOUNDARY = (
    "Search diagnostics explain retrieval; they are not evidence that the criterion "
    "is satisfied or missing from the repository."
)


def test_real_selection_counts_survive_all_export_formats() -> None:
    bundle = selection_bundle()
    original_gate = bundle.gate.model_copy(deep=True)
    original_findings = [item.model_copy(deep=True) for item in bundle.findings]

    payload = json.loads(export_json(bundle))
    reader = csv.DictReader(io.StringIO(export_csv(bundle)))
    row = next(reader)
    csv_diagnostic = json.loads(row["retrieval_diagnostic"])
    for diagnostic in (payload["retrieval_diagnostics"][0], csv_diagnostic):
        assert diagnostic["accepted_candidate_count"] == 8
        assert diagnostic["eligible_candidate_count"] == 12
        assert diagnostic["candidate_limit"] == 8
        assert diagnostic["omitted_candidate_count"] == 4
    assert not set(COUNTERS).intersection(reader.fieldnames or [])
    assert len(payload["evidence"]) == 8
    for report in (export_markdown(bundle), export_html(bundle)):
        assert SELECTION in report
        assert BOUNDARY in report
        assert UNKNOWN not in report
    assert bundle.gate == original_gate
    assert bundle.findings == original_findings
    assert bundle.resolutions == []


def test_raw_legacy_bundle_exports_unknown_selection_instead_of_zero() -> None:
    payload = selection_bundle().model_dump(mode="json")
    for diagnostic in payload["retrieval_diagnostics"]:
        for key in COUNTERS:
            diagnostic.pop(key, None)
    legacy = ReviewBundle.model_validate_json(json.dumps(payload))

    exported = json.loads(export_json(legacy))
    row = next(csv.DictReader(io.StringIO(export_csv(legacy))))
    for diagnostic in (
        exported["retrieval_diagnostics"][0],
        json.loads(row["retrieval_diagnostic"]),
    ):
        assert diagnostic["accepted_candidate_count"] == 8
        for key in COUNTERS:
            assert diagnostic[key] is None
    for report in (export_markdown(legacy), export_html(legacy)):
        assert UNKNOWN in report
        assert SELECTION not in report
        assert BOUNDARY in report


def test_saved_legacy_state_retains_unknown_counts_after_reopen(tmp_path: Path) -> None:
    state = new_review_state(selection_bundle())
    store = JsonReviewStore(tmp_path / "reviews")
    record_path = store.save(state)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    for diagnostic in record["state"]["bundle"]["retrieval_diagnostics"]:
        for key in COUNTERS:
            diagnostic.pop(key, None)
    record_path.write_text(json.dumps(record), encoding="utf-8")

    reopened = store.load(state.review.review_id)
    exported = json.loads(export_json(reopened))
    diagnostic = exported["bundle"]["retrieval_diagnostics"][0]
    assert diagnostic["accepted_candidate_count"] == 8
    for key in COUNTERS:
        assert diagnostic[key] is None
    assert UNKNOWN in export_markdown(reopened)
    assert UNKNOWN in export_html(reopened)
    assert reopened.bundle.gate == state.bundle.gate
    assert reopened.bundle.findings == state.bundle.findings
    assert reopened.resolution_events == state.resolution_events
