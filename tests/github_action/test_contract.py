import pytest

from scopeproof_core.github_action import (
    CommentMode,
    EventContext,
    comment_marker,
    plan_comment,
    render_check_summary,
)

HEAD_SHA = "2" * 40
OTHER_SHA = "3" * 40


def context(*, fork: bool = False) -> EventContext:
    return EventContext(
        repository="acme/widget",
        pr_number=42,
        head_sha=HEAD_SHA,
        is_fork=fork,
        requirements_confirmed=True,
    )


def test_fork_event_is_non_mutating_even_with_write_token() -> None:
    plan = plan_comment(context(fork=True), [], "ScopeProof summary")

    assert plan.mode is CommentMode.SKIP
    assert plan.reason == "fork_pull_request"


def test_existing_marker_for_same_head_is_updated_not_duplicated() -> None:
    marker = comment_marker(HEAD_SHA)
    plan = plan_comment(context(), [{"id": 7, "body": f"old\n{marker}"}], "new summary")

    assert plan.mode is CommentMode.UPDATE
    assert plan.comment_id == 7
    assert plan.body.endswith(marker)


def test_existing_marker_for_another_head_creates_a_new_auditable_comment() -> None:
    plan = plan_comment(
        context(), [{"id": 7, "body": comment_marker(OTHER_SHA)}], "summary"
    )

    assert plan.mode is CommentMode.CREATE
    assert plan.comment_id is None


def test_unconfirmed_requirements_cannot_emit_ready_check_summary() -> None:
    unconfirmed = EventContext(
        repository="acme/widget",
        pr_number=42,
        head_sha=HEAD_SHA,
        is_fork=False,
        requirements_confirmed=False,
    )
    summary = render_check_summary(unconfirmed, "ready", "Candidate evidence found")

    assert "Needs Review" in summary
    assert "requirements are not confirmed" in summary


@pytest.mark.parametrize(
    "invalid_sha",
    ["", "   ", "x", "not-a-sha", "g" * 40, "a" * 39, "a" * 41, "A" * 40],
)
def test_event_context_rejects_invalid_head_sha_shape(invalid_sha: str) -> None:
    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        EventContext(
            repository="acme/widget",
            pr_number=42,
            head_sha=invalid_sha,
            is_fork=False,
            requirements_confirmed=True,
        )


def test_event_context_preserves_valid_head_sha_exactly() -> None:
    assert context().head_sha == HEAD_SHA


@pytest.mark.parametrize(
    "invalid_repository",
    [
        " / ",
        "ac me/de mo",
        " acme/demo",
        "acme/demo\t",
        "acme/demo/extra",
        "acme@team/demo",
        "acme/demo#repo",
    ],
)
def test_event_context_rejects_noncanonical_repository_identity(
    invalid_repository: str,
) -> None:
    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        EventContext(
            repository=invalid_repository,
            pr_number=42,
            head_sha=HEAD_SHA,
            is_fork=False,
            requirements_confirmed=True,
        )


def test_event_context_preserves_supported_repository_identity_exactly() -> None:
    repository = "acme-team/demo.repo_name-test"

    event = EventContext(
        repository=repository,
        pr_number=42,
        head_sha=HEAD_SHA,
        is_fork=False,
        requirements_confirmed=True,
    )

    assert event.repository == repository
