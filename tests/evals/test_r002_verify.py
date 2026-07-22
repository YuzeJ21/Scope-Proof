"""ScopeProof-authored immutable-reference tests for the R-002 verifier."""

from __future__ import annotations

import ast
import traceback
from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote

import pytest

from scopeproof_core.evals import r002_verify
from scopeproof_core.evals.r002_diff import parse_case_diffs
from scopeproof_core.evals.r002_models import (
    R002CaseManifest,
    R002DiffStream,
    R002HeadFileLimits,
    R002ParsedCase,
    R002VerifiedCaseLines,
    R002VerifiedLine,
)
from scopeproof_core.evals.r002_verify import (
    R002ReferenceError,
    assert_test_stream_separation,
    candidate_permalink,
    verify_case_head_files,
    verify_evidence_reference,
)
from scopeproof_core.schemas.models import (
    EvidenceItem,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
)

IMPLEMENTATION_DIFF = """\
diff --git a/src/widget.py b/src/widget.py
--- a/src/widget.py
+++ b/src/widget.py
@@ -1,3 +1,3 @@
 before
+added{two_spaces}
-removed
 after
""".replace("{two_spaces}", "  ")
TEST_DIFF = """\
diff --git a/tests/test_widget.py b/tests/test_widget.py
--- a/tests/test_widget.py
+++ b/tests/test_widget.py
@@ -1,0 +1,2 @@
+def test_added():
+    assert True
"""


class _SpoofingBytes(bytes):
    def __len__(self) -> int:
        return 0

    def replace(self, old: bytes, new: bytes, count: int = -1) -> bytes:
        return b"before\nadded  \nafter\n"


class _ThrowingLengthBytes(bytes):
    def __len__(self) -> int:
        raise RuntimeError("TRACE_BYTES_LEN_SENTINEL")


class _ThrowingReplaceBytes(bytes):
    def replace(self, old: bytes, new: bytes, count: int = -1) -> bytes:
        raise RuntimeError("TRACE_BYTES_REPLACE_SENTINEL")


class _PathStringSubclass(str):
    pass


class _VerifiedLineSubclass(R002VerifiedLine):
    pass


class _ThrowingInteger(int):
    def __lt__(self, other: object) -> bool:
        raise RuntimeError("TRACE_INTEGER_SENTINEL")


class _ThrowingLimit:
    def __lt__(self, other: object) -> bool:
        raise RuntimeError("TRACE_LIMIT_SENTINEL")


@pytest.fixture
def r002_case_manifest() -> R002CaseManifest:
    return R002CaseManifest(
        case_id="R002-001",
        instance_id="alpha__one-1",
        repository="alpha/one",
        pr_number=1,
        pr_url="https://github.com/alpha/one/pull/1",
        dataset_base_commit="1" * 40,
        verified_pr_head_sha="2" * 40,
        row_index=0,
        difficulty="fixture",
        row_sha256="3" * 64,
        problem_statement_sha256="4" * 64,
        patch_sha256="5" * 64,
        test_patch_sha256="6" * 64,
    )


@pytest.fixture
def parsed_case(r002_case_manifest: R002CaseManifest) -> R002ParsedCase:
    return parse_case_diffs(
        case_id=r002_case_manifest.case_id,
        patch=IMPLEMENTATION_DIFF,
        test_patch=TEST_DIFF,
    )


@pytest.fixture
def head_files() -> dict[str, bytes]:
    return {
        "src/widget.py": b"before\nadded  \nafter\n",
        "tests/test_widget.py": b"def test_added():\n    assert True\n",
    }


