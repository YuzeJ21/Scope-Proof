"""Run explicitly against an installed wheel, outside the checkout, on POSIX or Windows."""

import html
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest


def test_installed_history_handoff(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")
    recipe = tmp_path / "constructed_history.py"
    shutil.copyfile(Path(__file__).parents[1] / "historical_analysis_fixture.py", recipe)
    records = tmp_path / "records"

    def run(*args, expected=0):
        process = subprocess.run(
            [interpreter, "-I", *args], cwd=tmp_path, capture_output=True, text=True,
            encoding="utf-8", timeout=60, check=False,
        )
        assert process.returncode == expected, process.stdout + process.stderr
        return process

    run("-c", "from pathlib import Path; import sys, scopeproof_core; "
        "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix)); "
        "import runpy; from scopeproof_core.storage.json_store import JsonReviewStore; "
        f"recipe = runpy.run_path({str(recipe)!r}); "
        f"JsonReviewStore(Path({str(records)!r})).save(recipe['historical_analysis_state']())")
    review_id = "constructed-history-only-review"
    record = records / f"{review_id}.json"
    before = record.read_bytes()
    catalog = json.loads(run("-m", "scopeproof_core.cli", "history", review_id,
                             "--storage-dir", str(records)).stdout)
    assert catalog["has_active_analysis"] is False
    assert catalog["current_criteria_confirmed"] is False
    assert catalog["current_criteria_revision_number"] == 3
    assert catalog["entries"][0]["history_position"] == 1
    args = ["-m", "scopeproof_core.cli", "export-history", review_id,
            "--storage-dir", str(records), "--history-position", "1",
            "--expected-state-fingerprint", catalog["state_fingerprint"]]
    report = json.loads(run(*args).stdout)
    assert report["report_kind"] == "scopeproof_historical_analysis"
    assert report["analysis"]["criteria_revision_number"] == 1
    assert report["analysis"]["review"]["tool_version"] == "0.2.4-constructed-historical-producer"
    assert report["validation_tool_version"] == "0.2.5"
    assert report["selection"]["state_fingerprint"] == catalog["state_fingerprint"]
    assert (report["selection"]["analysis_fingerprint"]
            == catalog["entries"][0]["analysis_fingerprint"])
    target = tmp_path / "historical.md"
    run(*args, "--format", "markdown", "--output", str(target))
    markdown = target.read_text(encoding="utf-8")
    assert markdown.startswith("# ScopeProof Historical Analysis\n")
    assert "not current-head verification or acceptance" in markdown
    assert "Full resolution history is unavailable" in markdown
    history = markdown.split("## Resolution History\n", 1)[1].split("\n## ", 1)[0]
    assert "constructed-historical-manual-decision" not in history
    run(*args, "--format", "markdown", "--output", str(target), expected=2)
    assert target.read_text(encoding="utf-8") == markdown
    assert record.read_bytes() == before
    # Mutate constructed saved criteria, keeping a valid record, then reuse the old receipt.
    run("-c", "from pathlib import Path; "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        f"store=JsonReviewStore(Path({str(records)!r})); state=store.load({review_id!r}); "
        "state.criteria_revision.source_text += ' CONSTRUCTED saved change'; store.save(state)")
    stale = run(*args, expected=2)
    assert stale.stdout == "" and "changed" in stale.stderr


def test_installed_readable_resolution_audit_handoff(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")
    recipe = tmp_path / "constructed_resolution_audit.py"
    shutil.copyfile(Path(__file__).parents[1] / "resolution_audit_fixture.py", recipe)
    records = tmp_path / "explicit-constructed-records"

    def run(*args):
        process = subprocess.run(
            [interpreter, "-I", *args], cwd=tmp_path, capture_output=True, text=True,
            encoding="utf-8", timeout=60, check=False,
        )
        assert process.returncode == 0, process.stdout + process.stderr
        return process.stdout

    run("-c", "from pathlib import Path; import sys, scopeproof_core, runpy; "
        "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix)); "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        f"fixture=runpy.run_path({str(recipe)!r}); "
        f"JsonReviewStore(Path({str(records)!r})).save(fixture['resolution_audit_state']())")
    review_id = "constructed-resolution-audit-review"
    path = records / f"{review_id}.json"
    before = path.read_bytes()
    original = json.loads(before)["state"]
    expected = [
        ("r1-old-accept", "Prior revision", 1),
        ("r2-old-change", "Superseded", 2),
        ("r2-current-accept", "Current", 2),
        ("r2-ac02-accept", "Current", 2),
        ("r2-ac03-accept", "Current", 2),
        ("r2-ac04-accept", "Current", 2),
        ("r2-final-true", "Superseded", 2),
        ("r2-final-false", "Current", 2),
    ]
    events = original["resolution_events"]
    assert [event["event_id"] for event in events] == [row[0] for row in expected]
    for kind in ("markdown", "html"):
        report = run("-m", "scopeproof_core.cli", "export", review_id,
                     "--storage-dir", str(records), "--format", kind)
        marker = "## Resolution History\n" if kind == "markdown" else "<h2>Resolution History</h2>"
        history = report.split(marker, 1)[1]
        history = history.split("\n## " if kind == "markdown" else "<h2>", 1)[0]
        assert "<a " not in history and "<script" not in history
        decoded = html.unescape(re.sub(r"<[^>]*>", " ", history))
        text = " ".join(re.sub(r"\\(.)", r"\1", decoded).replace("**", "").split())
        blocks = re.split(r"Event ID:?\s+", text)[1:]
        assert len(blocks) == 8
        for event, block, (event_id, status, revision) in zip(
            events, blocks, expected, strict=True,
        ):
            assert block.startswith(event_id + " ")
            assert re.search(rf"Event status:?\s+{status}\b", block)
            assert re.search(rf"Criteria revision:?\s+{revision}\b", block)
            outcome = (event["decision"] if event["decision"] is not None
                       else f"final_acceptance={str(event['final_acceptance']).lower()}")
            for recorded in (
                event["criterion_id"] or "Final acceptance", outcome, event["reviewer"],
                event["comment"], datetime.fromisoformat(event["timestamp"]).isoformat(),
            ):
                assert recorded in block
            if event["evidence_url"] is not None:
                assert event["evidence_url"] in block
        assert path.read_bytes() == before

    catalog = json.loads(run("-m", "scopeproof_core.cli", "history", review_id,
                             "--storage-dir", str(records)))
    historical = run("-m", "scopeproof_core.cli", "export-history", review_id,
                     "--storage-dir", str(records), "--history-position", "1",
                     "--expected-state-fingerprint", catalog["state_fingerprint"],
                     "--format", "markdown")
    history = historical.split("## Resolution History\n", 1)[1].split("\n## ", 1)[0]
    assert "Full resolution history is unavailable" in history
    assert "r1-old-accept" not in history and "r2-current-accept" not in history
    assert path.read_bytes() == before
