"""Constructed handoffs distinguish retained originals, effective mappings and audit."""

import csv
import html
import io
import json
import re
import string
from datetime import UTC, datetime

import pytest

from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.importers.junit import JUnitMappingSelection, build_junit_evidence_import
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.junit_audit import (
    effective_junit_mappings,
    junit_mapping_correction_events,
)
from scopeproof_core.reviews.junit_correction import correct_junit_mappings
from scopeproof_core.reviews.lifecycle import append_junit_evidence_import, new_review_state
from scopeproof_core.schemas.models import Criterion, JUnitCriterionMapping, ReviewBundle
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.verification.service import build_findings
from tests.junit_audit_fixture import JUNIT_AUDIT_XML, junit_audit_state

IMPORT_ID = "constructed-junit-import"
CASE1, CASE2, CASE3 = (f"suite-0001-case-000{i}" for i in (1, 2, 3))
REVIEWER = 'CONSTRUCTED <script>alert("actor")</script> [actor](javascript:1)'
REASON = 'CONSTRUCTED <img src=x onerror="alert(1)"> [details](https://evil.test/) `reason`'
OCCURRED_AT = datetime(2026, 11, 1, 13, 14, 15, tzinfo=UTC)


def correction_state():
    """Rebuild a valid confirmed analysis; never mutate bound import provenance."""
    base = junit_audit_state()
    criteria = [
        *base.bundle.criteria,
        Criterion(
            criterion_id="AC-03",
            text="CONSTRUCTED third behavior",
        ),
    ]
    source = base.bundle.source_text + "; CONSTRUCTED third behavior"
    provenance = build_criteria_source_provenance(
        source_uri=base.review.criteria_source_provenance.source_uri,
        source_revision="constructed-three-criterion-v1",
        source_text=source,
        criteria=criteria,
        confirmed_by="CONSTRUCTED criteria actor",
        confirmed_at=base.review.created_at,
    )
    review = base.review.model_copy(update={"criteria_source_provenance": provenance})
    findings = build_findings(criteria, [], review.ingestion_state)
    state = new_review_state(
        ReviewBundle(
            review=review,
            source_text=source,
            criteria=criteria,
            evidence=[],
            findings=findings,
            gate=evaluate_gate(review, criteria, findings, [], []),
        )
    )
    artifact = JUNIT_AUDIT_XML.replace(
        b"</testsuite>",
        b'<testcase name="CONSTRUCTED initially unassigned"/></testsuite>',
    )
    imported = build_junit_evidence_import(
        state,
        artifact,
        [
            JUnitMappingSelection(scope_id=CASE1, criterion_id="AC-01"),
            JUnitMappingSelection(scope_id=CASE2, criterion_id="AC-02"),
        ],
        importer="CONSTRUCTED JUnit actor",
        import_id=IMPORT_ID,
        imported_at=base.review.created_at,
    )
    return append_junit_evidence_import(state, imported)


def mappings(*groups):
    return [
        JUnitCriterionMapping(criterion_id=criterion, test_case_ids=sorted(cases))
        for criterion, cases in sorted(groups)
    ]


def correct(state, replacement, *, reason=REASON):
    return correct_junit_mappings(
        state,
        import_id=IMPORT_ID,
        criterion_mappings=replacement,
        reviewer=REVIEWER,
        reason=reason,
        confirm_whole_import=True,
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        occurred_at=OCCURRED_AT,
    )


def moved(state):
    return correct(state, mappings(("AC-02", [CASE2, CASE3]), ("AC-03", [CASE1])))


def csv_rows(state):
    reader = csv.DictReader(io.StringIO(export_csv(state)))
    return reader.fieldnames, {row["criterion_id"]: row for row in reader}


@pytest.mark.parametrize("as_state", [True, False], ids=["state", "bundle"])
def test_json_retains_originals_and_complete_events_separately_from_effective_projection(as_state):
    original = correction_state()
    state = moved(original)
    before = state.model_dump(mode="json")
    payload = json.loads(export_json(state if as_state else state.bundle))
    bundle = payload["bundle"] if as_state else payload
    assert (
        bundle["junit_evidence_imports"]
        == original.bundle.model_dump(mode="json")["junit_evidence_imports"]
    )
    assert bundle["effective_junit_mappings"][IMPORT_ID] == [
        item.model_dump(mode="json") for item in effective_junit_mappings(state.bundle, IMPORT_ID)
    ]
    events = junit_mapping_correction_events(state.bundle, IMPORT_ID)
    assert bundle["junit_import_events"] == [events[0].model_dump(mode="json")]
    event = bundle["junit_import_events"][0]
    assert event["schema_version"] == "junit-mapping-correction-v1"
    assert event["action"] == "mapping_corrected"
    assert event["previous_correction_event_id"] is None
    assert event["reviewer"] == REVIEWER and event["reason"] == REASON
    assert event["criterion_mappings"] == bundle["effective_junit_mappings"][IMPORT_ID]
    assert bundle["active_junit_import_ids"] == [IMPORT_ID]
    assert bundle["gate"] == original.bundle.model_dump(mode="json")["gate"]
    assert state.model_dump(mode="json") == before


