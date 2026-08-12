from __future__ import annotations

import base64

import httpx
import pytest

from scopeproof_core.github.client import GitHubClient, GitHubIngestionError

HEAD_SHA = "b" * 40
PR_URL = "https://github.com/acme/widget/pull/42"


def _pull_payload() -> dict:
    return {
        "number": 42,
        "title": "Paged export",
        "body": "",
        "html_url": PR_URL,
        "base": {
            "sha": "a" * 40,
            "repo": {
                "full_name": "acme/widget",
                "private": False,
                "visibility": "public",
            },
        },
        "head": {"sha": HEAD_SHA},
    }


def pagination_transport(
    *,
    file_pages: dict[int, object] | None = None,
    file_links: dict[int, str] | None = None,
    commit_pages: dict[int, object] | None = None,
    commit_links: dict[int, str] | None = None,
    pull_payload: dict | None = None,
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    requests: list[httpx.Request] = []
    file_pages = file_pages or {1: []}
    file_links = file_links or {}
    commit_pages = commit_pages or {1: []}
    commit_links = commit_links or {}

    def response(
        data: object,
        *,
        link: str | None = None,
    ) -> httpx.Response:
        headers = {"Link": link} if link is not None else None
        return httpx.Response(200, json=data, headers=headers)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        page = int(request.url.params.get("page", "1"))
        if path == "/repos/acme/widget/pulls/42":
            return response(pull_payload or _pull_payload())
        if path == "/repos/acme/widget/pulls/42/files":
            return response(file_pages.get(page, []), link=file_links.get(page))
        if path == "/repos/acme/widget/pulls/42/commits":
            return response(commit_pages.get(page, []), link=commit_links.get(page))
        if path == f"/repos/acme/widget/commits/{HEAD_SHA}/check-runs":
            return response({"check_runs": []})
        if path == f"/repos/acme/widget/commits/{HEAD_SHA}/status":
            return response({"state": "success"})
        return httpx.Response(404, json={"message": path})

    return httpx.MockTransport(handler), requests


def paged_transport() -> httpx.MockTransport:
    def response(data: object, *, headers: dict[str, str] | None = None) -> httpx.Response:
        return httpx.Response(200, json=data, headers=headers)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        page = request.url.params.get("page", "1")
        if path == "/repos/acme/widget/pulls/42":
            return response(
                {
                    "number": 42,
                    "title": "Paged export",
                    "body": "",
                    "html_url": "https://github.com/acme/widget/pull/42",
                    "base": {
                        "sha": "base",
                        "repo": {
                            "full_name": "acme/widget",
                            "private": False,
                            "visibility": "public",
                        },
                    },
                    "head": {"sha": "head"},
                }
            )
        if path.endswith("/files") and page == "1":
            return response(
                [
                    {
                        "filename": "src/first.py",
                        "status": "modified",
                        "patch": "@@ -1 +1 @@\n+first",
                    }
                ],
                headers={
                    "Link": (
                        "<https://api.github.com/repos/acme/widget/pulls/42/"
                        'files?page=2&per_page=100>; rel="next"'
                    )
                },
            )
        if path.endswith("/files") and page == "2":
            return response(
                [
                    {
                        "filename": "src/second.py",
                        "status": "modified",
                        "patch": "@@ -1 +1 @@\n+second",
                    }
                ]
            )
        if path.endswith("/commits"):
            return response([])
        if path.endswith("/check-runs"):
            return response({"check_runs": []})
        if path.endswith("/status"):
            return response({"state": "success"})
        if path == "/repos/acme/widget/contents/src/export.py":
            content = base64.b64encode(b"def export_csv(rows):\n    return rows\n").decode()
            return response({"type": "file", "encoding": "base64", "content": content})
        return httpx.Response(404, json={"message": path})

    return httpx.MockTransport(handler)


def test_files_pagination_continues_until_no_next_page() -> None:
    snapshot = GitHubClient(transport=paged_transport()).fetch_pull_request(
        "https://github.com/acme/widget/pull/42"
    )
    assert [file.path for file in snapshot.files] == ["src/first.py", "src/second.py"]
    assert snapshot.skipped_files == []


def test_pagination_rejects_off_origin_before_forwarding_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/repos/acme/widget/pulls/42":
            return httpx.Response(200, json=_pull_payload())
        if request.url.path.endswith("/files") and request.url.host == "api.github.com":
            return httpx.Response(
                200,
                json=[],
                headers={
                    "Link": (
                        "<https://attacker.invalid/repos/acme/widget/pulls/42/"
                        'files?page=2&per_page=100>; rel="next"'
                    )
                },
            )
        if request.url.host == "attacker.invalid":
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/check-runs"):
            return httpx.Response(200, json={"check_runs": []})
        if request.url.path.endswith("/status"):
            return httpx.Response(200, json={"state": "success"})
        return httpx.Response(404, json={"message": request.url.path})

    client = GitHubClient(
        token="session-secret",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GitHubIngestionError, match="expected GitHub API origin"):
        client.fetch_pull_request(PR_URL)

    assert [request.url.host for request in requests] == [
        "api.github.com",
        "api.github.com",
    ]
    assert all(request.url.host != "attacker.invalid" for request in requests)


def test_pagination_validates_unfollowed_next_link_at_overflow_boundary() -> None:
    files = [
        {
            "filename": f"src/{index}.py",
            "status": "modified",
            "patch": f"@@ -1 +1 @@\n+value = {index}",
        }
        for index in range(2)
    ]
    transport, requests = pagination_transport(
        file_pages={1: files},
        file_links={
            1: (
                "<https://attacker.invalid/repos/acme/widget/pulls/42/"
                'files?page=2&per_page=2>; rel="next"'
            )
        },
    )

    with pytest.raises(GitHubIngestionError, match="expected GitHub API origin"):
        GitHubClient(transport=transport, max_files=1).fetch_pull_request(PR_URL)

    assert len(requests) == 2


@pytest.mark.parametrize(
    "next_link",
    [
        "http://api.github.com/repos/acme/widget/pulls/42/files?page=2&per_page=100",
        "https://attacker.invalid/repos/acme/widget/pulls/42/files?page=2&per_page=100",
        "https://api.github.com/repos/other/widget/pulls/42/files?page=2&per_page=100",
        "https://api.github.com/repos/acme/widget/pulls/43/files?page=2&per_page=100",
        "https://api.github.com/repos/acme/widget/pulls/42/commits?page=2&per_page=100",
        "https://api.github.com/repos/acme/widget/pulls/42/files?page=2&per_page=100&extra=1",
        "https://api.github.com/repos/acme/widget/pulls/42/files?page=2&page=3&per_page=100",
        "https://api.github.com/repos/acme/widget/pulls/42/files?page=2",
        "https://api.github.com/repos/acme/widget/pulls/42/files?page=+2&per_page=100",
        "https://api.github.com/repos/acme/widget/pulls/42/files?page=02&per_page=100",
        "https://api.github.com/repos/acme/widget/pulls/42/files?page=2&per_page=0100",
    ],
)
def test_pagination_rejects_downgrade_escape_and_ambiguous_queries(
    next_link: str,
) -> None:
    transport, requests = pagination_transport(
        file_links={1: f'<{next_link}>; rel="next"'},
    )

    with pytest.raises(GitHubIngestionError, match="pagination target"):
        GitHubClient(transport=transport).fetch_pull_request(PR_URL)

    assert len(requests) == 2


def test_pagination_rejects_multiple_next_relations() -> None:
    transport, requests = pagination_transport(
        file_links={
            1: (
                "<https://api.github.com/repos/acme/widget/pulls/42/"
                'files?page=2&per_page=100>; rel="next", '
                "<https://api.github.com/repos/acme/widget/pulls/42/"
                'files?page=3&per_page=100>; rel="next"'
            )
        },
    )

    with pytest.raises(GitHubIngestionError, match="ambiguous"):
        GitHubClient(transport=transport).fetch_pull_request(PR_URL)

    assert len(requests) == 2


def test_pagination_allows_terminal_link_header_without_next_relation() -> None:
    transport, _ = pagination_transport(
        file_links={
            1: (
                "<https://api.github.com/repos/acme/widget/pulls/42/"
                'files?page=1&per_page=100>; rel="first", '
                "<https://api.github.com/repos/acme/widget/pulls/42/"
                'files?page=1&per_page=100>; rel="last"'
            )
        },
    )

    snapshot = GitHubClient(transport=transport).fetch_pull_request(PR_URL)

    assert snapshot.files == []


def test_pagination_rejects_malformed_link_header_without_relation() -> None:
    transport, _ = pagination_transport(file_links={1: "not-a-link-header"})

    with pytest.raises(GitHubIngestionError, match="malformed Link header"):
        GitHubClient(transport=transport).fetch_pull_request(PR_URL)


def test_pagination_rejects_two_page_cycle_before_repeating_request() -> None:
    second_page = "https://api.github.com/repos/acme/widget/pulls/42/files?page=2&per_page=100"
    first_page = "https://api.github.com/repos/acme/widget/pulls/42/files?page=1&per_page=100"
    transport, requests = pagination_transport(
        file_pages={1: [], 2: []},
        file_links={
            1: f'<{second_page}>; rel="next"',
            2: f'<{first_page}>; rel="next"',
        },
    )

    with pytest.raises(GitHubIngestionError, match=r"cycle|repeated"):
        GitHubClient(transport=transport).fetch_pull_request(PR_URL)

    assert [request.url.params.get("page") for request in requests] == [None, None, "2"]


def test_pagination_rejects_non_advancing_page_sequence() -> None:
    second_page = "https://api.github.com/repos/acme/widget/pulls/42/files?page=2&per_page=100"
    earlier_page = "https://api.github.com/repos/acme/widget/pulls/42/files?page=1&per_page=100"
    transport, requests = pagination_transport(
        file_pages={1: [], 2: []},
        file_links={
            1: f'<{second_page}>; rel="next"',
            2: f'<{earlier_page}>; rel="next"',
        },
    )

    with pytest.raises(GitHubIngestionError, match="advance"):
        GitHubClient(transport=transport).fetch_pull_request(PR_URL)

    assert [request.url.params.get("page") for request in requests] == [None, None, "2"]


@pytest.mark.parametrize(
    ("client_kwargs", "expected_message"),
    [
        ({"max_requests": 1}, "request budget"),
        ({"max_pagination_pages": 1}, "page budget"),
        ({"max_pagination_items": 1}, "item budget"),
        ({"max_response_bytes": 64}, "decoded response byte budget"),
    ],
)
def test_pagination_enforces_independent_budgets(
    client_kwargs: dict[str, int],
    expected_message: str,
) -> None:
    item = {
        "filename": "src/first.py",
        "status": "modified",
        "patch": "@@ -1 +1 @@\n+first",
    }
    second_page = "https://api.github.com/repos/acme/widget/pulls/42/files?page=2&per_page=100"
    transport, _ = pagination_transport(
        file_pages={1: [item], 2: [item]},
        file_links={1: f'<{second_page}>; rel="next"'},
    )

    with pytest.raises(GitHubIngestionError, match=expected_message):
        GitHubClient(transport=transport, **client_kwargs).fetch_pull_request(PR_URL)


def test_pagination_enforces_cumulative_decoded_response_budget() -> None:
    payload = _pull_payload()
    payload["body"] = "p" * 5_000
    file_item = {
        "filename": "src/large.py",
        "status": "modified",
        "patch": "x" * 5_000,
    }
    transport, _ = pagination_transport(
        pull_payload=payload,
        file_pages={1: [file_item]},
    )

    with pytest.raises(GitHubIngestionError, match="total decoded response byte budget"):
        GitHubClient(
            transport=transport,
            max_response_bytes=7_000,
            max_total_response_bytes=9_000,
        ).fetch_pull_request(PR_URL)


def test_pagination_rejects_non_list_collection_payload() -> None:
    transport, _ = pagination_transport(file_pages={1: {"filename": "src/not-a-list.py"}})

    with pytest.raises(GitHubIngestionError, match="list response"):
        GitHubClient(transport=transport).fetch_pull_request(PR_URL)


@pytest.mark.parametrize("collection", ["files", "commits"])
def test_pagination_rejects_malformed_observed_overflow_item(collection: str) -> None:
    file_item = {
        "filename": "src/valid.py",
        "status": "modified",
        "patch": "@@ -1 +1 @@\n+valid = True",
    }
    commit_item = {
        "sha": "1" * 40,
        "commit": {"message": "Valid"},
        "html_url": "https://github.com/acme/widget/commit/1",
    }
    kwargs: dict[str, object] = {"max_files": 1, "max_commits": 1}
    transport_kwargs = (
        {"file_pages": {1: [file_item, {}]}}
        if collection == "files"
        else {"commit_pages": {1: [commit_item, {}]}}
    )
    transport, _ = pagination_transport(**transport_kwargs)

    with pytest.raises(GitHubIngestionError, match=f"malformed {collection[:-1]} metadata"):
        GitHubClient(transport=transport, **kwargs).fetch_pull_request(PR_URL)


def test_file_ingestion_stops_after_smallest_observed_overflow() -> None:
    files = [
        {
            "filename": f"src/{index:03d}.py",
            "status": "modified",
            "patch": f"@@ -1 +1 @@\n+value = {index}",
        }
        for index in range(3)
    ]
    second_page = "https://api.github.com/repos/acme/widget/pulls/42/files?page=2&per_page=2"
    transport, requests = pagination_transport(
        file_pages={1: files[:2], 2: files[2:]},
        file_links={1: f'<{second_page}>; rel="next"'},
    )

    snapshot = GitHubClient(transport=transport, max_files=1).fetch_pull_request(PR_URL)

    assert [item.path for item in snapshot.files] == ["src/000.py"]
    assert snapshot.skipped_files == ["src/001.py"]
    assert snapshot.ingestion_state.value == "partial"
    assert any(
        "additional changed files were not retrieved" in warning
        for warning in snapshot.warnings
    )
    file_requests = [request for request in requests if request.url.path.endswith("/files")]
    assert [request.url.params.get("page") for request in file_requests] == [None]


def test_commit_ingestion_is_bounded_and_preserves_source_order() -> None:
    commits = [
        {
            "sha": str(index) * 40,
            "commit": {"message": f"Commit {index}"},
            "html_url": f"https://github.com/acme/widget/commit/{index}",
        }
        for index in range(1, 5)
    ]
    second_page = (
        "https://api.github.com/repos/acme/widget/pulls/42/commits?page=2&per_page=3"
    )
    transport, requests = pagination_transport(
        commit_pages={1: commits[:3], 2: commits[3:]},
        commit_links={1: f'<{second_page}>; rel="next"'},
    )

    snapshot = GitHubClient(transport=transport, max_commits=2).fetch_pull_request(PR_URL)

    assert [item.sha for item in snapshot.commits] == ["1" * 40, "2" * 40]
    assert snapshot.ingestion_state.value == "partial"
    assert any("commit history" in warning.lower() for warning in snapshot.warnings)
    commit_requests = [request for request in requests if request.url.path.endswith("/commits")]
    assert [request.url.params.get("page") for request in commit_requests] == [None]


def test_paginated_files_and_commits_keep_github_order() -> None:
    first_file = {
        "filename": "src/first.py",
        "status": "modified",
        "patch": "@@ -1 +1 @@\n+first",
    }
    second_file = {
        "filename": "src/second.py",
        "status": "modified",
        "patch": "@@ -1 +1 @@\n+second",
    }
    commits = [
        {
            "sha": character * 40,
            "commit": {"message": character},
            "html_url": f"https://github.com/acme/widget/commit/{character}",
        }
        for character in ("a", "b")
    ]
    transport, _ = pagination_transport(
        file_pages={1: [first_file], 2: [second_file]},
        file_links={
            1: (
                "<https://api.github.com/repos/acme/widget/pulls/42/"
                'files?page=2&per_page=6>; rel="next"'
            )
        },
        commit_pages={1: commits[:1], 2: commits[1:]},
        commit_links={
            1: (
                "<https://api.github.com/repos/acme/widget/pulls/42/"
                'commits?page=2&per_page=6>; rel="next"'
            )
        },
    )

    snapshot = GitHubClient(
        transport=transport,
        max_files=5,
        max_commits=5,
    ).fetch_pull_request(PR_URL)

    assert [item.path for item in snapshot.files] == ["src/first.py", "src/second.py"]
    assert [item.sha for item in snapshot.commits] == ["a" * 40, "b" * 40]


def test_candidate_file_is_bounded_and_anchored_to_head_sha() -> None:
    client = GitHubClient(
        transport=paged_transport(), max_candidate_files=1, max_candidate_bytes=128
    )
    candidates = client.fetch_candidate_files("acme/widget", HEAD_SHA, ["src/export.py"])
    assert candidates[0].path == "src/export.py"
    assert candidates[0].commit_sha == HEAD_SHA
    assert candidates[0].source_scope == "unchanged_candidate"
    assert candidates[0].content.startswith("def export_csv")


def test_empty_candidate_request_needs_no_commit_anchor() -> None:
    client = GitHubClient(transport=paged_transport())

    assert client.fetch_candidate_files("acme/widget", "unused", []) == []


@pytest.mark.parametrize("path", ["/etc/passwd", "../secret.txt", "src/../secret.txt"])
def test_candidate_file_rejects_paths_outside_repository(path: str) -> None:
    client = GitHubClient(transport=paged_transport())

    with pytest.raises(ValueError, match="repository-relative"):
        client.fetch_candidate_files("acme/widget", HEAD_SHA, [path])


@pytest.mark.parametrize(
    ("path", "encoded_path"),
    [
        ("src/probe.py?mode=default", b"src/probe.py%3Fmode%3Ddefault"),
        ("src/hash#fragment.py", b"src/hash%23fragment.py"),
        ("src/percent%file.py", b"src/percent%25file.py"),
        ("src/space file.py", b"src/space%20file.py"),
        ("src/\u65e5\u672c\u8a9e.py", b"src/%E6%97%A5%E6%9C%AC%E8%AA%9E.py"),
    ],
)
def test_candidate_file_encodes_path_and_transmits_exact_head_ref(
    path: str, encoded_path: bytes
) -> None:
    observed_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed_requests.append(request)
        content = base64.b64encode(b"candidate = True\n").decode()
        return httpx.Response(
            200,
            json={"type": "file", "encoding": "base64", "content": content},
        )

    client = GitHubClient(transport=httpx.MockTransport(handler))

    candidates = client.fetch_candidate_files("acme/widget", HEAD_SHA, [path])

    assert len(observed_requests) == 1
    request = observed_requests[0]
    assert request.url.raw_path.split(b"?", maxsplit=1)[0].endswith(encoded_path)
    assert request.url.params.multi_items() == [("ref", HEAD_SHA)]
    assert candidates[0].path == path
    assert candidates[0].commit_sha == HEAD_SHA


@pytest.mark.parametrize(
    "head_sha",
    ["head", "a" * 39, "a" * 41, "A" * 40, "g" * 40],
)
def test_candidate_file_rejects_non_exact_commit_sha(head_sha: str) -> None:
    client = GitHubClient(transport=paged_transport())

    with pytest.raises(ValueError, match="40-character lowercase commit SHA"):
        client.fetch_candidate_files("acme/widget", head_sha, ["src/export.py"])


def test_candidate_file_rejects_response_not_anchored_to_request() -> None:
    other_sha = "c" * 40

    class UnanchoredResponseClient(GitHubClient):
        def _get(
            self, path: str, *, params: dict[str, str] | None = None
        ) -> httpx.Response:
            content = base64.b64encode(b"candidate = True\n").decode()
            return httpx.Response(
                200,
                request=httpx.Request(
                    "GET",
                    "https://api.github.com/repos/acme/widget/contents/"
                    f"src/export.py?ref={other_sha}",
                ),
                json={"type": "file", "encoding": "base64", "content": content},
            )

    client = UnanchoredResponseClient()

    with pytest.raises(GitHubIngestionError, match="not anchored to the requested path and SHA"):
        client.fetch_candidate_files("acme/widget", HEAD_SHA, ["src/export.py"])


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"type": "dir", "encoding": "base64", "content": ""},
        {"type": "file", "encoding": "base64", "content": None},
        {"type": "file", "encoding": "base64", "content": "%%%not-base64%%%"},
    ],
)
def test_candidate_file_rejects_malformed_content_response(payload: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, json=payload)

    client = GitHubClient(transport=httpx.MockTransport(handler))

    with pytest.raises(GitHubIngestionError, match="not a readable UTF-8 text file"):
        client.fetch_candidate_files("acme/widget", HEAD_SHA, ["src/export.py"])
