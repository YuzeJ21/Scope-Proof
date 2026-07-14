import tomllib
from pathlib import Path


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


def test_wheel_includes_bundled_benchmark_data() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert wheel["force-include"]["evals"] == "evals"
    assert list(Path("evals/fixtures").glob("*.json"))
    assert list(Path("evals/labels").glob("*.json"))


def test_ci_runs_lint_tests_and_benchmark() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python -m pip install --upgrade pip" in workflow
    assert "ruff check" in workflow
    assert "pytest" in workflow
    assert "scopeproof_core.evals.runner" in workflow


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


def test_readme_documents_operating_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "streamlit run apps/web/app.py" in readme
    assert "RUN_LIVE_GITHUB_TESTS=1" in readme
    assert "scopeproof_core.evals.runner" in readme


def test_readme_separates_release_install_from_contributor_setup() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert (
        "https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.1.19/"
        "scopeproof-0.1.19-py3-none-any.whl"
    ) in readme
    assert "scopeproof benchmark" in readme
    assert "scopeproof-web --host 127.0.0.1 --port 8501" in readme
    assert "## Contributor setup" in readme
    assert "python -m pip install -e '.[dev]'" in readme
    assert "streamlit run apps/web/app.py" in readme
    assert "scopeproof web" not in readme


def test_readme_documents_optional_release_checksum_verification() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    wheel_name = "scopeproof-0.1.19-py3-none-any.whl"

    assert f"releases/download/v0.1.19/{wheel_name}" in readme
    assert f"releases/download/v0.1.19/{wheel_name}.sha256" in readme
    assert f"shasum -a 256 -c {wheel_name}.sha256" in readme
    assert f"sha256sum -c {wheel_name}.sha256" in readme
    assert f"python -m pip install ./{wheel_name}" in readme
    assert "does not provide code-signing or product-correctness assurance" in readme


def test_project_exposes_web_launcher_without_coupling_core_to_ui() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["scripts"]["scopeproof-web"] == "apps.web.launcher:main"
    core_cli = Path("scopeproof_core/cli.py").read_text(encoding="utf-8")
    assert "streamlit" not in core_cli
    assert "apps.web" not in core_cli


def test_hatch_and_reviews_share_one_version_source() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version_source = Path("scopeproof_core/version.py").read_text(encoding="utf-8")

    assert config["project"]["dynamic"] == ["version"]
    assert "version" not in config["project"]
    assert config["tool"]["hatch"]["version"]["path"] == "scopeproof_core/version.py"
    assert '__version__ = "0.1.19"' in version_source


def test_readme_documents_confirmed_public_pr_cli_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof review --pr" in readme
    assert "--requirements requirements.txt" in readme
    assert "scopeproof export" in readme
    assert "reviewer-confirmed criteria" in readme
    assert "not required or persisted" in readme


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


def test_launch_matrix_distinguishes_local_action_fixtures_from_recorded_run() -> None:
    matrix = Path("docs/launch/evidence-matrix.md").read_text(encoding="utf-8")

    assert "Local GitHub Action fixtures" in matrix
    assert "same-repository run and same-head rerun" in matrix
    assert "docs/launch/non-fork-action-validation.md" in matrix
    assert "source-owner-confirmed acceptance criteria" in matrix.lower()


def test_public_docs_do_not_require_or_offer_external_fork_validation() -> None:
    public_docs = {
        "README.md": Path("README.md").read_text(encoding="utf-8"),
        "docs/privacy-readiness.md": Path("docs/privacy-readiness.md").read_text(
            encoding="utf-8"
        ),
    }
    combined = "\n".join(public_docs.values()).lower()

    assert "fork evidence required" not in combined
    assert "same-head rerun, and fork evidence" not in combined
    assert "external fork validation is optional" not in combined
    assert "fork testing is permanently excluded" in combined
