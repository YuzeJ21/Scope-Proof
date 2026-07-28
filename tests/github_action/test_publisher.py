import json

import httpx

from scopeproof_core.github_action import CommentMode, EventContext
from scopeproof_core.github_action_publisher import publish_comment

HEAD_SHA = "2" * 40


def context(*, fork: bool = False) -> EventContext:
    return EventContext(
        repository="acme/widget",
        pr_number=42,
        head_sha=HEAD_SHA,
        is_fork=fork,
        requirements_confirmed=True,
    )


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
                200, json=[{"id": 7, "body": f"<!-- scopeproof:{HEAD_SHA} -->"}]
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
                        '<https://api.github.com/repos/acme/widget/issues/42/comments'
                        '?per_page=100&page=2>; rel="next"'
                    )
                },
            )
        if request.method == "GET" and page == "2":
            return httpx.Response(
                200, json=[{"id": 77, "body": f"<!-- scopeproof:{HEAD_SHA} -->"}]
            )
        if request.method == "POST":
            return httpx.Response(201, json={"id": 78})
        assert request.method == "PATCH"
        assert request.url.path.endswith("/issues/comments/77")
        return httpx.Response(200, json={"id": 77})

    result = publish_comment(context(), "Summary", "secret", httpx.MockTransport(handler))

    assert result.mode is CommentMode.UPDATE
    assert [request.method for request in requests] == ["GET", "GET", "PATCH"]


def test_new_head_creates_marker_comment() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        assert request.method == "POST"
        assert json.loads(request.content)["body"].endswith(
            f"<!-- scopeproof:{HEAD_SHA} -->"
        )
        return httpx.Response(201, json={"id": 8})

    result = publish_comment(context(), "Summary", "secret", httpx.MockTransport(handler))

    assert result.mode is CommentMode.CREATE
