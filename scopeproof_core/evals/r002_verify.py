"""Fail-closed immutable PR-head references for R-002 static candidates."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import NoReturn
from urllib.parse import quote

from scopeproof_core.evals.r002_models import (
    R002CandidateLineKey,
    R002CaseManifest,
    R002DiffStream,
    R002Error,
    R002HeadFileLimits,
    R002ParsedCase,
    R002ParsedFile,
    R002ParsedHunk,
    R002ParsedLine,
    R002VerifiedCaseLines,
    R002VerifiedLine,
    validate_r002_logical_path,
)
from scopeproof_core.retrieval.engine import classify_changed_path_evidence_type
from scopeproof_core.schemas.models import (
    EvidenceItem,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    LineChangeType,
)

DEFAULT_R002_HEAD_LIMITS = R002HeadFileLimits()
_MAX_R002_LOGICAL_PATH_CHARACTERS = 512
_MAX_R002_PARSED_FILES = 32
_MAX_R002_PARSED_HUNKS = 256
_MAX_R002_PARSED_LINES = 50_000
_MAX_R002_VERIFIED_LINES = 50_000
_MAX_R002_HUNK_ID_CHARACTERS = 1024
_MAX_R002_LINE_BYTES = 65_536
_MAX_R002_HUNK_START = 2_147_483_647


class R002ReferenceError(R002Error):
    """A stable, deliberately non-diagnostic immutable-reference error."""

    allowed_reason_codes = frozenset(
        {
            "case_identity_mismatch",
            "evidence_head_mismatch",
            "evidence_level_mismatch",
            "evidence_not_in_verified_universe",
            "evidence_permalink_mismatch",
            "evidence_source_scope_mismatch",
            "evidence_type_mismatch",
            "head_case_limit",
            "head_file_limit",
            "head_file_missing",
            "head_file_not_utf8",
            "head_line_mismatch",
            "head_line_out_of_range",
            "head_mapping_invalid",
            "model_validation_failed",
            "permalink_input_invalid",
            "stream_path_collision",
            "test_stream_not_test_evidence",
            "verified_case_mismatch",
            "verified_duplicate_identity",
            "verified_head_mismatch",
            "verified_permalink_mismatch",
            "verified_repository_mismatch",
        }
    )


def _fresh_reference_error(reason: str) -> R002ReferenceError:
    """Create an error after an input-bearing failure has been discarded."""
    return R002ReferenceError(reason)


def _raise_public_reference_error(reason: str) -> NoReturn:
    """Raise only a fresh, stable reason after local inputs have unwound."""
    raise R002ReferenceError(reason)


def _trusted_python_dump(model_type: type[object], instance: object) -> object:
    """Serialize through the fixed class schema, never an instance attribute."""
    serializer = type.__getattribute__(model_type, "__pydantic_serializer__")
    return serializer.to_python(instance, mode="python", warnings="error")


def _validated_case_snapshot(
    case: R002CaseManifest, *, reason: str
) -> R002CaseManifest:
    if type(case) is not R002CaseManifest:
        raise R002ReferenceError(reason)
    try:
        snapshot = R002CaseManifest.model_validate(
            _trusted_python_dump(R002CaseManifest, case), strict=True
        )
    except Exception:
        error = _fresh_reference_error(reason)
    else:
        error = None
    if error is not None:
        raise error
    return snapshot


def _validated_limits_snapshot(limits: R002HeadFileLimits) -> R002HeadFileLimits:
    if type(limits) is not R002HeadFileLimits:
        raise R002ReferenceError("model_validation_failed")
    try:
        snapshot = R002HeadFileLimits.model_validate(
            _trusted_python_dump(R002HeadFileLimits, limits), strict=True
        )
    except Exception:
        error = _fresh_reference_error("model_validation_failed")
    else:
        error = None
    if error is not None:
        raise error
    return snapshot


def _validated_evidence_snapshot(evidence: EvidenceItem) -> EvidenceItem:
    if type(evidence) is not EvidenceItem:
        raise R002ReferenceError("model_validation_failed")
    try:
        snapshot = EvidenceItem.model_validate(
            _trusted_python_dump(EvidenceItem, evidence), strict=True
        )
    except Exception:
        error = _fresh_reference_error("model_validation_failed")
    else:
        error = None
    if error is not None:
        raise error
    return snapshot


def _normalized_file_lines(raw: bytes, *, max_bytes: int) -> list[str]:
    if len(raw) > max_bytes:
        raise R002ReferenceError("head_file_limit")
    try:
        text = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("utf-8")
    except UnicodeDecodeError:
        error = _fresh_reference_error("head_file_not_utf8")
    else:
        error = None
    if error is not None:
        raise error
    values = text.split("\n")
    if values and values[-1] == "":
        values.pop()
    return values


def _validate_permalink_inputs(path: str, line_number: int) -> None:
    if type(path) is not str or type(line_number) is not int:
        raise R002ReferenceError("permalink_input_invalid")
    if line_number < 1 or len(path) > _MAX_R002_LOGICAL_PATH_CHARACTERS:
        raise R002ReferenceError("permalink_input_invalid")
    try:
        valid_path = validate_r002_logical_path(path)
    except ValueError:
        error = _fresh_reference_error("permalink_input_invalid")
    else:
        error = None
    if error is not None or valid_path != path:
        raise error or R002ReferenceError("permalink_input_invalid")


def _candidate_permalink_from_snapshot(
    case: R002CaseManifest, path: str, line_number: int
) -> str:
    _validate_permalink_inputs(path, line_number)
    repository = quote(case.repository, safe="/")
    head = quote(case.verified_pr_head_sha, safe="")
    logical_path = quote(path, safe="/")
    return (
        f"https://github.com/{repository}/blob/{head}/{logical_path}"
        f"#L{line_number}-L{line_number}"
    )


def _candidate_permalink(case: R002CaseManifest, path: str, line_number: int) -> str:
    snapshot = _validated_case_snapshot(case, reason="permalink_input_invalid")
    return _candidate_permalink_from_snapshot(snapshot, path, line_number)


def candidate_permalink(case: R002CaseManifest, path: str, line_number: int) -> str:
    """Return the sole canonical permalink form accepted by R-002."""
    try:
        return _candidate_permalink(case, path, line_number)
    except R002ReferenceError as caught:
        reason = caught.reason_code
    except Exception:
        reason = "permalink_input_invalid"
    del case, path, line_number
    _raise_public_reference_error(reason)


def _assert_test_stream_separation(parsed: R002ParsedCase) -> None:
    paths_by_stream: dict[str, set[str]] = {"patch": set(), "test_patch": set()}
    for file in parsed.files:
        stream_name = file.stream.value
        if stream_name not in paths_by_stream:
            raise R002ReferenceError("model_validation_failed")
        paths_by_stream[stream_name].add(file.path)
    if paths_by_stream["patch"] & paths_by_stream["test_patch"]:
        raise R002ReferenceError("stream_path_collision")
    for file in parsed.files:
        if file.stream.value == "test_patch" and (
            classify_changed_path_evidence_type(file.path) is not EvidenceType.TEST
        ):
            raise R002ReferenceError("test_stream_not_test_evidence")


def _prevalidate_parsed_shape(parsed: R002ParsedCase) -> None:
    if (
        type(parsed) is not R002ParsedCase
        or type(parsed.case_id) is not str
        or len(parsed.case_id) != 8
        or type(parsed.files) is not tuple
        or len(parsed.files) > _MAX_R002_PARSED_FILES
        or type(parsed.file_count) is not int
        or not 0 <= parsed.file_count <= _MAX_R002_PARSED_FILES
        or type(parsed.hunk_count) is not int
        or not 0 <= parsed.hunk_count <= _MAX_R002_PARSED_HUNKS
        or type(parsed.diff_line_count) is not int
        or not 0 <= parsed.diff_line_count <= _MAX_R002_PARSED_LINES
    ):
        raise R002ReferenceError("model_validation_failed")
    total_hunks = 0
    for file in parsed.files:
        if (
            type(file) is not R002ParsedFile
            or type(file.stream) is not R002DiffStream
            or type(file.path) is not str
            or not 1 <= len(file.path) <= _MAX_R002_LOGICAL_PATH_CHARACTERS
            or type(file.hunks) is not tuple
            or not 1 <= len(file.hunks) <= _MAX_R002_PARSED_HUNKS
            or type(file.additions) is not int
            or not 0 <= file.additions <= _MAX_R002_PARSED_LINES
            or type(file.deletions) is not int
            or not 0 <= file.deletions <= _MAX_R002_PARSED_LINES
        ):
            raise R002ReferenceError("model_validation_failed")
        try:
            valid_path = validate_r002_logical_path(file.path)
        except ValueError:
            error = _fresh_reference_error("model_validation_failed")
        else:
            error = None
        if error is not None or valid_path != file.path:
            raise error or R002ReferenceError("model_validation_failed")
        total_hunks += len(file.hunks)
        if total_hunks > _MAX_R002_PARSED_HUNKS:
            raise R002ReferenceError("model_validation_failed")

    total_lines = 0
    for file in parsed.files:
        for hunk in file.hunks:
            if (
                type(hunk) is not R002ParsedHunk
                or type(hunk.hunk_id) is not str
                or not 10 <= len(hunk.hunk_id) <= _MAX_R002_HUNK_ID_CHARACTERS
                or type(hunk.old_start) is not int
                or not 1 <= hunk.old_start <= _MAX_R002_HUNK_START
                or type(hunk.old_count) is not int
                or not 0 <= hunk.old_count <= _MAX_R002_PARSED_LINES
                or type(hunk.new_start) is not int
                or not 1 <= hunk.new_start <= _MAX_R002_HUNK_START
                or type(hunk.new_count) is not int
                or not 0 <= hunk.new_count <= _MAX_R002_PARSED_LINES
                or type(hunk.lines) is not tuple
                or len(hunk.lines) > _MAX_R002_PARSED_LINES
            ):
                raise R002ReferenceError("model_validation_failed")
            total_lines += len(hunk.lines)
            if total_lines > _MAX_R002_PARSED_LINES:
                raise R002ReferenceError("model_validation_failed")

    for file in parsed.files:
        for hunk in file.hunks:
            for line in hunk.lines:
                if (
                    type(line) is not R002ParsedLine
                    or type(line.change_type) is not LineChangeType
                    or (
                        line.old_line_number is not None
                        and (
                            type(line.old_line_number) is not int
                            or line.old_line_number < 1
                        )
                    )
                    or (
                        line.new_line_number is not None
                        and (
                            type(line.new_line_number) is not int
                            or line.new_line_number < 1
                        )
                    )
                    or type(line.content) is not str
                    or len(line.content) > _MAX_R002_LINE_BYTES
                    or type(line.normalized_line_sha256) is not str
                    or len(line.normalized_line_sha256) != 64
                ):
                    raise R002ReferenceError("model_validation_failed")
                try:
                    content_bytes = line.content.encode("utf-8")
                except UnicodeEncodeError:
                    error = _fresh_reference_error("model_validation_failed")
                else:
                    error = None
                if error is not None or len(content_bytes) > _MAX_R002_LINE_BYTES:
                    raise error or R002ReferenceError("model_validation_failed")


def _validated_parsed_snapshot(parsed: R002ParsedCase) -> R002ParsedCase:
    _prevalidate_parsed_shape(parsed)
    _assert_test_stream_separation(parsed)
    try:
        snapshot = R002ParsedCase.model_validate(
            _trusted_python_dump(R002ParsedCase, parsed), strict=True
        )
    except Exception:
        error = _fresh_reference_error("model_validation_failed")
    else:
        error = None
    if error is not None:
        raise error
    _assert_test_stream_separation(snapshot)
    return snapshot


def assert_test_stream_separation(parsed: R002ParsedCase) -> None:
    """Require test-patch paths to remain test evidence and streams disjoint."""
    error: R002ReferenceError | None = None
    try:
        _validated_parsed_snapshot(parsed)
    except R002ReferenceError as caught:
        error = _fresh_reference_error(caught.reason_code)
    except Exception:
        error = _fresh_reference_error("model_validation_failed")
    del parsed
    if error is not None:
        _raise_public_reference_error(error.reason_code)


def _validate_head_mapping(
    parsed: R002ParsedCase, head_file_bytes: Mapping[str, bytes]
) -> dict[str, bytes]:
    if not isinstance(head_file_bytes, Mapping):
        raise R002ReferenceError("head_mapping_invalid")
    required_paths = {file.path for file in parsed.files}
    max_entries = len(required_paths)
    try:
        items = iter(head_file_bytes.items())
        supplied: dict[str, bytes] = {}
        for index, item in enumerate(items):
            if index >= max_entries or type(item) is not tuple or len(item) != 2:
                raise R002ReferenceError("head_mapping_invalid")
            path, value = item
            if type(path) is not str or type(value) is not bytes or path in supplied:
                raise R002ReferenceError("head_mapping_invalid")
            if not 1 <= len(path) <= _MAX_R002_LOGICAL_PATH_CHARACTERS:
                raise R002ReferenceError("head_mapping_invalid")
            try:
                valid_path = validate_r002_logical_path(path)
            except ValueError:
                raise R002ReferenceError("head_mapping_invalid") from None
            if valid_path != path:
                raise R002ReferenceError("head_mapping_invalid")
            supplied[path] = value
    except Exception:
        error = _fresh_reference_error("head_mapping_invalid")
    else:
        error = None
    if error is not None:
        raise error
    supplied_paths = set(supplied)
    if required_paths - supplied_paths:
        raise R002ReferenceError("head_file_missing")
    if supplied_paths != required_paths:
        raise R002ReferenceError("head_mapping_invalid")
    return supplied


def _verify_case_head_files(
    *,
    case: R002CaseManifest,
    parsed: R002ParsedCase,
    head_file_bytes: Mapping[str, bytes],
    limits: R002HeadFileLimits,
) -> R002VerifiedCaseLines:
    case = _validated_case_snapshot(case, reason="model_validation_failed")
    parsed = _validated_parsed_snapshot(parsed)
    limits = _validated_limits_snapshot(limits)
    if case.case_id != parsed.case_id:
        raise R002ReferenceError("case_identity_mismatch")
    head_files = _validate_head_mapping(parsed, head_file_bytes)
    if sum(len(value) for value in head_files.values()) > limits.bytes_per_case:
        raise R002ReferenceError("head_case_limit")

    verified: list[R002VerifiedLine] = []
    for parsed_file in parsed.files:
        raw = head_files[parsed_file.path]
        lines = _normalized_file_lines(raw, max_bytes=limits.bytes_per_file)
        file_hash = sha256(raw).hexdigest()
        for hunk in parsed_file.hunks:
            for line in hunk.lines:
                if line.change_type is LineChangeType.REMOVED:
                    continue
                number = line.new_line_number
                if number is None or number > len(lines):
                    raise R002ReferenceError("head_line_out_of_range")
                head_content = lines[number - 1]
                if head_content != line.content:
                    raise R002ReferenceError("head_line_mismatch")
                verified.append(
                    R002VerifiedLine(
                        stream=parsed_file.stream,
                        path=parsed_file.path,
                        hunk_id=hunk.hunk_id,
                        new_line_number=number,
                        normalized_line_sha256=sha256(head_content.encode("utf-8")).hexdigest(),
                        head_file_sha256=file_hash,
                        head_sha=case.verified_pr_head_sha,
                        permalink=_candidate_permalink_from_snapshot(
                            case, parsed_file.path, number
                        ),
                    )
                )
    return R002VerifiedCaseLines(
        case_id=case.case_id,
        head_sha=case.verified_pr_head_sha,
        lines=tuple(
            sorted(verified, key=lambda item: (item.stream.value, item.path, item.new_line_number))
        ),
    )


def verify_case_head_files(
    *,
    case: R002CaseManifest,
    parsed: R002ParsedCase,
    head_file_bytes: Mapping[str, bytes],
    limits: R002HeadFileLimits = DEFAULT_R002_HEAD_LIMITS,
) -> R002VerifiedCaseLines:
    """Bind parsed non-removed candidate lines to supplied immutable head bytes."""
    try:
        return _verify_case_head_files(
            case=case, parsed=parsed, head_file_bytes=head_file_bytes, limits=limits
        )
    except R002ReferenceError as caught:
        reason = caught.reason_code
    except Exception:
        reason = "model_validation_failed"
    del case, parsed, head_file_bytes, limits
    _raise_public_reference_error(reason)


def _cross_bind_verified_sidecar(
    case: R002CaseManifest, verified_lines: R002VerifiedCaseLines
) -> None:
    if type(verified_lines.case_id) is not str or type(verified_lines.head_sha) is not str:
        raise R002ReferenceError("model_validation_failed")
    raw_lines = verified_lines.lines
    if (
        type(raw_lines) is not tuple
        or len(raw_lines) > _MAX_R002_VERIFIED_LINES
        or any(
        type(line) is not R002VerifiedLine for line in raw_lines
        )
    ):
        raise R002ReferenceError("model_validation_failed")
    if verified_lines.case_id != case.case_id:
        raise R002ReferenceError("verified_case_mismatch")
    if verified_lines.head_sha != case.verified_pr_head_sha:
        raise R002ReferenceError("verified_head_mismatch")
    identities: set[tuple[str, int]] = set()
    repository_prefix = f"https://github.com/{quote(case.repository, safe='/')}/blob/"
    for line in raw_lines:
        if type(line.path) is not str or type(line.new_line_number) is not int:
            raise R002ReferenceError("model_validation_failed")
        identity = (line.path, line.new_line_number)
        if identity in identities:
            raise R002ReferenceError("verified_duplicate_identity")
        identities.add(identity)
        if type(line.head_sha) is not str or line.head_sha != case.verified_pr_head_sha:
            raise R002ReferenceError("verified_head_mismatch")
        if type(line.permalink) is not str or not line.permalink.startswith(repository_prefix):
            raise R002ReferenceError("verified_repository_mismatch")
        if line.permalink != _candidate_permalink_from_snapshot(
            case, line.path, line.new_line_number
        ):
            raise R002ReferenceError("verified_permalink_mismatch")


def _validate_verified_sidecar(
    case: R002CaseManifest, verified_lines: R002VerifiedCaseLines
) -> R002VerifiedCaseLines:
    if type(verified_lines) is not R002VerifiedCaseLines:
        raise R002ReferenceError("model_validation_failed")
    _cross_bind_verified_sidecar(case, verified_lines)
    try:
        snapshot = R002VerifiedCaseLines.model_validate(
            _trusted_python_dump(R002VerifiedCaseLines, verified_lines),
            strict=True,
        )
    except Exception:
        error = _fresh_reference_error("model_validation_failed")
    else:
        error = None
    if error is not None:
        raise error
    _cross_bind_verified_sidecar(case, snapshot)
    for line in snapshot.lines:
        if line.stream is R002DiffStream.TEST_PATCH and (
            classify_changed_path_evidence_type(line.path) is not EvidenceType.TEST
        ):
            raise R002ReferenceError("test_stream_not_test_evidence")
    return snapshot


def _verify_evidence_reference(
    *,
    case: R002CaseManifest,
    evidence: EvidenceItem,
    verified_lines: R002VerifiedCaseLines,
) -> R002CandidateLineKey:
    case = _validated_case_snapshot(case, reason="model_validation_failed")
    evidence = _validated_evidence_snapshot(evidence)
    verified_lines = _validate_verified_sidecar(case, verified_lines)
    if evidence.source_scope is not EvidenceSourceScope.CHANGED_FILE:
        raise R002ReferenceError("evidence_source_scope_mismatch")
    expected_type = classify_changed_path_evidence_type(evidence.file_path)
    if evidence.evidence_type is not expected_type:
        raise R002ReferenceError("evidence_type_mismatch")
    expected_level = EvidenceLevel.E2 if expected_type is EvidenceType.TEST else EvidenceLevel.E1
    if evidence.evidence_level is not expected_level:
        raise R002ReferenceError("evidence_level_mismatch")
    if evidence.commit_sha != case.verified_pr_head_sha:
        raise R002ReferenceError("evidence_head_mismatch")
    matches = [
        line
        for line in verified_lines.lines
        if line.path == evidence.file_path and line.new_line_number == evidence.line_start
    ]
    if len(matches) != 1 or evidence.line_end != evidence.line_start:
        raise R002ReferenceError("evidence_not_in_verified_universe")
    line = matches[0]
    if evidence.permalink != line.permalink:
        raise R002ReferenceError("evidence_permalink_mismatch")
    return R002CandidateLineKey(
        case_id=case.case_id,
        criterion_id=evidence.criterion_id,
        stream=line.stream,
        path=line.path,
        new_line_number=line.new_line_number,
        normalized_line_sha256=line.normalized_line_sha256,
    )


def verify_evidence_reference(
    *,
    case: R002CaseManifest,
    evidence: EvidenceItem,
    verified_lines: R002VerifiedCaseLines,
) -> R002CandidateLineKey:
    """Map one static, changed-file evidence item into the verified line universe."""
    try:
        return _verify_evidence_reference(
            case=case, evidence=evidence, verified_lines=verified_lines
        )
    except R002ReferenceError as caught:
        reason = caught.reason_code
    except Exception:
        reason = "model_validation_failed"
    del case, evidence, verified_lines
    _raise_public_reference_error(reason)
