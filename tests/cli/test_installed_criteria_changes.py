"""Trusted CONSTRUCTED installed-wheel requirements handoff, outside the checkout."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


def test_installed_saved_requirements_handoff(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")
    recipe = tmp_path / "constructed_history.py"
    shutil.copyfile(Path(__file__).parents[1] / "historical_analysis_fixture.py", recipe)
    records = tmp_path / "records"
    current_source = "  CONSTRUCTED pending source\r\n\tunchanged whitespace  \n"

    def run(*args, expected=0):
        result = subprocess.run(
            [interpreter, "-I", *args], cwd=tmp_path, capture_output=True, text=True,
            encoding="utf-8", timeout=60, check=False,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        return result

    run("-c", "from pathlib import Path; import sys, scopeproof_core, runpy; "
        "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix)); "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        "from scopeproof_core.gates.evaluator import evaluate_gate; "
        f"recipe=runpy.run_path({str(recipe)!r}); state=recipe['historical_analysis_state'](); "
        # Construct valid hypothetical legacy input before first save, never rewrite real history.
        "old=state.analysis_history[0]; old.review.criteria_source_provenance=None; "
        "old.reviewer_selected_references=[]; old.selected_reference_events=[]; "
        "old.gate=evaluate_gate(old.review,old.criteria,old.findings,old.resolutions,"
        "old.evidence,old.file_scope_decisions); "
        f"state.criteria_revision.source_text={current_source!r}; "
        f"JsonReviewStore(Path({str(records)!r})).save(state)")
    review_id = "constructed-history-only-review"
    record = records / f"{review_id}.json"
    before = record.read_bytes()
    catalog = json.loads(run("-m", "scopeproof_core.cli", "history", review_id,
                             "--storage-dir", str(records)).stdout)
    assert not catalog["has_active_analysis"] and not catalog["current_criteria_confirmed"]
    args = ["-m", "scopeproof_core.cli", "export-criteria-changes", review_id,
            "--history-position", "1", "--expected-state-fingerprint", catalog["state_fingerprint"],
            "--storage-dir", str(records)]
    report = json.loads(run(*args).stdout)
    assert report["report_kind"] == "scopeproof_criteria_revision_comparison"
    assert report["previous"]["revision_number"] == 1
    assert report["current"]["revision_number"] == 3
    assert report["previous"]["source_text"] == "CONSTRUCTED export CSV"
    assert report["current"]["source_text"] == current_source
    assert report["previous"]["source_provenance"] is None
    assert report["current"]["source_provenance"] is None
    assert report["current"]["confirmed"] is False
    assert report["selection"]["historical"]["state_fingerprint"] == catalog["state_fingerprint"]
    assert (report["selection"]["historical"]["analysis_fingerprint"]
            == catalog["entries"][0]["analysis_fingerprint"])
    assert "gate" not in report and "evidence" not in report and "resolutions" not in report
    target = tmp_path / "criteria-changes.md"
    assert run(*args, "--format", "markdown", "--output", str(target)).stdout == ""
    markdown = target.read_text(encoding="utf-8")
    assert markdown.startswith("# ScopeProof Criteria Revision Changes\n")
    assert "Unconfirmed" in markdown and "provenance remains unknown" in markdown
    assert run(*args, "--output", str(target), expected=2).stdout == ""
    assert target.read_text(encoding="utf-8") == markdown
    acceptance_args = args.copy()
    acceptance_args[2] = "export-history"
    assert run(*acceptance_args, expected=2).stdout == ""
    assert record.read_bytes() == before
    run("-c", "from pathlib import Path; "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        f"store=JsonReviewStore(Path({str(records)!r})); state=store.load({review_id!r}); "
        "state.criteria_revision.source_text += ' CONSTRUCTED saved change'; store.save(state)")
    stale = run(*args, expected=2)
    assert stale.stdout == "" and "changed" in stale.stderr
