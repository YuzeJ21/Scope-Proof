import json
import re
import tomllib
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from struct import unpack
from typing import Literal
from urllib.parse import urlsplit

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

PUBLIC_RELEASE_VERSION = "0.2.3"
PUBLIC_RELEASE_TAG = "v0.2.3"
PUBLIC_RELEASE_WHEEL_FILENAME = "scopeproof-0.2.3-py3-none-any.whl"
PUBLIC_RELEASE_DOWNLOAD_ROOT = (
    "https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.2.3"
)
PUBLIC_RELEASES_INDEX = "https://github.com/YuzeJ21/Scope-Proof/releases"
PR183_SOURCE_MERGE_SHA = "cd362a85a558645a0f56d6540f6bf035e5821809"
PR183_EXACT_MAIN_RUN_IDS = ("30847416893", "30847415556", "30847417705")
PR184_RELEASE_MERGE_SHA = "448c42758ea139bf9203cbf1bb04b02b02ae412c"
PR184_EXACT_MAIN_RUN_IDS = ("30854382641", "30854382413", "30854382659")


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
    assert "Stages 2\u20134 remain gated" in roadmap


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
    assert "Streamlit 1.59.2" in guide
    assert "Streamlit 1.57.0" in guide
    assert "testing-interface regression" in guide
    assert "locked-environment:" in workflow
    assert "astral-sh/setup-uv@" not in workflow
    assert "python -m pip install uv==0.11.29" in workflow
    assert "python -m uv sync --extra dev --extra research --locked" in workflow
    assert "python -m uv run python -m pytest -q tests/test_repository_contracts.py" in workflow
    assert "python -m uv run scopeproof benchmark" in workflow
    assert "needs: [compatibility-python-311, locked-environment]" in workflow
    assert "[reproducible development environment](docs/development-environment.md)" in readme


def test_locked_gitpython_excludes_known_command_execution_advisories() -> None:
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    versions = [
        package["version"]
        for package in lock["package"]
        if package["name"].casefold() == "gitpython"
    ]

    assert len(versions) == 1
    assert tuple(int(part) for part in versions[0].split(".")) >= (3, 1, 55)


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
    assert f'__version__ = "{PUBLIC_RELEASE_VERSION}"' in version_source


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


def test_ci_validates_declared_minimum_python() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    compatibility = workflow.split("  compatibility-python-311:", maxsplit=1)[1].split(
        "\n  verify:", maxsplit=1
    )[0]
    verify = workflow.split("\n  verify:", maxsplit=1)[1]

    assert 'python-version: "3.11"' in compatibility
    assert "python -m pytest -q" in compatibility
    assert "python -m scopeproof_core.evals.runner" in compatibility
    assert "python -m pip wheel . --no-deps" in compatibility
    assert "scopeproof --version" in compatibility
    assert "scopeproof-web --version" in compatibility
    assert "needs: [compatibility-python-311, locked-environment]" in verify


def test_readme_documents_all_export_formats() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "`.md`, `.json`, `.csv`, or `.html`" in readme
    assert "`json`, `markdown`, `csv`, and `html`" in readme
    assert "Markdown / JSON / CSV / HTML" in readme
    assert "Markdown, JSON, CSV, and HTML exports" in readme


def test_roadmap_uses_evidence_gated_beta_stages() -> None:
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert "Five completed reviews" in roadmap
    assert "three independent practitioners" in roadmap
    assert "three public repositories" in roadmap
    assert "waiting_for_inbound_public_alpha_submission" in roadmap
    assert "source-owner-confirmed criteria" in roadmap
    assert "genuine public pull request" in roadmap
    assert "Software license decision" in roadmap
    assert "Do not create synthetic validation" in roadmap
    assert "No recurring monitor" in roadmap


