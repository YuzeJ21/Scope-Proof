"""CONSTRUCTED byte-preview handoff boundaries, without actor authentication."""

from hashlib import sha256

import pytest

from scopeproof_core.storage import transfer
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.historical_analysis_fixture import historical_analysis_state


@pytest.fixture
def record(tmp_path):
    store = JsonReviewStore(tmp_path / "source")
    state = historical_analysis_state()
    path = store.save(state)
    raw = path.read_bytes().replace(b"\n", b"\r\n")
    path.write_bytes(raw)
    return store, state, raw


def test_inspection_preserves_identity_and_pending_history(record):
    _, state, raw = record
    preview = transfer.inspect_review_bytes(raw)
    assert preview.receipt.action == "inspected"
    assert preview.receipt.record_sha256 == sha256(raw).hexdigest()
    assert preview.receipt.record_bytes == len(raw)
    assert preview.repository == state.review.repository
    assert preview.pr_number == state.review.pr_number
    assert preview.input_origin == state.review.input_origin
    assert preview.review_created_at == state.review.created_at
    assert preview.producer_tool_version == state.review.tool_version
    assert preview.producer_ruleset_version == state.review.ruleset_version
    assert preview.producer_source_identity == state.review.analysis_source_identity
    assert preview.criteria_source == state.review.criteria_source_provenance
    assert preview.criteria_revision_number == 3
    assert not preview.criteria_confirmed and not preview.has_active_analysis
    assert preview.criterion_count == len(state.criteria_revision.criteria)
    assert preview.resolution_event_count == len(state.resolution_events)
    assert preview.receipt.analysis_history_count == len(state.analysis_history)


def test_explicit_byte_import_preserves_record_and_rejects_overwrite(record, tmp_path):
    _, state, raw = record
    preview = transfer.inspect_review_bytes(raw)
    target = JsonReviewStore(tmp_path / "target")
    receipt = transfer.import_review_bytes(target, raw,
        expected_sha256=preview.receipt.record_sha256)
    path = target.directory / f"{state.review.review_id}.json"
    assert receipt.action == "imported"
    assert receipt.record_sha256 == preview.receipt.record_sha256
    assert path.read_bytes() == raw
    assert target.load(state.review.review_id) == state
    with pytest.raises(FileExistsError):
        transfer.import_review_bytes(target, raw, expected_sha256=receipt.record_sha256)
    assert path.read_bytes() == raw


def test_changed_bytes_after_inspection_never_write(record, tmp_path):
    _, _, raw = record
    preview = transfer.inspect_review_bytes(raw)
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(ValueError, match="changed"):
        transfer.import_review_bytes(target, raw + b" ",
            expected_sha256=preview.receipt.record_sha256)
    assert not target.directory.exists()


def test_snapshot_is_bound_to_original_bytes_and_owner(record):
    store, state, raw = record
    observed, preview = transfer.read_review_transfer(store, state.review.review_id)
    assert observed == raw
    expected = preview.receipt.record_sha256
    assert transfer.read_review_transfer(store, state.review.review_id,
        expected_sha256=expected)[0] == raw
    path = store.directory / f"{state.review.review_id}.json"
    path.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="changed"):
        transfer.read_review_transfer(store, state.review.review_id, expected_sha256=expected)
    path.rename(store.directory / "foreign.json")
    with pytest.raises(ValueError, match="identity"):
        transfer.read_review_transfer(store, "foreign")


@pytest.mark.parametrize("raw", [b"{}", b"[]", b"\xff", "not bytes", b"[" * 2000])
def test_malformed_byte_preview_rejected(raw):
    with pytest.raises(ValueError):
        transfer.inspect_review_bytes(raw)


def test_byte_bound_enforced_before_decode(record, monkeypatch):
    _, _, raw = record
    monkeypatch.setattr(transfer, "MAX_SAVED_RECORD_BYTES", len(raw))
    assert transfer.inspect_review_bytes(raw).receipt.record_bytes == len(raw)
    with pytest.raises(ValueError, match="byte limit"):
        transfer.inspect_review_bytes(raw + b" ")
