"""Run explicitly against an installed wheel, outside the checkout, on POSIX or Windows."""

import json
import os
import shutil
import subprocess
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
