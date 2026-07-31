from __future__ import annotations

import base64

import httpx
import pytest

from scopeproof_core.github.client import GitHubClient, GitHubIngestionError

HEAD_SHA = "b" * 40


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
                    "base": {"sha": "base"},
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
                        "<https://api.github.com/repos/acme/widget/pulls/42/files?page=2>; "
                        'rel="next"'
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
