"""Independent constructed attacks on informational final-acceptance projections."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.reviews.saved_comparison import (
    SavedComparisonUnavailable,
    locked_saved_comparison,
    prepare_saved_comparison,
)
from scopeproof_core.schemas.models import GateVerdict, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore

SNAPSHOT_FIELDS = (
    "repository", "pr_number", "review_id", "head_sha", "criteria_revision_number",
    "input_origin", "normalized_criteria_sha256", "criterion_ids",
    "recorded_final_acceptance", "event_context_status",
)


def acceptance_api():
    return import_module("scopeproof_core.reviews.final_acceptance_comparison")


def states(*, previous=False, current=True):
    return import_module("tests.final_acceptance_fixture").acceptance_comparison_states(
        previous=previous, current=current,
    )


def result():
    current, previous = states()
    return compare_reviews(previous.bundle, current.bundle)


def projection():
    current, previous = states()
    return acceptance_api().FinalAcceptanceComparison.from_bundles(previous.bundle, current.bundle)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field", SNAPSHOT_FIELDS)
def test_snapshot_requires_every_explicit_field_without_false_or_context_defaults(side, field):
    data = projection().model_dump(mode="json")
    del data[side][field]
    with pytest.raises(ValidationError):
        acceptance_api().FinalAcceptanceComparison.model_validate(data)


@pytest.mark.parametrize(
    "field", ["context_kind", "schema_version", "boundary", "previous", "current"],
)
def test_context_requires_explicit_fixed_metadata_and_both_snapshots(field):
    data = projection().model_dump(mode="json")
    del data[field]
    with pytest.raises(ValidationError):
        acceptance_api().FinalAcceptanceComparison.model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("recorded_final_acceptance", 0), ("recorded_final_acceptance", 1),
    ("recorded_final_acceptance", "true"), ("recorded_final_acceptance", "false"),
    ("recorded_final_acceptance", None),
    ("pr_number", True), ("pr_number", "7"), ("pr_number", 0),
    ("criteria_revision_number", True), ("criteria_revision_number", "1"),
    ("criteria_revision_number", 0), ("criteria_revision_number", -1),
    ("review_id", " \t"), ("head_sha", " \n"),
    ("normalized_criteria_sha256", "not-a-digest"),
    ("criterion_ids", ["AC-01", "AC-01"]),
    ("criterion_ids", ["AC-02", "AC-01"]), ("criterion_ids", [" "]),
    ("event_context_status", "authenticated"),
    ("actor", "Constructed invented actor"),
    ("timestamp", "2026-11-01T12:00:00Z"),
    ("rationale", "Constructed invented rationale"),
    ("event_id", "constructed-invented-event"),
])
def test_snapshot_rejects_coercion_bad_identity_and_invented_event_attribution(field, value):
    data = projection().current.model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        acceptance_api().FinalAcceptanceSnapshot.model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("context_kind", "authenticated_acceptance"), ("schema_version", 999),
    ("schema_version", True), ("schema_version", "1"),
    ("boundary", "Constructed forged correctness guarantee"),
    ("actor", "Constructed invented actor"),
])
def test_context_rejects_forged_fixed_metadata_or_actor(field, value):
    data = projection().model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        acceptance_api().FinalAcceptanceComparison.model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field,value", [
    ("repository", "constructed/foreign"), ("pr_number", 9876),
    ("review_id", "constructed-foreign-review"), ("head_sha", "f" * 40),
    ("criteria_revision_number", 9876), ("input_origin", "legacy_unknown"),
    ("normalized_criteria_sha256", "f" * 64),
    ("criterion_ids", ["AC-FOREIGN"]),
])
def test_outer_comparison_binds_every_acceptance_owner_field(side, field, value):
    data = result().model_dump(mode="json")
    data["final_acceptance_comparison"][side][field] = value
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("repository", "constructed/foreign"), ("pr_number", 9876),
    ("normalized_criteria_sha256", "f" * 64), ("criterion_ids", ["AC-FOREIGN"]),
])
def test_jointly_valid_foreign_projection_cannot_replace_owning_context(field, value):
    data = result().model_dump(mode="json")
    for side in ("previous", "current"):
        data["final_acceptance_comparison"][side][field] = value
    # Internal agreement must not bypass the independent owning identity chain.
    acceptance_api().FinalAcceptanceComparison.model_validate(data["final_acceptance_comparison"])
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


def test_acceptance_projection_requires_existing_decision_context():
    data = result().model_dump(mode="json")
    data["decision_context_comparison"] = None
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field,value", [
    ("recorded_final_acceptance", "false"), ("pr_number", True),
    ("event_context_status", "authenticated"),
])
def test_nested_constructed_instances_are_revalidated(side, field, value):
    context = projection()
    snapshot = getattr(context, side)
    forged = type(snapshot).model_construct(**{
        **snapshot.model_dump(mode="python"), field: value,
    })
    payload = context.model_dump(mode="python")
    payload[side] = forged
    with pytest.raises(ValidationError):
        acceptance_api().FinalAcceptanceComparison.model_validate(payload)


def test_outer_validation_rechecks_forged_context_instance():
    comparison = result()
    context = comparison.final_acceptance_comparison
    forged_snapshot = context.current.model_copy(update={"review_id": "constructed-foreign"})
    forged_context = context.model_copy(update={"current": forged_snapshot})
    payload = comparison.model_dump(mode="python")
    payload["final_acceptance_comparison"] = forged_context
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


def test_constructed_nested_snapshot_cannot_omit_the_recorded_boolean():
    context = projection()
    payload = context.current.model_dump(mode="python")
    del payload["recorded_final_acceptance"]
    forged = type(context.current).model_construct(**payload)
    with pytest.raises(ValidationError):
        type(context).model_validate({
            **context.model_dump(mode="python"), "current": forged,
        })


@pytest.mark.parametrize("side", ["previous", "current"])
def test_ready_gate_cannot_coexist_with_explicit_false_acceptance(side):
    current, previous = states(previous=False, current=False)
    payload = compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")
    payload[f"{side}_gate"] = GateVerdict.READY.value
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


@pytest.mark.parametrize(
    "gate", [GateVerdict.CONDITIONAL, GateVerdict.BLOCKED, GateVerdict.NEEDS_REVIEW],
)
@pytest.mark.parametrize("recorded", [False, True])
def test_nonready_gate_labels_do_not_invent_acceptance_rules(gate, recorded):
    current, previous = states(previous=recorded, current=recorded)
    payload = compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")
    payload["previous_gate"] = payload["current_gate"] = gate.value
    restored = ReviewComparison.model_validate(payload)
    assert restored.final_acceptance_comparison.previous.recorded_final_acceptance is recorded
    assert restored.final_acceptance_comparison.current.recorded_final_acceptance is recorded


@pytest.mark.parametrize(
    "previous,current", [(False, False), (False, True), (True, False), (True, True)],
)
def test_derived_change_and_availability_ignore_injected_serialized_claims(previous, current):
    current_state, previous_state = states(previous=previous, current=current)
    comparison = compare_reviews(previous_state.bundle, current_state.bundle)
    payload = comparison.model_dump(mode="json")
    payload["final_acceptance_compared"] = False
    payload["final_acceptance_comparison"]["recorded_value_changed"] = previous == current
    restored = ReviewComparison.model_validate(payload)
    assert restored.final_acceptance_compared is True
    assert restored.final_acceptance_comparison.recorded_value_changed is (previous != current)
    assert restored.final_acceptance_comparison.previous.recorded_final_acceptance is previous
    assert restored.final_acceptance_comparison.current.recorded_final_acceptance is current
    assert restored.previous_gate == restored.current_gate == GateVerdict.CONDITIONAL


@pytest.mark.parametrize("absence", ["missing", "null"])
def test_legacy_absence_cannot_be_promoted_to_false_values_or_available(absence):
    payload = result().model_dump(mode="json")
    if absence == "missing":
        del payload["final_acceptance_comparison"]
    else:
        payload["final_acceptance_comparison"] = None
    payload["final_acceptance_compared"] = True
    restored = ReviewComparison.model_validate(payload)
    assert restored.final_acceptance_comparison is None
    assert restored.final_acceptance_compared is False
    assert restored.model_dump(mode="json")["final_acceptance_comparison"] is None


def test_unknown_snapshot_revisions_stay_unknown_without_attribution_or_chronology():
    current, previous = states()
    before = current.model_dump_json(), previous.model_dump_json()
    old_bundle = previous.bundle.model_copy(
        update={"criteria_revision_number": "unknown", "file_scope_decisions": []}, deep=True,
    )
    # An unknown historical revision cannot own known-revision scope decisions.
    # Recompute its actual gate after removing that unavailable context.
    old_bundle.gate = evaluate_gate(
        old_bundle.review, old_bundle.criteria, old_bundle.findings,
        old_bundle.resolutions, old_bundle.evidence, old_bundle.file_scope_decisions,
    )
    context = compare_reviews(old_bundle, current.bundle).final_acceptance_comparison
    restored = type(context).model_validate_json(context.model_dump_json())
    assert restored.previous.criteria_revision_number == "unknown"
    assert restored.current.criteria_revision_number == current.bundle.criteria_revision_number
    for side in ("previous", "current"):
        snapshot = getattr(restored, side)
        assert snapshot.event_context_status == "unavailable_in_analysis_snapshot"
        assert set(snapshot.model_dump()) == set(SNAPSHOT_FIELDS)
    assert before == (current.model_dump_json(), previous.model_dump_json())


def test_projection_is_frozen_and_detached_from_bundles_and_its_other_side():
    current, _ = states()
    source = current.bundle
    before = source.model_dump_json()
    context = acceptance_api().FinalAcceptanceComparison.from_bundles(source, source)
    assert context.previous is not context.current
    assert isinstance(context.current.criterion_ids, tuple)
    with pytest.raises(ValidationError):
        context.current.recorded_final_acceptance = False
    source.review.final_acceptance = False
    source.review.review_id = "constructed-source-only-change"
    assert context.current.recorded_final_acceptance is True
    assert context.previous.recorded_final_acceptance is True
    assert context.current.review_id != source.review.review_id
    assert before != source.model_dump_json()


@pytest.mark.parametrize("side", ["previous", "current"])
def test_source_bundle_validation_is_not_bypassed_by_constructed_instances(side):
    current, previous = states()
    bundles = {"previous": previous.bundle, "current": current.bundle}
    original = bundles[side]
    bundles[side] = original.model_copy(update={
        "review": original.review.model_copy(update={"criteria_confirmed": False}),
    })
    with pytest.raises(ValueError):
        acceptance_api().FinalAcceptanceComparison.from_bundles(
            bundles["previous"], bundles["current"],
        )


@pytest.mark.parametrize("side", ["previous", "current"])
def test_acceptance_only_saved_change_expires_selection_with_gate_unchanged(tmp_path, side):
    current, previous = states()
    store = JsonReviewStore(tmp_path)
    store.save(previous)
    store.save(current)
    selection = prepare_saved_comparison(store, current, previous.review.review_id)
    target = previous if side == "previous" else current
    before_gate = target.bundle.gate.model_dump_json()
    before_bundle = target.bundle.model_dump(mode="json")

    def change_acceptance(state):
        return append_resolution(state, ResolutionEvent(
            event_id=f"constructed-safety-{side}-acceptance-change",
            final_acceptance=not state.review.final_acceptance,
            reviewer="CONSTRUCTED automatic safety-test actor",
            comment="Constructed acceptance-only change; no practitioner acceptance.",
            timestamp=datetime(2026, 11, 1, 12, tzinfo=UTC),
        ))

    updated, _ = store.mutate(target.review.review_id, change_acceptance)
    assert updated.bundle.gate.model_dump_json() == before_gate
    after_bundle = updated.bundle.model_dump(mode="json")
    assert before_bundle["review"].pop("final_acceptance") is not after_bundle["review"].pop(
        "final_acceptance"
    )
    assert before_bundle == after_bundle
    recorded_bytes = {path.name: path.read_bytes() for path in tmp_path.glob("*.json")}
    with pytest.raises(SavedComparisonUnavailable), locked_saved_comparison(store, selection):
        pytest.fail("stale acceptance-only selection yielded a comparison")
    assert {path.name: path.read_bytes() for path in tmp_path.glob("*.json")} == recorded_bytes
