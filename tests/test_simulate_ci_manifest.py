"""Verify that the constructed pipeline publishes usable exact-build CI artifacts."""

from __future__ import annotations

import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from scopeproof_core.criteria.confirmation import validate_criteria_source_confirmation
from scopeproof_core.criteria.document import NormalizedCriteriaDocument
from scopeproof_core.reviews.ci_status import load_ci_status_manifest
from scopeproof_core.schemas.models import CriteriaSourceProvenance, PullRequestSnapshot
from scripts import simulate_ci_manifest
from scripts.simulate_ci_manifest import SimulatedRun, build_manifest, simulate

_ROOT = Path(__file__).resolve().parents[1]
_A_HEAD = "2a95b61bcbbf2f3a07bc0ee8bde09dd4c58cb942"
_B_HEAD = "aac2fb06cb315a392e91e432f3d862607c7e9856"
_CRITERIA_DIGEST = "6d91bc9a2bd6f7a2ae8df11b71740a4d2262246e008b98fafad440083b5ada89"
_EXPECTED_TESTS = {
    "AC-01": ["category_filter"],
    "AC-02": ["row_entitlement"],
    "AC-03": ["csv_header"],
}
_RUNS = {
    "A": (_A_HEAD, dict.fromkeys(("category_filter", "row_entitlement", "csv_header"), "passed")),
    "B": (
        _B_HEAD,
        {"category_filter": "failed", "row_entitlement": "skipped", "csv_header": "passed"},
    ),
    "B-targeted": (
        _B_HEAD,
        {"category_filter": "skipped", "row_entitlement": "failed", "csv_header": "skipped"},
    ),
}
# Digests from the verified PR #293 replay. Its independently written manifests are the oracle.
_ORIGINAL_DIGESTS = {
    "A-ci.json": "983e0a1c1addaabccd1f6f318c52db47be4a34c6e448b6d556991ef8070ceeba",
    "B-ci.json": "0807f4aee54414567887045e8e62009029309e75b0d1d1bb9fc282640b4680a9",
    "B-targeted-ci.json": "aae1fa152f3bea3e5537b9b75d642bca46c2fa15178c62fb72190c6b5a506549",
    "ticket.md": "82df9b09c59461d85b77bd17e7d71ffe7ecd116baffd6c82088ae38eaff49a3a",
    "build-A-to-B.diff": "ffff342668180717423c5a747375d56e5fdea44bf7b414f9535d617c5fda4b7a",
    "A-scopeproof-manifest.json": (
        "434a1346dc21e7217bbcdc7796a059e28112f91dde25592522e3288b645c24bf"
    ),
    "B-scopeproof-manifest.json": (
        "4a8a7b76dd025858e32652a998acf71cc4985108d9d3049e0adda96acc567ac9"
    ),
    "B-targeted-scopeproof-manifest.json": (
        "95fdca9e60ad7f9148c2153e638515dbe7f533fb62f9004608cae945a7044d59"
    ),
}


def _confirmation(output: Path) -> CriteriaSourceProvenance:
    source = (output / "ticket-requirements.txt").read_bytes().decode("utf-8")
    document = NormalizedCriteriaDocument.model_validate_json(
        (output / "criteria.json").read_bytes(),
    )
    return validate_criteria_source_confirmation(
        output / "confirmation.json",
        source_text=source,
        criteria=document.criteria_for_source(source),
    )


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("simulated-ci") / "generated"
    simulate(output)
    return output


def test_cli_automatically_writes_reproducible_manifests(generated: Path, tmp_path: Path) -> None:
    repeat = tmp_path / "repeat"
    result = subprocess.run(
        [sys.executable, "-m", "scripts.simulate_ci_manifest", str(repeat)],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for name, original_digest in _ORIGINAL_DIGESTS.items():
        payload = (generated / name).read_bytes()
        assert (repeat / name).read_bytes() == payload, name
        assert sha256(payload).hexdigest() == original_digest, name

    assert _confirmation(generated).normalized_criteria_sha256 == _CRITERIA_DIGEST
    assert _confirmation(repeat).normalized_criteria_sha256 == _CRITERIA_DIGEST
    expected_run_ids = []
    for label, (head, _) in _RUNS.items():
        expected_run_ids.append(label)
        manifest = load_ci_status_manifest(
            (repeat / f"{label}-scopeproof-manifest.json").read_bytes(),
        )
        assert manifest.repository == "constructed/export"
        assert manifest.pr_number == 1
        assert manifest.criteria_sha256 == _CRITERIA_DIGEST
        assert manifest.expected_tests == _EXPECTED_TESTS
        assert [run.run_id for run in manifest.runs] == expected_run_ids
        for run in manifest.runs:
            assert (run.head_sha, run.outcomes) == _RUNS[run.run_id]
            assert run.source_url == f"https://ci.example.invalid/builds/{run.run_id}"
        if label != "B-targeted":
            snapshot = PullRequestSnapshot.model_validate_json(
                (repeat / f"{label}-fixture.json").read_bytes(),
            )
            assert (snapshot.repository, snapshot.pr_number, snapshot.head_sha) == (
                manifest.repository, manifest.pr_number, head,
            )


def test_simulation_refuses_to_touch_existing_output_directory(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    prior = existing / "A-scopeproof-manifest.json"
    prior.write_bytes(b"previous evidence")
    with pytest.raises((FileExistsError, ValueError)):
        simulate(existing)
    assert list(existing.iterdir()) == [prior]
    assert prior.read_bytes() == b"previous evidence"


def test_constructed_access_fix_changes_same_head_targeted_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        simulate_ci_manifest,
        "_QUERY_B",
        """def select_export_rows(db, analyst, category):
    return db.execute(
        "SELECT id, category, amount FROM records WHERE analyst = ? ORDER BY id", (analyst,),
    ).fetchall()
""",
    )
    output = tmp_path / "access-fix"
    simulate(output)
    manifest = load_ci_status_manifest(
        (output / "B-targeted-scopeproof-manifest.json").read_bytes(),
    )
    build_a, build_b, targeted = manifest.runs
    assert build_a.head_sha == _A_HEAD
    assert build_b.head_sha != _B_HEAD
    assert build_b.head_sha == targeted.head_sha
    assert build_b.outcomes == _RUNS["B"][1]
    assert targeted.outcomes == _RUNS["B-targeted"][1] | {"row_entitlement": "passed"}


def test_missing_result_does_not_become_an_explicit_skip(generated: Path) -> None:
    run = SimulatedRun.model_validate_json((generated / "B-targeted-ci.json").read_bytes())
    sparse_run = run.model_copy(update={"checks": run.checks[1:]})
    manifest = load_ci_status_manifest(build_manifest([sparse_run], _confirmation(generated)))
    assert manifest.expected_tests == _EXPECTED_TESTS
    assert manifest.runs[0].outcomes == {"row_entitlement": "failed", "csv_header": "skipped"}


@pytest.mark.parametrize("corruption", ["duplicate check", "wrong criterion", "unknown test"])
def test_incoherent_check_records_are_rejected(generated: Path, corruption: str) -> None:
    run = SimulatedRun.model_validate_json((generated / "B-ci.json").read_bytes())
    check = run.checks[0]
    if corruption == "unknown test":
        check = check.model_copy(update={"test": "unplanned_test"})
    elif corruption == "wrong criterion":
        check = check.model_copy(update={"criterion": "AC-02"})
    remaining = run.checks if corruption == "duplicate check" else run.checks[1:]
    invalid = run.model_copy(update={"checks": [*remaining, check]})
    with pytest.raises(ValueError):
        build_manifest([invalid], _confirmation(generated))
