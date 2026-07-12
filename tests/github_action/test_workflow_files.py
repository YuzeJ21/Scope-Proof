import re
from pathlib import Path


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


def test_example_requires_checked_in_confirmed_requirements_file() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")

    assert ".scopeproof/requirements.txt" in example
    assert "SCOPEPROOF_REQUIRED_CHECK" in example


def test_copyable_example_installs_a_pinned_public_scopeproof_revision() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")

    assert "pip install scopeproof" not in example
    assert (
        "scopeproof @ git+https://github.com/YuzeJ21/Scope-Proof.git@"
        "6bbd20008acc62ff4fa9d98378e6c652fc1c5abe"
    ) in example


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
