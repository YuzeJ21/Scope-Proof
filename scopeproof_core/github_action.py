"""Pure, fork-safe planning for the optional ScopeProof GitHub Action.

This module deliberately makes no HTTP calls.  The workflow adapter may execute a
returned plan only after GitHub has established that the pull request is not from
a fork.  Keeping the policy here pure makes it easy to test without credentials
or GitHub-side mutation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CommentMode(StrEnum):
    """The only permitted comment actions for an Action run."""

    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


class EventContext(BaseModel):
    """The minimum trusted pull-request context needed for publication policy."""

    model_config = ConfigDict(extra="forbid")

    repository: str = Field(pattern=r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$")
    pr_number: int = Field(gt=0)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    is_fork: bool
    requirements_confirmed: bool


class CommentPlan(BaseModel):
    """A mutation decision; callers must not infer an action outside this plan."""

    mode: CommentMode
    reason: str
    body: str = ""
    comment_id: int | None = None


def comment_marker(head_sha: str) -> str:
    """Return an invisible idempotency marker scoped to one immutable PR head."""

    return f"<!-- scopeproof:{head_sha} -->"


def render_check_summary(context: EventContext, verdict: str, content: str) -> str:
    """Render an intentionally non-authoritative summary for a GitHub check."""

    if not context.requirements_confirmed:
        return (
            "## ScopeProof — Needs Review\n\n"
            "ScopeProof cannot mark this pull request Ready because the checked-in "
            "requirements are not confirmed.\n\n"
            f"{content}"
        )
    return f"## ScopeProof — {verdict.replace('_', ' ').title()}\n\n{content}"


def plan_comment(
    context: EventContext, existing_comments: list[dict[str, Any]], summary: str
) -> CommentPlan:
    """Choose create, update, or skip without making a network request.

    Fork events never receive a write plan.  For same-revision reruns, update a
    marker-matched comment; a new head SHA creates a separate audit record.
    """

    if context.is_fork:
        return CommentPlan(mode=CommentMode.SKIP, reason="fork_pull_request")

    marker = comment_marker(context.head_sha)
    body = f"{summary.rstrip()}\n\n{marker}"
    for comment in existing_comments:
        if marker in str(comment.get("body", "")):
            comment_id = comment.get("id")
            if isinstance(comment_id, int):
                return CommentPlan(
                    mode=CommentMode.UPDATE,
                    reason="same_head_marker",
                    body=body,
                    comment_id=comment_id,
                )
    return CommentPlan(mode=CommentMode.CREATE, reason="new_head_marker", body=body)
