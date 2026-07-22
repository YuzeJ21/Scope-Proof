from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path

import pytest

from scopeproof_core.evals import r002_diff
from scopeproof_core.evals.r002_diff import (
    R002DiffError,
    parse_case_diffs,
    parse_unified_diff,
    parsed_case_to_changed_files,
)
from scopeproof_core.evals.r002_models import R002DiffStream, R002ParsedCase
from scopeproof_core.schemas.models import LineChangeType


def _file(path: str, *hunks: str) -> bytes:
    return (
        f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
        + "".join(hunks)
    ).encode()


def _hunk(old_start: int, old_count: int, new_start: int, new_count: int, body: str) -> str:
    return f"@@ -{old_start},{old_count} +{new_start},{new_count} @@\n{body}"


def test_parser_preserves_new_side_identity_whitespace_and_normalized_newlines() -> None:
    parsed = parse_unified_diff(
        b"diff --git a/src/a.py b/src/a.py\r\n--- a/src/a.py\r\n+++ b/src/a.py\r\n"
        b"@@ -2,2 +2,3 @@\r\n keep\r+\tadded  \r\n-old\r\n+\r\n"
        b"diff --git a/tests/test_a.py b/tests/test_a.py\n--- a/tests/test_a.py\n"
        b"+++ b/tests/test_a.py\n@@ -8 +8 @@\n-old test\n+new test\n"
        b"@@ -20,1 +20,1 @@\n context\n",
        stream=R002DiffStream.PATCH,
    )

    assert [(item.path, len(item.hunks)) for item in parsed.files] == [
        ("src/a.py", 1),
        ("tests/test_a.py", 2),
    ]
    lines = parsed.files[0].hunks[0].lines
    assert [
        (line.change_type.value, line.old_line_number, line.new_line_number, line.content)
        for line in lines
    ] == [
        ("context", 2, 2, "keep"),
        ("added", None, 3, "\tadded  "),
        ("removed", 3, None, "old"),
        ("added", None, 4, ""),
    ]
    assert lines[1].normalized_line_sha256 == sha256(b"\tadded  ").hexdigest()
    assert parsed.files[0].hunks[0].hunk_id == "patch:src/a.py:H1"


def test_parser_accepts_no_newline_marker_only_after_content_line() -> None:
    parsed = parse_unified_diff(
        _file("src/a.py", _hunk(1, 1, 1, 1, "-before\n\\ No newline at end of file\n+after\n")),
        stream=R002DiffStream.PATCH,
    )

    assert [line.content for line in parsed.files[0].hunks[0].lines] == ["before", "after"]


def test_adapter_preserves_removed_old_numbers_and_has_no_patch_body() -> None:
    parsed = parse_unified_diff(
        _file("src/a.py", _hunk(2, 2, 2, 3, " keep\n+added\n-removed\n+\n")),
        stream=R002DiffStream.PATCH,
    )

    changed = parsed_case_to_changed_files(
        R002ParsedCase(case_id="R002-001", files=parsed.files)
    )[0]

    assert (
        changed.status,
        changed.additions,
        changed.deletions,
        changed.changes,
        changed.patch,
    ) == (
        "modified",
        2,
        1,
        3,
        "",
    )
    assert [(line.change_type, line.line_number, line.content) for line in changed.lines] == [
        (LineChangeType.CONTEXT, 2, "keep"),
        (LineChangeType.ADDED, 3, "added"),
        (LineChangeType.REMOVED, 3, "removed"),
        (LineChangeType.ADDED, 4, ""),
    ]


def test_parser_accepts_omitted_and_zero_hunk_counts() -> None:
    parsed = parse_unified_diff(
        _file(
            "src/a.py",
            "@@ -1,0 +1 @@\n+created\n",
            "@@ -4 +5,0 @@\n-removed\n",
        ),
        stream=R002DiffStream.PATCH,
    )

    assert [(hunk.old_count, hunk.new_count) for hunk in parsed.files[0].hunks] == [
        (0, 1),
        (1, 0),
    ]


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (b"\xff", "invalid_utf8"),
        (b"diff --git a//x b//x\n", "invalid_path"),
        (b"diff --git a/../x b/../x\n", "invalid_path"),
        (b"diff --git a/a\\b b/a\\b\n", "invalid_path"),
        (b"diff --git a/x\x00 b/x\x00\n", "invalid_path"),
        (b"diff --git a/" + b"x" * 513 + b" b/" + b"x" * 513 + b"\n", "invalid_path"),
        (b"diff --git a/x b/x\nrename from x\nrename to y\n", "unsupported_rename"),
        (b"diff --git a/x b/x\ncopy from x\ncopy to y\n", "unsupported_copy"),
        (b"diff --git a/x b/x\nBinary files a/x and b/x differ\n", "binary_diff"),
        (b"diff --git a/x b/x\nnew file mode 100644\n", "unsupported_mode_change"),
        (b"diff --git a/x b/x\ndeleted file mode 100644\n", "unsupported_mode_change"),
        (
            b"diff --git a/x b/x\n--- /dev/null\n+++ b/x\n@@ -1 +1 @@\n+x\n",
            "dev_null_path",
        ),
        (
            b"diff --git a/x b/x\n--- a/y\n+++ b/x\n@@ -1 +1 @@\n x\n",
            "path_mismatch",
        ),
        (
            b"diff --git \"a/x\" \"b/x\"\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n x\n",
            "invalid_diff_header",
        ),
        (
            b"diff --git a/x b/x\nindex not-a-hash\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n x\n",
            "invalid_index",
        ),
        (_file("x", "@@ -0,1 +1,1 @@\n x\n"), "invalid_hunk_range"),
        (_file("x", "@@ -1,no +1,1 @@\n x\n"), "invalid_hunk_header"),
        (_file("x", "@@ -1 +1 @@\n\\ No newline at end of file\n"), "invalid_no_newline_marker"),
        (_file("x", "@@ -1 +1 @@\nplain marker-free text\n"), "invalid_line_marker"),
        (_file("x", "@@ -1 +1 @@\n\n"), "invalid_line_marker"),
    ],
)
def test_parser_rejects_ambiguous_or_unsafe_records(raw: bytes, reason: str) -> None:
    with pytest.raises(R002DiffError, match=reason):
        parse_unified_diff(raw, stream=R002DiffStream.PATCH)


