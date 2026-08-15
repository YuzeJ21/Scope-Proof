import json
import re
import subprocess
import tomllib
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from struct import unpack
from typing import Literal
from urllib.parse import urlsplit

import pytest
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from scopeproof_core.evals.r002_models import (
    R002_PUBLISHED_PRE_PROVENANCE_RESULT_SHA256,
    R002_SOURCE,
    canonical_sha256,
    load_confirmed_criteria,
    load_confirmed_labels,
    load_r002_benchmark_result,
    load_source_manifest,
)
from scopeproof_core.reviews.comparison import EvidenceChangeKind
from scopeproof_core.version import __version__

PUBLIC_RELEASE_VERSION = "0.2.3"
PUBLIC_RELEASE_TAG = "v0.2.3"
DEVELOPMENT_VERSION = "0.2.4.dev0"
PUBLIC_RELEASE_WHEEL_FILENAME = "scopeproof-0.2.3-py3-none-any.whl"
PUBLIC_RELEASE_DOWNLOAD_ROOT = (
    "https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.2.3"
)
PUBLIC_RELEASES_INDEX = "https://github.com/YuzeJ21/Scope-Proof/releases"
PR183_SOURCE_MERGE_SHA = "cd362a85a558645a0f56d6540f6bf035e5821809"
PR183_EXACT_MAIN_RUN_IDS = ("30847416893", "30847415556", "30847417705")
PR184_RELEASE_MERGE_SHA = "448c42758ea139bf9203cbf1bb04b02b02ae412c"
PR184_EXACT_MAIN_RUN_IDS = ("30854382641", "30854382413", "30854382659")
POST_PR193_RESULTING_MAIN_SHA = "432371c4faec0b790f70fec32b4d3fc4d5132cfa"
PR193_EXACT_HEAD_SHA = "8bb407079a0ff7098d2fc18af3d75b216725df2e"
PR193_EXACT_BASE_SHA = "9426e8714ffd2c3742bb074ae26fc788f1049c63"
PR193_RESULTING_MAIN_CI_RUN_ID = "31704668247"
PR193_RESULTING_MAIN_CODEQL_RUN_ID = "31704666031"
PR193_RESULTING_MAIN_PAGES_RUN_ID = "31704668164"
GITHUB_ACTIONS_RUN_ROOT = "https://github.com/YuzeJ21/Scope-Proof/actions/runs"


def test_r002_packaged_inputs_are_redacted_and_strict() -> None:
    root = Path("evals/r002")
    expected = {"source_manifest.json", "criteria.json", "candidate_labels.json"}
    assert not root.is_symlink()
    assert root.is_dir()
    entries = tuple(root.rglob("*"))
    assert all(path.is_file() and not path.is_symlink() for path in entries)
    assert all(path.parent == root for path in entries)
    assert {path.relative_to(root).as_posix() for path in entries} == expected
    source = load_source_manifest(root / "source_manifest.json")
    criteria = load_confirmed_criteria(root / "criteria.json", canonical_sha256(source))
    labels = load_confirmed_labels(
        root / "candidate_labels.json",
        canonical_sha256(source),
        canonical_sha256(criteria),
    )
    assert labels.benchmark_owner_confirmed is True
    forbidden_keys = {
        "problem_statement",
        "patch",
        "test_patch",
        "hints_text",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "source_text",
        "excerpt",
        "context_excerpt",
    }
    for path in entries:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stack = [payload]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                assert forbidden_keys.isdisjoint(value)
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)


def test_r002_tracked_outputs_exclude_scopeproof_authored_redaction_sentinels() -> None:
    sentinels = json.loads(
        Path("tests/fixtures/r002_redaction/sentinels.json").read_text(encoding="utf-8")
    )
    assert isinstance(sentinels, dict)
    assert sentinels
    values = tuple(sentinels.values())
    assert all(isinstance(value, str) and value for value in values)

    tracked = [
        *sorted(Path("evals/r002").glob("*.json")),
        *sorted(Path("docs/research/r002-swebench-verified").glob("*")),
    ]
    assert tracked
    for path in tracked:
        text = path.read_text(encoding="utf-8")
        assert all(value not in text for value in values)


