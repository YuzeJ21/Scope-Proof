"""Strict, deterministic persisted contracts for the R-002 research benchmark."""

from __future__ import annotations

import json
import re
import warnings
from collections import Counter
from collections.abc import Sequence
from enum import StrEnum
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Annotated, ClassVar, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictInt, model_validator

from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    CheckState,
    CIReasonCode,
    Criterion,
    CriterionSource,
    EvidenceLevel,
    EvidenceType,
    FindingStatus,
    GateVerdict,
    LineChangeType,
    Priority,
)


def validate_r002_logical_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError("invalid R-002 logical path")
    return value


def validate_r002_source_span(value: str) -> str:
    match = re.fullmatch(r"problem_statement:L([1-9]\d*)-L([1-9]\d*)", value)
    if match is None or int(match.group(1)) > int(match.group(2)) or len(value) > 64:
        raise ValueError("invalid R-002 source span")
    return value


R002CaseId = Annotated[str, Field(pattern=r"^R002-\d{3}$")]
GitSha = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
R002LogicalPath = Annotated[
    str, Field(min_length=1, max_length=512), AfterValidator(validate_r002_logical_path)
]
R002SourceSpan = Annotated[str, AfterValidator(validate_r002_source_span)]


class R002DiffStream(StrEnum):
    PATCH = "patch"
    TEST_PATCH = "test_patch"


class R002MetricState(StrEnum):
    VALUE = "value"
    NOT_APPLICABLE = "not_applicable"


class R002RequestKind(StrEnum):
    DATASET = "dataset"
    PR_METADATA = "pr_metadata"
    HEAD_FILE = "head_file"


R002_REQUEST_LIMITS = {
    R002RequestKind.DATASET: 4,
    R002RequestKind.PR_METADATA: 20,
    R002RequestKind.HEAD_FILE: 128,
}
R002_COMMAND_FAILURE_CODES = (
    "source_manifest_missing",
    "criteria_missing",
    "labels_missing",
    "prepared_cache_missing",
    "criteria_not_confirmed",
    "labels_not_confirmed",
    "input_validation_failed",
    "network_policy_failed",
    "network_unavailable",
    "source_integrity_failed",
    "preparation_integrity_failed",
    "annotation_required",
    "reannotation_required",
    "benchmark_gate_failed",
    "filesystem_failed",
    "internal_error",
)
R002_RESULT_LIMITATIONS = (
    "Criteria and relevance labels are benchmark-owner research judgements, "
    "not source-owner confirmation.",
    "Only static historical diff and immutable PR-head evidence was evaluated.",
    "No target code or tests were executed and current CI was not observed.",
    "Candidate evidence does not prove correctness or criterion satisfaction.",
    "R-002 is engineering evidence only and contributes zero Stage 1 validation credit.",
)
R002_ANNOTATION_UNIVERSE_MAX_BYTES = 256 * 1024 * 1024
R002_ANNOTATION_REVIEW_MAX_BYTES = 512 * 1024 * 1024
R002_REDACTION_RAW_VALUE_MAX_BYTES = 1024 * 1024 * 1024
R002_REDACTION_TRACKED_FILE_MAX_BYTES = 512 * 1024 * 1024
R002_STATIC_EVIDENCE_TYPES = (
    EvidenceType.IMPLEMENTATION,
    EvidenceType.TEST,
    EvidenceType.DOCUMENTATION,
    EvidenceType.CONTRACT,
)
R002_SCHEMA = (
    "repo",
    "instance_id",
    "base_commit",
    "patch",
    "test_patch",
    "problem_statement",
    "hints_text",
    "created_at",
    "version",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "environment_setup_commit",
    "difficulty",
)
R002_SOURCE: dict[str, object] = {
    "dataset_id": "SWE-bench/SWE-bench_Verified",
    "config": "default",
    "split": "test",
    "revision": "91aa3ed51b709be6457e12d00300a6a596d4c6a3",
    "source_url": "https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/resolve/91aa3ed51b709be6457e12d00300a6a596d4c6a3/data/test-00000-of-00001.parquet",
    "parquet_path": "data/test-00000-of-00001.parquet",
    "byte_length": 2_090_470,
    "sha256": "43ed5a3d1d98da36472c1ade65ddd2085d7b4ff694fcaf6a023a07c5c1f32f21",
    "row_count": 500,
    "repository_count": 12,
    "unique_instance_count": 500,
    "schema": list(R002_SCHEMA),
}
R002_APPROVED_CASES_SHA256 = "ef091bb60e78abf9311112ff434f9e80613438915db198662aecd5f469cee336"


