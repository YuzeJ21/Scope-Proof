import json
from datetime import UTC, datetime

import httpx
import pytest

import scopeproof_core.github_action_publisher as publisher_module
from scopeproof_core.demo import build_demo_review
from scopeproof_core.github_action import (
    CHECK_NAME,
    CheckMode,
    CheckRunContext,
    CommentMode,
    EventContext,
    check_external_id,
)
from scopeproof_core.github_action_publisher import (
    GitHubCheckPublicationError,
    publish_base_advance_invalidations,
    publish_check,
    publish_check_unavailability,
    publish_check_withdrawal,
    publish_comment,
)
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import CriteriaSourceProvenance
from scopeproof_core.storage.json_store import JsonReviewStore

HEAD_SHA = "2" * 40
OTHER_SHA = "3" * 40
BASE_SHA = "1" * 40


def context(*, fork: bool = False) -> EventContext:
    return EventContext(
        repository="acme/widget",
        pr_number=42,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        is_fork=fork,
        requirements_confirmed=True,
    )


def check_context(*, fork: bool = False) -> CheckRunContext:
    return CheckRunContext(
        repository="acme/widget",
        pr_number=42,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        is_fork=fork,
        criteria_source=CriteriaSourceProvenance(
            source_uri=(
                f"https://github.com/acme/widget/blob/{'1' * 40}/.scopeproof/requirements.txt"
            ),
            source_revision="1" * 40,
            source_text_sha256="4" * 64,
            normalized_criteria_sha256="5" * 64,
            confirmed_by="Requirements owner",
            confirmed_at=datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
        ),
    )


def pull_response(
    *,
    head_sha: str = HEAD_SHA,
    fork: bool = False,
    applicability_label: bool = True,
    state: str = "open",
    base_sha: str = BASE_SHA,
    base_ref: str = "main",
    pr_number: int = 42,
) -> dict:
    return {
        "url": f"https://api.github.com/repos/acme/widget/pulls/{pr_number}",
        "html_url": f"https://github.com/acme/widget/pull/{pr_number}",
        "number": pr_number,
        "state": state,
        "head": {
            "sha": head_sha,
            "repo": {
                "full_name": "acme/widget",
                "fork": fork,
            },
        },
        "base": {
            "sha": base_sha,
            "ref": base_ref,
            "repo": {"full_name": "acme/widget"},
        },
        "labels": ([{"name": "scopeproof-review"}] if applicability_label else []),
    }


def check_response(
    *,
    check_run_id: int = 7,
    head_sha: str = HEAD_SHA,
    external_id: str | None = None,
    app_slug: str = "github-actions",
    name: str = CHECK_NAME,
) -> dict:
    return {
        "id": check_run_id,
        "url": f"https://api.github.com/repos/acme/widget/check-runs/{check_run_id}",
        "name": name,
        "head_sha": head_sha,
        "external_id": external_id or check_external_id(check_context()),
        "app": {"slug": app_slug},
    }


def check_list(*checks: dict, total_count: int | None = None) -> dict:
    return {
        "total_count": len(checks) if total_count is None else total_count,
        "check_runs": list(checks),
    }


def check_detail_response(**overrides) -> dict:
    response = check_response()
    response["output"] = {
        "title": "ScopeProof — Ready (informational)",
        "summary": "ScopeProof evidence boundary",
        "text": (
            "## Confirmed criteria source\n\n- Revision: 111\n\n"
            "## Evidence report\n\nReady evidence"
        ),
    }
    response.update(overrides)
    return response


def assert_safe_request(request: httpx.Request) -> None:
    assert str(request.url).startswith("https://api.github.com/repos/acme/widget/")
    assert request.headers["authorization"] == "Bearer secret"
    assert "secret" not in str(request.url)
    assert "secret" not in request.content.decode()


