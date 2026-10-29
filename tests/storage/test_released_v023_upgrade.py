"""Reopen native published-v0.2.3 bytes, never a downgraded current record.

Every actor, runtime record and acceptance below is constructed automation for
persistence coverage. It supplies no actual target-runtime or human-use evidence.
"""

import csv
import io
import json
from hashlib import sha256
from pathlib import Path

from pydantic import JsonValue

from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.schemas.models import (
    GateVerdict,
    PullRequestSnapshot,
    RepositoryVisibility,
    ReviewState,
)
from scopeproof_core.storage.json_store import JsonReviewStore

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/released_v023_upgrade/native_v4.json"
FIXTURE_SHA256 = "5e933ed5e306a43098954aa2e461efd178b1f0de32dee6584e7e60ff5256df6f"
REVIEW_ID = "constructed-v023-upgrade"
BOUNDARY = "Constructed automation only; no actual target runtime or human use."
DERIVED_BUNDLE_FIELDS = {
    "gate",
    "candidate_evidence_proves_correctness",
    "runtime_verification_state",
    "reviewer_decision_state",
}


def _native_store(tmp_path: Path) -> tuple[JsonReviewStore, Path, bytes]:
    original = FIXTURE.read_bytes()
    assert sha256(original).hexdigest() == FIXTURE_SHA256
    payload = json.loads(original)
    assert payload["record_version"] == 4
    assert payload["state"]["bundle"]["gate"]["verdict"] == "ready"
    assert payload["state"]["analysis_history"][0]["gate"]["verdict"] == "ready"
    directory = tmp_path / "reviews"
    directory.mkdir()
    copied_record = directory / f"{REVIEW_ID}.json"
    copied_record.write_bytes(original)
    return JsonReviewStore(directory), copied_record, original


def _assert_original_facts(original: JsonValue, reopened: JsonValue) -> None:
    """Original facts must survive; new schema defaults are checked separately."""
    if isinstance(original, dict):
        assert isinstance(reopened, dict)
        # Only a bundle's policy/presentation values may be recomputed on load.
        ignored = (
            DERIVED_BUNDLE_FIELDS if {"gate", "findings", "review"} <= original.keys() else set()
        )
        for key, value in original.items():
            if key not in ignored:
                assert key in reopened, key
                _assert_original_facts(value, reopened[key])
    elif isinstance(original, list):
        assert isinstance(reopened, list)
        assert len(reopened) == len(original)
        for old_item, new_item in zip(original, reopened, strict=True):
            _assert_original_facts(old_item, new_item)
    else:
        assert reopened == original


def _assert_conservative_upgrade(state: ReviewState) -> None:
    assert state.bundle is not None
    assert state.criteria_revision.number == 2
    assert [bundle.criteria_revision_number for bundle in state.analysis_history] == [1]
    assert len(state.resolution_events) == 10
    assert {event.reviewer for event in state.resolution_events} == {BOUNDARY}
    assert state.review.criteria_source_provenance is not None
    assert state.review.criteria_source_provenance.confirmed_by == BOUNDARY
    assert state.criteria_revision.confirmed is True
    assert state.review.final_acceptance is True  # Retained fact, not a new approval.
    bundles = [*state.analysis_history, state.bundle]
    assert [item.runtime_evidence_id for bundle in bundles for item in bundle.runtime_evidence] == [
        "constructed-historical-runtime",
        "constructed-active-runtime",
    ]
    assert [
        event.runtime_evidence_id
        for event in state.resolution_events
        if event.runtime_evidence_id is not None
    ] == ["constructed-historical-runtime", "constructed-active-runtime"]
    for review in [state.review, *(bundle.review for bundle in bundles)]:
        assert review.tool_version == "0.2.3"
        assert review.ruleset_version == "1.0.0"
        assert review.repository_visibility is RepositoryVisibility.UNVERIFIED
        assert review.analysis_source_identity is None
        assert review.changed_file_inventory is None
    for bundle in bundles:
        assert bundle.review.final_acceptance is True
        assert bundle.file_scope_decisions == []
        assert bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
        assert "changed_file_inventory_unknown" in bundle.gate.reason_codes
        assert bundle.retrieval_diagnostics
        for diagnostic in bundle.retrieval_diagnostics:
            assert diagnostic.eligible_candidate_count is None
            assert diagnostic.candidate_limit is None
            assert diagnostic.omitted_candidate_count is None
        manual_resolution = bundle.resolutions[0]
        assert (
            manual_resolution.runtime_evidence_id == bundle.runtime_evidence[0].runtime_evidence_id
        )


