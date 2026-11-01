"""Loaded scope context must not borrow authority or expose excluded source."""

from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    IngestionState,
    LineChangeType,
    RepositoryVisibility,
)


def context(**kwargs):
    return import_module("tests.scope_preview_fixture").scope_preview_context(**kwargs)


def preview(state, snapshot, path="notes.md", **kwargs):
    return import_module("scopeproof_core.reviews.scope_file_preview").build_scope_file_preview(
        state, snapshot, path, **kwargs
    )


def matching_context(*, lines=None, skipped=False, truncated=False, partial=False):
    """Bind constructed source facts to a deterministic test-only analysis."""
    state, snapshot = context(lines=lines)
    snapshot = snapshot.model_copy(deep=True)
    selected_file = next(file for file in snapshot.files if file.path == "notes.md")
    selected_file.truncated = truncated
    if partial or skipped or truncated:
        snapshot.ingestion_state = IngestionState.PARTIAL
        snapshot.warnings = ["Constructed partial-source limitation"]
    if skipped:
        snapshot.skipped_files = [selected_file.path]
    state = state.model_copy(deep=True)
    state.review.ingestion_state = snapshot.ingestion_state
    state.review.ingestion_warnings = list(snapshot.warnings)
    state.review.skipped_files = list(snapshot.skipped_files)
    state.review.changed_file_inventory = snapshot.scope_inventory()
    assert state.bundle is not None
    state.bundle.review = state.review.model_copy(deep=True)
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
        state.bundle.evidence,
        state.bundle.file_scope_decisions,
    )
    return validated_review_state(state), snapshot


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository", "another/repository"),
        ("pr_number", 999),
        ("base_sha", "other-base"),
        ("head_sha", "other-head"),
        ("repository_visibility", RepositoryVisibility.VERIFIED_PUBLIC),
    ],
)
def test_preview_rejects_source_identity_mismatch(field, value):
    state, snapshot = context()
    source = snapshot.model_copy(update={field: value}, deep=True)
    with pytest.raises(ValueError):
        preview(state, source)


def test_preview_rejects_different_ci_counts_even_when_check_state_matches():
    state, snapshot = context()
    source = snapshot.model_copy(deep=True)
    source.ci_observation.total_check_runs += 1
    source.ci_observation.successful_check_runs += 1
    assert source.check_state == snapshot.check_state
    with pytest.raises(ValueError):
        preview(state, source)


@pytest.mark.parametrize("change", ["status", "previous_path", "extra", "duplicate"])
def test_matching_head_does_not_hide_inventory_conflicts(change):
    state, snapshot = context()
    source = snapshot.model_copy(deep=True)
    if change == "status":
        source.files[0].status = "renamed"
    elif change == "previous_path":
        source.files[0].previous_path = "former-notes.md"
    elif change == "extra":
        source.files.append(ChangedFile(path="extra.md", status="added"))
    else:
        source.files.append(source.files[0].model_copy(deep=True))
    with pytest.raises(ValueError):
        preview(state, source)


@pytest.mark.parametrize("change", ["unknown_inventory", "no_analysis", "unconfirmed"])
def test_preview_requires_confirmed_active_analysis_and_known_inventory(change):
    state, snapshot = context()
    state = state.model_copy(deep=True)
    if change == "unknown_inventory":
        state.review.changed_file_inventory = None
        state.bundle.review.changed_file_inventory = None
    elif change == "no_analysis":
        state.bundle = None
    else:
        state.review.criteria_confirmed = False
        state.criteria_revision.confirmed = False
    with pytest.raises(ValueError):
        preview(state, snapshot)


@pytest.mark.parametrize(
    "path", ["missing.md", "../notes.md", "a/../notes.md", "./notes.md", "a//notes.md", "/notes.md",
             "a\\notes.md", "notes.md\x00", None, b"notes.md", 1]
)
def test_preview_never_normalizes_or_falls_back_from_bad_path(path):
    state, snapshot = context()
    with pytest.raises(ValueError):
        preview(state, snapshot, path)


@pytest.mark.parametrize("page_index", [-1, True, "0", 0.0, None, 1])
def test_preview_page_request_rejects_coercion_and_missing_page(page_index):
    state, snapshot = context()
    with pytest.raises(ValueError):
        preview(state, snapshot, page_index=page_index)


@pytest.mark.parametrize("kind", [LineChangeType.ADDED, LineChangeType.REMOVED])
def test_duplicate_coordinates_on_either_side_expose_no_source(kind):
    state, snapshot = matching_context(lines=[
        ChangedLine(change_type=kind, line_number=7, content="first"),
        ChangedLine(change_type=kind, line_number=7, content="conflicting"),
    ])
    result = preview(state, snapshot)
    assert result.availability == "ambiguous_coordinates"
    assert result.lines == ()


