"""Constructed latest-decision comparisons do not change review authority."""

from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    HumanResolution,
    RuntimeEvidence,
)
from tests.saved_comparison_fixture import saved_comparison_states

RECORDED_AT = datetime(2026, 10, 30, 12, tzinfo=UTC)


def context_type():
    return import_module(
        "scopeproof_core.reviews.decision_context_comparison"
    ).DecisionContextComparison


def decision_bundle(*, linked=True, decision=True):
    state, _ = saved_comparison_states()
    bundle = state.bundle.model_copy(deep=True)
    if decision:
        bundle.resolutions = [HumanResolution(
            criterion_id="AC-01", decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Constructed external observation; not genuine independent use.",
            reviewer="Constructed automatic actor", claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id="constructed-runtime-1" if linked else None,
            evidence_url="https://example.test/constructed-observation",
            timestamp=RECORDED_AT,
        )]
    bundle.runtime_evidence = [RuntimeEvidence(
        runtime_evidence_id="constructed-runtime-1" if linked else None,
        repository=bundle.review.repository if linked else None,
        pr_number=bundle.review.pr_number if linked else None,
        head_sha=bundle.review.head_sha if linked else None,
        criterion_id="AC-01", artifact_reference="https://example.test/constructed-observation",
        scenario="Constructed CSV scenario", environment="Constructed disposable environment",
        result="Constructed passed result", reviewer="Constructed automatic actor",
        evidence_level=EvidenceLevel.E3,
        limitations=["Constructed observation, not an independently executed test."],
        timestamp=RECORDED_AT,
    )]
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, bundle.file_scope_decisions,
    )
    return bundle


def test_complete_decision_and_runtime_context_is_detached_and_identity_bound():
    bundle = decision_bundle()
    before = bundle.model_dump_json()
    result = compare_reviews(bundle, bundle)
    assert result.decision_context_compared is True
    context = result.decision_context_comparison
    assert context.previous.review_id == bundle.review.review_id
    assert context.previous.head_sha == bundle.review.head_sha
    assert context.previous.criteria_revision_number == bundle.criteria_revision_number
    assert context.previous.resolutions == bundle.resolutions
    assert context.previous.runtime_evidence == bundle.runtime_evidence
    row, = context.record_changes
    assert row.kind == "identical_recorded_context"
    assert row.previous.runtime_link_status == "linked"
    assert row.previous.resolution == bundle.resolutions[0]
    assert row.current.runtime_evidence == bundle.runtime_evidence
    context.previous.resolutions[0].comment = "Changed detached projection"
    assert bundle.model_dump_json() == before


@pytest.mark.parametrize("field,value", [
    ("comment", "Constructed revised rationale"),
    ("evidence_url", "https://example.test/another-constructed-reference"),
    ("timestamp", RECORDED_AT + timedelta(seconds=1)),
])
def test_same_enum_resolution_context_changes_are_visible_without_new_enum_delta(field, value):
    previous = decision_bundle()
    current = previous.model_copy(deep=True)
    setattr(current.resolutions[0], field, value)
    before = previous.model_dump_json(), current.model_dump_json()
    result = compare_reviews(previous, current)
    row, = result.decision_context_comparison.record_changes
    assert row.kind == "recorded_context_changed"
    assert getattr(row.current.resolution, field) == value
    assert result.changed_human_resolutions == []
    assert result.criteria_requiring_decision_review == []
    assert result.previous_gate == result.current_gate
    assert before == (previous.model_dump_json(), current.model_dump_json())


@pytest.mark.parametrize("field,value", [
    ("artifact_reference", "https://example.test/revised-artifact"),
    ("scenario", "Constructed changed scenario"),
    ("environment", "Constructed changed environment"),
    ("result", "Constructed failed observation"),
    ("limitations", ["Constructed newly recorded limitation"]),
    ("timestamp", RECORDED_AT + timedelta(seconds=1)),
])
def test_same_enum_linked_runtime_changes_remain_recorded_context(field, value):
    previous = decision_bundle()
    current = previous.model_copy(deep=True)
    setattr(current.runtime_evidence[0], field, value)
    result = compare_reviews(previous, current)
    row, = result.decision_context_comparison.record_changes
    assert row.kind == "recorded_context_changed"
    assert getattr(row.current.runtime_evidence[0], field) == value
    assert result.changed_human_resolutions == []
    assert result.previous_gate == result.current_gate


