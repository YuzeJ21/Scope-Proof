"""Reopen native public-v0.2.6 records without fabricating runtime or human evidence.

These immutable release-writer records contain constructed actors and observations.
They establish persistence compatibility only, not actual target-runtime or human use.
"""

import csv
import html
import io
import json
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.junit_audit import (
    effective_junit_mappings,
    junit_import_status,
)
from scopeproof_core.reviews.lifecycle import ResolutionEventStatus, resolution_event_statuses
from scopeproof_core.reviews.reference_audit import reference_status
from scopeproof_core.schemas.models import (
    GateVerdict,
    HumanDecision,
    ReviewBundle,
    ReviewInputOrigin,
    ReviewState,
)
from scopeproof_core.storage import transfer
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.fixtures.released_v026_upgrade.provenance_schema import (
    BOUNDARY,
    CORE_SHA256,
    ArtifactDigest,
    RecordProvenance,
    ReleasedWriterProvenance,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/released_v026_upgrade"
CASES = ("active-rich", "pending-rich")
ORIGINAL_MAPPINGS = [
    {"criterion_id": "AC-01", "test_case_ids": ["suite-0001-case-0001"]},
    {"criterion_id": "AC-02", "test_case_ids": ["suite-0001-case-0002"]},
]
CORRECTED_MAPPINGS = [
    {"criterion_id": "AC-01", "test_case_ids": ["suite-0001-case-0002"]},
    {"criterion_id": "AC-02", "test_case_ids": ["suite-0001-case-0001"]},
]
ORIGINAL_MAPPING_SHA256 = "985c83547c73261e143f477e44093e0b85f5064b1a86049fd195fa23d7af7dca"


def _provenance() -> ReleasedWriterProvenance:
    return ReleasedWriterProvenance.model_validate_json((FIXTURES / "provenance.json").read_bytes())


def _assert_digest(path: Path, digest: ArtifactDigest) -> bytes:
    raw = path.read_bytes()
    assert len(raw) == digest.bytes
    assert sha256(raw).hexdigest() == digest.sha256
    return raw


def _native_store(
    tmp_path: Path, case: str
) -> tuple[JsonReviewStore, Path, bytes, RecordProvenance]:
    record = next(record for record in _provenance().records if record.case == case)
    original = _assert_digest(FIXTURES / record.record.name, record.record)
    payload = json.loads(original)
    assert payload["record_version"] == 9
    assert payload["state"]["review"]["review_id"] == record.review_id
    store = JsonReviewStore(tmp_path / "source")
    store.directory.mkdir()
    copied = store.directory / f"{record.review_id}.json"
    copied.write_bytes(original)
    return store, copied, original, record


def _bundles(state: ReviewState) -> list[ReviewBundle]:
    return [*state.analysis_history, *([state.bundle] if state.bundle is not None else [])]


def _assert_native_semantics(state: ReviewState, record: RecordProvenance) -> None:
    """Named lifecycle and audit outcomes survive, beyond merely retaining counts."""
    pending = record.case == "pending-rich"
    assert state.review.review_id == record.review_id
    assert state.criteria_revision.number == (3 if pending else 2)
    assert state.criteria_revision.confirmed is (not pending)
    assert state.review.criteria_confirmed is (not pending)
    assert state.review.final_acceptance is False
    assert [bundle.criteria_revision_number for bundle in state.analysis_history] == (
        [1, 2] if pending else [1]
    )
    assert [bundle.gate.verdict for bundle in state.analysis_history] == (
        [GateVerdict.READY, GateVerdict.BLOCKED] if pending else [GateVerdict.READY]
    )
    if pending:
        assert state.bundle is None
        assert state.review.criteria_source_provenance is None
        assert state.criteria_revision.source_provenance is None
        assert state.criteria_revision.confirmed_at is None
    else:
        assert state.bundle is not None
        assert state.bundle.gate.verdict is GateVerdict.BLOCKED
        assert state.review.criteria_source_provenance is not None

    bundles = _bundles(state)
    assert len(bundles) == 2
    historical, later = bundles
    assert [bundle.criteria_revision_number for bundle in bundles] == [1, 2]
    assert historical.review.final_acceptance is True  # A retained constructed assertion.
    assert later.review.final_acceptance is False
    assert historical.gate.verdict is GateVerdict.READY
    assert later.gate.verdict is GateVerdict.BLOCKED
    assert later.gate.blocking_criteria == ["AC-03"]
    for review in [state.review, *(bundle.review for bundle in bundles)]:
        assert review.tool_version == record.producer_tool_version == "0.2.6"
        assert review.ruleset_version == record.producer_ruleset_version == "2.0.0"
        assert review.analysis_source_identity is not None
        assert review.analysis_source_identity.sha256 == record.producer_core_sha256 == CORE_SHA256
        assert review.input_origin is ReviewInputOrigin.CONSTRUCTED_DEMO
        assert review.changed_file_inventory is not None

    events = state.resolution_events
    assert len(events) == record.counts.resolution_events == 9
    assert [event.event_id for event in events] == record.resolution_event_ids
    assert [event.event_id for event in events] == [
        "constructed-historical-manual",
        "constructed-historical-AC-02",
        "constructed-historical-AC-03",
        "constructed-historical-AC-04",
        "constructed-historical-acceptance",
        "constructed-active-manual",
        "constructed-active-AC-02",
        "constructed-active-AC-03",
        "constructed-active-AC-04",
    ]
    assert [event.criteria_revision_number for event in events] == [1] * 5 + [2] * 4
    assert resolution_event_statuses(events, state.criteria_revision.number) == (
        [ResolutionEventStatus.PRIOR_REVISION] * 9
        if pending
        else [ResolutionEventStatus.PRIOR_REVISION] * 5 + [ResolutionEventStatus.CURRENT] * 4
    )
    assert events[4].final_acceptance is True
    assert events[7].decision is HumanDecision.CHANGE_REQUIRED
    assert (
        [item.runtime_evidence_id for bundle in bundles for item in bundle.runtime_evidence]
        == (record.runtime_evidence_ids)
        == ["constructed-historical-runtime", "constructed-active-runtime"]
    )
    assert (
        sum(len(bundle.runtime_evidence) for bundle in bundles)
        == record.counts.runtime_records
        == 2
    )
    assert (
        sum(len(bundle.reviewer_selected_references) for bundle in bundles)
        == (record.counts.selected_references)
        == 4
    )
    assert (
        sum(len(bundle.selected_reference_events) for bundle in bundles)
        == (record.counts.selected_reference_events)
        == 4
    )
    assert (
        sum(len(bundle.junit_evidence_imports) for bundle in bundles)
        == (record.counts.junit_imports)
        == 2
    )
    assert (
        sum(len(bundle.junit_import_events) for bundle in bundles)
        == record.counts.junit_events
        == 4
    )
    assert (
        sum(len(bundle.file_scope_decisions) for bundle in bundles)
        == (record.counts.scope_decisions)
        == 2
    )

    for name, bundle in zip(("historical", "active"), bundles, strict=True):
        revision = bundle.criteria_revision_number
        assert bundle.candidate_evidence_proves_correctness is False
        assert bundle.research_context is None or bundle.research_context.stage1_credit is False
        assert bundle.review.criteria_source_provenance is not None
        assert BOUNDARY in bundle.review.criteria_source_provenance.confirmed_by
        (runtime,) = bundle.runtime_evidence
        manual = next(
            resolution for resolution in bundle.resolutions if resolution.criterion_id == "AC-01"
        )
        event = next(event for event in events if event.event_id == f"constructed-{name}-manual")
        assert manual.decision is event.decision is HumanDecision.MANUALLY_VERIFIED
        assert (
            manual.runtime_evidence_id == event.runtime_evidence_id == runtime.runtime_evidence_id
        )
        assert runtime.criterion_id == manual.criterion_id == "AC-01"
        assert (runtime.repository, runtime.pr_number, runtime.head_sha) == (
            bundle.review.repository,
            bundle.review.pr_number,
            bundle.review.head_sha,
        )
        assert BOUNDARY in runtime.reviewer
        for value in (runtime.scenario, runtime.environment, runtime.result, *runtime.limitations):
            assert BOUNDARY in value

        original, replacement = bundle.reviewer_selected_references
        correction, withdrawal = bundle.selected_reference_events
        assert correction.action == "corrected"
        assert correction.reference_id == original.reference_id
        assert correction.replacement_reference_id == replacement.reference_id
        assert withdrawal.action == "withdrawn"
        assert withdrawal.reference_id == replacement.reference_id
        assert withdrawal.replacement_reference_id is None
        assert original.criterion_id == replacement.criterion_id == "AC-01"
        assert (original.file_path, original.line_number) != (
            replacement.file_path,
            replacement.line_number,
        )
        assert bundle.active_reviewer_selected_reference_ids == []
        assert [
            reference_status(
                bundle.reviewer_selected_references,
                bundle.selected_reference_events,
                reference.reference_id,
            )
            for reference in (original, replacement)
        ] == ["corrected", "withdrawn"]
        for reference in (original, replacement):
            assert reference.criteria_revision_number == revision
            assert reference.criteria_source_provenance == bundle.review.criteria_source_provenance
            assert BOUNDARY in reference.reviewer and BOUNDARY in reference.rationale
        for audit in (correction, withdrawal):
            assert BOUNDARY in audit.reviewer and BOUNDARY in audit.reason

        (imported,) = bundle.junit_evidence_imports
        mapping_correction, import_withdrawal = bundle.junit_import_events
        assert imported.import_id == f"constructed-{name}-junit"
        assert [mapping.model_dump(mode="json") for mapping in imported.criterion_mappings] == (
            ORIGINAL_MAPPINGS
        )
        assert mapping_correction.action == "mapping_corrected"
        assert mapping_correction.previous_correction_event_id is None
        assert mapping_correction.previous_mapping_sha256 == ORIGINAL_MAPPING_SHA256
        assert [
            mapping.model_dump(mode="json") for mapping in mapping_correction.criterion_mappings
        ] == CORRECTED_MAPPINGS
        assert import_withdrawal.action == "withdrawn"
        for audit in (mapping_correction, import_withdrawal):
            assert audit.import_id == imported.import_id
            assert audit.artifact_sha256 == imported.artifact_sha256
            assert audit.criteria_revision_number == revision
            assert audit.criteria_source_provenance == imported.criteria_source_provenance
            assert BOUNDARY in audit.reviewer and BOUNDARY in audit.reason
            assert audit.evidence_boundary.gate_effect == "non_gating"
            assert audit.evidence_boundary.execution == "not_executed_by_scopeproof"
            assert audit.evidence_boundary.importer_identity == "asserted_not_authenticated"
        assert (
            imported.totals.total == 2 and imported.totals.passed == imported.totals.failures == 1
        )
        assert [case.status.value for case in imported.test_cases] == ["passed", "failure"]
        assert [
            mapping.model_dump(mode="json")
            for mapping in effective_junit_mappings(bundle, imported.import_id)
        ] == (CORRECTED_MAPPINGS)
        assert bundle.active_junit_import_ids == []
        assert junit_import_status(bundle, imported.import_id) == "withdrawn"
        assert BOUNDARY in imported.imported_by and BOUNDARY in imported.limitations
        assert imported.evidence_boundary.gate_effect == "non_gating"
        assert imported.evidence_boundary.execution == "not_executed_by_scopeproof"

        (scope,) = bundle.file_scope_decisions
        assert scope.event_id == f"constructed-{name}-scope"
        assert scope.path == "notes/constructed-unrelated.txt"
        assert scope.disposition == "outside_confirmed_criteria"
        assert scope.criterion_id is None
        assert scope.criteria_revision_number == revision
        assert scope.head_sha == bundle.review.head_sha
        assert BOUNDARY in scope.reviewer and BOUNDARY in scope.note
    assert all(BOUNDARY in event.reviewer and BOUNDARY in event.comment for event in events)


def test_native_public_v026_provenance_matches_offline_corpus() -> None:
    """The public writer's records and provenance are permanent offline inputs."""
    provenance = _provenance()
    assert [record.case for record in provenance.records] == list(CASES)
    assert provenance.package_version == provenance.core_version == "0.2.6"
    assert provenance.installed_core_source_sha256 == CORE_SHA256
    assert (
        provenance.actual_target_runtime
        is provenance.human_use
        is provenance.network_access
        is False
    )
    assert provenance.native_round_trip_exact is provenance.load_preserved_original_bytes is True
    for artifact in (provenance.recipe, provenance.provenance_schema):
        _assert_digest(FIXTURES / artifact.name, artifact)
    for artifact in (provenance.packaged_fixture, provenance.packaged_labels):
        _assert_digest(FIXTURES.parents[2] / artifact.name, artifact)
    for record in provenance.records:
        _assert_digest(FIXTURES / record.record.name, record.record)


def test_hash_bound_corpus_inputs_survive_windows_style_checkout(tmp_path: Path) -> None:
    """Git's automatic CRLF conversion must not alter any recorded artifact digest."""
    provenance = _provenance()
    root = FIXTURES.parents[2]
    artifacts = [
        *(
            (FIXTURES / item.name, item)
            for item in (provenance.recipe, provenance.provenance_schema)
        ),
        *((FIXTURES / item.record.name, item.record) for item in provenance.records),
        *(
            (root / item.name, item)
            for item in (provenance.packaged_fixture, provenance.packaged_labels)
        ),
    ]
    checkout = tmp_path / "crlf-checkout"
    checkout.mkdir()
    (checkout / ".gitattributes").write_bytes((root / ".gitattributes").read_bytes())
    for path, _ in artifacts:
        destination = checkout / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=checkout, check=True, capture_output=True)

    git("init", "-q")
    git("config", "core.autocrlf", "true")
    git("config", "core.safecrlf", "false")
    git("add", ".")
    for path, _ in artifacts:
        (checkout / path.relative_to(root)).unlink()
    git("checkout-index", "--all", "--force")
    for path, digest in artifacts:
        _assert_digest(checkout / path.relative_to(root), digest)


