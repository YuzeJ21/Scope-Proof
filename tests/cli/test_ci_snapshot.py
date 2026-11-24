"""Export externally reported CI context from a saved review through the CLI."""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from scopeproof_core.cli import main
from scopeproof_core.reviews.ci_status import MAX_CI_STATUS_BYTES
from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import Criterion, normalized_criteria_sha256
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import junit_audit_state


@pytest.fixture
def snapshot_case(tmp_path):
    state = junit_audit_state()
    assert state.bundle is not None
    store = JsonReviewStore(tmp_path / "reviews")
    record = store.save(state)
    manifest = tmp_path / "manifest.json"
    data = {
        "schema_version": "criterion-ci-status-v1",
        "repository": state.review.repository,
        "pr_number": state.review.pr_number,
        "criteria_sha256": normalized_criteria_sha256(state.bundle.criteria),
        "expected_tests": {"AC-01": ["export"], "AC-02": ["error"]},
        "runs": [{
            "run_id": "constructed-exact",
            "head_sha": state.review.head_sha,
            "source_url": "https://ci.example.invalid/exact",
            "outcomes": {"export": "passed", "error": "skipped"},
        }],
    }
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    output = tmp_path / "handoff" / "snapshot.html"
    command = [
        "ci-snapshot", state.review.review_id, str(manifest),
        "--storage-dir", str(record.parent), "--output", str(output),
    ]
    return state, store, record, manifest, data, output, command


def test_ci_snapshot_command_renders_exact_manifest_without_mutating_inputs(snapshot_case, capsys):
    state, _, record, manifest, _, output, command = snapshot_case
    before_record, before_manifest = record.read_bytes(), manifest.read_bytes()

    assert main(command) == 0

    assert capsys.readouterr().err == ""
    html = output.read_text(encoding="utf-8")
    assert state.review.head_sha in html
    assert state.review.review_id in html
    assert sha256(before_manifest).hexdigest() in html
    assert "Local file" in html
    assert "https://ci.example.invalid/exact" in html
    assert "Explicitly skipped" in html
    assert "Externally supplied CI results" in html
    assert record.read_bytes() == before_record
    assert manifest.read_bytes() == before_manifest


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("repository", "confirmed review context"),
        ("pr_number", "confirmed review context"),
        ("criteria_sha256", "confirmed review context"),
        ("head_sha", "exact-head run"),
        ("invalid-json", "valid UTF-8 JSON"),
        ("oversized", "exceeds the byte limit"),
        ("missing-file", "No such file"),
    ],
)
def test_ci_snapshot_command_refuses_bad_inputs_before_output(
    snapshot_case, change, message, capsys,
):
    _, _, record, manifest, data, output, command = snapshot_case
    if change == "invalid-json":
        manifest.write_bytes(b"{")
    elif change == "oversized":
        manifest.write_bytes(b" " * (MAX_CI_STATUS_BYTES + 1))
    elif change == "missing-file":
        manifest.unlink()
    else:
        if change == "head_sha":
            data["runs"][0]["head_sha"] = "d" * 40
        else:
            data[change] = {"repository": "example/other", "pr_number": 714,
                            "criteria_sha256": "e" * 64}[change]
        manifest.write_text(json.dumps(data), encoding="utf-8")
    before = record.read_bytes()

    with pytest.raises(SystemExit) as error:
        main(command)

    assert error.value.code == 2
    assert message in capsys.readouterr().err
    assert not output.parent.exists()
    assert record.read_bytes() == before


def test_ci_snapshot_command_refuses_pending_review(snapshot_case, capsys):
    state, store, record, _, _, output, command = snapshot_case
    store.save(revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="CONSTRUCTED updated behavior")],
        "CONSTRUCTED updated behavior",
    ))
    before = record.read_bytes()

    with pytest.raises(SystemExit) as error:
        main(command)

    assert error.value.code == 2
    assert "active analysis" in capsys.readouterr().err
    assert not output.parent.exists()
    assert record.read_bytes() == before


def test_ci_snapshot_command_keeps_invalid_manifest_values_out_of_errors(snapshot_case, capsys):
    _, _, _, manifest, data, output, command = snapshot_case
    data["runs"][0]["source_url"] = "https://tester:constructed-secret@ci.example.invalid/exact"
    manifest.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(command)

    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "CI status manifest" in message
    assert "constructed-secret" not in message
    assert not output.parent.exists()


def test_ci_snapshot_command_refuses_existing_output_and_invalid_suffix(snapshot_case, capsys):
    _, _, record, _, _, output, command = snapshot_case
    output.parent.mkdir()
    output.write_text("existing output", encoding="utf-8")
    before = record.read_bytes()

    with pytest.raises(SystemExit) as error:
        main(command)
    assert error.value.code == 2
    assert "already exists" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "existing output"

    invalid_output = Path(command[-1]).with_suffix(".json")
    with pytest.raises(SystemExit) as error:
        main([*command[:-1], str(invalid_output)])
    assert error.value.code == 2
    assert "must end in .html" in capsys.readouterr().err
    assert not invalid_output.exists()
    assert record.read_bytes() == before
