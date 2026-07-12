"""Read a GitHub pull-request event and emit a non-mutating ScopeProof plan."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scopeproof_core.github_action import (
    CommentMode,
    CommentPlan,
    EventContext,
    plan_comment,
    render_check_summary,
)
from scopeproof_core.github_action_publisher import publish_comment

Publisher = Callable[[EventContext, str, str], CommentPlan]
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


def main(argv: list[str] | None = None) -> int:
    """Emit a plan to stdout and GitHub's step summary, if available."""

    parser = argparse.ArgumentParser(description="Plan a safe ScopeProof GitHub Action run")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--requirements-confirmed", action="store_true")
    parser.add_argument("--publish-comment", action="store_true")
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
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
