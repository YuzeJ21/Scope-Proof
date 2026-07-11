"""Read a GitHub pull-request event and emit a non-mutating ScopeProof plan."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from scopeproof_core.github_action import EventContext, plan_comment, render_check_summary


def build_event_plan(
    event_path: Path, *, requirements_confirmed: bool, content: str
) -> dict[str, Any]:
    """Build a serialisable plan from GitHub's event payload without HTTP calls."""

    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = payload["pull_request"]
    head = pull_request["head"]
    context = EventContext(
        repository=payload["repository"]["full_name"],
        pr_number=pull_request["number"],
        head_sha=head["sha"],
        is_fork=bool(head.get("repo", {}).get("fork", False)),
        requirements_confirmed=requirements_confirmed,
    )
    summary = render_check_summary(context, "needs_review", content)
    return {
        "context": context.model_dump(mode="json"),
        "summary": summary,
        "comment_plan": plan_comment(context, [], summary).model_dump(mode="json"),
    }


def main(argv: list[str] | None = None) -> int:
    """Emit a plan to stdout and GitHub's step summary, if available."""

    parser = argparse.ArgumentParser(description="Plan a safe ScopeProof GitHub Action run")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--requirements-confirmed", action="store_true")
    parser.add_argument("--content", default="Evidence report is available in the workflow logs.")
    args = parser.parse_args(argv)

    plan = build_event_plan(
        args.event_path,
        requirements_confirmed=args.requirements_confirmed,
        content=args.content,
    )
    print(json.dumps(plan, indent=2, sort_keys=True))
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        Path(step_summary).write_text(f"{plan['summary']}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
