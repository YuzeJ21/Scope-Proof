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
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    IngestionState,
    LineChangeType,
)


def _response(status: int, data: object, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, json=data, headers=headers)


def fixture_transport(
    *,
    file_count: int = 1,
    pull_status: int = 200,
    pull_headers: dict[str, str] | None = None,
    check_data: dict | None = None,
    check_status: int = 200,
    status_data: dict | None = None,
    status_status: int = 200,
    requested_urls: list[httpx.URL] | None = None,
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
        if requested_urls is not None:
            requested_urls.append(request.url)
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
                check_status,
                check_data
                if check_data is not None
                else {"check_runs": [{"status": "completed", "conclusion": "success"}]},
            )
        if path.endswith("/status"):
            return _response(
                status_status,
                status_data if status_data is not None else {"state": "success"},
            )
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


def test_client_requests_maximum_bounded_ci_observation_pages() -> None:
    requested_urls: list[httpx.URL] = []
    GitHubClient(
        transport=fixture_transport(requested_urls=requested_urls)
    ).fetch_pull_request("https://github.com/acme/widget/pull/42")

    ci_queries = {
        url.path: url.params.get("per_page")
        for url in requested_urls
        if url.path.endswith(("/check-runs", "/status"))
    }
    assert ci_queries == {
        "/repos/acme/widget/commits/head123/check-runs": "100",
        "/repos/acme/widget/commits/head123/status": "100",
    }


@pytest.mark.parametrize(
    ("check_data", "expected_state", "must_include"),
    [
        (
            {
                "total_count": 2,
                "check_runs": [
                    {"name": "verify", "status": "completed", "conclusion": "failure"}
                ],
            },
            CheckState.FAILING,
            "failing check run",
        ),
        (
            {
                "total_count": 2,
                "check_runs": [
                    {"name": "verify", "status": "in_progress", "conclusion": None}
                ],
            },
            CheckState.PENDING,
            "pending check run",
        ),
        (
            {
                "total_count": 2,
                "check_runs": [
                    {"name": "verify", "status": "completed", "conclusion": "success"}
                ],
            },
            CheckState.UNAVAILABLE,
            "passing cannot be concluded",
        ),
    ],
)
def test_incomplete_check_run_collection_fails_closed_without_hiding_failure_or_pending(
    check_data: dict, expected_state: CheckState, must_include: str
) -> None:
    snapshot = GitHubClient(
        transport=fixture_transport(
            check_data=check_data,
            status_data={"state": "pending", "total_count": 0, "statuses": []},
        )
    ).fetch_pull_request("https://github.com/acme/widget/pull/42")

    assert snapshot.check_state is expected_state
    assert snapshot.ci_observation.collection_complete is False
    assert "collection is incomplete" in snapshot.ci_observation.reason.lower()
    assert must_include in snapshot.ci_observation.reason.lower()


def test_incomplete_legacy_status_collection_prevents_a_passing_observation() -> None:
    snapshot = GitHubClient(
        transport=fixture_transport(
            check_data={"total_count": 0, "check_runs": []},
            status_data={
                "state": "success",
                "total_count": 2,
                "statuses": [{"state": "success"}],
            },
        )
    ).fetch_pull_request("https://github.com/acme/widget/pull/42")

    assert snapshot.check_state is CheckState.UNAVAILABLE
    assert snapshot.ci_observation.collection_complete is False
    assert "legacy statuses" in snapshot.ci_observation.reason.lower()


@pytest.mark.parametrize(
    ("check_status", "status_status", "unavailable_endpoint"),
    [
        (503, 200, "check-runs endpoint was unavailable"),
        (200, 503, "legacy status endpoint was unavailable"),
    ],
)
def test_unavailable_ci_endpoint_fails_closed_when_remaining_endpoint_succeeds(
    check_status: int, status_status: int, unavailable_endpoint: str
) -> None:
    snapshot = GitHubClient(
        transport=fixture_transport(
            check_status=check_status,
            status_status=status_status,
            check_data={
                "total_count": 1,
                "check_runs": [
                    {"name": "verify", "status": "completed", "conclusion": "success"}
                ],
            },
            status_data={
                "state": "success",
                "total_count": 1,
                "statuses": [{"state": "success"}],
            },
        )
    ).fetch_pull_request("https://github.com/acme/widget/pull/42")

    assert snapshot.check_state is CheckState.UNAVAILABLE
    assert snapshot.ci_observation.collection_complete is False
    assert unavailable_endpoint in snapshot.ci_observation.reason.lower()
    assert "passing cannot be concluded" in snapshot.ci_observation.reason.lower()


