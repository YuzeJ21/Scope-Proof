"""Constructed selected-reference comparisons preserve recorded, non-gating context."""

from datetime import timedelta
from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.reporting.exporters import export_comparison_json
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from tests.reviews.test_selected_references import append, source_state


def comparison_type():
    return import_module(
        "scopeproof_core.reviews.selected_reference_comparison"
    ).SelectedReferenceComparison


def constructed_pair():
    state, snapshot = source_state()
    selected = append(
        state,
        snapshot,
        reviewer="Constructed context reviewer",
        rationale="Constructed source context for comparison only.",
    )
    return state.bundle, selected.bundle


def projection(previous, current):
    return comparison_type().from_bundles(previous, current)


def counts(value):
    return value.change_counts.model_dump()


def test_new_comparison_includes_recorded_context_and_detaches_full_input():
    previous, current = constructed_pair()
    before = previous.model_dump_json(), current.model_dump_json()
    result = compare_reviews(previous, current)
    assert result.reviewer_selected_references_compared is True
    assert result.selected_reference_comparison.previous == []
    assert result.selected_reference_comparison.current == current.reviewer_selected_references
    assert counts(result.selected_reference_comparison) == {
        "identical_record": 0,
        "only_previous": 0,
        "only_current": 1,
    }
    assert before == (previous.model_dump_json(), current.model_dump_json())
    result.selected_reference_comparison.current.clear()
    assert len(current.reviewer_selected_references) == 1


def test_selected_context_does_not_change_automatic_gate_or_decision_review_projection():
    state, snapshot = source_state()
    state = append_resolution(
        state,
        ResolutionEvent(
            criterion_id=state.bundle.criteria[0].criterion_id,
            decision=HumanDecision.REJECTED_FINDING,
            reviewer="Constructed decision reviewer",
            comment="Constructed decision context.",
        ),
    )
    selected = append(state, snapshot, reviewer="Constructed reference reviewer")
    before = state.model_dump_json(), selected.model_dump_json()
    automatic = compare_reviews(state.bundle, state.bundle).model_dump(mode="json")
    contextual = compare_reviews(state.bundle, selected.bundle).model_dump(mode="json")
    for payload in (automatic, contextual):
        payload.pop("selected_reference_comparison", None)
        payload.pop("reviewer_selected_references_compared", None)
    assert contextual == automatic
    assert before == (state.model_dump_json(), selected.model_dump_json())


def test_empty_new_snapshots_are_available_but_legacy_projection_is_unknown():
    previous, _ = constructed_pair()
    result = compare_reviews(previous, previous)
    assert result.reviewer_selected_references_compared is True
    assert result.selected_reference_comparison.previous == []
    assert result.selected_reference_comparison.current == []
    data = result.model_dump(mode="json")
    data.pop("selected_reference_comparison")
    data.pop("reviewer_selected_references_compared")
    legacy = ReviewComparison.model_validate(data)
    assert legacy.selected_reference_comparison is None
    assert legacy.reviewer_selected_references_compared is False


def test_identical_complete_record_is_preserved_on_both_sides():
    _, current = constructed_pair()
    context = projection(current, current)
    assert counts(context) == {"identical_record": 1, "only_previous": 0, "only_current": 0}
    (change,) = context.record_changes
    assert change.kind == "identical_record"
    assert change.previous == change.current == current.reviewer_selected_references[0]


@pytest.mark.parametrize("field", ["reviewer", "rationale", "selected_at", "reference_id"])
def test_full_record_metadata_changes_are_two_one_sided_records(field):
    _, previous = constructed_pair()
    current = previous.model_copy(deep=True)
    reference = current.reviewer_selected_references[0]
    replacement = (
        reference.selected_at + timedelta(seconds=1)
        if field == "selected_at"
        else "Constructed changed metadata"
    )
    current.reviewer_selected_references[0] = reference.model_copy(update={field: replacement})
    context = projection(previous, current)
    assert counts(context) == {"identical_record": 0, "only_previous": 1, "only_current": 1}
    assert {change.kind for change in context.record_changes} == {"only_previous", "only_current"}
    for change in context.record_changes:
        assert (change.previous is None) != (change.current is None)


