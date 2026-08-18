"""Narrow GitHub API adapters for pre-approved ScopeProof publication plans."""

from __future__ import annotations

from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from scopeproof_core.github_action import (
    CHECK_NAME,
    CheckMode,
    CheckRunContext,
    CheckRunOutput,
    CheckRunPlan,
    CommentPlan,
    EventContext,
    ExistingCheckRun,
    check_external_id,
    plan_check,
    plan_comment,
    render_informational_check,
)

_API_BASE_URL = "https://api.github.com"
_MAX_CHECK_PAGES = 5
_MAX_BASE_ADVANCE_PULL_PAGES = 2
_BASE_ADVANCE_PULLS_PER_PAGE = 55
_PER_PAGE = 100
_WITHDRAWAL_NOTICE = (
    "The `scopeproof-review` label was removed for this exact pull-request head. "
    "Applicability and any Ready display are revoked."
)
_UNAVAILABILITY_NOTICE = (
    "The checked-in requirements confirmation is unavailable or does not match for this "
    "exact pull-request head. Any prior Ready display is revoked."
)
_BASE_ADVANCE_NOTICE = (
    "The target base branch advanced for this open pull request. The prior snapshot is stale, "
    "so any Ready display is revoked until a new exact-base review completes."
)
_POSTWRITE_STALE_NOTICE = (
    "The pull request identity or applicability changed during publication. "
    "Any Ready display is revoked."
)
_BASE_ADVANCE_QUERY = """
query ScopeProofBaseAdvanceCandidates(
  $owner: String!
  $name: String!
  $label: String!
  $baseRef: String!
  $first: Int!
  $after: String
) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    label(name: $label) {
      pullRequests(
        states: OPEN
        baseRefName: $baseRef
        first: $first
        after: $after
        orderBy: {field: CREATED_AT, direction: ASC}
      ) {
        nodes {
          number
          state
          url
          headRefOid
          baseRefOid
          baseRefName
          headRepository { nameWithOwner }
          repository { nameWithOwner }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
""".strip()


class GitHubCheckPublicationError(RuntimeError):
    """A sanitized, fail-closed GitHub Check publication failure."""


class _RepositoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    full_name: str = Field(pattern=r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$")
    fork: bool | None = None


class _PullHeadResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    repo: _RepositoryResponse | None


class _PullBaseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    ref: str = Field(min_length=1, max_length=255)
    repo: _RepositoryResponse


class _PullLabelResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    name: str = Field(min_length=1, max_length=100)


class _PullResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    url: str = Field(min_length=1, max_length=500)
    html_url: str = Field(min_length=1, max_length=500)
    number: int = Field(gt=0)
    state: Literal["open", "closed"]
    head: _PullHeadResponse
    base: _PullBaseResponse
    labels: list[_PullLabelResponse] = Field(max_length=100)


class _GraphQLRepositoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    nameWithOwner: str = Field(pattern=r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$")


class _GraphQLPullResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    number: int = Field(gt=0)
    state: Literal["OPEN"]
    url: str = Field(min_length=1, max_length=500)
    headRefOid: str = Field(pattern=r"^[0-9a-f]{40}$")
    baseRefOid: str = Field(pattern=r"^[0-9a-f]{40}$")
    baseRefName: str = Field(min_length=1, max_length=255)
    headRepository: _GraphQLRepositoryResponse | None
    repository: _GraphQLRepositoryResponse


class _GraphQLPageInfoResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    hasNextPage: bool
    endCursor: str | None = Field(default=None, min_length=1, max_length=500)


class _GraphQLPullConnectionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    nodes: list[_GraphQLPullResponse] = Field(max_length=_BASE_ADVANCE_PULLS_PER_PAGE)
    pageInfo: _GraphQLPageInfoResponse


class _GraphQLLabelResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    pullRequests: _GraphQLPullConnectionResponse


class _GraphQLBaseAdvanceRepositoryResponse(_GraphQLRepositoryResponse):
    label: _GraphQLLabelResponse | None


class _GraphQLBaseAdvanceDataResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    repository: _GraphQLBaseAdvanceRepositoryResponse


class _GraphQLBaseAdvanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    data: _GraphQLBaseAdvanceDataResponse


class _CheckAppResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    slug: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


class _CheckRunResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    id: int = Field(gt=0)
    url: str = Field(min_length=1, max_length=500)
    name: str = Field(min_length=1, max_length=100)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    external_id: str | None = Field(default=None, max_length=255)
    app: _CheckAppResponse


class _CheckOutputResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=65_535)
    text: str = Field(min_length=1, max_length=65_535)


class _CheckRunDetailResponse(_CheckRunResponse):
    output: _CheckOutputResponse


class _CheckListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    total_count: int = Field(ge=0)
    check_runs: list[_CheckRunResponse] = Field(max_length=_PER_PAGE)


class _CheckOutputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=65_535)
    text: str = Field(min_length=1, max_length=65_535)


