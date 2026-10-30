"""Audit status and original records survive every handoff format."""

import csv
import io
import json

from scopeproof_core.reporting.exporters import (
    export_comparison_markdown,
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.comparison import compare_reviews
from scopeproof_core.reviews.selected_reference_comparison import SelectedReferenceComparison
from tests.reviews.test_reference_audit import correct, withdraw
from tests.reviews.test_selected_references import append, source_state


def audited():
    state, snapshot = source_state()
    original = append(state, snapshot)
    return original, withdraw(correct(original, snapshot))


def test_reports_show_inactive_history_events_and_zero_active():
    _, state = audited()
    payload = json.loads(export_json(state))["bundle"]
    assert payload["active_reviewer_selected_reference_ids"] == []
    assert len(payload["reviewer_selected_references"]) == 2
    assert len(payload["selected_reference_events"]) == 2
    for text in (export_markdown(state), export_html(state)):
        assert "Corrected" in text and "Withdrawn" in text
        assert "Constructed audit actor" in text and "Original rationale" in text
        assert "Audit event" in text and "Active references: 0" in text
        for reference in state.bundle.reviewer_selected_references:
            assert reference.reference_id in text
    rows = list(csv.DictReader(io.StringIO(export_csv(state))))
    row = next(row for row in rows if row["criterion_id"] == state.bundle.criteria[0].criterion_id)
    assert json.loads(row["active_reviewer_selected_reference_ids"]) == []
    assert len(json.loads(row["selected_reference_events"])) == 2
    assert sorted(json.loads(row["selected_reference_statuses"]).values()) == [
        "corrected",
        "withdrawn",
    ]


def test_comparison_keeps_original_record_identity_but_exposes_status_changes():
    old, current = audited()
    comparison = compare_reviews(old.bundle, current.bundle)
    context = comparison.selected_reference_comparison
    assert context.previous_reference_events == []
    assert len(context.current_reference_events) == 2
    assert (
        context.previous_active_reference_ids == old.bundle.active_reviewer_selected_reference_ids
    )
    assert context.current_active_reference_ids == []
    assert (
        context.lifecycle_changed_reference_ids == old.bundle.active_reviewer_selected_reference_ids
    )
    text = export_comparison_markdown(comparison)
    assert "Withdrawn" in text and "Corrected" in text and "Audit event" in text


def test_old_comparison_lifecycle_is_unknown_not_empty():
    old, _ = audited()
    data = SelectedReferenceComparison.from_bundles(old.bundle, old.bundle).model_dump(mode="json")
    data.pop("previous_reference_events")
    data.pop("current_reference_events")
    legacy = SelectedReferenceComparison.model_validate(data)
    assert legacy.previous_active_reference_ids is None
    assert legacy.current_active_reference_ids is None
