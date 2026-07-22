"""Fail-closed parsing of bounded, normalized R-002 unified diffs."""

from __future__ import annotations

import re
from hashlib import sha256

from pydantic import ValidationError

from scopeproof_core.evals.r002_models import (
    R002CaseId,
    R002DiffLimits,
    R002DiffStream,
    R002Error,
    R002ParsedCase,
    R002ParsedDiff,
    R002ParsedFile,
    R002ParsedHunk,
    R002ParsedLine,
    validate_r002_logical_path,
)
from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType

DEFAULT_R002_DIFF_LIMITS = R002DiffLimits()

_DIFF_HEADER = re.compile(r"^diff --git a/(\S*) b/(\S*)$")
_INDEX = re.compile(r"^index [0-9A-Fa-f]+\.\.[0-9A-Fa-f]+(?: [0-7]{6})?$")
_HUNK_HEADER = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$"
)
_NO_NEWLINE_MARKER = r"\ No newline at end of file"


class R002DiffError(R002Error):
    """A stable, deliberately non-diagnostic R-002 diff parsing error."""

    allowed_reason_codes = frozenset(
        {
            "binary_diff",
            "case_diff_line_limit",
            "case_limit",
            "dev_null_path",
            "diff_line_limit",
            "duplicate_path",
            "duplicate_path_across_streams",
            "file_limit",
            "hunk_count_mismatch",
            "hunk_limit",
            "hunk_overlap",
            "invalid_diff_header",
            "invalid_hunk_header",
            "invalid_hunk_range",
            "invalid_index",
            "invalid_line_marker",
            "invalid_no_newline_marker",
            "invalid_path",
            "invalid_utf8",
            "line_limit",
            "model_validation_failed",
            "path_mismatch",
            "unsupported_copy",
            "unsupported_mode_change",
            "unsupported_rename",
        }
    )


def _validate_path(path: str, *, limits: R002DiffLimits) -> str:
    if len(path) > limits.path_characters:
        raise R002DiffError("invalid_path")
    try:
        return validate_r002_logical_path(path)
    except ValueError:
        raise R002DiffError("invalid_path") from None


def _metadata_error(record: str) -> None:
    if record.startswith(("rename from ", "rename to ")):
        raise R002DiffError("unsupported_rename")
    if record.startswith(("copy from ", "copy to ")):
        raise R002DiffError("unsupported_copy")
    if record.startswith(("Binary files ", "GIT binary patch")):
        raise R002DiffError("binary_diff")
    if record.startswith(
        (
            "new file mode ",
            "deleted file mode ",
            "old mode ",
            "new mode ",
            "similarity index ",
            "dissimilarity index ",
        )
    ):
        raise R002DiffError("unsupported_mode_change")


def _heading_path(record: str, *, prefix: str, expected_path: str, limits: R002DiffLimits) -> None:
    if not record.startswith(prefix):
        _metadata_error(record)
        raise R002DiffError("path_mismatch")
    value = record[len(prefix) :]
    if value == "/dev/null":
        raise R002DiffError("dev_null_path")
    expected_prefix = "a/" if prefix == "--- " else "b/"
    if not value.startswith(expected_prefix):
        raise R002DiffError("path_mismatch")
    actual_path = _validate_path(value[len(expected_prefix) :], limits=limits)
    if actual_path != expected_path:
        raise R002DiffError("path_mismatch")


def _parsed_line(
    marker: str,
    content: str,
    old_line: int,
    new_line: int,
    *,
    limits: R002DiffLimits,
) -> R002ParsedLine:
    if len(content.encode("utf-8")) > limits.line_bytes:
        raise R002DiffError("line_limit")
    if marker == " ":
        kind, old_number, new_number = LineChangeType.CONTEXT, old_line, new_line
    elif marker == "+":
        kind, old_number, new_number = LineChangeType.ADDED, None, new_line
    elif marker == "-":
        kind, old_number, new_number = LineChangeType.REMOVED, old_line, None
    else:
        raise R002DiffError("invalid_line_marker")
    return R002ParsedLine(
        change_type=kind,
        old_line_number=old_number,
        new_line_number=new_number,
        content=content,
        normalized_line_sha256=sha256(content.encode("utf-8")).hexdigest(),
    )