class _CreateCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Literal[CHECK_NAME]
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    external_id: str = Field(min_length=1, max_length=255)
    status: Literal["completed"]
    conclusion: Literal["neutral"]
    output: _CheckOutputRequest


class _UpdateCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Literal[CHECK_NAME]
    external_id: str = Field(min_length=1, max_length=255)
    status: Literal["completed"]
    conclusion: Literal["neutral"]
    output: _CheckOutputRequest


class BaseAdvanceInvalidationResult(BaseModel):
    """Validated aggregate result for one trusted default-branch push."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    reason: str = Field(min_length=1, max_length=100)
    updated_count: int = Field(
        ge=0,
        le=_MAX_BASE_ADVANCE_PULL_PAGES * _BASE_ADVANCE_PULLS_PER_PAGE,
    )
    skipped_count: int = Field(
        ge=0,
        le=_MAX_BASE_ADVANCE_PULL_PAGES * _BASE_ADVANCE_PULLS_PER_PAGE,
    )
    plans: list[CheckRunPlan] = Field(
        max_length=_MAX_BASE_ADVANCE_PULL_PAGES * _BASE_ADVANCE_PULLS_PER_PAGE,
    )


def _skipped_check_plan(
    context: CheckRunContext, verdict: str, content: str, reason: str
) -> CheckRunPlan:
    """Return a fully validated non-mutating plan."""

    output = render_informational_check(context, verdict, content)
    planned = plan_check(context, [], verdict, content)
    return CheckRunPlan(
        mode=CheckMode.SKIP,
        reason=reason,
        name=planned.name,
        external_id=planned.external_id,
        head_sha=planned.head_sha,
        conclusion="neutral",
        output=output,
    )


def _validate_live_pull(
    context: CheckRunContext | EventContext,
    pull: _PullResponse,
    *,
    applicability_label_expected: bool,
    require_open: bool,
) -> None:
    """Require the live public PR to match every trusted immutable identity."""

    expected_api_url = f"{_API_BASE_URL}/repos/{context.repository}/pulls/{context.pr_number}"
    expected_html_url = f"https://github.com/{context.repository}/pull/{context.pr_number}"
    if (
        pull.number != context.pr_number
        or (require_open and pull.state != "open")
        or pull.url != expected_api_url
        or pull.html_url != expected_html_url
        or pull.head.sha != context.head_sha
        or pull.base.sha != context.base_sha
        or pull.head.repo is None
        or pull.head.repo.full_name != context.repository
        or pull.base.repo.full_name != context.repository
    ):
        raise GitHubCheckPublicationError("live pull request identity mismatch")
    label_is_present = any(label.name == "scopeproof-review" for label in pull.labels)
    if label_is_present is not applicability_label_expected:
        raise GitHubCheckPublicationError("live applicability label mismatch")


def _validated_existing_check(
    context: CheckRunContext | EventContext, response: _CheckRunResponse
) -> ExistingCheckRun | None:
    """Validate the repository-scoped URL before exposing a check to the planner."""

    expected_url = f"{_API_BASE_URL}/repos/{context.repository}/check-runs/{response.id}"
    if response.url != expected_url:
        raise GitHubCheckPublicationError("check run URL identity mismatch")
    if not response.external_id:
        return None
    return ExistingCheckRun(
        check_run_id=response.id,
        name=response.name,
        head_sha=response.head_sha,
        external_id=response.external_id,
        app_slug=response.app.slug,
    )


def _read_existing_checks(
    client: httpx.Client, context: CheckRunContext | EventContext
) -> list[ExistingCheckRun]:
    """Read at most five locally constructed pages without following Link URLs."""

    existing: list[ExistingCheckRun] = []
    seen_ids: set[int] = set()
    expected_total: int | None = None
    for page_number in range(1, _MAX_CHECK_PAGES + 1):
        response = client.get(
            f"/repos/{context.repository}/commits/{context.head_sha}/check-runs",
            params={
                "check_name": CHECK_NAME,
                "filter": "all",
                "per_page": _PER_PAGE,
                "page": page_number,
            },
        )
        response.raise_for_status()
        page = _CheckListResponse.model_validate(response.json())
        if expected_total is None:
            expected_total = page.total_count
        elif page.total_count != expected_total:
            raise GitHubCheckPublicationError("check run total changed during pagination")
        for item in page.check_runs:
            if item.id in seen_ids:
                raise GitHubCheckPublicationError("repeated check run across pages")
            seen_ids.add(item.id)
            validated = _validated_existing_check(context, item)
            if validated is not None:
                existing.append(validated)
        if len(seen_ids) >= page.total_count:
            return existing
        if len(page.check_runs) < _PER_PAGE:
            raise GitHubCheckPublicationError("incomplete check run pagination")
    raise GitHubCheckPublicationError("check run page budget exceeded")


def _request_output(output: CheckRunOutput) -> _CheckOutputRequest:
    return _CheckOutputRequest.model_validate(output.model_dump(mode="python"))


def _validate_write_response(
    context: CheckRunContext | EventContext,
    plan: CheckRunPlan,
    response: httpx.Response,
) -> _CheckRunResponse:
    """Require GitHub to echo the exact published identity."""

    response.raise_for_status()
    created = _CheckRunResponse.model_validate(response.json())
    validated = _validated_existing_check(context, created)
    if (
        validated is None
        or created.name != plan.name
        or created.head_sha != plan.head_sha
        or created.external_id != plan.external_id
        or created.app.slug != "github-actions"
        or (plan.mode is CheckMode.UPDATE and created.id != plan.check_run_id)
    ):
        raise GitHubCheckPublicationError("published check run identity mismatch")
    return created


def _compensate_stale_publication(
    client: httpx.Client,
    context: CheckRunContext,
    plan: CheckRunPlan,
    published: _CheckRunResponse,
) -> None:
    """Fail closed by neutralizing the exact Check written by this invocation."""

    summary = f"{_POSTWRITE_STALE_NOTICE} {plan.output.summary}"
    if len(summary) > 65_535:
        summary = _POSTWRITE_STALE_NOTICE
    compensation = CheckRunPlan(
        mode=CheckMode.UPDATE,
        reason="live_pull_changed_during_publication",
        name=plan.name,
        external_id=plan.external_id,
        head_sha=plan.head_sha,
        conclusion="neutral",
        output=CheckRunOutput(
            title="ScopeProof — Needs Review (informational)",
            summary=summary,
            text=plan.output.text,
        ),
        check_run_id=published.id,
    )
    request = _UpdateCheckRequest(
        name=compensation.name,
        external_id=compensation.external_id,
        status="completed",
        conclusion="neutral",
        output=_request_output(compensation.output),
    )
    response = client.patch(
        f"/repos/{context.repository}/check-runs/{published.id}",
        json=request.model_dump(mode="json"),
    )
    _validate_write_response(context, compensation, response)


def _existing_check_skip_plan(context: EventContext, reason: str) -> CheckRunPlan:
    """Return a validated no-write plan for an inapplicable exact-head Check."""

    return CheckRunPlan(
        mode=CheckMode.SKIP,
        reason=reason,
        external_id=check_external_id(context),
        head_sha=context.head_sha,
        conclusion="neutral",
        output=CheckRunOutput(
            title="ScopeProof — Needs Review (informational)",
            summary="ScopeProof applicability is not confirmed for this exact pull-request head.",
            text="No trusted exact-head ScopeProof Check was available to update.",
        ),
    )


def _needs_review_output(detail: _CheckRunDetailResponse, notice: str) -> CheckRunOutput:
    """Preserve validated detail and make state-transition summaries canonical."""

    base_summary = detail.output.summary
    prior_notices = (_WITHDRAWAL_NOTICE, _UNAVAILABILITY_NOTICE, _BASE_ADVANCE_NOTICE)
    changed = True
    while changed:
        changed = False
        for prior_notice in prior_notices:
            if base_summary == prior_notice:
                base_summary = ""
                changed = True
                break
            prefix = f"{prior_notice} "
            if base_summary.startswith(prefix):
                base_summary = base_summary[len(prefix) :]
                changed = True
                break
    summary = f"{notice} {base_summary}" if base_summary else notice
    if len(summary) > 65_535:
        summary = notice
    return CheckRunOutput(
        title="ScopeProof — Needs Review (informational)",
        summary=summary,
        text=detail.output.text,
    )


def _publish_existing_check_needs_review(
    context: EventContext,
    token: str,
    transport: httpx.BaseTransport | None,
    *,
    applicability_label_expected: bool,
    require_open: bool,
    reason: str,
    notice: str,
) -> CheckRunPlan:
    """Update only one existing trusted exact-head Check to Needs Review."""

    if context.is_fork:
        return _existing_check_skip_plan(context, "fork_pull_request")
    checked_token = token.strip()
    if not checked_token:
        return _existing_check_skip_plan(context, "missing_token")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {checked_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        with httpx.Client(
            base_url=_API_BASE_URL,
            headers=headers,
            transport=transport,
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            pull_response = client.get(f"/repos/{context.repository}/pulls/{context.pr_number}")
            pull_response.raise_for_status()
            pull = _PullResponse.model_validate(pull_response.json())
            _validate_live_pull(
                context,
                pull,
                applicability_label_expected=applicability_label_expected,
                require_open=require_open,
            )

            expected_external_id = check_external_id(context)
            matches = [
                check
                for check in _read_existing_checks(client, context)
                if check.name == CHECK_NAME
                and check.head_sha == context.head_sha
                and check.external_id == expected_external_id
                and check.app_slug == "github-actions"
            ]
            if len(matches) > 1:
                raise GitHubCheckPublicationError("multiple trusted exact-head checks")
            if not matches:
                return _existing_check_skip_plan(context, "no_exact_head_check")

            existing = matches[0]
            detail_response = client.get(
                f"/repos/{context.repository}/check-runs/{existing.check_run_id}"
            )
            detail_response.raise_for_status()
            detail = _CheckRunDetailResponse.model_validate(detail_response.json())
            validated_detail = _validated_existing_check(context, detail)
            if validated_detail != existing:
                raise GitHubCheckPublicationError("check run detail identity mismatch")

            output = _needs_review_output(detail, notice)
            plan = CheckRunPlan(
                mode=CheckMode.UPDATE,
                reason=reason,
                external_id=expected_external_id,
                head_sha=context.head_sha,
                conclusion="neutral",
                output=output,
                check_run_id=existing.check_run_id,
            )
            request = _UpdateCheckRequest(
                name=plan.name,
                external_id=plan.external_id,
                status="completed",
                conclusion="neutral",
                output=_request_output(plan.output),
            )
            prewrite_pull_response = client.get(
                f"/repos/{context.repository}/pulls/{context.pr_number}"
            )
            prewrite_pull_response.raise_for_status()
            prewrite_pull = _PullResponse.model_validate(prewrite_pull_response.json())
            _validate_live_pull(
                context,
                prewrite_pull,
                applicability_label_expected=applicability_label_expected,
                require_open=require_open,
            )
            write_response = client.patch(
                f"/repos/{context.repository}/check-runs/{plan.check_run_id}",
                json=request.model_dump(mode="json"),
            )
            _validate_write_response(context, plan, write_response)
            return plan
    except GitHubCheckPublicationError:
        raise
    except (httpx.HTTPError, ValidationError, ValueError) as exc:
        raise GitHubCheckPublicationError("GitHub Check update failed closed") from exc


def publish_check_withdrawal(
    context: EventContext,
    token: str,
    transport: httpx.BaseTransport | None = None,
) -> CheckRunPlan:
    """Withdraw applicability from one existing trusted exact-head Check."""

    return _publish_existing_check_needs_review(
        context,
        token,
        transport,
        applicability_label_expected=False,
        require_open=False,
        reason="applicability_label_removed",
        notice=_WITHDRAWAL_NOTICE,
    )


def publish_check_unavailability(
    context: EventContext,
    token: str,
    transport: httpx.BaseTransport | None = None,
) -> CheckRunPlan:
    """Revoke an existing display when exact criteria confirmation is unavailable."""

    return _publish_existing_check_needs_review(
        context,
        token,
        transport,
        applicability_label_expected=True,
        require_open=True,
        reason="requirements_confirmation_unavailable",
        notice=_UNAVAILABILITY_NOTICE,
    )


def publish_check_base_advance(
    context: EventContext,
    token: str,
    transport: httpx.BaseTransport | None = None,
) -> CheckRunPlan:
    """Revoke one existing exact-head display after its target base advances."""

    return _publish_existing_check_needs_review(
        context,
        token,
        transport,
        applicability_label_expected=True,
        require_open=True,
        reason="target_base_advanced",
        notice=_BASE_ADVANCE_NOTICE,
    )


def publish_base_advance_invalidations(
    *,
    repository: str,
    base_ref: str,
    after_sha: str,
    token: str,
    transport: httpx.BaseTransport | None = None,
) -> BaseAdvanceInvalidationResult:
    """Revoke stale Checks on same-repository labeled PRs targeting one pushed base."""

    identity = EventContext(
        repository=repository,
        pr_number=1,
        base_sha=after_sha,
        head_sha=after_sha,
        is_fork=False,
        requirements_confirmed=False,
    )
    checked_ref = base_ref.strip()
    if not checked_ref or len(checked_ref) > 255:
        raise ValueError("invalid base ref")
    checked_token = token.strip()
    if not checked_token:
        return BaseAdvanceInvalidationResult(
            reason="missing_token",
            updated_count=0,
            skipped_count=0,
            plans=[],
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {checked_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    owner, name = identity.repository.split("/", maxsplit=1)
    pulls: list[_GraphQLPullResponse] = []
    seen_numbers: set[int] = set()
    try:
        with httpx.Client(
            base_url=_API_BASE_URL,
            headers=headers,
            transport=transport,
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            cursor: str | None = None
            seen_cursors: set[str] = set()
            for page_number in range(_MAX_BASE_ADVANCE_PULL_PAGES):
                response = client.post(
                    "/graphql",
                    json={
                        "query": _BASE_ADVANCE_QUERY,
                        "variables": {
                            "owner": owner,
                            "name": name,
                            "label": "scopeproof-review",
                            "baseRef": checked_ref,
                            "first": _BASE_ADVANCE_PULLS_PER_PAGE,
                            "after": cursor,
                        },
                    },
                )
                response.raise_for_status()
                page = _GraphQLBaseAdvanceResponse.model_validate(response.json())
                repository_page = page.data.repository
                if repository_page.nameWithOwner != identity.repository:
                    raise GitHubCheckPublicationError("base advance repository mismatch")
                if repository_page.label is None:
                    break
                connection = repository_page.label.pullRequests
                for pull in connection.nodes:
                    if pull.number in seen_numbers:
                        raise GitHubCheckPublicationError("repeated pull request across pages")
                    seen_numbers.add(pull.number)
                    pulls.append(pull)
                page_info = connection.pageInfo
                if not page_info.hasNextPage:
                    break
                if page_number == _MAX_BASE_ADVANCE_PULL_PAGES - 1:
                    raise GitHubCheckPublicationError("pull request page budget exceeded")
                cursor = page_info.endCursor
                if cursor is None or cursor in seen_cursors:
                    raise GitHubCheckPublicationError("invalid pull request pagination cursor")
                seen_cursors.add(cursor)

        plans: list[CheckRunPlan] = []
        failed_pr_numbers: list[int] = []
        for pull in sorted(pulls, key=lambda item: item.number):
            if (
                pull.headRepository is None
                or pull.headRepository.nameWithOwner != identity.repository
            ):
                continue
            if (
                pull.url
                != f"https://github.com/{identity.repository}/pull/{pull.number}"
                or pull.baseRefName != checked_ref
                or pull.baseRefOid != identity.base_sha
                or pull.repository.nameWithOwner != identity.repository
            ):
                raise GitHubCheckPublicationError("base advance pull identity mismatch")
            context = EventContext(
                repository=identity.repository,
                pr_number=pull.number,
                base_sha=identity.base_sha,
                head_sha=pull.headRefOid,
                is_fork=False,
                requirements_confirmed=False,
            )
            try:
                plans.append(publish_check_base_advance(context, checked_token, transport))
            except GitHubCheckPublicationError:
                failed_pr_numbers.append(pull.number)
        if failed_pr_numbers:
            joined = ",".join(str(number) for number in failed_pr_numbers)
            raise GitHubCheckPublicationError(f"base advance invalidation failed for PRs: {joined}")
        return BaseAdvanceInvalidationResult(
            reason="default_base_advanced",
            updated_count=sum(plan.mode is CheckMode.UPDATE for plan in plans),
            skipped_count=sum(plan.mode is CheckMode.SKIP for plan in plans),
            plans=plans,
        )
    except GitHubCheckPublicationError:
        raise
    except (httpx.HTTPError, ValidationError, ValueError) as exc:
        raise GitHubCheckPublicationError("GitHub base-advance invalidation failed closed") from exc


def publish_check(
    context: CheckRunContext,
    verdict: str,
    content: str,
    token: str,
    transport: httpx.BaseTransport | None = None,
) -> CheckRunPlan:
    """Validate the live PR, plan one exact-head Check, and write at most once."""

    if context.is_fork:
        return _skipped_check_plan(context, verdict, content, "fork_pull_request")
    checked_token = token.strip()
    if not checked_token:
        return _skipped_check_plan(context, verdict, content, "missing_token")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {checked_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        with httpx.Client(
            base_url=_API_BASE_URL,
            headers=headers,
            transport=transport,
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            pull_response = client.get(f"/repos/{context.repository}/pulls/{context.pr_number}")
            pull_response.raise_for_status()
            pull = _PullResponse.model_validate(pull_response.json())
            _validate_live_pull(
                context,
                pull,
                applicability_label_expected=True,
                require_open=True,
            )

            existing = _read_existing_checks(client, context)
            try:
                plan = plan_check(context, existing, verdict, content)
            except ValueError as exc:
                if str(exc) == "multiple trusted exact-head checks":
                    raise GitHubCheckPublicationError(str(exc)) from exc
                raise
            if plan.mode is CheckMode.CREATE:
                request = _CreateCheckRequest(
                    name=plan.name,
                    head_sha=plan.head_sha,
                    external_id=plan.external_id,
                    status="completed",
                    conclusion="neutral",
                    output=_request_output(plan.output),
                )
            elif plan.mode is CheckMode.UPDATE:
                request = _UpdateCheckRequest(
                    name=plan.name,
                    external_id=plan.external_id,
                    status="completed",
                    conclusion="neutral",
                    output=_request_output(plan.output),
                )
            else:
                return plan
            prewrite_pull_response = client.get(
                f"/repos/{context.repository}/pulls/{context.pr_number}"
            )
            prewrite_pull_response.raise_for_status()
            prewrite_pull = _PullResponse.model_validate(prewrite_pull_response.json())
            _validate_live_pull(
                context,
                prewrite_pull,
                applicability_label_expected=True,
                require_open=True,
            )
            if plan.mode is CheckMode.CREATE:
                write_response = client.post(
                    f"/repos/{context.repository}/check-runs",
                    json=request.model_dump(mode="json"),
                )
            else:
                write_response = client.patch(
                    f"/repos/{context.repository}/check-runs/{plan.check_run_id}",
                    json=request.model_dump(mode="json"),
                )
            published = _validate_write_response(context, plan, write_response)
            try:
                postwrite_pull_response = client.get(
                    f"/repos/{context.repository}/pulls/{context.pr_number}"
                )
                postwrite_pull_response.raise_for_status()
                postwrite_pull = _PullResponse.model_validate(postwrite_pull_response.json())
                _validate_live_pull(
                    context,
                    postwrite_pull,
                    applicability_label_expected=True,
                    require_open=True,
                )
            except (
                GitHubCheckPublicationError,
                httpx.HTTPError,
                ValidationError,
                ValueError,
            ) as exc:
                _compensate_stale_publication(client, context, plan, published)
                raise GitHubCheckPublicationError(
                    "live pull changed during publication"
                ) from exc
            return plan
    except GitHubCheckPublicationError:
        raise
    except (httpx.HTTPError, ValidationError, ValueError) as exc:
        raise GitHubCheckPublicationError("GitHub Check publication failed closed") from exc


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
        comments: list[dict] = []
        page = 1
        while True:
            comments_response = client.get(
                f"/repos/{context.repository}/issues/{context.pr_number}/comments",
                params={"per_page": 100, "page": page},
            )
            comments_response.raise_for_status()
            comments.extend(comments_response.json())
            if "next" not in comments_response.links:
                break
            page += 1
        plan = plan_comment(context, comments, summary)
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
