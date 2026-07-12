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
    assert "actions/upload-artifact@v4" in example
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
    assert "actions/upload-artifact@v4" in workflow
    assert "scopeproof-report.md" in workflow
    assert "if-no-files-found: ignore" in workflow
    assert "--verdict \"$SCOPEPROOF_VERDICT\"" in workflow
    assert 'echo "SCOPEPROOF_VERDICT=needs_review" >> "$GITHUB_ENV"' in workflow
