"""CONSTRUCTED portable review journey against installed packages on POSIX and Windows."""

import json
import os
import shutil
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest


def test_installed_review_transfer(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")
    recipe = tmp_path / "constructed_history.py"
    shutil.copyfile(Path(__file__).parents[1] / "historical_analysis_fixture.py", recipe)
    source = tmp_path / "source"
    target = tmp_path / "target"
    output = tmp_path / "portable.json"
    review_id = "constructed-history-only-review"

    def run(*args, expected=0):
        process = subprocess.run(
            [interpreter, "-X", "utf8", "-I", *args], cwd=tmp_path,
            capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
        )
        assert process.returncode == expected, process.stdout + process.stderr
        return process

    def cli(*args, expected=0):
        return run("-m", "scopeproof_core.cli", *args, expected=expected)

    run("-c", "from pathlib import Path; import sys, scopeproof_core, runpy; "
        "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix)); "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        f"recipe=runpy.run_path({str(recipe)!r}); "
        f"JsonReviewStore(Path({str(source)!r})).save(recipe['historical_analysis_state']())")
    original = source / f"{review_id}.json"
    original.write_bytes(original.read_bytes().replace(b"\n", b"\r\n"))
    before = original.read_bytes()
    exported = json.loads(cli("export-review", review_id, "--storage-dir", str(source),
                              "--output", str(output)).stdout)
    imported = json.loads(cli("import-review", "--input", str(output),
                              "--storage-dir", str(target)).stdout)
    assert exported["record_sha256"] == imported["record_sha256"] == sha256(before).hexdigest()
    assert original.read_bytes() == output.read_bytes() == (target / original.name).read_bytes()
    first = json.loads(cli("history", review_id, "--storage-dir", str(source)).stdout)
    second = json.loads(cli("history", review_id, "--storage-dir", str(target)).stdout)
    assert first == second
    assert second["has_active_analysis"] is False
    assert second["current_criteria_confirmed"] is False
    assert second["entries"]
    cli("import-review", "--input", str(output), "--storage-dir", str(target), expected=2)
    cli("export-review", review_id, "--storage-dir", str(source),
        "--output", str(output), expected=2)
    assert output.read_bytes() == before == (target / original.name).read_bytes()
    report = tmp_path / "report.json"
    report.write_text(json.dumps(json.loads(before)["state"]), encoding="utf-8")
    cli("import-review", "--input", str(report), "--storage-dir", str(tmp_path / "invalid"),
        expected=2)
    assert not (tmp_path / "invalid").exists()
