"""File pages expose exact static references without expanding their authority."""

from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    IngestionState,
    LineChangeType,
    RetrievedFile,
)
from tests.reviews.test_selected_references import append, source_state


def api():
    return import_module("scopeproof_core.reviews.selected_references")


def changed(path, count=1, **kwargs):
    return ChangedFile(
        path=path,
        status=kwargs.pop("status", "modified"),
        lines=[
            ChangedLine(change_type=LineChangeType.ADDED, line_number=i, content=f"value_{i} = {i}")
            for i in range(1, count + 1)
        ],
        **kwargs,
    )


def page(state, snapshot, path, index=0, unchanged=None, scope=EvidenceSourceScope.CHANGED_FILE):
    return api().selectable_reference_page(
        state,
        snapshot,
        source_scope=scope,
        file_path=path,
        page_index=index,
        unchanged_files=unchanged,
    )


def test_late_file_and_last_page_remain_available_beyond_legacy_prefix():
    state, snapshot = source_state([changed("src/a.py", 1105), changed("src/z.py", 103)])
    legacy = api().selectable_reference_lines(state, snapshot)
    assert len(legacy) == 1000
    assert {line.file_path for line in legacy} == {"src/a.py"}
    sources = api().selectable_reference_sources(state, snapshot)
    assert [(s.file_path, s.eligible_line_count) for s in sources] == [
        ("src/a.py", 1105),
        ("src/z.py", 103),
    ]
    assert api().MAX_REFERENCE_PAGE_LINES == 100
    last = page(state, snapshot, "src/a.py", 11)
    assert last.source == sources[0]
    assert last.page_index == 11 and last.page_count == 12
    assert [line.line_number for line in last.lines] == list(range(1101, 1106))
    later = page(state, snapshot, "src/z.py", 1)
    assert later.page_count == 2
    assert [line.line_number for line in later.lines] == [101, 102, 103]
    before = state.model_dump(mode="json")
    updated = append(state, snapshot, last.lines[-1])
    updated = append(updated, snapshot, later.lines[-1])
    after = updated.model_dump(mode="json")
    assert len(after["bundle"]["reviewer_selected_references"]) == 2
    after["bundle"]["reviewer_selected_references"] = []
    after["bundle"]["active_reviewer_selected_reference_ids"] = []
    assert after == before


def test_pages_sort_sparse_physical_coordinates_after_eligibility_filtering():
    file = changed("src/sparse.py", 0)
    file.lines = [
        ChangedLine(change_type=LineChangeType.CONTEXT, line_number=i * 3, content=f"line {i}")
        for i in range(105, 0, -1)
    ] + [
        ChangedLine(change_type=LineChangeType.ADDED, line_number=1, content=" \t"),
        ChangedLine(change_type=LineChangeType.ADDED, line_number=2, content="é" * 2049),
        ChangedLine(change_type=LineChangeType.REMOVED, line_number=4, content="removed"),
    ]
    state, snapshot = source_state([changed("src/z.py"), file])
    first = page(state, snapshot, file.path)
    last = page(state, snapshot, file.path, 1)
    assert first.source.eligible_line_count == 105
    assert [line.line_number for line in first.lines] == list(range(3, 301, 3))
    assert [line.line_number for line in last.lines] == [303, 306, 309, 312, 315]
    reordered = snapshot.model_copy(deep=True)
    reordered.files.reverse()
    reordered.files[-1].lines.reverse()
    assert api().selectable_reference_sources(
        state, reordered
    ) == api().selectable_reference_sources(state, snapshot)
    assert page(state, reordered, file.path, 1) == last


@pytest.mark.parametrize("index", [-1, True, "1", 1.0, 2])
def test_invalid_or_out_of_range_page_indexes_fail_closed(index):
    state, snapshot = source_state([changed("src/file.py", 101)])
    with pytest.raises(ValueError):
        page(state, snapshot, "src/file.py", index)


@pytest.mark.parametrize("path", ["src/missing.py", "../file.py", "src//file.py", "src\\file.py"])
def test_unknown_or_noncanonical_source_never_substitutes_another_file(path):
    state, snapshot = source_state([changed("src/file.py", 101)])
    with pytest.raises(ValueError):
        page(state, snapshot, path)


@pytest.mark.parametrize("separator", ["\r", "\v", "\f", "\x85", "\u2028", "\u2029"])
def test_ambiguous_raw_changed_patch_is_unavailable_on_every_page(separator):
    file = changed("src/ambiguous.py", 1100, patch=f"+bad{separator}record\n")
    state, snapshot = source_state([file, changed("src/safe.py")])
    assert [s.file_path for s in api().selectable_reference_sources(state, snapshot)] == [
        "src/safe.py"
    ]
    with pytest.raises(ValueError):
        page(state, snapshot, file.path, 10)