class R002StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class R002Error(Exception):
    allowed_reason_codes: ClassVar[frozenset[str]]

    def __init__(self, reason_code: str) -> None:
        if reason_code not in self.allowed_reason_codes:
            raise RuntimeError("unregistered R-002 reason code")
        self.reason_code = reason_code
        super().__init__(reason_code)


class R002SourceError(R002Error):
    allowed_reason_codes = frozenset({"source_pin_mismatch", "approved_cohort_mismatch"})


class R002AnnotationError(R002Error):
    allowed_reason_codes = frozenset({"criteria_manifest_drift", "candidate_label_upstream_drift"})


class R002Manifest(R002StrictModel):
    pack_id: Literal["R-002"] = "R-002"
    classification: Literal["public_engineering_research"] = "public_engineering_research"
    eligible_for_stage_1: Literal[False] = False
    does_not_advance_stage_1: Literal[True] = True
    target_repository_code_executed: Literal[False] = False


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message='Field name "schema".*', category=UserWarning)

    class SWEbenchSourcePin(R002StrictModel):
        dataset_id: str = Field(min_length=1)
        config: str = Field(min_length=1)
        split: str = Field(min_length=1)
        revision: GitSha
        source_url: str = Field(pattern=r"^https://huggingface\.co/.+\.parquet$")
        parquet_path: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.parquet$")
        byte_length: StrictInt = Field(gt=0)
        sha256: Sha256
        row_count: StrictInt = Field(gt=0)
        repository_count: StrictInt = Field(gt=0)
        unique_instance_count: StrictInt = Field(gt=0)
        schema: tuple[str, ...] = Field(min_length=1)


class R002CaseManifest(R002StrictModel):
    case_id: R002CaseId
    instance_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+-\d+$")
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    pr_url: str = Field(pattern=r"^https://github\.com/.+/.+/pull/\d+$")
    dataset_base_commit: GitSha
    verified_pr_head_sha: GitSha
    row_index: StrictInt = Field(ge=0, lt=500)
    difficulty: str = Field(min_length=1, max_length=64)
    row_sha256: Sha256
    problem_statement_sha256: Sha256
    patch_sha256: Sha256
    test_patch_sha256: Sha256

    @model_validator(mode="after")
    def bind_identity(self) -> Self:
        expected_instance = self.repository.replace("/", "__") + f"-{self.pr_number}"
        expected_url = f"https://github.com/{self.repository}/pull/{self.pr_number}"
        if self.instance_id != expected_instance or self.pr_url != expected_url:
            raise ValueError("case identity fields disagree")
        return self


