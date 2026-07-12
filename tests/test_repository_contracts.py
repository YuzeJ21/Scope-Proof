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


def test_ci_runs_lint_tests_and_benchmark() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python -m pip install --upgrade pip" in workflow
    assert "ruff check" in workflow
    assert "pytest" in workflow
    assert "scopeproof_core.evals.runner" in workflow


def test_readme_documents_operating_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "streamlit run apps/web/app.py" in readme
    assert "RUN_LIVE_GITHUB_TESTS=1" in readme
    assert "scopeproof_core.evals.runner" in readme


def test_readme_documents_actual_stage_2a_durability_behavior() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "12 executable benchmark cases" in readme
    assert "criteria revisions" in readme
    assert "resolution history" in readme
    assert "Local review storage" in readme
    assert "unchanged candidate" in readme


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