def test_identical_excerpt_at_changed_head_never_implies_continuity():
    _, previous = constructed_pair()
    current = previous.model_copy(deep=True)
    old_head = current.review.head_sha
    new_head = "b" * 40
    current.review.head_sha = new_head
    current.review.changed_file_inventory.head_sha = new_head
    for item in current.evidence:
        item.commit_sha = new_head
        item.permalink = item.permalink.replace(old_head, new_head)
    ref = current.reviewer_selected_references[0]
    current.reviewer_selected_references[0] = ref.model_copy(
        update={
            "head_sha": new_head,
            "permalink": ref.permalink.replace(old_head, new_head),
        }
    )
    context = projection(previous, current)
    assert context.previous[0].excerpt == context.current[0].excerpt
    assert counts(context) == {"identical_record": 0, "only_previous": 1, "only_current": 1}


def test_shuffled_source_order_has_canonical_snapshots_and_json():
    state, snapshot = source_state()
    module = import_module("scopeproof_core.reviews.selected_references")
    lines = module.selectable_reference_lines(state, snapshot)
    state = append(state, snapshot, selected=lines[0], reviewer="Constructed reviewer one")
    state = append(state, snapshot, selected=lines[1], reviewer="Constructed reviewer two")
    forward = projection(state.bundle, state.bundle)
    shuffled = state.bundle.model_copy(deep=True)
    shuffled.reviewer_selected_references.reverse()
    backward = projection(shuffled, shuffled)
    assert forward.model_dump_json() == backward.model_dump_json()


def test_serialized_derived_values_are_ignored_and_recomputed():
    _, current = constructed_pair()
    context = projection(current, current)
    data = context.model_dump(mode="json")
    data["record_changes"] = [{"kind": "invented"}]
    data["change_counts"] = {"identical_record": -1, "only_previous": 99, "only_current": 99}
    assert comparison_type().model_validate(data).model_dump_json() == context.model_dump_json()


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("duplicate_kind", ["id", "location", "limit"])
def test_snapshot_duplicate_identity_location_and_collection_limits_reject(side, duplicate_kind):
    _, bundle = constructed_pair()
    data = projection(bundle, bundle).model_dump(mode="json")
    ref = data[side][0]
    if duplicate_kind == "limit":
        data[side] = [
            dict(
                ref,
                reference_id=f"constructed-{i}",
                line_number=i + 1,
                permalink=ref["permalink"].split("#")[0] + f"#L{i + 1}-L{i + 1}",
            )
            for i in range(33)
        ]
    else:
        duplicate = dict(ref)
        if duplicate_kind == "location":
            duplicate["reference_id"] = "constructed-distinct-id"
        else:
            duplicate["line_number"] += 1
            number = duplicate["line_number"]
            duplicate["permalink"] = ref["permalink"].split("#")[0] + f"#L{number}-L{number}"
        data[side].append(duplicate)
    with pytest.raises(ValidationError):
        comparison_type().model_validate(data)


@pytest.mark.parametrize("field,value", [("repository", "foreign/repository"), ("pr_number", 999)])
def test_context_rejects_foreign_repository_or_pr(field, value):
    _, bundle = constructed_pair()
    data = projection(bundle, bundle).model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        comparison_type().model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("review_id", "constructed-foreign-owner"),
        ("criteria_revision_number", 999),
        ("criterion_id", "AC-CONSTRUCTED-UNKNOWN"),
    ],
)
def test_outer_projection_rejects_reference_not_owned_by_scope_snapshot(side, field, value):
    _, bundle = constructed_pair()
    data = compare_reviews(bundle, bundle).model_dump(mode="json")
    data["selected_reference_comparison"][side][0][field] = value
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


def test_selected_context_requires_scope_identity():
    _, bundle = constructed_pair()
    data = compare_reviews(bundle, bundle).model_dump(mode="json")
    data["file_scope"] = None
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("identity", ["head", "digest"])
def test_outer_projection_rejects_internally_valid_reference_with_wrong_scope_identity(
    side, identity
):
    _, bundle = constructed_pair()
    data = compare_reviews(bundle, bundle).model_dump(mode="json")
    ref = data["selected_reference_comparison"][side][0]
    if identity == "head":
        new_head = "c" * 40
        ref["permalink"] = ref["permalink"].replace(ref["head_sha"], new_head)
        ref["head_sha"] = new_head
    else:
        ref["confirmed_criteria_sha256"] = "d" * 64
        ref["criteria_source_provenance"]["normalized_criteria_sha256"] = "d" * 64
    # This rejection must come from the outer comparison relationship, rather than
    # a malformed standalone source record.
    type(bundle.reviewer_selected_references[0]).model_validate(ref)
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


