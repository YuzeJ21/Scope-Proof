"""CONSTRUCTED intent handoff: no actor, runtime, or independent-use evidence."""

import json
from copy import deepcopy
from hashlib import sha256

import pytest

from scopeproof_core.cli import main
from scopeproof_core.storage.json_store import JsonReviewStore


def handoff_inputs(tmp_path):
    source = tmp_path / "requirements.txt"
    source.write_bytes("Export café CSV\r\nShow export errors\r\n".encode())
    # Deliberately edited normalized text/order, stable nonconsecutive IDs and all fields.
    criteria = [
        {
            "criterion_id": "AC-20",
            "text": "Show a clear export error",
            "priority": "should_have",
            "criterion_type": "error_state",
            "criterion_source": "user_confirmed",
            "source_span": "requirements:2",
            "required_evidence_level": "E4",
        },
        {
            "criterion_id": "AC-03",
            "text": "Export the café list as CSV",
            "priority": "must_have",
            "criterion_type": "behavior",
            "criterion_source": "implicit_rule_pack",
            "source_span": None,
            "required_evidence_level": "E3",
        },
    ]
    payload = {
        "schema_version": 1,
        "source_text_sha256": sha256(source.read_bytes()).hexdigest(),
        "criteria": criteria,
    }
    document = tmp_path / "criteria.json"
    document.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return source, document, payload


def confirm(source, document, tmp_path):
    path = tmp_path / "confirmation.json"
    assert (
        main(
            [
                "prepare-requirements-confirmation",
                "--requirements",
                str(source),
                "--criteria",
                str(document),
                "--source-uri",
                "https://example.test/constructed",
                "--confirmed-by",
                "CONSTRUCTED authorized-role simulation",
                "--output",
                str(path),
            ]
        )
        == 0
    )
    return path


def test_prepare_criteria_emits_unconfirmed_complete_draft(tmp_path, capsys):
    source = tmp_path / "requirements.txt"
    source.write_bytes("- Export café CSV\r\n\r\n2. Show export errors\r\n".encode())
    output = tmp_path / "draft.json"

    assert main(["prepare-criteria", "--requirements", str(source), "--output", str(output)]) == 0

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document == {
        "schema_version": 1,
        "source_text_sha256": sha256(source.read_bytes()).hexdigest(),
        "criteria": [
            {
                "criterion_id": "AC-01",
                "text": "Export café CSV",
                "priority": "must_have",
                "criterion_type": "behavior",
                "criterion_source": "user_confirmed",
                "source_span": None,
                "required_evidence_level": "E1",
            },
            {
                "criterion_id": "AC-02",
                "text": "Show export errors",
                "priority": "must_have",
                "criterion_type": "behavior",
                "criterion_source": "user_confirmed",
                "source_span": None,
                "required_evidence_level": "E1",
            },
        ],
    }
    metadata = json.loads(capsys.readouterr().out)
    assert metadata["confirmed"] is False
    assert not (tmp_path / "confirmation.json").exists()


def test_typed_handoff_preserves_complete_criteria_in_saved_review(tmp_path, capsys):
    source, document, payload = handoff_inputs(tmp_path)
    confirmation = confirm(source, document, tmp_path)
    capsys.readouterr()
    assert (
        main(
            [
                "validate-requirements-confirmation",
                "--requirements",
                str(source),
                "--criteria",
                str(document),
                "--confirmation",
                str(confirmation),
            ]
        )
        == 0
    )
    provenance = json.loads(capsys.readouterr().out)
    canonical = json.dumps(
        payload["criteria"], ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    assert provenance["normalized_criteria_sha256"] == sha256(canonical).hexdigest()
    storage = tmp_path / "reviews"
    report = tmp_path / "review.json"
    assert (
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(source),
                "--criteria",
                str(document),
                "--confirmation",
                str(confirmation),
                "--storage-dir",
                str(storage),
                "--report",
                str(report),
            ]
        )
        == 0
    )
    metadata = json.loads(capsys.readouterr().out)
    state = JsonReviewStore(storage).load(metadata["review_id"])
    assert [c.model_dump(mode="json") for c in state.criteria_revision.criteria] == payload[
        "criteria"
    ]
    assert state.bundle is not None
    assert [c.model_dump(mode="json") for c in state.bundle.criteria] == payload["criteria"]
    assert state.bundle.source_text.encode() == source.read_bytes()
    assert state.review.criteria_source_provenance.model_dump(mode="json") == provenance
    assert state.bundle.runtime_evidence == []
    assert state.bundle.resolutions == [] and not state.review.final_acceptance
    assert state.review.input_origin.value == "local_fixture"
    exported = json.loads(report.read_text(encoding="utf-8"))
    assert exported["bundle"]["criteria"] == payload["criteria"]
    assert (
        main(
            ["export", metadata["review_id"], "--storage-dir", str(storage), "--format", "markdown"]
        )
        == 0
    )
    readable = capsys.readouterr().out.replace("\\-", "-")
    assert "AC-20" in readable and "AC-03" in readable and "E4" in readable and "E3" in readable