def test_r002_engineering_result_is_linked_without_advancing_product_stages() -> None:
    result_path = Path("docs/research/r002-swebench-verified/result.json")
    summary_path = Path("docs/research/r002-swebench-verified/summary.md")
    raw_result = result_path.read_bytes()
    assert sha256(raw_result).hexdigest() == R002_PUBLISHED_PRE_PROVENANCE_RESULT_SHA256
    result = load_r002_benchmark_result(result_path)
    summary = summary_path.read_text(encoding="utf-8")
    public_link = "docs/research/r002-swebench-verified/summary.md"
    development_link = "research/r002-swebench-verified/summary.md"

    assert result.executed_case_count == 20
    assert result.failed_case_count == 0
    assert result.skipped_case_count == 0
    assert result.unexpected_ready_count == 0
    assert result.normalized_rerun_mismatches == 0
    assert result.target_repository_code_executed is False
    assert result.does_not_advance_stage_1 is True
    assert "20 historical public PRs" in summary
    assert "12 repositories" in summary
    assert "No target-repository code was executed." in summary
    assert "does not measure customer precision" in summary

    readme = Path("README.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    environment = Path("docs/development-environment.md").read_text(encoding="utf-8")
    assert public_link in readme
    assert public_link in changelog
    assert development_link in environment
    assert "R-002 is engineering evidence only" in roadmap
    assert "contribute zero genuine Alpha reviews" in roadmap
    assert "owner-led engineering work but not customer" in " ".join(roadmap.split())


def test_r002_module_commands_are_packaged_but_not_live_ci() -> None:
    module = Path("scopeproof_core/evals/r002_swebench.py")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert module.is_file() and not module.is_symlink()
    assert (
        project["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]["evals"] == "evals"
    )
    assert "python -m scopeproof_core.evals.r002_swebench --help" in workflow
    assert "python -m scopeproof_core.evals.r002_swebench prepare" not in workflow
    assert "python -m scopeproof_core.evals.r002_swebench annotate" not in workflow
    assert "python -m scopeproof_core.evals.r002_swebench run" not in workflow
    assert "python -m pip install -e '.[dev,research]'" in workflow
    assert "python -m uv sync --extra dev --extra research --locked" in workflow


def test_r002_source_manifest_is_exact_and_redacted() -> None:
    path = Path("evals/r002/source_manifest.json")
    manifest = load_source_manifest(path)

    assert manifest.source.model_dump(mode="json") == R002_SOURCE
    assert [case.case_id for case in manifest.cases] == [
        f"R002-{number:03d}" for number in range(1, 21)
    ]
    assert len({case.repository for case in manifest.cases}) == 12
    raw = path.read_text(encoding="utf-8")
    for forbidden_key in (
        '"problem_statement":',
        '"patch":',
        '"test_patch":',
        '"hints_text":',
        '"FAIL_TO_PASS":',
        '"PASS_TO_PASS":',
    ):
        assert forbidden_key not in raw


def _mp4_duration_seconds(path: Path) -> float:
    data = path.read_bytes()
    marker = data.find(b"mvhd")
    assert marker >= 0, "MP4 must contain an mvhd movie header"
    version = data[marker + 4]
    if version == 0:
        timescale = unpack(">I", data[marker + 16 : marker + 20])[0]
        duration = unpack(">I", data[marker + 20 : marker + 24])[0]
    elif version == 1:
        timescale = unpack(">I", data[marker + 24 : marker + 28])[0]
        duration = unpack(">Q", data[marker + 28 : marker + 36])[0]
    else:
        raise AssertionError(f"unsupported mvhd version: {version}")
    return duration / timescale


class _PublicSiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms = 0
        self.links: list[str] = []
        self.remote_scripts: list[str] = []
        self.video_tracks: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "form":
            self.forms += 1
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "script" and str(values.get("src", "")).startswith(("http://", "https://")):
            self.remote_scripts.append(str(values["src"]))
        if tag == "track":
            self.video_tracks.append(values)


def test_readme_states_product_limits() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "does not replace QA" in readme
    assert "No paid LLM API" in readme
    assert "deliberately constructed demo" in readme
    assert "public repositories only" in readme


def test_core_never_imports_streamlit() -> None:
    imports = [
        path
        for path in Path("scopeproof_core").rglob("*.py")
        if "import streamlit" in path.read_text(encoding="utf-8")
    ]
    assert imports == []


def test_project_has_no_paid_llm_runtime_dependency() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependencies = " ".join(project["dependencies"]).lower()
    assert "openai" not in dependencies
    assert "anthropic" not in dependencies


def test_public_docs_state_evaluation_only_use_policy() -> None:
    policy = Path("USE_POLICY.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert "intentionally published without an open-source license" in policy
    assert "evaluation and review only" in policy
    assert "No additional permission is granted" in policy
    assert "GitHub Terms of Service" in policy
    assert "applicable law" in policy
    assert "warranty" in policy.lower()
    assert "correctness claim" in policy
    assert "service commitment" in policy
    assert "support obligation" in policy
    assert "repository owner" in policy
    assert "[evaluation-only use policy](USE_POLICY.md)" in readme
    assert "[evaluation-only use policy](USE_POLICY.md)" in contributing
    assert "- [x] **Software license decision:**" in roadmap
    assert not Path("LICENSE").exists()


def test_wheel_packages_use_policy_without_license_metadata() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert project["urls"]["Use Policy"] == (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/USE_POLICY.md"
    )
    assert wheel["force-include"]["USE_POLICY.md"] == "scopeproof_core/USE_POLICY.md"
    assert "license" not in project
    assert "license-files" not in project
    assert not any(
        classifier.startswith("License ::") for classifier in project.get("classifiers", [])
    )


def test_python_312_ci_enforces_local_coverage_floor() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = config["project"]["optional-dependencies"]["dev"]
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    compatibility = workflow.split("  compatibility-python-311:", maxsplit=1)[1].split(
        "\n  verify:", maxsplit=1
    )[0]
    verify = workflow.split("\n  verify:", maxsplit=1)[1]

    assert "pytest-cov>=6,<7" in dev_dependencies
    assert "python -m pytest -q" in compatibility
    assert "--cov" not in compatibility
    assert "--cov=scopeproof_core" in verify
    assert "--cov=apps" in verify
    assert "--cov-report=term-missing:skip-covered" in verify
    assert "--cov-fail-under=95" in verify
    assert "codecov" not in workflow.lower()
    assert "coverage.xml" not in workflow
    assert ".coverage" in gitignore.splitlines()
    assert ".coverage.*" in gitignore.splitlines()


def test_internal_engineering_archive_has_provenance_index() -> None:
    archive = Path("docs/superpowers/README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "historical engineering records" in archive
    assert "not current product status" in archive
    assert "not runtime evidence" in archive
    assert "not adoption evidence" in archive
    assert "not a sequential user manual" in archive
    assert "[engineering archive index](docs/superpowers/README.md)" in contributing


def test_wheel_includes_bundled_benchmark_data() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert wheel["force-include"]["evals"] == "evals"
    assert list(Path("evals/fixtures").glob("*.json"))
    assert list(Path("evals/labels").glob("*.json"))


def test_sdist_excludes_local_development_state() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert config["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"] == [
        "/.scopeproof",
        "/.coverage*",
        "/.superpowers",
    ]


def test_comparison_benchmark_corpus_and_docs_preserve_research_boundary() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]
    comparison_files = {path.name for path in Path("evals/comparisons").glob("*.json")}
    expected_files = {
        "previous_pr.json",
        "previous_labels.json",
        "current_pr.json",
        "current_labels.json",
        "rereview_evidence_integrity.json",
        "unchanged_pr.json",
        "unchanged_labels.json",
    }
    readme = Path("README.md").read_text(encoding="utf-8")
    guide = Path("docs/development-environment.md").read_text(encoding="utf-8")

    assert Path("evals/comparisons").is_dir()
    assert comparison_files == expected_files
    assert wheel["force-include"]["evals"] == "evals"
    assert "scopeproof comparison-benchmark" in readme
    assert "deliberately constructed engineering evidence" in readme
    assert "does not advance Stage 1" in readme
    assert "uv run scopeproof benchmark" in guide
    assert "uv run scopeproof comparison-benchmark" in guide
    assert "across two paired previous/current cases" in guide
    for document in (readme, guide):
        assert "does not prove correctness" in document
        assert "does not constitute customer validation" in document
        assert "does not show external use" in document

    manifest = json.loads(
        Path("evals/comparisons/rereview_evidence_integrity.json").read_text(encoding="utf-8")
    )
    aggregate_counts = {kind.value: 0 for kind in EvidenceChangeKind}
    for case in manifest["cases"]:
        for kind, count in case["expected_counts"].items():
            aggregate_counts[kind] += count
    assert set(aggregate_counts) == {kind.value for kind in EvidenceChangeKind}
    assert all(count > 0 for count in aggregate_counts.values())


def test_owner_rehearsal_runbook_is_checked_and_stays_engineering_only() -> None:
    rehearsal_dir = Path("evals/rehearsals")
    requirements = (rehearsal_dir / "owner_rehearsal_criteria.txt").read_text(encoding="utf-8")
    guide = Path("docs/alpha/owner-rehearsal.md").read_text(encoding="utf-8")
    development_guide = Path("docs/development-environment.md").read_text(encoding="utf-8")
    development_copy = development_guide.replace("\n", " ")

    assert not list(rehearsal_dir.glob("*requirements*.txt"))

    assert requirements.splitlines() == [
        "User can export the research list as CSV",
        "Export respects all active filters",
        "Failed export shows an error message",
        "Successful export records research_exported",
    ]
    for command in (
        "uv run scopeproof owner-rehearsal init",
        "uv run scopeproof owner-rehearsal show",
        "uv run scopeproof prepare-requirements-confirmation",
        "uv run scopeproof review --fixture evals/fixtures/csv_export_pr.json",
        "uv run scopeproof export",
        "uv run scopeproof comparison-benchmark",
    ):
        assert command in guide
    assert "mktemp -d /tmp/" not in guide
    assert "uv run python -c" in guide
    assert "os.path.realpath(tempfile.mkdtemp" in guide
    assert "engineering evidence only" in guide
    assert "does not advance Stage 1" in guide
    assert "public issue" in guide.lower()
    assert "notification" in guide.lower()
    assert "across two paired previous/current cases" in guide
    assert "[owner-rehearsal runbook](alpha/owner-rehearsal.md)" in development_guide
    assert "scopeproof owner-rehearsal init" in development_guide
    assert "owner/Codex rehearsal is engineering evidence only" in development_copy
    assert "does not advance Stage 1" in development_copy


def test_ci_runs_lint_tests_and_benchmark() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python -m pip install --upgrade pip" in workflow
    assert "ruff check" in workflow
    assert "pytest" in workflow
    assert "scopeproof_core.evals.runner" in workflow


def test_streamlit_floor_supports_click_time_deferred_exports() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "streamlit>=1.52,<2" in project["project"]["dependencies"]


def test_locked_development_environment_is_documented_and_verified() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    guide = Path("docs/development-environment.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    lock = Path("uv.lock").read_text(encoding="utf-8")

    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.12"
    assert 'name = "scopeproof"' in lock
    assert 'name = "streamlit"' in lock
    assert "uv sync --extra dev --extra research --locked" in guide
    assert "uv run pytest" in guide
    assert "uv run scopeproof benchmark" in guide
    assert "Streamlit 1.59.1" in guide
    assert "Streamlit 1.57.0" in guide
    assert "testing-interface regression" in guide
    assert "locked-environment:" in workflow
    assert "astral-sh/setup-uv@" not in workflow
    assert "python -m pip install uv==0.11.29" in workflow
    assert "python -m uv sync --extra dev --extra research --locked" in workflow
    assert "python -m uv run python -m pytest -q tests/test_repository_contracts.py" in workflow
    assert "python -m uv run scopeproof benchmark" in workflow
    assert (
        "needs: [compatibility-python-311, compatibility-python-313, "
        "compatibility-windows, locked-environment]"
        in workflow
    )
    assert "[reproducible development environment](docs/development-environment.md)" in readme


def test_locked_gitpython_excludes_known_command_execution_advisories() -> None:
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    versions = [
        package["version"]
        for package in lock["package"]
        if package["name"].casefold() == "gitpython"
    ]

    assert len(versions) == 1
    assert tuple(int(part) for part in versions[0].split(".")) >= (3, 1, 59)


def test_ci_avoids_duplicate_feature_branch_runs() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "on:\n  push:\n    branches: [main]\n  pull_request:\n" in workflow


def test_ci_builds_and_executes_installed_wheel() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Installed wheel smoke" in workflow
    assert "python -m pip wheel . --no-deps" in workflow
    assert "python -m pip install --force-reinstall --no-deps" in workflow
    assert 'cd "$RUNNER_TEMP"' in workflow
    assert "from scopeproof_core import __version__" in workflow
    assert 'version("scopeproof") == __version__ == review.tool_version' in workflow
    assert "scopeproof --version" in workflow
    assert "scopeproof-web --version" in workflow
    assert "scopeproof benchmark" in workflow


def test_ci_executes_comparison_benchmark_in_locked_and_installed_environments() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    locked = workflow.split("  locked-environment:", maxsplit=1)[1].split(
        "\n  verify:", maxsplit=1
    )[0]
    installed_wheel = workflow.split("      - name: Installed wheel smoke", maxsplit=1)[1]

    required_commands = {
        "locked environment": "python -m uv run scopeproof comparison-benchmark",
        "installed wheel smoke": ('(cd "$RUNNER_TEMP" && scopeproof comparison-benchmark)'),
    }
    missing = {
        environment: command
        for environment, command in required_commands.items()
        if command not in (locked if environment == "locked environment" else installed_wheel)
    }

    assert not missing, f"CI comparison benchmark coverage is incomplete: {missing}"


def test_ci_starts_and_cleans_up_installed_web_workbench() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "setsid scopeproof-web" in workflow
    assert "STREAMLIT_SERVER_ADDRESS" not in workflow
    assert "STREAMLIT_SERVER_PORT" not in workflow
    assert "scopeproof-web --host 127.0.0.1 --port 8512" in workflow
    assert "http://127.0.0.1:8512/_stcore/health" in workflow
    assert "for attempt in $(seq 1 30)" in workflow
    assert '[ "$response" = "ok" ]' in workflow
    assert 'if ! kill -0 "$web_pid"' in workflow
    assert 'kill -- -"$web_pid"' in workflow
    assert 'wait "$web_pid"' in workflow
    assert "trap cleanup EXIT" in workflow
    assert 'cat "$web_log"' in workflow


def test_packaged_browser_regression_is_dev_only_and_runs_after_wheel_smoke() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    runtime_dependencies = config["project"]["dependencies"]
    dev_dependencies = config["project"]["optional-dependencies"]["dev"]
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    verify = workflow.split("\n  verify:", maxsplit=1)[1]

    assert "playwright==1.62.0" in dev_dependencies
    assert [
        package["version"]
        for package in lock["package"]
        if package["name"] == "playwright"
    ] == ["1.62.0"]
    assert not any(dependency.startswith("playwright") for dependency in runtime_dependencies)
    assert "browser: installed-wheel real-browser regression" in markers
    assert "python -m playwright install --with-deps chromium" in verify
    assert "python -m pytest -q -m browser tests/browser" in verify
    assert verify.index("Installed wheel smoke") < verify.index("Packaged browser regression")
    browser_test = Path("tests/browser/test_packaged_workbench.py").read_text(
        encoding="utf-8"
    )
    assert "context.route(" in browser_test
    assert '"**/*"' in browser_test
    assert "external_requests == []" in browser_test


def test_readme_documents_operating_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "streamlit run apps/web/app.py" in readme
    assert "RUN_LIVE_GITHUB_TESTS=1" in readme
    assert "scopeproof_core.evals.runner" in readme


def test_public_product_surfaces_use_reviewer_first_vocabulary() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    demo = Path("docs/launch/demo-script.md").read_text(encoding="utf-8")
    public_surfaces = "\n".join((readme, site, demo))

    assert "See which acceptance criteria have credible PR evidence" in readme
    assert "Prove the PR matches the product intent" not in public_surfaces
    assert "Alpha feedback session" in readme
    assert "GitHub Action advanced preview" in readme
    assert "Observed CI state" in readme


def test_readme_separates_release_install_from_contributor_setup() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert f"{PUBLIC_RELEASE_DOWNLOAD_ROOT}/{PUBLIC_RELEASE_WHEEL_FILENAME}" in readme
    assert "scopeproof benchmark" in readme
    assert "scopeproof-web --host 127.0.0.1 --port 8501" in readme
    assert "## Contributor setup" in readme
    assert "python -m pip install -e '.[dev]'" in readme
    assert "streamlit run apps/web/app.py" in readme
    assert "scopeproof web" not in readme


def test_readme_documents_optional_release_checksum_verification() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert f"{PUBLIC_RELEASE_DOWNLOAD_ROOT}/{PUBLIC_RELEASE_WHEEL_FILENAME}" in readme
    assert f"{PUBLIC_RELEASE_DOWNLOAD_ROOT}/SHA256SUMS.txt" in readme
    assert (
        f'grep " {PUBLIC_RELEASE_WHEEL_FILENAME}$" SHA256SUMS.txt | '
        "shasum -a 256 -c -"
    ) in readme
    assert (
        f'grep " {PUBLIC_RELEASE_WHEEL_FILENAME}$" SHA256SUMS.txt | '
        "sha256sum -c -"
    ) in readme
    assert f"{PUBLIC_RELEASE_WHEEL_FILENAME}.sha256" not in readme
    assert f"python -m pip install ./{PUBLIC_RELEASE_WHEEL_FILENAME}" in readme
    assert "does not provide code-signing or product-correctness assurance" in readme


def test_project_exposes_web_launcher_without_coupling_core_to_ui() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["scripts"]["scopeproof-web"] == "apps.web.launcher:main"
    core_cli = Path("scopeproof_core/cli.py").read_text(encoding="utf-8")
    assert "streamlit" not in core_cli
    assert "apps.web" not in core_cli


def test_product_surfaces_share_the_supported_theme_and_alpha_action_hierarchy() -> None:
    config = tomllib.loads(Path(".streamlit/config.toml").read_text(encoding="utf-8"))
    app = Path("apps/web/app.py").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    css = Path("site/styles.css").read_text(encoding="utf-8")
    parser = _PublicSiteParser()
    parser.feed(site)

    assert config["theme"] == {
        "base": "dark",
        "primaryColor": "#d8ff63",
        "backgroundColor": "#0d0f12",
        "secondaryBackgroundColor": "#171a1f",
        "textColor": "#f7f7f2",
    }
    assert "):focus-visible" in app
    assert "[data-testid=\"stAppViewContainer\"]" in app
    assert "@media (prefers-reduced-motion: reduce)" in app
    assert "alpha-actions-primary" in site
    assert "alpha-actions-secondary" in site
    assert "alpha-actions-resources" in site
    assert ".alpha-actions-resources" in css
    for action_class in (
        "alpha-actions-primary",
        "alpha-actions-secondary",
        "alpha-actions-resources",
    ):
        assert f".{action_class} {{ order:" not in css
    alpha_urls = {
        "https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml",
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/docs/alpha/participant-quickstart.md",
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/docs/alpha/public-pr-qualification-checklist.md",
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/docs/commercialization/design-partner-sprint.md",
        "https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-feedback.yml",
    }
    assert alpha_urls.issubset(parser.links)
    assert "Submit a public alpha case" in site
    assert "Open the ten-minute quickstart" in site
    assert "Post-review: share a completed review outcome" in site
    assert (
        "Submit no private code, credentials, customer data, private links, or confidential "
        "information."
    ) in site


def test_hatch_and_reviews_share_one_version_source() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version_source = Path("scopeproof_core/version.py").read_text(encoding="utf-8")

    assert config["project"]["dynamic"] == ["version"]
    assert "version" not in config["project"]
    assert config["tool"]["hatch"]["version"]["path"] == "scopeproof_core/version.py"
    assert f'__version__ = "{DEVELOPMENT_VERSION}"' in version_source


def _assert_published_version_matches_repository(
    *, repository: Path, current_version: str
) -> None:
    published_final_tags = {PUBLIC_RELEASE_VERSION: PUBLIC_RELEASE_TAG}
    published_tag = published_final_tags.get(current_version)

    if published_tag is None:
        assert current_version == DEVELOPMENT_VERSION
        return

    current_tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    published_tree = subprocess.run(
        ["git", "rev-parse", f"{published_tag}^{{tree}}"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert current_tree == published_tree, (
        f"version {current_version} is already published from {published_tag}, but the current "
        "committed tree differs; advance the development version before packaging"
    )
    tracked_diff = subprocess.run(
        ["git", "diff", "--quiet", published_tag, "--"],
        cwd=repository,
        check=False,
    )
    assert tracked_diff.returncode in {0, 1}, "Git could not compare tracked package inputs"
    assert tracked_diff.returncode == 0, (
        f"version {current_version} is already published from {published_tag}, but the tracked "
        "working tree differs; advance the development version before packaging"
    )
    untracked_paths = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    untracked_package_inputs = {
        path
        for path in untracked_paths
        if not (
            path.startswith(".coverage")
            or path == ".scopeproof"
            or path.startswith(".scopeproof/")
            or path == ".superpowers"
            or path.startswith(".superpowers/")
        )
    }
    build_config_path = repository / "pyproject.toml"
    build_config = (
        tomllib.loads(build_config_path.read_text(encoding="utf-8"))
        if build_config_path.exists()
        else {}
    )
    force_included_sources = list(
        build_config.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("force-include", {})
    )
    if force_included_sources:
        ignored_force_included_paths = subprocess.run(
            [
                "git",
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "--",
                *force_included_sources,
            ],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        untracked_package_inputs.update(ignored_force_included_paths)
    untracked_package_inputs = sorted(untracked_package_inputs)
    assert not untracked_package_inputs, (
        f"version {current_version} is already published from {published_tag}, but untracked "
        f"package inputs exist: {', '.join(untracked_package_inputs)}; track them and advance "
        "the development version before packaging"
    )


def test_divergent_tree_cannot_reuse_a_published_final_version() -> None:
    _assert_published_version_matches_repository(
        repository=Path.cwd(),
        current_version=__version__,
    )


def test_published_final_contract_rejects_dirty_tracked_tree(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "scopeproof-contract@example.test"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ScopeProof contract"],
        cwd=repository,
        check=True,
    )
    tracked = repository / "versioned.txt"
    tracked.write_text("published\n", encoding="utf-8")
    subprocess.run(["git", "add", "versioned.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "published"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v0.2.3"], cwd=repository, check=True)
    tracked.write_text("different package bytes\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="tracked working tree differs"):
        _assert_published_version_matches_repository(
            repository=repository,
            current_version="0.2.3",
        )


def test_published_final_contract_rejects_untracked_package_input(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    package = repository / "scopeproof_core"
    package.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "scopeproof-contract@example.test"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ScopeProof contract"],
        cwd=repository,
        check=True,
    )
    (package / "__init__.py").write_text("published = True\n", encoding="utf-8")
    subprocess.run(["git", "add", "scopeproof_core"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "published"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v0.2.3"], cwd=repository, check=True)
    (repository / ".coverage 2").write_text("preserve me\n", encoding="utf-8")
    untracked_package_input = package / "untracked_probe.py"
    untracked_package_input.write_text("different_package_bytes = True\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="untracked package inputs") as error:
        _assert_published_version_matches_repository(
            repository=repository,
            current_version="0.2.3",
        )

    assert "scopeproof_core/untracked_probe.py" in str(error.value)
    assert ".coverage 2" not in str(error.value)


def test_published_final_contract_rejects_ignored_force_included_input(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    force_included = repository / "evals"
    force_included.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "scopeproof-contract@example.test"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ScopeProof contract"],
        cwd=repository,
        check=True,
    )
    (repository / ".gitignore").write_text("*.py[cod]\n", encoding="utf-8")
    (repository / "pyproject.toml").write_text(
        '[tool.hatch.build.targets.wheel.force-include]\n"evals" = "evals"\n',
        encoding="utf-8",
    )
    (force_included / "README.md").write_text("published\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "published"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v0.2.3"], cwd=repository, check=True)
    ignored_package_input = force_included / "probe.pyc"
    ignored_package_input.write_bytes(b"different package bytes\n")

    with pytest.raises(AssertionError, match="untracked package inputs") as error:
        _assert_published_version_matches_repository(
            repository=repository,
            current_version="0.2.3",
        )

    assert "evals/probe.pyc" in str(error.value)


class _StrictVerificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _CommitIdentity(_StrictVerificationModel):
    sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")


class _MergedProductDisposition(_CommitIdentity):
    version: Literal["0.2.3"]
    pull_request: Literal[180]
    merged: Literal[True]
    tagged: Literal[False]
    released: Literal[False]
    stage_0: Literal["engineering_foundation_restored"]


class _IndependentlyVerifiedHead(_CommitIdentity):
    pull_request: Literal[180]
    same_tree_as_merged_product: Literal[True]


class _WorkflowRun(_StrictVerificationModel):
    run_id: int = Field(gt=0)
    workflow_id: int = Field(gt=0)
    workflow: str = Field(min_length=1)
    workflow_file: str = Field(min_length=1)
    run_number: int = Field(gt=0)
    attempt: Literal[1]
    check_suite_id: int = Field(gt=0)
    url: str = Field(pattern=r"^https://github\.com/YuzeJ21/Scope-Proof/actions/runs/\d+$")
    status: Literal["completed"]
    conclusion: Literal["success"]
    event: Literal["push", "dynamic"]
    head_branch: Literal["main"]
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class _MergedMainRuns(_StrictVerificationModel):
    verified_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    attributed_to: _CommitIdentity
    ci: _WorkflowRun
    codeql: _WorkflowRun
    pages: _WorkflowRun


class _DocumentationAlignmentBoundary(_StrictVerificationModel):
    classification: Literal["docs_only_post_merge_alignment"]
    changes_later_repository_tree: Literal[True]
    covered_by_product_tree_package_hashes: Literal[False]
    required_verification: Literal["affected_checks_and_pull_request_ci"]


class _EngineeringBoundary(_StrictVerificationModel):
    classification: Literal["engineering_only"]
    proves_correctness: Literal[False]
    target_repository_code_executed: Literal[False]
    advances_stage_1: Literal[False]


class _PublicInstall(_StrictVerificationModel):
    version: Literal["0.2.1"]
    latest_release: Literal["0.2.1"]


class _RuntimeEvidenceContract(_StrictVerificationModel):
    identity_field: Literal["runtime_evidence_id"]
    legacy_unlinked_gate: Literal["needs_review"]
    reconfirmation_reason: Literal["runtime_verification_reconfirmation_required"]
    record_version: Literal[3]


class _StageOneCounts(_StrictVerificationModel):
    qualifying_reviews: Literal[0]
    independent_practitioners: Literal[0]
    repositories: Literal[0]
    observed_under_ten_minute_completions: Literal[0]
    reuse_intent_signals: Literal[0]


class _ProductStageBoundary(_StrictVerificationModel):
    stage_0: Literal["engineering_foundation_restored"]
    stage_1: _StageOneCounts
    gated_stages: tuple[Literal[2], Literal[3], Literal[4]]


class _SourceSuiteEvidence(_StrictVerificationModel):
    sync_resolved_packages: Literal[60]
    sync_checked_packages: Literal[55]
    lock_resolved_packages: Literal[60]
    ruff_passed: Literal[True]
    tests_passed: Literal[1751]
    tests_skipped: Literal[1]
    coverage_statements: Literal[8588]
    coverage_missed: Literal[416]
    coverage_percent: Literal[95.16]
    coverage_threshold_percent: Literal[95.0]


class _CriterionBenchmarkEvidence(_StrictVerificationModel):
    cases: Literal[12]
    criteria: Literal[13]
    mismatches: Literal[0]
    status_mismatches: Literal[0]
    must_have_false_ready: Literal[0]
    false_blockers: Literal[0]
    unexecuted_declared_categories: Literal[0]


class _ComparisonChangeCounts(_StrictVerificationModel):
    added: Literal[3]
    modified: Literal[1]
    relocated: Literal[1]
    removed: Literal[3]
    unchanged: Literal[1]


class _ComparisonBenchmarkEvidence(_StrictVerificationModel):
    cases: Literal[2]
    mismatches: Literal[0]
    changes: _ComparisonChangeCounts
    advances_stage_1: Literal[False]


class _BenchmarkEvidence(_StrictVerificationModel):
    criterion: _CriterionBenchmarkEvidence
    comparison: _ComparisonBenchmarkEvidence


class _ArtifactEvidence(_StrictVerificationModel):
    filename: str
    size_bytes: int = Field(gt=0)
    entries: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    forbidden_inventory_matches: Literal[0]


class _PackageEvidence(_StrictVerificationModel):
    wheel: _ArtifactEvidence
    source_distribution: _ArtifactEvidence


class _InstallHealthEvidence(_StrictVerificationModel):
    python_version: Literal["3.12.0"]
    installed_packages: Literal[48]
    pip_check_passed: Literal[True]
    scopeproof_version: Literal["0.2.3"]
    scopeproof_web_version: Literal["0.2.3"]
    installed_benchmark_mismatches: Literal[0]
    installed_comparison_mismatches: Literal[0]
    health_body: Literal["ok"]
    post_stop_health_exit: Literal[7]
    listener_remained: Literal[False]
    process_remained: Literal[False]
    distribution_removed: Literal[True]
    virtual_environment_removed: Literal[True]
    isolated_home_removed: Literal[True]


class _MeasuredEvidence(_StrictVerificationModel):
    attributed_to: _CommitIdentity
    source: _SourceSuiteEvidence
    benchmarks: _BenchmarkEvidence
    package: _PackageEvidence
    install_health: _InstallHealthEvidence


class _HistoricalEvidenceBoundary(_StrictVerificationModel):
    r002_rerun_for_verified_head: Literal[False]
    browser_walkthrough_for_verified_head: Literal[False]
    historical_browser_is_current: Literal[False]
    historical_package_is_current: Literal[False]
    historical_r002_is_current: Literal[False]
    merged_product_tree_package_runtime_evidence: Literal[True]


class _ExactHeadVerificationManifest(_StrictVerificationModel):
    schema_version: Literal[2]
    boundary: _EngineeringBoundary
    merged_product: _MergedProductDisposition
    independently_verified_head: _IndependentlyVerifiedHead
    merged_main_runs: _MergedMainRuns
    documentation_alignment: _DocumentationAlignmentBoundary
    public_install: _PublicInstall
    runtime_evidence: _RuntimeEvidenceContract
    product_stages: _ProductStageBoundary
    measurements: _MeasuredEvidence
    historical_evidence: _HistoricalEvidenceBoundary


def _load_exact_head_verification_manifest() -> _ExactHeadVerificationManifest:
    path = Path("docs/audits/exact-head-runtime-evidence/verification.json")
    return _ExactHeadVerificationManifest.model_validate_json(path.read_text(encoding="utf-8"))


def test_exact_head_verification_manifest_preserves_captured_public_install_boundary() -> None:
    manifest = _load_exact_head_verification_manifest()

    assert manifest.public_install.version == "0.2.1"
    assert manifest.public_install.latest_release == "0.2.1"
    assert manifest.merged_product.version == "0.2.3"
    assert manifest.merged_product.merged is True
    assert manifest.merged_product.tagged is False
    assert manifest.merged_product.released is False


def test_exact_head_verification_manifest_binds_verified_and_merged_product_tree() -> None:
    manifest = _load_exact_head_verification_manifest()

    assert manifest.merged_product.sha == "2a320df966eff30c05a2b1dce607a247201fa165"
    assert manifest.merged_product.tree == "add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8"
    assert manifest.merged_product.pull_request == 180
    assert manifest.independently_verified_head.sha == "ed9f9c0cf6b7cf7cc25403d6138e7a8391f55e0f"
    assert manifest.independently_verified_head.tree == "add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8"
    assert manifest.independently_verified_head.same_tree_as_merged_product is True
    assert manifest.measurements.attributed_to == _CommitIdentity(
        sha=manifest.independently_verified_head.sha,
        tree=manifest.independently_verified_head.tree,
    )
    assert manifest.measurements.attributed_to.tree == manifest.merged_product.tree
    assert manifest.historical_evidence.merged_product_tree_package_runtime_evidence is True


def test_exact_head_verification_manifest_records_merged_main_workflows() -> None:
    manifest = _load_exact_head_verification_manifest()
    runs = manifest.merged_main_runs

    assert runs.attributed_to == _CommitIdentity(
        sha="2a320df966eff30c05a2b1dce607a247201fa165",
        tree="add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8",
    )
    assert runs.verified_at == "2026-08-02T05:47:39Z"
    assert {
        key: (
            run.run_id,
            run.workflow_id,
            run.workflow,
            run.workflow_file,
            run.run_number,
            run.attempt,
            run.check_suite_id,
            run.url,
            run.status,
            run.conclusion,
            run.event,
            run.head_sha,
        )
        for key, run in {
            "ci": runs.ci,
            "codeql": runs.codeql,
            "pages": runs.pages,
        }.items()
    } == {
        "ci": (
            30734386610,
            311501286,
            "CI",
            ".github/workflows/ci.yml",
            548,
            1,
            83342869656,
            "https://github.com/YuzeJ21/Scope-Proof/actions/runs/30734386610",
            "completed",
            "success",
            "push",
            "2a320df966eff30c05a2b1dce607a247201fa165",
        ),
        "codeql": (
            30734386396,
            311532827,
            "CodeQL",
            "dynamic/github-code-scanning/codeql",
            358,
            1,
            83342869149,
            "https://github.com/YuzeJ21/Scope-Proof/actions/runs/30734386396",
            "completed",
            "success",
            "dynamic",
            "2a320df966eff30c05a2b1dce607a247201fa165",
        ),
        "pages": (
            30734386626,
            314177066,
            "Pages",
            ".github/workflows/pages.yml",
            30,
            1,
            83342869686,
            "https://github.com/YuzeJ21/Scope-Proof/actions/runs/30734386626",
            "completed",
            "success",
            "push",
            "2a320df966eff30c05a2b1dce607a247201fa165",
        ),
    }


def test_exact_head_verification_manifest_excludes_docs_alignment_from_product_hashes() -> None:
    manifest = _load_exact_head_verification_manifest()

    assert manifest.documentation_alignment.model_dump() == {
        "classification": "docs_only_post_merge_alignment",
        "changes_later_repository_tree": True,
        "covered_by_product_tree_package_hashes": False,
        "required_verification": "affected_checks_and_pull_request_ci",
    }


def test_exact_head_verification_manifest_records_integrity_and_stage_boundaries() -> None:
    manifest = _load_exact_head_verification_manifest()

    assert manifest.boundary.classification == "engineering_only"
    assert manifest.runtime_evidence.identity_field == "runtime_evidence_id"
    assert (
        manifest.runtime_evidence.reconfirmation_reason
        == "runtime_verification_reconfirmation_required"
    )
    assert manifest.runtime_evidence.record_version == 3
    assert manifest.product_stages.stage_0 == "engineering_foundation_restored"
    assert manifest.product_stages.stage_1.model_dump() == {
        "qualifying_reviews": 0,
        "independent_practitioners": 0,
        "repositories": 0,
        "observed_under_ten_minute_completions": 0,
        "reuse_intent_signals": 0,
    }
    assert manifest.product_stages.gated_stages == (2, 3, 4)


def test_exact_head_verification_manifest_records_measured_evidence() -> None:
    manifest = _load_exact_head_verification_manifest()
    measurements = manifest.measurements

    assert measurements.source.tests_passed == 1751
    assert measurements.source.coverage_percent == 95.16
    assert measurements.benchmarks.criterion.cases == 12
    assert measurements.benchmarks.criterion.criteria == 13
    assert measurements.benchmarks.comparison.changes == _ComparisonChangeCounts(
        added=3,
        modified=1,
        relocated=1,
        removed=3,
        unchanged=1,
    )
    assert measurements.package.wheel.model_dump() == {
        "filename": "scopeproof-0.2.3-py3-none-any.whl",
        "size_bytes": 248171,
        "entries": 99,
        "sha256": "70bdca1a0d609c81ac8cd2274dc4915612067cfdb1c2205276faafd7c6358ac8",
        "forbidden_inventory_matches": 0,
    }
    assert measurements.package.source_distribution.model_dump() == {
        "filename": "scopeproof-0.2.3.tar.gz",
        "size_bytes": 5818424,
        "entries": 534,
        "sha256": "7fff8ba0b6b6c85ae0f22fe487762de8a525d04145c50eab46792233b798573e",
        "forbidden_inventory_matches": 0,
    }
    assert measurements.install_health.health_body == "ok"
    assert measurements.install_health.post_stop_health_exit == 7
    assert measurements.install_health.listener_remained is False
    assert measurements.install_health.process_remained is False
    assert measurements.install_health.distribution_removed is True
    assert measurements.install_health.virtual_environment_removed is True
    assert measurements.install_health.isolated_home_removed is True
    assert manifest.historical_evidence.browser_walkthrough_for_verified_head is False
    assert manifest.historical_evidence.r002_rerun_for_verified_head is False


def test_current_intake_policy_keeps_linkedin_material_archived_and_owner_gated() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(encoding="utf-8")
    draft = Path("docs/launch/linkedin-draft.md").read_text(encoding="utf-8")

    boundary = "Archived preparation; not authorized under the current passive-intake policy."
    assert boundary in playbook
    assert boundary in draft
    assert "Do not publish or use this material without a separate owner decision" in playbook
    assert "The owner may publish the post" not in playbook
    assert "If separately reauthorized" in playbook
    assert "archived LinkedIn preparation" in readme


def test_release_alignment_preserves_historical_candidate_provenance() -> None:
    candidate_notes = Path("docs/releases/v0.2.2-internal-candidate.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    candidate_provenance = " ".join(candidate_notes.split())

    assert "subsequent local-only changes contained" not in candidate_provenance
    assert "historical isolated artifact snapshot" in candidate_provenance
    assert "including its recorded hashes, is preserved as captured" in candidate_provenance
    assert (
        "Later merged changes through current `main` are documentation and "
        "repository-contract maintenance; they are not part of that historical "
        "isolated artifact snapshot."
    ) in candidate_provenance
    assert (
        "Current-HEAD CI is separate from this historical snapshot and must be "
        "evaluated independently."
    ) in candidate_provenance
    assert (
        "- Added the self-contained public-alpha participant quickstart install path from PR "
        "#172, pinned to the verified public v0.2.1 wheel. Participant setup and benchmark "
        "success are engineering evidence only; they did not publish v0.2.2 and do not advance "
        "Stage 1."
    ) in " ".join(changelog.split())


def test_readme_documents_confirmed_public_pr_cli_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof review --pr" in readme
    assert "--requirements requirements.txt" in readme
    assert "prepare-requirements-confirmation" in readme
    assert "--confirmation requirements-confirmation.json" in readme
    assert "does not verify their identity, authority" in readme
    assert "scopeproof export" in readme
    assert "scopeproof resolve REVIEW_ID" in readme
    assert "scopeproof verify-runtime REVIEW_ID" in readme
    assert "scopeproof final-acceptance REVIEW_ID" in readme
    assert "scopeproof compare PREVIOUS_REVIEW_ID CURRENT_REVIEW_ID" in readme
    assert "Static candidates never become runtime evidence through `resolve`" in readme
    assert "reviewer-confirmed criteria" in readme
    assert "not required or persisted" in readme


def test_active_confirmation_and_alpha_cli_docs_are_runnable() -> None:
    dogfood = Path("docs/dogfood/public-pr-protocol.md").read_text(encoding="utf-8")
    rehearsal = Path("docs/alpha/owner-rehearsal.md").read_text(encoding="utf-8")
    action = Path("docs/github-action.md").read_text(encoding="utf-8")
    outcome = Path("docs/alpha/outcome-form.md").read_text(encoding="utf-8")

    for document in (dogfood, rehearsal, action):
        assert "prepare-requirements-confirmation" in document
        assert "--confirmed-by" in document
    for document in (dogfood, rehearsal):
        assert "--confirmation" in document
    assert "--review-storage-dir .scopeproof/reviews" in outcome
    assert "--head-sha" not in outcome
    assert "live public GitHub ingestion" in outcome
    assert "Fixture, demo, research, and legacy" in outcome


def test_readme_documents_one_command_report_without_removing_repeat_export() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "--report scopeproof-review.md" in readme
    assert "refuses to overwrite" in readme
    assert "scopeproof export REVIEW_ID" in readme


def test_readme_documents_actual_stage_2a_durability_behavior() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "12 executable benchmark cases" in readme
    assert "criteria revisions" in readme
    assert "resolution history" in readme
    assert "Local review storage" in readme
    assert "unchanged candidate" in readme


def test_readme_documents_single_record_local_review_deletion() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof delete REVIEW_ID" in readme
    assert "Permanently delete the selected local review" in readme
    assert "Exported reports remain user-owned and are not removed" in readme
    assert "not secure erasure" in readme


def test_readme_documents_local_saved_review_discovery() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof list" in readme
    assert "local review IDs" in readme
    assert "does not parse review contents" in readme


def test_security_policy_uses_github_private_vulnerability_reporting() -> None:
    policy = Path("SECURITY.md").read_text(encoding="utf-8")

    assert "private vulnerability report" in policy.lower()
    assert "Do not post security vulnerabilities in public issues" in policy


def test_contributing_guide_preserves_public_alpha_boundaries() -> None:
    guide = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "public repository" in guide.lower()
    assert "Do not include tokens" in guide
    assert "python -m pytest -q" in guide
    assert "private vulnerability report" in guide.lower()


def test_external_validation_runbook_permanently_excludes_fork_testing() -> None:
    runbook = Path("docs/github-action-external-validation.md").read_text(encoding="utf-8")

    assert "fork testing is permanently excluded" in runbook.lower()
    assert "optional test 3" not in runbook.lower()


def test_launch_matrix_keeps_action_as_an_advanced_preview() -> None:
    matrix = Path("docs/launch/evidence-matrix.md").read_text(encoding="utf-8")

    assert "GitHub Action advanced preview" in matrix
    assert "Trusted-base planning" in matrix
    assert "default first-use path" in matrix
    assert "successful hosted Action run" not in matrix


def test_copyable_action_and_guide_share_the_reviewed_source_candidate_pin() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    expected_pin = "d553791cba83d9f756b2adce22bd814872b73ea2"

    install = re.search(
        r"scopeproof @ git\+https://github\.com/YuzeJ21/Scope-Proof\.git@([0-9a-f]{40})",
        example,
    )

    assert install is not None
    assert install.group(1) == expected_pin
    assert f"`{install.group(1)}`" in guide
    assert f"`{install.group(1)}`" in changelog
    assert "source-candidate installation" in guide
    assert "not a published v0.2.3 release" in guide


def test_public_docs_do_not_require_or_offer_external_fork_validation() -> None:
    public_docs = {
        "README.md": Path("README.md").read_text(encoding="utf-8"),
        "docs/privacy-readiness.md": Path("docs/privacy-readiness.md").read_text(encoding="utf-8"),
    }
    combined = "\n".join(public_docs.values()).lower()

    assert "fork evidence required" not in combined
    assert "same-head rerun, and fork evidence" not in combined
    assert "external fork validation is optional" not in combined
    assert "fork testing is permanently excluded" in combined


def test_ci_validates_declared_python_compatibility() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    minimum_compatibility = workflow.split(
        "  compatibility-python-311:", maxsplit=1
    )[1].split("\n  compatibility-python-313:", maxsplit=1)[0]
    python_313_compatibility = workflow.split(
        "  compatibility-python-313:", maxsplit=1
    )[1].split("\n  compatibility-windows:", maxsplit=1)[0]
    windows_compatibility = workflow.split(
        "  compatibility-windows:", maxsplit=1
    )[1].split("\n  locked-environment:", maxsplit=1)[0]
    verify = workflow.split("\n  verify:", maxsplit=1)[1]

    assert 'python-version: "3.11"' in minimum_compatibility
    assert "python -m pytest -q" in minimum_compatibility
    assert "python -m scopeproof_core.evals.runner" in minimum_compatibility
    assert "python -m pip wheel . --no-deps" in minimum_compatibility
    assert "scopeproof --version" in minimum_compatibility
    assert "scopeproof-web --version" in minimum_compatibility

    assert 'python-version: "3.13"' in python_313_compatibility
    assert "python -m pytest -q" in python_313_compatibility
    assert "python -m scopeproof_core.evals.runner" in python_313_compatibility
    assert "scopeproof comparison-benchmark" in python_313_compatibility
    assert "python -m pip wheel . --no-deps" in python_313_compatibility
    assert "python -m pip check" in python_313_compatibility
    assert "scopeproof --version" in python_313_compatibility
    assert "scopeproof-web --version" in python_313_compatibility
    assert "http://127.0.0.1:8513/_stcore/health" in python_313_compatibility
    assert '"$response" = "ok"' in python_313_compatibility

    assert "runs-on: windows-latest" in windows_compatibility
    assert '$PSNativeCommandUseErrorActionPreference = $true' in windows_compatibility
    assert 'python-version: "3.12"' in windows_compatibility
    assert "scopeproof_core.alpha.rehearsal_storage" in windows_compatibility
    assert "import apps.web.app" in windows_compatibility
    assert "tests/storage/test_atomic_files.py" in windows_compatibility
    assert "test_concurrent_process_alpha_creates_publish_exactly_once" in windows_compatibility
    assert "test_concurrent_process_outcome_updates_commit_exactly_once" in windows_compatibility
    assert "python -m pip wheel . --no-deps" in windows_compatibility
    assert "python -m pip check" in windows_compatibility
    assert "scopeproof --version" in windows_compatibility
    assert "scopeproof-web --version" in windows_compatibility
    assert "scopeproof benchmark" in windows_compatibility
    assert "scopeproof comparison-benchmark" in windows_compatibility
    assert (
        "needs: [compatibility-python-311, compatibility-python-313, "
        "compatibility-windows, locked-environment]"
        in verify
    )


def test_platform_storage_docs_do_not_overclaim_hostile_local_account_protection() -> None:
    design = Path(
        "docs/superpowers/specs/2026-08-12-platform-safe-alpha-storage-design.md"
    ).read_text(encoding="utf-8")
    environment = Path("docs/development-environment.md").read_text(encoding="utf-8")
    combined = f"{design}\n{environment}"

    assert "ScopeProof writers that use the shared claim boundary" in combined
    assert "same-user\nprocess that deliberately bypasses" in combined
    assert "atomic compare-and-swap protection" in combined
    assert "remains unsupported" in combined


def test_readme_documents_all_export_formats() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "`.md`, `.json`, `.csv`, or `.html`" in readme
    assert "`json`, `markdown`, `csv`, and `html`" in readme
    assert "Markdown / JSON / CSV / HTML" in readme
    assert "Markdown, JSON, CSV, and HTML exports" in readme


def test_roadmap_preserves_closed_stage_one_and_owner_led_later_gates() -> None:
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert "Five completed reviews" in roadmap
    assert "three independent practitioners" in roadmap
    assert "three public repositories" in roadmap
    assert "closed_not_pursued_by_owner" in roadmap
    assert "source-owner-confirmed criteria" in roadmap
    assert "genuine public pull request" in roadmap
    assert "Software license decision" in roadmap
    assert "Do not create synthetic validation" in roadmap
    assert "Do not create recurring external-evidence monitors" in roadmap


def test_changelog_points_to_authoritative_release_history() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Unreleased" in changelog
    assert "github.com/YuzeJ21/Scope-Proof/releases" in changelog
    assert "does not reconstruct" in changelog


def test_unreleased_ledger_records_post_v023_engineering_without_stage_credit() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = changelog.split("## Unreleased", maxsplit=1)[1].split(
        "## 0.2.3", maxsplit=1
    )[0]
    normalized_unreleased = " ".join(unreleased.split())

    for expected in (
        "Development version: `0.2.4.dev0`",
        "CLI lifecycle parity",
        "strict saved-record envelope",
        "packaged Chromium",
        "Python 3.13",
        "keyboard-only",
        "bounded native 200% zoom",
        "verified-public provenance",
        "Private, ambiguous, malformed, and legacy-unverified",
        "zero Stage 1 credit",
        "screen-reader",
        "Windows desktop",
        "Linux desktop",
        "non-Chromium",
        "WCAG conformance",
    ):
        assert expected in normalized_unreleased
    assert "No changes currently recorded" not in unreleased


def test_changelog_discloses_v021_rereview_evidence_boundaries() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## 0.2.1 — Re-review evidence integrity" in changelog
    assert "deliberately constructed engineering evidence" in changelog
    assert "does not advance Stage 1" in changelog


def test_active_public_release_surfaces_align_to_v023_without_rewriting_history() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(encoding="utf-8")
    design_partner = Path("docs/commercialization/design-partner-sprint.md").read_text(
        encoding="utf-8"
    )
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    status_page = Path("docs/releases/v0.2.3-status-and-next-stages.md").read_text(
        encoding="utf-8"
    )
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    candidate = Path("docs/releases/v0.2.3-internal-candidate.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")

    readme_quickstart = readme.split("## Quickstart", maxsplit=1)[1].split(
        "## Contributor setup", maxsplit=1
    )[0]
    conditional_asset_rule = (
        "Use the v0.2.3 asset URLs only when the GitHub Releases page shows v0.2.3 with "
        f"`{PUBLIC_RELEASE_WHEEL_FILENAME}` and `SHA256SUMS.txt`; otherwise, do not use "
        "an unpublished branch or candidate."
    )
    assert f"{PUBLIC_RELEASE_DOWNLOAD_ROOT}/{PUBLIC_RELEASE_WHEEL_FILENAME}" in readme_quickstart
    assert "releases/download/v0.2.1/" not in readme_quickstart
    assert conditional_asset_rule in readme_quickstart
    assert conditional_asset_rule in quickstart
    assert PUBLIC_RELEASES_INDEX in readme_quickstart
    assert PUBLIC_RELEASES_INDEX in quickstart
    for stale_predicate in (
        "untagged",
        "unreleased",
        "not published",
        "source candidate",
        "still-public v0.2.1",
        "v0.2.1 release",
        "no v0.2.3 tag or github release exists",
    ):
        assert stale_predicate not in readme_quickstart.lower()
    assert f"{PUBLIC_RELEASE_DOWNLOAD_ROOT}/{PUBLIC_RELEASE_WHEEL_FILENAME}" in quickstart
    assert "releases/download/v0.2.1/" not in quickstart
    assert f"ScopeProof v{PUBLIC_RELEASE_VERSION} can" in design_partner
    assert "ScopeProof v0.2.1 can" not in design_partner
    assert "ScopeProof v0.2.3 is published" in readme
    assert "PR #184" in readme
    assert f"`{PR184_RELEASE_MERGE_SHA}`" in readme
    assert "PR #183" in readme
    assert "historical source-integration evidence" in readme

    for active_status in (roadmap, status_page):
        assert f"Public install: v{PUBLIC_RELEASE_VERSION}" in active_status
        assert "v0.2.3 is published" in active_status
        assert "PR #184" in active_status
        assert f"`{PR184_RELEASE_MERGE_SHA}`" in active_status
        assert all(run_id in active_status for run_id in PR184_EXACT_MAIN_RUN_IDS)
        assert "exact-main CI, CodeQL, and Pages all succeeded" in active_status
        assert "The GitHub Release record is authoritative for publication availability." in (
            active_status
        )
        assert "Public install: v0.2.3 is available" in active_status
        assert "PR #183" in active_status
        assert f"`{PR183_SOURCE_MERGE_SHA}`" in active_status
        assert all(run_id in active_status for run_id in PR183_EXACT_MAIN_RUN_IDS)
        assert "historical source-integration evidence" in active_status
        assert "publication alignment is underway" not in active_status
        assert "publication alignment is completed" not in active_status
        assert "Stage 1" in active_status
        assert "closed_not_pursued_by_owner" in active_status
        assert "zero" in active_status

    assert "current local ingestion and reviewer-loop evidence" not in roadmap
    assert "current candidate's missing-patch" not in status_page

    unreleased_index = changelog.index("## Unreleased")
    release_index = changelog.index("## 0.2.3 — Evidence integrity and reviewer loop")
    historical_release_index = changelog.index("## 0.2.1 — Re-review evidence integrity")
    release_notes = changelog[release_index:historical_release_index]
    assert unreleased_index < release_index < historical_release_index
    assert "Candidate version:" not in changelog[unreleased_index:release_index]
    assert "engineering source work only" in release_notes
    assert "zero Stage 1" in release_notes
    assert "then-current v0.2.1 release-package guidance" in release_notes

    candidate_banner = candidate.split("## Included", maxsplit=1)[0]
    assert "Historical pre-publication record" in candidate_banner
    assert "not the current public-release status" in candidate_banner
    assert "Public install and latest release: v0.2.1" in candidate
    assert "70bdca1a0d609c81ac8cd2274dc4915612067cfdb1c2205276faafd7c6358ac8" in candidate
    assert "7fff8ba0b6b6c85ae0f22fe487762de8a525d04145c50eab46792233b798573e" in candidate
    assert (
        f'<a class="button button-primary" href="{PUBLIC_RELEASES_INDEX}/tag/'
        f'{PUBLIC_RELEASE_TAG}">Download {PUBLIC_RELEASE_TAG}</a>'
    ) in site


def test_active_docs_distinguish_post_v023_engineering_from_release_and_stage_progress() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    environment = Path("docs/development-environment.md").read_text(encoding="utf-8")
    status = Path("docs/releases/v0.2.3-status-and-next-stages.md").read_text(
        encoding="utf-8"
    )
    platform = Path("docs/releases/v0.2.3-platform-package-matrix.md").read_text(
        encoding="utf-8"
    )
    market = Path("docs/commercialization/market-comparison-2026-07-26.md").read_text(
        encoding="utf-8"
    )

    for active_surface in (readme, roadmap, environment, status, platform, market):
        assert "0.2.4.dev0" in active_surface
        assert "v0.2.3" in active_surface

    for active_status in (roadmap, status):
        assert all(pr in active_status for pr in ("PR #185", "PR #187", "PR #188"))
        assert "CLI lifecycle parity is implemented" in active_status
        assert "verified-public provenance enforcement" in active_status
        for count in ("0/5", "0/3", "0/2"):
            assert count in active_status

    python_313_row = next(line for line in status.splitlines() if "| Python 3.13 |" in line)
    assert "Protected Python 3.13 CI passed" in python_313_row
    assert "not Linux desktop evidence" in python_313_row
    assert "must pass" not in python_313_row

    prioritized = status.split("## Prioritized post-release decision candidates", maxsplit=1)[1]
    assert "**CLI lifecycle parity:**" not in prioritized
    assert "**Real-browser regression coverage:**" not in prioritized

    assert "Python 3.11, Python 3.12, and Python 3.13" in environment
    assert "Python 3.14" in environment
    python_314_line = environment.split("Python 3.14", maxsplit=1)[1].split(
        "\n", maxsplit=1
    )[0]
    assert "unverified" in python_314_line

    normalized_market = " ".join(market.split())
    assert (
        "keyboard-only and visible-focus engineering evidence is implemented"
        in normalized_market
    )
    assert "CLI lifecycle parity is implemented" in normalized_market
    assert "not yet verified with keyboard-only completion" not in normalized_market
    assert "Finish keyboard, zoom" not in normalized_market

    for unsupported in (
        "real screen-reader",
        "Windows desktop",
        "Linux desktop",
        "non-Chromium",
        "WCAG conformance",
    ):
        assert unsupported in platform


def test_authoritative_stage_one_docs_record_post_pr193_truth_and_owner_gate() -> None:
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    status = Path("docs/releases/v0.2.3-status-and-next-stages.md").read_text(
        encoding="utf-8"
    )

    def section(document: str, start: str, end: str) -> str:
        return document.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0]

    roadmap_header = section(roadmap, "## Current release and validation state", "## Stage 0")
    roadmap_rows = {
        cells[1].strip(): cells[2].strip()
        for line in roadmap_header.splitlines()
        if line.startswith("| ")
        if len(cells := line.split("|")) == 4
        if cells[1].strip() != "Area"
    }
    snapshot_row = roadmap_rows["Post-PR #193 resulting-main snapshot (2026-08-13)"]
    assert snapshot_row == (
        "PR #193 product-source baseline at "
        f"`{POST_PR193_RESULTING_MAIN_SHA}` (PR head `{PR193_EXACT_HEAD_SHA}`, "
        f"base `{PR193_EXACT_BASE_SHA}`)"
    )
    assert roadmap_rows["Active source line"] == (
        "Unreleased `0.2.4.dev0`; no v0.2.4 release, tag, or package publication exists"
    )
    assert roadmap_rows["Published install"] == (
        "v0.2.3 GitHub Release with wheel, source archive, and checksum manifest"
    )
    assert roadmap_rows["Snapshot verification"] == (
        f"Hosted resulting-main CI run [`{PR193_RESULTING_MAIN_CI_RUN_ID}`]"
        f"({GITHUB_ACTIONS_RUN_ROOT}/{PR193_RESULTING_MAIN_CI_RUN_ID}) "
        f"at exact PR #193 tree `{POST_PR193_RESULTING_MAIN_SHA}` recorded 2,251 passed, "
        "2 intentional skips, and 95.22% coverage"
    )
    assert roadmap_rows["Snapshot engineering checks"] == (
        f"Resulting-main CI run [`{PR193_RESULTING_MAIN_CI_RUN_ID}`]"
        f"({GITHUB_ACTIONS_RUN_ROOT}/{PR193_RESULTING_MAIN_CI_RUN_ID}) "
        "covers Python 3.11, Python 3.13, Windows, installed-wheel, deterministic benchmark, "
        "and packaged-browser checks; "
        f"CodeQL run [`{PR193_RESULTING_MAIN_CODEQL_RUN_ID}`]"
        f"({GITHUB_ACTIONS_RUN_ROOT}/{PR193_RESULTING_MAIN_CODEQL_RUN_ID}) "
        f"and Pages run [`{PR193_RESULTING_MAIN_PAGES_RUN_ID}`]"
        f"({GITHUB_ACTIONS_RUN_ROOT}/{PR193_RESULTING_MAIN_PAGES_RUN_ID}) "
        "also succeeded"
    )

    status_header = section(
        status,
        "# ScopeProof v0.2.3 status, gaps, and next stages",
        "## Current evidence",
    )
    normalized_status_header = " ".join(status_header.split())
    assert (
        "Post-PR #193 resulting-main snapshot (2026-08-13): PR #193 product-source baseline at "
        f"`{POST_PR193_RESULTING_MAIN_SHA}` (PR head `{PR193_EXACT_HEAD_SHA}`, "
        f"base `{PR193_EXACT_BASE_SHA}`)"
    ) in normalized_status_header
    assert (
        "Development version in this snapshot: unreleased `0.2.4.dev0`"
        in normalized_status_header
    )
    assert (
        "ScopeProof v0.2.3 is published. Public install: v0.2.3 is available"
        in normalized_status_header
    )
    assert (
        f"Hosted resulting-main CI run [`{PR193_RESULTING_MAIN_CI_RUN_ID}`]"
        f"({GITHUB_ACTIONS_RUN_ROOT}/{PR193_RESULTING_MAIN_CI_RUN_ID}) "
        f"at exact PR #193 tree `{POST_PR193_RESULTING_MAIN_SHA}` recorded 2,251 passed, "
        "2 intentional skips, and 95.22% coverage."
    ) in normalized_status_header
    for run_id in (
        PR193_RESULTING_MAIN_CI_RUN_ID,
        PR193_RESULTING_MAIN_CODEQL_RUN_ID,
        PR193_RESULTING_MAIN_PAGES_RUN_ID,
    ):
        assert (
            f"{GITHUB_ACTIONS_RUN_ROOT}/{run_id}" in status_header
        )
    assert "95.27% coverage" not in roadmap_header
    assert "95.27% coverage" not in status_header
    assert "PR #184 release-integration checks" in status_header
    assert "not resulting-main PR #193 checks" in normalized_status_header

    for pr in ("PR #189", "PR #190", "PR #191", "PR #192", "PR #193"):
        assert pr in roadmap_header
        assert pr in status_header
    for conflicting_declaration in (
        "Current resulting `main`",
        "current-source status bound",
    ):
        assert conflicting_declaration not in roadmap
        assert conflicting_declaration not in status

    stage_one_blocks = (
        section(roadmap, "## Stage 1 — Genuine public alpha", "## Stage 2"),
        section(status, "### Stage 1 — genuine public alpha", "### Stage 2"),
    )
    for stage_one in stage_one_blocks:
        assert "closed_not_pursued_by_owner" in stage_one
        assert "Stage 1 did not pass" in stage_one
        for count in (
            "0/5 qualifying reviews",
            "0/3 independent practitioners",
            "0/3 public repositories",
            "0/3 independently observed under-ten-minute completions",
            "0/2 reuse-intent signals",
        ):
            assert count in stage_one

        checklist = stage_one.split("Archived external-evidence distinctions", maxsplit=1)[1]
        assert "optional external research is separately authorized" in checklist
        for distinction in (
            "Preparation is not outreach",
            "Inbound submissions are not recruited participants",
            "Observed completion evidence is not self-reported timing",
            "Qualifying reviews are not demos, tests, maintainers, bots, or repository activity",
        ):
            assert distinction in checklist

    for document, heading, next_heading, required in (
        (
            roadmap,
            "## Stage 2 — Owner-led productization",
            "## Stage 3",
            "External commercial discovery is optional and separate",
        ),
        (
            status,
            "### Stage 2 — owner-led productization",
            "### Stage 3",
            "External commercial discovery is optional and separate",
        ),
        (
            roadmap,
            "## Stage 3 — Limited beta",
            "## Stage 4",
            "Stage 3 may define a bounded release candidate or beta",
        ),
        (
            status,
            "### Stage 3 — limited beta",
            "### Stage 4",
            "A future bounded release candidate or beta requires a new owner-authorized plan.",
        ),
        (
            roadmap,
            "## Stage 4 — Evidence-guided expansion decision",
            "## Honest stop and pivot rules",
            "Stage 4 requires a named constraint",
        ),
        (
            status,
            "### Stage 4 — evidence-guided expansion",
            "## Prioritized post-release decision candidates",
            "Missing external evidence remains missing",
        ),
        ):
        stage = section(document, heading, next_heading)
        normalized_stage = " ".join(stage.split())
        assert required in normalized_stage
        assert (
            "customer" in normalized_stage.lower()
            or "external evidence" in normalized_stage.lower()
        )


def test_owner_led_stage_two_strategy_preserves_zero_external_evidence() -> None:
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    status = Path("docs/releases/v0.2.3-status-and-next-stages.md").read_text(
        encoding="utf-8"
    )
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    market_comparison = Path(
        "docs/commercialization/market-comparison-2026-07-26.md"
    ).read_text(encoding="utf-8")

    def section(document: str, start: str, end: str) -> str:
        remainder = document.split(start, maxsplit=1)[1]
        return remainder if not end else remainder.split(end, maxsplit=1)[0]

    stage_blocks = (
        section(roadmap, "## Stage 1 — Genuine public alpha", "## Stage 2"),
        section(status, "### Stage 1 — genuine public alpha", "### Stage 2"),
    )
    productization_blocks = (
        section(roadmap, "## Stage 2 — Owner-led productization", "## Stage 3"),
        section(status, "### Stage 2 — owner-led productization", "### Stage 3"),
    )
    packet_status = section(packet, "## Current status", "## Owner-led productization scope")
    packet_scope = section(
        packet, "## Owner-led productization scope", "## Optional external discovery"
    )
    optional_discovery = section(
        packet, "## Optional external discovery", "## Hypothesis ledger"
    )
    optional_discovery_rules = section(
        packet, "## Optional-discovery decision rules", "## Boundaries"
    )
    current_headers = "\n".join(
        (
            section(roadmap, "# ScopeProof Roadmap", "## Stage 0"),
            section(
                status,
                "# ScopeProof v0.2.3 status, gaps, and next stages",
                "## Current evidence",
            ),
            section(market_comparison, "## Stage implications", ""),
        )
    )

    for stage_one in stage_blocks:
        normalized_stage_one = " ".join(stage_one.split())
        assert "closed_not_pursued_by_owner" in normalized_stage_one
        assert "Stage 1 did not pass" in normalized_stage_one
        for count in (
            "0/5 qualifying reviews",
            "0/3 independent practitioners",
            "0/3 public repositories",
            "0/3 independently observed under-ten-minute completions",
            "0/2 reuse-intent signals",
        ):
            assert count in normalized_stage_one
        assert "not a validated False Ready rate" in normalized_stage_one

    for stage_two in productization_blocks:
        normalized_stage_two = " ".join(stage_two.split())
        assert "owner_led_productization_active" in normalized_stage_two
        assert "owner-led productization" in normalized_stage_two
        assert "External commercial discovery is optional and separate" in normalized_stage_two
        assert "does not claim customer validation" in normalized_stage_two

    for count in (
        "0/5 qualifying reviews",
        "0/3 independent practitioners",
        "0/3 public repositories",
        "0/3 independently observed under-ten-minute completions",
        "0/2 reuse-intent signals",
    ):
        assert count in packet_status
    assert "does not authorize outreach" in packet_status
    normalized_packet_scope = " ".join(packet_scope.split())
    normalized_optional_discovery = " ".join(optional_discovery.split())
    assert "product and workflow clarity" in normalized_packet_scope
    assert "deterministic evidence quality" in normalized_packet_scope
    assert "release, tag, or package publication" in normalized_packet_scope
    assert "External commercial discovery is optional and separate" in normalized_optional_discovery
    assert "separate owner authorization" in normalized_optional_discovery
    normalized_discovery_rules = " ".join(optional_discovery_rules.split())
    assert (
        "No optional-discovery decision may be calculated while the qualifying denominator is zero"
        in normalized_discovery_rules
    )
    assert "No customer, product, or commercial decision" not in normalized_discovery_rules

    protected_current_sections = "\n".join(
        (*stage_blocks, *productization_blocks, packet_status, packet_scope, optional_discovery)
    )
    for forbidden_claim in (
        "Stage 1 passed",
        "Stage 1 is complete",
        "customer validation achieved",
        "validated demand",
        "validated price",
        "willingness to pay is validated",
        "Stages 2\u20134 remain gated",
        "Stage 1 waits",
        "Stage 1 remains at zero until",
        "Stage 2 commercial discovery cannot claim willingness to pay before Stage 1",
    ):
        assert forbidden_claim not in protected_current_sections
        assert forbidden_claim not in current_headers


def test_superseded_audits_preserve_historical_results_and_link_current_status() -> None:
    historical_audits = (
        Path("docs/audits/exact-head-runtime-evidence/verification.md"),
        Path("docs/audits/v0.2.3-integrity-reviewer-loop/verification.md"),
        Path("docs/audits/v0.2.3-product-convergence/verification.md"),
        Path("docs/audits/workbench-ux-simplification/verification.md"),
        Path("docs/audits/post-release-cli-browser/verification.md"),
        Path("docs/audits/accessibility-platform-evidence/verification.md"),
        Path("docs/audits/v0.2.3-workbench/accessibility-and-first-use-audit.md"),
    )

    for audit in historical_audits:
        text = audit.read_text(encoding="utf-8")
        opening = "\n".join(text.splitlines()[:10])
        assert "Historical evidence boundary" in opening
        assert "../../releases/v0.2.3-status-and-next-stages.md" in opening
        assert "does not rewrite" in opening


def test_public_contribution_templates_preserve_evidence_boundaries() -> None:
    defect = Path(".github/ISSUE_TEMPLATE/defect.yml").read_text(encoding="utf-8")
    feedback = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(encoding="utf-8")
    pull_request = Path(".github/pull_request_template.md").read_text(encoding="utf-8")

    assert "Do not include tokens" in defect
    assert "Reproduction" in defect
    assert "source-owner-confirmed" in feedback
    assert "constructed demo" in feedback
    assert "User-confirmed requirement" in pull_request
    assert "Static evidence is not runtime verification" in pull_request
    assert "Remaining limitations" in pull_request


def test_public_docs_link_governance_surfaces() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "[public roadmap](ROADMAP.md)" in readme
    assert "[changelog](CHANGELOG.md)" in readme
    assert "[public roadmap](ROADMAP.md)" in contributing
    assert "[changelog](CHANGELOG.md)" in contributing


def test_readme_shows_disclosed_constructed_demo_visual() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    image_path = Path("docs/assets/scopeproof-constructed-demo-evidence-matrix.jpg")

    assert image_path.is_file()
    assert image_path.read_bytes().startswith(b"\xff\xd8\xff")
    assert image_path.stat().st_size > 50_000
    assert (
        "![ScopeProof deliberately constructed demo evidence matrix]"
        "(docs/assets/scopeproof-constructed-demo-evidence-matrix.jpg)"
    ) in readme
    assert "Controlled demo screenshot—not a customer case" in readme
    assert "not runtime verification or proof of correctness" in readme


def test_linkedin_alpha_launch_package_is_current_and_truthful() -> None:
    draft = Path("docs/launch/linkedin-draft.md").read_text(encoding="utf-8")
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(encoding="utf-8")
    disclosure = (
        "This is a deliberately constructed demo case. ScopeProof uses deterministic "
        "evidence rules and human review; it does not guarantee correctness or replace QA."
    )
    issue_url = "https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml"

    for required_text in (
        "https://github.com/YuzeJ21/Scope-Proof",
        "https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.1",
        issue_url,
        disclosure,
        "genuine public pull request",
        "product managers",
        "QA",
        "engineers",
    ):
        assert required_text in draft

    for required_field in (
        "Public PR URL",
        "Source-owner confirmation",
        "Public criteria",
        "No confidential information",
        "Technical smoke only",
        "Decline",
    ):
        assert required_field in playbook


def test_linkedin_alpha_intake_is_inbound_only_and_owner_passive() -> None:
    draft = Path("docs/launch/linkedin-draft.md").read_text(encoding="utf-8")
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(encoding="utf-8")
    issue_url = "https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml"

    for required_text in (
        "## Inbound-only intake",
        "The owner path stays passive",
        "A submission is only an intake candidate",
        issue_url,
        "genuine public PR",
        "source-owner-confirmed",
        "No paid LLM API",
    ):
        assert required_text in playbook

    assert issue_url in draft
    for forbidden_text in (
        "DM me",
        "DM-first outreach",
        "Warm-contact message",
        "Cold-contact message",
        "One optional follow-up",
        "First-response DM",
    ):
        assert forbidden_text not in draft
        assert forbidden_text not in playbook


def test_concierge_host_checklist_indexes_real_alpha_without_contact_data() -> None:
    checklist_path = Path("docs/alpha/concierge-host-checklist.md")
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert checklist_path.is_file()
    checklist = checklist_path.read_text(encoding="utf-8")
    for required_link in (
        "../../README.md#quickstart",
        "public-pr-qualification-checklist.md",
        "acceptance-criteria-confirmation-template.md",
        "participant-quickstart.md",
        "../dogfood/public-pr-protocol.md",
        "outcome-form.md",
    ):
        assert required_link in checklist

    for status in (
        "not_started",
        "qualified",
        "criteria_confirmed",
        "review_completed",
        "outcome_received",
        "declined",
        "withdrawn",
    ):
        assert f"`{status}`" in checklist

    prohibited_fields = (
        "participant name",
        "email address",
        "linkedin profile",
        "dm transcript",
        "contact list",
    )
    assert all(field not in checklist.lower() for field in prohibited_fields)
    assert "../alpha/concierge-host-checklist.md" in playbook
    assert "[concierge host checklist](docs/alpha/concierge-host-checklist.md)" in roadmap


def test_linkedin_alpha_visual_has_publishable_dimensions() -> None:
    image_path = Path("docs/assets/scopeproof-linkedin-alpha.png")

    assert image_path.is_file()
    assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert image_path.stat().st_size > 40_000
    with Image.open(image_path) as image:
        assert image.format == "PNG"
        assert image.size == (1200, 1200)


def test_public_alpha_participant_kit_is_safe_complete_and_actionable() -> None:
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(encoding="utf-8")
    qualification = Path("docs/alpha/public-pr-qualification-checklist.md").read_text(
        encoding="utf-8"
    )
    criteria = Path("docs/alpha/acceptance-criteria-confirmation-template.md").read_text(
        encoding="utf-8"
    )
    outcome = Path("docs/alpha/outcome-form.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    protocol = Path("docs/dogfood/public-pr-protocol.md").read_text(encoding="utf-8")

    assert all(f"Minute {minute}" in quickstart for minute in range(1, 11))
    assert f"{PUBLIC_RELEASE_DOWNLOAD_ROOT}/{PUBLIC_RELEASE_WHEEL_FILENAME}" in quickstart
    assert "scopeproof benchmark" in quickstart
    assert "scopeproof-web --host 127.0.0.1 --port 8501" in quickstart
    assert "setup evidence only" in quickstart
    assert "Stage 1 is closed as not pursued" in quickstart
    assert "creates no external-evidence credit" in quickstart
    assert "releases/download/v0.2.2/" not in quickstart
    assert "scopeproof-0.2.2" not in quickstart
    assert "Alpha feedback session" in quickstart
    assert "Standard review mode creates no participant record" in quickstart
    assert "source owner" in qualification.lower()
    assert "No confidential information" in qualification
    assert "one criterion per line" in criteria.lower()
    assert "found_useful_gap" in outcome
    assert "showed_only_known_information" in outcome
    assert "created_friction" in outcome
    assert "report consent" in outcome.lower()
    assert "quotation consent" in outcome.lower()
    prohibited = ("participant name", "email address", "linkedin profile", "dm transcript")
    combined = "\n".join((quickstart, qualification, criteria, outcome)).lower()
    assert all(term not in combined for term in prohibited)
    assert "[public-alpha participant quickstart](docs/alpha/participant-quickstart.md)" in readme
    assert "docs/alpha/participant-quickstart.md" in protocol


def test_participant_evidence_unblocker_prevents_empty_monitoring_loops() -> None:
    unblocker = Path("docs/alpha/participant-evidence-unblocker.md").read_text(encoding="utf-8")
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(encoding="utf-8")

    assert "[participant evidence unblocker](participant-evidence-unblocker.md)" in checklist
    assert "closed_not_pursued_by_owner" in unblocker
    assert "Stage 1 did not pass" in unblocker
    assert "must not be used to restart it automatically" in unblocker
    assert "Do not create recurring" in unblocker
    for forbidden in (
        "private source",
        "billing",
        "outreach",
        "scrape profiles",
        "invent a participant",
        "willingness-to-pay result",
        "notification-only GitHub",
    ):
        assert forbidden in unblocker


def test_inbound_alpha_case_submission_path_is_public_safe_and_owner_passive() -> None:
    template_path = Path(".github/ISSUE_TEMPLATE/public-alpha-case.yml")
    template = template_path.read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    unblocker = Path("docs/alpha/participant-evidence-unblocker.md").read_text(encoding="utf-8")
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(encoding="utf-8")

    issue_url = "https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml"
    assert "name: Public-alpha case submission" in template
    assert 'title: "[Alpha case]: "' in template
    assert "public_pr_url" in template
    assert "public_requirements_url" in template
    assert "criteria_authority" in template
    assert "confidentiality_confirmation" in template
    assert "participant_role" in template
    assert "source-owner-confirmed acceptance criteria" in template
    assert "not a constructed demo, synthetic validation, or invented evidence" in template
    assert 'labels: ["dogfood"]' in template
    assert "attributable completed-use evidence" in template
    assert "does not establish customer, product, or commercial validation by itself" in template
    assert "external-validation" not in template
    assert "not validation until" not in template
    assert "case counts only" not in template
    for forbidden in (
        "tokens",
        "credentials",
        "private code",
        "customer data",
        "confidential requirements",
    ):
        assert forbidden in template

    assert issue_url in site
    assert "Submit a public alpha case" in site
    assert "Use LinkedIn DM only" not in site
    assert "inbound-only" in unblocker
    assert issue_url in unblocker
    assert "Do not manually contact participants" in " ".join(unblocker.split())
    assert "Submit a public alpha case" in checklist
    assert issue_url in checklist


def test_public_pages_site_and_captioned_demo_are_truthful_and_self_contained() -> None:
    index_path = Path("site/index.html")
    styles_path = Path("site/styles.css")
    transcript_path = Path("site/demo-transcript.html")
    video_path = Path("site/assets/scopeproof-captioned-demo.mp4")
    captions_path = Path("site/assets/scopeproof-captioned-demo.vtt")
    poster_path = Path("site/assets/scopeproof-demo-poster.jpg")
    alpha_visual_path = Path("site/assets/scopeproof-linkedin-alpha.png")
    disclosure = (
        "This is a deliberately constructed demo case. ScopeProof uses deterministic "
        "evidence rules and human review; it does not guarantee correctness or replace QA."
    )

    html = index_path.read_text(encoding="utf-8")
    css = styles_path.read_text(encoding="utf-8")
    transcript = transcript_path.read_text(encoding="utf-8")
    captions = captions_path.read_text(encoding="utf-8")
    parser = _PublicSiteParser()
    parser.feed(html)

    assert html.count("<h1") == 1
    assert disclosure in html
    assert disclosure in transcript
    assert "Public PR → Confirm criteria → Review coverage → Record decisions → Export" in html
    assert "Likes, views, stars, impressions, and downloads are not product validation." in html
    assert "https://github.com/YuzeJ21/Scope-Proof" in html
    assert PUBLIC_RELEASES_INDEX in html
    assert f"{PUBLIC_RELEASES_INDEX}/tag/{PUBLIC_RELEASE_TAG}" in html
    assert (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/docs/alpha/participant-quickstart.md"
        in html
    )
    qualification_url = (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/"
        "docs/alpha/public-pr-qualification-checklist.md"
    )
    assert qualification_url in parser.links
    assert "Check whether your PR qualifies" in html
    assert not any(urlsplit(link).hostname == "www.linkedin.com" for link in parser.links)
    assert "DM me" not in html
    assert "https://github.com/YuzeJ21/Scope-Proof/blob/main/USE_POLICY.md" in html
    assert parser.forms == 0
    assert parser.remote_scripts == []
    assert "analytics" not in html.lower()
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "clamp(2.35rem, 12vw, 3.5rem)" in css
    assert "overflow-wrap: anywhere" in css
    assert "max-width: 100%" in css
    assert ":focus-visible" in css
    assert parser.video_tracks == [
        {
            "kind": "captions",
            "src": "assets/scopeproof-captioned-demo.vtt",
            "srclang": "en",
            "label": "English",
            "default": None,
        }
    ]
    assert captions.startswith("WEBVTT\n")
    assert disclosure in captions
    assert video_path.read_bytes()[4:8] == b"ftyp"
    assert 59.9 <= _mp4_duration_seconds(video_path) <= 60.1
    assert video_path.stat().st_size > 100_000
    with Image.open(poster_path) as poster:
        assert poster.size == (1280, 720)
    with Image.open(alpha_visual_path) as alpha_visual:
        assert alpha_visual.size == (1200, 1200)


def test_public_site_desktop_hero_keeps_actions_and_safety_boundary_above_the_fold() -> None:
    html = Path("site/index.html").read_text(encoding="utf-8")
    css = Path("site/styles.css").read_text(encoding="utf-8")
    desktop_css = css.split("@media (max-width: 900px)", maxsplit=1)[0]
    mobile_css = css.split("@media (max-width: 600px)", maxsplit=1)[1]

    hero = html.split('<section class="hero"', maxsplit=1)[1].split("</section>", maxsplit=1)[0]
    assert (
        '<link rel="icon" href="assets/scopeproof-linkedin-alpha.png" type="image/png">'
        in html
    )
    assert hero.index('<div class="actions">') < hero.index('<p class="boundary">')
    assert "min-height: calc(100vh - 5.2rem)" in desktop_css
    assert "padding: 2rem 0" in desktop_css
    assert "clamp(3rem, 5.625vw, 4.5rem)" in desktop_css

    # Preserve the separately verified narrow layout while compacting desktop only.
    assert ".hero { min-height: auto; padding: 3.5rem 0; }" in mobile_css
    assert "clamp(2.35rem, 12vw, 3.5rem)" in mobile_css


def test_optional_commercial_discovery_is_separate_and_evidence_gated() -> None:
    guide_path = Path("docs/commercialization/design-partner-sprint.md")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    normalized_roadmap = " ".join(roadmap.split())

    assert guide_path.is_file()
    guide = guide_path.read_text(encoding="utf-8")
    normalized_guide = " ".join(guide.split())
    for required in (
        "30-day Design Partner Sprint",
        "free",
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research hypotheses only",
        "not a purchase agreement",
        "after a genuine participant completes a review",
        "closed_not_pursued_by_owner",
        "optional",
        "separate owner authorization",
        "not customer validation",
        "Local Pro",
    ):
        assert required in normalized_guide
    for non_evidence in (
        "stars",
        "views",
        "downloads",
        "issue submissions",
        "constructed demos",
        "synthetic cases",
        "owner-authored examples",
    ):
        assert non_evidence in normalized_guide

    assert "## Stage 2 — Owner-led productization" in roadmap
    assert "External commercial discovery is optional and separate" in normalized_roadmap
    assert "does not claim customer validation" in normalized_roadmap
    assert "does not authorize a merge, release, tag, package publication" in normalized_roadmap


def test_optional_external_feedback_collects_bounded_signals_without_price_research() -> None:
    template = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(encoding="utf-8")
    for field_id in (
        "public_pr",
        "alpha_case_issue",
        "reviewed_head_sha",
        "public_requirements_url",
        "source_owner",
        "outcome",
        "timing_evidence",
        "timing_evidence_support",
        "useful_gap_category",
        "decision_impact",
        "reuse_intent",
        "friction",
        "limitations",
        "safety",
    ):
        assert f"id: {field_id}" in template

    for required_text in (
        "optional external feedback",
        "independently observed timing",
        "self-reported timing is not independently observed",
        "does not reopen Stage 1",
        "commercial discovery is separate",
        "customer validation",
        "Prefer not to answer",
        "submission alone is not validation",
    ):
        assert required_text.lower() in template.lower()

    forbidden_ids = (
        "name",
        "email",
        "linkedin_profile",
        "employer",
        "private_repository",
        "payment",
        "purchase_commitment",
        "sales_contact",
        "design_partner_interest",
        "price_discussion",
    )
    assert all(f"id: {field_id}" not in template for field_id in forbidden_ids)


def test_optional_external_feedback_timing_is_single_source_and_fail_closed() -> None:
    template = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(
        encoding="utf-8"
    )

    assert "id: timing_evidence" in template
    assert "id: timing_evidence_support" in template
    for removed_id in (
        "completion_time",
        "timing_observation_status",
        "timing_observer_category",
        "timing_public_evidence_reference",
    ):
        assert f"id: {removed_id}" not in template
    for option in (
        "Not independently observed",
        '"Independently observed: under 5 minutes"',
        '"Independently observed: 5 to 10 minutes"',
        '"Independently observed: more than 10 minutes"',
    ):
        assert f"- {option}" in template
    assert "both an observer category and a specific public evidence reference" in template
    assert "fails closed to not observed" in template
    assert "cannot upgrade a Not independently observed selection" in template


def test_optional_discovery_cohorts_are_ordered_once_and_frozen() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    rules = packet.split("## Optional-discovery decision rules", maxsplit=1)[1].split(
        "## Boundaries", maxsplit=1
    )[0]
    normalized = " ".join(rules.split())

    for required in (
        "qualified_at_utc",
        "feedback_issue_number",
        "evidence_snapshot_sha256",
        "(qualified_at_utc, feedback_issue_number) ascending",
        "positions 1\u20135, 6\u201310",
        "Freeze a cohort when its fifth member is assigned",
        "cannot reorder, replace, or repartition a frozen cohort",
        "fewer than five unassigned qualifying records",
        "no optional-discovery decision is calculated",
    ):
        assert required in normalized


def test_optional_discovery_corrections_never_count_a_session_twice() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    rules = packet.split("## Optional-discovery decision rules", maxsplit=1)[1].split(
        "## Boundaries", maxsplit=1
    )[0]
    normalized = " ".join(rules.split())

    for required in (
        "Material corrections annotate the original qualification record",
        "do not create a new cohort member",
        "The same completed session can appear in at most one cohort",
        "the affected frozen cohort becomes invalid and remains on hold",
    ):
        assert required in normalized


def test_optional_discovery_qualification_binds_an_immutable_evidence_snapshot() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    rules = packet.split("## Optional-discovery decision rules", maxsplit=1)[1].split(
        "## Boundaries", maxsplit=1
    )[0]
    normalized = " ".join(rules.split())

    assert "evidence_snapshot_sha256" in normalized
    assert "SHA-256 digest of the evidence snapshot used at qualification" in normalized
    assert "A mutable public reference does not qualify" in normalized


def test_optional_discovery_decision_predicates_are_explicit_and_fail_closed() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    rules = packet.split("## Optional-discovery decision rules", maxsplit=1)[1].split(
        "## Boundaries", maxsplit=1
    )[0]
    normalized = " ".join(rules.replace("`", "").split())

    for required in (
        "Useful or decision-relevant is true only when",
        "Found a useful previously unknown gap",
        "Changed my review decision",
        "Clarified my review decision",
        "Confirmed an existing review decision does not count",
        "Affirmative repeat use is true only when",
        "Yes, I intend to use ScopeProof on another PR",
        "No, Unsure, Prefer not to answer, missing, and ambiguous responses do not count",
        "zero explicit affirmative repeat-use responses",
    ):
        assert required in normalized


def test_optional_discovery_holds_contradictory_useful_gap_inputs() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    assert (
        "Found a useful previously unknown gap counts only when useful_gap_category is not "
        "No new useful gap"
        in normalized
    )
    assert (
        "Any contradiction between outcome and useful_gap_category keeps the record on hold"
        in normalized
    )
    assert (
        normalized.index("Any contradiction between outcome and useful_gap_category")
        < normalized.index("Precedence, highest first")
    )


def test_optional_discovery_continue_requires_every_member_to_understand_boundary() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    rules = packet.split("## Optional-discovery decision rules", maxsplit=1)[1].split(
        "## Boundaries", maxsplit=1
    )[0]
    normalized = " ".join(rules.replace("`", "").split())

    assert "all 5 of 5 members explicitly understood the evidence boundary" in normalized
    assert (
        "misunderstood, unsure, declined, missing, and ambiguous values keep the cohort on hold"
        in normalized
    )


def test_optional_discovery_pivot_uses_bounded_authorized_inputs() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    for value in (
        "prefer_different_job",
        "existing_alternative_sufficient",
        "current_job_and_tool_gap",
        "unknown",
        "declined",
    ):
        assert value in normalized
    assert (
        "Pivot-positive is true only for prefer_different_job or "
        "existing_alternative_sufficient"
        in normalized
    )
    assert "Pivot requires at least 3 of 5 Pivot-positive records" in normalized
    assert (
        "current_job_and_tool_gap, unknown, declined, missing, and ambiguous responses do not "
        "count toward Pivot"
        in normalized
    )


def test_optional_discovery_false_ready_requires_participant_and_source_owner_evidence() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    for required in (
        "participant_false_ready",
        "confirmed, not_confirmed, or unknown",
        "Confirmed participant False Ready requires all of",
        "saved review final gate is Ready and bound to the exact reviewed head",
        "participant identifies a specific must-have criterion",
        "source owner confirms explicit missing or conflicting acceptance evidence",
        "evidence_snapshot_sha256 binds the complete confirmation record",
        "Any missing condition classifies the record as unknown, never not_confirmed",
    ):
        assert required in normalized


def test_optional_discovery_unknown_false_ready_blocks_continue() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    assert (
        "Continue requires all 5 of 5 participant_false_ready values to be not_confirmed"
        in normalized
    )
    assert "A confirmed value triggers Stop; unknown keeps the cohort on hold" in normalized


def test_optional_discovery_decisions_require_five_complete_records() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split()).lower()

    for field in (
        "outcome",
        "useful_gap_category",
        "decision impact",
        "reuse response",
        "alternative workflow",
        "friction_category",
        "evidence-boundary understanding",
        "participant_false_ready",
        "evidence_snapshot_sha256",
    ):
        assert field in normalized
    assert (
        "decision inputs for outcome, useful_gap_category, decision impact"
        in normalized
    )
    assert (
        "before applying the remaining stop predicates, pivot, narrow, or continue, all five "
        "records must have complete bounded decision inputs"
        in normalized
    )
    assert (
        "any missing, ambiguous, unknown, or declined required decision input keeps the cohort "
        "on hold; do not evaluate stop"
        in normalized
    )


def test_optional_discovery_non_understanding_holds_all_non_false_ready_decisions() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    assert (
        "All five evidence-boundary understanding values must be understood before evaluating "
        "any non-False-Ready Stop predicate, Pivot, Narrow, or Continue"
        in normalized
    )
    assert (
        "misunderstood, unsure, declined, missing, and ambiguous values keep the cohort on hold"
        in normalized
    )


def test_confirmed_false_ready_bypasses_the_completeness_hold() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    assert (
        "Evaluate confirmed participant False Ready before the completeness precondition"
        in normalized
    )
    assert (
        "Any confirmed record returns Stop immediately even when other cohort records are "
        "incomplete, unknown, or declined"
        in normalized
    )


def test_not_confirmed_false_ready_has_an_affirmative_evidence_predicate() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    for required in (
        "participant_false_ready is not_confirmed only when",
        "the exact-head final gate is not Ready",
        "or a Ready result has both an explicit participant no-False-Ready statement",
        "and source-owner confirmation after checking every must-have criterion",
        "evidence_snapshot_sha256 binds that negative confirmation",
        "Otherwise classify unknown",
    ):
        assert required in normalized


def test_optional_discovery_narrow_uses_bounded_friction_categories() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(packet.replace("`", "").split())

    for value in (
        "installation_or_setup",
        "criteria_confirmation",
        "evidence_quality",
        "runtime_verification",
        "decision_or_export",
        "comparison_or_rereview",
        "other_material_friction",
        "none",
        "unknown",
        "declined",
    ):
        assert value in normalized
    assert "Narrow-positive friction category is one of" in normalized
    assert (
        "Narrow requires the same Narrow-positive friction_category in at least 3 of 5 complete "
        "records"
        in normalized
    )
    assert "none, unknown, and declined do not count toward Narrow" in normalized


def test_inbound_host_sequence_requires_separate_contact_authorization() -> None:
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(encoding="utf-8")
    normalized = " ".join(checklist.split())
    authorization = (
        "Before any reply, criteria return, supervised review, outcome request, or feedback "
        "request, record separate explicit owner authorization for participant contact."
    )
    self_service = (
        "Without that authorization, do not reply or initiate a hosted sequence; leave the "
        "inbound path self-service."
    )

    assert authorization in normalized
    assert self_service in normalized
    assert normalized.index(authorization) < normalized.index("If voluntary feedback arrives")


def test_public_alpha_onboarding_requires_inbound_case_and_completed_outcome() -> None:
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    feedback = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(encoding="utf-8")
    sprint = Path("docs/commercialization/design-partner-sprint.md").read_text(encoding="utf-8")
    case_url = "https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml"

    assert quickstart.index(case_url) < quickstart.index("## Ten-minute path")
    assert "Submit the inbound public-alpha case form before starting locally" in quickstart
    assert "submit the inbound\npublic-alpha case form before starting locally" in readme
    assert "incomplete review" not in site

    outcome_block = feedback.split("id: outcome", maxsplit=1)[1].split("validations:", maxsplit=1)[
        0
    ]
    assert [
        line.strip()[2:] for line in outcome_block.splitlines() if line.strip().startswith("- ")
    ] == [
        "Found a useful previously unknown gap",
        "Produced only already-known information",
        "Created material product friction",
    ]
    assert "Completed reviews only" in feedback
    assert "Independently observed timing evidence" in feedback
    assert "Independent timing support" in feedback
    assert "Prefer not to answer" in feedback

    completed_signals = sprint.split(
        "## Signals recorded only after a completed review", maxsplit=1
    )[1].split("## Research-only price hypotheses", maxsplit=1)[0]
    assert "inspectable report" not in completed_signals
    assert "incomplete review" not in completed_signals


def test_public_alpha_mobile_navigation_and_closed_stage_state_are_truthful() -> None:
    site = Path("site/index.html").read_text(encoding="utf-8")
    css = Path("site/styles.css").read_text(encoding="utf-8")
    current_sections = (
        Path("ROADMAP.md").read_text(encoding="utf-8").split(
            "## Stage 1 — Genuine public alpha", maxsplit=1
        )[1],
        Path("CHANGELOG.md").read_text(encoding="utf-8").split(
            "## Unreleased", maxsplit=1
        )[1].split("## 0.2.3", maxsplit=1)[0],
        Path("docs/alpha/participant-evidence-unblocker.md").read_text(encoding="utf-8"),
        Path("docs/alpha/concierge-host-checklist.md").read_text(encoding="utf-8"),
        Path("docs/commercialization/design-partner-sprint.md").read_text(encoding="utf-8"),
    )

    mobile_css = css.split("@media (max-width: 600px)", maxsplit=1)[1]
    assert '<a href="#alpha">Public alpha</a>' in site
    assert ".site-header {" in mobile_css
    assert "align-items: stretch" in mobile_css
    assert "flex-direction: column" in mobile_css
    assert ".brand { white-space: nowrap;" in mobile_css
    assert "nav { display: flex;" in mobile_css
    for current_section in current_sections:
        assert "closed_not_pursued_by_owner" in current_section
        assert "waiting_for_inbound_public_alpha_submission" not in current_section


def test_public_design_partner_positioning_is_free_inbound_and_noncommercial() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(encoding="utf-8")
    outcome = Path("docs/alpha/outcome-form.md").read_text(encoding="utf-8")
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(encoding="utf-8")
    readme_status = readme.split("## Product status", maxsplit=1)[1].split(
        "## GitHub Action advanced preview", maxsplit=1
    )[0]
    site_alpha = site.split('<section id="alpha"', maxsplit=1)[1].split(
        "</section>", maxsplit=1
    )[0]

    guide = "docs/commercialization/design-partner-sprint.md"
    feedback_url = (
        "https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-feedback.yml"
    )
    assert guide in readme
    assert "../commercialization/design-partner-sprint.md" in quickstart
    assert guide in site
    assert feedback_url in site
    assert feedback_url in quickstart
    assert "../commercialization/design-partner-sprint.md" in outcome
    assert "../commercialization/design-partner-sprint.md" in checklist

    for public_surface in (readme_status, site_alpha):
        normalized_surface = " ".join(public_surface.split()).lower()
        for required in (
            "free design-partner review",
            "no paid product or billing is active",
            "external commercial discovery is optional and separate",
            "public-repository-only",
            "acceptance-coverage assistant",
            "not an ai code reviewer",
            "stage 1 is closed as not pursued",
            "owner-led stage 2 productization is active without claiming customer validation",
            "public feedback form contains no pricing question",
        ):
            assert required in normalized_surface
        for unsupported_claim in (
            "scopeproof customers",
            "validated pricing",
            "paid plan is available",
            "proven commercial demand",
            "pricing question is optional research after product use",
            "validating the requirement-to-evidence workflow",
            "next product decision must be based on repeat use",
            "evidence-gated path from engineering-complete public alpha to limited beta",
        ):
            assert unsupported_claim not in normalized_surface

    assert "Incomplete reviews do not become completed feedback outcomes" in site
    assert "participant-selected outcome" in quickstart
    assert "not commercial validation" in outcome


def test_r001_public_engineering_research_record_is_hash_bound_and_stage_safe() -> None:
    research_dir = Path("docs/research/r001-microsoft-hve-core")
    requirements_path = research_dir / "acceptance-criteria.txt"
    before_path = research_dir / "before.md"
    after_path = research_dir / "after.md"
    summary_path = research_dir / "summary.md"

    assert requirements_path.is_file()
    assert list(Path("docs/research").rglob("requirements*.txt")) == []
    assert before_path.is_file()
    assert after_path.is_file()
    assert summary_path.is_file()

    requirements = requirements_path.read_text(encoding="utf-8")
    assert sha256(requirements.encode("utf-8")).hexdigest() == (
        "07ee2fa337b4e2b992bd9d6d39753237dd167be48456a548dd2ff36201b8fcdd"
    )
    assert len(requirements.splitlines()) == 6

    before = before_path.read_text(encoding="utf-8")
    after = after_path.read_text(encoding="utf-8")
    summary = summary_path.read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    immutable_pr = "https://github.com/microsoft/hve-core/pull/2149"
    reviewed_head = "8e5277e88f0ca650549d41255eb24d74afc74772"
    for document in (before, after, summary):
        assert immutable_pr in document
        assert reviewed_head in document
        assert "public engineering research" in document.lower()
        assert "does not advance Stage 1" in document
        assert "No Microsoft repository code was executed" in document
        assert "not runtime proof" in document
    assert "bc114f4825aaf8c114b47a0509fc4d3235ff3708d771bc81b8fc0048903c0f39" in before
    assert "/tmp/scopeproof-r001-before.rpLI3m" in before
    assert "ephemeral provenance" in before
    for fact in (
        "Ingestion was `complete`, with zero warnings and zero skipped changed files.",
        "**94 total**, **89 success**",
        "**5 skipped** check runs",
        "Classification: `public_engineering_research`; Stage 1 credit: `0`.",
        "47 E1 documentation candidates plus one E2 test",
        "No manual runtime evidence, resolutions, reviewer decisions, or final acceptance exists.",
        "gate remains `blocked` for `blocking_criteria` and `unresolved_criteria`.",
    ):
        assert fact in after
    for skipped_check in (
        "`Eval Validation / Eval Report`",
        "`Eval Validation / Eval Execute (${{ matrix.kind }})`",
        "`ADR Consistency Validation / Upload ADR SARIF`",
        "`ADR Consistency Validation / Validate ADR Consistency`",
        "`Docusaurus Tests / Docusaurus Unit Tests`",
    ):
        assert skipped_check in after
    assert "skipped and provide no runtime proof" in after
    assert "closed_not_pursued_by_owner" in roadmap
    assert "Stage 1 did not pass" in roadmap
    assert "owner_led_productization_active" in roadmap
    assert "Stage 4 requires a named constraint" in roadmap
    assert "r001-microsoft-hve-core" in readme
    assert "R-001" in changelog


def test_pages_workflow_is_sha_pinned_minimal_and_deploys_only_static_site() -> None:
    workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert "  push:\n    branches: [main]\n  workflow_dispatch:" in workflow
    assert "pull_request_target" not in workflow
    assert "schedule:" not in workflow
    assert "contents: read" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0" in workflow
    assert "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d # v6.0.0" in workflow
    assert (
        "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0"
        in workflow
    )
    assert "actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128 # v5.0.0" in workflow
    assert "path: site" in workflow
    assert "github-pages" in workflow
    assert "cancel-in-progress: true" in workflow
    for line in workflow.splitlines():
        if "uses:" in line:
            reference = line.split("@", maxsplit=1)[1].split()[0]
            assert len(reference) == 40
            assert all(character in "0123456789abcdef" for character in reference)
