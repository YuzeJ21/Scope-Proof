import os

import pytest

from scopeproof_core.github.client import GitHubClient


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_GITHUB_TESTS") != "1",
    reason="Set RUN_LIVE_GITHUB_TESTS=1 to call public GitHub",
)
def test_live_public_pull_request_ingestion() -> None:
    snapshot = GitHubClient(max_files=20).fetch_pull_request(
        "https://github.com/octocat/Hello-World/pull/1"
    )
    assert snapshot.repository == "octocat/Hello-World"
    assert snapshot.pr_number == 1
    assert snapshot.head_sha
    assert snapshot.files