def test_same_enum_changed_asserted_actor_level_and_runtime_link_are_visible():
    previous = decision_bundle()
    current = previous.model_copy(deep=True)
    resolution, runtime = current.resolutions[0], current.runtime_evidence[0]
    resolution.reviewer = runtime.reviewer = "Constructed second automatic actor"
    resolution.claimed_evidence_level = runtime.evidence_level = EvidenceLevel.E4
    resolution.runtime_evidence_id = runtime.runtime_evidence_id = "constructed-runtime-2"
    result = compare_reviews(previous, current)
    row, = result.decision_context_comparison.record_changes
    assert row.kind == "recorded_context_changed"
    assert row.current.runtime_link_status == "linked"
    assert row.current.resolution.reviewer == "Constructed second automatic actor"
    assert row.current.resolution.claimed_evidence_level is EvidenceLevel.E4
    assert result.changed_human_resolutions == []


def test_legacy_unlinked_observation_is_not_attached_by_matching_criterion_or_url():
    bundle = decision_bundle(linked=False)
    row, = compare_reviews(bundle, bundle).decision_context_comparison.record_changes
    assert row.previous.runtime_link_status == "legacy_unlinked"
    assert row.previous.resolution.runtime_evidence_id is None
    assert row.previous.runtime_evidence[0].runtime_evidence_id is None
    assert row.previous.runtime_evidence[0].head_sha is None


def test_runtime_without_resolution_is_context_with_no_inferred_decision():
    bundle = decision_bundle(decision=False)
    row, = compare_reviews(bundle, bundle).decision_context_comparison.record_changes
    assert row.previous.resolution is None
    assert row.previous.runtime_link_status == "no_link"
    assert len(row.previous.runtime_evidence) == 1


def test_known_empty_and_legacy_unavailable_remain_distinct():
    state, _ = saved_comparison_states()
    result = compare_reviews(state.bundle, state.bundle)
    assert result.decision_context_compared is True
    assert result.decision_context_comparison.record_changes == []
    payload = result.model_dump(mode="json")
    payload.pop("decision_context_comparison")
    payload["decision_context_compared"] = True
    legacy = ReviewComparison.model_validate(payload)
    assert legacy.decision_context_compared is False
    assert legacy.decision_context_comparison is None


def test_only_previous_and_only_current_describe_record_presence():
    with_records = decision_bundle()
    state, _ = saved_comparison_states()
    empty = state.bundle
    assert (
        context_type().from_bundles(with_records, empty).record_changes[0].kind == "only_previous"
    )
    assert context_type().from_bundles(empty, with_records).record_changes[0].kind == "only_current"


def test_computed_changes_and_link_status_are_recomputed_on_round_trip():
    context = context_type().from_bundles(decision_bundle(), decision_bundle())
    payload = context.model_dump(mode="json")
    payload["record_changes"] = [{"kind": "only_current"}]
    restored = context_type().model_validate(payload)
    assert restored.record_changes[0].kind == "identical_recorded_context"
    assert restored.record_changes[0].current.runtime_link_status == "linked"


def test_existing_comparison_fields_remain_identical_when_only_runtime_context_changes():
    previous = decision_bundle()
    current = previous.model_copy(deep=True)
    current.runtime_evidence[0].limitations.append("Constructed extra limitation")
    unchanged = compare_reviews(previous, previous).model_dump(mode="json")
    changed = compare_reviews(previous, current).model_dump(mode="json")
    for payload in (unchanged, changed):
        payload.pop("decision_context_comparison")
        payload.pop("decision_context_compared")
    assert changed == unchanged