def test_parser_rejects_mismatched_hunk_counts_and_overlapping_ranges() -> None:
    with pytest.raises(R002DiffError, match="hunk_count_mismatch"):
        parse_unified_diff(
            _file("x", "@@ -1,2 +1,1 @@\n x\n"), stream=R002DiffStream.PATCH
        )

    with pytest.raises(R002DiffError, match="hunk_overlap"):
        parse_unified_diff(
            _file("x", "@@ -1 +1 @@\n x\n@@ -1 +2 @@\n y\n"),
            stream=R002DiffStream.PATCH,
        )


def test_parser_rejects_duplicate_path_within_stream() -> None:
    raw = _file("src/a.py", "@@ -1 +1 @@\n x\n") + _file(
        "src/a.py", "@@ -2 +2 @@\n y\n"
    )

    with pytest.raises(R002DiffError, match="duplicate_path"):
        parse_unified_diff(raw, stream=R002DiffStream.PATCH)


def test_parser_enforces_exact_per_stream_boundaries_before_model_construction() -> None:
    exact_files = b"".join(_file(f"src/{number}.py", "@@ -1 +1 @@\n x\n") for number in range(32))
    assert parse_unified_diff(exact_files, stream=R002DiffStream.PATCH).file_count == 32
    over_files = exact_files + b"diff --git a/src/32.py b/src/32.py\n"
    with pytest.raises(R002DiffError, match="file_limit"):
        parse_unified_diff(over_files, stream=R002DiffStream.PATCH)

    exact_hunks = _file(
        "src/a.py",
        *[
            _hunk(number, 1, number, 1, " x\n")
            for number in range(1, 257)
        ],
    )
    assert parse_unified_diff(exact_hunks, stream=R002DiffStream.PATCH).hunk_count == 256
    over_hunks = exact_hunks + b"@@ malformed 257th hunk\n"
    with pytest.raises(R002DiffError, match="hunk_limit"):
        parse_unified_diff(over_hunks, stream=R002DiffStream.PATCH)

    exact_lines = _file("src/a.py", _hunk(1, 0, 1, 50000, "+x\n" * 50000))
    assert parse_unified_diff(exact_lines, stream=R002DiffStream.PATCH).diff_line_count == 50000
    over_lines = _file("src/a.py", _hunk(1, 0, 1, 50001, "+x\n" * 50001))
    with pytest.raises(R002DiffError, match="diff_line_limit"):
        parse_unified_diff(over_lines, stream=R002DiffStream.PATCH)

    exact_content = _file("src/a.py", _hunk(1, 0, 1, 1, "+" + "x" * 65536 + "\n"))
    assert parse_unified_diff(exact_content, stream=R002DiffStream.PATCH).files
    over_content = _file("src/a.py", _hunk(1, 0, 1, 1, "+" + "x" * 65537 + "\n"))
    with pytest.raises(R002DiffError, match="line_limit"):
        parse_unified_diff(over_content, stream=R002DiffStream.PATCH)


def test_case_parser_rejects_cross_stream_duplicates_and_combined_line_excess() -> None:
    duplicate = _file("src/a.py", "@@ -1 +1 @@\n x\n").decode()
    with pytest.raises(R002DiffError, match="duplicate_path_across_streams"):
        parse_case_diffs(case_id="R002-001", patch=duplicate, test_patch=duplicate)

    patch = _file("src/a.py", _hunk(1, 0, 1, 25000, "+x\n" * 25000)).decode()
    test_patch = _file("tests/test_a.py", _hunk(1, 0, 1, 25001, "+x\n" * 25001)).decode()
    with pytest.raises(R002DiffError, match="case_diff_line_limit"):
        parse_case_diffs(case_id="R002-001", patch=patch, test_patch=test_patch)


def test_parser_errors_do_not_chain_input_or_model_details() -> None:
    with pytest.raises(R002DiffError, match="invalid_utf8") as invalid_utf8:
        parse_unified_diff(b"\xff", stream=R002DiffStream.PATCH)
    assert invalid_utf8.value.__cause__ is None

    with pytest.raises(R002DiffError, match="model_validation_failed") as invalid_case:
        parse_case_diffs(case_id="not-a-case", patch="", test_patch="")
    assert invalid_case.value.__cause__ is None


def test_diff_error_reason_allowlist_is_exact_and_closed() -> None:
    assert R002DiffError.allowed_reason_codes == frozenset(
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
    source = ast.parse(Path(r002_diff.__file__).read_text(encoding="utf-8"))
    raise_literals = {
        node.args[0].value
        for node in ast.walk(source)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "R002DiffError"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert raise_literals == R002DiffError.allowed_reason_codes
