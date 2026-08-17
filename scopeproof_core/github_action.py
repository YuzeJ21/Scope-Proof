"""Pure, fork-safe planning for the optional ScopeProof GitHub Action.

This module deliberately makes no HTTP calls.  The workflow adapter may execute a
returned plan only after GitHub has established that the pull request is not from
a fork.  Keeping the policy here pure makes it easy to test without credentials
or GitHub-side mutation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scopeproof_core.schemas.models import CriteriaSourceProvenance

CHECK_NAME = "ScopeProof evidence summary (informational)"
_CHECK_EXTERNAL_ID_PREFIX = "scopeproof-check:v1"
_TRUSTED_CHECK_APP_SLUG = "github-actions"
_MAX_CHECK_TEXT_CHARS = 65_535


class CommentMode(StrEnum):
    """The only permitted comment actions for an Action run."""

    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


class CheckMode(StrEnum):
    """The only permitted exact-head check publication actions."""

    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


_TRUSTED_COMMENT_AUTHOR = {
    "login": "github-actions[bot]",
    "type": "Bot",
}


def _is_trusted_action_comment(comment: dict[str, Any]) -> bool:
    """Return whether GitHub attributes the comment to its Actions bot identity."""

    user = comment.get("user")
    return isinstance(user, dict) and all(
        user.get(key) == value for key, value in _TRUSTED_COMMENT_AUTHOR.items()
    )


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


class CheckRunContext(BaseModel):
    """Validated immutable inputs for an exact-head informational check."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    repository: str = Field(pattern=r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$")
    pr_number: int = Field(gt=0)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    is_fork: bool
    criteria_source: CriteriaSourceProvenance


class ExistingCheckRun(BaseModel):
    """A bounded GitHub check identity considered by the pure planner."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    check_run_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    external_id: str = Field(min_length=1, max_length=255)
    app_slug: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


class CheckRunOutput(BaseModel):
    """Validated, bounded GitHub Check output."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=_MAX_CHECK_TEXT_CHARS)
    text: str = Field(min_length=1, max_length=_MAX_CHECK_TEXT_CHARS)


class CheckRunPlan(BaseModel):
    """A fail-closed mutation decision for one exact PR head."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mode: CheckMode
    reason: str = Field(min_length=1, max_length=100)
    name: Literal[CHECK_NAME] = CHECK_NAME
    external_id: str = Field(min_length=1, max_length=255)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    conclusion: Literal["neutral"] = "neutral"
    output: CheckRunOutput
    check_run_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_check_run_identity(self) -> CheckRunPlan:
        """Permit an existing check id only for an exact update plan."""

        if self.mode is CheckMode.UPDATE and self.check_run_id is None:
            raise ValueError("update mode requires check_run_id")
        if self.mode is not CheckMode.UPDATE and self.check_run_id is not None:
            raise ValueError("check_run_id is permitted only for update mode")
        return self


def comment_marker(head_sha: str) -> str:
    """Return an invisible idempotency marker scoped to one immutable PR head."""

    return f"<!-- scopeproof:{head_sha} -->"


def check_external_id(context: CheckRunContext | EventContext) -> str:
    """Return the stable identity for one repository, PR, and immutable head."""

    return (
        f"{_CHECK_EXTERNAL_ID_PREFIX}:{context.repository}:{context.pr_number}:{context.head_sha}"
    )


def _informational_verdict(verdict: str) -> str:
    """Normalize only known display verdicts and fail closed otherwise."""

    return {
        "ready": "Ready",
        "conditional": "Conditional",
        "blocked": "Blocked",
        "needs_review": "Needs Review",
    }.get(verdict, "Needs Review")


def render_informational_check(
    context: CheckRunContext, verdict: str, content: str
) -> CheckRunOutput:
    """Render explicit evidence boundaries and criteria-source provenance."""

    source = context.criteria_source
    title = f"ScopeProof — {_informational_verdict(verdict)} (informational)"
    summary = (
        "ScopeProof is an evidence assistant, not a correctness oracle. "
        "Candidate implementation and test matches are candidates, not runtime "
        "verification. Runtime verification must be externally supplied. "
        "Missing or incomplete evidence remains missing. Unresolved human "
        "decisions remain unresolved. Reviewer and source-owner identities are "
        "asserted, not authenticated."
    )
    provenance = (
        "## Confirmed criteria source\n\n"
        f"- Source: {source.source_uri}\n"
        f"- Revision: {source.source_revision or 'Not provided'}\n"
        f"- Source text SHA-256: {source.source_text_sha256}\n"
        f"- Normalized criteria SHA-256: {source.normalized_criteria_sha256}\n"
        f"- Confirmed by: {source.confirmed_by}\n"
        f"- Confirmed at: {source.confirmed_at.isoformat()}\n\n"
        "## Evidence report\n\n"
    )
    report = content.strip() or "No evidence report was produced."
    text = f"{provenance}{report}"
    if len(text) > _MAX_CHECK_TEXT_CHARS:
        title = "ScopeProof — Needs Review (informational)"
        text = (
            f"{provenance}"
            "The evidence report was not published because it exceeds the GitHub "
            "Check output limit. No criterion verdict from the omitted report is "
            "displayed. Review the validated ScopeProof artifact directly."
        )
    return CheckRunOutput(title=title, summary=summary, text=text)


def plan_check(
    context: CheckRunContext,
    existing_checks: list[ExistingCheckRun],
    verdict: str,
    content: str,
) -> CheckRunPlan:
    """Choose create, exact update, or fork skip without network access."""

    external_id = check_external_id(context)
    output = render_informational_check(context, verdict, content)
    common = {
        "external_id": external_id,
        "head_sha": context.head_sha,
        "output": output,
    }
    if context.is_fork:
        return CheckRunPlan(
            mode=CheckMode.SKIP,
            reason="fork_pull_request",
            **common,
        )

    matches = [
        check
        for check in existing_checks
        if check.name == CHECK_NAME
        and check.head_sha == context.head_sha
        and check.external_id == external_id
        and check.app_slug == _TRUSTED_CHECK_APP_SLUG
    ]
    if len(matches) > 1:
        raise ValueError("multiple trusted exact-head checks")
    if matches:
        return CheckRunPlan(
            mode=CheckMode.UPDATE,
            reason="same_head_exact_identity",
            check_run_id=matches[0].check_run_id,
            **common,
        )
    return CheckRunPlan(
        mode=CheckMode.CREATE,
        reason="new_exact_head_identity",
        **common,
    )


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
        if _is_trusted_action_comment(comment) and marker in str(comment.get("body", "")):
            comment_id = comment.get("id")
            if isinstance(comment_id, int):
                return CommentPlan(
                    mode=CommentMode.UPDATE,
                    reason="same_head_marker",
                    body=body,
                    comment_id=comment_id,
                )
    return CommentPlan(mode=CommentMode.CREATE, reason="new_head_marker", body=body)
