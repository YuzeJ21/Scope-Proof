"""Literal file search preserves source policy, text and physical Git coordinates."""

import pytest

from scopeproof_core.reviews import selected_references as references
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    EvidenceSourceScope,
    LineChangeType,
)
from tests.reviews.test_selected_references import source_state


def search_fixture():
    return source_state([ChangedFile(
        path="src/search.py", status="modified", lines=[
            ChangedLine(change_type=LineChangeType.ADDED, line_number=number, content=text)
            for number, text in [
                (10, "  Match.*[x]  "), (200, "match plain"),
                (1002, "Straße = 'Kept'\t"),
                (1005, "<img src=x onerror=bad> **Match**"),
                (1006, ""), (1007, "x" * 4097),
            ]
        ],
    )])


def search(state, snapshot, **kwargs):
    return references.search_reference_page(
        state, snapshot, source_scope=EvidenceSourceScope.CHANGED_FILE,
        file_path="src/search.py", **kwargs,
    )


@pytest.mark.parametrize("query,numbers", [
    ("", [10, 200, 1002, 1005]), ("MATCH", [10, 200, 1005]),
    (".*[x]", [10]), ("STRASSE", [1002]), ("  ", [10]), ("^match$", []),
])
def test_search_is_literal_casefolded_and_preserves_exact_source(tmp_path, query, numbers):
    state, snapshot = search_fixture()
    before = state.model_dump_json(), snapshot.model_dump_json()
    page = search(state, snapshot, query=query)
    assert [line.line_number for line in page.lines] == numbers
    assert page.source.eligible_line_count == 4
    assert page.matching_line_count == len(numbers)
    assert page.page_count == (1 if numbers else 0)
    assert page.query == query
    if numbers == [10]:
        assert page.lines[0].excerpt == "  Match.*[x]  "
    if numbers == [1002]:
        assert page.lines[0].excerpt == "Straße = 'Kept'\t"
    assert before == (state.model_dump_json(), snapshot.model_dump_json())


def test_search_reaches_later_source_without_global_cutoff_and_pages_matches():
    state, snapshot = source_state([ChangedFile(
        path="src/search.py", status="modified", lines=[
            ChangedLine(change_type=LineChangeType.ADDED, line_number=index * 2,
                        content=f"CONSTRUCTED needle line {index}")
            for index in range(1, 1204)
        ],
    )])
    first = search(state, snapshot, query="needle", page_index=0)
    last = search(state, snapshot, query="needle", page_index=12)
    assert (first.source.eligible_line_count, first.matching_line_count) == (1203, 1203)
    assert first.page_count == 13 and len(first.lines) == 100
    assert [line.line_number for line in last.lines] == [2402, 2404, 2406]
    exact = search(state, snapshot, query="needle line 1203")
    assert [line.line_number for line in exact.lines] == [2406]
    with pytest.raises(ValueError):
        search(state, snapshot, query="needle", page_index=13)


@pytest.mark.parametrize("query", [None, 1, True, "x" * 201, "界" * 201])
def test_query_limits_and_types_are_validated_before_search(query):
    state, snapshot = search_fixture()
    with pytest.raises(ValueError):
        search(state, snapshot, query=query)


def test_exact_query_bound_is_accepted_without_truncation():
    state, snapshot = search_fixture()
    page = search(state, snapshot, query="界" * 200)
    assert page.query == "界" * 200 and page.lines == ()


@pytest.mark.parametrize("page_index", [-1, True, 0.0, "0", 1])
def test_no_match_and_invalid_pages_never_default_to_another_page(page_index):
    state, snapshot = search_fixture()
    with pytest.raises(ValueError):
        search(state, snapshot, query="missing", page_index=page_index)


def test_unavailable_file_does_not_fall_back_to_available_source():
    state, snapshot = search_fixture()
    with pytest.raises(ValueError):
        references.search_reference_page(
            state, snapshot, source_scope=EvidenceSourceScope.CHANGED_FILE,
            file_path="src/absent.py", query="Match",
        )


def test_result_schema_rejects_forged_membership_counts_or_coordinates():
    state, snapshot = search_fixture()
    page = search(state, snapshot, query="match")
    for field, value in [("query", "absent"), ("matching_line_count", 5),
                         ("matching_line_count", 0), ("page_index", 1)]:
        payload = page.model_dump(mode="python")
        payload[field] = value
        with pytest.raises(ValueError):
            references.SelectableReferenceSearchPage.model_validate(payload)
    payload = page.model_dump(mode="python")
    payload["lines"] = tuple(reversed(payload["lines"]))
    with pytest.raises(ValueError):
        references.SelectableReferenceSearchPage.model_validate(payload)