@pytest.mark.parametrize("case", CASES)
def test_native_public_v026_load_retains_every_state_field(tmp_path: Path, case: str) -> None:
    """Current validation may not silently rewrite this compatible native v9 state."""
    store, copied, original, record = _native_store(tmp_path, case)
    expected = json.loads(original)["state"]
    reopened = store.load(record.review_id)

    assert reopened.model_dump(mode="json") == expected
    _assert_native_semantics(reopened, record)
    assert store.load(record.review_id).model_dump(mode="json") == expected
    assert copied.read_bytes() == original
    assert (FIXTURES / record.record.name).read_bytes() == original


@pytest.mark.parametrize("case", CASES)
def test_native_public_v026_resave_keeps_complete_state(tmp_path: Path, case: str) -> None:
    """Only a temporary copy is resaved; native originals remain release-writer bytes."""
    store, copied, original, record = _native_store(tmp_path, case)
    expected = json.loads(original)["state"]
    reopened = store.load(record.review_id)

    assert store.save(reopened) == copied
    saved = json.loads(copied.read_bytes())
    assert saved["record_version"] == 9
    assert saved["state"] == expected
    again = store.load(record.review_id)
    assert again.model_dump(mode="json") == expected
    _assert_native_semantics(again, record)
    assert (FIXTURES / record.record.name).read_bytes() == original


