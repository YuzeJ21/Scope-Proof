"""Content search retains exact-source exclusions and non-gating reference boundaries."""

from hashlib import sha256
from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    MAX_REFERENCE_LINE_BYTES,
    ChangedLine,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    IngestionState,
    LineChangeType,
    RetrievedFile,
)
from tests.reviews.test_reference_pages import changed
from tests.reviews.test_selected_references import append, source_state


def api():
    return import_module("scopeproof_core.reviews.selected_references")


def search(state, snapshot, path="src/file.py", **kwargs):
    return api().search_reference_page(
        state,
        snapshot,
        source_scope=kwargs.pop("source_scope", EvidenceSourceScope.CHANGED_FILE),
        file_path=path,
        **kwargs,
    )


@pytest.mark.parametrize("exclusion", ["removed", "truncated", "skipped", "duplicate-lines"])
def test_search_never_reopens_excluded_changed_sources(exclusion):
    excluded = changed("src/excluded.py", 2)
    if exclusion == "removed":
        excluded.status = "removed"
    elif exclusion == "truncated":
        excluded.truncated = True
    elif exclusion == "duplicate-lines":
        excluded.lines.append(excluded.lines[0].model_copy(deep=True))
    state, snapshot = source_state([excluded, changed("src/file.py")])
    if exclusion == "skipped":
        snapshot.skipped_files = [excluded.path]
        snapshot.ingestion_state = IngestionState.PARTIAL
    with pytest.raises(ValueError):
        search(state, snapshot, excluded.path, query="value")
    assert search(state, snapshot, query="value").source.file_path == "src/file.py"


@pytest.mark.parametrize("separator", ["\r", "\v", "\f", "\x85", "\u2028", "\u2029"])
def test_search_cannot_reinterpret_ambiguous_changed_patch_boundaries(separator):
    state, snapshot = source_state([changed("src/file.py", patch=f"+value{separator}injected\n")])
    with pytest.raises(ValueError):
        search(state, snapshot, query="value")


def test_unchanged_search_excludes_stale_ambiguous_and_changed_path_aliases():
    state, snapshot = source_state(
        [changed("src/current.py", previous_path="src/old.py", status="renamed")]
    )
    candidate = RetrievedFile(
        path="src/good.py",
        content="find me",
        commit_sha=snapshot.head_sha,
        retrieval_reason="Constructed already-loaded source",
    )
    unchanged = [
        candidate,
        candidate.model_copy(update={"path": "src/current.py"}),
        candidate.model_copy(update={"path": "src/old.py"}),
        candidate.model_copy(update={"path": "src/stale.py", "commit_sha": "older-head"}),
        candidate.model_copy(update={"path": "src/duplicate.py"}),
        candidate.model_copy(update={"path": "src/duplicate.py"}),
        candidate.model_copy(
            update={"path": "src/wrong-scope.py", "source_scope": EvidenceSourceScope.CHANGED_FILE}
        ),
    ]
    for path in [
        "src/current.py",
        "src/old.py",
        "src/stale.py",
        "src/duplicate.py",
        "src/wrong-scope.py",
    ]:
        with pytest.raises(ValueError):
            search(
                state,
                snapshot,
                path,
                query="find",
                source_scope=EvidenceSourceScope.UNCHANGED_CANDIDATE,
                unchanged_files=unchanged,
            )
    good = search(
        state,
        snapshot,
        candidate.path,
        query="find",
        source_scope=EvidenceSourceScope.UNCHANGED_CANDIDATE,
        unchanged_files=unchanged,
    )
    assert [(line.line_number, line.excerpt) for line in good.lines] == [(1, "find me")]


def test_duplicate_changed_paths_fail_instead_of_concatenating_search_matches():
    state, snapshot = source_state([changed("src/file.py")])
    snapshot.files.append(snapshot.files[0].model_copy(deep=True))
    with pytest.raises(ValueError):
        search(state, snapshot, query="value")


def test_unchanged_search_preserves_lf_coordinates_after_raw_line_exclusions():
    state, snapshot = source_state()
    content = "\n".join(
        [
            "bad\u2028match",
            "match first\r",
            "\t ",
            "match" + "é" * 2049,
            "match second",
            "bad\vmatch",
            "match final\r",
        ]
    )
    unchanged = [
        RetrievedFile(
            path="src/raw.py",
            content=content,
            commit_sha=snapshot.head_sha,
            retrieval_reason="Constructed raw physical-line fixture",
        )
    ]
    result = search(
        state,
        snapshot,
        "src/raw.py",
        query="match",
        source_scope=EvidenceSourceScope.UNCHANGED_CANDIDATE,
        unchanged_files=unchanged,
    )
    assert result.source.eligible_line_count == result.matching_line_count == 2
    assert [(line.line_number, line.excerpt) for line in result.lines] == [
        (2, "match first"),
        (5, "match second"),
    ]
    assert unchanged[0].content == content


