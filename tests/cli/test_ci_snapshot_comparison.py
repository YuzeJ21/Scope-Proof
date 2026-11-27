"""An explicit previous-manifest flag adds a read-only comparison to CI export."""

import json
from hashlib import sha256

import pytest

from scopeproof_core.cli import main
from scopeproof_core.reviews.ci_status import MAX_CI_STATUS_BYTES
from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import Criterion
from tests.cli.test_ci_snapshot import snapshot_case as snapshot_case


def _comparison_case(snapshot_case, tmp_path):
    state, store, record, current, data, output, command = snapshot_case
    previous = tmp_path / "previous.json"
    previous.write_bytes(current.read_bytes())
    data["runs"].append({
        "run_id": "targeted", "head_sha": state.review.head_sha,
        "source_url": "https://ci.example.invalid/targeted",
        "outcomes": {"error": "failed"},
    })
    current.write_text(json.dumps(data), encoding="utf-8")
    return state, store, record, current, previous, output, [
        *command, "--previous-manifest", str(previous),
    ]


def test_cli_exports_comparison_and_preserves_both_manifests_and_saved_record(
    snapshot_case, tmp_path, capsys,
):
    state, _, record, current, previous, output, command = _comparison_case(snapshot_case, tmp_path)
    before = {path: path.read_bytes() for path in (record, previous, current)}
    assert main(command) == 0
    assert not capsys.readouterr().err
    html = output.read_text(encoding="utf-8")
    assert "ScopeProof CI Context Comparison" in html
    assert "Explicitly skipped" in html and "Failed" in html
    assert "https://ci.example.invalid/targeted" in html
    assert state.review.head_sha in html
    assert sha256(before[previous]).hexdigest() in html
    assert sha256(before[current]).hexdigest() in html
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("change", ["repository", "head", "invalid", "oversized", "missing"])
def test_cli_refuses_bad_previous_context_before_creating_output(
    snapshot_case, tmp_path, change, capsys,
):
    _, _, record, _, previous, output, command = _comparison_case(snapshot_case, tmp_path)
    if change == "invalid":
        previous.write_bytes(b"{")
    elif change == "oversized":
        previous.write_bytes(b" " * (MAX_CI_STATUS_BYTES + 1))
    elif change == "missing":
        previous.unlink()
    else:
        data = json.loads(previous.read_bytes())
        if change == "repository":
            data["repository"] = "different/repository"
        else:
            for run in data["runs"]:
                run["head_sha"] = "e" * 40
        previous.write_text(json.dumps(data), encoding="utf-8")
    before = record.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(command)
    assert error.value.code == 2
    assert "unrecognized arguments" not in capsys.readouterr().err
    assert not output.parent.exists()
    assert record.read_bytes() == before


def test_cli_sanitizes_invalid_values_in_previous_manifest(snapshot_case, tmp_path, capsys):
    _, _, _, _, previous, output, command = _comparison_case(snapshot_case, tmp_path)
    data = json.loads(previous.read_bytes())
    data["runs"][0]["source_url"] = "https://tester:constructed-secret@ci.example.invalid/run"
    previous.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(command)
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "CI status manifest" in message and "constructed-secret" not in message
    assert not output.parent.exists()


def test_cli_context_mismatch_does_not_print_validation_payloads(snapshot_case, tmp_path, capsys):
    _, _, _, _, previous, output, command = _comparison_case(snapshot_case, tmp_path)
    data = json.loads(previous.read_bytes())
    data["repository"] = "different/repository"
    previous.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main(command)
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "input_value" not in message
    assert "ReviewBundle(" not in message and "CIStatusManifest(" not in message
    assert not output.parent.exists()


def test_cli_refuses_pending_review_comparison(snapshot_case, tmp_path, capsys):
    state, store, record, _, _, output, command = _comparison_case(snapshot_case, tmp_path)
    store.save(revise_criteria(
        state, [Criterion(criterion_id="AC-01", text="CONSTRUCTED updated requirement")],
        "CONSTRUCTED updated requirement",
    ))
    before = record.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(command)
    assert error.value.code == 2
    assert "active analysis" in capsys.readouterr().err
    assert not output.parent.exists()
    assert record.read_bytes() == before


def test_cli_comparison_does_not_overwrite_existing_report(snapshot_case, tmp_path, capsys):
    _, _, record, current, previous, output, command = _comparison_case(snapshot_case, tmp_path)
    output.parent.mkdir()
    output.write_bytes(b"prior handoff")
    before = {path: path.read_bytes() for path in (record, current, previous)}
    with pytest.raises(SystemExit) as error:
        main(command)
    assert error.value.code == 2
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == b"prior handoff"
    assert {path: path.read_bytes() for path in before} == before