def test_incompatible_criteria_source_identity_rejects_even_when_digest_matches():
    _, bundle = constructed_pair()
    data = compare_reviews(bundle, bundle).model_dump(mode="json")
    data["selected_reference_comparison"]["current"][0]["criteria_source_provenance"][
        "source_uri"
    ] = "https://example.test/constructed-different-source"
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


def test_export_revalidation_rejects_mutated_nested_ownership():
    _, bundle = constructed_pair()
    result = compare_reviews(bundle, bundle)
    reference = result.selected_reference_comparison.current[0]
    result.selected_reference_comparison.current[0] = reference.model_copy(
        update={
            "review_id": "constructed-tampered-owner",
        }
    )
    with pytest.raises(ValidationError):
        export_comparison_json(result)


def test_one_sided_reference_source_uri_is_bound_to_recorded_owner_provenance():
    previous, current = constructed_pair()
    data = compare_reviews(previous, current).model_dump(mode="json")
    ref = data["selected_reference_comparison"]["current"][0]
    ref["criteria_source_provenance"]["source_uri"] = (
        "https://example.test/constructed-unrelated-source"
    )
    type(current.reviewer_selected_references[0]).model_validate(ref)
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


def test_empty_snapshots_still_retain_both_criteria_source_provenances():
    previous, _ = constructed_pair()
    context = projection(previous, previous)
    assert context.previous_criteria_source_provenance == previous.review.criteria_source_provenance
    assert context.current_criteria_source_provenance == previous.review.criteria_source_provenance


def test_compatible_source_with_different_confirmation_actor_is_record_change():
    _, previous = constructed_pair()
    current = previous.model_copy(deep=True)
    provenance = current.review.criteria_source_provenance.model_copy(
        update={
            "confirmed_by": "Constructed different criteria confirmer",
        }
    )
    current.review.criteria_source_provenance = provenance
    current.reviewer_selected_references[0] = current.reviewer_selected_references[0].model_copy(
        update={"criteria_source_provenance": provenance.model_copy(deep=True)}
    )
    result = compare_reviews(previous, current)
    assert counts(result.selected_reference_comparison) == {
        "identical_record": 0,
        "only_previous": 1,
        "only_current": 1,
    }
    assert result.selected_reference_comparison.current[0].criteria_source_provenance == provenance


@pytest.mark.parametrize(
    "contradiction",
    [
        "foreign_path",
        "skipped_path",
        "removed_path",
        "unchanged_inventory_path",
        "unchanged_previous_rename_path",
    ],
)
def test_export_rejects_reference_contradicting_inspected_scope(contradiction):
    previous, current = constructed_pair()
    data = compare_reviews(previous, current).model_dump(mode="json")
    ref = data["selected_reference_comparison"]["current"][0]
    scope = data["file_scope"]["current"]
    original_path = ref["file_path"]
    if contradiction == "foreign_path":
        ref["file_path"] = "src/constructed-outside-inventory.py"
    elif contradiction == "skipped_path":
        scope["skipped_files"] = [original_path]
        scope["ingestion_state"] = "partial"
    elif contradiction == "removed_path":
        scope["inventory"]["files"][0]["status"] = "removed"
    elif contradiction == "unchanged_inventory_path":
        ref["source_scope"] = "unchanged_candidate"
    else:
        old_path = "src/constructed-previous-name.py"
        scope["inventory"]["files"][0].update(status="renamed", previous_path=old_path)
        ref["source_scope"] = "unchanged_candidate"
        ref["file_path"] = old_path
    ref["permalink"] = ref["permalink"].replace(original_path, ref["file_path"])
    type(current.reviewer_selected_references[0]).model_validate(ref)
    # Scope metadata itself remains valid; the contradiction is the retained
    # selected record's relationship to that metadata.
    without_context = dict(data, selected_reference_comparison=None)
    ReviewComparison.model_validate(without_context)
    result = compare_reviews(previous, current)
    result.selected_reference_comparison = comparison_type().model_validate(
        data["selected_reference_comparison"]
    )
    result.file_scope = type(result.file_scope).model_validate(data["file_scope"])
    with pytest.raises(ValidationError):
        export_comparison_json(result)