def test_unsafe_files_and_aliases_cannot_supply_later_pages():
    duplicate_lines = changed("src/duplicate-lines.py", 1100)
    duplicate_lines.lines.append(duplicate_lines.lines[-1])
    files = [
        changed("src/removed.py", 1100, status="removed"),
        changed("src/truncated.py", 1100, truncated=True),
        changed("src/skipped.py", 1100),
        changed("../outside.py", 1100),
        changed("src/new.py", 1100, status="renamed", previous_path="src/old.py"),
        duplicate_lines,
    ]
    state, snapshot = source_state(files)
    snapshot.skipped_files = ["src/skipped.py"]
    snapshot.ingestion_state = IngestionState.PARTIAL
    unchanged = [
        RetrievedFile(
            path=path,
            content="bypass\n" * 1100,
            commit_sha=snapshot.head_sha,
            retrieval_reason="Constructed candidate",
        )
        for path in ["src/old.py", "src/removed.py", "src/skipped.py"]
    ]
    assert [
        s.file_path for s in api().selectable_reference_sources(state, snapshot, unchanged)
    ] == ["src/new.py"]
    assert page(state, snapshot, "src/new.py", 10).lines[0].line_number == 1001
    for path in [
        "src/removed.py",
        "src/truncated.py",
        "src/skipped.py",
        "../outside.py",
        "src/duplicate-lines.py",
        "src/old.py",
    ]:
        with pytest.raises(ValueError):
            page(state, snapshot, path, 10, unchanged)


def test_unchanged_pages_keep_lf_coordinates_and_duplicate_and_head_exclusions():
    state, snapshot = source_state([changed("src/a.py", 1100)])
    good = RetrievedFile(
        path="src/unchanged.py",
        content="bad\u2028record\n" + "ok\r\n" * 101,
        commit_sha=snapshot.head_sha,
        retrieval_reason="Constructed candidate",
    )
    duplicate = good.model_copy(update={"path": "src/duplicate.py"})
    stale = good.model_copy(update={"path": "src/stale.py", "commit_sha": "other-head"})
    unchanged = [good, duplicate, duplicate.model_copy(deep=True), stale]
    sources = api().selectable_reference_sources(state, snapshot, unchanged)
    assert [(s.file_path, s.eligible_line_count) for s in sources] == [
        ("src/a.py", 1100),
        ("src/unchanged.py", 101),
    ]
    result = page(state, snapshot, good.path, 1, unchanged, EvidenceSourceScope.UNCHANGED_CANDIDATE)
    assert [(line.line_number, line.excerpt) for line in result.lines] == [(102, "ok")]
    updated = append(state, snapshot, result.lines[0], unchanged_files=unchanged)
    assert updated.bundle.reviewer_selected_references[0].line_number == 102
    for path in ["src/duplicate.py", "src/stale.py"]:
        with pytest.raises(ValueError):
            page(state, snapshot, path, 0, unchanged, EvidenceSourceScope.UNCHANGED_CANDIDATE)


@pytest.mark.parametrize(
    "path,kind,level",
    [
        ("generated/output.py", EvidenceType.IMPLEMENTATION, EvidenceLevel.E1),
        ("unrelated/other.py", EvidenceType.IMPLEMENTATION, EvidenceLevel.E1),
        ("tests/test_late.py", EvidenceType.TEST, EvidenceLevel.E2),
    ],
)
def test_later_pages_remain_static_non_gating_context(path, kind, level):
    state, snapshot = source_state([changed(path, 1001)])
    selected = page(state, snapshot, path, 10).lines[0]
    assert selected.evidence_type is kind and selected.evidence_level is level
    before = state.model_dump(mode="json")
    updated = append(state, snapshot, selected)
    after = updated.model_dump(mode="json")
    after["bundle"]["reviewer_selected_references"] = []
    after["bundle"]["active_reviewer_selected_reference_ids"] = []
    assert before == after


def test_late_page_selection_revalidates_exact_line_and_active_context():
    state, snapshot = source_state([changed("src/a.py", 1001)])
    selected = page(state, snapshot, "src/a.py", 10).lines[0]
    for change in [
        {"excerpt": "invented"},
        {"line_number": 1002},
        {"source_scope": EvidenceSourceScope.UNCHANGED_CANDIDATE},
    ]:
        with pytest.raises(ValueError):
            append(state, snapshot, selected.model_copy(update=change))
    with pytest.raises(ValueError, match="stale"):
        append(state, snapshot, selected, expected_state_fingerprint="0" * 64)
    stale = snapshot.model_copy(update={"head_sha": "other-head"})
    with pytest.raises(ValueError):
        page(state, stale, "src/a.py", 10)
    with pytest.raises(ValueError):
        append(state, stale, selected)
    mutated = snapshot.model_copy(deep=True)
    mutated.files[0].lines[-1].content = "changed_source"
    with pytest.raises(ValueError):
        append(state, mutated, selected)


def test_duplicate_changed_paths_and_invalid_model_instances_fail_closed():
    state, snapshot = source_state([changed("src/a.py", 101)])
    duplicate = snapshot.model_copy(deep=True)
    duplicate.files.append(duplicate.files[0].model_copy(deep=True))
    with pytest.raises(ValueError):
        api().selectable_reference_sources(state, duplicate)
    with pytest.raises(ValueError):
        page(state, duplicate, "src/a.py")
    result = page(state, snapshot, "src/a.py")
    with pytest.raises(ValidationError):
        result.page_index = 1
    with pytest.raises(ValueError):
        type(result).model_validate(result.model_copy(update={"page_index": True}))
    with pytest.raises(ValueError):
        type(result.source).model_validate(
            result.source.model_copy(update={"eligible_line_count": -1})
        )