def test_check_fork_and_empty_token_make_no_http_requests() -> None:
    def unexpected(_: httpx.Request) -> httpx.Response:
        raise AssertionError("skipped publication must not call GitHub")

    transport = httpx.MockTransport(unexpected)

    assert (
        publish_check(check_context(fork=True), "ready", "Report", "secret", transport).mode
        is CheckMode.SKIP
    )
    assert publish_check(check_context(), "ready", "Report", "", transport).mode is CheckMode.SKIP
    assert publish_check_withdrawal(context(fork=True), "secret", transport).mode is CheckMode.SKIP
    assert publish_check_withdrawal(context(), "", transport).mode is CheckMode.SKIP


def test_exact_trusted_check_is_patched_with_neutral_validated_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert_safe_request(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        if request.method == "GET":
            assert request.url.params["check_name"] == CHECK_NAME
            return httpx.Response(200, json=check_list(check_response()))
        assert request.method == "PATCH"
        assert request.url.path.endswith("/check-runs/7")
        payload = json.loads(request.content)
        assert payload["name"] == CHECK_NAME
        assert payload["external_id"] == check_external_id(check_context())
        assert payload["status"] == "completed"
        assert payload["conclusion"] == "neutral"
        assert payload["output"]["title"] == "ScopeProof — Ready (informational)"
        assert "criteria source" in payload["output"]["text"].lower()
        return httpx.Response(200, json=check_response())

    plan = publish_check(check_context(), "ready", "Report", "secret", httpx.MockTransport(handler))

    assert plan.mode is CheckMode.UPDATE
    assert [request.method for request in requests] == ["GET", "GET", "GET", "PATCH"]


def test_fork_hosted_repository_same_repository_pr_can_publish() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response(fork=True))
        if request.method == "GET":
            return httpx.Response(200, json=check_list())
        return httpx.Response(201, json=check_response(check_run_id=8))

    plan = publish_check(check_context(), "ready", "Report", "secret", httpx.MockTransport(handler))

    assert plan.mode is CheckMode.CREATE
    assert [request.method for request in requests] == ["GET", "GET", "GET", "POST"]


def test_label_withdrawal_updates_only_existing_exact_head_check() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert_safe_request(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response(applicability_label=False))
        if request.method == "GET" and request.url.path.endswith("/commits") is False:
            if request.url.path.endswith("/check-runs/7"):
                return httpx.Response(200, json=check_detail_response())
            return httpx.Response(200, json=check_list(check_response()))
        assert request.method == "PATCH"
        payload = json.loads(request.content)
        assert payload["conclusion"] == "neutral"
        assert payload["output"]["title"] == "ScopeProof — Needs Review (informational)"
        assert "label was removed" in payload["output"]["summary"]
        assert "Confirmed criteria source" in payload["output"]["text"]
        return httpx.Response(200, json=check_response())

    plan = publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert plan.mode is CheckMode.UPDATE
    assert plan.reason == "applicability_label_removed"
    assert [request.method for request in requests] == ["GET", "GET", "GET", "GET", "PATCH"]


def test_closed_pull_label_withdrawal_updates_exact_head_check() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(
                200,
                json=pull_response(applicability_label=False, state="closed"),
            )
        if request.method == "GET" and request.url.path.endswith("/check-runs/7"):
            return httpx.Response(200, json=check_detail_response())
        if request.method == "GET":
            return httpx.Response(200, json=check_list(check_response()))
        return httpx.Response(200, json=check_response())

    plan = publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert plan.mode is CheckMode.UPDATE
    assert [request.method for request in requests] == ["GET", "GET", "GET", "GET", "PATCH"]


