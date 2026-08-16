from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.github_action import (
    CHECK_NAME,
    CheckMode,
    CheckRunContext,
    CheckRunPlan,
    CommentMode,
    EventContext,
    ExistingCheckRun,
    check_external_id,
    comment_marker,
    plan_check,
    plan_comment,
    render_check_summary,
    render_informational_check,
)
from scopeproof_core.schemas.models import CriteriaSourceProvenance

HEAD_SHA = "2" * 40
OTHER_SHA = "3" * 40
SOURCE_TEXT_SHA = "4" * 64
CRITERIA_SHA = "5" * 64


def context(*, fork: bool = False) -> EventContext:
    return EventContext(
        repository="acme/widget",
        pr_number=42,
        head_sha=HEAD_SHA,
        is_fork=fork,
        requirements_confirmed=True,
    )


def criteria_source() -> CriteriaSourceProvenance:
    return CriteriaSourceProvenance(
        source_uri=(f"https://github.com/acme/widget/blob/{'1' * 40}/.scopeproof/requirements.txt"),
        source_revision="1" * 40,
        source_text_sha256=SOURCE_TEXT_SHA,
        normalized_criteria_sha256=CRITERIA_SHA,
        confirmed_by="Requirements owner",
        confirmed_at=datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
    )


def check_context(*, fork: bool = False, head_sha: str = HEAD_SHA) -> CheckRunContext:
    return CheckRunContext(
        repository="acme/widget",
        pr_number=42,
        head_sha=head_sha,
        is_fork=fork,
        criteria_source=criteria_source(),
    )


def trusted_check(*, head_sha: str = HEAD_SHA) -> ExistingCheckRun:
    current = check_context(head_sha=head_sha)
    return ExistingCheckRun(
        check_run_id=7,
        name=CHECK_NAME,
        head_sha=head_sha,
        external_id=check_external_id(current),
        app_slug="github-actions",
    )


def test_new_exact_head_creates_neutral_provenance_bound_check() -> None:
    current = check_context()

    plan = plan_check(current, [], "blocked", "Candidate report")

    assert plan.mode is CheckMode.CREATE
    assert plan.name == CHECK_NAME
    assert plan.external_id == f"scopeproof-check:v1:acme/widget:42:{HEAD_SHA}"
    assert plan.head_sha == HEAD_SHA
    assert plan.conclusion == "neutral"
    assert plan.check_run_id is None
    assert plan.output.title == "ScopeProof — Blocked (informational)"
    assert "evidence assistant, not a correctness oracle" in plan.output.summary
    assert "implementation and test matches are candidates" in plan.output.summary
    assert "externally supplied" in plan.output.summary
    assert "Missing or incomplete evidence remains missing" in plan.output.summary
    assert "human decisions remain unresolved" in plan.output.summary
    assert "asserted, not authenticated" in plan.output.summary
    assert SOURCE_TEXT_SHA in plan.output.text
    assert CRITERIA_SHA in plan.output.text
    assert criteria_source().source_uri in plan.output.text
    assert "Candidate report" in plan.output.text


def test_same_head_trusted_check_is_updated_without_duplicate() -> None:
    current = check_context()

    plan = plan_check(current, [trusted_check()], "ready", "Current report")

    assert plan.mode is CheckMode.UPDATE
    assert plan.reason == "same_head_exact_identity"
    assert plan.check_run_id == 7
    assert plan.conclusion == "neutral"


@pytest.mark.parametrize(
    ("change", "value"),
    [
        ("head_sha", OTHER_SHA),
        ("external_id", f"scopeproof-check:v1:acme/widget:99:{HEAD_SHA}"),
        ("name", "Foreign informational check"),
        ("app_slug", "foreign-app"),
    ],
)
def test_foreign_or_changed_check_identity_creates_current_head_check(
    change: str, value: str
) -> None:
    existing = trusted_check().model_copy(update={change: value})

    plan = plan_check(check_context(), [existing], "needs_review", "Report")

    assert plan.mode is CheckMode.CREATE
    assert plan.reason == "new_exact_head_identity"
    assert plan.check_run_id is None


def test_duplicate_trusted_same_head_checks_fail_closed() -> None:
    with pytest.raises(ValueError, match="multiple trusted exact-head checks"):
        plan_check(
            check_context(),
            [trusted_check(), trusted_check().model_copy(update={"check_run_id": 8})],
            "blocked",
            "Report",
        )


def test_fork_check_plan_is_non_mutating_skip() -> None:
    plan = plan_check(check_context(fork=True), [], "ready", "Report")

    assert plan.mode is CheckMode.SKIP
    assert plan.reason == "fork_pull_request"
    assert plan.conclusion == "neutral"
    assert plan.check_run_id is None


def test_unknown_verdict_fails_closed_to_needs_review_title() -> None:
    output = render_informational_check(check_context(), "not-a-verdict", "Report")

    assert output.title == "ScopeProof — Needs Review (informational)"


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (CheckRunContext, {"repository": "ac me/widget"}),
        (CheckRunContext, {"pr_number": 0}),
        (CheckRunContext, {"head_sha": "not-a-sha"}),
        (ExistingCheckRun, {"check_run_id": 0}),
        (ExistingCheckRun, {"external_id": ""}),
        (ExistingCheckRun, {"app_slug": ""}),
    ],
)
def test_check_models_reject_malformed_identity(model: type, payload: dict) -> None:
    if model is CheckRunContext:
        data = check_context().model_dump(mode="python") | payload
    else:
        data = trusted_check().model_dump(mode="python") | payload

    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_check_plan_rejects_blocking_conclusion_and_invalid_update_identity() -> None:
    create = plan_check(check_context(), [], "blocked", "Report")

    with pytest.raises(ValidationError):
        CheckRunPlan.model_validate(create.model_dump(mode="python") | {"conclusion": "failure"})
    with pytest.raises(ValidationError, match="check_run_id"):
        CheckRunPlan.model_validate(create.model_dump(mode="python") | {"check_run_id": 7})


def test_fork_event_is_non_mutating_even_with_write_token() -> None:
    plan = plan_comment(context(fork=True), [], "ScopeProof summary")

    assert plan.mode is CommentMode.SKIP
    assert plan.reason == "fork_pull_request"


def test_existing_marker_for_same_head_is_updated_not_duplicated() -> None:
    marker = comment_marker(HEAD_SHA)
    plan = plan_comment(
        context(),
        [
            {
                "id": 7,
                "body": f"old\n{marker}",
                "user": {"login": "github-actions[bot]", "type": "Bot"},
            }
        ],
        "new summary",
    )

    assert plan.mode is CommentMode.UPDATE
    assert plan.comment_id == 7
    assert plan.body.endswith(marker)


@pytest.mark.parametrize(
    "user",
    [
        {"login": "unrelated-user", "type": "User"},
        {"login": "github-actions[bot]", "type": "User"},
        {"login": "lookalike-actions[bot]", "type": "Bot"},
        {},
        None,
    ],
)
def test_same_head_marker_from_untrusted_author_is_not_updated(user: object) -> None:
    plan = plan_comment(
        context(),
        [{"id": 7, "body": comment_marker(HEAD_SHA), "user": user}],
        "summary",
    )

    assert plan.mode is CommentMode.CREATE
    assert plan.comment_id is None


def test_existing_marker_for_another_head_creates_a_new_auditable_comment() -> None:
    plan = plan_comment(context(), [{"id": 7, "body": comment_marker(OTHER_SHA)}], "summary")

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
