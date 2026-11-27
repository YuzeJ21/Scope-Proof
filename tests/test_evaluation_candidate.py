"""Controlled own-package archives exercise candidate bindings without building a package."""

import io
import json
import shutil
import subprocess
import sys
import tarfile
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from scopeproof_core.build_identity import core_source_identity


@pytest.fixture
def candidate_inputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    files = {
        "scopeproof_core/__init__.py": b"value = 1\n",
        "scopeproof_core/version.py": b'__version__ = "0.2.9.dev0"\n',
        "apps/__init__.py": b"value = 2\n",
        "scripts/recipe.py": b"recipe = 3\n",
        "tests/fixture.py": b"fixture = 4\n",
        "pyproject.toml": (
            b'[tool.hatch.build.targets.wheel]\npackages = ["scopeproof_core", "apps"]\n'
            b'[tool.hatch.build.targets.wheel.force-include]\n"evals" = "evals"\n'
            b'[tool.hatch.build.targets.sdist]\n'
            b'exclude = ["/.scopeproof", "/.coverage*", "/.superpowers"]\n'
        ),
    }
    for name, data in files.items():
        path = source / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
    for args in (
        ["init", "--initial-branch=main"], ["config", "user.name", "Constructed builder"],
        ["config", "user.email", "constructed@example.invalid"], ["add", "."],
        ["commit", "-m", "Constructed source"],
    ):
        subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "scopeproof-0.2.9.dev0-py3-none-any.whl"
    metadata = b"Metadata-Version: 2.1\nName: scopeproof\nVersion: 0.2.9.dev0\n"
    with ZipFile(wheel, "w") as archive:
        for name, data in files.items():
            if name.startswith(("scopeproof_core/", "apps/")):
                archive.writestr(name, data)
        archive.writestr("scopeproof-0.2.9.dev0.dist-info/METADATA", metadata)
    sdist = dist / "scopeproof-0.2.9.dev0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for name, data in {**files, "PKG-INFO": metadata}.items():
            info = tarfile.TarInfo("scopeproof-0.2.9.dev0/" + name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    rebuilt = tmp_path / "rebuilt"
    cli = tmp_path / "cli"
    browser = tmp_path / "browser"
    for directory in (rebuilt, cli, browser / "installed-workbench0/dist"):
        directory.mkdir(parents=True)
        shutil.copyfile(wheel, directory / wheel.name)
    source_xml = tmp_path / "source.xml"
    browser_xml = tmp_path / "browser.xml"
    for path in (source_xml, browser_xml):
        path.write_text(
            '<testsuites><testsuite tests="3" failures="0" errors="0" skipped="1">'
            '<testcase name="one"/><testcase name="two"/>'
            '<testcase name="skipped"><skipped/></testcase></testsuite>'
            '</testsuites>'
        )
    probe = tmp_path / "probe.json"
    probe.write_text(json.dumps({
        "version": "0.2.9.dev0",
        "core_sha256": core_source_identity(source / "scopeproof_core").sha256,
        "wheel_sha256": sha256(wheel.read_bytes()).hexdigest(),
        "isolated_package_paths": True, "benchmark_passed": True,
        "comparison_benchmark_passed": True,
        "dependency_context": "inherited-ci-dependencies",
        "python_version": "3.12.0", "platform": "constructed-platform",
    }))
    return dict(
        source=source, dist=dist, rebuilt_dist=rebuilt, installed_wheel_dir=cli,
        browser_root=browser, source_results=source_xml, browser_results=browser_xml,
        probe=probe, output=tmp_path / "packet", source_ref="refs/heads/main",
        run_url="https://github.com/YuzeJ21/Scope-Proof/actions/runs/123/attempts/1",
        run_attempt=1,
        expected_commit=subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True,
        ).strip(),
    )


def test_packet_binds_archives_source_tests_and_installed_wheels(candidate_inputs):
    from scripts.prepare_evaluation_candidate import CandidateManifest, prepare_candidate

    args = candidate_inputs
    before = {p: p.read_bytes() for p in args["dist"].iterdir()}
    manifest = prepare_candidate(**args)
    output = args["output"]
    read_back = CandidateManifest.model_validate_json((output / "candidate.json").read_bytes())
    assert read_back == manifest
    assert manifest.source_kind == "main"
    assert manifest.workflow_event_commit == manifest.source_commit
    assert manifest.source_tests.passed == manifest.browser_tests.passed == 2
    assert manifest.source_tests.skipped == 1
    assert manifest.source_commit == subprocess.check_output(
        ["git", "-C", str(args["source"]), "rev-parse", "HEAD"], text=True,
    ).strip()
    assert manifest.source_tree == subprocess.check_output(
        ["git", "-C", str(args["source"]), "rev-parse", "HEAD^{tree}"], text=True,
    ).strip()
    for artifact in manifest.archives:
        raw = (output / artifact.name).read_bytes()
        assert artifact.sha256 == sha256(raw).hexdigest()
        assert artifact.bytes == len(raw)
        assert f"{artifact.sha256}  {artifact.name}" in (output / "SHA256SUMS.txt").read_text()
    assert {p: p.read_bytes() for p in before} == before
    assert "unpublished" in (output / "README.md").read_text().lower()
    assert set(p.name for p in output.iterdir()) == {
        "candidate.json", "README.md", "SHA256SUMS.txt",
        "scopeproof-0.2.9.dev0-py3-none-any.whl", "scopeproof-0.2.9.dev0.tar.gz",
    }


