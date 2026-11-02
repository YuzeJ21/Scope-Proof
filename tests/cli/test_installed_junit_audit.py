"""Installed, isolated CLI recovery uses a real locked race and explicit disposable storage."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


def test_installed_junit_withdrawal_handoff_and_concurrent_stale_guard(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")
    recipe = tmp_path / "constructed_junit_audit.py"
    shutil.copy2(Path(__file__).parents[1] / "junit_audit_fixture.py", recipe)
    records = tmp_path / "explicit-records"

    def run(*args):
        result = subprocess.run(
            [interpreter, "-X", "utf8", "-I", *args], cwd=tmp_path, capture_output=True,
            text=True, encoding="utf-8", timeout=60, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    run("-c", "from pathlib import Path; import sys, runpy, apps, scopeproof_core; "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        "assert all(Path(m.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()) "
        "for m in (apps, scopeproof_core)); "
        "recipe=runpy.run_path(sys.argv[1]); "
        "JsonReviewStore(Path(sys.argv[2])).save(recipe['junit_audit_state']())",
        str(recipe), str(records))
    review_id = "constructed-junit-audit-review"
    record = records / f"{review_id}.json"
    before = json.loads(record.read_text(encoding="utf-8"))["state"]
    before_bytes = record.read_bytes()
    base = ["-m", "scopeproof_core.cli"]
    catalog = json.loads(run(*base, "junit-imports", review_id, "--storage-dir", str(records)))
    assert record.read_bytes() == before_bytes
    assert catalog["imports"][0]["status"] == "active"
    assert catalog["imports"][0]["mapped_criterion_ids"] == ["AC-01", "AC-02"]
    command = [interpreter, "-X", "utf8", "-I", *base, "withdraw-junit", review_id,
               "--storage-dir", str(records), "--import-id", "constructed-junit-import",
               "--expected-state-fingerprint", catalog["state_fingerprint"],
               "--reviewer", "CONSTRUCTED CLI 审计", "--reason", "CONSTRUCTED wrong mapping"]
    children = [subprocess.Popen(command, cwd=tmp_path, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, encoding="utf-8")
                for _ in range(2)]
    try:
        results = [(child, *child.communicate(timeout=60)) for child in children]
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
    assert sorted(child.returncode for child in children) == [0, 2], results
    success = next(out for child, out, _err in results if child.returncode == 0)
    failure = next((out, err) for child, out, err in results if child.returncode == 2)
    assert failure[0] == "" and "stale" in failure[1]
    receipt = json.loads(success)
    after = json.loads(record.read_text(encoding="utf-8"))["state"]
    event = after["bundle"]["junit_import_events"][0]
    assert receipt["event"] == event
    assert event["reviewer"] == "CONSTRUCTED CLI 审计"
    assert event["reason"] == "CONSTRUCTED wrong mapping"
    assert len(after["bundle"]["junit_import_events"]) == 1
    assert after["bundle"]["active_junit_import_ids"] == []
    assert after["bundle"]["junit_evidence_imports"] == before["bundle"]["junit_evidence_imports"]
    for payload in (before, after):
        payload["bundle"].pop("junit_import_events", None)
        payload["bundle"].pop("active_junit_import_ids", None)
    assert after == before
    saved_bytes = record.read_bytes()
    for format_name in ("json", "markdown", "html", "csv"):
        report = run(*base, "export", review_id, "--storage-dir", str(records),
                     "--format", format_name)
        assert "CONSTRUCTED CLI 审计" in report
        assert "CONSTRUCTED wrong mapping" in report
        if format_name in {"markdown", "html"}:
            assert "Withdrawn" in report
        else:
            assert "withdrawn" in report
    assert record.read_bytes() == saved_bytes
