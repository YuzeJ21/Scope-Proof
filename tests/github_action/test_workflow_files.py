import re
import subprocess
from pathlib import Path

from scopeproof_core.criteria.confirmation import validate_requirements_confirmation


def test_action_workflow_uses_minimal_permissions_and_nonblocking_default() -> None:
    workflow = Path(".github/workflows/scopeproof.yml").read_text(encoding="utf-8")

    assert "pull_request_target:" in workflow
    assert "contents: read" in workflow
    assert "pull-requests: write" in workflow
    assert "SCOPEPROOF_REQUIRED_CHECK: false" in workflow
    assert "pull_request:" not in workflow
    assert "ref: ${{ github.event.pull_request.base.sha }}" in workflow
    assert "persist-credentials: false" in workflow
    assert "pull_request.head.sha" not in workflow
    assert "gh pr checkout" not in workflow
    assert "git fetch" not in workflow


def test_repository_action_workflow_uses_the_locked_environment() -> None:
    workflow = Path(".github/workflows/scopeproof.yml").read_text(encoding="utf-8")

    assert "python -m pip install uv==0.11.29" in workflow
    assert "python -m uv sync --frozen" in workflow
    assert "python -m uv run --frozen scopeproof review --pr" in workflow
    assert "python -m uv run --frozen scopeproof export" in workflow
    assert "run: pip install ." not in workflow