@pytest.mark.parametrize("binding", ["rebuilt_dist", "installed_wheel_dir", "browser_root"])
def test_different_tested_or_rebuilt_wheel_cannot_be_distributed(candidate_inputs, binding):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    wheel, = candidate_inputs[binding].rglob("*.whl")
    wheel.write_bytes(wheel.read_bytes() + b"different byte identity")
    with pytest.raises(ValueError, match="wheel"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


@pytest.mark.parametrize("check", ["source_results", "browser_results"])
@pytest.mark.parametrize("condition", ["failure", "empty", "inconsistent", "malformed"])
def test_failed_or_invalid_test_results_prevent_a_candidate(candidate_inputs, check, condition):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    values = {
        "failure": '<testsuite tests="1" failures="1" errors="0" skipped="0"/>',
        "empty": '<testsuite tests="0" failures="0" errors="0" skipped="0"/>',
        "inconsistent": '<testsuite tests="1" failures="0" errors="0" skipped="2"/>',
        "malformed": "<",
    }
    candidate_inputs[check].write_text(values[condition])
    with pytest.raises(ValueError):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


@pytest.mark.parametrize("field", [
    "version", "core_sha256", "wheel_sha256", "isolated_package_paths",
    "benchmark_passed", "comparison_benchmark_passed",
])
def test_source_install_probe_must_match_the_candidate(candidate_inputs, field):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    path = candidate_inputs["probe"]
    probe = json.loads(path.read_text())
    probe[field] = False if field.endswith("passed") or field == "isolated_package_paths" else (
        "0.2.8" if field == "version" else "f" * 64
    )
    path.write_text(json.dumps(probe))
    with pytest.raises(ValueError):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


def test_archive_parity_alone_does_not_prove_source_inventory(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    args = candidate_inputs
    wheel, = args["dist"].glob("*.whl")
    with ZipFile(wheel, "a") as archive:
        archive.writestr("apps/unexpected.py", b"not part of reviewed source\n")
    for key in ("rebuilt_dist", "installed_wheel_dir", "browser_root"):
        destination, = args[key].rglob("*.whl")
        shutil.copyfile(wheel, destination)
    with pytest.raises(ValueError, match="inventory"):
        prepare_candidate(**args)
    assert not args["output"].exists()


def test_pr_merge_candidate_cannot_be_relabelled_as_main(candidate_inputs):
    from scripts.prepare_evaluation_candidate import CandidateManifest, prepare_candidate

    candidate_inputs["source_ref"] = "refs/pull/123/merge"
    manifest = prepare_candidate(**candidate_inputs)
    assert manifest.source_kind == "pr-merge"
    raw = manifest.model_dump(mode="python")
    raw["source_kind"] = "main"
    with pytest.raises(ValidationError):
        CandidateManifest.model_validate(raw)


def test_existing_packet_is_never_replaced(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    prepare_candidate(**candidate_inputs)
    before = {p.name: p.read_bytes() for p in candidate_inputs["output"].iterdir()}
    with pytest.raises(FileExistsError):
        prepare_candidate(**candidate_inputs)
    assert {p.name: p.read_bytes() for p in candidate_inputs["output"].iterdir()} == before


def test_dirty_source_is_not_a_commit_bound_candidate(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    (candidate_inputs["source"] / "apps/__init__.py").write_text("changed = True\n")
    with pytest.raises(ValueError, match="clean"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


def test_source_archive_cannot_hide_an_extra_package_python_file(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    path, = candidate_inputs["dist"].glob("*.tar.gz")
    with tarfile.open(path, "r:gz") as archive:
        members = [(member, archive.extractfile(member).read()) for member in archive.getmembers()]
    with tarfile.open(path, "w:gz") as archive:
        for member, data in members:
            archive.addfile(member, io.BytesIO(data))
        extra = tarfile.TarInfo("scopeproof-0.2.9.dev0/apps/unexpected.py")
        extra.size = 4
        archive.addfile(extra, io.BytesIO(b"x=1\n"))
    with pytest.raises(ValueError, match="inventory"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


def test_failed_testcase_cannot_be_hidden_by_suite_totals(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    candidate_inputs["browser_results"].write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0">'
        '<testcase name="failed"><failure message="failure"/></testcase></testsuite>'
    )
    with pytest.raises(ValueError, match="verification"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


def test_ci_attempt_must_agree_with_its_recorded_url(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    candidate_inputs["run_attempt"] = 2
    with pytest.raises(ValueError, match="attempt"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


@pytest.mark.parametrize("invalid_attempt", [False, True])
def test_candidate_command_uses_real_archive_bindings_and_failure_exit_code(
    candidate_inputs, invalid_attempt,
):
    args = dict(candidate_inputs)
    if invalid_attempt:
        args["run_attempt"] = 2
    command = [sys.executable, "-m", "scripts.prepare_evaluation_candidate"]
    for name, value in args.items():
        command.extend(["--" + name.replace("_", "-"), str(value)])
    result = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if invalid_attempt:
        assert result.returncode == 2
        assert "Candidate preparation failed:" in result.stderr
        assert not args["output"].exists()
    else:
        assert result.returncode == 0, result.stderr
        printed = json.loads(result.stdout)
        recorded = json.loads((args["output"] / "candidate.json").read_text())
        assert printed["source_commit"] == recorded["source_commit"]
        assert printed["archives"] == recorded["archives"]
        assert printed["source_kind"] == "main"


def test_foreign_top_level_python_cannot_hide_in_parity_matching_wheels(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    args = candidate_inputs
    wheel, = args["dist"].glob("*.whl")
    with ZipFile(wheel, "a") as archive:
        archive.writestr("foreign_package/__init__.py", b"not_reviewed = True\n")
    for key in ("rebuilt_dist", "installed_wheel_dir", "browser_root"):
        destination, = args[key].rglob("*.whl")
        shutil.copyfile(wheel, destination)
    probe = json.loads(args["probe"].read_text())
    probe["wheel_sha256"] = sha256(wheel.read_bytes()).hexdigest()
    args["probe"].write_text(json.dumps(probe))
    with pytest.raises(ValueError, match="inventory"):
        prepare_candidate(**args)
    assert not args["output"].exists()


@pytest.mark.parametrize("changed", ["scripts/recipe.py", "tests/fixture.py"])
def test_source_archive_must_preserve_tracked_python_outside_wheel_packages(
    candidate_inputs, changed,
):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    path, = candidate_inputs["dist"].glob("*.tar.gz")
    with tarfile.open(path, "r:gz") as archive:
        members = [(member.name, archive.extractfile(member).read())
                   for member in archive.getmembers()]
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members:
            if name.endswith("/" + changed):
                data = b"changed_without_review = True\n"
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    with pytest.raises(ValueError, match="inventory"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


@pytest.mark.parametrize("structure", ["nested_suite", "foreign_root", "case_outside_suite",
                                      "outcome_in_properties", "nested_case"])
def test_unsupported_junit_structure_cannot_hide_verification_failures(candidate_inputs, structure):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    passing = '<testcase name="passing"/>'
    failed = '<testcase name="failed"><failure message="failed"/></testcase>'
    attrs = 'tests="1" failures="0" errors="0" skipped="0"'
    if structure == "nested_suite":
        payload = f'<testsuite {attrs}>{passing}<testsuite>{failed}</testsuite></testsuite>'
    elif structure == "foreign_root":
        payload = f'<other><testsuite {attrs}>{passing}</testsuite></other>'
    elif structure == "case_outside_suite":
        payload = f'<testsuites>{failed}<testsuite {attrs}>{passing}</testsuite></testsuites>'
    elif structure == "outcome_in_properties":
        payload = (f'<testsuite {attrs}><testcase><properties><failure/>'
                   '</properties></testcase></testsuite>')
    else:
        payload = f'<testsuite {attrs}><testcase>{failed}</testcase></testsuite>'
    candidate_inputs["browser_results"].write_text(payload)
    with pytest.raises(ValueError, match="verification"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


def test_every_numbered_browser_fixture_requires_a_wheel(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    (candidate_inputs["browser_root"] / "installed-workbench1/dist").mkdir(parents=True)
    with pytest.raises(ValueError):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()


def test_checkout_must_match_the_trusted_workflow_event_commit(candidate_inputs):
    from scripts.prepare_evaluation_candidate import prepare_candidate

    source = candidate_inputs["source"]
    subprocess.run(["git", "-C", str(source), "switch", "-c", "different-checkout"],
                   capture_output=True, check=True)
    (source / "different.txt").write_text("A different event's checkout")
    subprocess.run(["git", "-C", str(source), "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-m", "Different checkout"],
                   capture_output=True, check=True)
    with pytest.raises(ValueError, match=r"workflow.*commit"):
        prepare_candidate(**candidate_inputs)
    assert not candidate_inputs["output"].exists()
