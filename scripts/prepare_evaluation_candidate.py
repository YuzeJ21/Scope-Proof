"""Retain an unpublished own-package candidate bound to completed CI observations."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import tarfile
import tomllib
from email.parser import Parser
from fnmatch import fnmatchcase
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scopeproof_core.build_identity import core_source_identity
from scopeproof_core.version import __version__

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Commit = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Archive(_StrictModel):
    name: str
    bytes: int = Field(gt=0)
    sha256: Digest


class TestSummary(_StrictModel):
    tests: int = Field(gt=0)
    passed: int = Field(gt=0)
    skipped: int = Field(ge=0)

    @model_validator(mode="after")
    def totals_match(self) -> TestSummary:
        if self.tests != self.passed + self.skipped:
            raise ValueError("test totals are inconsistent")
        return self


class InstallationProbe(_StrictModel):
    version: str
    core_sha256: Digest
    wheel_sha256: Digest
    isolated_package_paths: Literal[True]
    benchmark_passed: Literal[True]
    comparison_benchmark_passed: Literal[True]
    dependency_context: Literal["inherited-ci-dependencies"]
    python_version: str
    platform: str


class CandidateManifest(_StrictModel):
    schema_version: Literal["scopeproof-evaluation-candidate-v1"] = (
        "scopeproof-evaluation-candidate-v1"
    )
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(?:\.dev[0-9]+)?$")
    source_ref: str = Field(pattern=r"^(refs/heads/main|refs/pull/[0-9]+/merge)$")
    source_kind: Literal["main", "pr-merge"]
    source_commit: Commit
    workflow_event_commit: Commit
    source_tree: Commit
    core_sha256: Digest
    run_url: str = Field(
        pattern=r"^https://github\.com/YuzeJ21/Scope-Proof/actions/runs/[0-9]+/attempts/[0-9]+$",
    )
    run_attempt: int = Field(ge=1)
    archives: tuple[Archive, Archive]
    rebuilt_wheel_sha256: Digest
    installed_cli_wheel_sha256: Digest
    browser_wheel_sha256: Annotated[tuple[Digest, ...], Field(min_length=1)]
    source_tests: TestSummary
    browser_tests: TestSummary
    source_installation: InstallationProbe
    publication: Literal["unpublished"] = "unpublished"
    evidence_boundary: Literal["constructed automated engineering evidence"] = (
        "constructed automated engineering evidence"
    )

    @model_validator(mode="after")
    def bindings_match(self) -> CandidateManifest:
        expected_kind = "main" if self.source_ref == "refs/heads/main" else "pr-merge"
        if self.source_kind != expected_kind:
            raise ValueError("source kind differs from its workflow ref")
        if not self.run_url.endswith(f"/attempts/{self.run_attempt}"):
            raise ValueError("CI attempt differs from its recorded URL")
        if self.source_commit != self.workflow_event_commit:
            raise ValueError("checkout differs from the workflow event commit")
        wheel, sdist = self.archives
        if (wheel.name, sdist.name) != (
            f"scopeproof-{self.version}-py3-none-any.whl", f"scopeproof-{self.version}.tar.gz",
        ):
            raise ValueError("archive filenames differ from the candidate version")
        if any(value != wheel.sha256 for value in (
            self.rebuilt_wheel_sha256, self.installed_cli_wheel_sha256,
            *self.browser_wheel_sha256, self.source_installation.wheel_sha256,
        )):
            raise ValueError("candidate and tested wheel byte identities differ")
        if (
            self.source_installation.version != self.version
            or self.source_installation.core_sha256 != self.core_sha256
        ):
            raise ValueError("source installation differs from candidate identity")
        return self


def _git(source: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("candidate input must be a regular file")
    return path.read_bytes()


def _one(directory: Path, pattern: str) -> Path:
    paths = sorted(directory.glob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected one {pattern} candidate input")
    return paths[0]


def _test_results(path: Path) -> TestSummary:
    try:
        root = ElementTree.fromstring(_read(path))
        if root.tag == "testsuite":
            suites = [root]
        elif root.tag == "testsuites" and all(child.tag == "testsuite" for child in root):
            suites = list(root)
        else:
            raise ValueError("unsupported pytest verification root")
        if len(suites) != 1:
            raise ValueError("expected one pytest result suite")
        suite = suites[0]
        for child in suite:
            if child.tag == "testcase":
                if any(node.tag not in {
                    "properties", "failure", "error", "skipped", "system-out", "system-err",
                } for node in child):
                    raise ValueError("unsupported pytest verification case structure")
                if len(child.findall("skipped")) > 1:
                    raise ValueError("duplicate pytest verification outcome")
                leaves = list(child)
            elif child.tag in {"properties", "system-out", "system-err"}:
                leaves = [child]
            else:
                raise ValueError("unsupported pytest verification suite structure")
            for node in leaves:
                if node.tag == "properties":
                    if any(prop.tag != "property" or len(prop) for prop in node):
                        raise ValueError("unsupported pytest verification properties")
                elif len(node):
                    raise ValueError("unsupported nested pytest verification elements")
        values = {key: int(suites[0].attrib[key]) for key in (
            "tests", "failures", "errors", "skipped",
        )}
        if values["failures"] != 0 or values["errors"] != 0:
            raise ValueError("candidate verification did not pass")
        cases = suites[0].findall("testcase")
        if (
            len(cases) != values["tests"]
            or sum(case.find("skipped") is not None for case in cases) != values["skipped"]
            or any(case.find("failure") is not None or case.find("error") is not None
                   for case in cases)
        ):
            raise ValueError("pytest verification results are inconsistent")
        return TestSummary(
            tests=values["tests"], skipped=values["skipped"],
            passed=values["tests"] - values["skipped"],
        )
    except (ElementTree.ParseError, KeyError) as error:
        raise ValueError("invalid pytest verification results") from error


def _source_inventory(source: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    """Bind all Python to Git and this repository's declared Hatch selection."""
    config = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))
    targets = config["tool"]["hatch"]["build"]["targets"]
    exclusions = targets["sdist"]["exclude"]
    if (
        targets["wheel"]["packages"] != ["scopeproof_core", "apps"]
        or targets["wheel"]["force-include"].get("evals") != "evals"
        or set(exclusions) != {"/.scopeproof", "/.coverage*", "/.superpowers"}
    ):
        raise ValueError("candidate inventory needs review for changed Hatch selection")
    tracked = [name for name in _git(source, "ls-files", "-z", "--", "*.py").split("\0")
               if name]
    inventory = {name: _read(source / name) for name in tracked}
    wheel = {name: raw for name, raw in inventory.items()
             if name.startswith(("scopeproof_core/", "apps/", "evals/"))}
    sdist = {}
    for name, raw in inventory.items():
        components = [name, *(str(parent) for parent in Path(name).parents)]
        if not any(fnmatchcase(component, pattern.lstrip("/"))
                   for component in components for pattern in exclusions):
            sdist[name] = raw
    return wheel, sdist


