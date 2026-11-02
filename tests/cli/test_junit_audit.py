"""Headless saved-import recovery is explicit, locked and fingerprint-bound."""

import json

import pytest

from scopeproof_core.cli import main
from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import Criterion
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import junit_audit_state


def saved(tmp_path):
    state = junit_audit_state()
    store = JsonReviewStore(tmp_path / "reviews")
    path = store.save(state)
    return state, store, path


def arguments(state, store, fingerprint):
    return [
        "withdraw-junit",
        state.review.review_id,
        "--storage-dir",
        str(store.directory),
        "--import-id",
        "constructed-junit-import",
        "--reviewer",
        "Constructed CLI reviewer",
        "--reason",
        "Constructed mistaken mapping",
        "--expected-state-fingerprint",
        fingerprint,
    ]


def test_catalog_and_withdrawal_are_typed_complete_and_preserve_gate(tmp_path, capsys):
    state, store, path = saved(tmp_path)
    before = path.read_bytes()
    assert (
        main(["junit-imports", state.review.review_id, "--storage-dir", str(store.directory)]) == 0
    )
    catalog = json.loads(capsys.readouterr().out)
    assert catalog["state_fingerprint"] == store.state_fingerprint(state)
    assert catalog["active_analysis_available"] is True
    entry = catalog["imports"][0]
    assert entry["import_id"] == "constructed-junit-import"
    assert entry["status"] == "active" and entry["withdrawal_event"] is None
    assert entry["mapped_criterion_ids"] == ["AC-01", "AC-02"]
    assert path.read_bytes() == before
    assert main(arguments(state, store, catalog["state_fingerprint"])) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["event"]["import_id"] == "constructed-junit-import"
    assert receipt["event"]["reviewer"] == "Constructed CLI reviewer"
    assert receipt["verdict"] == state.bundle.gate.verdict.value
    assert receipt["final_acceptance"] == state.review.final_acceptance
    updated = store.load(state.review.review_id)
    assert updated.bundle.junit_evidence_imports == state.bundle.junit_evidence_imports
    assert updated.bundle.gate == state.bundle.gate
    assert updated.bundle.active_junit_import_ids == []
    assert receipt["state_fingerprint"] == store.state_fingerprint(updated)
    assert (
        main(["junit-imports", state.review.review_id, "--storage-dir", str(store.directory)]) == 0
    )
    after = json.loads(capsys.readouterr().out)
    assert after["imports"][0]["status"] == "withdrawn"
    assert after["imports"][0]["withdrawal_event"] == receipt["event"]


@pytest.mark.parametrize("failure", ["stale", "unknown", "blank", "repeat", "deleted"])
def test_failed_cli_withdrawal_does_not_create_or_modify_record(tmp_path, capsys, failure):
    state, store, path = saved(tmp_path)
    args = arguments(state, store, store.state_fingerprint(state))
    if failure == "stale":
        args[-1] = "0" * 64
    elif failure == "unknown":
        args[args.index("--import-id") + 1] = "unknown-import"
    elif failure == "blank":
        args[args.index("--reason") + 1] = " "
    elif failure == "repeat":
        assert main(args) == 0
        capsys.readouterr()
        args[-1] = store.state_fingerprint(store.load(state.review.review_id))
    else:
        path.unlink()
    before = path.read_bytes() if path.exists() else None
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert (path.read_bytes() if path.exists() else None) == before
    captured = capsys.readouterr()
    assert not captured.out
    assert "invalid choice" not in captured.err


def test_catalog_pending_review_does_not_present_archived_import_as_active(tmp_path, capsys):
    state, store, _ = saved(tmp_path)
    state = revise_criteria(state, [Criterion(criterion_id="AC-01", text="Changed")], "Changed")
    path = store.save(state)
    before = path.read_bytes()
    assert (
        main(["junit-imports", state.review.review_id, "--storage-dir", str(store.directory)]) == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["active_analysis_available"] is False and payload["imports"] == []
    assert path.read_bytes() == before