def test_trusted_base_workflows_pass_validated_confirmation_into_review() -> None:
    for path in (
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")
        review_command = workflow.split("scopeproof review --pr", maxsplit=1)[1].split(
            "> \"$RUNNER_TEMP/scopeproof-result.json\"", maxsplit=1
        )[0]
        assert "--requirements .scopeproof/requirements.txt" in review_command
        assert (
            "--confirmation .scopeproof/requirements-confirmation.json"
            in review_command
        )
        assert workflow.index("validate-requirements-confirmation") < workflow.index(
            "scopeproof review --pr"
        )


def test_example_requires_checked_in_confirmed_requirements_file() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")

    assert ".scopeproof/requirements.txt" in example
    assert "SCOPEPROOF_REQUIRED_CHECK" in example


def test_repository_confirmation_is_a_valid_typed_source_snapshot() -> None:
    confirmation = validate_requirements_confirmation(
        Path(".scopeproof/requirements.txt"),
        Path(".scopeproof/requirements-confirmation.json"),
    )

    assert confirmation.source_uri == (
        "https://github.com/YuzeJ21/Scope-Proof/blob/"
        "a2fdecbd5918535f4db35bfdf7da64156f393b67/.scopeproof/requirements.txt"
    )
    assert confirmation.source_revision == "a2fdecbd5918535f4db35bfdf7da64156f393b67"


def test_copyable_example_installs_a_pinned_public_scopeproof_revision() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    reviewed_revision = "d553791cba83d9f756b2adce22bd814872b73ea2"

    assert "pip install scopeproof" not in example
    assert (
        "scopeproof @ git+https://github.com/YuzeJ21/Scope-Proof.git@"
        f"{reviewed_revision}"
    ) in example
    assert reviewed_revision in guide


def test_copyable_source_pin_supports_the_confirmation_contract() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(
        encoding="utf-8"
    )
    install = re.search(
        r"scopeproof @ git\+https://github\.com/YuzeJ21/Scope-Proof\.git@([0-9a-f]{40})",
        example,
    )
    assert install is not None
    pinned_revision = install.group(1)

    cli_at_pin = subprocess.run(
        ["git", "show", f"{pinned_revision}:scopeproof_core/cli.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    confirmation_at_pin = subprocess.run(
        [
            "git",
            "show",
            f"{pinned_revision}:scopeproof_core/criteria/confirmation.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    models_at_pin = subprocess.run(
        ["git", "show", f"{pinned_revision}:scopeproof_core/schemas/models.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    alpha_service_at_pin = subprocess.run(
        ["git", "show", f"{pinned_revision}:scopeproof_core/alpha/service.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert re.search(
        r'review\.add_argument\(\s*"--confirmation",\s*required=True', cli_at_pin
    )
    assert "validate_requirements_confirmation" in cli_at_pin
    assert "prepare-requirements-confirmation" in cli_at_pin
    assert "CriteriaSourceProvenance.model_validate_json" in confirmation_at_pin
    assert "validate_criteria_source_confirmation" in confirmation_at_pin
    assert "class ReviewInputOrigin" in models_at_pin
    assert "LIVE_PUBLIC_GITHUB" in alpha_service_at_pin


def test_ci_checkouts_include_history_for_source_pin_contract() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    python_313_compatibility = workflow.split(
        "  compatibility-python-313:", maxsplit=1
    )[1].split("\n  compatibility-windows:", maxsplit=1)[0]
    windows_compatibility = workflow.split(
        "  compatibility-windows:", maxsplit=1
    )[1].split("\n  locked-environment:", maxsplit=1)[0]

    assert workflow.count("fetch-depth: 0") == 5
    assert "fetch-depth: 0" in python_313_compatibility
    assert "fetch-depth: 0" in windows_compatibility


def test_single_account_alpha_policy_explicitly_skips_external_fork_testing() -> None:
    runbook = Path("docs/github-action-external-validation.md").read_text(encoding="utf-8")
    privacy = Path("docs/privacy-readiness.md").read_text(encoding="utf-8")

    normalized_runbook = " ".join(runbook.split())
    assert "Single-account public alpha policy" in runbook
    assert "fork testing is permanently excluded." in normalized_runbook
    assert "Optional Test 3" not in runbook
    assert "single-account public alpha" in privacy


def test_public_action_guidance_matches_the_trusted_base_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    privacy = Path("docs/privacy-readiness.md").read_text(encoding="utf-8")
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")

    assert "never uses `pull_request_target`" not in readme
    assert "workflow uses the trusted base definition" in privacy
    assert "pull_request_target:" in example
    assert "ref: ${{ github.event.pull_request.base.sha }}" in example
    assert "persist-credentials: false" in example
    assert "requirements-confirmation.json" in example
    assert "checks: write" not in example
    assert "actions/upload-artifact@" in example
    assert "Emit fork-safe ScopeProof summary and comment plan" in example
    assert "Fork pull requests never receive a write request." in example


def test_publish_step_has_no_orphaned_shell_branch_terminator() -> None:
    workflow = Path(".github/workflows/scopeproof.yml").read_text(encoding="utf-8")

    assert "--publish-comment\n          fi" not in workflow
    assert "scopeproof review --pr" in workflow
    assert "scopeproof export \"$review_id\"" in workflow
    assert "validate-requirements-confirmation" in workflow
    assert "SCOPEPROOF_REQUIREMENTS_CONFIRMED=true" in workflow
    assert "--content-file \"$RUNNER_TEMP/scopeproof-report.md\"" in workflow
    assert "actions/upload-artifact@" in workflow
    assert "scopeproof-report.md" in workflow
    assert "if-no-files-found: ignore" in workflow
    assert "--verdict \"$SCOPEPROOF_VERDICT\"" in workflow
    assert 'echo "SCOPEPROOF_VERDICT=needs_review" >> "$GITHUB_ENV"' in workflow


def test_all_third_party_actions_are_pinned_to_immutable_commit_shas() -> None:
    workflow_paths = (
        Path(".github/workflows/ci.yml"),
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    )

    for path in workflow_paths:
        uses_references = re.findall(r"uses:\s+([^\s]+)", path.read_text(encoding="utf-8"))
        assert uses_references
        for reference in uses_references:
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", reference), reference


def test_workflows_use_the_vetted_node24_action_revisions() -> None:
    expected_references = {
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    }

    for path in (
        Path(".github/workflows/ci.yml"),
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        contents = path.read_text(encoding="utf-8")
        for reference in expected_references:
            if "upload-artifact" in reference and path.name == "ci.yml":
                continue
            assert reference in contents, f"{path}: {reference}"


def test_action_requires_explicit_per_pr_requirements_applicability() -> None:
    for path in (
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")
        assert "types: [opened, reopened, synchronize, labeled]" in workflow
        assert re.search(
            r"(?m)^jobs:\n"
            r"  review:\n"
            r"    if: contains\(github\.event\.pull_request\.labels\.\*\.name, "
            r"'scopeproof-review'\)$",
            workflow,
        )
        assert "paths:" not in workflow
        assert "github.event.pull_request.user" not in workflow


def test_action_guidance_requires_maintainer_applicability_opt_in() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    runbook = Path("docs/github-action-external-validation.md").read_text(encoding="utf-8")

    assert "## GitHub Action advanced preview" in readme
    assert "[GitHub Actions\nguide](docs/github-action.md)" in readme
    assert "not part of first use" in readme

    for document in (guide, runbook):
        assert "`scopeproof-review`" in document
        assert "not reviewed, not Ready" in document
    assert "repository maintainer" in guide
    assert "checked-in requirements apply to this PR" in guide


def test_action_guidance_requires_fresh_applicability_review_after_byte_changes() -> None:
    for path in (
        Path("docs/github-action.md"),
        Path("docs/github-action-external-validation.md"),
    ):
        document = " ".join(path.read_text(encoding="utf-8").split())
        assert "requirements bytes change" in document
        assert "remove `scopeproof-review`" in document
        assert "review the new confirmed text for applicability" in document
        assert "reapply the label" in document
