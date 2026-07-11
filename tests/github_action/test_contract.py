from scopeproof_core.github_action import (
    CommentMode,
    EventContext,
    comment_marker,
    plan_comment,
    render_check_summary,
)


def context(*, fork: bool = False) -> EventContext:
    return EventContext(
        repository="acme/widget",
        pr_number=42,
        head_sha="head123",
        is_fork=fork,
        requirements_confirmed=True,
    )


def test_fork_event_is_non_mutating_even_with_write_token() -> None:
    plan = plan_comment(context(fork=True), [], "ScopeProof summary")

    assert plan.mode is CommentMode.SKIP
    assert plan.reason == "fork_pull_request"


def test_existing_marker_for_same_head_is_updated_not_duplicated() -> None:
    marker = comment_marker("head123")
    plan = plan_comment(context(), [{"id": 7, "body": f"old\n{marker}"}], "new summary")

    assert plan.mode is CommentMode.UPDATE
    assert plan.comment_id == 7
    assert plan.body.endswith(marker)


def test_existing_marker_for_another_head_creates_a_new_auditable_comment() -> None:
    plan = plan_comment(context(), [{"id": 7, "body": "<!-- scopeproof:old-head -->"}], "summary")

    assert plan.mode is CommentMode.CREATE
    assert plan.comment_id is None


def test_unconfirmed_requirements_cannot_emit_ready_check_summary() -> None:
    unconfirmed = EventContext(
        repository="acme/widget",
        pr_number=42,
        head_sha="head123",
        is_fork=False,
        requirements_confirmed=False,
    )
    summary = render_check_summary(unconfirmed, "ready", "Candidate evidence found")

    assert "Needs Review" in summary
    assert "requirements are not confirmed" in summary