@pytest.mark.parametrize(
    "location,value",
    [
        (("human_use",), 0),
        (("actual_target_runtime",), True),
        (("package_version",), "0.2.7.dev0"),
        (("records", 0, "producer_tool_version"), "0.2.7.dev0"),
        (("records", 0, "record_version"), 8),
        (("records", 0, "counts", "runtime_records"), 2.0),
        (("records", 1, "criteria_confirmed"), True),
        (("records", 1, "has_active_analysis"), True),
    ],
)
def test_native_public_v026_provenance_rejects_credit_or_producer_drift(
    location: tuple[str | int, ...], value: object
) -> None:
    payload = json.loads((FIXTURES / "provenance.json").read_bytes())
    target = payload
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value

    with pytest.raises(ValidationError):
        ReleasedWriterProvenance.model_validate_json(json.dumps(payload))


def _assert_transfer_preview(
    preview: transfer.ReviewTransferPreview,
    state: ReviewState,
    original: bytes,
    record: RecordProvenance,
) -> None:
    receipt = preview.receipt
    assert receipt.review_id == record.review_id
    assert receipt.record_sha256 == record.record.sha256 == sha256(original).hexdigest()
    assert receipt.record_bytes == record.record.bytes == len(original)
    assert receipt.record_version == 9
    assert receipt.saved_at == json.loads(original)["saved_at"]
    assert receipt.head_sha == state.review.head_sha
    assert receipt.analysis_history_count == record.counts.historical_analyses
    assert "no actor authentication, renewed verification" in receipt.boundary_note
    assert "independent-use evidence" in receipt.boundary_note
    assert preview.producer_tool_version == "0.2.6"
    assert preview.producer_ruleset_version == "2.0.0"
    assert preview.producer_source_identity == state.review.analysis_source_identity
    assert preview.producer_source_identity is not None
    assert preview.producer_source_identity.sha256 == CORE_SHA256
    assert preview.criteria_source == state.review.criteria_source_provenance
    assert preview.input_origin is ReviewInputOrigin.CONSTRUCTED_DEMO
    assert preview.criteria_revision_number == record.criteria_revision_number
    assert preview.criteria_confirmed is record.criteria_confirmed
    assert preview.has_active_analysis is record.has_active_analysis
    assert preview.resolution_event_count == 9


