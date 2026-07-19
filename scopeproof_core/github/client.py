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
    CIObservation,
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


def _reported_total_note(payload: dict, label: str, valid_entry_count: int) -> str | None:
    """Return a fail-closed diagnostic when a supplied GitHub total is not exact."""
    if "total_count" not in payload:
        return None
    reported_total = payload["total_count"]
    if (
        not isinstance(reported_total, int)
        or isinstance(reported_total, bool)
        or reported_total < 0
    ):
        return f"GitHub reported an invalid {label} total count"
    if reported_total != valid_entry_count:
        return (
            f"GitHub reported {reported_total} {label} but "
            f"{valid_entry_count} valid entries were retrieved"
        )
    return None


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
    def _check_observation(
        check_runs: dict,
        commit_status: dict,
        *,
        check_runs_available: bool = True,
        legacy_status_available: bool = True,
    ) -> CIObservation:
        """Aggregate concrete GitHub workflow observations conservatively.

        The combined-status endpoint can report ``pending`` with zero statuses.
        Only its concrete ``statuses`` entries are therefore allowed to affect
        the aggregate.  Observed CI remains metadata, never runtime proof.
        """
        raw_runs = check_runs.get("check_runs", [])
        runs = raw_runs if isinstance(raw_runs, list) else []
        dictionary_runs = [run for run in runs if isinstance(run, dict)]
        counts = {
            "successful_check_runs": 0,
            "pending_check_runs": 0,
            "failing_check_runs": 0,
            "neutral_check_runs": 0,
            "skipped_check_runs": 0,
        }
        skipped_names: list[str] = []
        malformed_check_run = len(dictionary_runs) != len(runs)
        for run in dictionary_runs:
            conclusion = run.get("conclusion")
            status = run.get("status")
            normalized_status = (
                status.strip().casefold()
                if isinstance(status, str) and status.strip()
                else None
            )
            normalized_conclusion = (
                conclusion.strip().casefold()
                if isinstance(conclusion, str) and conclusion.strip()
                else None
            )
            structurally_valid = normalized_status is not None and (
                normalized_status != "completed" or normalized_conclusion is not None
            )
            if not structurally_valid:
                malformed_check_run = True

            if normalized_conclusion in _FAILING_CONCLUSIONS:
                counts["failing_check_runs"] += 1
            elif normalized_status is None:
                continue
            elif normalized_status != "completed":
                counts["pending_check_runs"] += 1
            elif normalized_conclusion is None:
                continue
            elif normalized_conclusion in _PASSING_CONCLUSIONS:
                counts["successful_check_runs"] += 1
            elif normalized_conclusion == "skipped":
                counts["skipped_check_runs"] += 1
                name = run.get("name")
                if (
                    isinstance(name, str)
                    and name.strip()
                    and name.strip() not in skipped_names
                    and len(skipped_names) < 8
                ):
                    skipped_names.append(name.strip())
            else:
                counts["neutral_check_runs"] += 1

        raw_legacy_statuses = commit_status.get("statuses", [])
        dictionary_legacy_statuses = (
            [status for status in raw_legacy_statuses if isinstance(status, dict)]
            if isinstance(raw_legacy_statuses, list)
            else []
        )
        legacy_counts = {
            "successful_legacy_statuses": 0,
            "pending_legacy_statuses": 0,
            "failing_legacy_statuses": 0,
            "neutral_legacy_statuses": 0,
        }
        malformed_legacy_status = len(dictionary_legacy_statuses) != len(
            raw_legacy_statuses if isinstance(raw_legacy_statuses, list) else []
        )
        for legacy_status in dictionary_legacy_statuses:
            raw_state = legacy_status.get("state")
            state_value = (
                raw_state.strip().casefold()
                if isinstance(raw_state, str) and raw_state.strip()
                else None
            )
            if state_value is None:
                malformed_legacy_status = True
                continue
            if state_value == "success":
                legacy_counts["successful_legacy_statuses"] += 1
            elif state_value == "pending":
                legacy_counts["pending_legacy_statuses"] += 1
            elif state_value in {"failure", "error"}:
                legacy_counts["failing_legacy_statuses"] += 1
            else:
                legacy_counts["neutral_legacy_statuses"] += 1
        concrete_legacy_status_count = sum(legacy_counts.values())
        incomplete_collections: list[str] = []
        if not check_runs_available:
            incomplete_collections.append("GitHub check-runs endpoint was unavailable")
        if not legacy_status_available:
            incomplete_collections.append("GitHub legacy status endpoint was unavailable")
        if not isinstance(raw_runs, list) or malformed_check_run:
            incomplete_collections.append("GitHub check-runs response contained malformed entries")
        if not isinstance(raw_legacy_statuses, list) or malformed_legacy_status:
            incomplete_collections.append(
                "GitHub legacy status response contained malformed entries"
            )
        categorized_check_run_count = sum(counts.values())
        check_run_total_note = _reported_total_note(
            check_runs, "check runs", categorized_check_run_count
        )
        if check_run_total_note:
            incomplete_collections.append(check_run_total_note)
        legacy_status_total_note = _reported_total_note(
            commit_status, "legacy statuses", concrete_legacy_status_count
        )
        if legacy_status_total_note:
            incomplete_collections.append(legacy_status_total_note)

        if counts["failing_check_runs"]:
            state = CheckState.FAILING
            reason = (
                f"Observed {counts['failing_check_runs']} failing check run"
                f"{'s' if counts['failing_check_runs'] != 1 else ''}."
            )
        elif legacy_counts["failing_legacy_statuses"]:
            state = CheckState.FAILING
            reason = (
                "Observed "
                f"{legacy_counts['failing_legacy_statuses']} concrete failing legacy status"
                f"{'es' if legacy_counts['failing_legacy_statuses'] != 1 else ''}."
            )
        elif counts["pending_check_runs"]:
            state = CheckState.PENDING
            reason = (
                f"Observed {counts['pending_check_runs']} pending check run"
                f"{'s' if counts['pending_check_runs'] != 1 else ''}."
            )
        elif legacy_counts["pending_legacy_statuses"]:
            state = CheckState.PENDING
            reason = (
                "Observed "
                f"{legacy_counts['pending_legacy_statuses']} concrete pending legacy status"
                f"{'es' if legacy_counts['pending_legacy_statuses'] != 1 else ''}."
            )
        elif counts["successful_check_runs"]:
            state = CheckState.PASSING
            suffix = (
                "; no concrete legacy statuses."
                if not concrete_legacy_status_count
                else "."
            )
            reason = (
                f"Observed {counts['successful_check_runs']} successful completed check run"
                f"{'s' if counts['successful_check_runs'] != 1 else ''}{suffix}"
            )
        elif legacy_counts["successful_legacy_statuses"]:
            state = CheckState.PASSING
            reason = (
                "Observed "
                f"{legacy_counts['successful_legacy_statuses']} concrete successful legacy status"
                f"{'es' if legacy_counts['successful_legacy_statuses'] != 1 else ''}."
            )
        elif not categorized_check_run_count and not concrete_legacy_status_count:
            state = CheckState.UNAVAILABLE
            reason = "No check runs or concrete legacy statuses were observed."
        else:
            state = CheckState.UNAVAILABLE
            reason = "Observed neutral or skipped checks; neither proves passing."

        collection_complete = not incomplete_collections
        if incomplete_collections:
            incomplete_reason = "CI observation collection is incomplete: " + "; ".join(
                incomplete_collections
            ) + "."
            if state is CheckState.PASSING:
                state = CheckState.UNAVAILABLE
                reason = f"{incomplete_reason} Passing cannot be concluded."
            else:
                reason = f"{reason} {incomplete_reason}"

        return CIObservation(
            state=state,
            reason=reason,
            total_check_runs=categorized_check_run_count,
            concrete_legacy_status_count=concrete_legacy_status_count,
            skipped_check_names=skipped_names,
            collection_complete=collection_complete,
            collection_notes=incomplete_collections,
            **counts,
            **legacy_counts,
        )

    @staticmethod
    def _check_state(check_runs: dict, commit_status: dict) -> CheckState:
        """Compatibility wrapper for callers that only need the aggregate state."""
        return GitHubClient._check_observation(check_runs, commit_status).state

    def fetch_pull_request(self, url: str) -> PullRequestSnapshot:
        owner, repository, pr_number = parse_pr_url(url)
        root = f"/repos/{owner}/{repository}"
        pr_response = self._get(f"{root}/pulls/{pr_number}")
        self._raise_for_pr(pr_response)
        pr_data = pr_response.json()

        raw_files = self._get_all(f"{root}/pulls/{pr_number}/files?per_page=100")
        raw_commits = self._get_all(f"{root}/pulls/{pr_number}/commits?per_page=100")

        head_sha = pr_data["head"]["sha"]
        check_response = self._get(f"{root}/commits/{head_sha}/check-runs?per_page=100")
        status_response = self._get(f"{root}/commits/{head_sha}/status?per_page=100")
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
        ci_observation = self._check_observation(
            check_data,
            status_data,
            check_runs_available=check_response.is_success,
            legacy_status_available=status_response.is_success,
        )
        return PullRequestSnapshot(
            repository=f"{owner}/{repository}",
            pr_number=pr_number,
            title=pr_data.get("title", ""),
            description=pr_data.get("body") or "",
            html_url=pr_data.get("html_url", url),
            base_sha=pr_data["base"]["sha"],
            head_sha=head_sha,
            check_state=ci_observation.state,
            ci_observation=ci_observation,
            ingestion_state=ingestion_state,
            fetched_at=datetime.now(UTC),
            files=files,
            commits=commits,
            warnings=warnings,
            skipped_files=skipped_files,
        )