def _validate_archives(
    wheel: bytes, sdist: bytes, wheel_source: dict[str, bytes],
    sdist_source: dict[str, bytes], version: str,
) -> None:
    try:
        with ZipFile(io.BytesIO(wheel)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("duplicate wheel inventory entries")
            wheel_inventory = {name: archive.read(name) for name in names
                               if name.endswith(".py")}
            metadata = archive.read(f"scopeproof-{version}.dist-info/METADATA").decode("utf-8")
        with tarfile.open(fileobj=io.BytesIO(sdist), mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) != len({member.name for member in members}):
                raise ValueError("duplicate source inventory entries")
            if any(member.issym() or member.islnk() for member in members):
                raise ValueError("source archive inventory contains links")
            prefix = f"scopeproof-{version}/"
            sdist_inventory = {}
            for member in members:
                if member.isfile() and not member.name.startswith(prefix):
                    raise ValueError("source archive inventory has an unexpected root")
                name = member.name.removeprefix(prefix)
                if member.isfile() and name.endswith(".py"):
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ValueError("source archive Python inventory is unreadable")
                    sdist_inventory[name] = stream.read()
            stream = archive.extractfile(prefix + "PKG-INFO")
            if stream is None:
                raise ValueError("source archive metadata is unavailable")
            source_metadata = stream.read().decode("utf-8")
    except (BadZipFile, tarfile.TarError, KeyError, UnicodeError) as error:
        raise ValueError("invalid candidate archive inventory") from error
    if wheel_inventory != wheel_source or sdist_inventory != sdist_source:
        raise ValueError("candidate Python inventory differs from source")
    for text in (metadata, source_metadata):
        parsed = Parser().parsestr(text)
        if parsed.get("Name") != "scopeproof" or parsed.get("Version") != version:
            raise ValueError("candidate archive metadata differs from source version")


def prepare_candidate(
    *, source: Path, dist: Path, rebuilt_dist: Path, installed_wheel_dir: Path,
    browser_root: Path, source_results: Path, browser_results: Path, probe: Path,
    output: Path, source_ref: str, run_url: str, run_attempt: int, expected_commit: str,
) -> CandidateManifest:
    """Validate every binding before creating a new, explicitly unpublished packet."""
    if output.exists() or output.is_symlink():
        raise FileExistsError("candidate output already exists")
    if _git(source, "status", "--porcelain"):
        raise ValueError("candidate requires a clean source checkout")
    observed_commit = _git(source, "rev-parse", "HEAD")
    if observed_commit != expected_commit:
        raise ValueError("checkout differs from the workflow event commit")
    wheel, sdist = _one(dist, "*.whl"), _one(dist, "*.tar.gz")
    wheel_raw, sdist_raw = _read(wheel), _read(sdist)
    wheel_source, sdist_source = _source_inventory(source)
    _validate_archives(wheel_raw, sdist_raw, wheel_source, sdist_source, __version__)
    browser_directories = sorted(path for path in browser_root.glob("installed-workbench*")
                                 if re.fullmatch(r"installed-workbench[0-9]+", path.name))
    if not browser_directories:
        raise ValueError("candidate requires tested browser wheels")
    if any(path.is_symlink() or not path.is_dir() for path in browser_directories):
        raise ValueError("browser wheel fixture directory is unavailable")
    browser_wheels = [_one(path / "dist", "*.whl") for path in browser_directories]
    manifest = CandidateManifest(
        version=__version__, source_ref=source_ref,
        source_kind="main" if source_ref == "refs/heads/main" else "pr-merge",
        source_commit=observed_commit, workflow_event_commit=expected_commit,
        source_tree=_git(source, "rev-parse", observed_commit + "^{tree}"),
        core_sha256=core_source_identity(source / "scopeproof_core").sha256,
        run_url=run_url, run_attempt=run_attempt,
        archives=(
            Archive(name=wheel.name, bytes=len(wheel_raw), sha256=sha256(wheel_raw).hexdigest()),
            Archive(name=sdist.name, bytes=len(sdist_raw), sha256=sha256(sdist_raw).hexdigest()),
        ),
        rebuilt_wheel_sha256=sha256(_read(_one(rebuilt_dist, "*.whl"))).hexdigest(),
        installed_cli_wheel_sha256=sha256(_read(_one(installed_wheel_dir, "*.whl"))).hexdigest(),
        browser_wheel_sha256=tuple(sha256(_read(path)).hexdigest() for path in browser_wheels),
        source_tests=_test_results(source_results), browser_tests=_test_results(browser_results),
        source_installation=InstallationProbe.model_validate_json(_read(probe)),
    )
    serialized = manifest.model_dump_json(indent=2) + "\n"
    CandidateManifest.model_validate_json(serialized)
    output.mkdir(parents=True, exist_ok=False)
    (output / wheel.name).write_bytes(wheel_raw)
    (output / sdist.name).write_bytes(sdist_raw)
    (output / "candidate.json").write_text(serialized, encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text("".join(
        f"{item.sha256}  {item.name}\n" for item in manifest.archives
    ), encoding="utf-8")
    (output / "README.md").write_text(
        f"# ScopeProof {manifest.version} — unpublished evaluation candidate\n\n"
        f"Source: `{manifest.source_commit}` ({manifest.source_kind}).\n"
        f"CI observations: {manifest.run_url}\n\n"
        "Verify both archives against SHA256SUMS.txt before installation. Install the wheel "
        "in a new virtual environment using `python -m pip install ./scopeproof-*.whl`. "
        "See candidate.json for exact package, test and source-install bindings.\n\n"
        "PR merge previews are not reviewed-main candidates; use the separately rebuilt "
        "main artifact for a distribution decision. CI artifacts are retained for 90 days.\n\n"
        "This is constructed engineering evidence, not signed provenance, customer validation "
        "or a beta. The source-install probe inherits tested CI runtime dependencies; browser "
        "journeys use their own fresh environments. Current/future dependency combinations "
        "are not universally verified. Public v0.2.8 remains current. No publication, tag or "
        "deployment follows from this packet; final-version packages require a fresh build.\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "source", "dist", "rebuilt-dist", "installed-wheel-dir", "browser-root",
        "source-results", "browser-results", "probe", "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    try:
        manifest = prepare_candidate(**vars(args))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Candidate preparation failed: {error}\n")
    print(json.dumps({
        "source_commit": manifest.source_commit, "source_kind": manifest.source_kind,
        "output": str(args.output), "archives": [a.model_dump() for a in manifest.archives],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
