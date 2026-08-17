import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scopeproof_core.criteria.confirmation import (
    canonical_criteria_sha256,
    source_text_sha256,
)
from scopeproof_core.github_action import CheckMode, CommentMode
from scopeproof_core.github_action_runner import (
    build_check_context,
    build_event_plan,
    main,
    publish_event_check,
    publish_event_check_unavailability,
    publish_event_check_withdrawal,
    publish_event_comment,
    validate_review_result_identity,
)
from scopeproof_core.schemas.models import Criterion

HEAD_SHA = "2" * 40
BASE_SHA = "1" * 40


def write_event(tmp_path: Path, *, fork: bool = False) -> Path:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {
                    "number": 42,
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {
                            "fork": fork,
                            "full_name": "acme/fork" if fork else "acme/widget",
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return event_path


def test_event_classifies_cross_repository_identity_not_repository_fork_flag(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "fork-hosted-event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {
                    "number": 42,
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {"fork": True, "full_name": "acme/widget"},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    plan = build_event_plan(
        event_path,
        requirements_confirmed=True,
        content="Report",
    )

    assert plan["context"]["is_fork"] is False


def write_confirmed_requirements(tmp_path: Path) -> tuple[Path, Path]:
    requirements = tmp_path / "requirements.txt"
    source_text = "Export the filtered list.\n"
    requirements.write_text(source_text, encoding="utf-8")
    confirmation = tmp_path / "requirements-confirmation.json"
    confirmation.write_text(
        json.dumps(
            {
                "source_uri": (
                    f"https://github.com/acme/widget/blob/{'1' * 40}/.scopeproof/requirements.txt"
                ),
                "source_revision": "1" * 40,
                "source_text_sha256": source_text_sha256(source_text),
                "normalized_criteria_sha256": canonical_criteria_sha256(
                    [Criterion(criterion_id="AC-01", text="Export the filtered list.")]
                ),
                "confirmed_by": "Requirements owner",
                "confirmed_at": datetime(2026, 8, 16, 12, 0, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return requirements, confirmation


def test_check_context_validates_exact_requirements_bytes_and_provenance(
    tmp_path: Path,
) -> None:
    event_path = write_event(tmp_path)
    requirements, confirmation = write_confirmed_requirements(tmp_path)

    context = build_check_context(event_path, requirements, confirmation)

    assert context.repository == "acme/widget"
    assert context.base_sha == BASE_SHA
    assert context.head_sha == HEAD_SHA
    assert context.criteria_source.source_text_sha256 == source_text_sha256(
        requirements.read_text(encoding="utf-8")
    )
    assert context.criteria_source.confirmed_by == "Requirements owner"


def test_check_context_rejects_stale_confirmation_instead_of_trusting_boolean(
    tmp_path: Path,
) -> None:
    event_path = write_event(tmp_path)
    requirements, confirmation = write_confirmed_requirements(tmp_path)
    requirements.write_text("Changed requirements.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        build_check_context(event_path, requirements, confirmation)


def test_check_runner_routes_validated_context_and_provenance_to_publisher(
    tmp_path: Path,
) -> None:
    event_path = write_event(tmp_path)
    requirements, confirmation = write_confirmed_requirements(tmp_path)
    calls = []

    def publisher(context, verdict, content, token):
        calls.append((context, verdict, content, token))
        return type("Result", (), {"mode": CheckMode.CREATE})()

    mode = publish_event_check(
        event_path,
        requirements,
        confirmation,
        "blocked",
        "Evidence report",
        "token",
        publisher,
    )

    assert mode is CheckMode.CREATE
    assert calls[0][0].criteria_source.confirmed_by == "Requirements owner"
    assert calls[0][1:] == ("blocked", "Evidence report", "token")


@pytest.mark.parametrize(("field", "value"), [("head_sha", "3" * 40), ("base_sha", "4" * 40)])
def test_review_result_identity_rejects_mixed_snapshot(
    tmp_path: Path, field: str, value: str
) -> None:
    event_path = write_event(tmp_path)
    result_path = tmp_path / "result.json"
    result = {
        "review_id": "review-1",
        "verdict": "ready",
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
    }
    result[field] = value
    result_path.write_text(json.dumps(result), encoding="utf-8")

    with pytest.raises(ValueError, match="identity mismatch"):
        validate_review_result_identity(event_path, result_path)


def test_review_result_identity_returns_validated_metadata(tmp_path: Path) -> None:
    event_path = write_event(tmp_path)
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "review_id": "review-1",
                "verdict": "blocked",
                "base_sha": BASE_SHA,
                "head_sha": HEAD_SHA,
            }
        ),
        encoding="utf-8",
    )

    result = validate_review_result_identity(event_path, result_path)

    assert result.review_id == "review-1"
    assert result.verdict == "blocked"


@pytest.mark.parametrize(("fork", "token"), [(True, "token"), (False, None)])
def test_check_runner_skips_fork_or_missing_token_without_publication(
    tmp_path: Path, fork: bool, token: str | None
) -> None:
    event_path = write_event(tmp_path, fork=fork)
    requirements, confirmation = write_confirmed_requirements(tmp_path)

    def unexpected(*args):
        raise AssertionError(f"publisher must not be called: {args}")

    assert (
        publish_event_check(
            event_path,
            requirements,
            confirmation,
            "blocked",
            "Report",
            token,
            unexpected,
        )
        is CheckMode.SKIP
    )


def test_withdrawal_runner_routes_exact_event_without_requirements(
    tmp_path: Path,
) -> None:
    event_path = write_event(tmp_path)
    calls = []

    def publisher(context, token):
        calls.append((context, token))
        return type("Result", (), {"mode": CheckMode.UPDATE})()

    mode = publish_event_check_withdrawal(event_path, "token", publisher)

    assert mode is CheckMode.UPDATE
    assert calls[0][0].head_sha == HEAD_SHA
    assert calls[0][1] == "token"


def test_unavailability_runner_routes_exact_event_without_requirements(
    tmp_path: Path,
) -> None:
    event_path = write_event(tmp_path)
    calls = []

    def publisher(context, token):
        calls.append((context, token))
        return type("Result", (), {"mode": CheckMode.UPDATE})()

    mode = publish_event_check_unavailability(event_path, "token", publisher)

    assert mode is CheckMode.UPDATE
    assert calls[0][0].head_sha == HEAD_SHA
    assert calls[0][1] == "token"


@pytest.mark.parametrize(("fork", "token"), [(True, "token"), (False, None)])
def test_withdrawal_runner_skips_fork_or_missing_token(
    tmp_path: Path, fork: bool, token: str | None
) -> None:
    event_path = write_event(tmp_path, fork=fork)

    def unexpected(*args):
        raise AssertionError(f"withdrawal publisher must not be called: {args}")

    assert publish_event_check_withdrawal(event_path, token, unexpected) is CheckMode.SKIP


def test_main_check_path_requires_exact_confirmation_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    event_path = write_event(tmp_path)
    requirements, confirmation = write_confirmed_requirements(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "")

    assert (
        main(
            [
                "--event-path",
                str(event_path),
                "--requirements",
                str(requirements),
                "--confirmation",
                str(confirmation),
                "--publish-check",
                "--verdict",
                "blocked",
            ]
        )
        == 0
    )
    assert '"check_mode": "skip"' in capsys.readouterr().out

    with pytest.raises(SystemExit):
        main(["--event-path", str(event_path), "--publish-check"])


def test_main_withdrawal_path_needs_no_requirements_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    event_path = write_event(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "")

    assert main(["--event-path", str(event_path), "--withdraw-check"]) == 0
    assert '"check_withdrawal_mode": "skip"' in capsys.readouterr().out

    with pytest.raises(SystemExit):
        main(
            [
                "--event-path",
                str(event_path),
                "--publish-check",
                "--withdraw-check",
            ]
        )


def test_main_unavailability_path_needs_no_requirements_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    event_path = write_event(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "")

    assert main(["--event-path", str(event_path), "--invalidate-check"]) == 0
    assert '"check_unavailability_mode": "skip"' in capsys.readouterr().out


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
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {"fork": True, "full_name": "acme/fork"},
                    },
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
                "pull_request": {
                    "number": 42,
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {"fork": False, "full_name": "acme/widget"},
                    },
                },
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
                "pull_request": {
                    "number": 42,
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {"fork": False, "full_name": "acme/widget"},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def publisher(context, summary, token):
        calls.append((context, summary, token))
        return type("Result", (), {"mode": CommentMode.CREATE})()

    assert (
        publish_event_comment(event_path, True, "Summary", "token", publisher) is CommentMode.CREATE
    )
    assert calls[0][0].repository == "acme/widget"
    assert publish_event_comment(event_path, True, "Summary", None, publisher) is CommentMode.SKIP


def test_runner_uses_exported_report_file_as_summary_content(tmp_path: Path, capsys) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {
                    "number": 42,
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {"fork": False, "full_name": "acme/widget"},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.md"
    report_path.write_text("# ScopeProof Acceptance Review\n\nEvidence details", encoding="utf-8")

    assert (
        main(
            [
                "--event-path",
                str(event_path),
                "--requirements-confirmed",
                "--content-file",
                str(report_path),
            ]
        )
        == 0
    )

    assert "Evidence details" in capsys.readouterr().out


def test_action_summary_marks_large_report_as_truncated(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "acme/widget"},
                "pull_request": {
                    "number": 42,
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {"fork": False, "full_name": "acme/widget"},
                    },
                },
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
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": "not-a-sha",
                        "repo": {"fork": False, "full_name": "acme/widget"},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        build_event_plan(event_path, requirements_confirmed=True, content="Report")


def test_build_event_plan_rejects_noncanonical_repository_before_planning(
    tmp_path: Path,
) -> None:
    event_path = tmp_path / "invalid-repository-event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "ac me/de mo"},
                "pull_request": {
                    "number": 42,
                    "base": {"sha": BASE_SHA},
                    "head": {
                        "sha": HEAD_SHA,
                        "repo": {"fork": False, "full_name": "ac me/de mo"},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        build_event_plan(event_path, requirements_confirmed=True, content="Report")
