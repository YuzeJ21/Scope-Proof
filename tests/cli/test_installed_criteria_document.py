"""CONSTRUCTED typed-intent journey against an installed wheel, outside the checkout."""

import json
import os
import shutil
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest


def test_installed_typed_criteria_handoff(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")

    def run(*args, expected=0):
        process = subprocess.run(
            [interpreter, "-X", "utf8", "-I", *args],
            cwd=tmp_path, capture_output=True, text=True,
            encoding="utf-8", timeout=60, check=False,
        )
        assert process.returncode == expected, process.stdout + process.stderr
        return process

    def cli(*args, expected=0):
        return run("-m", "scopeproof_core.cli", *args, expected=expected)

    run("-c", "from pathlib import Path; import sys, scopeproof_core; "
        "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix)); "
        "assert not Path.cwd().is_relative_to(Path(scopeproof_core.__file__).resolve().parent)")
    fixture = tmp_path / "constructed-pr.json"
    shutil.copyfile(
        Path(__file__).parents[2] / "evals" / "fixtures" / "complete_implementation_pr.json",
        fixture,
    )
    fixture_snapshot = json.loads(fixture.read_text(encoding="utf-8"))
    source = tmp_path / "requirements.txt"
    source_text = "- Export café CSV\r\n\r\n2. Show export errors\r\n"
    source.write_bytes(source_text.encode("utf-8"))
    document_path = tmp_path / "criteria.json"
    confirmation_path = tmp_path / "confirmation.json"
    preparation = json.loads(cli(
        "prepare-criteria", "--requirements", str(source), "--output", str(document_path),
    ).stdout)
    assert preparation["confirmed"] is False
    assert preparation["criteria_document"] == str(document_path)
    assert not confirmation_path.exists()
    document = json.loads(document_path.read_text(encoding="utf-8"))
    defaults = {
        "priority": "must_have", "criterion_type": "behavior",
        "criterion_source": "user_confirmed", "source_span": None,
        "required_evidence_level": "E1",
    }
    assert document == {
        "schema_version": 1,
        "source_text_sha256": sha256(source.read_bytes()).hexdigest(),
        "criteria": [
            {"criterion_id": "AC-01", "text": "Export café CSV", **defaults},
            {"criterion_id": "AC-02", "text": "Show export errors", **defaults},
        ],
    }

    # Explicitly edited intent may differ from the source lines; no equivalence is inferred.
    document["criteria"] = [
        {
            "criterion_id": "AC-20", "text": "Show a clear export error",
            "priority": "should_have", "criterion_type": "error_state",
            "criterion_source": "user_confirmed", "source_span": "requirements:2",
            "required_evidence_level": "E4",
        },
        {
            "criterion_id": "AC-03", "text": "Export the café list as CSV",
            "priority": "must_have", "criterion_type": "behavior",
            "criterion_source": "implicit_rule_pack", "source_span": None,
            "required_evidence_level": "E3",
        },
    ]
    document_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    common = ["--requirements", str(source), "--criteria", str(document_path)]
    cli(
        "prepare-requirements-confirmation", *common,
        "--source-uri", "https://example.test/constructed-requirements",
        "--source-revision", "CONSTRUCTED source revision",
        "--confirmed-by", "CONSTRUCTED authorized-role simulation 测试",
        "--output", str(confirmation_path),
    )
    confirmation_before = confirmation_path.read_bytes()
    confirmation = json.loads(confirmation_before)
    validated = json.loads(cli(
        "validate-requirements-confirmation", *common,
        "--confirmation", str(confirmation_path),
    ).stdout)
    assert validated == confirmation
    canonical_criteria = json.dumps(
        document["criteria"], ensure_ascii=False, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    assert confirmation["source_text_sha256"] == sha256(source.read_bytes()).hexdigest()
    assert confirmation["normalized_criteria_sha256"] == sha256(canonical_criteria).hexdigest()
    assert confirmation["confirmed_by"] == "CONSTRUCTED authorized-role simulation 测试"
    assert confirmation["source_revision"] == "CONSTRUCTED source revision"

    storage = tmp_path / "reviews"
    report_path = tmp_path / "review.json"
    metadata = json.loads(cli(
        "review", "--fixture", str(fixture), *common,
        "--confirmation", str(confirmation_path), "--storage-dir", str(storage),
        "--report", str(report_path),
    ).stdout)
    record = storage / f"{metadata['review_id']}.json"
    assert metadata["record"] == str(record)
    assert metadata["report"] == str(report_path)
    assert metadata["base_sha"] == fixture_snapshot["base_sha"]
    assert metadata["head_sha"] == fixture_snapshot["head_sha"]
    assert metadata["ci_state"] == "passing"
    assert metadata["ci_total_check_runs"] == metadata["ci_successful_check_runs"] == 1
    assert metadata["ci_concrete_legacy_status_count"] == 0
    assert metadata["candidate_evidence_proves_correctness"] is False
    assert metadata["criteria_source_provenance"] == confirmation
    record_before = record.read_bytes()
    state = json.loads(record_before)["state"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report == state
    assert state["criteria_revision"]["confirmed"] is True
    assert state["criteria_revision"]["criteria"] == document["criteria"]
    assert state["criteria_revision"]["source_text"] == source_text
    assert state["bundle"]["criteria"] == document["criteria"]
    assert state["bundle"]["source_text"] == source_text
    assert state["review"]["criteria_source_provenance"] == confirmation
    assert state["review"]["input_origin"] == "local_fixture"
    assert state["bundle"]["runtime_evidence"] == []
    assert state["bundle"]["resolutions"] == state["resolution_events"] == []
    assert state["review"]["final_acceptance"] is False
    assert metadata["verdict"] == state["bundle"]["gate"]["verdict"]
    assert metadata["gate_reason_codes"] == state["bundle"]["gate"]["reason_codes"]
    exported = json.loads(cli(
        "export", metadata["review_id"], "--storage-dir", str(storage), "--format", "json",
    ).stdout)
    assert exported == state
    readable = cli(
        "export", metadata["review_id"], "--storage-dir", str(storage), "--format", "markdown",
    ).stdout.replace("\\-", "-").replace("\\_", "_")
    for field in ("AC-20", "AC-03", "E4", "E3", "café", "should_have"):
        assert field in readable
    assert record.read_bytes() == record_before

    # Reusing the old confirmation after an intent change must stop before fixture reads/writes.
    changed = deepcopy(document)
    changed["criteria"][0]["required_evidence_level"] = "E1"
    document_path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    refused = cli(
        "validate-requirements-confirmation", *common,
        "--confirmation", str(confirmation_path), expected=2,
    )
    assert refused.stdout == "" and "normalized_criteria_sha256" in refused.stderr
    refused_storage = tmp_path / "must-not-create-reviews"
    refused_report = tmp_path / "must-not-create-report.json"
    refused = cli(
        "review", "--fixture", str(tmp_path / "must-not-read-fixture.json"), *common,
        "--confirmation", str(confirmation_path), "--storage-dir", str(refused_storage),
        "--report", str(refused_report), expected=2,
    )
    assert refused.stdout == "" and "normalized_criteria_sha256" in refused.stderr
    assert not refused_storage.exists() and not refused_report.exists()
    assert record.read_bytes() == record_before
    assert confirmation_path.read_bytes() == confirmation_before
    assert source.read_bytes() == source_text.encode("utf-8")
