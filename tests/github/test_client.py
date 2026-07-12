from __future__ import annotations

import json

import httpx
import pytest

from scopeproof_core.github.client import (
    GitHubClient,
    GitHubRateLimited,
    InvalidPullRequestUrl,
    PrivateOrInaccessibleRepository,
    PullRequestNotFound,
    parse_pr_url,
)
from scopeproof_core.schemas.models import CheckState, IngestionState, LineChangeType


def _response(status: int, data: object, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, json=data, headers=headers)


def fixture_transport(
    *,
    file_count: int = 1,
    pull_status: int = 200,
    pull_headers: dict[str, str] | None = None,
) -> httpx.MockTransport:
    files = [
        {
            "filename": f"src/export_{index}.py",
            "status": "modified",
            "additions": 2,
            "deletions": 1,
            "changes": 3,
            "patch": (
                "@@ -10,2 +10,3 @@\n-old_export()\n+def export_csv():"
                "\n+    return filtered_rows\n context()"
            ),
        }
        for index in range(file_count)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/acme/widget/pulls/42":
            if pull_status != 200:
                return _response(pull_status, {"message": "request failed"}, pull_headers)
            return _response(
                200,
                {
                    "number": 42,
                    "title": "Export CSV",
                    "body": "Adds export",
                    "html_url": "https://github.com/acme/widget/pull/42",
                    "base": {"sha": "base123"},
                    "head": {"sha": "head123"},
                },
            )
        if path.endswith("/files"):
            return _response(200, files)
        if path.endswith("/commits"):
            return _response(
                200,
                [
                    {
                        "sha": "head123",
                        "commit": {"message": "Add export"},
                        "html_url": "https://github.com/acme/widget/commit/head123",
                    }
                ],
            )
        if path.endswith("/check-runs"):
            return _response(
                200, {"check_runs": [{"status": "completed", "conclusion": "success"}]}
            )
        if path.endswith("/status"):
            return _response(200, {"state": "success"})
        return _response(404, {"message": f"Unhandled {path}"})

    return httpx.MockTransport(handler)


def test_parse_pr_url_accepts_only_github_pull_urls() -> None:
    assert parse_pr_url("https://github.com/acme/widget/pull/42") == ("acme", "widget", 42)
    for invalid in (
        "https://example.com/acme/widget/pull/42",
        "https://github.com/acme/widget/issues/42",
        "not a URL",
    ):
        with pytest.raises(InvalidPullRequestUrl):
            parse_pr_url(invalid)


def test_client_uses_optional_token_without_placing_it_in_snapshot() -> None:
    client = GitHubClient(token="secret", transport=fixture_transport())
    snapshot = client.fetch_pull_request("https://github.com/acme/widget/pull/42")
    assert snapshot.repository == "acme/widget"
    assert "secret" not in snapshot.model_dump_json()
    assert client.last_request_authorized is True


def test_client_maps_patch_lines_and_keeps_removed_lines_distinct() -> None:
    snapshot = GitHubClient(transport=fixture_transport()).fetch_pull_request(
        "https://github.com/acme/widget/pull/42"
    )
    lines = snapshot.files[0].lines
    assert [(line.change_type, line.line_number) for line in lines] == [
        (LineChangeType.REMOVED, 10),
        (LineChangeType.ADDED, 10),
        (LineChangeType.ADDED, 11),
        (LineChangeType.CONTEXT, 12),
    ]


def test_check_runs_and_commit_status_aggregate_to_passing() -> None:
    snapshot = GitHubClient(transport=fixture_transport()).fetch_pull_request(
        "https://github.com/acme/widget/pull/42"
    )
    assert snapshot.check_state is CheckState.PASSING


@pytest.mark.parametrize(
    ("status", "headers", "expected"),
    [
        (404, {}, PullRequestNotFound),
        (403, {"x-ratelimit-remaining": "10"}, PrivateOrInaccessibleRepository),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "123"}, GitHubRateLimited),
    ],
)
def test_client_classifies_github_errors(
    status: int, headers: dict[str, str], expected: type[Exception]
) -> None:
    client = GitHubClient(transport=fixture_transport(pull_status=status, pull_headers=headers))
    with pytest.raises(expected):
        client.fetch_pull_request("https://github.com/acme/widget/pull/42")


def test_file_limit_marks_snapshot_partial_and_lists_skipped_files() -> None:
    client = GitHubClient(transport=fixture_transport(file_count=3), max_files=1)
    snapshot = client.fetch_pull_request("https://github.com/acme/widget/pull/42")
    assert snapshot.ingestion_state is IngestionState.PARTIAL
    assert len(snapshot.files) == 1
    assert snapshot.skipped_files == ["src/export_1.py", "src/export_2.py"]
    assert any("file limit" in warning.lower() for warning in snapshot.warnings)


def test_snapshot_json_contains_no_authorization_header() -> None:
    snapshot = GitHubClient(token="ghp_private", transport=fixture_transport()).fetch_pull_request(
        "https://github.com/acme/widget/pull/42"
    )
    data = json.loads(snapshot.model_dump_json())
    assert "authorization" not in json.dumps(data).lower()
    assert "ghp_private" not in json.dumps(data)