def test_search_preserves_complete_maximum_byte_line_and_omits_unusable_records():
    file = changed("src/file.py", 0)
    raw = "  " + "é" * ((MAX_REFERENCE_LINE_BYTES - 4) // 2) + "  "
    file.lines = [
        ChangedLine(change_type=LineChangeType.ADDED, line_number=i, content=content)
        for i, content in enumerate(["", " \t", raw + "é", raw, "one\ntwo"], start=1)
    ] + [
        ChangedLine(change_type=LineChangeType.REMOVED, line_number=9, content="removed"),
        ChangedLine(change_type=LineChangeType.CONTEXT, line_number=None, content="unlocated"),
    ]
    state, snapshot = source_state([file])
    result = search(state, snapshot, query="é")
    assert result.source.eligible_line_count == result.matching_line_count == 1
    assert [(line.line_number, line.excerpt) for line in result.lines] == [(4, raw)]
    assert len(result.lines[0].excerpt.encode("utf-8")) == MAX_REFERENCE_LINE_BYTES


@pytest.mark.parametrize("query", [None, True, 4, 1.0, b"value", ["value"], "é" * 201])
def test_queries_are_strict_bounded_unicode_text(query):
    state, snapshot = source_state([changed("src/file.py")])
    with pytest.raises(ValueError):
        search(state, snapshot, query=query)


@pytest.mark.parametrize("index", [-1, True, "0", 0.0, None, 2])
def test_search_page_requests_reject_coercion_and_out_of_range_indexes(index):
    state, snapshot = source_state([changed("src/file.py", 101)])
    with pytest.raises(ValueError):
        search(state, snapshot, query="value", page_index=index)


def test_empty_result_is_valid_only_on_page_zero_and_has_no_selection_fallback():
    state, snapshot = source_state([changed("src/file.py", 101)])
    result = search(state, snapshot, query="not present")
    assert result.matching_line_count == result.page_count == 0
    assert result.source.eligible_line_count == 101 and result.lines == ()
    with pytest.raises(ValueError):
        search(state, snapshot, query="not present", page_index=1)


@pytest.mark.parametrize("path", ["src/missing.py", "../file.py", "src//file.py"])
def test_search_never_falls_back_from_unknown_or_noncanonical_file(path):
    state, snapshot = source_state([changed("src/file.py")])
    with pytest.raises(ValueError):
        search(state, snapshot, path, query="value")


def test_search_model_revalidates_forged_counts_windows_and_nested_instances():
    state, snapshot = source_state([changed("src/file.py", 101)])
    result = search(state, snapshot, query="value")
    first = result.lines[0]
    for update in [
        {"query": None},
        {"query": "x" * 201},
        {"query": "absent"},
        {"page_index": True},
        {"page_index": 1},
        {"matching_line_count": True},
        {"matching_line_count": -1},
        {"matching_line_count": 102},
        {"matching_line_count": 0},
        {"lines": result.lines[:-1]},
        {"lines": tuple(reversed(result.lines))},
        {"lines": (first, *result.lines[:-1])},
        {"lines": (first.model_copy(update={"excerpt": "value\ninjected"}), *result.lines[1:])},
        {"lines": (first.model_copy(update={"excerpt": "no literal match"}), *result.lines[1:])},
        {"lines": (first.model_copy(update={"line_number": True}), *result.lines[1:])},
        {"lines": (first.model_copy(update={"file_path": "src/other.py"}), *result.lines[1:])},
        {
            "lines": (
                first.model_copy(update={"evidence_level": EvidenceLevel.E2}),
                *result.lines[1:],
            )
        },
        {"source": result.source.model_copy(update={"eligible_line_count": True})},
        {"source": result.source.model_copy(update={"eligible_line_count": 99})},
        {"source": result.source.model_copy(update={"file_path": "src/other.py"})},
        {"source": result.source.model_copy(update={"source_scope": "unchanged_candidate"})},
    ]:
        with pytest.raises(ValueError):
            type(result).model_validate(result.model_copy(update=update))
    with pytest.raises(ValidationError):
        type(result).model_validate({**result.model_dump(), "page_count": 999})
    with pytest.raises(ValidationError):
        result.query = "edited"


def test_search_selected_line_still_requires_current_source_and_stored_digest():
    state, snapshot = source_state([changed("src/file.py")])
    selected = search(state, snapshot, query="value").lines[0]
    updated = append(state, snapshot, selected)
    reference = updated.bundle.reviewer_selected_references[0]
    assert reference.excerpt_sha256 == sha256(selected.excerpt.encode("utf-8")).hexdigest()
    with pytest.raises(ValueError):
        type(reference).model_validate(reference.model_copy(update={"excerpt_sha256": "0" * 64}))
    with pytest.raises(ValueError):
        append(state, snapshot, selected.model_copy(update={"excerpt": "invented value"}))
    changed_source = snapshot.model_copy(deep=True)
    changed_source.files[0].lines[0].content = "different value at the same coordinate"
    with pytest.raises(ValueError):
        append(state, changed_source, selected)
    with pytest.raises(ValueError):
        search(state, snapshot.model_copy(update={"head_sha": "other-head"}), query="value")


def test_search_is_read_only_and_keeps_test_source_at_static_intent_authority():
    state, snapshot = source_state([changed("tests/test_file.py", 101)])
    unchanged = [
        RetrievedFile(
            path="src/helper.py",
            content="value helper",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Constructed loaded candidate",
        )
    ]
    before = (state.model_dump_json(), snapshot.model_dump_json(), unchanged[0].model_dump_json())
    result = search(state, snapshot, "tests/test_file.py", query="value", page_index=1)
    assert len(result.lines) == 1
    assert result.lines[0].evidence_type is EvidenceType.TEST
    assert result.lines[0].evidence_level is EvidenceLevel.E2
    search(
        state,
        snapshot,
        unchanged[0].path,
        query="helper",
        source_scope=EvidenceSourceScope.UNCHANGED_CANDIDATE,
        unchanged_files=unchanged,
    )
    assert before == (
        state.model_dump_json(),
        snapshot.model_dump_json(),
        unchanged[0].model_dump_json(),
    )
    assert state.bundle.runtime_evidence == []
    assert state.bundle.reviewer_selected_references == []