@pytest.fixture
def verified_case_lines(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> R002VerifiedCaseLines:
    return verify_case_head_files(
        case=r002_case_manifest, parsed=parsed_case, head_file_bytes=head_files
    )


def evidence_item(
    *,
    case: R002CaseManifest,
    file_path: str = "src/widget.py",
    line_start: int = 2,
    line_end: int | None = None,
    evidence_type: EvidenceType = EvidenceType.IMPLEMENTATION,
    evidence_level: EvidenceLevel = EvidenceLevel.E1,
    source_scope: EvidenceSourceScope = EvidenceSourceScope.CHANGED_FILE,
    commit_sha: str | None = None,
    permalink: str | None = None,
    evidence_id: str = "EV-AC-01-01",
) -> EvidenceItem:
    end = line_start if line_end is None else line_end
    return EvidenceItem(
        evidence_id=evidence_id,
        criterion_id="AC-01",
        evidence_type=evidence_type,
        evidence_level=evidence_level,
        source_scope=source_scope,
        file_path=file_path,
        line_start=line_start,
        line_end=end,
        commit_sha=case.verified_pr_head_sha if commit_sha is None else commit_sha,
        permalink=(
            candidate_permalink(case, file_path, line_start) if permalink is None else permalink
        ),
        excerpt="ScopeProof-authored fixture excerpt",
        matching_rule="fixture",
        relevance_reason="fixture",
        relevance_score=1,
    )


def test_added_context_and_test_lines_bind_to_head_bytes(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    verified = verify_case_head_files(
        case=r002_case_manifest, parsed=parsed_case, head_file_bytes=head_files
    )

    assert {(line.stream.value, line.path, line.new_line_number) for line in verified.lines} == {
        ("patch", "src/widget.py", 1),
        ("patch", "src/widget.py", 2),
        ("patch", "src/widget.py", 3),
        ("test_patch", "tests/test_widget.py", 1),
        ("test_patch", "tests/test_widget.py", 2),
    }
    assert all(line.head_sha == r002_case_manifest.verified_pr_head_sha for line in verified.lines)
    assert all(
        line.normalized_line_sha256 != sha256(b"removed").hexdigest()
        for line in verified.lines
    )


def test_evidence_mapping_uses_verified_sidecar_line_not_trimmed_excerpt(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    key = verify_evidence_reference(
        case=r002_case_manifest,
        evidence=evidence_item(case=r002_case_manifest),
        verified_lines=verified_case_lines,
    )

    assert key.normalized_line_sha256 == sha256(b"added  ").hexdigest()


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda files: files.pop("src/widget.py"), "head_file_missing"),
        (
            lambda files: files.__setitem__("src/widget.py", b"before\nchanged\nafter\n"),
            "head_line_mismatch",
        ),
        (lambda files: files.__setitem__("src/widget.py", b"\xff"), "head_file_not_utf8"),
        (
            lambda files: files.__setitem__("src/widget.py", b"before\nadded\nafter\n"),
            "head_line_mismatch",
        ),
    ],
)
def test_head_verification_fails_closed_for_missing_invalid_or_changed_bytes(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
    mutate: object,
    reason: str,
) -> None:
    files = deepcopy(head_files)
    mutate(files)  # type: ignore[operator]
    with pytest.raises(R002ReferenceError, match=reason):
        verify_case_head_files(case=r002_case_manifest, parsed=parsed_case, head_file_bytes=files)


@pytest.mark.parametrize(
    ("files", "reason"),
    [
        ({"src/widget.py": b"x", "tests/test_widget.py": "not bytes"}, "head_mapping_invalid"),
        (
            {"src/widget.py": b"x", "tests/test_widget.py": b"x", "extra.py": b"x"},
            "head_mapping_invalid",
        ),
        (
            {"src/widget.py": b"x", "tests/test_widget.py": b"x", "../unsafe": b"x"},
            "head_mapping_invalid",
        ),
    ],
)
def test_head_mapping_must_be_exact_canonical_bytes_before_budgeting(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    files: dict[str, object],
    reason: str,
) -> None:
    with pytest.raises(R002ReferenceError, match=reason):
        verify_case_head_files(case=r002_case_manifest, parsed=parsed_case, head_file_bytes=files)  # type: ignore[arg-type]


def test_bytes_subclass_cannot_spoof_verified_head_content(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    spoofed = {
        **head_files,
        "src/widget.py": _SpoofingBytes(b"candidate line is absent\n"),
    }

    with pytest.raises(R002ReferenceError, match="head_mapping_invalid") as captured:
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed_case,
            head_file_bytes=spoofed,
        )

    assert captured.value.args == ("head_mapping_invalid",)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


