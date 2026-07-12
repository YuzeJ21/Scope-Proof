"""Pydantic contracts for reviews, evidence, findings, and reports."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

RULESET_VERSION = "1.0.0"


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

    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
    requirements_base_sha: str = Field(min_length=1)
    non_fork_pr_url: str = Field(pattern=r"^https://github\.com/[^/]+/[^/]+/pull/\d+$")
    non_fork_head_sha: str = Field(min_length=1)
    non_fork_run_url: str = Field(pattern=r"^https://github\.com/[^/]+/[^/]+/actions/runs/\d+$")
    non_fork_comment_count: int = Field(ge=1)
    rerun_url: str = Field(pattern=r"^https://github\.com/[^/]+/[^/]+/actions/runs/\d+$")
    rerun_head_sha: str = Field(min_length=1)
    rerun_comment_count: int = Field(ge=1)
    fork_pr_url: str = Field(pattern=r"^https://github\.com/[^/]+/[^/]+/pull/\d+$")
    fork_run_url: str = Field(pattern=r"^https://github\.com/[^/]+/[^/]+/actions/runs/\d+$")
    fork_comment_count: int = Field(ge=0, le=0)
    validated_by: str = Field(min_length=1)
    validated_at: datetime
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rerun_idempotency(self) -> ActionValidationRecord:
        repository_url = f"https://github.com/{self.repository}/"
        evidence_urls = [
            self.non_fork_pr_url,
            self.non_fork_run_url,
            self.rerun_url,
            self.fork_pr_url,
            self.fork_run_url,
        ]
        if any(not url.startswith(repository_url) for url in evidence_urls):
            raise ValueError("all Action evidence links must reference the same repository")
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
        return value.strip()


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
    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
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


class Review(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
    pr_number: int = Field(gt=0)
    base_sha: str = Field(min_length=1)
    head_sha: str = Field(min_length=1)
    check_state: CheckState = CheckState.UNAVAILABLE
    criteria_confirmed: bool = False
    ingestion_state: IngestionState = IngestionState.COMPLETE
    final_acceptance: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tool_version: str = "0.1.0"
    ruleset_version: str = RULESET_VERSION

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
        return self


class CriteriaRevision(BaseModel):
    """A user-owned criterion set that must be confirmed before analysis."""

    number: int = Field(gt=0)
    criteria: list[Criterion]
    source_text: str
    confirmed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmed_at: datetime | None = None


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


class ReviewState(BaseModel):
    """Validated local lifecycle state for one review and its audit history."""

    review: Review
    criteria_revision: CriteriaRevision
    bundle: ReviewBundle | None = None
    analysis_history: list[ReviewBundle] = Field(default_factory=list)
    resolution_events: list[ResolutionEvent] = Field(default_factory=list)