def test_withdrawal_preserves_maximum_length_prior_report_without_truncation() -> None:
    requests: list[httpx.Request] = []
    prior_text = "x" * 65_535

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response(applicability_label=False))
        if request.method == "GET" and request.url.path.endswith("/check-runs/7"):
            detail = check_detail_response()
            detail["output"]["text"] = prior_text
            return httpx.Response(200, json=detail)
        if request.method == "GET":
            return httpx.Response(200, json=check_list(check_response()))
        payload = json.loads(request.content)
        assert payload["output"]["text"] == prior_text
        assert "label was removed" in payload["output"]["summary"]
        return httpx.Response(200, json=check_response())

    plan = publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert plan.output.text == prior_text
    assert [request.method for request in requests] == ["GET", "GET", "GET", "GET", "PATCH"]


def test_withdrawal_rerun_keeps_canonical_summary() -> None:
    requests: list[httpx.Request] = []
    withdrawn = (
        "The `scopeproof-review` label was removed for this exact pull-request head. "
        "Applicability and any Ready display are revoked. ScopeProof evidence boundary"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response(applicability_label=False))
        if request.method == "GET" and request.url.path.endswith("/check-runs/7"):
            detail = check_detail_response()
            detail["output"]["summary"] = withdrawn
            return httpx.Response(200, json=detail)
        if request.method == "GET":
            return httpx.Response(200, json=check_list(check_response()))
        payload = json.loads(request.content)
        assert payload["output"]["summary"] == withdrawn
        return httpx.Response(200, json=check_response())

    plan = publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert plan.output.summary == withdrawn
    assert [request.method for request in requests] == ["GET", "GET", "GET", "GET", "PATCH"]


def test_missing_confirmation_revokes_existing_ready_display() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response(applicability_label=True))
        if request.method == "GET" and request.url.path.endswith("/check-runs/7"):
            return httpx.Response(200, json=check_detail_response())
        if request.method == "GET":
            return httpx.Response(200, json=check_list(check_response()))
        payload = json.loads(request.content)
        assert payload["output"]["title"] == "ScopeProof — Needs Review (informational)"
        assert "confirmation is unavailable" in payload["output"]["summary"]
        assert "Confirmed criteria source" in payload["output"]["text"]
        return httpx.Response(200, json=check_response())

    plan = publish_check_unavailability(context(), "secret", httpx.MockTransport(handler))

    assert plan.mode is CheckMode.UPDATE
    assert plan.reason == "requirements_confirmation_unavailable"
    assert [request.method for request in requests] == ["GET", "GET", "GET", "GET", "PATCH"]


def test_default_base_advance_revokes_existing_labeled_exact_head_check() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/repos/acme/widget/pulls" and "state" in request.url.params:
            return httpx.Response(200, json=[pull_response()])
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        if request.method == "GET" and request.url.path.endswith("/check-runs/7"):
            return httpx.Response(200, json=check_detail_response())
        if request.method == "GET":
            return httpx.Response(200, json=check_list(check_response()))
        payload = json.loads(request.content)
        assert payload["output"]["title"] == "ScopeProof — Needs Review (informational)"
        assert "target base branch advanced" in payload["output"]["summary"]
        return httpx.Response(200, json=check_response())

    result = publish_base_advance_invalidations(
        repository="acme/widget",
        base_ref="main",
        after_sha=BASE_SHA,
        token="secret",
        transport=httpx.MockTransport(handler),
    )

    assert result.updated_count == 1
    assert result.skipped_count == 0
    assert [request.method for request in requests] == [
        "GET",
        "GET",
        "GET",
        "GET",
        "GET",
        "PATCH",
    ]


def test_base_advance_without_token_is_non_mutating() -> None:
    def unexpected(_: httpx.Request) -> httpx.Response:
        raise AssertionError("missing-token base advance must not call GitHub")

    result = publish_base_advance_invalidations(
        repository="acme/widget",
        base_ref="main",
        after_sha=BASE_SHA,
        token="",
        transport=httpx.MockTransport(unexpected),
    )

    assert result.reason == "missing_token"
    assert result.updated_count == 0


