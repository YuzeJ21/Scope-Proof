"""Audit handoffs retain original JUnit context and make retirement explicit."""

import csv
import html
import io
import json
import re
from datetime import UTC, datetime

import pytest

from scopeproof_core.importers.junit import JUnitMappingSelection, build_junit_evidence_import
from scopeproof_core.reporting.exporters import (
    export_comparison_json,
    export_comparison_markdown,
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reporting.historical_analysis import (
    export_historical_json,
    export_historical_markdown,
)
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.reviews.historical_analysis import (
    locked_historical_analysis,
    prepare_historical_analysis,
)
from scopeproof_core.reviews.junit_audit import withdraw_junit_evidence_import
from scopeproof_core.reviews.lifecycle import append_junit_evidence_import, revise_criteria
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import JUNIT_AUDIT_XML, junit_audit_state

_ARTIFACT = "4ade313a449dfcc98c02a483c8adcddfc5edddf9e2a10b16f9e44e2820ed1ccc"
_OCCURRED_AT = datetime(2026, 11, 1, 13, 14, 15, tzinfo=UTC)
_REVIEWER = 'CONSTRUCTED <script>alert("actor")</script> [actor](javascript:1)'
_REASON = 'CONSTRUCTED <img src=x onerror="alert(1)"> [details](https://evil.test/) `reason`'


def _withdraw(state):
    return withdraw_junit_evidence_import(
        state, import_id="constructed-junit-import", reviewer=_REVIEWER, reason=_REASON,
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        occurred_at=_OCCURRED_AT,
    )


def _two_imports():
    state = junit_audit_state()
    second = build_junit_evidence_import(
        state, JUNIT_AUDIT_XML.replace(b"audit suite", b"second suite"),
        [JUnitMappingSelection(scope_id="suite-0001-case-0001", criterion_id="AC-01")],
        importer="CONSTRUCTED retained active actor", import_id="constructed-active-import",
        imported_at=datetime(2026, 11, 1, 12, 1, tzinfo=UTC),
    )
    return append_junit_evidence_import(state, second)


def _assert_event_payload(event, event_id):
    assert event["schema_version"] == "junit-import-withdrawal-v1"
    assert event["action"] == "withdrawn"
    assert event["event_id"] == event_id
    assert event["import_id"] == "constructed-junit-import"
    assert event["artifact_sha256"] == _ARTIFACT
    assert event["review_id"] == "constructed-junit-audit-review"
    assert event["repository"] == "constructed/audit-example"
    assert event["pr_number"] == 17
    assert event["head_sha"] == "a" * 40
    assert event["criteria_revision_number"] == 1
    assert event["reviewer"] == _REVIEWER
    assert event["reason"] == _REASON
    assert event["occurred_at"] == "2026-11-01T13:14:15Z"
    assert event["confirmed_criteria_sha256"] == (
        "1088d3732ddc7d51ae46032c87254c1ad05cf068a4a9ad488c9c8ea152bebb29"
    )
    assert event["criteria_source_provenance"] == {
        "source_uri": "scopeproof://constructed-demo/acceptance-criteria",
        "source_revision": "constructed-junit-audit-v1",
        "source_text_sha256": "cec2daac042dee106625eb37bd737d679f11cced8527b27ac40930fa288218ef",
        "normalized_criteria_sha256": (
            "1088d3732ddc7d51ae46032c87254c1ad05cf068a4a9ad488c9c8ea152bebb29"
        ),
        "confirmed_by": "CONSTRUCTED criteria actor",
        "confirmed_at": "2026-11-01T12:00:00Z",
    }
    assert event["evidence_boundary"]["gate_effect"] == "non_gating"
    assert event["evidence_boundary"]["execution"] == "not_executed_by_scopeproof"


def _assert_inert_complete_event(report, event_id, *, markdown=False):
    # Compare displayed facts across the two encodings without assuming HTML code spans.
    display_text = re.sub(r"\\([^\w\s])", r"\1", report) if markdown else report
    display_text = html.unescape(display_text)
    for value in (
        event_id, "constructed-junit-import", _ARTIFACT, "a" * 40,
        "constructed-junit-audit-review", "constructed/audit-example",
        "2026-11-01T13:14:15", "constructed-junit-audit-v1",
        "scopeproof://constructed-demo/acceptance-criteria", "CONSTRUCTED criteria actor",
        "1088d3732ddc7d51ae46032c87254c1ad05cf068a4a9ad488c9c8ea152bebb29",
        "cec2daac042dee106625eb37bd737d679f11cced8527b27ac40930fa288218ef",
    ):
        assert value in display_text
    assert _REVIEWER in display_text
    assert _REASON in display_text
    if markdown:
        assert r"\[actor\]\(" in report
        assert r"\[details\]\(" in report
        assert "[actor](" not in report
        assert "[details](" not in report
    assert "<script>" not in report
    assert "<img src=x" not in report
    assert '<a href="javascript:' not in report
    assert '<a href="https://evil.test/' not in report


@pytest.mark.parametrize("as_state", [True, False], ids=["state", "bundle"])
def test_json_preserves_originals_terminal_event_and_only_remaining_active_id(as_state):
    original = _two_imports()
    state = _withdraw(original)
    before = state.model_dump(mode="json")
    value = state if as_state else state.bundle

    rendered = export_json(value)
    payload = json.loads(rendered)
    bundle = payload["bundle"] if as_state else payload

    assert bundle["junit_evidence_imports"] == (
        original.bundle.model_dump(mode="json")["junit_evidence_imports"]
    )
    assert len(bundle["junit_import_events"]) == 1
    _assert_event_payload(
        bundle["junit_import_events"][0], state.bundle.junit_import_events[0].event_id,
    )
    assert bundle["active_junit_import_ids"] == ["constructed-active-import"]
    assert bundle["gate"] == original.bundle.model_dump(mode="json")["gate"]
    assert bundle["runtime_evidence"] == []
    assert bundle["resolutions"] == []
    assert export_json(value) == rendered
    assert state.model_dump(mode="json") == before


@pytest.mark.parametrize("exporter", [export_markdown, export_html], ids=["markdown", "html"])
def test_human_reports_label_both_retained_import_statuses_and_complete_audit(exporter):
    state = _withdraw(_two_imports())

    report = exporter(state)

    assert "constructed-junit-import" in report
    assert "constructed-active-import" in report
    assert "Active" in report
    assert "Withdrawn" in report
    assert "suite-0001-case-0001" in report
    assert "suite-0001-case-0002" in report
    assert "CONSTRUCTED pass" in report and "CONSTRUCTED failure" in report
    _assert_inert_complete_event(
        report, state.bundle.junit_import_events[0].event_id,
        markdown=exporter is export_markdown,
    )
    assert "non-gating" in report
    assert "asserted, not authenticated" in report
    assert "organizational context, not proof" in report


def test_csv_appends_audit_per_affected_criterion_and_preserves_retained_columns():
    original = _two_imports()
    state = _withdraw(original)
    old_reader = csv.DictReader(io.StringIO(export_csv(original)))
    old_rows = list(old_reader)
    reader = csv.DictReader(io.StringIO(export_csv(state)))
    rows = list(reader)

    assert reader.fieldnames[-1] == "junit_import_audit"
    assert [row["criterion_id"] for row in rows] == ["AC-01", "AC-02"]
    retained_columns = (
        "junit_artifact_digests", "junit_mapped_cases", "junit_evidence_boundary",
        "junit_importers", "junit_parser_warnings", "junit_limitations",
        "gate_reason_codes", "gate_blocking_criteria", "gate_conditional_criteria",
        "gate_unresolved_criteria", "gate_resolved_exceptions", "gate_guidance",
    )
    assert all(name in reader.fieldnames for name in retained_columns)
    for old_row, row in zip(old_rows, rows, strict=True):
        for name in retained_columns:
            assert row[name] == old_row[name]
        audit = json.loads(row["junit_import_audit"])
        assert audit[0]["import_id"] == "constructed-junit-import"
        assert audit[0]["artifact_sha256"] == _ARTIFACT
        assert audit[0]["status"] == "withdrawn"
        _assert_event_payload(
            audit[0]["withdrawal_event"], state.bundle.junit_import_events[0].event_id,
        )
        cases = json.loads(row["junit_mapped_cases"])
        expected_case = "suite-0001-case-0001" if row["criterion_id"] == "AC-01" else (
            "suite-0001-case-0002"
        )
        assert cases[0]["test_case_id"] == expected_case
        assert cases[0]["import_id"] == "constructed-junit-import"
        if row["criterion_id"] == "AC-01":
            assert len(audit) == 2
            assert audit[1]["import_id"] == "constructed-active-import"
            assert audit[1]["status"] == "active"
            assert audit[1]["withdrawal_event"] is None
        else:
            assert len(audit) == 1


def test_comparison_exports_show_withdrawn_event_both_mappings_and_unchanged_gates():
    previous = junit_audit_state()
    current = _withdraw(previous)
    comparison = compare_reviews(previous.bundle, current.bundle)

    payload = json.loads(export_comparison_json(comparison))
    change = payload["junit_import_changes"][0]
    assert change["kind"] == "context_modified"
    assert change["previous"]["status"] == "active"
    assert change["previous"]["withdrawal_event"] is None
    assert change["current"]["status"] == "withdrawn"
    _assert_event_payload(
        change["current"]["withdrawal_event"], current.bundle.junit_import_events[0].event_id,
    )
    assert change["previous"]["mappings"] == change["current"]["mappings"] == [
        {"criterion_id": "AC-01", "test_case_ids": ["suite-0001-case-0001"]},
        {"criterion_id": "AC-02", "test_case_ids": ["suite-0001-case-0002"]},
    ]
    assert payload["previous_gate"] == payload["current_gate"]
    markdown = export_comparison_markdown(comparison)
    assert "Previous import" in markdown and "Current import" in markdown
    assert "Active" in markdown and "Withdrawn" in markdown
    _assert_inert_complete_event(
        markdown, current.bundle.junit_import_events[0].event_id, markdown=True,
    )


def test_legacy_comparison_markdown_explicitly_labels_status_unavailable():
    state = junit_audit_state()
    payload = compare_reviews(state.bundle, state.bundle).model_dump(mode="json")
    for side in ("previous", "current"):
        payload["junit_import_changes"][0][side].pop("status", None)
        payload["junit_import_changes"][0][side].pop("withdrawal_event", None)
    comparison = ReviewComparison.model_validate(payload)

    markdown = export_comparison_markdown(comparison)

    assert "status unavailable" in markdown.lower()
    assert "Status: <code>Active</code>" not in markdown
    assert "Status: Active" not in markdown


def test_archived_exports_keep_the_original_owning_revision_and_terminal_event(tmp_path):
    withdrawn = _withdraw(junit_audit_state())
    state = revise_criteria(
        withdrawn, withdrawn.criteria_revision.criteria, withdrawn.criteria_revision.source_text,
    )
    store = JsonReviewStore(tmp_path / "constructed-junit-records")
    path = store.save(state)
    original_bytes = path.read_bytes()

    selection = prepare_historical_analysis(store, state, 0)
    with locked_historical_analysis(store, selection) as report:
        payload = json.loads(export_historical_json(report))
        markdown = export_historical_markdown(report)

    assert payload["analysis"]["criteria_revision_number"] == 1
    assert payload["analysis"]["active_junit_import_ids"] == []
    assert len(payload["analysis"]["junit_evidence_imports"]) == 1
    event = payload["analysis"]["junit_import_events"][0]
    _assert_event_payload(event, withdrawn.bundle.junit_import_events[0].event_id)
    assert event["criteria_revision_number"] != state.criteria_revision.number
    assert "Withdrawn" in markdown
    _assert_inert_complete_event(markdown, event["event_id"], markdown=True)
    assert "not current-head verification" in markdown
    assert path.read_bytes() == original_bytes


@pytest.mark.parametrize("exporter", [export_json, export_markdown, export_html, export_csv])
def test_report_export_revalidates_mutated_audit_ownership(exporter):
    state = _withdraw(junit_audit_state())
    state.bundle.junit_import_events[0] = state.bundle.junit_import_events[0].model_copy(
        update={"review_id": "foreign-review"},
    )

    with pytest.raises(ValueError):
        exporter(state)