def test_native_old_writer_load_preserves_facts_without_inventing_ready(tmp_path: Path) -> None:
    """Catch lost native-v4 links/history or an inferred inventory/Ready verdict."""
    store, copied_record, original = _native_store(tmp_path)
    provenance = json.loads(FIXTURE.with_name("provenance.json").read_text(encoding="utf-8"))
    generation = provenance["generation"]
    reader_result = provenance["published_reader_result"]
    assert generation["package_version"] == generation["core_version"] == "0.2.3"
    assert generation["record_version"] == 4
    assert generation["record_sha256"] == reader_result["input_sha256"] == FIXTURE_SHA256
    assert (
        generation["recipe_sha256"]
        == sha256(FIXTURE.with_name("generate_record.py").read_bytes()).hexdigest()
    )
    assert generation["actual_target_runtime"] is False
    assert generation["human_use"] is False
    assert generation["boundary"] == reader_result["boundary"] == BOUNDARY
    assert reader_result["package_version"] == reader_result["core_version"] == "0.2.4"
    assert reader_result["input_record_version"] == 4
    assert reader_result["output_record_version"] == 5
    reopened = store.load(REVIEW_ID)

    _assert_original_facts(json.loads(original)["state"], reopened.model_dump(mode="json"))
    _assert_conservative_upgrade(reopened)
    assert store.load(REVIEW_ID) == reopened
    assert copied_record.read_bytes() == original
    assert FIXTURE.read_bytes() == original


def test_native_old_writer_resave_preserves_history_and_original_bytes(tmp_path: Path) -> None:
    """Catch a v5 save that discards migrated facts, promotes scope or rewrites history."""
    store, copied_record, original = _native_store(tmp_path)
    reopened = store.load(REVIEW_ID)
    before_save = reopened.model_dump(mode="json")

    assert store.save(reopened) == copied_record
    resaved = json.loads(copied_record.read_bytes())
    assert resaved["record_version"] == 5
    assert resaved["state"] == before_save
    assert store.load(REVIEW_ID).model_dump(mode="json") == before_save
    _assert_conservative_upgrade(store.load(REVIEW_ID))
    assert FIXTURE.read_bytes() == original


def test_native_old_writer_exports_keep_preserved_decisions_and_cautious_gate(
    tmp_path: Path,
) -> None:
    """Catch exports that lose native history or present historical acceptance as Ready."""
    store, copied_record, original = _native_store(tmp_path)
    reopened = store.load(REVIEW_ID)
    exported = ReviewState.model_validate_json(export_json(reopened))

    assert exported == reopened
    _assert_conservative_upgrade(exported)
    csv_rows = list(csv.DictReader(io.StringIO(export_csv(reopened))))
    assert len(csv_rows) == 4
    assert {row["verdict"] for row in csv_rows} == {"needs_review"}
    assert {row["changed_file_inventory_state"] for row in csv_rows} == {"unknown legacy inventory"}
    for rendered in (export_markdown(reopened), export_html(reopened)):
        assert "unknown legacy inventory" in rendered
        assert BOUNDARY in rendered
    assert copied_record.read_bytes() == original


def test_native_old_writer_head_detection_does_not_mutate_saved_identity(tmp_path: Path) -> None:
    """Catch a comparison that updates saved identity or misses a changed snapshot head."""
    store, copied_record, original = _native_store(tmp_path)
    reopened = store.load(REVIEW_ID)
    before = reopened.model_dump(mode="json")
    snapshot_payload = load_demo_snapshot().model_dump(mode="json")
    snapshot_payload["head_sha"] = reopened.review.head_sha
    same_head = PullRequestSnapshot.model_validate(snapshot_payload)
    snapshot_payload["head_sha"] = "constructed-changed-head"
    changed_head = PullRequestSnapshot.model_validate(snapshot_payload)

    same = store.detect_head_change(reopened, same_head)
    changed = store.detect_head_change(reopened, changed_head)

    assert same.changed is False
    assert same.saved_head_sha == same.current_head_sha == "head-demo-002"
    assert changed.changed is True
    assert changed.saved_head_sha == "head-demo-002"
    assert changed.current_head_sha == "constructed-changed-head"
    assert reopened.model_dump(mode="json") == before
    assert copied_record.read_bytes() == original