def test_base_advance_accepts_exactly_110_pulls_with_empty_page_three_sentinel() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        per_page = int(request.url.params["per_page"])
        page = int(request.url.params["page"])
        assert per_page == 55
        if page == 3:
            return httpx.Response(200, json=[])
        start = (page - 1) * 55 + 1
        return httpx.Response(
            200,
            json=[
                pull_response(pr_number=number, applicability_label=False)
                for number in range(start, start + 55)
            ],
        )

    result = publish_base_advance_invalidations(
        repository="acme/widget",
        base_ref="main",
        after_sha=BASE_SHA,
        token="secret",
        transport=httpx.MockTransport(handler),
    )

    assert result.updated_count == 0
    assert len(requests) == 3


def test_base_advance_rejects_nonempty_overflow_sentinel_before_writes() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        per_page = int(request.url.params["per_page"])
        page = int(request.url.params["page"])
        assert per_page == 55
        if page == 3:
            return httpx.Response(
                200,
                json=[pull_response(pr_number=111, applicability_label=False)],
            )
        start = (page - 1) * 55 + 1
        return httpx.Response(
            200,
            json=[
                pull_response(pr_number=number, applicability_label=False)
                for number in range(start, start + 55)
            ],
        )

    with pytest.raises(GitHubCheckPublicationError, match="page budget"):
        publish_base_advance_invalidations(
            repository="acme/widget",
            base_ref="main",
            after_sha=BASE_SHA,
            token="secret",
            transport=httpx.MockTransport(handler),
        )

    assert len(requests) == 3
    assert all(request.method == "GET" for request in requests)


def test_base_advance_deep_check_pagination_stays_within_actions_token_budget() -> None:
    requests: list[httpx.Request] = []

    def pr_head_sha(pr_number: int) -> str:
        return f"{pr_number:040x}"

    def pr_context(pr_number: int) -> EventContext:
        return EventContext(
            repository="acme/widget",
            pr_number=pr_number,
            base_sha=BASE_SHA,
            head_sha=pr_head_sha(pr_number),
            is_fork=False,
            requirements_confirmed=False,
        )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == "/repos/acme/widget/pulls" and "state" in request.url.params:
            per_page = int(request.url.params["per_page"])
            page = int(request.url.params["page"])
            assert per_page == 55
            if page == 3:
                return httpx.Response(200, json=[])
            start = (page - 1) * 55 + 1
            return httpx.Response(
                200,
                json=[
                    pull_response(pr_number=number, head_sha=pr_head_sha(number))
                    for number in range(start, start + 55)
                ],
            )
        if "/pulls/" in path:
            pr_number = int(path.rsplit("/", 1)[-1])
            return httpx.Response(
                200,
                json=pull_response(
                    pr_number=pr_number,
                    head_sha=pr_head_sha(pr_number),
                ),
            )
        if "/commits/" in path:
            head_sha = path.split("/commits/", 1)[1].split("/", 1)[0]
            pr_number = int(head_sha, 16)
            page = int(request.url.params["page"])
            start = pr_number * 1_000 + (page - 1) * 100
            if page < 5:
                checks = [
                    check_response(
                        check_run_id=start + index + 1,
                        head_sha=head_sha,
                        external_id=f"foreign:{start + index + 1}",
                        app_slug="foreign-app",
                    )
                    for index in range(100)
                ]
            else:
                checks = [
                    check_response(
                        check_run_id=pr_number,
                        head_sha=head_sha,
                        external_id=check_external_id(pr_context(pr_number)),
                    )
                ]
            return httpx.Response(200, json=check_list(*checks, total_count=401))
        pr_number = int(path.rsplit("/", 1)[-1])
        existing = check_response(
            check_run_id=pr_number,
            head_sha=pr_head_sha(pr_number),
            external_id=check_external_id(pr_context(pr_number)),
        )
        if request.method == "GET":
            return httpx.Response(200, json=check_detail_response(**existing))
        return httpx.Response(200, json=existing)

    result = publish_base_advance_invalidations(
        repository="acme/widget",
        base_ref="main",
        after_sha=BASE_SHA,
        token="secret",
        transport=httpx.MockTransport(handler),
    )

    assert result.updated_count == 110
    assert len(requests) == 993
    assert len(requests) < 1_000


