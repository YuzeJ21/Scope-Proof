"""Pydantic contracts for reviews, evidence, findings, and reports."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from scopeproof_core.version import __version__

RULESET_VERSION = "1.0.0"
GITHUB_REPOSITORY_PATTERN = r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$"


class StringEnum(StrEnum):
    """A JSON-friendly enum with readable values."""


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


class EvidenceType(StringEnum):
    IMPLEMENTATION = "implementation"
    TEST = "test"
    CI = "ci"
    DOCUMENTATION = "documentation"
    CONTRACT = "contract"
    RUNTIME = "runtime"
    HUMAN = "human"


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


class CheckState(StringEnum):
    PASSING = "passing"
    FAILING = "failing"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


class IngestionState(StringEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


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
    pr_number: int = Field(gt=0)
    title: str
    description: str = ""
    html_url: str
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    check_state: CheckState = CheckState.UNAVAILABLE
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

    @model_validator(mode="after")
    def limitations_require_noncomplete_ingestion(self) -> PullRequestSnapshot:
        if self.ingestion_state is IngestionState.COMPLETE and (
            self.warnings or self.skipped_files
        ):
            raise ValueError("complete ingestion cannot include limitations")
        return self


class Review(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: int = Field(gt=0)
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    check_state: CheckState = CheckState.UNAVAILABLE
    criteria_confirmed: bool = False
    ingestion_state: IngestionState = IngestionState.COMPLETE
    ingestion_warnings: list[str] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)
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

    @model_validator(mode="after")
    def limitations_require_noncomplete_ingestion(self) -> Review:
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


class RuntimeEvidence(BaseModel):
    """Human-supplied runtime observation; never inferred from static code."""

    model_config = ConfigDict(extra="forbid")

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

    @model_validator(mode="after")
    def validate_manual_level(self) -> RuntimeEvidence:
        if self.evidence_level not in {EvidenceLevel.E3, EvidenceLevel.E4}:
            raise ValueError("runtime evidence requires E3 or E4")
        return self


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
    reviewer: str = "Local reviewer"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def manual_verification_needs_level(self) -> HumanResolution:
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
    reviewer: str = "Local reviewer"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    criteria_revision_number: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_event_kind(self) -> ResolutionEvent:
        is_criterion_event = self.criterion_id is not None and self.decision is not None
        is_final_event = self.criterion_id is None and self.final_acceptance is not None
        if is_criterion_event == is_final_event:
            raise ValueError("event must be either a criterion decision or a final acceptance")
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

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requirements source must contain non-whitespace text")
        return value


class GateDecision(BaseModel):
    verdict: GateVerdict
    blocking_criteria: list[str] = Field(default_factory=list)
    conditional_criteria: list[str] = Field(default_factory=list)
    unresolved_criteria: list[str] = Field(default_factory=list)
    resolved_exceptions: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class ReviewBundle(BaseModel):
    review: Review
    source_text: str
    criteria: list[Criterion]
    evidence: list[EvidenceItem]
    runtime_evidence: list[RuntimeEvidence] = Field(default_factory=list)
    findings: list[Finding]
    resolutions: list[HumanResolution] = Field(default_factory=list)
    gate: GateDecision

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
        known_criteria = set(criterion_ids)

        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        if any(item.criterion_id not in known_criteria for item in self.evidence):
            raise ValueError("evidence criterion IDs must reference known criteria")

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

        resolution_ids = [resolution.criterion_id for resolution in self.resolutions]
        if len(resolution_ids) != len(set(resolution_ids)):
            raise ValueError("resolution criterion IDs must be unique")
        if any(criterion_id not in known_criteria for criterion_id in resolution_ids):
            raise ValueError("resolution criterion IDs must reference known criteria")

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
        if self.bundle is not None and self.bundle.review != self.review:
            raise ValueError("active bundle review must match lifecycle review")
        if self.review.criteria_confirmed != self.criteria_revision.confirmed:
            raise ValueError("criteria confirmation must match the active revision")
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
        return self
