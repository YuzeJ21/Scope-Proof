import re
import subprocess
from pathlib import Path

from scopeproof_core.criteria.confirmation import validate_requirements_confirmation


def test_action_workflow_uses_minimal_permissions_and_nonblocking_default() -> None:
    workflow = Path(".github/workflows/scopeproof.yml").read_text(encoding="utf-8")
    checkout = workflow.split("- uses: actions/checkout@", maxsplit=1)[1].split(
        "- uses: actions/setup-python@", maxsplit=1
    )[0]

    assert "pull_request:" in workflow
    assert "pull_request_target:" not in workflow
    assert "contents: read" in workflow
    assert "pull-requests: read" in workflow
    assert "checks: write" in workflow
    assert "SCOPEPROOF_REQUIRED_CHECK: false" in workflow
    assert "ref: ${{ github.event.pull_request.base.sha }}" in workflow
    assert "persist-credentials: false" in workflow
    assert "pull_request.head.sha" not in checkout
    assert "gh pr checkout" not in workflow
    assert "git fetch" not in workflow


def test_workflows_serialize_same_pull_request_head_publication() -> None:
    for path in (
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")

        assert "concurrency:" in workflow
        assert (
            "group: scopeproof-${{ github.repository }}-"
            "${{ github.event.pull_request.number }}-"
            "${{ github.event.pull_request.head.sha }}"
        ) in workflow
        assert "cancel-in-progress: false" in workflow


def test_workflows_withdraw_exact_head_check_when_opt_in_label_is_removed() -> None:
    for path in (
        Path(".github/workflows/scopeproof-withdraw.yml"),
        Path("examples/github-actions/scopeproof-withdraw.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")

        assert "pull_request_target:" in workflow
        assert "types: [unlabeled]" in workflow
        withdrawal = workflow.split("jobs:\n  withdraw:", maxsplit=1)[1]
        assert "github.event.action == 'unlabeled'" in withdrawal
        assert "github.event.label.name == 'scopeproof-review'" in withdrawal
        assert "github.event.pull_request.head.repo.full_name == github.repository" in withdrawal
        assert "--withdraw-check" in withdrawal
        assert "--publish-check" not in withdrawal
        assert "scopeproof review --pr" not in withdrawal
        assert "ref: ${{ github.event.pull_request.base.sha }}" in withdrawal
        assert "persist-credentials: false" in withdrawal

    for path in (
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")
        assert "pull_request_target:" not in workflow
        assert "  withdraw:" not in workflow
        assert "pull_request.head.repo.fork" not in workflow
        assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow


def test_failed_or_empty_export_cannot_publish_a_ready_report() -> None:
    for path in (
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")

        assert (
            'scopeproof-report.tmp.md" &&\n'
            '              [ -s "$RUNNER_TEMP/scopeproof-report.tmp.md" ]'
        ) in workflow
        assert (
            '[ -s "$RUNNER_TEMP/scopeproof-report.tmp.md" ] &&\n'
            '              mv "$RUNNER_TEMP/scopeproof-report.tmp.md" '
            '"$RUNNER_TEMP/scopeproof-report.md"; then'
        ) in workflow
        assert 'echo "SCOPEPROOF_VERDICT=needs_review" >> "$GITHUB_ENV"' in workflow
        assert workflow.count('if [ -s "$RUNNER_TEMP/scopeproof-report.md" ]; then') == 2
        assert 'if [ -f "$RUNNER_TEMP/scopeproof-report.md" ]; then' not in workflow


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
            '> "$RUNNER_TEMP/scopeproof-result.json"', maxsplit=1
        )[0]
        assert "--requirements .scopeproof/requirements.txt" in review_command
        assert "--confirmation .scopeproof/requirements-confirmation.json" in review_command
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
    examples = (
        Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8"),
        Path("examples/github-actions/scopeproof-withdraw.yml").read_text(encoding="utf-8"),
    )
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    reviewed_revision = "fd9308a6e94800f84bcdc41260f527fc030e0e94"

    for example in examples:
        assert "pip install scopeproof" not in example
        assert (
            f"scopeproof @ git+https://github.com/YuzeJ21/Scope-Proof.git@{reviewed_revision}"
        ) in example
    assert reviewed_revision in guide


def test_copyable_source_pin_supports_the_confirmation_contract() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")
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
    runner_at_pin = subprocess.run(
        ["git", "show", f"{pinned_revision}:scopeproof_core/github_action_runner.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    publisher_at_pin = subprocess.run(
        [
            "git",
            "show",
            f"{pinned_revision}:scopeproof_core/github_action_publisher.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    planner_at_pin = subprocess.run(
        ["git", "show", f"{pinned_revision}:scopeproof_core/github_action.py"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    workflow_at_pin = subprocess.run(
        ["git", "show", f"{pinned_revision}:.github/workflows/scopeproof.yml"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    withdrawal_workflow_at_pin = subprocess.run(
        [
            "git",
            "show",
            f"{pinned_revision}:.github/workflows/scopeproof-withdraw.yml",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert re.search(r'review\.add_argument\(\s*"--confirmation",\s*required=True', cli_at_pin)
    assert "validate_requirements_confirmation" in cli_at_pin
    assert "prepare-requirements-confirmation" in cli_at_pin
    assert "CriteriaSourceProvenance.model_validate_json" in confirmation_at_pin
    assert "validate_criteria_source_confirmation" in confirmation_at_pin
    assert "class ReviewInputOrigin" in models_at_pin
    assert "LIVE_PUBLIC_GITHUB" in alpha_service_at_pin
    assert 'parser.add_argument("--publish-check"' in runner_at_pin
    assert 'parser.add_argument("--invalidate-check"' in runner_at_pin
    assert 'parser.add_argument("--validate-result"' in runner_at_pin
    assert "def publish_check(" in publisher_at_pin
    assert '"check_name": CHECK_NAME' in publisher_at_pin
    assert "class CheckRunPlan" in planner_at_pin
    assert '"conditional": "Conditional"' in planner_at_pin
    assert "concurrency:" in workflow_at_pin
    assert "scopeproof-report.tmp.md" in workflow_at_pin
    assert 'scopeproof-report.md"; then' in workflow_at_pin
    assert "pull_request_target:" not in workflow_at_pin
    assert "head.repo.full_name == github.repository" in workflow_at_pin
    assert "pull_request_target:" in withdrawal_workflow_at_pin
    assert "types: [unlabeled]" in withdrawal_workflow_at_pin
    assert "--withdraw-check" in withdrawal_workflow_at_pin
    assert "applicability_label_expected" in publisher_at_pin


def test_ci_checkouts_include_history_for_source_pin_contract() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    python_313_compatibility = workflow.split("  compatibility-python-313:", maxsplit=1)[1].split(
        "\n  compatibility-windows:", maxsplit=1
    )[0]
    windows_compatibility = workflow.split("  compatibility-windows:", maxsplit=1)[1].split(
        "\n  locked-environment:", maxsplit=1
    )[0]

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
    assert "pull_request:" in example
    assert "pull_request_target:" not in example
    assert "ref: ${{ github.event.pull_request.base.sha }}" in example
    assert "persist-credentials: false" in example
    assert "requirements-confirmation.json" in example
    assert "checks: write" in example
    assert "actions/upload-artifact@" in example
    assert "Emit fork-safe ScopeProof summary plan" in example
    assert "Fork pull requests never receive a write request." in example


def test_publish_step_has_no_orphaned_shell_branch_terminator() -> None:
    workflow = Path(".github/workflows/scopeproof.yml").read_text(encoding="utf-8")

    assert "--publish-comment" not in workflow
    assert "--publish-check" in workflow
    assert "--invalidate-check" in workflow
    assert "scopeproof review --pr" in workflow
    assert 'scopeproof export "$review_id"' in workflow
    assert "validate-requirements-confirmation" in workflow
    assert "SCOPEPROOF_REQUIREMENTS_CONFIRMED=true" in workflow
    assert "--validate-result" in workflow
    assert '--content-file "$RUNNER_TEMP/scopeproof-report.md"' in workflow
    assert "actions/upload-artifact@" in workflow
    assert "scopeproof-report.md" in workflow
    assert "if-no-files-found: ignore" in workflow
    assert '--verdict "$SCOPEPROOF_VERDICT"' in workflow
    assert 'echo "SCOPEPROOF_VERDICT=needs_review" >> "$GITHUB_ENV"' in workflow
    assert workflow.index("--validate-result") < workflow.index('print("SCOPEPROOF_VERDICT="')
    assert workflow.index("--validate-result") < workflow.index('scopeproof export "$review_id"')


def test_workflows_publish_only_exact_file_bound_neutral_checks() -> None:
    for path in (
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")
        checkout = workflow.split("- uses: actions/checkout@", maxsplit=1)[1].split(
            "- uses: actions/setup-python@", maxsplit=1
        )[0]
        publish = workflow.split("Publish exact-head informational Check", maxsplit=1)[1].split(
            "- name: Publication boundary", maxsplit=1
        )[0]

        assert "--requirements .scopeproof/requirements.txt" in publish
        assert "--confirmation .scopeproof/requirements-confirmation.json" in publish
        assert '--verdict "$SCOPEPROOF_VERDICT"' in publish
        assert '--content-file "$RUNNER_TEMP/scopeproof-report.md"' in publish
        assert "--publish-check" in publish
        assert "--invalidate-check" in publish
        assert 'if [ "$SCOPEPROOF_REQUIREMENTS_CONFIRMED" = "true" ]; then' in publish
        assert "requirements confirmation is unavailable or does not match" not in publish
        assert "--publish-comment" not in workflow
        assert "pull_request_target" not in workflow
        assert "pull_request.head.sha" not in checkout
        assert "gh pr checkout" not in workflow
        assert "git fetch" not in workflow
        assert "ref: ${{ github.event.pull_request.base.sha }}" in workflow
        assert "persist-credentials: false" in workflow
        assert "checks: write" in workflow
        assert "pull-requests: read" in workflow


def test_all_third_party_actions_are_pinned_to_immutable_commit_shas() -> None:
    workflow_paths = (
        Path(".github/workflows/ci.yml"),
        Path(".github/workflows/scopeproof.yml"),
        Path(".github/workflows/scopeproof-withdraw.yml"),
        Path("examples/github-actions/scopeproof.yml"),
        Path("examples/github-actions/scopeproof-withdraw.yml"),
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


def test_action_guidance_defines_exact_head_neutral_check_lifecycle() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    runbook = Path("docs/github-action-external-validation.md").read_text(encoding="utf-8")
    combined = " ".join((readme, guide, runbook))
    normalized_guide = " ".join(guide.split())

    for required in (
        "ScopeProof evidence summary (informational)",
        "same-head",
        "new head",
        "neutral",
        "criteria-source",
        "fork",
        "missing token",
        "stale head",
        "not a required branch-protection check",
        "asserted, not authenticated",
    ):
        assert required.lower() in combined.lower()
    assert "same-head rerun updates" in normalized_guide
    assert "new head creates" in normalized_guide
    assert "Legacy comment APIs remain backward compatible" in normalized_guide
    assert "workflow does not invoke them" in normalized_guide