@pytest.mark.parametrize("case", CASES)
def test_native_public_v026_transfer_keeps_bytes_and_original_producer(
    tmp_path: Path, case: str
) -> None:
    """Inspect, download and both import APIs preserve native bytes and pending authority."""
    source, copied, original, record = _native_store(tmp_path, case)
    expected = json.loads(original)["state"]
    state = source.load(record.review_id)
    preview = transfer.inspect_review_bytes(copied.read_bytes())
    _assert_transfer_preview(preview, state, original, record)
    downloaded, download_preview = transfer.read_review_transfer(
        source, record.review_id, expected_sha256=record.record.sha256
    )
    assert downloaded == original
    assert download_preview == preview

    portable = tmp_path / "portable.json"
    exported = transfer.export_review(source, record.review_id, portable)
    assert portable.read_bytes() == original
    for index, use_bytes in enumerate((False, True)):
        recipient = JsonReviewStore(tmp_path / f"recipient-{index}")
        imported = (
            transfer.import_review_bytes(
                recipient, downloaded, expected_sha256=preview.receipt.record_sha256
            )
            if use_bytes
            else transfer.import_review(recipient, portable)
        )
        destination = recipient.directory / copied.name
        assert destination.read_bytes() == original
        reopened = recipient.load(record.review_id)
        assert reopened.model_dump(mode="json") == expected
        _assert_native_semantics(reopened, record)
        assert transfer.inspect_review_bytes(destination.read_bytes()) == preview
        for receipt in (exported, imported):
            assert receipt.model_dump(exclude={"action"}) == preview.receipt.model_dump(
                exclude={"action"}
            )
        with pytest.raises(FileExistsError):
            transfer.import_review(recipient, portable)
        with pytest.raises(FileExistsError):
            transfer.import_review_bytes(
                recipient, downloaded, expected_sha256=preview.receipt.record_sha256
            )
        assert destination.read_bytes() == original

    with pytest.raises(FileExistsError):
        transfer.export_review(source, record.review_id, portable)
    with pytest.raises(FileExistsError):
        transfer.export_review(source, record.review_id, copied)
    assert portable.read_bytes() == copied.read_bytes() == original
    assert source.load(record.review_id).model_dump(mode="json") == expected
    assert (FIXTURES / record.record.name).read_bytes() == original