def test_empty_legacy_pending_does_not_override_completed_successful_check_run() -> None:
    observation = GitHubClient._check_observation(
        {"check_runs": [{"name": "verify", "status": "completed", "conclusion": "success"}]},
        {"state": "pending", "total_count": 0, "statuses": []},
    )

    assert observation == CIObservation(
        state=CheckState.PASSING,
        reason="Observed 1 successful completed check run; no concrete legacy statuses.",
        total_check_runs=1,
        successful_check_runs=1,
        concrete_legacy_status_count=0,
    )
    assert GitHubClient._check_state(
        {"check_runs": [{"name": "verify", "status": "completed", "conclusion": "success"}]},
        {"state": "pending", "total_count": 0, "statuses": []},
    ) is CheckState.PASSING


@pytest.mark.parametrize(
    ("check_runs", "commit_status", "expected_state", "expected_reason"),
    [
        (
            {"check_runs": [{"name": "verify", "status": "in_progress", "conclusion": None}]},
            {"state": "success", "statuses": [{"state": "success"}]},
            CheckState.PENDING,
            "Observed 1 pending check run.",
        ),
        (
            {"check_runs": [{"name": "verify", "status": "completed", "conclusion": "success"}]},
            {"state": "pending", "statuses": [{"state": "pending"}]},
            CheckState.PENDING,
            "Observed 1 concrete pending legacy status.",
        ),
        (
            {"check_runs": [{"name": "verify", "status": "completed", "conclusion": "failure"}]},
            {"state": "pending", "statuses": [{"state": "pending"}]},
            CheckState.FAILING,
            "Observed 1 failing check run.",
        ),
    ],
)
def test_check_observation_prioritizes_failure_then_real_pending(
    check_runs: dict, commit_status: dict, expected_state: CheckState, expected_reason: str
) -> None:
    observation = GitHubClient._check_observation(check_runs, commit_status)

    assert observation.state is expected_state
    assert observation.reason == expected_reason


def test_check_observation_is_unavailable_without_real_observations() -> None:
    observation = GitHubClient._check_observation(
        {"check_runs": []}, {"state": "pending", "total_count": 0, "statuses": []}
    )

    assert observation.state is CheckState.UNAVAILABLE
    assert observation.reason == "No check runs or concrete legacy statuses were observed."


def test_neutral_and_skipped_checks_are_observed_without_proving_passing() -> None:
    observation = GitHubClient._check_observation(
        {
            "check_runs": [
                {"name": "lint", "status": "completed", "conclusion": "neutral"},
                {"name": "integration", "status": "completed", "conclusion": "skipped"},
            ]
        },
        {"state": "pending", "total_count": 0, "statuses": []},
    )

    assert observation.state is CheckState.UNAVAILABLE
    assert observation.neutral_check_runs == 1
    assert observation.skipped_check_runs == 1
    assert observation.skipped_check_names == ["integration"]


def test_skipped_check_names_are_bounded_and_unique() -> None:
    observation = GitHubClient._check_observation(
        {
            "check_runs": [
                {"name": "integration", "status": "completed", "conclusion": "skipped"},
                {"name": "integration", "status": "completed", "conclusion": "skipped"},
            ]
        },
        {"statuses": []},
    )

    assert observation.skipped_check_runs == 2
    assert observation.skipped_check_names == ["integration"]


@pytest.mark.parametrize("conclusion", ["neutral", "skipped"])
def test_neutral_or_skipped_checks_do_not_prove_observed_ci_passing(
    conclusion: str,
) -> None:
    state = GitHubClient._check_state(
        {"check_runs": [{"status": "completed", "conclusion": conclusion}]},
        {"state": None},
    )

    assert state is CheckState.UNAVAILABLE


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
