from pathlib import Path


def test_action_workflow_uses_minimal_permissions_and_nonblocking_default() -> None:
    workflow = Path(".github/workflows/scopeproof.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "contents: read" in workflow
    assert "pull-requests: write" in workflow
    assert "checks: write" in workflow
    assert "SCOPEPROOF_REQUIRED_CHECK: false" in workflow
    assert "pull_request_target" not in workflow


def test_example_requires_checked_in_confirmed_requirements_file() -> None:
    example = Path("examples/github-actions/scopeproof.yml").read_text(encoding="utf-8")

    assert ".scopeproof/requirements.txt" in example
    assert "SCOPEPROOF_REQUIRED_CHECK" in example


def test_publish_step_has_no_orphaned_shell_branch_terminator() -> None:
    workflow = Path(".github/workflows/scopeproof.yml").read_text(encoding="utf-8")

    assert "--publish-comment\n          fi" not in workflow
    assert "scopeproof review --pr" in workflow
    assert "--verdict \"$SCOPEPROOF_VERDICT\"" in workflow