class R002SourceManifest(R002Manifest):
    source: SWEbenchSourcePin
    cases: tuple[R002CaseManifest, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def validate_cohort(self) -> Self:
        expected_ids = [f"R002-{number:03d}" for number in range(1, 21)]
        if [case.case_id for case in self.cases] != expected_ids:
            raise ValueError("case IDs must be consecutive R002-001 through R002-020")
        if list(self.cases) != sorted(
            self.cases, key=lambda case: (case.repository, case.instance_id)
        ):
            raise ValueError("cases must be ordered by repository and instance ID")
        for values, label in (
            ([case.instance_id for case in self.cases], "instance IDs"),
            ([case.pr_url for case in self.cases], "PR URLs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        counts = Counter(case.repository for case in self.cases)
        if len(counts) != 12 or max(counts.values()) > 2:
            raise ValueError("cohort must cover 12 repositories with at most two cases each")
        return self


class SWEbenchVerifiedRow(R002StrictModel):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    FAIL_TO_PASS: str
    PASS_TO_PASS: str
    environment_setup_commit: str
    difficulty: str

    @model_validator(mode="after")
    def validate_bounded_content(self) -> Self:
        if len(canonical_json_bytes(self)) > 1024 * 1024:
            raise ValueError("verified row exceeds one MiB")
        if len(self.problem_statement.encode()) > 128 * 1024 or any(
            len(value.encode()) > 512 * 1024 for value in (self.patch, self.test_patch)
        ):
            raise ValueError("verified row content exceeds R-002 bounds")
        return self


class SWEbenchCriteriaSourceRow(R002StrictModel):
    repo: str
    instance_id: str
    base_commit: str
    problem_statement: str
    difficulty: str


class R002DiffLimits(R002StrictModel):
    files: Literal[32] = 32
    hunks: Literal[256] = 256
    diff_lines: Literal[50000] = 50000
    path_characters: Literal[512] = 512
    line_bytes: Literal[65536] = 65536


class R002HeadFileLimits(R002StrictModel):
    bytes_per_file: Literal[4194304] = 4194304
    bytes_per_case: Literal[16777216] = 16777216
    bytes_per_pack: Literal[134217728] = 134217728
    request_count: Literal[128] = 128


class R002ParsedLine(R002StrictModel):
    change_type: LineChangeType
    old_line_number: StrictInt | None = Field(default=None, ge=1)
    new_line_number: StrictInt | None = Field(default=None, ge=1)
    content: str
    normalized_line_sha256: Sha256

    @model_validator(mode="after")
    def validate_marker_numbers(self) -> Self:
        expected = {
            LineChangeType.ADDED: (False, True),
            LineChangeType.REMOVED: (True, False),
            LineChangeType.CONTEXT: (True, True),
        }[self.change_type]
        actual = (self.old_line_number is not None, self.new_line_number is not None)
        if actual != expected:
            raise ValueError("parsed line numbers must match its change marker")
        return self


class R002ParsedHunk(R002StrictModel):
    hunk_id: StrictInt = Field(ge=1)
    old_start: StrictInt = Field(ge=1)
    old_count: StrictInt = Field(ge=0)
    new_start: StrictInt = Field(ge=1)
    new_count: StrictInt = Field(ge=0)
    lines: tuple[R002ParsedLine, ...] = Field(max_length=50000)

    @model_validator(mode="after")
    def reconstruct_counts_and_line_numbers(self) -> Self:
        old_number = self.old_start
        new_number = self.new_start
        for line in self.lines:
            if line.old_line_number is not None:
                if line.old_line_number != old_number:
                    raise ValueError("parsed hunk old line numbers must be consecutive")
                old_number += 1
            if line.new_line_number is not None:
                if line.new_line_number != new_number:
                    raise ValueError("parsed hunk new line numbers must be consecutive")
                new_number += 1
        if (
            self.old_count != old_number - self.old_start
            or self.new_count != new_number - self.new_start
        ):
            raise ValueError("parsed hunk counts must match its lines")
        return self


class R002ParsedFile(R002StrictModel):
    stream: R002DiffStream
    path: R002LogicalPath
    hunks: tuple[R002ParsedHunk, ...] = Field(max_length=256)
    additions: StrictInt = Field(ge=0)
    deletions: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def reconstruct_counts_and_order(self) -> Self:
        if any(hunk.hunk_id != number for number, hunk in enumerate(self.hunks, start=1)):
            raise ValueError("parsed file hunk IDs must be ordered and consecutive")
        starts = [(hunk.old_start, hunk.new_start) for hunk in self.hunks]
        if starts != sorted(starts):
            raise ValueError("parsed file hunks must be stably ordered")
        additions = sum(
            line.change_type is LineChangeType.ADDED for hunk in self.hunks for line in hunk.lines
        )
        deletions = sum(
            line.change_type is LineChangeType.REMOVED for hunk in self.hunks for line in hunk.lines
        )
        if self.additions != additions or self.deletions != deletions:
            raise ValueError("parsed file counts must match its hunks")
        return self


class R002ParsedDiff(R002StrictModel):
    stream: R002DiffStream
    files: tuple[R002ParsedFile, ...] = Field(max_length=32)
    file_count: StrictInt = Field(ge=0)
    hunk_count: StrictInt = Field(ge=0)
    diff_line_count: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def reconstruct_counts_and_order(self) -> Self:
        paths = [item.path for item in self.files]
        if any(item.stream is not self.stream for item in self.files):
            raise ValueError("parsed diff files must match the diff stream")
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("parsed diff paths must be sorted and unique")
        expected = (
            len(self.files),
            sum(len(item.hunks) for item in self.files),
            sum(len(hunk.lines) for item in self.files for hunk in item.hunks),
        )
        if (self.file_count, self.hunk_count, self.diff_line_count) != expected:
            raise ValueError("parsed diff counts must match its files")
        return self


class R002ParsedCase(R002StrictModel):
    case_id: R002CaseId
    files: tuple[R002ParsedFile, ...] = Field(max_length=64)
    file_count: StrictInt = Field(ge=0)
    hunk_count: StrictInt = Field(ge=0)
    diff_line_count: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def reconstruct_counts_and_stream_separation(self) -> Self:
        keys = [(item.stream.value, item.path) for item in self.files]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("parsed case files must be sorted and unique")
        patch_paths = {item.path for item in self.files if item.stream is R002DiffStream.PATCH}
        test_paths = {item.path for item in self.files if item.stream is R002DiffStream.TEST_PATCH}
        if patch_paths & test_paths:
            raise ValueError("patch and test_patch paths must remain distinguishable")
        expected = (
            len(self.files),
            sum(len(item.hunks) for item in self.files),
            sum(len(hunk.lines) for item in self.files for hunk in item.hunks),
        )
        if (self.file_count, self.hunk_count, self.diff_line_count) != expected:
            raise ValueError("parsed case counts must match its files")
        return self


class R002VerifiedLine(R002StrictModel):
    stream: R002DiffStream
    path: R002LogicalPath
    hunk_id: StrictInt = Field(ge=1)
    new_line_number: StrictInt = Field(ge=1)
    normalized_line_sha256: Sha256
    head_file_sha256: Sha256
    head_sha: GitSha
    permalink: str = Field(pattern=r"^https://github\.com/.+/blob/[0-9a-f]{40}/.+#L\d+$")


class R002VerifiedCaseLines(R002StrictModel):
    case_id: R002CaseId
    head_sha: GitSha
    lines: tuple[R002VerifiedLine, ...]

    def by_path_and_line(self, path: str, number: int) -> R002VerifiedLine:
        matches = [
            line for line in self.lines if line.path == path and line.new_line_number == number
        ]
        if len(matches) != 1:
            raise ValueError("verified line must match exactly once")
        return matches[0]


class R002CachedHeadFile(R002StrictModel):
    logical_path: R002LogicalPath
    head_sha: GitSha
    byte_length: StrictInt = Field(ge=0, le=4194304)
    content_sha256: Sha256


class R002CachedCase(R002StrictModel):
    case_id: R002CaseId
    row_sha256: Sha256
    problem_statement_sha256: Sha256
    patch_sha256: Sha256
    test_patch_sha256: Sha256
    parsed_case_sha256: Sha256
    verified_lines: tuple[R002VerifiedLine, ...]
    head_files: tuple[R002CachedHeadFile, ...]


class R002CriteriaSourceCase(R002StrictModel):
    case_id: R002CaseId
    problem_statement_sha256: Sha256
    byte_length: StrictInt = Field(ge=1)


class R002CriteriaSourceIndex(R002Manifest):
    source_sha256: Sha256
    manifest_sha256: Sha256
    complete: Literal[True] = True
    cases: tuple[R002CriteriaSourceCase, ...] = Field(min_length=20, max_length=20)


class R002CacheIndex(R002Manifest):
    source_sha256: Sha256
    manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    complete: Literal[True] = True
    cases: tuple[R002CachedCase, ...] = Field(min_length=20, max_length=20)


class R002CriteriaSourcePreparationResult(R002Manifest):
    phase: Literal["criteria_sources"]
    complete: Literal[True]
    executed_case_count: StrictInt = Field(ge=0)
    failed_case_count: StrictInt = Field(ge=0)
    skipped_case_count: StrictInt = Field(ge=0)
    case_ids: tuple[R002CaseId, ...] = Field(min_length=20, max_length=20)
    errors: tuple[str, ...]
    hard_gate_errors: tuple[str, ...]


class R002PreparationCaseResult(R002StrictModel):
    case_id: R002CaseId
    status: Literal["prepared"]
    head_file_count: StrictInt = Field(ge=0)
    candidate_line_count: StrictInt = Field(ge=0)


class R002PreparationResult(R002Manifest):
    phase: Literal["evidence"]
    complete: Literal[True]
    criteria_set_sha256: Sha256
    executed_case_count: StrictInt = Field(ge=0)
    failed_case_count: StrictInt = Field(ge=0)
    skipped_case_count: StrictInt = Field(ge=0)
    head_file_count: StrictInt = Field(ge=0)
    candidate_line_count: StrictInt = Field(ge=0)
    cases: tuple[R002PreparationCaseResult, ...] = Field(min_length=20, max_length=20)
    errors: tuple[str, ...]
    hard_gate_errors: tuple[str, ...]


class R002CommandFailure(R002Manifest):
    ok: Literal[False] = False
    operation_failed: Literal[True] = True
    command: Literal["prepare", "annotate", "run"]
    reason_code: Literal[
        "source_manifest_missing",
        "criteria_missing",
        "labels_missing",
        "prepared_cache_missing",
        "criteria_not_confirmed",
        "labels_not_confirmed",
        "input_validation_failed",
        "network_policy_failed",
        "network_unavailable",
        "source_integrity_failed",
        "preparation_integrity_failed",
        "annotation_required",
        "reannotation_required",
        "benchmark_gate_failed",
        "filesystem_failed",
        "internal_error",
    ]
    errors: tuple[str, ...] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def bind_error_code(self) -> Self:
        if self.errors != (self.reason_code,):
            raise ValueError("command failure errors must contain only the stable reason code")
        return self


class R002RedactionAudit(R002Manifest):
    passed: Literal[True] = True
    tracked_file_count: StrictInt = Field(ge=0)
    raw_value_count: StrictInt = Field(ge=0)
    checked_value_sha256: tuple[Sha256, ...]


class R002CriterionCase(R002StrictModel):
    case_id: R002CaseId
    problem_statement_sha256: Sha256
    criteria: tuple[Criterion, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="before")
    @classmethod
    def require_complete_serialized_criteria(cls, value: object) -> object:
        if not isinstance(value, dict) or not isinstance(value.get("criteria"), (list, tuple)):
            return value
        required_fields = {
            "criterion_id",
            "text",
            "priority",
            "criterion_type",
            "criterion_source",
            "source_span",
            "required_evidence_level",
        }
        for criterion in value["criteria"]:
            fields = (
                set(criterion.model_fields_set)
                if isinstance(criterion, Criterion)
                else set(criterion)
                if isinstance(criterion, dict)
                else set()
            )
            if fields != required_fields:
                raise ValueError("R-002 criteria require complete serialized fields")
        # JSON arrays are the canonical serialization of persisted tuples. Preserve
        # strict scalar validation while reconstructing this collection boundary.
        return {**value, "criteria": tuple(value["criteria"])}

    @model_validator(mode="after")
    def validate_criteria(self) -> Self:
        ids = [item.criterion_id for item in self.criteria]
        if ids != [f"AC-{number:02d}" for number in range(1, len(ids) + 1)]:
            raise ValueError("criterion IDs must be ordered and consecutive")
        if not any(item.priority is Priority.MUST_HAVE for item in self.criteria):
            raise ValueError("every case requires at least one MUST_HAVE criterion")
        if any(
            item.criterion_source is not CriterionSource.USER_CONFIRMED for item in self.criteria
        ):
            raise ValueError("R-002 criteria must use the operator-confirmed source value")
        if any(
            item.source_span is None
            or validate_r002_source_span(item.source_span) != item.source_span
            for item in self.criteria
        ):
            raise ValueError("every R-002 criterion requires a bounded problem-statement span")
        if any(
            len(item.text) > 512 or "\n" in item.text or "\r" in item.text for item in self.criteria
        ):
            raise ValueError("R-002 criteria must be bounded single-line paraphrases")
        return self


class R002CriterionReviewCase(R002CriterionCase):
    problem_statement: str = Field(min_length=1, max_length=131072)


def _validate_criteria_cases(cases: Sequence[R002CriterionCase]) -> None:
    ids = [case.case_id for case in cases]
    hashes = [case.problem_statement_sha256 for case in cases]
    if ids != [f"R002-{number:03d}" for number in range(1, 21)]:
        raise ValueError("criteria cases must be ordered and complete")
    if len(hashes) != len(set(hashes)):
        raise ValueError("criteria cases require complete unique problem hashes")


class _CriteriaCollection(R002Manifest):
    source_manifest_sha256: Sha256
    cases: tuple[R002CriterionCase, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def bind_cases(self) -> Self:
        _validate_criteria_cases(self.cases)
        return self


class R002CriteriaProposal(R002Manifest):
    source_manifest_sha256: Sha256
    source_owner_confirmed: Literal[False] = False
    benchmark_owner_confirmed: Literal[False] = False
    cases: tuple[R002CriterionReviewCase, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def bind_cases(self) -> Self:
        _validate_criteria_cases(self.cases)
        return self


class R002CriteriaSet(_CriteriaCollection):
    source_owner_confirmed: Literal[False] = False
    benchmark_owner_confirmed: Literal[True]


class R002CandidateLineKey(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=r"^AC-\d{2,}$")
    stream: R002DiffStream
    path: R002LogicalPath
    new_line_number: StrictInt = Field(ge=1)
    normalized_line_sha256: Sha256


class R002CandidateLabel(R002StrictModel):
    key: R002CandidateLineKey
    relevant: bool
    reason_code: Literal[
        "direct_static_candidate",
        "supporting_static_candidate",
        "test_intent_candidate",
        "unrelated_candidate",
        "insufficient_context",
    ]

    @model_validator(mode="after")
    def bind_reason_to_relevance(self) -> Self:
        true_codes = {
            "direct_static_candidate",
            "supporting_static_candidate",
            "test_intent_candidate",
        }
        if self.relevant != (self.reason_code in true_codes):
            raise ValueError("candidate reason code must agree with relevance")
        if (
            self.reason_code == "test_intent_candidate"
            and self.key.stream is not R002DiffStream.TEST_PATCH
        ):
            raise ValueError("test intent candidates require test_patch stream")
        return self


class R002ExpectedMissing(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=r"^AC-\d{2,}$")
    evidence_type: Literal[
        EvidenceType.IMPLEMENTATION,
        EvidenceType.TEST,
        EvidenceType.DOCUMENTATION,
        EvidenceType.CONTRACT,
    ]
    reason_code: Literal["no_owner_labelled_relevant_candidate"]


class R002AnnotationUniverse(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    candidate_count: StrictInt = Field(ge=1, le=250000)
    candidate_keys: tuple[R002CandidateLineKey, ...] = Field(min_length=1, max_length=250000)

    @model_validator(mode="after")
    def bind_keys(self) -> Self:
        keys = [canonical_json_bytes(key) for key in self.candidate_keys]
        if self.candidate_count != len(keys) or len(keys) != len(set(keys)) or keys != sorted(keys):
            raise ValueError("annotation keys must be sorted, unique, and complete")
        return self


class R002AnnotationReviewItem(R002StrictModel):
    key: R002CandidateLineKey
    line_content: str
    previous_line: str | None = None
    next_line: str | None = None
    relevant: bool | None = None
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_line_bounds(self) -> Self:
        if any(
            value is not None and len(value.encode()) > 65536
            for value in (self.line_content, self.previous_line, self.next_line)
        ):
            raise ValueError("annotation review lines must not exceed 64 KiB")
        return self


class R002AnnotationReview(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    annotation_universe_sha256: Sha256
    items: tuple[R002AnnotationReviewItem, ...]


class _LabelCollection(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    annotation_universe_sha256: Sha256
    annotation_count: StrictInt = Field(ge=1, le=250000)
    labels: tuple[R002CandidateLabel, ...] = Field(min_length=1, max_length=250000)
    expected_missing: tuple[R002ExpectedMissing, ...]

    @model_validator(mode="after")
    def bind_labels(self) -> Self:
        keys = [canonical_json_bytes(label.key) for label in self.labels]
        if (
            self.annotation_count != len(keys)
            or len(keys) != len(set(keys))
            or keys != sorted(keys)
        ):
            raise ValueError("labels must be sorted, unique, and complete")
        missing = {
            (item.case_id, item.criterion_id, item.evidence_type) for item in self.expected_missing
        }
        if len(missing) != len(self.expected_missing):
            raise ValueError("expected missing records must be unique")
        expected_pairs = {
            (label.key.case_id, label.key.criterion_id)
            for label in self.labels
            if not label.relevant
            and not any(
                other.key.case_id == label.key.case_id
                and other.key.criterion_id == label.key.criterion_id
                and other.relevant
                for other in self.labels
            )
        }
        expected_records = {
            (case_id, criterion_id, evidence_type)
            for case_id, criterion_id in expected_pairs
            for evidence_type in R002_STATIC_EVIDENCE_TYPES
        }
        if missing != expected_records:
            raise ValueError("expected missing records must be derived from labels")
        return self


class R002CandidateLabelProposal(_LabelCollection):
    benchmark_owner_confirmed: Literal[False] = False


class R002CandidateLabelSet(_LabelCollection):
    benchmark_owner_confirmed: Literal[True]


class R002Metric(R002StrictModel):
    state: R002MetricState
    numerator: StrictInt = Field(ge=0)
    denominator: StrictInt = Field(ge=0)
    value: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_ratio(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("metric numerator cannot exceed denominator")
        if self.denominator == 0:
            if self.state is not R002MetricState.NOT_APPLICABLE or self.value is not None:
                raise ValueError("zero denominator must be not_applicable")
        elif (
            self.state is not R002MetricState.VALUE
            or self.value != self.numerator / self.denominator
        ):
            raise ValueError("nonzero denominator must report the exact ratio")
        return self


class R002RetrievedCandidate(R002StrictModel):
    key: R002CandidateLineKey
    evidence_type: EvidenceType
    evidence_level: EvidenceLevel
    hunk_id: StrictInt = Field(ge=1)
    head_file_sha256: Sha256
    matching_rule: str = Field(min_length=1)
    relevance_score: float = Field(ge=0, le=1)
    owner_label_relevant: bool


class R002MissingExplanation(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=r"^AC-\d{2,}$")
    evidence_type: EvidenceType
    source: Literal["scopeproof_finding", "r002_retrieval_comparison"]
    finding_status: FindingStatus
    reason_code: str = Field(min_length=1)


class R002CaseResult(R002StrictModel):
    case_id: R002CaseId
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    head_sha: GitSha
    criterion_count: StrictInt = Field(ge=0)
    annotation_candidate_count: StrictInt = Field(ge=0)
    retrieved_candidates: tuple[R002RetrievedCandidate, ...]
    missing_explanations: tuple[R002MissingExplanation, ...]
    gate_verdict: GateVerdict
    gate_reason_codes: tuple[str, ...]
    blocking_criteria: tuple[str, ...]
    conditional_criteria: tuple[str, ...]
    unresolved_criteria: tuple[str, ...]
    check_state: CheckState
    ci_reason_code: CIReasonCode
    runtime_evidence_count: StrictInt = Field(ge=0)
    resolution_count: StrictInt = Field(ge=0)
    final_acceptance: bool
    separation_errors: StrictInt = Field(ge=0)
    reference_errors: StrictInt = Field(ge=0)
    limitations: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_non_static_success_signals(self) -> Self:
        criterion_groups = (
            self.blocking_criteria,
            self.conditional_criteria,
            self.unresolved_criteria,
        )
        if self.gate_verdict not in {GateVerdict.BLOCKED, GateVerdict.NEEDS_REVIEW}:
            raise ValueError("R-002 case results must be blocked or needs_review")
        if (
            not self.gate_reason_codes
            or tuple(sorted(set(self.gate_reason_codes))) != self.gate_reason_codes
            or any(not re.fullmatch(r"[a-z0-9_]+", code) for code in self.gate_reason_codes)
        ):
            raise ValueError("gate reason codes must be sorted stable codes")
        if any(
            tuple(sorted(set(group))) != group
            or any(re.fullmatch(r"AC-\d{2,}", item) is None for item in group)
            for group in criterion_groups
        ):
            raise ValueError("criterion groups must be sorted unique criterion IDs")
        if self.gate_verdict is GateVerdict.BLOCKED and not (
            self.blocking_criteria or self.unresolved_criteria
        ):
            raise ValueError("blocked R-002 cases require unresolved criteria")
        if self.gate_verdict is GateVerdict.NEEDS_REVIEW and not (
            self.conditional_criteria or self.unresolved_criteria
        ):
            raise ValueError("needs_review R-002 cases require unresolved criteria")
        if self.check_state is not CheckState.UNAVAILABLE:
            raise ValueError("R-002 case results require unavailable CI")
        if (
            self.runtime_evidence_count != 0
            or self.resolution_count != 0
            or self.final_acceptance
            or self.separation_errors != 0
            or self.reference_errors != 0
        ):
            raise ValueError("R-002 case results cannot contain success or integrity signals")
        if self.limitations != R002_RESULT_LIMITATIONS:
            raise ValueError("R-002 case results require the fixed limitations")
        if any(
            candidate.evidence_level not in {EvidenceLevel.E1, EvidenceLevel.E2}
            or candidate.evidence_type not in R002_STATIC_EVIDENCE_TYPES
            for candidate in self.retrieved_candidates
        ):
            raise ValueError("R-002 candidates must be static E1 or E2 evidence")
        if any(
            item.evidence_type not in R002_STATIC_EVIDENCE_TYPES
            for item in self.missing_explanations
        ):
            raise ValueError("R-002 missing explanations must be static evidence types")
        return self


class R002Metrics(R002StrictModel):
    precision: R002Metric
    recall: R002Metric
    f1: R002Metric
    implementation_precision: R002Metric
    test_precision: R002Metric
    implementation_test_separation_errors: StrictInt = Field(ge=0)
    immutable_reference_integrity_errors: StrictInt = Field(ge=0)
    parse_errors: StrictInt = Field(ge=0)
    schema_errors: StrictInt = Field(ge=0)
    source_hash_errors: StrictInt = Field(ge=0)
    source_sha_errors: StrictInt = Field(ge=0)
    unexpected_ready_count: StrictInt = Field(ge=0)
    normalized_rerun_mismatches: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def require_zero_integrity_errors(self) -> Self:
        error_counts = (
            self.implementation_test_separation_errors,
            self.immutable_reference_integrity_errors,
            self.parse_errors,
            self.schema_errors,
            self.source_hash_errors,
            self.source_sha_errors,
            self.unexpected_ready_count,
            self.normalized_rerun_mismatches,
        )
        if any(error_counts):
            raise ValueError("successful R-002 metrics require zero integrity errors")
        return self


class R002DeterminismProjection(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    candidate_labels_sha256: Sha256
    scopeproof_commit: GitSha
    case_results: tuple[R002CaseResult, ...] = Field(min_length=20, max_length=20)
    metrics: R002Metrics
    limitations: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def bind_safe_case_results(self) -> Self:
        ids = [result.case_id for result in self.case_results]
        if ids != [f"R002-{number:03d}" for number in range(1, 21)]:
            raise ValueError("R-002 case results must be ordered and complete")
        if self.limitations != R002_RESULT_LIMITATIONS:
            raise ValueError("R-002 projections require the fixed limitations")
        return self


class R002BenchmarkResult(R002DeterminismProjection):
    executed_case_count: StrictInt = Field(ge=0)
    failed_case_count: StrictInt = Field(ge=0)
    skipped_case_count: StrictInt = Field(ge=0)
    confirmed_criterion_count: StrictInt = Field(ge=0)
    annotation_candidate_count: StrictInt = Field(ge=0)
    unexpected_ready_count: StrictInt = Field(ge=0)
    normalized_rerun_mismatches: StrictInt = Field(ge=0)
    hard_gate_errors: tuple[str, ...]

    @model_validator(mode="after")
    def require_successful_run_boundary(self) -> Self:
        if (
            self.executed_case_count != 20
            or self.failed_case_count != 0
            or self.skipped_case_count != 0
            or self.confirmed_criterion_count
            != sum(item.criterion_count for item in self.case_results)
            or self.annotation_candidate_count
            != sum(item.annotation_candidate_count for item in self.case_results)
            or self.unexpected_ready_count != self.metrics.unexpected_ready_count
            or self.normalized_rerun_mismatches != self.metrics.normalized_rerun_mismatches
            or self.hard_gate_errors
        ):
            raise ValueError("R-002 benchmark result violates the successful-run boundary")
        return self


def canonical_json_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_sha256(value: BaseModel | dict[str, object]) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def case_projection_sha256(cases: Sequence[R002CaseManifest]) -> str:
    payload = [case.model_dump(mode="json") for case in cases]
    return sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def load_source_manifest(path: Path) -> R002SourceManifest:
    value = R002SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if value.source.model_dump(mode="json") != R002_SOURCE:
        raise R002SourceError("source_pin_mismatch")
    if case_projection_sha256(value.cases) != R002_APPROVED_CASES_SHA256:
        raise R002SourceError("approved_cohort_mismatch")
    return value


def load_confirmed_criteria(path: Path, manifest_sha256: str) -> R002CriteriaSet:
    value = R002CriteriaSet.model_validate_json(path.read_text(encoding="utf-8"))
    if value.source_manifest_sha256 != manifest_sha256:
        raise R002AnnotationError("criteria_manifest_drift")
    return value


def load_confirmed_labels(
    path: Path, manifest_sha256: str, criteria_sha256: str
) -> R002CandidateLabelSet:
    value = R002CandidateLabelSet.model_validate_json(path.read_text(encoding="utf-8"))
    if (
        value.source_manifest_sha256 != manifest_sha256
        or value.criteria_set_sha256 != criteria_sha256
    ):
        raise R002AnnotationError("candidate_label_upstream_drift")
    return value
