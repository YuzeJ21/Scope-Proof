from __future__ import annotations

import base64

import httpx

from scopeproof_core.github.client import GitHubClient


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
    candidates = client.fetch_candidate_files("acme/widget", "head", ["src/export.py"])
    assert candidates[0].path == "src/export.py"
    assert candidates[0].commit_sha == "head"
    assert candidates[0].source_scope == "unchanged_candidate"
    assert candidates[0].content.startswith("def export_csv")