def _parse_hunk_header(record: str) -> tuple[int, int, int, int]:
    match = _HUNK_HEADER.fullmatch(record)
    if match is None:
        raise R002DiffError("invalid_hunk_header")
    old_start, old_count, new_start, new_count = match.groups()
    values = (int(old_start), int(old_count or 1), int(new_start), int(new_count or 1))
    if values[0] < 1 or values[2] < 1:
        raise R002DiffError("invalid_hunk_range")
    return values


def _raise_for_unexpected_record(record: str) -> None:
    _metadata_error(record)
    if record.startswith("index "):
        raise R002DiffError("invalid_index")
    if record == _NO_NEWLINE_MARKER:
        raise R002DiffError("invalid_no_newline_marker")
    if record.startswith("diff --git"):
        raise R002DiffError("invalid_diff_header")
    if record.startswith("@@"):
        raise R002DiffError("invalid_hunk_header")
    raise R002DiffError("invalid_line_marker")


def parse_unified_diff(
    raw: bytes,
    *,
    stream: R002DiffStream,
    limits: R002DiffLimits = DEFAULT_R002_DIFF_LIMITS,
) -> R002ParsedDiff:
    """Parse only the R-002 accepted unified-diff grammar, or fail closed."""
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    try:
        records = normalized.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        raise R002DiffError("invalid_utf8") from None
    if records and records[-1] == "":
        records.pop()

    files: list[R002ParsedFile] = []
    paths: set[str] = set()
    hunk_count = 0
    diff_line_count = 0
    index = 0
    try:
        while index < len(records):
            header = records[index]
            match = _DIFF_HEADER.fullmatch(header)
            if match is None:
                _raise_for_unexpected_record(header)
            old_path, new_path = match.groups()
            path = _validate_path(old_path, limits=limits)
            if _validate_path(new_path, limits=limits) != path:
                raise R002DiffError("path_mismatch")
            if path in paths:
                raise R002DiffError("duplicate_path")
            if len(files) >= limits.files:
                raise R002DiffError("file_limit")
            index += 1

            if index < len(records) and records[index].startswith("index "):
                if _INDEX.fullmatch(records[index]) is None:
                    raise R002DiffError("invalid_index")
                index += 1
            if index >= len(records):
                raise R002DiffError("invalid_line_marker")
            _heading_path(records[index], prefix="--- ", expected_path=path, limits=limits)
            index += 1
            if index >= len(records):
                raise R002DiffError("invalid_line_marker")
            _heading_path(records[index], prefix="+++ ", expected_path=path, limits=limits)
            index += 1

            hunks: list[R002ParsedHunk] = []
            previous: R002ParsedHunk | None = None
            additions = 0
            deletions = 0
            while index < len(records) and not records[index].startswith("diff --git"):
                record = records[index]
                if record.startswith("@@") and hunk_count >= limits.hunks:
                    raise R002DiffError("hunk_limit")
                old_start, old_count, new_start, new_count = _parse_hunk_header(record)
                if previous is not None and (
                    old_start <= previous.old_start
                    or new_start <= previous.new_start
                    or old_start < previous.old_start + previous.old_count
                    or new_start < previous.new_start + previous.new_count
                ):
                    raise R002DiffError("hunk_overlap")
                index += 1
                old_line = old_start
                new_line = new_start
                old_seen = 0
                new_seen = 0
                lines: list[R002ParsedLine] = []
                last_was_content = False
                while index < len(records):
                    record = records[index]
                    if record.startswith(("diff --git", "@@")):
                        break
                    if record == _NO_NEWLINE_MARKER:
                        if not last_was_content:
                            raise R002DiffError("invalid_no_newline_marker")
                        last_was_content = False
                        index += 1
                        continue
                    if not record or record[0] not in {" ", "+", "-"}:
                        _raise_for_unexpected_record(record)
                    if diff_line_count >= limits.diff_lines:
                        raise R002DiffError("diff_line_limit")
                    line = _parsed_line(
                        record[0], record[1:], old_line, new_line, limits=limits
                    )
                    if line.change_type is not LineChangeType.ADDED:
                        old_line += 1
                        old_seen += 1
                    if line.change_type is not LineChangeType.REMOVED:
                        new_line += 1
                        new_seen += 1
                    if line.change_type is LineChangeType.ADDED:
                        additions += 1
                    elif line.change_type is LineChangeType.REMOVED:
                        deletions += 1
                    lines.append(line)
                    diff_line_count += 1
                    last_was_content = True
                    index += 1
                if (old_seen, new_seen) != (old_count, new_count):
                    raise R002DiffError("hunk_count_mismatch")
                hunk = R002ParsedHunk(
                    hunk_id=f"{stream}:{path}:H{len(hunks) + 1}",
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    lines=tuple(lines),
                )
                hunks.append(hunk)
                previous = hunk
                hunk_count += 1
            if not hunks:
                raise R002DiffError("invalid_line_marker")
            files.append(
                R002ParsedFile(
                    stream=stream,
                    path=path,
                    hunks=tuple(hunks),
                    additions=additions,
                    deletions=deletions,
                )
            )
            paths.add(path)
        ordered_files = tuple(sorted(files, key=lambda item: item.path))
        return R002ParsedDiff(
            stream=stream,
            files=ordered_files,
            file_count=len(ordered_files),
            hunk_count=hunk_count,
            diff_line_count=diff_line_count,
        )
    except ValidationError:
        raise R002DiffError("model_validation_failed") from None