def _assert_readable_analysis_exports(
    value: ReviewState | ReviewBundle, bundle: ReviewBundle
) -> None:
    """Assertions concern the explicitly selected analysis, not pending lifecycle authority."""
    rows = list(csv.DictReader(io.StringIO(export_csv(value))))
    by_id = {row["criterion_id"]: row for row in rows}
    assert len(rows) == len(bundle.criteria) == 4
    assert set(by_id) == {criterion.criterion_id for criterion in bundle.criteria}
    assert {row["verdict"] for row in rows} == {bundle.gate.verdict.value}
    assert {row["tool_version"] for row in rows} == {"0.2.6"}
    assert {row["ruleset_version"] for row in rows} == {"2.0.0"}
    assert {row["analysis_core_source"] for row in rows} == {f"core-python-source-v1:{CORE_SHA256}"}
    for finding in bundle.findings:
        row = by_id[finding.criterion_id]
        assert row["status"] == finding.status.value
        assert json.loads(row["missing_evidence"]) == finding.missing_evidence
        assert row["concern"] == finding.reason
        assert row["candidate_evidence_proves_correctness"] == "False"
        assert json.loads(row["gate_reason_codes"]) == bundle.gate.reason_codes
        assert json.loads(row["gate_blocking_criteria"]) == bundle.gate.blocking_criteria
        assert json.loads(row["file_scope_decisions"]) == [
            decision.model_dump(mode="json") for decision in bundle.file_scope_decisions
        ]
        assert BOUNDARY in row["criteria_confirmed_by"]
    manual_row = by_id["AC-01"]
    (runtime,) = bundle.runtime_evidence
    assert manual_row["human_decision"] == "manually_verified"
    assert manual_row["manual_runtime_evidence_id"] == runtime.runtime_evidence_id
    assert json.loads(manual_row["runtime_result"]) == [runtime.result]
    assert json.loads(manual_row["active_reviewer_selected_reference_ids"]) == []
    refs = bundle.reviewer_selected_references
    assert json.loads(manual_row["selected_reference_statuses"]) == {
        refs[0].reference_id: "corrected",
        refs[1].reference_id: "withdrawn",
    }
    assert json.loads(manual_row["reviewer_selected_references"]) == [
        reference.model_dump(mode="json") for reference in refs
    ]
    assert json.loads(manual_row["selected_reference_events"]) == [
        event.model_dump(mode="json") for event in bundle.selected_reference_events
    ]
    (audit,) = json.loads(manual_row["junit_import_audit"])
    assert audit["status"] == "withdrawn"
    assert audit["original_mappings"] == ORIGINAL_MAPPINGS
    assert audit["effective_mappings"] == CORRECTED_MAPPINGS
    assert audit["mapping_correction_events"] == [
        bundle.junit_import_events[0].model_dump(mode="json")
    ]
    assert audit["withdrawal_event"] == bundle.junit_import_events[1].model_dump(mode="json")

    for rendered in (export_markdown(value), export_html(value)):
        # These native fixtures contain plain constructed text, not hostile-markup probes.
        text = html.unescape(rendered).replace(r"\-", "-")
        assert "0.2.6" in text and "2.0.0" in text and CORE_SHA256 in text
        assert BOUNDARY in text
        assert bundle.review.review_id in text
        assert bundle.review.head_sha in text
        expected_status = (
            "Action required" if bundle.gate.verdict is GateVerdict.BLOCKED else "Review complete"
        )
        assert expected_status in text
        if isinstance(value, ReviewBundle):
            assert "Full resolution history is unavailable for this analysis-only report." in text
        for reason in bundle.gate.reason_codes:
            assert reason in text
        for item in (*refs, *bundle.selected_reference_events, *bundle.junit_import_events):
            assert item.reviewer in text
        for reference in refs:
            assert reference.reference_id in text
        for event in (*bundle.selected_reference_events, *bundle.junit_import_events):
            assert event.event_id in text
        assert runtime.runtime_evidence_id in text
        assert "<script" not in rendered.lower()


