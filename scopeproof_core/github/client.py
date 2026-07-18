"""Read-only public GitHub REST client with an explicit error taxonomy."""

from __future__ import annotations

import base64
import re
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx

from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    CommitInfo,
    IngestionState,
    LineChangeType,
    PullRequestSnapshot,
    RetrievedFile,
)

_PR_PATH = re.compile(r"^/([^/]+)/([^/]+)/pull/(\d+)/?$")
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_FAILING_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}
_PASSING_CONCLUSIONS = {"success"}


class GitHubIngestionError(RuntimeError):
    """Base error for user-safe GitHub ingestion failures."""


class InvalidPullRequestUrl(GitHubIngestionError):
    pass


class PullRequestNotFound(GitHubIngestionError):
    pass


class PrivateOrInaccessibleRepository(GitHubIngestionError):
    pass


class GitHubRateLimited(GitHubIngestionError):
    def __init__(self, reset_at: str | None = None) -> None:
        self.reset_at = reset_at
        suffix = f" Reset timestamp: {reset_at}." if reset_at else ""
        super().__init__(f"GitHub rate limit reached.{suffix}")


class GitHubNetworkError(GitHubIngestionError):
    pass


class DiffLimitExceeded(GitHubIngestionError):
    pass


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Return owner, repository, and PR number for a canonical GitHub PR URL."""
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise InvalidPullRequestUrl("Expected https://github.com/OWNER/REPO/pull/NUMBER")
    match = _PR_PATH.fullmatch(parsed.path)
    if not match:
        raise InvalidPullRequestUrl("Expected https://github.com/OWNER/REPO/pull/NUMBER")
    owner, repository, number = match.groups()
    return owner, repository, int(number)


def _parse_patch(patch: str) -> list[ChangedLine]:
    lines: list[ChangedLine] = []
    old_line = 0
    new_line = 0
    for raw in patch.splitlines():
        header = _HUNK_HEADER.match(raw)
        if header:
            old_line, new_line = (int(value) for value in header.groups())
            continue
        if raw.startswith("\\ No newline"):
            continue
        if raw.startswith("-"):
            lines.append(
                ChangedLine(
                    change_type=LineChangeType.REMOVED,
                    line_number=old_line,
                    content=raw[1:],
                )
            )
            old_line += 1
        elif raw.startswith("+"):
            lines.append(
                ChangedLine(
                    change_type=LineChangeType.ADDED,
                    line_number=new_line,
                    content=raw[1:],
                )
            )
            new_line += 1
        elif raw.startswith(" "):
            lines.append(
                ChangedLine(
                    change_type=LineChangeType.CONTEXT,
                    line_number=new_line,
                    content=raw[1:],
                )
            )
            old_line += 1
            new_line += 1
    return lines


class GitHubClient:
    """Fetch public PR context without persisting credentials or repository code."""

    def __init__(
        self,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
        *,
        max_files: int = 100,
        max_patch_bytes: int = 200_000,
        max_total_diff_bytes: int = 1_000_000,
        max_candidate_files: int = 8,
        max_candidate_bytes: int = 200_000,
        timeout_seconds: float = 15.0,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ScopeProof/0.1",
        }
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            transport=transport,
            timeout=timeout_seconds,
        )
        self.max_files = max_files
        self.max_patch_bytes = max_patch_bytes
        self.max_total_diff_bytes = max_total_diff_bytes
        self.max_candidate_files = max_candidate_files
        self.max_candidate_bytes = max_candidate_bytes
        self.last_request_authorized = "Authorization" in headers

    def _get(self, path: str) -> httpx.Response:
        try:
            response = self._client.get(path)
        except httpx.HTTPError as error:
            message = "Could not reach GitHub. Retry without losing criteria."
            raise GitHubNetworkError(message) from error
        return response

    @staticmethod
    def _raise_for_pr(response: httpx.Response) -> None:
        if response.status_code == 404:
            raise PullRequestNotFound("The public pull request was not found.")
        if response.status_code in {401, 403}:
            if response.headers.get("x-ratelimit-remaining") == "0":
                raise GitHubRateLimited(response.headers.get("x-ratelimit-reset"))
            raise PrivateOrInaccessibleRepository(
                "The repository is private, inaccessible, or does not allow anonymous access."
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise GitHubIngestionError(f"GitHub returned HTTP {response.status_code}.") from error

    def _get_all(self, path: str) -> list[dict]:
        """Follow GitHub pagination while retaining normal HTTP error handling."""
        response = self._get(path)
        self._raise_for_pr(response)
        items = list(response.json())
        while next_link := response.links.get("next", {}).get("url"):
            response = self._get(next_link)
            self._raise_for_pr(response)
            items.extend(response.json())
        return items

    @staticmethod
    def _validate_candidate_path(path: str) -> str:
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts or path != candidate.as_posix():
            raise ValueError("candidate paths must be repository-relative paths")
        return path

    def fetch_candidate_files(
        self, repository: str, head_sha: str, paths: list[str]
    ) -> list[RetrievedFile]:
        """Read a small justified set of unchanged files without scanning the repository."""
        if not re.fullmatch(r"[^/]+/[^/]+", repository):
            raise ValueError("repository must be owner/name")
        if len(paths) > self.max_candidate_files:
            raise DiffLimitExceeded("Candidate file count exceeds the configured safety limit.")
        total_bytes = 0
        candidates: list[RetrievedFile] = []
        for path in paths:
            path = self._validate_candidate_path(path)
            response = self._get(f"/repos/{repository}/contents/{path}?ref={head_sha}")
            self._raise_for_pr(response)
            payload = response.json()
            if payload.get("type") != "file" or payload.get("encoding") != "base64":
                raise GitHubIngestionError(f"Candidate {path} is not a readable text file.")
            try:
                content = base64.b64decode(payload.get("content", "")).decode("utf-8")
            except (UnicodeDecodeError, ValueError) as error:
                raise GitHubIngestionError(f"Candidate {path} is not UTF-8 text.") from error
            total_bytes += len(content.encode("utf-8"))
            if total_bytes > self.max_candidate_bytes:
                raise DiffLimitExceeded("Candidate file bytes exceed the configured safety limit.")
            candidates.append(
                RetrievedFile(
                    path=path,
                    content=content,
                    commit_sha=head_sha,
                    retrieval_reason=f"Requested bounded unchanged candidate: {path}",
                )
            )
        return candidates

    @staticmethod
    def _check_state(check_runs: dict, commit_status: dict) -> CheckState:
        runs = check_runs.get("check_runs", [])
        conclusions = {run.get("conclusion") for run in runs if run.get("conclusion")}
        statuses = {run.get("status") for run in runs}
        legacy_state = commit_status.get("state")
        if conclusions & _FAILING_CONCLUSIONS or legacy_state in {"failure", "error"}:
            return CheckState.FAILING
        if "in_progress" in statuses or "queued" in statuses or legacy_state == "pending":
            return CheckState.PENDING
        if conclusions & _PASSING_CONCLUSIONS or legacy_state == "success":
            return CheckState.PASSING
        return CheckState.UNAVAILABLE

    def fetch_pull_request(self, url: str) -> PullRequestSnapshot:
        owner, repository, pr_number = parse_pr_url(url)
        root = f"/repos/{owner}/{repository}"
        pr_response = self._get(f"{root}/pulls/{pr_number}")
        self._raise_for_pr(pr_response)
        pr_data = pr_response.json()

        raw_files = self._get_all(f"{root}/pulls/{pr_number}/files?per_page=100")
        raw_commits = self._get_all(f"{root}/pulls/{pr_number}/commits?per_page=100")

        head_sha = pr_data["head"]["sha"]
        check_response = self._get(f"{root}/commits/{head_sha}/check-runs")
        status_response = self._get(f"{root}/commits/{head_sha}/status")
        check_data = check_response.json() if check_response.is_success else {}
        status_data = status_response.json() if status_response.is_success else {}

        warnings: list[str] = []
        skipped_files: list[str] = []
        ingestion_state = IngestionState.COMPLETE
        if len(raw_files) > self.max_files:
            skipped_files.extend(item["filename"] for item in raw_files[self.max_files :])
            raw_files = raw_files[: self.max_files]
            warnings.append(f"File limit reached; skipped {len(skipped_files)} changed files.")
            ingestion_state = IngestionState.PARTIAL

        total_bytes = 0
        files: list[ChangedFile] = []
        for item in raw_files:
            patch = item.get("patch") or ""
            patch_bytes = len(patch.encode("utf-8"))
            truncated = patch_bytes > self.max_patch_bytes
            if total_bytes + patch_bytes > self.max_total_diff_bytes:
                skipped_files.append(item["filename"])
                ingestion_state = IngestionState.PARTIAL
                continue
            if truncated:
                encoded_patch = patch.encode("utf-8")[: self.max_patch_bytes]
                patch = encoded_patch.decode("utf-8", errors="ignore")
                warnings.append(f"Patch truncated for {item['filename']}.")
                ingestion_state = IngestionState.PARTIAL
            total_bytes += len(patch.encode("utf-8"))
            files.append(
                ChangedFile(
                    path=item["filename"],
                    status=item.get("status", "modified"),
                    additions=item.get("additions", 0),
                    deletions=item.get("deletions", 0),
                    changes=item.get("changes", 0),
                    patch=patch,
                    lines=_parse_patch(patch),
                    truncated=truncated,
                )
            )
        if skipped_files and not any("File limit" in warning for warning in warnings):
            skipped_count = len(skipped_files)
            warnings.append(f"Total diff limit reached; skipped {skipped_count} changed files.")

        commits = [
            CommitInfo(
                sha=item["sha"],
                message=item.get("commit", {}).get("message", ""),
                html_url=item.get("html_url", ""),
            )
            for item in raw_commits
        ]
        return PullRequestSnapshot(
            repository=f"{owner}/{repository}",
            pr_number=pr_number,
            title=pr_data.get("title", ""),
            description=pr_data.get("body") or "",
            html_url=pr_data.get("html_url", url),
            base_sha=pr_data["base"]["sha"],
            head_sha=head_sha,
            check_state=self._check_state(check_data, status_data),
            ingestion_state=ingestion_state,
            fetched_at=datetime.now(UTC),
            files=files,
            commits=commits,
            warnings=warnings,
            skipped_files=skipped_files,
        )
