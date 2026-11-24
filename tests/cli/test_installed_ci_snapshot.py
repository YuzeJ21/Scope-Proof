"""Constructed CI snapshot handoff using only the installed ScopeProof package."""

import json
import os
import shutil
import subprocess
from hashlib import sha256
from pathlib import Path

import pytest


def test_installed_ci_snapshot_follows_two_builds_without_mutating_reviews(tmp_path):
    interpreter = os.environ.get("SCOPEPROOF_INSTALLED_PYTHON")
    if not interpreter:
        pytest.skip("set SCOPEPROOF_INSTALLED_PYTHON to an isolated installed-wheel interpreter")
    recipe = tmp_path / "simulate_ci_manifest.py"
    repository = Path(__file__).resolve().parents[2]
    shutil.copyfile(repository / "scripts" / recipe.name, recipe)
    scenario = tmp_path / "constructed-ci"
    storage = scenario / "reviews"

    def installed(*args, expected=0):
        result = subprocess.run(
            [interpreter, "-X", "utf8", "-I", *args], cwd=tmp_path,
            capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        return result

    installed(
        "-c",
        "from pathlib import Path; import sys, scopeproof_core; "
        "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix))",
    )
    installed(str(recipe), "--prepare-workbench", str(scenario))
    reviewed = {path: path.read_bytes() for path in storage.glob("*.json")}
    assert len(reviewed) == 2
    records = {
        json.loads(payload)["state"]["review"]["head_sha"]: path.stem
        for path, payload in reviewed.items()
    }

    def emit(review_id, manifest, output, *, expected=0):
        return installed(
            "-m", "scopeproof_core.cli", "ci-snapshot", review_id, str(manifest),
            "--storage-dir", str(storage), "--output", str(output), expected=expected,
        )

    def verify_snapshot(label, statuses):
        manifest_path = scenario / f"{label}-scopeproof-manifest.json"
        payload = manifest_path.read_bytes()
        manifest = json.loads(payload)
        head = manifest["runs"][-1]["head_sha"]
        output = tmp_path / f"{label}.html"
        emit(records[head], manifest_path, output)
        report = output.read_text(encoding="utf-8")
        assert head in report and sha256(payload).hexdigest() in report
        assert "Local file" in report
        for name, status in zip(
            ("category_filter", "row_entitlement", "csv_header"), statuses, strict=True,
        ):
            assert f"<code>{name}</code></td><td>{status}</td>" in report
        return head, report

    a_head, _ = verify_snapshot("A", ("Passed", "Passed", "Passed"))
    b_head, _ = verify_snapshot("B", ("Failed", "Explicitly skipped", "Passed"))
    assert a_head != b_head
    installed(str(recipe), "--publish-targeted", str(scenario))
    targeted_head, targeted_report = verify_snapshot("B-targeted", ("Failed", "Failed", "Passed"))
    assert targeted_head == b_head
    assert "https://ci.example.invalid/builds/B-targeted" in targeted_report

    wrong_output = tmp_path / "wrong.html"
    failure = emit(
        records[b_head], scenario / "A-scopeproof-manifest.json", wrong_output, expected=2,
    )
    assert "exact-head run" in failure.stderr
    assert not wrong_output.exists()
    assert {path: path.read_bytes() for path in storage.glob("*.json")} == reviewed