@pytest.mark.parametrize("exporter", [export_markdown, export_html], ids=["markdown", "html"])
def test_readable_reports_label_original_effective_mapping_and_full_inert_audit(exporter):
    state = moved(correction_state())
    event = state.bundle.junit_import_events[-1]
    report = exporter(state)
    decoded = (
        re.sub(r"\\([" + re.escape(string.punctuation) + r"])", r"\1", report)
        if exporter is export_markdown
        else report
    )
    displayed = html.unescape(decoded)
    assert "original" in report.lower() and "effective" in report.lower()
    assert "correction" in report.lower()
    for value in (
        IMPORT_ID,
        event.event_id,
        event.previous_mapping_sha256,
        event.artifact_sha256,
        event.review_id,
        event.repository,
        event.head_sha,
        event.confirmed_criteria_sha256,
        event.criteria_source_provenance.source_revision,
        event.criteria_source_provenance.source_text_sha256,
        event.criteria_source_provenance.confirmed_by,
        event.schema_version,
        event.action,
        event.criteria_source_provenance.source_uri,
        event.criteria_source_provenance.normalized_criteria_sha256,
        "2026-11-01T12:00:00",
        "externally_supplied",
        "non_gating",
        "not_executed_by_scopeproof",
        "2026-11-01T13:14:15",
        "AC-01",
        "AC-02",
        "AC-03",
        CASE1,
        CASE2,
        CASE3,
        REVIEWER,
        REASON,
    ):
        assert value in displayed
    assert "<script>" not in report and "<img src=x" not in report
    assert '<a href="javascript:' not in report and '<a href="https://evil.test/' not in report
    if exporter is export_markdown:
        assert "[actor](" not in report and "[details](" not in report
    assert "non-gating" in report


def test_csv_current_cases_move_but_original_and_intermediate_groups_keep_complete_audit():
    original = correction_state()
    first = moved(original)
    state = correct(first, mappings(("AC-01", [CASE1]), ("AC-02", [CASE2, CASE3])))
    old_columns, old_rows = csv_rows(original)
    columns, rows = csv_rows(state)
    assert columns == old_columns
    assert json.loads(rows["AC-03"]["junit_mapped_cases"]) == []
    assert json.loads(rows["AC-03"]["junit_artifact_digests"]) == []
    assert [item["test_case_id"] for item in json.loads(rows["AC-01"]["junit_mapped_cases"])] == [
        CASE1,
    ]
    assert [item["test_case_id"] for item in json.loads(rows["AC-02"]["junit_mapped_cases"])] == [
        CASE2,
        CASE3,
    ]
    expected = [item.model_dump(mode="json") for item in state.bundle.junit_import_events]
    for criterion in ("AC-01", "AC-02", "AC-03"):
        audit = json.loads(rows[criterion]["junit_import_audit"])
        assert len(audit) == 1 and audit[0]["import_id"] == IMPORT_ID
        assert audit[0]["mapping_correction_events"] == expected
        assert audit[0]["status"] == "active"
        for name in columns:
            if not name.startswith("junit_"):
                assert rows[criterion][name] == old_rows[criterion][name]


def test_uncorrected_import_keeps_its_csv_columns_and_values_when_another_import_is_corrected():
    state = correction_state()
    second = build_junit_evidence_import(
        state,
        JUNIT_AUDIT_XML.replace(b"audit suite", b"unmodified suite"),
        [JUnitMappingSelection(scope_id=CASE1, criterion_id="AC-03")],
        importer="CONSTRUCTED uncorrected actor",
        import_id="constructed-uncorrected-import",
        imported_at=state.review.created_at,
    )
    original = append_junit_evidence_import(state, second)
    current = correct(original, mappings(("AC-02", [CASE1, CASE2, CASE3])))
    columns, before = csv_rows(original)
    after_columns, after = csv_rows(current)
    assert columns == after_columns
    assert before["AC-03"] == after["AC-03"]


@pytest.mark.parametrize("exporter", [export_json, export_markdown, export_html, export_csv])
def test_all_exports_revalidate_forged_correction_ownership(exporter):
    state = moved(correction_state())
    state.bundle.junit_import_events[0] = state.bundle.junit_import_events[0].model_copy(
        update={"review_id": "constructed-foreign-review"},
    )
    with pytest.raises(ValueError):
        exporter(state)