def parse_case_diffs(
    *,
    case_id: R002CaseId,
    patch: str,
    test_patch: str,
    limits: R002DiffLimits = DEFAULT_R002_DIFF_LIMITS,
) -> R002ParsedCase:
    """Parse the isolated patch streams and impose the combined R-002 bounds."""
    try:
        parsed = (
            parse_unified_diff(patch.encode("utf-8"), stream=R002DiffStream.PATCH, limits=limits),
            parse_unified_diff(
                test_patch.encode("utf-8"), stream=R002DiffStream.TEST_PATCH, limits=limits
            ),
        )
    except UnicodeEncodeError:
        raise R002DiffError("invalid_utf8") from None
    files = tuple(file for diff in parsed for file in diff.files)
    paths = [file.path for file in files]
    if len(paths) != len(set(paths)):
        raise R002DiffError("duplicate_path_across_streams")
    if len(files) > limits.files or sum(len(file.hunks) for file in files) > limits.hunks:
        raise R002DiffError("case_limit")
    if sum(diff.diff_line_count for diff in parsed) > limits.diff_lines:
        raise R002DiffError("case_diff_line_limit")
    try:
        return R002ParsedCase(
            case_id=case_id,
            files=tuple(sorted(files, key=lambda item: (item.stream.value, item.path))),
        )
    except ValidationError:
        raise R002DiffError("model_validation_failed") from None


def parsed_case_to_changed_files(parsed: R002ParsedCase) -> list[ChangedFile]:
    """Adapt parsed patches to the existing retrieval contract without a patch body."""
    return [
        ChangedFile(
            path=file.path,
            status="modified",
            additions=file.additions,
            deletions=file.deletions,
            changes=file.additions + file.deletions,
            patch="",
            lines=[
                ChangedLine(
                    change_type=line.change_type,
                    line_number=(
                        line.old_line_number
                        if line.change_type is LineChangeType.REMOVED
                        else line.new_line_number
                    ),
                    content=line.content,
                )
                for hunk in file.hunks
                for line in hunk.lines
            ],
        )
        for file in parsed.files
    ]
