"""Narrow GitHub REST adapter for a pre-approved ScopeProof comment plan."""

from __future__ import annotations

import httpx

from scopeproof_core.github_action import CommentPlan, EventContext, plan_comment


def publish_comment(
    context: EventContext,
    summary: str,
    token: str,
    transport: httpx.BaseTransport | None = None,
) -> CommentPlan:
    """Apply a fork-safe, head-SHA-idempotent comment plan without logging secrets."""

    if context.is_fork:
        return plan_comment(context, [], summary)
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(
        base_url="https://api.github.com", headers=headers, transport=transport, timeout=15.0
    ) as client:
        comments_response = client.get(
            f"/repos/{context.repository}/issues/{context.pr_number}/comments",
            params={"per_page": 100},
        )
        comments_response.raise_for_status()
        plan = plan_comment(context, comments_response.json(), summary)
        if plan.mode.value == "create":
            response = client.post(
                f"/repos/{context.repository}/issues/{context.pr_number}/comments",
                json={"body": plan.body},
            )
            response.raise_for_status()
        elif plan.mode.value == "update":
            response = client.patch(
                f"/repos/{context.repository}/issues/comments/{plan.comment_id}",
                json={"body": plan.body},
            )
            response.raise_for_status()
        return plan