def test_changelog_points_to_authoritative_release_history() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Unreleased" in changelog
    assert "github.com/YuzeJ21/Scope-Proof/releases" in changelog
    assert "does not reconstruct" in changelog


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
        assert "remains at zero" in active_status

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
    assert "does not advance Stage 1" in quickstart
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
    assert "waiting_for_inbound_public_alpha_submission" in unblocker
    assert "public PR URL" in unblocker
    assert "public HTTPS requirements source" in unblocker
    assert "explicit authority to confirm criteria" in unblocker
    assert (
        "explicit confirmation that no private or confidential information is included" in unblocker
    )
    assert "Do not start another overnight monitor" in unblocker
    assert "/goal Run ScopeProof's first genuine public-alpha case" in unblocker
    for forbidden in (
        "paid OpenAI/LLM API",
        "billing",
        "automated outreach",
        "scraping",
        "synthetic validation",
        "invented evidence",
        "fork testing",
        "GitHub issue comment",
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
    assert "Do not manually contact participants" in unblocker
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


def test_commercial_validation_guide_and_roadmap_are_evidence_gated() -> None:
    guide_path = Path("docs/commercialization/design-partner-sprint.md")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert guide_path.is_file()
    guide = guide_path.read_text(encoding="utf-8")
    for required in (
        "30-day Design Partner Sprint",
        "free",
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research hypotheses only",
        "not a purchase agreement",
        "after a genuine participant completes a review",
        "waiting_for_inbound_public_alpha_submission",
        "Local Pro",
    ):
        assert required in guide
    for non_evidence in (
        "stars",
        "views",
        "downloads",
        "issue submissions",
        "constructed demos",
        "synthetic cases",
        "owner-authored examples",
    ):
        assert non_evidence in guide

    assert "## Stage 2 — Commercial discovery" in roadmap
    assert "two independent completed participants" in roadmap
    assert "voluntarily agree to discuss the team-price hypothesis" in roadmap
    assert "Local Pro remains deferred" in roadmap
    assert "not revenue, orders, customers, paid demand, or willingness to pay" in roadmap


def test_public_alpha_feedback_collects_bounded_commercial_signals() -> None:
    template = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(encoding="utf-8")
    for field_id in (
        "public_pr",
        "alpha_case_issue",
        "reviewed_head_sha",
        "public_requirements_url",
        "source_owner",
        "outcome",
        "completion_time",
        "useful_gap_category",
        "decision_impact",
        "reuse_intent",
        "design_partner_interest",
        "friction",
        "limitations",
        "safety",
    ):
        assert f"id: {field_id}" in template

    for required_text in (
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research hypotheses only",
        "not a purchase agreement",
        "only after completing a genuine review",
        "Prefer not to answer",
        "submission alone is not validation",
    ):
        assert required_text in template

    forbidden_ids = (
        "name",
        "email",
        "linkedin_profile",
        "employer",
        "private_repository",
        "payment",
        "purchase_commitment",
        "sales_contact",
    )
    assert all(f"id: {field_id}" not in template for field_id in forbidden_ids)


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
    assert "required dropdown" in feedback
    assert "Prefer not to answer" in feedback

    completed_signals = sprint.split(
        "## Signals recorded only after a completed review", maxsplit=1
    )[1].split("## Research-only price hypotheses", maxsplit=1)[0]
    assert "inspectable report" not in completed_signals
    assert "incomplete review" not in completed_signals


def test_public_alpha_mobile_navigation_and_active_waiting_state_are_truthful() -> None:
    site = Path("site/index.html").read_text(encoding="utf-8")
    css = Path("site/styles.css").read_text(encoding="utf-8")
    active_docs = (
        Path("ROADMAP.md"),
        Path("CHANGELOG.md"),
        Path("docs/alpha/participant-evidence-unblocker.md"),
        Path("docs/alpha/concierge-host-checklist.md"),
        Path("docs/commercialization/design-partner-sprint.md"),
    )

    mobile_css = css.split("@media (max-width: 600px)", maxsplit=1)[1]
    assert '<a href="#alpha">Public alpha</a>' in site
    assert ".site-header {" in mobile_css
    assert "align-items: stretch" in mobile_css
    assert "flex-direction: column" in mobile_css
    assert ".brand { white-space: nowrap;" in mobile_css
    assert "nav { display: flex;" in mobile_css
    for path in active_docs:
        content = path.read_text(encoding="utf-8")
        assert "waiting_for_inbound_public_alpha_submission" in content
        assert "waiting_for_external_participant_evidence" not in content


def test_public_design_partner_positioning_is_free_inbound_and_noncommercial() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(encoding="utf-8")
    outcome = Path("docs/alpha/outcome-form.md").read_text(encoding="utf-8")
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(encoding="utf-8")
    public_surfaces = "\n".join((readme, site))

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

    for required in (
        "free design-partner review",
        "No paid product or billing is active",
        "pricing question is optional research after product use",
        "public-repository-only",
        "acceptance-coverage assistant",
        "not an AI code reviewer",
    ):
        assert required in public_surfaces
    for unsupported_claim in (
        "ScopeProof customers",
        "validated pricing",
        "paid plan is available",
        "proven commercial demand",
    ):
        assert unsupported_claim not in public_surfaces

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
    assert "waiting_for_inbound_public_alpha_submission" in roadmap
    assert "Entry requires every Stage 1 condition." in roadmap
    assert (
        "Entry requires every Stage 1 and Stage 2 condition plus a separate owner decision."
        in roadmap
    )
    assert "Only recurring behavior can justify broader scope." in roadmap
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
