"""Pydantic contracts for reviews, evidence, findings, and reports."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictInt,
    computed_field,
    field_validator,
    model_validator,
)

from scopeproof_core.version import __version__

RULESET_VERSION = "1.0.0"
GITHUB_REPOSITORY_PATTERN = r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$"
LocalReviewId = Annotated[
    str,
    Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$"),
]


class StringEnum(StrEnum):
    """A JSON-friendly enum with readable values."""


class SavedReviewListing(BaseModel):
    """Validated local identifiers returned by CLI review discovery."""

    review_ids: list[LocalReviewId]
    storage_dir: str

    @field_validator("review_ids")
    @classmethod
    def validate_sorted_unique_ids(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("saved review IDs must be sorted and unique")
        return value


class Priority(StringEnum):
    MUST_HAVE = "must_have"
    SHOULD_HAVE = "should_have"


class CriterionType(StringEnum):
    BEHAVIOR = "behavior"
    ERROR_STATE = "error_state"
    ANALYTICS = "analytics"
    PERMISSION = "permission"
    DOCUMENTATION = "documentation"
    MIGRATION = "migration"
    NON_FUNCTIONAL = "non_functional"


class CriterionSource(StringEnum):
    """Whether a criterion came from the user or an explicit local rule pack."""

    USER_CONFIRMED = "user_confirmed"
    IMPLICIT_RULE_PACK = "implicit_rule_pack"


class ReviewInputOrigin(StringEnum):
    """How the review snapshot entered ScopeProof; legacy records remain unknown."""

    LIVE_PUBLIC_GITHUB = "live_public_github"
    LOCAL_FIXTURE = "local_fixture"
    CONSTRUCTED_DEMO = "constructed_demo"
    LEGACY_UNKNOWN = "legacy_unknown"


class RepositoryVisibility(StringEnum):
    """Whether the owning repository has current verified-public provenance."""

    VERIFIED_PUBLIC = "verified_public"
    UNVERIFIED = "unverified"


def require_verified_public_origin(
    repository_visibility: RepositoryVisibility,
    input_origin: ReviewInputOrigin,
) -> None:
    """Reject current live-public labeling without verified repository provenance."""

    if (
        input_origin is ReviewInputOrigin.LIVE_PUBLIC_GITHUB
        and repository_visibility is not RepositoryVisibility.VERIFIED_PUBLIC
    ):
        raise ValueError(
            "live public GitHub review construction requires verified public "
            "repository visibility"
        )


_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_EXACT_HEAD_PATTERN = r"^[a-f0-9]{40}$"
_PATH_OR_URI_LIKE = re.compile(
    r"(?:[/\\]|(?<![A-Za-z0-9+.-])[A-Za-z][A-Za-z0-9+.-]*:)"
)
CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI = (
    "scopeproof://constructed-demo/acceptance-criteria"
)


def junit_name_is_path_or_url_like(value: str) -> bool:
    """Return whether a JUnit display name could disclose a path or URI."""

    return _PATH_OR_URI_LIKE.search(value) is not None
_CRITERIA_SOURCE_URI_ERROR = (
    "source URI must be an HTTPS URL or "
    "scopeproof://constructed-demo/acceptance-criteria"
)


def normalize_public_https_source_uri(value: str) -> str:
    """Normalize one public HTTPS source URI and reject secret-bearing/local forms."""

    normalized = value.strip()
    try:
        parsed = HttpUrl(normalized)
    except ValueError:
        raise ValueError(_CRITERIA_SOURCE_URI_ERROR) from None
    split = urlsplit(str(parsed))
    hostname = split.hostname
    normalized_hostname = hostname.rstrip(".").lower() if hostname else None
    unsafe = (
        parsed.scheme != "https"
        or split.username is not None
        or split.password is not None
        or normalized_hostname is None
        or normalized_hostname == "localhost"
        or normalized_hostname.endswith(".localhost")
        or normalized_hostname.endswith(".local")
        or bool(split.query)
        or bool(split.fragment)
    )
    if normalized_hostname is not None:
        try:
            address = ipaddress.ip_address(normalized_hostname)
        except ValueError:
            pass
        else:
            unsafe = unsafe or not address.is_global or address.is_multicast
    if unsafe:
        raise ValueError(_CRITERIA_SOURCE_URI_ERROR)
    return str(parsed)


class CriteriaSourceProvenance(BaseModel):
    """An immutable confirmation bound to one criteria-source snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_uri: str = Field(max_length=2048)
    source_revision: str | None = Field(default=None, max_length=512)
    source_text_sha256: str
    normalized_criteria_sha256: str
    confirmed_by: str = Field(max_length=256)
    confirmed_at: datetime

    @field_validator("source_uri")
    @classmethod
    def validate_source_uri(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI:
            return normalized
        return normalize_public_https_source_uri(normalized)

    @field_validator("source_text_sha256", "normalized_criteria_sha256")
    @classmethod
    def validate_sha256_digest(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("must be a lowercase SHA-256 digest")
        return value

    @field_validator("source_revision")
    @classmethod
    def normalize_source_revision(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("source_revision must contain non-whitespace text")
        return normalized

    @field_validator("confirmed_by")
    @classmethod
    def normalize_confirmer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("confirmed_by must contain non-whitespace text")
        return normalized

    @field_validator("confirmed_at")
    @classmethod
    def normalize_utc_confirmation(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("confirmed_at must be timezone-aware")
        return value.astimezone(UTC)


class EvidenceType(StringEnum):
    IMPLEMENTATION = "implementation"
    TEST = "test"
    CI = "ci"
    DOCUMENTATION = "documentation"
    CONTRACT = "contract"
    RUNTIME = "runtime"
    HUMAN = "human"


class RetrievalOutcome(StringEnum):
    CANDIDATES_FOUND = "candidates_found"
    NO_SEARCHABLE_TERMS = "no_searchable_terms"
    NO_INSPECTABLE_LINES = "no_inspectable_lines"
    EXACT_IDENTIFIER_NOT_FOUND = "exact_identifier_not_found"
    NO_TERM_OVERLAP = "no_term_overlap"
    BELOW_RELEVANCE_THRESHOLD = "below_relevance_threshold"


class EvidenceSourceScope(StringEnum):
    CHANGED_FILE = "changed_file"
    UNCHANGED_CANDIDATE = "unchanged_candidate"


class EvidenceLevel(StringEnum):
    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"

    @property
    def rank(self) -> int:
        return int(self.value[1:])


class FindingStatus(StringEnum):
    EVIDENCE_FOUND = "evidence_found"
    PARTIAL = "partial"
    MISSING = "missing"
    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    ACCEPTED_EXCEPTION = "accepted_exception"


class HumanDecision(StringEnum):
    ACCEPTED = "accepted"
    ACCEPTED_EXCEPTION = "accepted_exception"
    CHANGE_REQUIRED = "change_required"
    REJECTED_FINDING = "rejected_finding"
    MANUALLY_VERIFIED = "manually_verified"
    NOT_IN_SCOPE = "not_in_scope"


class GateVerdict(StringEnum):
    READY = "ready"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


class LifecycleMutationMetadata(BaseModel):
    """Validated CLI output for one persisted lifecycle mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: LocalReviewId
    record: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    verdict: GateVerdict
    gate_reason_codes: list[str] = Field(default_factory=list)


class CheckState(StringEnum):
    PASSING = "passing"
    FAILING = "failing"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


class CIReasonCode(StringEnum):
    """Deterministic category for a persisted CI observation explanation."""

    FAILING_CHECK_RUNS = "failing_check_runs"
    FAILING_LEGACY_STATUSES = "failing_legacy_statuses"
    PENDING_CHECK_RUNS = "pending_check_runs"
    PENDING_LEGACY_STATUSES = "pending_legacy_statuses"
    SUCCESSFUL_CHECK_RUNS = "successful_check_runs"
    SUCCESSFUL_LEGACY_STATUSES = "successful_legacy_statuses"
    NO_OBSERVATIONS = "no_observations"
    NEUTRAL_OR_SKIPPED = "neutral_or_skipped"
    INCOMPLETE_COLLECTION = "incomplete_collection"
    HISTORICAL_UNCAPTURED = "historical_uncaptured"


class IngestionState(StringEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class CIObservation(BaseModel):
    """A validated summary of observed GitHub check and status metadata.

    This is workflow metadata, not criterion-level runtime verification.  The
    individual check-run categories partition ``total_check_runs`` so every
    persisted summary can be checked for internal consistency.
    """

    model_config = ConfigDict(extra="forbid")

    state: CheckState = CheckState.UNAVAILABLE
    reason: str = Field(min_length=1)
    reason_code: CIReasonCode = CIReasonCode.NO_OBSERVATIONS
    total_check_runs: int = Field(default=0, ge=0)
    successful_check_runs: int = Field(default=0, ge=0)
    pending_check_runs: int = Field(default=0, ge=0)
    failing_check_runs: int = Field(default=0, ge=0)
    neutral_check_runs: int = Field(default=0, ge=0)
    skipped_check_runs: int = Field(default=0, ge=0)
    concrete_legacy_status_count: int = Field(default=0, ge=0)
    successful_legacy_statuses: int = Field(default=0, ge=0)
    pending_legacy_statuses: int = Field(default=0, ge=0)
    failing_legacy_statuses: int = Field(default=0, ge=0)
    neutral_legacy_statuses: int = Field(default=0, ge=0)
    skipped_check_names: list[str] = Field(default_factory=list, max_length=8)
    collection_complete: bool = True
    collection_notes: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="before")
    @classmethod
    def fail_closed_for_uncategorized_historical_legacy_statuses(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        legacy_categories = {
            "successful_legacy_statuses",
            "pending_legacy_statuses",
            "failing_legacy_statuses",
            "neutral_legacy_statuses",
        }
        concrete_count = value.get("concrete_legacy_status_count", 0)
        if (
            isinstance(concrete_count, int)
            and concrete_count > 0
            and not legacy_categories.issubset(value)
        ):
            return {
                **value,
                "state": CheckState.UNAVAILABLE,
                "reason": (
                    "Historical legacy status categories were not captured; "
                    "CI observation collection is incomplete and unavailable."
                ),
                "reason_code": CIReasonCode.HISTORICAL_UNCAPTURED,
                "successful_legacy_statuses": 0,
                "pending_legacy_statuses": 0,
                "failing_legacy_statuses": 0,
                "neutral_legacy_statuses": concrete_count,
                "collection_complete": False,
            }
        return value

    @field_validator("reason")
    @classmethod
    def require_non_blank_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must contain non-whitespace text")
        return normalized

    @field_validator("skipped_check_names")
    @classmethod
    def require_unique_nonblank_skipped_check_names(cls, value: list[str]) -> list[str]:
        if any(not name.strip() for name in value):
            raise ValueError("skipped check names must contain non-whitespace text")
        if len(value) != len(set(value)):
            raise ValueError("skipped check names must be unique")
        return value

    @field_validator("collection_notes")
    @classmethod
    def require_unique_nonblank_collection_notes(cls, value: list[str]) -> list[str]:
        normalized = [note.strip() for note in value]
        if any(not note for note in normalized):
            raise ValueError("collection notes must contain non-whitespace text")
        if len(normalized) != len(set(normalized)):
            raise ValueError("collection notes must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_check_run_counts(self) -> CIObservation:
        if self.collection_complete and self.collection_notes:
            raise ValueError("complete CI collection cannot contain collection notes")
        categorized_runs = (
            self.successful_check_runs
            + self.pending_check_runs
            + self.failing_check_runs
            + self.neutral_check_runs
            + self.skipped_check_runs
        )
        if self.total_check_runs != categorized_runs:
            raise ValueError("total_check_runs must equal the categorized check-run counts")
        if len(self.skipped_check_names) > self.skipped_check_runs:
            raise ValueError("skipped check names cannot exceed skipped check runs")
        categorized_legacy_statuses = (
            self.successful_legacy_statuses
            + self.pending_legacy_statuses
            + self.failing_legacy_statuses
            + self.neutral_legacy_statuses
        )
        if self.concrete_legacy_status_count != categorized_legacy_statuses:
            raise ValueError(
                "concrete_legacy_status_count must equal the categorized legacy status counts"
            )

        failing_observations = self.failing_check_runs + self.failing_legacy_statuses
        pending_observations = self.pending_check_runs + self.pending_legacy_statuses
        successful_observations = self.successful_check_runs + self.successful_legacy_statuses
        if failing_observations:
            expected_state = CheckState.FAILING
        elif pending_observations:
            expected_state = CheckState.PENDING
        elif not self.collection_complete:
            expected_state = CheckState.UNAVAILABLE
        elif successful_observations:
            expected_state = CheckState.PASSING
        else:
            expected_state = CheckState.UNAVAILABLE

        if self.state is CheckState.PASSING and not successful_observations:
            raise ValueError("CI observation cannot be passing without a successful observation")
        if self.state is not expected_state:
            if not self.collection_complete:
                raise ValueError("CI observation must be unavailable when collection is incomplete")
            raise ValueError("CI observation state must match its categorized observations")

        historical_uncaptured = (
            self.reason_code is CIReasonCode.HISTORICAL_UNCAPTURED
            and self.state is CheckState.UNAVAILABLE
            and not self.collection_complete
            and not categorized_runs
            and not categorized_legacy_statuses
        )
        if failing_observations:
            reason_code = (
                CIReasonCode.FAILING_CHECK_RUNS
                if self.failing_check_runs
                else CIReasonCode.FAILING_LEGACY_STATUSES
            )
        elif pending_observations:
            reason_code = (
                CIReasonCode.PENDING_CHECK_RUNS
                if self.pending_check_runs
                else CIReasonCode.PENDING_LEGACY_STATUSES
            )
        elif not self.collection_complete:
            reason_code = (
                CIReasonCode.HISTORICAL_UNCAPTURED
                if historical_uncaptured
                else CIReasonCode.INCOMPLETE_COLLECTION
            )
        elif successful_observations:
            reason_code = (
                CIReasonCode.SUCCESSFUL_CHECK_RUNS
                if self.successful_check_runs
                else CIReasonCode.SUCCESSFUL_LEGACY_STATUSES
            )
        elif not categorized_runs and not categorized_legacy_statuses:
            reason_code = CIReasonCode.NO_OBSERVATIONS
        else:
            reason_code = CIReasonCode.NEUTRAL_OR_SKIPPED

        if reason_code is CIReasonCode.FAILING_CHECK_RUNS:
            reason = (
                f"Observed {self.failing_check_runs} failing check run"
                f"{'s' if self.failing_check_runs != 1 else ''}."
            )
        elif reason_code is CIReasonCode.FAILING_LEGACY_STATUSES:
            reason = (
                f"Observed {self.failing_legacy_statuses} concrete failing legacy status"
                f"{'es' if self.failing_legacy_statuses != 1 else ''}."
            )
        elif reason_code is CIReasonCode.PENDING_CHECK_RUNS:
            reason = (
                f"Observed {self.pending_check_runs} pending check run"
                f"{'s' if self.pending_check_runs != 1 else ''}."
            )
        elif reason_code is CIReasonCode.PENDING_LEGACY_STATUSES:
            reason = (
                f"Observed {self.pending_legacy_statuses} concrete pending legacy status"
                f"{'es' if self.pending_legacy_statuses != 1 else ''}."
            )
        elif reason_code is CIReasonCode.SUCCESSFUL_CHECK_RUNS:
            suffix = "; no concrete legacy statuses." if not categorized_legacy_statuses else "."
            reason = (
                f"Observed {self.successful_check_runs} successful completed check run"
                f"{'s' if self.successful_check_runs != 1 else ''}{suffix}"
            )
        elif reason_code is CIReasonCode.SUCCESSFUL_LEGACY_STATUSES:
            reason = (
                f"Observed {self.successful_legacy_statuses} concrete successful legacy status"
                f"{'es' if self.successful_legacy_statuses != 1 else ''}."
            )
        elif reason_code is CIReasonCode.NO_OBSERVATIONS:
            reason = "No check runs or concrete legacy statuses were observed."
        elif reason_code is CIReasonCode.NEUTRAL_OR_SKIPPED:
            if self.skipped_check_runs and not self.neutral_check_runs:
                reason = (
                    f"Observed {self.skipped_check_runs} skipped check run"
                    f"{'s' if self.skipped_check_runs != 1 else ''}; "
                    "it does not prove passing."
                )
            else:
                reason = "Observed neutral or skipped checks; neither proves passing."
        elif reason_code is CIReasonCode.HISTORICAL_UNCAPTURED:
            reason = (
                "CI observation was not captured in this historical record; "
                "collection is incomplete and unavailable."
            )
        else:
            reason = "CI observation collection is incomplete."
            if successful_observations:
                reason += " Passing cannot be concluded."
        if (
            not self.collection_complete
            and reason_code
            not in {CIReasonCode.HISTORICAL_UNCAPTURED, CIReasonCode.INCOMPLETE_COLLECTION}
        ):
            reason += " CI observation collection is incomplete."
        self.reason_code = reason_code
        self.reason = reason
        return self


def _historical_ci_observation(check_state: object) -> dict[str, object]:
    """Preserve old saved records while making their missing observation explicit."""
    return {
        "state": CheckState.UNAVAILABLE,
        "reason": (
            "CI observation was not captured in this historical record; "
            "collection is incomplete and unavailable."
        ),
        "reason_code": CIReasonCode.HISTORICAL_UNCAPTURED,
        "concrete_legacy_status_count": 0,
        "successful_legacy_statuses": 0,
        "pending_legacy_statuses": 0,
        "failing_legacy_statuses": 0,
        "neutral_legacy_statuses": 0,
        "collection_complete": False,
    }


def _requires_historical_ci_fail_closed_migration(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    observation = value.get("ci_observation")
    if not isinstance(observation, dict):
        return "ci_observation" not in value
    concrete_count = observation.get("concrete_legacy_status_count", 0)
    required_categories = {
        "successful_legacy_statuses",
        "pending_legacy_statuses",
        "failing_legacy_statuses",
        "neutral_legacy_statuses",
    }
    return (
        isinstance(concrete_count, int)
        and concrete_count > 0
        and not required_categories.issubset(observation)
    )


class ActionValidationRecord(BaseModel):
    """Owner-supplied public Action evidence; validates shape, not GitHub truth."""

    model_config = ConfigDict(extra="forbid")

    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    requirements_base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    non_fork_pr_url: str = Field(
        pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/pull/\d+$"
    )
    non_fork_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    non_fork_run_url: str = Field(
        pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/actions/runs/\d+$"
    )
    non_fork_comment_count: int = Field(ge=1)
    scopeproof_comment_marker: str = Field(pattern=r"^<!-- scopeproof:.+ -->$")
    rerun_url: str = Field(
        pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/actions/runs/\d+$"
    )
    rerun_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    rerun_comment_count: int = Field(ge=1)
    fork_status: Literal["excluded", "validated"] = "validated"
    fork_pr_url: str | None = Field(
        default=None,
        pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/pull/\d+$",
    )
    fork_run_url: str | None = Field(
        default=None,
        pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/actions/runs/\d+$",
    )
    fork_comment_count: int | None = Field(default=None, ge=0, le=0)
    validated_by: str = Field(min_length=1)
    validated_at: datetime
    limitations: list[str] = Field(min_length=1)

    @field_validator("validated_by")
    @classmethod
    def require_non_blank_action_context(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("limitations")
    @classmethod
    def require_non_blank_limitations(cls, value: list[str]) -> list[str]:
        if any(not limitation.strip() for limitation in value):
            raise ValueError("limitations must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def validate_rerun_idempotency(self) -> ActionValidationRecord:
        repository_url = f"https://github.com/{self.repository}/"
        evidence_urls = [
            self.non_fork_pr_url,
            self.non_fork_run_url,
            self.rerun_url,
        ]
        fork_evidence = [self.fork_pr_url, self.fork_run_url, self.fork_comment_count]
        if self.fork_status == "validated":
            if any(value is None for value in fork_evidence):
                raise ValueError(
                    "validated fork evidence requires PR URL, run URL, and comment count"
                )
            evidence_urls.extend([self.fork_pr_url, self.fork_run_url])
        elif any(value is not None for value in fork_evidence):
            raise ValueError("excluded fork evidence must not include fork run details")
        if any(not url.startswith(repository_url) for url in evidence_urls):
            raise ValueError("all Action evidence links must reference the same repository")
        if self.scopeproof_comment_marker != f"<!-- scopeproof:{self.non_fork_head_sha} -->":
            raise ValueError("comment marker must reference the verified non-fork head SHA")
        if self.rerun_head_sha != self.non_fork_head_sha:
            raise ValueError("same head SHA is required for an idempotency rerun")
        if self.rerun_comment_count != self.non_fork_comment_count:
            raise ValueError("same comment count is required for an idempotency rerun")
        return self


class ConfidenceBand(StringEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class LineChangeType(StringEnum):
    ADDED = "added"
    REMOVED = "removed"
    CONTEXT = "context"


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(pattern=r"^AC-\d{2,}$")
    text: str = Field(min_length=1)
    priority: Priority = Priority.MUST_HAVE
    criterion_type: CriterionType = CriterionType.BEHAVIOR
    criterion_source: CriterionSource = CriterionSource.USER_CONFIRMED
    source_span: str | None = None
    required_evidence_level: EvidenceLevel = EvidenceLevel.E1

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("criterion text must contain non-whitespace text")
        return normalized


def source_text_sha256(source_text: str) -> str:
    """Return the SHA-256 digest of source text encoded as exact UTF-8 bytes."""

    import hashlib

    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def normalized_criteria_sha256(criteria: Sequence[Criterion]) -> str:
    """Hash ordered JSON-compatible criterion payloads without mutating them."""

    import hashlib
    import json

    payload = [criterion.model_dump(mode="json") for criterion in criteria]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class CriterionDraft(BaseModel):
    criterion_id: str
    text: str


class CriterionWarning(BaseModel):
    criterion_id: str
    code: str
    message: str


class ChangedLine(BaseModel):
    change_type: LineChangeType
    content: str
    line_number: int | None = Field(default=None, ge=1)


class ChangedFile(BaseModel):
    path: str = Field(min_length=1)
    status: str
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    changes: int = Field(default=0, ge=0)
    patch: str = ""
    lines: list[ChangedLine] = Field(default_factory=list)
    truncated: bool = False


class CommitInfo(BaseModel):
    sha: str = Field(min_length=1)
    message: str
    html_url: str


class RetrievedFile(BaseModel):
    """A bounded unchanged-file candidate fetched at one immutable commit SHA."""

    path: str = Field(min_length=1)
    content: str
    commit_sha: str = Field(min_length=1)
    retrieval_reason: str = Field(min_length=1)
    source_scope: EvidenceSourceScope = EvidenceSourceScope.UNCHANGED_CANDIDATE


class PullRequestSnapshot(BaseModel):
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    repository_visibility: RepositoryVisibility = RepositoryVisibility.UNVERIFIED
    pr_number: int = Field(gt=0)
    title: str
    description: str = ""
    html_url: str
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    check_state: CheckState = CheckState.UNAVAILABLE
    ci_observation: CIObservation = Field(
        default_factory=lambda: CIObservation(
            reason="No check runs or concrete legacy statuses were observed."
        )
    )
    ingestion_state: IngestionState = IngestionState.COMPLETE
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    files: list[ChangedFile] = Field(default_factory=list)
    commits: list[CommitInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)

    @field_validator("base_sha", "head_sha")
    @classmethod
    def require_non_blank_review_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review identity must contain non-whitespace text")
        return value

    @model_validator(mode="before")
    @classmethod
    def preserve_historical_ci_state(cls, value: object) -> object:
        if isinstance(value, dict) and "check_state" in value:
            if "ci_observation" not in value:
                return {
                    **value,
                    "check_state": CheckState.UNAVAILABLE,
                    "ci_observation": _historical_ci_observation(value.get("check_state")),
                }
            if _requires_historical_ci_fail_closed_migration(value):
                return {**value, "check_state": CheckState.UNAVAILABLE}
        return value

    @model_validator(mode="after")
    def limitations_require_noncomplete_ingestion(self) -> PullRequestSnapshot:
        if self.check_state is not self.ci_observation.state:
            raise ValueError("check_state must agree with ci_observation.state")
        if self.ingestion_state is IngestionState.COMPLETE and (
            self.warnings or self.skipped_files
        ):
            raise ValueError("complete ingestion cannot include limitations")
        return self


class Review(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    repository_visibility: RepositoryVisibility = RepositoryVisibility.UNVERIFIED
    pr_number: int = Field(gt=0)
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    check_state: CheckState = CheckState.UNAVAILABLE
    ci_observation: CIObservation = Field(
        default_factory=lambda: CIObservation(
            reason="No check runs or concrete legacy statuses were observed."
        )
    )
    criteria_confirmed: bool = False
    criteria_source_provenance: CriteriaSourceProvenance | None = None
    ingestion_state: IngestionState = IngestionState.COMPLETE
    ingestion_warnings: list[str] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)
    input_origin: ReviewInputOrigin = ReviewInputOrigin.LEGACY_UNKNOWN
    final_acceptance: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tool_version: str = Field(default_factory=lambda: __version__)
    ruleset_version: str = RULESET_VERSION

    @field_validator("base_sha", "head_sha")
    @classmethod
    def require_non_blank_review_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review identity must contain non-whitespace text")
        return value

    @model_validator(mode="before")
    @classmethod
    def preserve_historical_review_state(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        migrated = value
        if (
            value.get("input_origin")
            in {ReviewInputOrigin.LIVE_PUBLIC_GITHUB, ReviewInputOrigin.LIVE_PUBLIC_GITHUB.value}
            and value.get(
                "repository_visibility", RepositoryVisibility.UNVERIFIED
            )
            not in {
                RepositoryVisibility.VERIFIED_PUBLIC,
                RepositoryVisibility.VERIFIED_PUBLIC.value,
            }
        ):
            migrated = {**migrated, "input_origin": ReviewInputOrigin.LEGACY_UNKNOWN}
        elif (
            value.get("input_origin", ReviewInputOrigin.LEGACY_UNKNOWN)
            not in {
                ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
                ReviewInputOrigin.LIVE_PUBLIC_GITHUB.value,
            }
            and value.get("repository_visibility")
            in {
                RepositoryVisibility.VERIFIED_PUBLIC,
                RepositoryVisibility.VERIFIED_PUBLIC.value,
            }
        ):
            migrated = {
                **migrated,
                "repository_visibility": RepositoryVisibility.UNVERIFIED,
            }

        if "check_state" in migrated:
            if "ci_observation" not in migrated:
                return {
                    **migrated,
                    "check_state": CheckState.UNAVAILABLE,
                    "ci_observation": _historical_ci_observation(migrated.get("check_state")),
                }
            if _requires_historical_ci_fail_closed_migration(migrated):
                return {**migrated, "check_state": CheckState.UNAVAILABLE}
        return migrated

    @model_validator(mode="after")
    def limitations_require_noncomplete_ingestion(self) -> Review:
        if self.check_state is not self.ci_observation.state:
            raise ValueError("check_state must agree with ci_observation.state")
        if self.ingestion_state is IngestionState.COMPLETE and (
            self.ingestion_warnings or self.skipped_files
        ):
            raise ValueError("complete ingestion cannot include limitations")
        return self

    @computed_field
    @property
    def can_analyze(self) -> bool:
        return self.criteria_confirmed and self.ingestion_state is not IngestionState.FAILED


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    criterion_id: str
    evidence_type: EvidenceType
    evidence_level: EvidenceLevel
    source_scope: EvidenceSourceScope = EvidenceSourceScope.CHANGED_FILE
    file_path: str = Field(min_length=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    commit_sha: str = Field(min_length=1)
    permalink: str
    excerpt: str = Field(min_length=1)
    context_excerpt: str | None = None
    matching_rule: str = Field(min_length=1)
    relevance_reason: str = Field(min_length=1)
    relevance_score: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)

    @field_validator(
        "evidence_id",
        "criterion_id",
        "file_path",
        "commit_sha",
        "permalink",
        "excerpt",
        "matching_rule",
        "relevance_reason",
        mode="before",
    )
    @classmethod
    def require_non_blank_candidate_context(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("context_excerpt")
    @classmethod
    def require_non_blank_optional_context(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("context excerpt must contain non-whitespace text")
        return value

    @field_validator("limitations")
    @classmethod
    def require_non_blank_limitations(cls, value: list[str]) -> list[str]:
        if any(not limitation.strip() for limitation in value):
            raise ValueError("limitations must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def validate_line_range(self) -> EvidenceItem:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class CriterionRetrievalDiagnostic(BaseModel):
    """Deterministic search metadata that is never criterion evidence."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1)
    outcome: RetrievalOutcome
    searched_terms: list[str]
    exact_identifiers: list[str]
    searched_paths: list[str]
    searched_evidence_types: list[EvidenceType]
    changed_file_count: int = Field(ge=0)
    unchanged_candidate_file_count: int = Field(ge=0)
    inspectable_line_count: int = Field(ge=0)
    exact_identifier_match_line_count: int = Field(ge=0)
    term_overlap_line_count: int = Field(ge=0)
    below_threshold_line_count: int = Field(ge=0)
    accepted_candidate_count: int = Field(ge=0)

    @field_validator("criterion_id")
    @classmethod
    def require_non_blank_criterion_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("criterion ID must contain non-whitespace text")
        return normalized

    @field_validator(
        "searched_terms",
        "exact_identifiers",
        "searched_paths",
        mode="before",
    )
    @classmethod
    def normalize_sorted_text_lists(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                return value
            text = item.strip()
            if not text:
                raise ValueError("search metadata must contain non-whitespace text")
            normalized.append(text)
        return sorted(set(normalized))

    @field_validator("searched_evidence_types")
    @classmethod
    def normalize_sorted_evidence_types(
        cls, value: list[EvidenceType]
    ) -> list[EvidenceType]:
        return sorted(set(value), key=lambda item: item.value)


class EvidenceRetrievalResult(BaseModel):
    """Validated evidence candidates and their separate retrieval diagnostics."""

    model_config = ConfigDict(extra="forbid")

    evidence: list[EvidenceItem]
    diagnostics: list[CriterionRetrievalDiagnostic]


class RuntimeEvidence(BaseModel):
    """Human-supplied runtime observation; never inferred from static code."""

    model_config = ConfigDict(extra="forbid")

    runtime_evidence_id: str | None = None
    repository: str | None = Field(default=None, pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: int | None = Field(default=None, gt=0)
    head_sha: str | None = None
    criterion_id: str
    artifact_reference: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    environment: str = Field(min_length=1)
    result: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    evidence_level: EvidenceLevel
    limitations: list[str] = Field(default_factory=list)

    @field_validator(
        "artifact_reference",
        "scenario",
        "environment",
        "result",
        "reviewer",
    )
    @classmethod
    def require_non_blank_human_context(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("limitations")
    @classmethod
    def require_non_blank_limitations(cls, value: list[str]) -> list[str]:
        if any(not limitation.strip() for limitation in value):
            raise ValueError("limitations must contain non-whitespace text")
        return value

    @field_validator("runtime_evidence_id", "head_sha")
    @classmethod
    def require_non_blank_runtime_identity(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def validate_runtime_identity_scope(self) -> RuntimeEvidence:
        identity = (
            self.runtime_evidence_id,
            self.repository,
            self.pr_number,
            self.head_sha,
        )
        populated_fields = sum(value is not None for value in identity)
        if populated_fields not in {0, len(identity)}:
            raise ValueError(
                "runtime identity fields must all be present or all be absent"
            )
        return self

    @model_validator(mode="after")
    def validate_manual_level(self) -> RuntimeEvidence:
        if self.evidence_level not in {EvidenceLevel.E3, EvidenceLevel.E4}:
            raise ValueError("runtime evidence requires E3 or E4")
        return self


class JUnitCaseStatus(StringEnum):
    """Sanitized externally supplied JUnit result state."""

    PASSED = "passed"
    FAILURE = "failure"
    ERROR = "error"
    SKIPPED = "skipped"


class JUnitCaseResult(BaseModel):
    """One bounded result projection without raw XML or output bodies."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    test_case_id: str = Field(pattern=r"^suite-\d{4}-case-\d{4}$")
    suite_id: str = Field(pattern=r"^suite-\d{4}$")
    suite_name: str = Field(max_length=512)
    class_name: str | None = Field(default=None, max_length=512)
    test_name: str = Field(max_length=512)
    status: JUnitCaseStatus

    @field_validator("suite_name", "test_name")
    @classmethod
    def require_non_blank_names(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must contain non-whitespace text")
        if junit_name_is_path_or_url_like(normalized):
            raise ValueError("JUnit names must not contain path- or URL-like text")
        return normalized

    @field_validator("class_name")
    @classmethod
    def normalize_optional_class_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("class name must contain non-whitespace text")
        if junit_name_is_path_or_url_like(normalized):
            raise ValueError("JUnit names must not contain path- or URL-like text")
        return normalized

    @model_validator(mode="after")
    def require_case_to_belong_to_suite(self) -> JUnitCaseResult:
        if not self.test_case_id.startswith(f"{self.suite_id}-case-"):
            raise ValueError("JUnit test case ID must belong to its suite ID")
        return self


class JUnitResultTotals(BaseModel):
    """Computed JUnit result totals; artifact-declared totals are not trusted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failures: int = Field(ge=0)
    errors: int = Field(ge=0)
    skipped: int = Field(ge=0)

    @model_validator(mode="after")
    def require_categories_to_sum_to_total(self) -> JUnitResultTotals:
        categorized = self.passed + self.failures + self.errors + self.skipped
        if categorized != self.total:
            raise ValueError("JUnit result categories must sum to total")
        return self


class JUnitCriterionMapping(BaseModel):
    """Explicit human mapping from sanitized test cases to one criterion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str = Field(min_length=1)
    test_case_ids: list[str] = Field(min_length=1)

    @field_validator("criterion_id")
    @classmethod
    def require_non_blank_criterion_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("criterion ID must contain non-whitespace text")
        return normalized

    @field_validator("test_case_ids")
    @classmethod
    def require_canonical_case_ids(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("mapped test case IDs must be sorted and unique")
        if any(re.fullmatch(r"suite-\d{4}-case-\d{4}", item) is None for item in value):
            raise ValueError("mapped test case IDs must use stable JUnit case IDs")
        return value


class JUnitEvidenceBoundary(BaseModel):
    """Fixed machine-readable trust semantics for every external JUnit import."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["externally_supplied"] = "externally_supplied"
    gate_effect: Literal["non_gating"] = "non_gating"
    execution: Literal["not_executed_by_scopeproof"] = "not_executed_by_scopeproof"
    artifact_digest_scope: Literal["imported_bytes_only"] = "imported_bytes_only"
    importer_identity: Literal["asserted_not_authenticated"] = (
        "asserted_not_authenticated"
    )
    criterion_mapping: Literal["organizational_context_not_proof"] = (
        "organizational_context_not_proof"
    )


class JUnitEvidenceImport(BaseModel):
    """Versioned external test-result context that never enters gate truth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["junit-import-v1"]
    evidence_boundary: JUnitEvidenceBoundary
    import_id: LocalReviewId
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: int = Field(gt=0)
    head_sha: str = Field(pattern=_EXACT_HEAD_PATTERN)
    criteria_revision_number: Annotated[StrictInt, Field(gt=0)]
    confirmed_criteria_sha256: str
    criteria_source_provenance: CriteriaSourceProvenance
    artifact_sha256: str
    artifact_format: Literal["junit_xml"] = "junit_xml"
    imported_by: str = Field(max_length=256)
    imported_at: datetime
    totals: JUnitResultTotals
    test_cases: list[JUnitCaseResult] = Field(min_length=1, max_length=5_000)
    criterion_mappings: list[JUnitCriterionMapping] = Field(min_length=1)
    parser_warnings: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(min_length=1, max_length=100)

    @field_validator("confirmed_criteria_sha256", "artifact_sha256")
    @classmethod
    def validate_sha256_digest(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("must be a lowercase SHA-256 digest")
        return value

    @field_validator("imported_by")
    @classmethod
    def normalize_importer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("imported_by must contain non-whitespace text")
        return normalized

    @field_validator("imported_at")
    @classmethod
    def normalize_import_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("imported_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("parser_warnings", "limitations")
    @classmethod
    def require_unique_non_blank_notes(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("notes must contain non-whitespace text")
        if len(normalized) != len(set(normalized)):
            raise ValueError("notes must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_result_and_mapping_cross_references(self) -> JUnitEvidenceImport:
        case_ids = [item.test_case_id for item in self.test_cases]
        if case_ids != sorted(set(case_ids)):
            raise ValueError("JUnit test case IDs must be sorted and unique")
        observed = {
            JUnitCaseStatus.PASSED: 0,
            JUnitCaseStatus.FAILURE: 0,
            JUnitCaseStatus.ERROR: 0,
            JUnitCaseStatus.SKIPPED: 0,
        }
        for item in self.test_cases:
            observed[item.status] += 1
        if (
            self.totals.total,
            self.totals.passed,
            self.totals.failures,
            self.totals.errors,
            self.totals.skipped,
        ) != (
            len(self.test_cases),
            observed[JUnitCaseStatus.PASSED],
            observed[JUnitCaseStatus.FAILURE],
            observed[JUnitCaseStatus.ERROR],
            observed[JUnitCaseStatus.SKIPPED],
        ):
            raise ValueError("JUnit totals must match sanitized test case results")
        mapping_criteria = [item.criterion_id for item in self.criterion_mappings]
        if mapping_criteria != sorted(set(mapping_criteria)):
            raise ValueError("JUnit criterion mappings must be sorted and unique")
        known_case_ids = set(case_ids)
        if any(
            case_id not in known_case_ids
            for mapping in self.criterion_mappings
            for case_id in mapping.test_case_ids
        ):
            raise ValueError("mapped test case IDs must resolve")
        mapped_case_ids = [
            case_id
            for mapping in self.criterion_mappings
            for case_id in mapping.test_case_ids
        ]
        if len(mapped_case_ids) != len(set(mapped_case_ids)):
            raise ValueError("one JUnit test case must not map to multiple criteria")
        return self


class JUnitImportMutationMetadata(BaseModel):
    """Validated CLI output for one persisted JUnit import mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: LocalReviewId
    record: str = Field(min_length=1)
    head_sha: str = Field(pattern=_EXACT_HEAD_PATTERN)
    import_id: LocalReviewId
    artifact_sha256: str
    mapped_criterion_ids: list[str] = Field(min_length=1)
    totals: JUnitResultTotals
    evidence_boundary: Literal["externally_supplied_non_gating"]
    verdict: GateVerdict

    @field_validator("artifact_sha256")
    @classmethod
    def validate_artifact_digest(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("must be a lowercase SHA-256 digest")
        return value

    @field_validator("mapped_criterion_ids")
    @classmethod
    def require_canonical_criteria(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)) or any(not item.strip() for item in value):
            raise ValueError("mapped criterion IDs must be sorted unique IDs")
        return value


class Finding(BaseModel):
    criterion_id: str
    status: FindingStatus
    evidence_level: EvidenceLevel = EvidenceLevel.E0
    confidence_band: ConfidenceBand = ConfidenceBand.LOW
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    recommended_action: str

    @field_validator("reason", "recommended_action", mode="before")
    @classmethod
    def require_non_blank_explanation(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value

    @field_validator("missing_evidence", "contradictions")
    @classmethod
    def require_non_blank_context(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("finding context must contain non-whitespace text")
        return value


class HumanResolution(BaseModel):
    criterion_id: str
    decision: HumanDecision
    comment: str = ""
    evidence_url: str | None = None
    claimed_evidence_level: EvidenceLevel | None = None
    runtime_evidence_id: str | None = None
    reviewer: str = "Local reviewer"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def manual_verification_needs_level(self) -> HumanResolution:
        if (
            self.runtime_evidence_id is not None
            and self.decision is not HumanDecision.MANUALLY_VERIFIED
        ):
            raise ValueError(
                "runtime evidence ID is reserved for manually verified decisions"
            )
        if self.decision is HumanDecision.MANUALLY_VERIFIED and self.claimed_evidence_level is None:
            raise ValueError("manually verified decisions require a claimed evidence level")
        if self.decision is HumanDecision.MANUALLY_VERIFIED and not self.comment.strip():
            raise ValueError("manually verified decisions require a reviewer note")
        return self


class ResolutionEvent(BaseModel):
    """Append-only human decision or review-level final-acceptance event."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    criterion_id: str | None = None
    decision: HumanDecision | None = None
    final_acceptance: bool | None = None
    comment: str = ""
    evidence_url: str | None = None
    claimed_evidence_level: EvidenceLevel | None = None
    runtime_evidence_id: str | None = None
    reviewer: str = "Local reviewer"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    criteria_revision_number: int = Field(default=0, ge=0)

    @field_validator("event_id")
    @classmethod
    def require_non_blank_event_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("event ID must contain non-whitespace text")
        return value

    @field_validator("reviewer")
    @classmethod
    def require_non_blank_reviewer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewer must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def validate_event_kind(self) -> ResolutionEvent:
        is_criterion_event = self.criterion_id is not None and self.decision is not None
        is_final_event = self.criterion_id is None and self.final_acceptance is not None
        if is_criterion_event == is_final_event:
            raise ValueError("event must be either a criterion decision or a final acceptance")
        if (
            self.runtime_evidence_id is not None
            and self.decision is not HumanDecision.MANUALLY_VERIFIED
        ):
            raise ValueError(
                "runtime evidence ID is reserved for manually verified decisions"
            )
        has_wrong_claimed_level = (
            self.claimed_evidence_level is not None
            and self.decision is not HumanDecision.MANUALLY_VERIFIED
        )
        if has_wrong_claimed_level:
            raise ValueError("claimed evidence level is reserved for manually verified decisions")
        if self.decision is HumanDecision.MANUALLY_VERIFIED and self.claimed_evidence_level is None:
            raise ValueError("manually verified events require a claimed evidence level")
        if self.decision is HumanDecision.MANUALLY_VERIFIED and not self.comment.strip():
            raise ValueError("manually verified decisions require a reviewer note")
        return self


class CriteriaRevision(BaseModel):
    """A user-owned criterion set that must be confirmed before analysis."""

    number: int = Field(gt=0)
    criteria: list[Criterion]
    source_text: str
    confirmed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmed_at: datetime | None = None
    source_provenance: CriteriaSourceProvenance | None = None

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requirements source must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def validate_source_provenance(self) -> CriteriaRevision:
        if self.source_provenance is None:
            return self
        if not self.confirmed:
            raise ValueError("criteria source provenance requires confirmed criteria")
        if self.confirmed_at != self.source_provenance.confirmed_at:
            raise ValueError(
                "criteria confirmation timestamp must match source provenance"
            )
        if self.source_provenance.source_text_sha256 != source_text_sha256(
            self.source_text
        ):
            raise ValueError("criteria source provenance does not match source text")
        if self.source_provenance.normalized_criteria_sha256 != normalized_criteria_sha256(
            self.criteria
        ):
            raise ValueError("criteria source provenance does not match criteria")
        return self


class GateDecision(BaseModel):
    verdict: GateVerdict
    blocking_criteria: list[str] = Field(default_factory=list)
    conditional_criteria: list[str] = Field(default_factory=list)
    unresolved_criteria: list[str] = Field(default_factory=list)
    resolved_exceptions: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class RuntimeVerificationState(StringEnum):
    NOT_RECORDED = "not_recorded"
    RECORDED = "recorded"


class ReviewerDecisionState(StringEnum):
    UNRESOLVED = "unresolved"
    PARTIAL = "partial"
    RECORDED = "recorded"


class ResearchContext(BaseModel):
    """Fixed boundary for a public engineering research review.

    Research cases can improve deterministic engineering evidence, but they are
    never participants, customer validation, or Stage 1 credit.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(pattern=r"^[A-Z][A-Z0-9_-]{0,31}-\d{3,}$")
    classification: Literal["public_engineering_research"] = (
        "public_engineering_research"
    )
    stage1_credit: Literal[False] = False
    boundary_note: str = Field(min_length=1)

    @field_validator("boundary_note")
    @classmethod
    def require_non_blank_boundary_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("boundary note must contain non-whitespace text")
        return normalized


class ReviewBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review: Review
    criteria_revision_number: Annotated[StrictInt, Field(gt=0)] | Literal[
        "unknown"
    ] = "unknown"
    source_text: str
    criteria: list[Criterion]
    evidence: list[EvidenceItem]
    retrieval_diagnostics: list[CriterionRetrievalDiagnostic] = Field(
        default_factory=list
    )
    runtime_evidence: list[RuntimeEvidence] = Field(default_factory=list)
    junit_evidence_imports: list[JUnitEvidenceImport] = Field(default_factory=list)
    findings: list[Finding]
    resolutions: list[HumanResolution] = Field(default_factory=list)
    gate: GateDecision
    research_context: ResearchContext | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_serialized_presentation_fields(cls, value: object) -> object:
        """Discard serialized presentation values so derived state cannot drift."""
        if not isinstance(value, dict):
            return value
        return {
            key: item
            for key, item in value.items()
            if key
            not in {
                "candidate_evidence_proves_correctness",
                "runtime_verification_state",
                "reviewer_decision_state",
            }
        }

    @computed_field
    @property
    def candidate_evidence_proves_correctness(self) -> Literal[False]:
        """Candidate references are never a correctness claim."""
        return False

    @computed_field
    @property
    def runtime_verification_state(self) -> RuntimeVerificationState:
        """State derived solely from persisted manual runtime records."""
        return (
            RuntimeVerificationState.RECORDED
            if self.runtime_evidence
            else RuntimeVerificationState.NOT_RECORDED
        )

    @computed_field
    @property
    def reviewer_decision_state(self) -> ReviewerDecisionState:
        """Review-wide decision completeness derived from criterion resolutions."""
        if not self.resolutions:
            return ReviewerDecisionState.UNRESOLVED
        if len(self.resolutions) == len(self.criteria):
            return ReviewerDecisionState.RECORDED
        return ReviewerDecisionState.PARTIAL

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requirements source must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def validate_cross_references(self) -> ReviewBundle:
        criterion_ids = [criterion.criterion_id for criterion in self.criteria]
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError("criterion IDs must be unique")
        if self.review.criteria_source_provenance is not None:
            provenance = self.review.criteria_source_provenance
            if provenance.source_text_sha256 != source_text_sha256(self.source_text):
                raise ValueError("criteria source provenance does not match source text")
            if provenance.normalized_criteria_sha256 != normalized_criteria_sha256(self.criteria):
                raise ValueError("criteria source provenance does not match criteria")
        known_criteria = set(criterion_ids)

        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        if any(item.criterion_id not in known_criteria for item in self.evidence):
            raise ValueError("evidence criterion IDs must reference known criteria")

        if self.retrieval_diagnostics:
            diagnostic_ids = [
                diagnostic.criterion_id for diagnostic in self.retrieval_diagnostics
            ]
            if len(diagnostic_ids) != len(set(diagnostic_ids)):
                raise ValueError("diagnostic criterion IDs must be unique")
            if set(diagnostic_ids) != known_criteria:
                raise ValueError("diagnostics must match criteria exactly")
            evidence_count_by_criterion = {
                criterion_id: sum(
                    item.criterion_id == criterion_id for item in self.evidence
                )
                for criterion_id in known_criteria
            }
            if any(
                diagnostic.accepted_candidate_count
                != evidence_count_by_criterion[diagnostic.criterion_id]
                for diagnostic in self.retrieval_diagnostics
            ):
                raise ValueError("diagnostic candidate count must match evidence")

        finding_ids = [finding.criterion_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("finding criterion IDs must be unique")
        if set(finding_ids) != known_criteria:
            raise ValueError("findings must match criteria exactly")
        for finding in self.findings:
            if len(finding.evidence_ids) != len(set(finding.evidence_ids)):
                raise ValueError("finding evidence references must be unique")
            if any(evidence_id not in evidence_by_id for evidence_id in finding.evidence_ids):
                raise ValueError("finding evidence references must resolve")
            if any(
                evidence_by_id[evidence_id].criterion_id != finding.criterion_id
                for evidence_id in finding.evidence_ids
            ):
                raise ValueError("finding evidence must belong to the same criterion")

        if any(item.criterion_id not in known_criteria for item in self.runtime_evidence):
            raise ValueError("runtime evidence criterion IDs must reference known criteria")
        runtime_ids = [
            item.runtime_evidence_id
            for item in self.runtime_evidence
            if item.runtime_evidence_id is not None
        ]
        if len(runtime_ids) != len(set(runtime_ids)):
            raise ValueError("runtime evidence IDs must be unique")
        for item in self.runtime_evidence:
            if item.runtime_evidence_id is None:
                continue
            if (
                item.repository,
                item.pr_number,
                item.head_sha,
            ) != (
                self.review.repository,
                self.review.pr_number,
                self.review.head_sha,
            ):
                raise ValueError(
                    "runtime evidence identity must match the owning review"
                )
        runtime_by_id = {
            item.runtime_evidence_id: item
            for item in self.runtime_evidence
            if item.runtime_evidence_id is not None
        }

        junit_import_ids = [item.import_id for item in self.junit_evidence_imports]
        if len(junit_import_ids) != len(set(junit_import_ids)):
            raise ValueError("JUnit import IDs must be unique")
        junit_artifact_digests = [
            item.artifact_sha256 for item in self.junit_evidence_imports
        ]
        if len(junit_artifact_digests) != len(set(junit_artifact_digests)):
            raise ValueError("JUnit artifact digests must be unique")
        criteria_digest = normalized_criteria_sha256(self.criteria)
        for item in self.junit_evidence_imports:
            if (
                item.repository,
                item.pr_number,
                item.head_sha,
            ) != (
                self.review.repository,
                self.review.pr_number,
                self.review.head_sha,
            ):
                raise ValueError("JUnit import identity must match the owning review")
            if item.criteria_revision_number != self.criteria_revision_number:
                raise ValueError("JUnit import criteria revision must match the bundle")
            if item.confirmed_criteria_sha256 != criteria_digest:
                raise ValueError("JUnit import criteria digest must match the bundle")
            if item.criteria_source_provenance != self.review.criteria_source_provenance:
                raise ValueError("JUnit import criteria provenance must match the review")
            if any(
                mapping.criterion_id not in known_criteria
                for mapping in item.criterion_mappings
            ):
                raise ValueError("JUnit import mappings must reference known criteria")

        resolution_ids = [resolution.criterion_id for resolution in self.resolutions]
        if len(resolution_ids) != len(set(resolution_ids)):
            raise ValueError("resolution criterion IDs must be unique")
        if any(criterion_id not in known_criteria for criterion_id in resolution_ids):
            raise ValueError("resolution criterion IDs must reference known criteria")
        for resolution in self.resolutions:
            if resolution.runtime_evidence_id is None:
                continue
            runtime_item = runtime_by_id.get(resolution.runtime_evidence_id)
            if runtime_item is None:
                raise ValueError("resolution runtime evidence ID must resolve")
            if (
                resolution.criterion_id,
                resolution.reviewer,
                resolution.claimed_evidence_level,
            ) != (
                runtime_item.criterion_id,
                runtime_item.reviewer,
                runtime_item.evidence_level,
            ):
                raise ValueError(
                    "linked resolution must match runtime evidence criterion, "
                    "reviewer, and level"
                )

        for field_name in (
            "blocking_criteria",
            "conditional_criteria",
            "unresolved_criteria",
            "resolved_exceptions",
        ):
            gate_criterion_ids = getattr(self.gate, field_name)
            if len(gate_criterion_ids) != len(set(gate_criterion_ids)):
                raise ValueError(f"{field_name} must contain unique criterion IDs")
            if any(criterion_id not in known_criteria for criterion_id in gate_criterion_ids):
                raise ValueError(f"{field_name} must reference known criteria")

        return self


class ReviewState(BaseModel):
    """Validated local lifecycle state for one review and its audit history."""

    review: Review
    criteria_revision: CriteriaRevision
    bundle: ReviewBundle | None = None
    analysis_history: list[ReviewBundle] = Field(default_factory=list)
    resolution_events: list[ResolutionEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_active_review_identity(self) -> ReviewState:
        event_ids = [event.event_id for event in self.resolution_events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("resolution event IDs must be unique")
        if any(
            event.criteria_revision_number < 1
            or event.criteria_revision_number > self.criteria_revision.number
            for event in self.resolution_events
        ):
            raise ValueError(
                "resolution event revisions must reference an existing criteria revision"
            )
        if self.bundle is not None and self.bundle.review != self.review:
            raise ValueError("active bundle review must match lifecycle review")
        if self.bundle is not None and (
            self.bundle.criteria_revision_number == "unknown"
            or self.bundle.criteria_revision_number != self.criteria_revision.number
        ):
            raise ValueError(
                "active bundle revision must match the active criteria revision"
            )
        if self.review.criteria_confirmed != self.criteria_revision.confirmed:
            raise ValueError("criteria confirmation must match the active revision")
        if (
            self.review.criteria_source_provenance
            != self.criteria_revision.source_provenance
        ) or (
            self.bundle is not None
            and self.bundle.review.criteria_source_provenance
            != self.review.criteria_source_provenance
        ):
            raise ValueError(
                "active criteria source provenance must match lifecycle review and active revision"
            )
        if self.bundle is not None and not self.criteria_revision.confirmed:
            raise ValueError("active bundle requires a confirmed criteria revision")
        if (
            self.bundle is not None
            and self.bundle.criteria != self.criteria_revision.criteria
        ):
            raise ValueError("active bundle criteria must match the active revision")
        if (
            self.bundle is not None
            and self.bundle.source_text != self.criteria_revision.source_text
        ):
            raise ValueError("active bundle source must match the active revision")
        active_lineage = (
            self.review.review_id,
            self.review.repository,
            self.review.pr_number,
        )
        known_historical_revisions: list[int] = []
        for historical_bundle in self.analysis_history:
            historical_lineage = (
                historical_bundle.review.review_id,
                historical_bundle.review.repository,
                historical_bundle.review.pr_number,
            )
            if historical_lineage != active_lineage:
                raise ValueError(
                    "historical bundle review lineage must match lifecycle review"
                )
            if historical_bundle.criteria_revision_number != "unknown":
                known_historical_revisions.append(
                    historical_bundle.criteria_revision_number
                )
        if any(
            revision_number >= self.criteria_revision.number
            for revision_number in known_historical_revisions
        ):
            raise ValueError(
                "historical bundle revisions must be lower than the active revision"
            )
        if any(
            earlier >= later
            for earlier, later in pairwise(known_historical_revisions)
        ):
            raise ValueError(
                "known historical bundle revisions must be unique and strictly increasing"
            )
        return self