def test_native_public_v026_active_exports_keep_full_state_and_analysis(tmp_path: Path) -> None:
    source, copied, original, record = _native_store(tmp_path, "active-rich")
    reopened = source.load(record.review_id)
    expected = json.loads(original)["state"]

    assert json.loads(export_json(reopened)) == expected
    exported = ReviewState.model_validate_json(export_json(reopened))
    _assert_native_semantics(exported, record)
    assert reopened.bundle is not None
    _assert_readable_analysis_exports(reopened, reopened.bundle)
    assert reopened.model_dump(mode="json") == expected
    assert copied.read_bytes() == original
    assert (FIXTURES / record.record.name).read_bytes() == original


def test_native_public_v026_pending_exports_require_explicit_retained_analysis(
    tmp_path: Path,
) -> None:
    """Pending current-state export is denied; retained analysis reports are analysis-only."""
    source, copied, original, record = _native_store(tmp_path, "pending-rich")
    reopened = source.load(record.review_id)
    expected = json.loads(original)["state"]

    for exporter in (export_json, export_markdown, export_csv, export_html):
        with pytest.raises(ValueError, match=r"criteria source provenance|confirmed analysis"):
            exporter(reopened)
    # Select genuine retained bundles directly; never manufacture a confirmed active state.
    for historical in reopened.analysis_history:
        assert json.loads(export_json(historical)) == historical.model_dump(mode="json")
        _assert_readable_analysis_exports(historical, historical)
    assert reopened.model_dump(mode="json") == expected
    _assert_native_semantics(reopened, record)
    assert copied.read_bytes() == original
    assert (FIXTURES / record.record.name).read_bytes() == original