@pytest.mark.parametrize(
    ("value", "sentinel"),
    [
        (_ThrowingLengthBytes(b"before\nadded  \nafter\n"), "TRACE_BYTES_LEN_SENTINEL"),
        (
            _ThrowingReplaceBytes(b"before\nadded  \nafter\n"),
            "TRACE_BYTES_REPLACE_SENTINEL",
        ),
    ],
)
def test_bytes_subclass_hooks_fail_closed_without_traceback_input(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
    value: bytes,
    sentinel: str,
) -> None:
    with pytest.raises(R002ReferenceError, match="head_mapping_invalid") as captured:
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed_case,
            head_file_bytes={**head_files, "src/widget.py": value},
        )

    error = captured.value
    trace = traceback.TracebackException.from_exception(error, capture_locals=True)
    frames = [frame for frame in trace.stack if frame.filename == r002_verify.__file__]
    assert error.args == ("head_mapping_invalid",)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert sentinel not in "\n".join(
        local for frame in frames for local in (frame.locals or {}).values()
    )


def test_path_string_subclass_is_not_an_exact_canonical_mapping_key(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    subclass_keyed = {
        _PathStringSubclass(path): value for path, value in head_files.items()
    }

    with pytest.raises(R002ReferenceError, match="head_mapping_invalid") as captured:
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed_case,
            head_file_bytes=subclass_keyed,
        )

    assert captured.value.args == ("head_mapping_invalid",)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_head_mapping_is_snapshotted_before_budgeting_and_line_checks(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    class FlippingMapping(Mapping[str, bytes]):
        def __init__(self, initial: dict[str, bytes]) -> None:
            self._initial = initial
            self._reads = 0

        def __iter__(self):  # type: ignore[no-untyped-def]
            return iter(self._initial)

        def __len__(self) -> int:
            return len(self._initial)

        def __getitem__(self, key: str) -> bytes:
            self._reads += 1
            if self._reads <= len(self._initial):
                return self._initial[key]
            return b"mutated after validation\n"

    verified = verify_case_head_files(
        case=r002_case_manifest,
        parsed=parsed_case,
        head_file_bytes=FlippingMapping(head_files),
    )
    assert {line.head_file_sha256 for line in verified.lines} == {
        sha256(head_files["src/widget.py"]).hexdigest(),
        sha256(head_files["tests/test_widget.py"]).hexdigest(),
    }


def test_head_mapping_snapshot_failure_is_closed_and_sanitized(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
) -> None:
    class ExplodingMapping(Mapping[str, bytes]):
        def __iter__(self):  # type: ignore[no-untyped-def]
            return iter(())

        def __len__(self) -> int:
            return 0

        def __getitem__(self, key: str) -> bytes:
            raise KeyError(key)

        def items(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("TRACE_MAPPING_INPUT_SENTINEL")

    with pytest.raises(R002ReferenceError, match="head_mapping_invalid") as captured:
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed_case,
            head_file_bytes=ExplodingMapping(),
        )

    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_head_file_and_case_byte_limits_are_exact(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    oversized_file = {**head_files, "src/widget.py": b"x" * (4 * 1024 * 1024 + 1)}
    with pytest.raises(R002ReferenceError, match="head_file_limit"):
        verify_case_head_files(
            case=r002_case_manifest, parsed=parsed_case, head_file_bytes=oversized_file
        )

    oversized_case = {**head_files, "src/widget.py": b"x" * (16 * 1024 * 1024)}
    with pytest.raises(R002ReferenceError, match="head_case_limit"):
        verify_case_head_files(
            case=r002_case_manifest, parsed=parsed_case, head_file_bytes=oversized_case
        )


def test_newline_whitespace_and_unicode_are_compared_exactly(
    r002_case_manifest: R002CaseManifest,
) -> None:
    parsed = parse_case_diffs(
        case_id=r002_case_manifest.case_id,
        patch=(
            "diff --git a/src/café.py b/src/café.py\r\n--- a/src/café.py\r\n"
            "+++ b/src/café.py\r\n@@ -1 +1 @@\r\n-café\r\n+café  \r\n"
        ),
        test_patch="",
    )
    verified = verify_case_head_files(
        case=r002_case_manifest,
        parsed=parsed,
        head_file_bytes={"src/café.py": "café  \r".encode()},
    )
    assert verified.lines[0].new_line_number == 1

    with pytest.raises(R002ReferenceError, match="head_line_mismatch"):
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed,
            head_file_bytes={"src/café.py": "café  \n".encode()},
        )


def test_line_number_beyond_end_of_head_file_fails_closed(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    with pytest.raises(R002ReferenceError, match="head_line_out_of_range"):
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed_case,
            head_file_bytes={**head_files, "src/widget.py": b"before\n"},
        )


def test_case_and_parsed_identity_must_match_before_head_verification(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    mismatched = parsed_case.model_copy(update={"case_id": "R002-002"})
    with pytest.raises(R002ReferenceError, match="case_identity_mismatch"):
        verify_case_head_files(
            case=r002_case_manifest, parsed=mismatched, head_file_bytes=head_files
        )


def test_forged_parsed_line_hash_is_revalidated_before_output(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    forged_hash = "9" * 64
    parsed_file = parsed_case.files[0]
    parsed_hunk = parsed_file.hunks[0]
    forged_line = parsed_hunk.lines[0].model_copy(
        update={"normalized_line_sha256": forged_hash}
    )
    forged_hunk = parsed_hunk.model_copy(
        update={"lines": (forged_line, *parsed_hunk.lines[1:])}
    )
    forged_file = parsed_file.model_copy(update={"hunks": (forged_hunk,)})
    forged_case = parsed_case.model_copy(
        update={"files": (forged_file, *parsed_case.files[1:])}
    )

    with pytest.raises(R002ReferenceError, match="model_validation_failed") as captured:
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=forged_case,
            head_file_bytes=head_files,
        )

    error = captured.value
    trace = traceback.TracebackException.from_exception(error, capture_locals=True)
    frames = [frame for frame in trace.stack if frame.filename == r002_verify.__file__]
    assert error.args == ("model_validation_failed",)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert forged_hash not in "\n".join(
        local for frame in frames for local in (frame.locals or {}).values()
    )


def test_test_stream_must_remain_test_classified(r002_case_manifest: R002CaseManifest) -> None:
    parsed = parse_case_diffs(
        case_id=r002_case_manifest.case_id,
        patch=IMPLEMENTATION_DIFF,
        test_patch=TEST_DIFF.replace("tests/test_widget.py", "src/not_a_test.py"),
    )
    with pytest.raises(R002ReferenceError, match="test_stream_not_test_evidence"):
        assert_test_stream_separation(parsed)


def test_stream_path_collision_fails_closed_even_if_model_validation_was_bypassed(
    parsed_case: R002ParsedCase,
) -> None:
    patch_file = next(item for item in parsed_case.files if item.stream is R002DiffStream.PATCH)
    test_file = next(item for item in parsed_case.files if item.stream is R002DiffStream.TEST_PATCH)
    collision = test_file.model_copy(update={"path": patch_file.path})
    invalid = R002ParsedCase.model_construct(case_id="R002-001", files=(patch_file, collision))

    with pytest.raises(R002ReferenceError, match="stream_path_collision"):
        assert_test_stream_separation(invalid)


@pytest.mark.parametrize(
    ("path", "line"),
    [
        ("src/a b#c?%.py", 7),
        ("src/café.py", 1),
    ],
)
def test_candidate_permalink_is_canonical_and_percent_encoded(
    r002_case_manifest: R002CaseManifest, path: str, line: int
) -> None:
    value = candidate_permalink(r002_case_manifest, path, line)
    assert value == (
        f"https://github.com/alpha/one/blob/{r002_case_manifest.verified_pr_head_sha}/"
        f"{quote(path, safe='/')}"
        f"#L{line}-L{line}"
    )


@pytest.mark.parametrize("path,line", [("../unsafe", 1), ("src\\unsafe.py", 1), ("src/x.py", 0)])
def test_candidate_permalink_rejects_invalid_direct_inputs(
    r002_case_manifest: R002CaseManifest, path: str, line: int
) -> None:
    with pytest.raises(R002ReferenceError, match="permalink_input_invalid"):
        candidate_permalink(r002_case_manifest, path, line)


@pytest.mark.parametrize(
    ("update", "sentinel"),
    [
        ({"repository": "TRACE_CASE_REPOSITORY_SENTINEL"}, "TRACE_CASE_REPOSITORY_SENTINEL"),
        ({"verified_pr_head_sha": "TRACE_CASE_HEAD_SENTINEL"}, "TRACE_CASE_HEAD_SENTINEL"),
    ],
)
def test_candidate_permalink_revalidates_bypassed_case_fields(
    r002_case_manifest: R002CaseManifest,
    update: dict[str, object],
    sentinel: str,
) -> None:
    malformed = r002_case_manifest.model_copy(update=update)
    with pytest.raises(R002ReferenceError, match="permalink_input_invalid") as captured:
        candidate_permalink(malformed, "src/widget.py", 1)

    error = captured.value
    trace = traceback.TracebackException.from_exception(error, capture_locals=True)
    frames = [frame for frame in trace.stack if frame.filename == r002_verify.__file__]
    assert error.args == ("permalink_input_invalid",)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert sentinel not in "\n".join(
        local for frame in frames for local in (frame.locals or {}).values()
    )


def test_candidate_permalink_closes_overridden_integer_operations(
    r002_case_manifest: R002CaseManifest,
) -> None:
    with pytest.raises(R002ReferenceError, match="permalink_input_invalid") as captured:
        candidate_permalink(r002_case_manifest, "src/widget.py", _ThrowingInteger(1))

    error = captured.value
    trace = traceback.TracebackException.from_exception(error, capture_locals=True)
    frames = [frame for frame in trace.stack if frame.filename == r002_verify.__file__]
    assert error.args == ("permalink_input_invalid",)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert "TRACE_INTEGER_SENTINEL" not in "\n".join(
        local for frame in frames for local in (frame.locals or {}).values()
    )


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda item: item.model_copy(update={"commit_sha": "9" * 40}), "evidence_head_mismatch"),
        (
            lambda item: item.model_copy(update={"permalink": "https://github.com/wrong"}),
            "evidence_permalink_mismatch",
        ),
        (
            lambda item: item.model_copy(update={"line_end": 3}),
            "evidence_not_in_verified_universe",
        ),
        (
            lambda item: item.model_copy(
                update={"source_scope": EvidenceSourceScope.UNCHANGED_CANDIDATE}
            ),
            "evidence_source_scope_mismatch",
        ),
        (
            lambda item: item.model_copy(update={"evidence_type": EvidenceType.TEST}),
            "evidence_type_mismatch",
        ),
        (
            lambda item: item.model_copy(update={"evidence_level": EvidenceLevel.E2}),
            "evidence_level_mismatch",
        ),
    ],
)
def test_evidence_requires_exact_static_scope_type_level_head_and_permalink(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
    mutate: object,
    reason: str,
) -> None:
    evidence = mutate(evidence_item(case=r002_case_manifest))  # type: ignore[operator]
    with pytest.raises(R002ReferenceError, match=reason):
        verify_evidence_reference(
            case=r002_case_manifest, evidence=evidence, verified_lines=verified_case_lines
        )


