import json
from datetime import UTC, datetime

import httpx
import pytest

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
    publish_check,
    publish_check_withdrawal,
    publish_comment,
)
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import CriteriaSourceProvenance
from scopeproof_core.storage.json_store import JsonReviewStore

HEAD_SHA = "2" * 40
OTHER_SHA = "3" * 40


def context(*, fork: bool = False) -> EventContext:
    return EventContext(
        repository="acme/widget",
        pr_number=42,
        head_sha=HEAD_SHA,
        is_fork=fork,
        requirements_confirmed=True,
    )


def check_context(*, fork: bool = False) -> CheckRunContext:
    return CheckRunContext(
        repository="acme/widget",
        pr_number=42,
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
    *, head_sha: str = HEAD_SHA, fork: bool = False, applicability_label: bool = True
) -> dict:
    return {
        "url": "https://api.github.com/repos/acme/widget/pulls/42",
        "html_url": "https://github.com/acme/widget/pull/42",
        "number": 42,
        "state": "open",
        "head": {
            "sha": head_sha,
            "repo": {
                "full_name": "acme/widget",
                "fork": fork,
            },
        },
        "base": {"repo": {"full_name": "acme/widget"}},
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
    assert [request.method for request in requests] == ["GET", "GET", "PATCH"]


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
    assert [request.method for request in requests] == ["GET", "GET", "POST"]


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
        assert "label was removed" in payload["output"]["text"]
        assert "Confirmed criteria source" in payload["output"]["text"]
        return httpx.Response(200, json=check_response())

    plan = publish_check_withdrawal(context(), "secret", httpx.MockTransport(handler))

    assert plan.mode is CheckMode.UPDATE
    assert plan.reason == "applicability_label_removed"
    assert [request.method for request in requests] == ["GET", "GET", "GET", "PATCH"]


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
    assert [request.method for request in requests] == ["GET", "GET", "POST"]


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
    assert [request.method for request in requests] == ["GET", "GET", "POST"]


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("number",), 99),
        (("state",), "closed"),
        (("url",), "https://api.github.com/repos/acme/widget/pulls/99"),
        (("html_url",), "https://github.com/acme/widget/pull/99"),
        (("head", "sha"), OTHER_SHA),
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