def test_publish_revalidates_live_base_immediately_before_write() -> None:
    requests: list[httpx.Request] = []
    pull_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal pull_reads
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            pull_reads += 1
            if pull_reads == 1:
                return httpx.Response(200, json=pull_response())
            return httpx.Response(200, json=pull_response(base_sha=OTHER_SHA))
        if request.method == "GET":
            return httpx.Response(200, json=check_list())
        raise AssertionError("stale base must fail before Check mutation")

    with pytest.raises(GitHubCheckPublicationError, match="identity mismatch"):
        publish_check(
            check_context(),
            "ready",
            "Report",
            "secret",
            httpx.MockTransport(handler),
        )

    assert [request.method for request in requests] == ["GET", "GET", "GET"]


def test_base_advance_skips_deleted_fork_before_processing_same_repo_pr() -> None:
    requests: list[httpx.Request] = []
    deleted_fork = pull_response(pr_number=41)
    deleted_fork["head"]["repo"] = None

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/repos/acme/widget/pulls" and "state" in request.url.params:
            return httpx.Response(200, json=[deleted_fork, pull_response()])
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        if request.method == "GET" and request.url.path.endswith("/check-runs/7"):
            return httpx.Response(200, json=check_detail_response())
        if request.method == "GET":
            return httpx.Response(200, json=check_list(check_response()))
        return httpx.Response(200, json=check_response())

    result = publish_base_advance_invalidations(
        repository="acme/widget",
        base_ref="main",
        after_sha=BASE_SHA,
        token="secret",
        transport=httpx.MockTransport(handler),
    )

    assert result.updated_count == 1
    assert all("pulls/41" not in str(request.url) for request in requests[1:])


def test_base_advance_continues_after_individual_pr_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[int] = []

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[pull_response(pr_number=41), pull_response(pr_number=42)],
        )

    def fake_publish(context, token, transport):
        attempted.append(context.pr_number)
        if context.pr_number == 41:
            raise GitHubCheckPublicationError("first PR failed")
        return type("Plan", (), {"mode": CheckMode.UPDATE})()

    monkeypatch.setattr(publisher_module, "publish_check_base_advance", fake_publish)

    with pytest.raises(GitHubCheckPublicationError, match="41"):
        publish_base_advance_invalidations(
            repository="acme/widget",
            base_ref="main",
            after_sha=BASE_SHA,
            token="secret",
            transport=httpx.MockTransport(handler),
        )

    assert attempted == [41, 42]


def test_label_withdrawal_without_exact_check_makes_no_write() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response(applicability_label=False))
        return httpx.Response(200, json=check_list())

    plan = publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert plan.mode is CheckMode.SKIP
    assert plan.reason == "no_exact_head_check"
    assert [request.method for request in requests] == ["GET", "GET"]


def test_live_applicability_label_is_revalidated_before_publication() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=pull_response(applicability_label=False))

    with pytest.raises(GitHubCheckPublicationError, match="applicability label mismatch"):
        publish_check(check_context(), "ready", "Report", "secret", httpx.MockTransport(handler))

    assert [request.method for request in requests] == ["GET"]


def test_withdrawal_rejects_reapplied_live_applicability_label() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=pull_response(applicability_label=True))

    with pytest.raises(GitHubCheckPublicationError, match="applicability label mismatch"):
        publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert [request.method for request in requests] == ["GET"]


def test_label_withdrawal_duplicate_exact_checks_fails_before_mutation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response(applicability_label=False))
        return httpx.Response(
            200,
            json=check_list(check_response(), check_response(check_run_id=8)),
        )

    with pytest.raises(GitHubCheckPublicationError, match="multiple trusted"):
        publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert [request.method for request in requests] == ["GET", "GET"]


