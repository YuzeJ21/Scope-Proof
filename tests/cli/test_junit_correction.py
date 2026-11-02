"""CLI corrections require explicit whole-import intent and preserve saved originals."""

import json

import pytest

from scopeproof_core.cli import main
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import junit_audit_state


def correction_args(state, store):
    return [
        "correct-junit-mappings", state.review.review_id,
        "--storage-dir", str(store.directory), "--import-id", "constructed-junit-import",
        "--map", "AC-01=suite-0001-case-0002", "--map", "AC-02=suite-0001-case-0001",
        "--reviewer", "CONSTRUCTED CLI correction", "--reason", "CONSTRUCTED wrong mapping",
        "--expected-state-fingerprint", store.state_fingerprint(state), "--confirm-whole-import",
    ]


def test_cli_catalog_preserves_original_and_exposes_effective_mappings(tmp_path, capsys):
    state = junit_audit_state()
    store = JsonReviewStore(tmp_path)
    store.save(state)
    assert main(correction_args(state, store)) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["event"]["action"] == "mapping_corrected"
    assert receipt["final_acceptance"] == state.review.final_acceptance
    updated = store.load(state.review.review_id)
    assert updated.bundle.junit_evidence_imports == state.bundle.junit_evidence_imports
    assert updated.bundle.gate == state.bundle.gate
    assert main(["junit-imports", state.review.review_id, "--storage-dir", str(tmp_path)]) == 0
    catalog = json.loads(capsys.readouterr().out)
    entry = catalog["imports"][0]
    assert entry["mapped_criterion_ids"] == ["AC-01", "AC-02"]
    assert entry["original_mappings"][0]["test_case_ids"] == ["suite-0001-case-0001"]
    assert entry["effective_mappings"][0]["test_case_ids"] == ["suite-0001-case-0002"]
    assert entry["mapping_correction_events"] == [receipt["event"]]


@pytest.mark.parametrize("bad", ["unconfirmed", "malformed", "duplicate", "unknown", "stale"])
def test_invalid_cli_correction_cannot_modify_saved_record(tmp_path, capsys, bad):
    state = junit_audit_state()
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    args = correction_args(state, store)
    if bad == "unconfirmed":
        args.remove("--confirm-whole-import")
    elif bad == "malformed":
        args[args.index("--map") + 1] = "AC-01=suite-0001"
    elif bad == "duplicate":
        args.extend(["--map", "AC-02=suite-0001-case-0002"])
    elif bad == "unknown":
        args[args.index("--import-id") + 1] = "unknown-import"
    else:
        args[args.index("--expected-state-fingerprint") + 1] = "0" * 64
    before = path.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert path.read_bytes() == before
    captured = capsys.readouterr()
    assert not captured.out
    assert "invalid choice" not in captured.err
