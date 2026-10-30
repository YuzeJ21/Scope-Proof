"""Explicit non-public observations differ from an unavailable GitHub response."""

import httpx
import pytest

from scopeproof_core.github.client import GitHubClient, PrivateOrInaccessibleRepository


@pytest.mark.parametrize(
    "metadata",
    [
        {"private": True, "visibility": "public"},
        {"private": False, "visibility": "private"},
        {"private": False, "visibility": "internal"},
    ],
)
def test_explicit_repository_metadata_preserves_observed_non_public_fact(metadata):
    pr_data = {"base": {"repo": {"full_name": "constructed/repository", **metadata}}}
    with pytest.raises(PrivateOrInaccessibleRepository) as caught:
        GitHubClient._verified_repository_visibility(
            pr_data, expected_repository="constructed/repository"
        )
    assert getattr(caught.value, "observed_non_public", False) is True


@pytest.mark.parametrize("status", [401, 403])
def test_inaccessible_http_response_does_not_invent_repository_visibility(status):
    response = httpx.Response(
        status,
        headers={"x-ratelimit-remaining": "10"},
        request=httpx.Request("GET", "https://api.github.com/repos/constructed/repository/pulls/1"),
    )
    with pytest.raises(PrivateOrInaccessibleRepository) as caught:
        GitHubClient._raise_for_pr(response)
    assert getattr(caught.value, "observed_non_public", False) is False


def test_generic_inaccessible_error_contains_no_observed_non_public_fact():
    error = PrivateOrInaccessibleRepository("Constructed unavailable repository response")
    assert getattr(error, "observed_non_public", False) is False


@pytest.mark.parametrize("args", [(), ("Constructed unavailable",), ("Constructed code", 403)])
def test_visibility_error_preserves_existing_exception_arguments(args):
    error = PrivateOrInaccessibleRepository(*args)
    assert error.args == args
    assert error.observed_non_public is False
