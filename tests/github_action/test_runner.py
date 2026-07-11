import json
from pathlib import Path

from scopeproof_core.github_action_runner import build_event_plan


def test_build_event_plan_is_fork_safe_and_needs_review_without_requirements(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {
                    "number": 42,
                    "head": {"sha": "head123", "repo": {"fork": True}},
                },
            }
        ),
        encoding="utf-8",
    )

    plan = build_event_plan(event_path, requirements_confirmed=False, content="No source file")

    assert plan["comment_plan"]["mode"] == "skip"
    assert plan["comment_plan"]["reason"] == "fork_pull_request"
    assert "Needs Review" in plan["summary"]
