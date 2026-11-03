"""CONSTRUCTED transfer safety and preservation checks, not independent-use evidence."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.storage import transfer
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.historical_analysis_fixture import historical_analysis_state


@pytest.fixture
def saved(tmp_path):
    store = JsonReviewStore(tmp_path / "source")
    state = historical_analysis_state()
    path = store.save(state)
    # Exercise exact byte preservation, including non-default line endings.
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    return store, state, path


def test_transfer_preserves_exact_record_and_pending_history(saved, tmp_path):
    store, state, path = saved
    before = path.read_bytes()
    output = tmp_path / "portable.json"
    exported = transfer.export_review(store, state.review.review_id, output)
    target = JsonReviewStore(tmp_path / "recipient")
    imported = transfer.import_review(target, output)
    assert output.read_bytes() == before == path.read_bytes()
    assert (target.directory / path.name).read_bytes() == before
    assert target.load(state.review.review_id) == state
    assert state.bundle is None and not state.review.criteria_confirmed
    for receipt in (exported, imported):
        assert receipt.review_id == state.review.review_id
        assert receipt.record_sha256 == sha256(before).hexdigest()
        assert receipt.record_bytes == len(before)
        assert receipt.record_version == 9
        assert receipt.saved_at == json.loads(before)["saved_at"]
        assert receipt.head_sha == state.review.head_sha
        assert receipt.analysis_history_count == len(state.analysis_history)
        assert receipt.state_fingerprint == store.state_fingerprint(state)
        assert "authentication" in receipt.boundary_note


def test_transfer_current_analysis_unchanged(tmp_path):
    source = JsonReviewStore(tmp_path / "source")
    state = new_review_state(build_demo_review())
    original = source.save(state)
    output = tmp_path / "review.json"
    transfer.export_review(source, state.review.review_id, output)
    target = JsonReviewStore(tmp_path / "target")
    transfer.import_review(target, output)
    assert target.load(state.review.review_id) == state
    assert (target.directory / original.name).read_bytes() == original.read_bytes()


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(record_version=10),
    lambda p: p.update(record_version=True),
    lambda p: p.update(extra="unknown"),
    lambda p: p.update(state={}),
    lambda p: p["state"]["review"].update(review_id="../escape"),
])
def test_invalid_transfer_never_creates_store(saved, tmp_path, mutation):
    _, _, path = saved
    payload = json.loads(path.read_bytes())
    mutation(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(ValueError):
        transfer.import_review(target, path)
    assert not target.directory.exists()


@pytest.mark.parametrize("content", [b"[]", b"null", b"{", b"\xff", b"[" * 2000,
    b'{"record_version":1,"record_version":9,"state":{}}'])
def test_malformed_transfer_rejected_before_writes(tmp_path, content):
    source = tmp_path / "bad.json"
    source.write_bytes(content)
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(ValueError):
        transfer.import_review(target, source)
    assert not target.directory.exists()


def test_export_rejects_filename_owner_mismatch(saved, tmp_path):
    store, _, path = saved
    path.rename(store.directory / "foreign.json")
    with pytest.raises(ValueError, match="identity"):
        transfer.export_review(store, "foreign", tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


def test_export_and_import_do_not_overwrite(saved, tmp_path):
    source, state, original = saved
    before = original.read_bytes()
    with pytest.raises(FileExistsError):
        transfer.export_review(source, state.review.review_id, original)
    with pytest.raises(FileExistsError):
        transfer.import_review(source, original)
    assert original.read_bytes() == before


def test_concurrent_imports_create_exactly_once(saved, tmp_path):
    _, state, path = saved
    target = JsonReviewStore(tmp_path / "target")
    def attempt():
        try:
            transfer.import_review(target, path)
            return True
        except FileExistsError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == [False, True]
    assert target.load(state.review.review_id) == state
    assert (target.directory / path.name).read_bytes() == path.read_bytes()


def test_import_rejects_oversize_before_creating_store(saved, tmp_path, monkeypatch):
    _, _, path = saved
    monkeypatch.setattr(transfer, "MAX_SAVED_RECORD_BYTES", 100)
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(ValueError, match="byte limit"):
        transfer.import_review(target, path)
    assert not target.directory.exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink creation requires privileges on Windows")
def test_symlink_source_and_destination_rejected(saved, tmp_path):
    source, state, path = saved
    link = tmp_path / "linked.json"
    link.symlink_to(path)
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(ValueError):
        transfer.import_review(target, link)
    assert not target.directory.exists()
    before = path.read_bytes()
    with pytest.raises((ValueError, FileExistsError)):
        transfer.export_review(source, state.review.review_id, link)
    target.directory.mkdir()
    (target.directory / path.name).symlink_to(path)
    with pytest.raises((ValueError, FileExistsError)):
        transfer.import_review(target, path)
    assert path.read_bytes() == before


def test_legacy_transfer_retains_bytes_and_reopens_conservatively(tmp_path):
    fixture = Path(__file__).parents[1] / "fixtures/released_v023_upgrade/native_v4.json"
    before = fixture.read_bytes()
    source = JsonReviewStore(tmp_path / "source")
    imported = transfer.import_review(source, fixture)
    assert imported.record_version == 4
    loaded = source.load(imported.review_id)
    assert loaded.bundle.gate.verdict.value == "needs_review"
    assert loaded.analysis_history[0].gate.verdict.value == "needs_review"
    output = tmp_path / "portable.json"
    transfer.export_review(source, imported.review_id, output)
    assert output.read_bytes() == before == fixture.read_bytes()
    assert json.loads(before)["state"]["bundle"]["gate"]["verdict"] == "ready"


def test_transfer_preserves_junit_audit_and_rejects_tampered_gate(tmp_path):
    from tests.junit_audit_fixture import junit_audit_state
    state = junit_audit_state()
    # The imported artifact and original mapping remain in the complete saved record.
    source = JsonReviewStore(tmp_path / "source")
    original = source.save(state)
    target = JsonReviewStore(tmp_path / "target")
    transfer.import_review(target, original)
    assert target.load(state.review.review_id) == state
    assert state.bundle.junit_evidence_imports
    data = json.loads(original.read_bytes())
    data["state"]["bundle"]["gate"]["verdict"] = "ready"
    original.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        transfer.import_review(JsonReviewStore(tmp_path / "other"), original)
    assert not (tmp_path / "other").exists()


def test_nested_duplicate_key_rejected(saved, tmp_path):
    _, _, path = saved
    text = path.read_text().replace('"criteria_confirmed": false',
        '"criteria_confirmed": true, "criteria_confirmed": false', 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        transfer.import_review(JsonReviewStore(tmp_path / "target"), path)
    assert not (tmp_path / "target").exists()


def test_raw_report_is_not_a_transfer_file(saved, tmp_path):
    _, state, path = saved
    path.write_text(state.model_dump_json(), encoding="utf-8")
    with pytest.raises(ValueError):
        transfer.import_review(JsonReviewStore(tmp_path / "target"), path)
    assert not (tmp_path / "target").exists()


def test_corrupt_existing_target_is_never_overwritten(saved, tmp_path):
    _, _, path = saved
    target = JsonReviewStore(tmp_path / "target")
    target.directory.mkdir()
    destination = target.directory / path.name
    destination.write_bytes(b"corrupt but owned by recipient")
    with pytest.raises(FileExistsError):
        transfer.import_review(target, path)
    assert destination.read_bytes() == b"corrupt but owned by recipient"


@pytest.mark.parametrize("portable", [False, True])
def test_exact_reader_and_transfer_on_both_atomic_backends(saved, tmp_path, monkeypatch, portable):
    import scopeproof_core.storage.atomic_files as atomic
    if portable:
        monkeypatch.setattr(atomic, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    source, state, original = saved
    output = tmp_path / "out.json"
    transfer.export_review(source, state.review.review_id, output)
    transfer.import_review(JsonReviewStore(tmp_path / "target"), output)
    assert output.read_bytes() == original.read_bytes()


def test_import_failure_does_not_leave_partial_record(saved, tmp_path, monkeypatch):
    import scopeproof_core.storage.atomic_files as atomic
    _, _, original = saved
    def fail(*args):
        raise OSError("constructed write failure")
    monkeypatch.setattr(atomic, "_write_all", fail)
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(OSError, match="constructed"):
        transfer.import_review(target, original)
    assert not (target.directory / original.name).exists()
    assert not list(target.directory.glob("*.json"))


def test_cli_transfer_receipts_and_no_overwrite(saved, tmp_path, capsys):
    from scopeproof_core.cli import main
    source, state, path = saved
    output = tmp_path / "portable.json"
    assert main(["export-review", state.review.review_id, "--storage-dir", str(source.directory),
                 "--output", str(output)]) == 0
    exported = json.loads(capsys.readouterr().out)
    target = tmp_path / "target"
    assert main(["import-review", "--input", str(output), "--storage-dir", str(target)]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert exported["record_sha256"] == imported["record_sha256"]
    assert exported["action"] == "exported" and imported["action"] == "imported"
    with pytest.raises(SystemExit) as exc:
        main(["import-review", "--input", str(output), "--storage-dir", str(target)])
    assert exc.value.code == 2
    assert (target / path.name).read_bytes() == path.read_bytes()


@pytest.mark.parametrize("location,field", [
    (("review",), "created_at"),
    (("criteria_revision",), "created_at"),
    (("analysis_history", 0, "review"), "created_at"),
    (("analysis_history", 0, "reviewer_selected_references", 0), "selected_at"),
    (("analysis_history", 0, "runtime_evidence", 0), "timestamp"),
    (("resolution_events", 0), "timestamp"),
    (("resolution_events", 0), "event_id"),
    (("analysis_history", 0, "resolutions", 0), "timestamp"),
])
def test_transfer_requires_recorded_provenance(saved, tmp_path, location, field):
    _, _, path = saved
    payload = json.loads(path.read_bytes())
    value = payload["state"]
    for key in location:
        value = value[key]
    del value[field]
    path.write_text(json.dumps(payload), encoding="utf-8")
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(ValueError, match="recorded"):
        transfer.import_review(target, path)
    assert not target.directory.exists()


def test_transfer_never_generates_a_missing_review_identity(saved, tmp_path):
    _, _, path = saved
    payload = json.loads(path.read_bytes())
    payload["state"]["analysis_history"] = []
    payload["state"]["resolution_events"] = []
    del payload["state"]["review"]["review_id"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    target = JsonReviewStore(tmp_path / "target")
    with pytest.raises(ValueError, match="recorded"):
        transfer.import_review(target, path)
    assert not target.directory.exists()
