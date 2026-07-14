import json
from pathlib import Path

import pytest

from scopeproof_core.github_action import CommentMode
from scopeproof_core.github_action_runner import build_event_plan, main, publish_event_comment

HEAD_SHA = "2" * 40


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
                    "head": {"sha": HEAD_SHA, "repo": {"fork": True}},
                },
            }
        ),
        encoding="utf-8",
    )

    plan = build_event_plan(event_path, requirements_confirmed=False, content="No source file")

    assert plan["comment_plan"]["mode"] == "skip"
    assert plan["comment_plan"]["reason"] == "fork_pull_request"
    assert "Needs Review" in plan["summary"]


def test_confirmed_requirements_preserve_the_core_gate_verdict_in_summary(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {"number": 42, "head": {"sha": HEAD_SHA, "repo": {"fork": False}}},
            }
        ),
        encoding="utf-8",
    )

    plan = build_event_plan(
        event_path, requirements_confirmed=True, content="Report", verdict="blocked"
    )

    assert "Blocked" in plan["summary"]


def test_runner_publishes_only_with_a_token_and_nonfork_context(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {"number": 42, "head": {"sha": HEAD_SHA, "repo": {"fork": False}}},
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def publisher(context, summary, token):
        calls.append((context, summary, token))
        return type("Result", (), {"mode": CommentMode.CREATE})()

    assert (
        publish_event_comment(event_path, True, "Summary", "token", publisher)
        is CommentMode.CREATE
    )
    assert calls[0][0].repository == "acme/widget"
    assert publish_event_comment(event_path, True, "Summary", None, publisher) is CommentMode.SKIP


def test_runner_uses_exported_report_file_as_summary_content(tmp_path: Path, capsys) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {"number": 42, "head": {"sha": HEAD_SHA, "repo": {"fork": False}}},
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.md"
    report_path.write_text("# ScopeProof Acceptance Review\n\nEvidence details", encoding="utf-8")

    assert main(
        [
            "--event-path",
            str(event_path),
            "--requirements-confirmed",
            "--content-file",
            str(report_path),
        ]
    ) == 0

    assert "Evidence details" in capsys.readouterr().out


def test_action_summary_marks_large_report_as_truncated(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {"number": 42, "head": {"sha": HEAD_SHA, "repo": {"fork": False}}},
            }
        ),
        encoding="utf-8",
    )

    plan = build_event_plan(
        event_path, requirements_confirmed=True, content="x" * 70_000, verdict="blocked"
    )

    assert len(plan["summary"]) <= 60_000
    assert "truncated" in plan["summary"]


def test_build_event_plan_rejects_invalid_head_sha_before_planning(tmp_path: Path) -> None:
    event_path = tmp_path / "invalid-sha-event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {
                    "number": 42,
                    "head": {"sha": "not-a-sha", "repo": {"fork": False}},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        build_event_plan(event_path, requirements_confirmed=True, content="Report")
