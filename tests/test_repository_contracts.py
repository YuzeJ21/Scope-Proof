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