@pytest.mark.parametrize(
    "existing",
    [
        check_response(head_sha=OTHER_SHA),
        check_response(external_id=f"scopeproof-check:v1:acme/widget:99:{HEAD_SHA}"),
        check_response(app_slug="foreign-app"),
    ],
)
def test_changed_or_foreign_check_posts_new_exact_head_check(existing: dict) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert_safe_request(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        if request.method == "GET":
            return httpx.Response(200, json=check_list(existing))
        assert request.method == "POST"
        assert request.url.path.endswith("/check-runs")
        payload = json.loads(request.content)
        assert payload["head_sha"] == HEAD_SHA
        assert payload["name"] == CHECK_NAME
        assert payload["conclusion"] == "neutral"
        return httpx.Response(201, json=check_response(check_run_id=8))

    plan = publish_check(
        check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler)
    )

    assert plan.mode is CheckMode.CREATE
    assert [request.method for request in requests] == ["GET", "GET", "GET", "POST"]


@pytest.mark.parametrize("external_id", [None, ""])
def test_foreign_same_name_check_without_external_id_is_ignored(
    external_id: str | None,
) -> None:
    requests: list[httpx.Request] = []
    foreign = check_response(app_slug="foreign-app")
    foreign["external_id"] = external_id

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        if request.method == "GET":
            return httpx.Response(200, json=check_list(foreign))
        return httpx.Response(201, json=check_response(check_run_id=8))

    plan = publish_check(
        check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler)
    )

    assert plan.mode is CheckMode.CREATE
    assert [request.method for request in requests] == ["GET", "GET", "GET", "POST"]


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("number",), 99),
        (("state",), "closed"),
        (("url",), "https://api.github.com/repos/acme/widget/pulls/99"),
        (("html_url",), "https://github.com/acme/widget/pull/99"),
        (("head", "sha"), OTHER_SHA),
        (("base", "sha"), OTHER_SHA),
        (("head", "repo", "full_name"), "acme/other"),
        (("base", "repo", "full_name"), "acme/other"),
    ],
)
def test_live_pull_request_identity_mismatch_fails_before_write(
    field_path: tuple[str, ...], value: object
) -> None:
    body = pull_response()
    target = body
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = value
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=body)

    with pytest.raises(GitHubCheckPublicationError):
        publish_check(check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler))

    assert [request.method for request in requests] == ["GET"]


def test_duplicate_trusted_checks_fail_before_mutation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        return httpx.Response(
            200,
            json=check_list(check_response(), check_response(check_run_id=8)),
        )

    with pytest.raises(GitHubCheckPublicationError, match="multiple trusted"):
        publish_check(check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler))

    assert [request.method for request in requests] == ["GET", "GET"]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://evil.example/steal"}),
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"unexpected": True}),
    ],
)
def test_status_or_malformed_response_fails_without_token_disclosure(
    response: httpx.Response,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert_safe_request(request)
        return response

    with pytest.raises(GitHubCheckPublicationError) as exc_info:
        publish_check(check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler))

    assert "secret" not in str(exc_info.value)


def test_repeated_check_page_is_rejected_before_mutation() -> None:
    requests: list[httpx.Request] = []
    page = [check_response(check_run_id=index + 1) for index in range(100)]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        return httpx.Response(200, json=check_list(*page, total_count=200))

    with pytest.raises(GitHubCheckPublicationError, match="repeated check run"):
        publish_check(check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler))

    assert all(request.method == "GET" for request in requests)


def test_sixth_check_page_is_rejected_before_mutation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/pulls/42"):
            return httpx.Response(200, json=pull_response())
        page_number = int(request.url.params["page"])
        checks = [
            check_response(check_run_id=(page_number - 1) * 100 + index + 1) for index in range(100)
        ]
        return httpx.Response(200, json=check_list(*checks, total_count=501))

    with pytest.raises(GitHubCheckPublicationError, match="page budget"):
        publish_check(check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler))

    assert len(requests) == 6
    assert all(request.method == "GET" for request in requests)


