"""Read-only public GitHub REST client with an explicit error taxonomy."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import parse_qsl, quote, urlparse

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
    RepositoryVisibility,
    RetrievedFile,
)

_PR_PATH = re.compile(r"^/([^/]+)/([^/]+)/pull/(\d+)/?$")
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_FAILING_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}
_PASSING_CONCLUSIONS = {"success"}
_NEXT_RELATION = re.compile(
    r'\brel\s*=\s*(?:"next"|next)(?=\s*(?:;|,|$))',
    flags=re.IGNORECASE,
)


class GitHubIngestionError(RuntimeError):
    """Base error for user-safe GitHub ingestion failures."""


class InvalidPullRequestUrl(GitHubIngestionError):
    pass


class PullRequestNotFound(GitHubIngestionError):
    pass


class PrivateOrInaccessibleRepository(GitHubIngestionError):
    pass


class RepositoryVisibilityUnverified(GitHubIngestionError):
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


class GitHubPaginationError(GitHubIngestionError):
    """A pagination target or traversal exceeded the supported trust boundary."""


@dataclass
class _FetchBudget:
    max_requests: int
    max_pages: int
    max_items: int
    max_response_bytes: int
    max_total_response_bytes: int
    requests_used: int = 0
    pages_used: int = 0
    items_used: int = 0
    total_response_bytes: int = 0

    def charge_request(self) -> None:
        if self.requests_used >= self.max_requests:
            raise GitHubPaginationError("GitHub request budget was exhausted.")
        self.requests_used += 1

    def charge_page(self) -> None:
        if self.pages_used >= self.max_pages:
            raise GitHubPaginationError("GitHub pagination page budget was exhausted.")
        self.pages_used += 1

    def charge_items(self, count: int) -> None:
        if self.items_used + count > self.max_items:
            raise GitHubPaginationError("GitHub pagination item budget was exhausted.")
        self.items_used += count

    def charge_response(self, response: httpx.Response) -> None:
        decoded_bytes = len(response.content)
        if decoded_bytes > self.max_response_bytes:
            raise GitHubPaginationError(
                "GitHub decoded response byte budget was exhausted."
            )
        if self.total_response_bytes + decoded_bytes > self.max_total_response_bytes:
            raise GitHubPaginationError(
                "GitHub total decoded response byte budget was exhausted."
            )
        self.total_response_bytes += decoded_bytes


@dataclass(frozen=True)
class _PaginatedResult:
    items: list[dict]
    truncated: bool = False


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
        max_commits: int = 250,
        max_candidate_files: int = 8,
        max_candidate_bytes: int = 200_000,
        max_requests: int = 16,
        max_pagination_pages: int = 10,
        max_pagination_items: int = 1_000,
        max_response_bytes: int = 4 * 1024 * 1024,
        max_total_response_bytes: int = 16 * 1024 * 1024,
        timeout_seconds: float = 15.0,
    ) -> None:
        configured_limits = {
            "max_files": max_files,
            "max_commits": max_commits,
            "max_requests": max_requests,
            "max_pagination_pages": max_pagination_pages,
            "max_pagination_items": max_pagination_items,
            "max_response_bytes": max_response_bytes,
            "max_total_response_bytes": max_total_response_bytes,
        }
        invalid_limits = [name for name, value in configured_limits.items() if value <= 0]
        if invalid_limits:
            names = ", ".join(invalid_limits)
            raise ValueError(f"GitHub ingestion limits must be positive: {names}")
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
        self.max_commits = max_commits
        self.max_patch_bytes = max_patch_bytes
        self.max_total_diff_bytes = max_total_diff_bytes
        self.max_candidate_files = max_candidate_files
        self.max_candidate_bytes = max_candidate_bytes
        self.max_requests = max_requests
        self.max_pagination_pages = max_pagination_pages
        self.max_pagination_items = max_pagination_items
        self.max_response_bytes = max_response_bytes
        self.max_total_response_bytes = max_total_response_bytes
        self.last_request_authorized = "Authorization" in headers

    def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        budget: _FetchBudget | None = None,
    ) -> httpx.Response:
        if budget is not None:
            budget.charge_request()
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as error:
            message = "Could not reach GitHub. Retry without losing criteria."
            raise GitHubNetworkError(message) from error
        if budget is not None:
            budget.charge_response(response)
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

    @staticmethod
    def _verified_repository_visibility(
        pr_data: object,
        *,
        expected_repository: str,
    ) -> RepositoryVisibility:
        """Return verified-public only for complete, consistent GitHub metadata."""

        base = pr_data.get("base") if isinstance(pr_data, dict) else None
        repository = base.get("repo") if isinstance(base, dict) else None
        if not isinstance(repository, dict):
            raise RepositoryVisibilityUnverified(
                "GitHub did not provide enough metadata to verify public repository visibility."
            )

        full_name = repository.get("full_name")
        private = repository.get("private")
        visibility = repository.get("visibility")
        if private is True or (
            isinstance(visibility, str) and visibility in {"private", "internal"}
        ):
            raise PrivateOrInaccessibleRepository(
                "ScopeProof accepts only a verified public GitHub repository."
            )
        if (
            not isinstance(full_name, str)
            or full_name.casefold() != expected_repository.casefold()
            or private is not False
            or visibility != "public"
        ):
            raise RepositoryVisibilityUnverified(
                "GitHub did not provide enough metadata to verify public repository visibility."
            )
        return RepositoryVisibility.VERIFIED_PUBLIC

    @staticmethod
    def _next_link(response: httpx.Response) -> str | None:
        raw_link = ", ".join(response.headers.get_list("link"))
        if not raw_link:
            return None
        next_relation_count = len(_NEXT_RELATION.findall(raw_link))
        if next_relation_count > 1:
            raise GitHubPaginationError(
                "GitHub pagination response contained ambiguous next links."
            )
        try:
            parsed_links = response.links
            next_link = parsed_links.get("next", {}).get("url")
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubPaginationError(
                "GitHub pagination response contained a malformed Link header."
            ) from error
        if next_relation_count == 0 and next_link is None:
            if not parsed_links or any(
                not isinstance(link.get("rel"), str)
                or not link["rel"]
                or not isinstance(link.get("url"), str)
                or not link["url"]
                for link in parsed_links.values()
            ):
                raise GitHubPaginationError(
                    "GitHub pagination response contained a malformed Link header."
                )
            return None
        if next_relation_count != 1 or not isinstance(next_link, str) or not next_link:
            raise GitHubPaginationError(
                "GitHub pagination response contained a malformed next link."
            )
        return next_link

    @staticmethod
    def _validated_pagination_target(
        target: str,
        *,
        expected_path: str,
        per_page: int,
    ) -> tuple[str, str]:
        try:
            parsed_target = urlparse(target)
            target_port = parsed_target.port
            query_items = parse_qsl(
                parsed_target.query,
                keep_blank_values=True,
                strict_parsing=True,
            )
        except ValueError as error:
            raise GitHubPaginationError(
                "GitHub pagination target is malformed."
            ) from error
        if (
            parsed_target.scheme != "https"
            or parsed_target.hostname != "api.github.com"
            or parsed_target.username is not None
            or parsed_target.password is not None
            or parsed_target.fragment
            or target_port not in {None, 443}
        ):
            raise GitHubPaginationError(
                "GitHub pagination target is outside the expected GitHub API origin."
            )
        if parsed_target.path != expected_path:
            raise GitHubPaginationError(
                "GitHub pagination target escaped the expected repository endpoint."
            )
        if len(query_items) != 2 or {name for name, _ in query_items} != {
            "page",
            "per_page",
        }:
            raise GitHubPaginationError(
                "GitHub pagination target query is malformed or ambiguous."
            )
        query = dict(query_items)
        page_text = query.get("page", "")
        per_page_text = query.get("per_page", "")
        if not re.fullmatch(r"[1-9][0-9]*", page_text) or not re.fullmatch(
            r"[1-9][0-9]*", per_page_text
        ):
            raise GitHubPaginationError(
                "GitHub pagination target query is malformed or ambiguous."
            )
        try:
            page = int(page_text)
            target_per_page = int(per_page_text)
        except (KeyError, ValueError) as error:
            raise GitHubPaginationError(
                "GitHub pagination target query is malformed or ambiguous."
            ) from error
        if page < 1 or target_per_page != per_page:
            raise GitHubPaginationError(
                "GitHub pagination target query is malformed or ambiguous."
            )
        canonical_target = f"{expected_path}?page={page}&per_page={per_page}"
        return canonical_target, canonical_target

    def _get_paginated(
        self,
        path: str,
        *,
        expected_path: str,
        per_page: int,
        retain_limit: int,
        budget: _FetchBudget,
    ) -> _PaginatedResult:
        """Return one ordered, lineage-bound collection with bounded overflow."""
        canonical_initial = f"{expected_path}?page=1&per_page={per_page}"
        visited = {canonical_initial}
        response = self._get(
            path,
            params={"per_page": str(per_page)},
            budget=budget,
        )
        items: list[dict] = []
        while True:
            self._raise_for_pr(response)
            budget.charge_page()
            try:
                page_items = response.json()
            except ValueError as error:
                raise GitHubPaginationError(
                    "GitHub pagination response was not valid JSON."
                ) from error
            if not isinstance(page_items, list) or any(
                not isinstance(item, dict) for item in page_items
            ):
                raise GitHubPaginationError(
                    "GitHub pagination expected a list response of objects."
                )
            budget.charge_items(len(page_items))
            remaining = retain_limit + 1 - len(items)
            if remaining > 0:
                items.extend(page_items[:remaining])
            next_link = self._next_link(response)
            canonical_target: str | None = None
            relative_target: str | None = None
            if next_link is not None:
                canonical_target, relative_target = self._validated_pagination_target(
                    next_link,
                    expected_path=expected_path,
                    per_page=per_page,
                )
                if canonical_target in visited:
                    raise GitHubPaginationError(
                        "GitHub pagination did not advance; a cycle or repeated target "
                        "was rejected."
                    )
            if len(items) > retain_limit:
                return _PaginatedResult(items=items, truncated=True)
            if next_link is None:
                return _PaginatedResult(items=items)
            if len(items) == retain_limit:
                return _PaginatedResult(items=items, truncated=True)
            assert canonical_target is not None
            assert relative_target is not None
            visited.add(canonical_target)
            response = self._get(relative_target, budget=budget)

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
        if not paths:
            return []
        if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
            raise ValueError("head SHA must be a 40-character lowercase commit SHA")
        total_bytes = 0
        candidates: list[RetrievedFile] = []
        for path in paths:
            path = self._validate_candidate_path(path)
            encoded_path = quote(path, safe="/")
            response = self._get(
                f"/repos/{repository}/contents/{encoded_path}",
                params={"ref": head_sha},
            )
            self._raise_for_pr(response)
            expected_path = f"/repos/{repository}/contents/{encoded_path}".encode()
            request_path = response.request.url.raw_path.split(b"?", maxsplit=1)[0]
            request_params = response.request.url.params.multi_items()
            if request_path != expected_path or request_params != [("ref", head_sha)]:
                raise GitHubIngestionError(
                    f"Candidate {path} response is not anchored to the requested path and SHA."
                )
            try:
                payload = response.json()
                encoded_content = payload.get("content") if isinstance(payload, dict) else None
                if (
                    not isinstance(payload, dict)
                    or payload.get("type") != "file"
                    or payload.get("encoding") != "base64"
                    or not isinstance(encoded_content, str)
                ):
                    raise ValueError("unexpected GitHub contents payload")
                compact_content = "".join(encoded_content.split())
                content = base64.b64decode(compact_content, validate=True).decode("utf-8")
            except (TypeError, UnicodeDecodeError, ValueError) as error:
                raise GitHubIngestionError(
                    f"Candidate {path} is not a readable UTF-8 text file."
                ) from error
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
        budget = _FetchBudget(
            max_requests=self.max_requests,
            max_pages=self.max_pagination_pages,
            max_items=self.max_pagination_items,
            max_response_bytes=self.max_response_bytes,
            max_total_response_bytes=self.max_total_response_bytes,
        )
        pr_response = self._get(f"{root}/pulls/{pr_number}", budget=budget)
        self._raise_for_pr(pr_response)
        pr_data = pr_response.json()
        repository_visibility = self._verified_repository_visibility(
            pr_data,
            expected_repository=f"{owner}/{repository}",
        )

        files_path = f"{root}/pulls/{pr_number}/files"
        file_result = self._get_paginated(
            files_path,
            expected_path=files_path,
            per_page=min(100, self.max_files + 1),
            retain_limit=self.max_files,
            budget=budget,
        )
        for item in file_result.items:
            filename = item.get("filename")
            if not isinstance(filename, str) or not filename:
                raise GitHubIngestionError("GitHub returned malformed file metadata.")
        raw_files = file_result.items[: self.max_files]
        observed_file_overflow = file_result.items[self.max_files :]

        commits_path = f"{root}/pulls/{pr_number}/commits"
        commit_result = self._get_paginated(
            commits_path,
            expected_path=commits_path,
            per_page=min(100, self.max_commits + 1),
            retain_limit=self.max_commits,
            budget=budget,
        )
        all_commits: list[CommitInfo] = []
        for item in commit_result.items:
            sha = item.get("sha")
            commit = item.get("commit")
            message = commit.get("message") if isinstance(commit, dict) else None
            html_url = item.get("html_url")
            if (
                not isinstance(sha, str)
                or not sha
                or not isinstance(message, str)
                or not isinstance(html_url, str)
            ):
                raise GitHubIngestionError("GitHub returned malformed commit metadata.")
            all_commits.append(CommitInfo(sha=sha, message=message, html_url=html_url))

        head_sha = pr_data["head"]["sha"]
        check_response = self._get(
            f"{root}/commits/{head_sha}/check-runs",
            params={"per_page": "100"},
            budget=budget,
        )
        status_response = self._get(
            f"{root}/commits/{head_sha}/status",
            params={"per_page": "100"},
            budget=budget,
        )
        check_data = check_response.json() if check_response.is_success else {}
        status_data = status_response.json() if status_response.is_success else {}

        warnings: list[str] = []
        skipped_files: list[str] = []
        ingestion_state = IngestionState.COMPLETE
        if file_result.truncated:
            for item in observed_file_overflow:
                filename = item.get("filename")
                if isinstance(filename, str) and filename:
                    skipped_files.append(filename)
            warnings.append(
                "File limit reached; additional changed files were not retrieved."
            )
            ingestion_state = IngestionState.PARTIAL
        if commit_result.truncated:
            warnings.append(
                "Commit history limit reached; additional commits were not retrieved."
            )
            ingestion_state = IngestionState.PARTIAL

        total_bytes = 0
        diff_limit_skipped_count = 0
        files: list[ChangedFile] = []
        for item in raw_files:
            filename = item["filename"]
            raw_patch = item.get("patch")
            if raw_patch is None or raw_patch == "":
                if filename not in skipped_files:
                    skipped_files.append(filename)
                warning = (
                    f"Patch unavailable for {filename}; file excluded from analysis."
                )
                if warning not in warnings:
                    warnings.append(warning)
                ingestion_state = IngestionState.PARTIAL
                continue
            if not isinstance(raw_patch, str):
                raise GitHubIngestionError("GitHub returned malformed patch data.")
            patch = raw_patch
            patch_bytes = len(patch.encode("utf-8"))
            truncated = patch_bytes > self.max_patch_bytes
            if total_bytes + patch_bytes > self.max_total_diff_bytes:
                if filename not in skipped_files:
                    skipped_files.append(filename)
                diff_limit_skipped_count += 1
                ingestion_state = IngestionState.PARTIAL
                continue
            if truncated:
                encoded_patch = patch.encode("utf-8")[: self.max_patch_bytes]
                patch = encoded_patch.decode("utf-8", errors="ignore")
                warnings.append(f"Patch truncated for {filename}.")
                ingestion_state = IngestionState.PARTIAL
            total_bytes += len(patch.encode("utf-8"))
            files.append(
                ChangedFile(
                    path=filename,
                    status=item.get("status", "modified"),
                    additions=item.get("additions", 0),
                    deletions=item.get("deletions", 0),
                    changes=item.get("changes", 0),
                    patch=patch,
                    lines=_parse_patch(patch),
                    truncated=truncated,
                )
            )
        if diff_limit_skipped_count:
            warnings.append(
                "Total diff limit reached; skipped "
                f"{diff_limit_skipped_count} changed files."
            )

        commits = all_commits[: self.max_commits]
        ci_observation = self._check_observation(
            check_data,
            status_data,
            check_runs_available=check_response.is_success,
            legacy_status_available=status_response.is_success,
        )
        return PullRequestSnapshot(
            repository=f"{owner}/{repository}",
            repository_visibility=repository_visibility,
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