def test_context_and_added_records_share_the_same_head_coordinate_space():
    state, snapshot = matching_context(lines=[
        ChangedLine(change_type=LineChangeType.CONTEXT, line_number=7, content="context"),
        ChangedLine(change_type=LineChangeType.ADDED, line_number=7, content="conflicting"),
    ])
    result = preview(state, snapshot)
    assert result.availability == "ambiguous_coordinates"
    assert result.lines == ()


def test_removal_and_addition_can_use_the_same_number_on_different_sides():
    state, snapshot = matching_context(lines=[
        ChangedLine(change_type=LineChangeType.REMOVED, line_number=7, content="old"),
        ChangedLine(change_type=LineChangeType.ADDED, line_number=7, content="new"),
    ])
    result = preview(state, snapshot)
    assert result.availability == "available"
    assert [(line.change_type, line.line_number, line.content) for line in result.lines] == [
        (LineChangeType.REMOVED, 7, "old"),
        (LineChangeType.ADDED, 7, "new"),
    ]


def test_multirecord_content_cannot_invent_physical_line_coordinates():
    state, snapshot = matching_context(lines=[
        ChangedLine(change_type=LineChangeType.ADDED, line_number=1, content="first\nsecond"),
    ])
    result = preview(state, snapshot)
    assert result.availability == "ambiguous_coordinates"
    assert result.lines == ()


def test_carriage_return_content_preserves_loaded_record_and_coordinates():
    state, snapshot = matching_context(lines=[
        ChangedLine(change_type=LineChangeType.ADDED, line_number=7, content="first\rsecond"),
    ])
    before = state.model_dump_json(), snapshot.model_dump_json()
    result = preview(state, snapshot)
    assert result.availability == "available"
    assert [(line.line_number, line.content) for line in result.lines] == [(7, "first\rsecond")]
    assert (state.model_dump_json(), snapshot.model_dump_json()) == before


@pytest.mark.parametrize("limitation", ["skipped", "truncated"])
def test_ingestion_exclusions_never_expose_retained_line_content(limitation):
    state, snapshot = matching_context(**{limitation: True})
    assert next(file for file in snapshot.files if file.path == "notes.md").lines
    result = preview(state, snapshot)
    assert result.availability == limitation
    assert result.lines == ()


def test_matching_partial_source_can_be_read_without_relaxing_its_gate():
    state, snapshot = matching_context(partial=True)
    before = state.model_dump_json(), snapshot.model_dump_json()
    result = preview(state, snapshot)
    assert result.availability == "available" and result.lines
    assert state.review.ingestion_state is IngestionState.PARTIAL
    assert (state.model_dump_json(), snapshot.model_dump_json()) == before


@pytest.mark.parametrize("change", ["warnings", "skipped_files", "ingestion_state"])
def test_same_head_cannot_hide_different_ingestion_limitations(change):
    state, snapshot = matching_context(partial=True)
    source = snapshot.model_copy(deep=True)
    if change == "warnings":
        source.warnings.append("Additional source limitation")
    elif change == "skipped_files":
        source.skipped_files = ["other.md"]
    else:
        source.ingestion_state = IngestionState.COMPLETE
        source.warnings = []
    with pytest.raises(ValueError):
        preview(state, source)


def test_utf8_byte_limit_keeps_exact_boundary_and_marks_oversized_record():
    state, snapshot = matching_context(lines=[
        ChangedLine(change_type=LineChangeType.ADDED, line_number=2, content="é" * 2048),
        ChangedLine(change_type=LineChangeType.ADDED, line_number=9, content="é" * 2049),
        ChangedLine(change_type=LineChangeType.ADDED, line_number=20, content="after"),
    ])
    before = state.model_dump_json(), snapshot.model_dump_json()
    result = preview(state, snapshot)
    assert result.availability == "available" and result.total_line_count == 3
    assert [(line.line_number, line.content) for line in result.lines] == [
        (2, "é" * 2048), (9, None), (20, "after"),
    ]
    assert (state.model_dump_json(), snapshot.model_dump_json()) == before


def test_projection_is_frozen_and_revalidates_unavailable_source_leak():
    state, snapshot = context()
    result = preview(state, snapshot)
    with pytest.raises(ValidationError):
        result.path = "retargeted.md"
    with pytest.raises(ValueError):
        type(result).model_validate(result.model_copy(update={"availability": "skipped"}))
    with pytest.raises(ValueError):
        type(result).model_validate({**result.model_dump(), "invented_evidence": "runtime"})