def test_test_evidence_requires_test_type_and_e2(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    valid = evidence_item(
        case=r002_case_manifest,
        file_path="tests/test_widget.py",
        line_start=1,
        evidence_type=EvidenceType.TEST,
        evidence_level=EvidenceLevel.E2,
    )
    assert verify_evidence_reference(
        case=r002_case_manifest, evidence=valid, verified_lines=verified_case_lines
    ).stream is R002DiffStream.TEST_PATCH

    invalid = valid.model_copy(update={"evidence_level": EvidenceLevel.E1})
    with pytest.raises(R002ReferenceError, match="evidence_level_mismatch"):
        verify_evidence_reference(
            case=r002_case_manifest, evidence=invalid, verified_lines=verified_case_lines
        )


def test_evidence_sidecar_must_cross_bind_case_head_and_repository(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    evidence = evidence_item(case=r002_case_manifest)
    for sidecar, reason in (
        (verified_case_lines.model_copy(update={"case_id": "R002-002"}), "verified_case_mismatch"),
        (verified_case_lines.model_copy(update={"head_sha": "8" * 40}), "verified_head_mismatch"),
        (
            verified_case_lines.model_copy(
                update={
                    "lines": tuple(
                        line.model_copy(
                            update={
                                "permalink": line.permalink.replace("alpha/one", "bravo/one")
                            }
                        )
                        for line in verified_case_lines.lines
                    )
                }
            ),
            "verified_repository_mismatch",
        ),
    ):
        with pytest.raises(R002ReferenceError, match=reason):
            verify_evidence_reference(
                case=r002_case_manifest, evidence=evidence, verified_lines=sidecar
            )


def test_state_changing_verified_line_container_cannot_inject_unchecked_line(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    target = next(
        line
        for line in verified_case_lines.lines
        if line.path == "src/widget.py" and line.new_line_number == 2
    )
    injected = target.model_copy(update={"normalized_line_sha256": "9" * 64})

    class FlippingLines:
        def __init__(self) -> None:
            self.iterations = 0

        def __iter__(self):  # type: ignore[no-untyped-def]
            self.iterations += 1
            if self.iterations == 1:
                return iter(verified_case_lines.lines)
            return iter((injected,))

    malformed = R002VerifiedCaseLines.model_construct(
        case_id=verified_case_lines.case_id,
        head_sha=verified_case_lines.head_sha,
        lines=FlippingLines(),
    )
    with pytest.raises(R002ReferenceError, match="model_validation_failed") as captured:
        verify_evidence_reference(
            case=r002_case_manifest,
            evidence=evidence_item(case=r002_case_manifest),
            verified_lines=malformed,
        )

    assert captured.value.args == ("model_validation_failed",)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_verified_sidecar_rejects_nested_model_subclasses(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    first = _VerifiedLineSubclass.model_validate(
        verified_case_lines.lines[0].model_dump(mode="python")
    )
    malformed = R002VerifiedCaseLines.model_construct(
        case_id=verified_case_lines.case_id,
        head_sha=verified_case_lines.head_sha,
        lines=(first, *verified_case_lines.lines[1:]),
    )
    with pytest.raises(R002ReferenceError, match="model_validation_failed") as captured:
        verify_evidence_reference(
            case=r002_case_manifest,
            evidence=evidence_item(case=r002_case_manifest),
            verified_lines=malformed,
        )

    assert captured.value.args == ("model_validation_failed",)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_malformed_limits_and_evidence_are_revalidated_at_public_boundaries(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    malformed_limits = R002HeadFileLimits().model_copy(
        update={"bytes_per_case": _ThrowingLimit()}
    )
    with pytest.raises(R002ReferenceError, match="model_validation_failed") as limits_error:
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed_case,
            head_file_bytes=head_files,
            limits=malformed_limits,
        )
    assert limits_error.value.args == ("model_validation_failed",)
    assert limits_error.value.__cause__ is None
    assert limits_error.value.__context__ is None

    malformed_evidence = evidence_item(case=r002_case_manifest).model_copy(
        update={"line_start": "2"}
    )
    with pytest.raises(R002ReferenceError, match="model_validation_failed") as evidence_error:
        verify_evidence_reference(
            case=r002_case_manifest,
            evidence=malformed_evidence,
            verified_lines=verified_case_lines,
        )
    assert evidence_error.value.args == ("model_validation_failed",)
    assert evidence_error.value.__cause__ is None
    assert evidence_error.value.__context__ is None


def test_malformed_verified_permalink_fails_closed(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    malformed = verified_case_lines.model_copy(
        update={
            "lines": tuple(
                line.model_copy(update={"permalink": "not a permalink"})
                for line in verified_case_lines.lines
            )
        }
    )
    with pytest.raises(R002ReferenceError, match="verified_repository_mismatch"):
        verify_evidence_reference(
            case=r002_case_manifest,
            evidence=evidence_item(case=r002_case_manifest),
            verified_lines=malformed,
        )


@pytest.mark.parametrize(
    ("evidence_type", "evidence_level", "reason"),
    [
        (EvidenceType.CI, EvidenceLevel.E1, "evidence_type_mismatch"),
        (EvidenceType.RUNTIME, EvidenceLevel.E1, "evidence_type_mismatch"),
        (EvidenceType.HUMAN, EvidenceLevel.E1, "evidence_type_mismatch"),
        (EvidenceType.IMPLEMENTATION, EvidenceLevel.E0, "evidence_level_mismatch"),
        (EvidenceType.IMPLEMENTATION, EvidenceLevel.E3, "evidence_level_mismatch"),
        (EvidenceType.IMPLEMENTATION, EvidenceLevel.E4, "evidence_level_mismatch"),
    ],
)
def test_nonstatic_or_non_e1_evidence_never_enters_implementation_universe(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
    evidence_type: EvidenceType,
    evidence_level: EvidenceLevel,
    reason: str,
) -> None:
    with pytest.raises(R002ReferenceError, match=reason):
        verify_evidence_reference(
            case=r002_case_manifest,
            evidence=evidence_item(
                case=r002_case_manifest,
                evidence_type=evidence_type,
                evidence_level=evidence_level,
            ),
            verified_lines=verified_case_lines,
        )


def test_duplicate_verified_identity_and_missing_line_fail_closed(
    r002_case_manifest: R002CaseManifest,
    verified_case_lines: R002VerifiedCaseLines,
) -> None:
    duplicate = verified_case_lines.model_copy(
        update={"lines": (*verified_case_lines.lines, verified_case_lines.lines[0])}
    )
    with pytest.raises(R002ReferenceError, match="verified_duplicate_identity"):
        verify_evidence_reference(
            case=r002_case_manifest,
            evidence=evidence_item(case=r002_case_manifest),
            verified_lines=duplicate,
        )

    with pytest.raises(R002ReferenceError, match="evidence_not_in_verified_universe"):
        verify_evidence_reference(
            case=r002_case_manifest,
            evidence=evidence_item(case=r002_case_manifest, line_start=99),
            verified_lines=verified_case_lines,
        )


def test_public_reference_error_has_no_chained_or_input_bearing_context(
    r002_case_manifest: R002CaseManifest,
    parsed_case: R002ParsedCase,
    head_files: dict[str, bytes],
) -> None:
    sentinel = "TRACE_REFERENCE_INPUT_SENTINEL"
    with pytest.raises(R002ReferenceError, match="head_file_not_utf8") as captured:
        verify_case_head_files(
            case=r002_case_manifest,
            parsed=parsed_case,
            head_file_bytes={**head_files, "src/widget.py": b"\xff" + sentinel.encode()},
        )

    error = captured.value
    trace = traceback.TracebackException.from_exception(error, capture_locals=True)
    frames = [frame for frame in trace.stack if frame.filename == r002_verify.__file__]
    assert error.args == (error.reason_code,)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert sentinel not in "\n".join(
        value for frame in frames for value in (frame.locals or {}).values()
    )


def test_reference_error_reason_allowlist_is_closed_and_matches_raise_sites() -> None:
    source = ast.parse(Path(r002_verify.__file__).read_text(encoding="utf-8"))
    literals = {
        node.args[0].value
        for node in ast.walk(source)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"R002ReferenceError", "_fresh_reference_error"}
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert literals == R002ReferenceError.allowed_reason_codes
