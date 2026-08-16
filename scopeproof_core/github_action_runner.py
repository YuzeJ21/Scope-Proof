"""Read a GitHub pull-request event and emit a non-mutating ScopeProof plan."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scopeproof_core.criteria.confirmation import validate_requirements_confirmation
from scopeproof_core.github_action import (
    CheckMode,
    CheckRunContext,
    CheckRunPlan,
    CommentMode,
    CommentPlan,
    EventContext,
    plan_comment,
    render_check_summary,
)
from scopeproof_core.github_action_publisher import publish_check, publish_comment

Publisher = Callable[[EventContext, str, str], CommentPlan]
CheckPublisher = Callable[[CheckRunContext, str, str, str], CheckRunPlan]
MAX_ACTION_SUMMARY_CHARS = 60_000
_TRUNCATION_NOTICE = (
    "\n\n> ScopeProof summary truncated; use the workflow artifact/log for full details."
)


def _event_context(event_path: Path, requirements_confirmed: bool) -> EventContext:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = payload["pull_request"]
    head = pull_request["head"]
    return EventContext(
        repository=payload["repository"]["full_name"],
        pr_number=pull_request["number"],
        head_sha=head["sha"],
        is_fork=bool(head.get("repo", {}).get("fork", False)),
        requirements_confirmed=requirements_confirmed,
    )


def build_event_plan(
    event_path: Path,
    *,
    requirements_confirmed: bool,
    content: str,
    verdict: str = "needs_review",
) -> dict[str, Any]:
    """Build a serialisable plan from GitHub's event payload without HTTP calls."""

    context = _event_context(event_path, requirements_confirmed)
    summary = render_check_summary(context, verdict, content)
    if len(summary) > MAX_ACTION_SUMMARY_CHARS:
        summary = summary[: MAX_ACTION_SUMMARY_CHARS - len(_TRUNCATION_NOTICE)] + _TRUNCATION_NOTICE
    return {
        "context": context.model_dump(mode="json"),
        "summary": summary,
        "comment_plan": plan_comment(context, [], summary).model_dump(mode="json"),
    }


def build_check_context(
    event_path: Path,
    requirements_path: Path,
    confirmation_path: Path,
) -> CheckRunContext:
    """Bind an exact event identity to validated criteria-source bytes."""

    event = _event_context(event_path, requirements_confirmed=True)
    criteria_source = validate_requirements_confirmation(
        requirements_path,
        confirmation_path,
    )
    return CheckRunContext(
        repository=event.repository,
        pr_number=event.pr_number,
        head_sha=event.head_sha,
        is_fork=event.is_fork,
        criteria_source=criteria_source,
    )


def publish_event_comment(
    event_path: Path,
    requirements_confirmed: bool,
    summary: str,
    token: str | None,
    publisher: Publisher = publish_comment,
) -> CommentMode:
    """Publish only a non-fork, contract-confirmed Action event with a supplied token."""

    context = _event_context(event_path, requirements_confirmed)
    if context.is_fork or not context.requirements_confirmed or not token:
        return CommentMode.SKIP
    return publisher(context, summary, token).mode


def publish_event_check(
    event_path: Path,
    requirements_path: Path,
    confirmation_path: Path,
    verdict: str,
    content: str,
    token: str | None,
    publisher: CheckPublisher = publish_check,
) -> CheckMode:
    """Publish only after exact requirements confirmation and event validation."""

    context = build_check_context(event_path, requirements_path, confirmation_path)
    if context.is_fork or not token:
        return CheckMode.SKIP
    return publisher(context, verdict, content, token).mode


def main(argv: list[str] | None = None) -> int:
    """Emit a plan to stdout and GitHub's step summary, if available."""

    parser = argparse.ArgumentParser(description="Plan a safe ScopeProof GitHub Action run")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--requirements-confirmed", action="store_true")
    parser.add_argument("--publish-comment", action="store_true")
    parser.add_argument("--requirements", type=Path)
    parser.add_argument("--confirmation", type=Path)
    parser.add_argument("--publish-check", action="store_true")
    parser.add_argument("--verdict", default="needs_review")
    parser.add_argument("--content", default="Evidence report is available in the workflow logs.")
    parser.add_argument("--content-file", type=Path)
    args = parser.parse_args(argv)
    content = args.content_file.read_text(encoding="utf-8") if args.content_file else args.content

    plan = build_event_plan(
        args.event_path,
        requirements_confirmed=args.requirements_confirmed,
        content=content,
        verdict=args.verdict,
    )
    print(json.dumps(plan, indent=2, sort_keys=True))
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        Path(step_summary).write_text(f"{plan['summary']}\n", encoding="utf-8")
    if args.publish_comment:
        mode = publish_event_comment(
            args.event_path,
            args.requirements_confirmed,
            plan["summary"],
            os.environ.get("GITHUB_TOKEN"),
        )
        print(json.dumps({"comment_mode": mode}, sort_keys=True))
    if args.publish_check:
        if args.requirements is None or args.confirmation is None:
            parser.error("--publish-check requires --requirements and --confirmation")
        mode = publish_event_check(
            args.event_path,
            args.requirements,
            args.confirmation,
            args.verdict,
            content,
            os.environ.get("GITHUB_TOKEN"),
        )
        print(json.dumps({"check_mode": mode}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
