"""Loaded static diff context, without source execution or implicit decisions."""

import pytest

from scopeproof_core.schemas.models import ChangedLine, LineChangeType
from tests.scope_preview_fixture import scope_preview_context


def preview(state, snapshot, **kwargs):
    from scopeproof_core.reviews.scope_file_preview import build_scope_file_preview

    return build_scope_file_preview(state, snapshot, "notes.md", **kwargs)


def test_base_and_head_coordinates_and_gaps_are_preserved_without_mutation():
    state, snapshot = scope_preview_context()
    before = state.model_dump_json(), snapshot.model_dump_json()
    result = preview(state, snapshot)
    assert result.availability == "available" and result.total_line_count == 3
    assert [(line.change_type.value, line.line_number) for line in result.lines] == [
        ("removed", 20), ("added", 21), ("context", 50),
    ]
    assert result.lines[1].content == "CONSTRUCTED new note <img src=x> **Ready**"
    assert result.path == "notes.md" and result.status == "modified"
    assert result.repository == state.review.repository
    assert result.head_sha == state.review.head_sha and result.base_sha == state.review.base_sha
    assert (state.model_dump_json(), snapshot.model_dump_json()) == before


@pytest.mark.parametrize("status,previous_path", [
    ("added", None), ("removed", None), ("renamed", "old/notes.md"),
    ("copied", "old/notes.md"),
])
def test_file_status_and_explicit_rename_context_remain_recorded(status, previous_path):
    state, snapshot = scope_preview_context(status=status, previous_path=previous_path)
    result = preview(state, snapshot)
    assert result.status == status and result.previous_path == previous_path
    assert result.lines[0].change_type is LineChangeType.REMOVED


def test_pages_use_stored_diff_record_order_and_do_not_silently_cut_off_at_100():
    lines = [ChangedLine(change_type=LineChangeType.ADDED, line_number=index + 10,
                         content=f"CONSTRUCTED record {index}") for index in range(205)]
    state, snapshot = scope_preview_context(lines=lines)
    for page, count, first, last in [(0, 100, 10, 109), (1, 100, 110, 209), (2, 5, 210, 214)]:
        result = preview(state, snapshot, page_index=page)
        assert result.page_count == 3 and result.total_line_count == 205
        assert len(result.lines) == count
        assert (result.lines[0].line_number, result.lines[-1].line_number) == (first, last)
    with pytest.raises(ValueError):
        preview(state, snapshot, page_index=3)


def test_long_line_is_an_explicit_omission_not_a_truncated_or_normalized_excerpt():
    state, snapshot = scope_preview_context(lines=[
        ChangedLine(change_type=LineChangeType.ADDED, line_number=1, content="x" * 4096),
        ChangedLine(change_type=LineChangeType.ADDED, line_number=2, content="x" * 4097),
    ])
    result = preview(state, snapshot)
    assert result.lines[0].content == "x" * 4096
    assert result.lines[1].content is None and result.lines[1].line_number == 2


@pytest.mark.parametrize("kind,expected", [
    ("skipped", "skipped"), ("truncated", "truncated"),
    ("no_lines", "no_lines"), ("unsupported_status", "unsupported_status"),
    ("duplicate", "ambiguous_coordinates"),
])
def test_uninspectable_content_is_explicitly_unavailable(kind, expected):
    state, snapshot = scope_preview_context()
    if kind == "skipped":
        from scopeproof_core.gates.evaluator import evaluate_gate
        from scopeproof_core.schemas.models import IngestionState

        snapshot.skipped_files = ["notes.md"]
        snapshot.ingestion_state = IngestionState.PARTIAL
        state.review.skipped_files = ["notes.md"]
        state.review.ingestion_state = IngestionState.PARTIAL
        state.bundle.review = state.review.model_copy(deep=True)
        state.bundle.gate = evaluate_gate(
            state.review, state.bundle.criteria, state.bundle.findings,
            state.bundle.resolutions, state.bundle.evidence,
        )
    elif kind == "truncated":
        snapshot.files[-1].truncated = True
    elif kind == "no_lines":
        snapshot.files[-1].lines = []
    elif kind == "unsupported_status":
        snapshot.files[-1].status = "binary"
        state.review.changed_file_inventory.files[-1].status = "binary"
        state.bundle.review = state.review.model_copy(deep=True)
    else:
        snapshot.files[-1].lines.append(snapshot.files[-1].lines[1].model_copy(deep=True))
    result = preview(state, snapshot)
    assert result.availability == expected and not result.lines


def test_models_reject_unvalidated_copy_tampering_on_round_trip():
    from scopeproof_core.reviews.scope_file_preview import ScopeFilePreview

    state, snapshot = scope_preview_context()
    result = preview(state, snapshot)
    forged = result.model_copy(update={"lines": (), "page_index": 99})
    with pytest.raises(ValueError):
        ScopeFilePreview.model_validate(forged)