@pytest.mark.parametrize(
    "change",
    [
        "criterion_id",
        "text",
        "priority",
        "criterion_type",
        "criterion_source",
        "source_span",
        "required_evidence_level",
        "order",
        "source",
        "omit_typed",
    ],
)
def test_changed_handoff_fails_before_ingestion_or_writes(tmp_path, capsys, monkeypatch, change):
    source, document, payload = handoff_inputs(tmp_path)
    confirmation = confirm(source, document, tmp_path)
    capsys.readouterr()
    replacements = {
        "criterion_id": "AC-21",
        "text": "Different promise",
        "priority": "must_have",
        "criterion_type": "documentation",
        "criterion_source": "implicit_rule_pack",
        "source_span": "requirements:3",
        "required_evidence_level": "E1",
    }
    if change == "order":
        payload["criteria"].reverse()
    elif change == "source":
        source.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
    elif change != "omit_typed":
        payload["criteria"][0][change] = replacements[change]
    document.write_text(json.dumps(payload), encoding="utf-8")

    def forbidden_fetch(*_args, **_kwargs):
        pytest.fail("changed criteria reached network ingestion")

    monkeypatch.setattr("scopeproof_core.cli.GitHubClient.fetch_pull_request", forbidden_fetch)
    storage, report = tmp_path / "reviews", tmp_path / "review.md"
    option = [] if change == "omit_typed" else ["--criteria", str(document)]
    for input_option in (
        ["--pr", "https://github.com/acme/repo/pull/7"],
        ["--fixture", str(tmp_path / "must-not-be-read.json")],
    ):
        with pytest.raises(SystemExit) as raised:
            main(
                [
                    "review",
                    *input_option,
                    "--requirements",
                    str(source),
                    *option,
                    "--confirmation",
                    str(confirmation),
                    "--storage-dir",
                    str(storage),
                    "--report",
                    str(report),
                ]
            )
        assert raised.value.code == 2
        error = capsys.readouterr().err
        assert "does not match" in error and "must-not-be-read" not in error
        assert not storage.exists() and not report.exists()
    with pytest.raises(SystemExit):
        main(
            [
                "validate-requirements-confirmation",
                "--requirements",
                str(source),
                *option,
                "--confirmation",
                str(confirmation),
            ]
        )


@pytest.mark.parametrize(
    "malformation",
    [
        "empty",
        "duplicate",
        "unknown_document",
        "unknown_criterion",
        "bad_enum",
        "schema_version",
        "bad_hash",
        "stale_hash",
        "not_json",
        "too_large",
        "not_regular",
    ],
)
def test_invalid_document_never_creates_confirmation(tmp_path, capsys, malformation):
    source, document, original = handoff_inputs(tmp_path)
    payload = deepcopy(original)
    if malformation == "empty":
        payload["criteria"] = []
    elif malformation == "duplicate":
        payload["criteria"][1]["criterion_id"] = "AC-20"
    elif malformation == "unknown_document":
        payload["confirmed"] = True
    elif malformation == "unknown_criterion":
        payload["criteria"][0]["accepted"] = True
    elif malformation == "bad_enum":
        payload["criteria"][0]["required_evidence_level"] = "E5"
    elif malformation == "schema_version":
        payload["schema_version"] = 2
    elif malformation == "bad_hash":
        payload["source_text_sha256"] = "unknown"
    elif malformation == "stale_hash":
        payload["source_text_sha256"] = "f" * 64
    document.write_text(json.dumps(payload), encoding="utf-8")
    if malformation == "not_json":
        document.write_bytes(b"not-json")
    elif malformation == "too_large":
        document.write_bytes(b" " * (1_048_576 + 1))
    elif malformation == "not_regular":
        document.unlink()
        document.mkdir()
    output = tmp_path / "must-not-be-written.json"
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "prepare-requirements-confirmation",
                "--requirements",
                str(source),
                "--criteria",
                str(document),
                "--source-uri",
                "https://example.test/constructed",
                "--confirmed-by",
                "CONSTRUCTED role",
                "--output",
                str(output),
            ]
        )
    assert raised.value.code == 2
    assert not output.exists()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("command", ["prepare-criteria", "prepare-requirements-confirmation"])
def test_handoff_output_never_overwrites_existing_file(tmp_path, command):
    source, document, _payload = handoff_inputs(tmp_path)
    output = tmp_path / "existing.json"
    output.write_bytes(b"original bytes")
    args = [command, "--requirements", str(source), "--output", str(output)]
    if command == "prepare-requirements-confirmation":
        args += [
            "--criteria",
            str(document),
            "--source-uri",
            "https://example.test/constructed",
            "--confirmed-by",
            "CONSTRUCTED role",
        ]
    with pytest.raises(SystemExit):
        main(args)
    assert output.read_bytes() == b"original bytes"


def test_draft_does_not_replace_confirmation(tmp_path, capsys):
    source, document, _payload = handoff_inputs(tmp_path)
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--fixture",
                str(tmp_path / "must-not-be-read.json"),
                "--requirements",
                str(source),
                "--criteria",
                str(document),
                "--confirmation",
                str(document),
                "--storage-dir",
                str(tmp_path / "reviews"),
            ]
        )
    assert raised.value.code == 2
    assert "must-not-be-read" not in capsys.readouterr().err
    assert not (tmp_path / "reviews").exists()


def test_generated_draft_cannot_exceed_its_readable_byte_budget(tmp_path, capsys):
    source = tmp_path / "large-requirements.txt"
    source.write_bytes(b"x" * 1_048_576)
    output = tmp_path / "unreadable-draft.json"
    with pytest.raises(SystemExit) as raised:
        main(["prepare-criteria", "--requirements", str(source), "--output", str(output)])
    assert raised.value.code == 2
    assert "byte limit" in capsys.readouterr().err
    assert not output.exists()