def test_publication_failure_does_not_mutate_validated_saved_review(
    tmp_path,
) -> None:
    store = JsonReviewStore(tmp_path / "reviews")
    state = new_review_state(build_demo_review())
    store.save(state)
    record_path = tmp_path / "reviews" / f"{state.review.review_id}.json"
    before_bytes = record_path.read_bytes()
    before_fingerprint = store.state_fingerprint(store.load(state.review.review_id))

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"message": "temporarily unavailable"})

    with pytest.raises(GitHubCheckPublicationError):
        publish_check(check_context(), "blocked", "Report", "secret", httpx.MockTransport(handler))

    assert record_path.read_bytes() == before_bytes
    assert store.state_fingerprint(store.load(state.review.review_id)) == before_fingerprint


def test_fork_context_makes_no_http_requests() -> None:
    def unexpected(_: httpx.Request) -> httpx.Response:
        raise AssertionError("fork publication must not call GitHub")

    result = publish_comment(
        context(fork=True), "Summary", "secret", httpx.MockTransport(unexpected)
    )

    assert result.mode is CommentMode.SKIP


def test_rerun_updates_same_head_comment_without_creating_another() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 7,
                        "body": f"<!-- scopeproof:{HEAD_SHA} -->",
                        "user": {"login": "github-actions[bot]", "type": "Bot"},
                    }
                ],
            )
        assert request.method == "PATCH"
        assert request.url.path.endswith("/issues/comments/7")
        assert "secret" not in request.content.decode()
        return httpx.Response(200, json={"id": 7})

    result = publish_comment(context(), "Summary", "secret", httpx.MockTransport(handler))

    assert result.mode is CommentMode.UPDATE
    assert [request.method for request in requests] == ["GET", "PATCH"]


def test_rerun_finds_same_head_comment_after_first_comment_page() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = request.url.params.get("page", "1")
        if request.method == "GET" and page == "1":
            return httpx.Response(
                200,
                json=[{"id": number, "body": "unrelated"} for number in range(100)],
                headers={
                    "Link": (
                        "<https://api.github.com/repos/acme/widget/issues/42/comments"
                        '?per_page=100&page=2>; rel="next"'
                    )
                },
            )
        if request.method == "GET" and page == "2":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 77,
                        "body": f"<!-- scopeproof:{HEAD_SHA} -->",
                        "user": {"login": "github-actions[bot]", "type": "Bot"},
                    }
                ],
            )
        if request.method == "POST":
            return httpx.Response(201, json={"id": 78})
        assert request.method == "PATCH"
        assert request.url.path.endswith("/issues/comments/77")
        return httpx.Response(200, json={"id": 77})

    result = publish_comment(context(), "Summary", "secret", httpx.MockTransport(handler))

    assert result.mode is CommentMode.UPDATE
    assert [request.method for request in requests] == ["GET", "GET", "PATCH"]


def test_rerun_does_not_update_untrusted_same_head_marker() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 7,
                        "body": f"<!-- scopeproof:{HEAD_SHA} -->",
                        "user": {"login": "unrelated-user", "type": "User"},
                    }
                ],
            )
        assert request.method == "POST"
        return httpx.Response(201, json={"id": 8})

    result = publish_comment(context(), "Summary", "secret", httpx.MockTransport(handler))

    assert result.mode is CommentMode.CREATE
    assert [request.method for request in requests] == ["GET", "POST"]


def test_new_head_creates_marker_comment() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        assert request.method == "POST"
        assert json.loads(request.content)["body"].endswith(f"<!-- scopeproof:{HEAD_SHA} -->")
        return httpx.Response(201, json={"id": 8})

    result = publish_comment(context(), "Summary", "secret", httpx.MockTransport(handler))

    assert result.mode is CommentMode.CREATE
