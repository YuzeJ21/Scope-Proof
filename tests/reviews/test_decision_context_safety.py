"""Independent constructed attacks on recorded decision context boundaries."""

from __future__ import annotations

import builtins
import io
import os
import socket
import subprocess
import urllib.request
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from pydantic import ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import export_comparison_json
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    HumanResolution,
    RepositoryVisibility,
    ReviewBundle,
    ReviewInputOrigin,
    RuntimeEvidence,
)
from tests.reviews.test_comparison import bundle_with, evidence

RECORDED_AT = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
RESOLUTION_FIELDS = (
    "criterion_id", "decision", "comment", "evidence_url", "claimed_evidence_level",
    "runtime_evidence_id", "reviewer", "timestamp",
)
RUNTIME_FIELDS = (
    "runtime_evidence_id", "repository", "pr_number", "head_sha", "criterion_id",
    "artifact_reference", "scenario", "timestamp", "environment", "result", "reviewer",
    "evidence_level", "limitations",
)


def context_type():
    return import_module(
        "scopeproof_core.reviews.decision_context_comparison"
    ).DecisionContextComparison


def constructed_bundle(*, linked=True, legacy=False):
    """Use real schema/gate boundaries with explicit automated attribution."""
    head = "a" * 40
    bundle = bundle_with(
        evidence("constructed-evidence-1", sha=head, criterion_id="AC-01"),
        evidence("constructed-evidence-2", sha=head, criterion_id="AC-02"),
        head_sha=head,
    )
    bundle.review.review_id = "constructed-decision-context-owner"
    bundle.criteria_revision_number = 1
    bundle.runtime_evidence = [RuntimeEvidence(
        runtime_evidence_id=None if legacy else "constructed-runtime-1",
        repository=None if legacy else bundle.review.repository,
        pr_number=None if legacy else bundle.review.pr_number,
        head_sha=None if legacy else head,
        criterion_id="AC-01",
        artifact_reference="https://example.test/constructed/run-1",
        scenario="Constructed automated comparison observation only",
        timestamp=RECORDED_AT,
        environment="Constructed fixture; no target execution",
        result="Constructed recorded result",
        reviewer="Constructed automated reviewer",
        evidence_level=EvidenceLevel.E3,
        limitations=["Synthetic observation; no independent runtime verification."],
    )]
    bundle.resolutions = [HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment="Constructed latest recorded resolution only.",
        evidence_url="https://example.test/constructed/run-1",
        claimed_evidence_level=EvidenceLevel.E3,
        runtime_evidence_id="constructed-runtime-1" if linked and not legacy else None,
        reviewer="Constructed automated reviewer",
        timestamp=RECORDED_AT,
    )]
    return regated(bundle)


def regated(bundle):
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, bundle.file_scope_decisions,
    )
    return ReviewBundle.model_validate(bundle.model_dump(mode="python"))


def projection(bundle):
    return context_type().from_bundles(bundle, bundle)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field", RESOLUTION_FIELDS)
def test_serialized_resolution_requires_every_explicit_recorded_field(side, field):
    data = projection(constructed_bundle()).model_dump(mode="json")
    del data[side]["resolutions"][0][field]
    with pytest.raises(ValidationError):
        context_type().model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field", RUNTIME_FIELDS)
def test_serialized_runtime_requires_every_explicit_recorded_field(side, field):
    data = projection(constructed_bundle()).model_dump(mode="json")
    del data[side]["runtime_evidence"][0][field]
    with pytest.raises(ValidationError):
        context_type().model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("collection", ["resolutions", "runtime_evidence"])
def test_duplicate_identified_records_reject_instead_of_overwriting(side, collection):
    data = projection(constructed_bundle()).model_dump(mode="json")
    data[side][collection].append(dict(data[side][collection][0]))
    with pytest.raises(ValidationError):
        context_type().model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("collection", ["resolutions", "runtime_evidence"])
def test_unknown_criterion_records_reject(side, collection):
    data = projection(constructed_bundle()).model_dump(mode="json")
    data[side][collection][0]["criterion_id"] = "AC-CONSTRUCTED-UNKNOWN"
    with pytest.raises(ValidationError):
        context_type().model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field,value", [
    ("repository", "constructed/foreign"),
    ("pr_number", 9876),
    ("head_sha", "b" * 40),
])
def test_runtime_records_must_match_owner_scope(side, field, value):
    data = projection(constructed_bundle()).model_dump(mode="json")
    data[side]["runtime_evidence"][0][field] = value
    with pytest.raises(ValidationError):
        context_type().model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field,value", [
    ("runtime_evidence_id", "constructed-missing-observation"),
    ("criterion_id", "AC-02"),
    ("reviewer", "Constructed different asserted reviewer"),
    ("claimed_evidence_level", "E4"),
])
def test_explicit_resolution_links_must_resolve_with_existing_relationship(side, field, value):
    data = projection(constructed_bundle()).model_dump(mode="json")
    data[side]["resolutions"][0][field] = value
    with pytest.raises(ValidationError):
        context_type().model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field,value", [
    ("review_id", "constructed-foreign-owner"),
    ("criteria_revision_number", 9876),
    ("criterion_ids", ["AC-01", "AC-02", "AC-CONSTRUCTED-EXTRA"]),
])
def test_outer_comparison_binds_decision_snapshot_to_file_scope(side, field, value):
    bundle = constructed_bundle()
    data = compare_reviews(bundle, bundle).model_dump(mode="json")
    data["decision_context_comparison"][side][field] = value
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field,value", [
    ("source_uri", "https://example.test/constructed/different-source"),
    ("confirmed_by", "Constructed different confirming actor"),
    ("normalized_criteria_sha256", "d" * 64),
])
def test_outer_comparison_binds_full_provenance_even_without_selected_records(side, field, value):
    bundle = constructed_bundle()
    assert bundle.reviewer_selected_references == []
    data = compare_reviews(bundle, bundle).model_dump(mode="json")
    data["decision_context_comparison"][side]["criteria_source_provenance"][field] = value
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


def test_context_requires_owning_scope_even_when_snapshots_are_empty():
    bundle = constructed_bundle()
    bundle.resolutions = []
    bundle.runtime_evidence = []
    bundle = regated(bundle)
    data = compare_reviews(bundle, bundle).model_dump(mode="json")
    data["file_scope"] = None
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


@pytest.mark.parametrize("mutation", ["runtime_owner", "resolution_link", "provenance"])
def test_export_revalidates_mutated_nested_records(mutation):
    bundle = constructed_bundle()
    result = compare_reviews(bundle, bundle)
    snapshot = result.decision_context_comparison.current
    if mutation == "runtime_owner":
        snapshot.runtime_evidence[0].head_sha = "b" * 40
    elif mutation == "resolution_link":
        snapshot.resolutions[0].runtime_evidence_id = "constructed-missing-observation"
    else:
        snapshot.criteria_source_provenance = snapshot.criteria_source_provenance.model_copy(
            update={"confirmed_by": "Constructed forged confirmer"}
        )
    with pytest.raises(ValidationError):
        export_comparison_json(result)


def test_derived_rows_link_status_and_availability_never_trust_serialized_claims():
    bundle = constructed_bundle()
    result = compare_reviews(bundle, bundle)
    original = result.model_dump(mode="json")
    forged = result.model_dump(mode="json")
    forged["decision_context_compared"] = False
    forged["decision_context_comparison"]["record_changes"] = [{
        "criterion_id": "AC-CONSTRUCTED-INVENTED",
        "kind": "only_current",
        "current": {"runtime_link_status": "no_link"},
    }]
    restored = ReviewComparison.model_validate(forged)
    assert restored.model_dump(mode="json") == original
    row = result.decision_context_comparison.record_changes[0]
    data = row.current.model_dump(mode="json")
    data["runtime_link_status"] = "legacy_unlinked"
    assert type(row.current).model_validate(data).runtime_link_status == "linked"
    assert export_comparison_json(restored) == export_comparison_json(result)


def test_legacy_unavailable_is_distinct_from_known_empty_despite_forged_availability():
    bundle = constructed_bundle()
    bundle.resolutions = []
    bundle.runtime_evidence = []
    bundle = regated(bundle)
    result = compare_reviews(bundle, bundle)
    assert result.decision_context_compared is True
    assert result.decision_context_comparison.previous.resolutions == []
    assert result.decision_context_comparison.current.runtime_evidence == []
    assert result.decision_context_comparison.record_changes == []
    data = result.model_dump(mode="json")
    del data["decision_context_comparison"]
    data["decision_context_compared"] = True
    old = ReviewComparison.model_validate(data)
    assert old.decision_context_comparison is None
    assert old.decision_context_compared is False


def test_legacy_unlinked_matching_metadata_does_not_infer_runtime_link():
    bundle = constructed_bundle(legacy=True)
    context = projection(bundle)
    row = context.record_changes[0].current
    assert row.resolution.runtime_evidence_id is None
    assert row.runtime_evidence[0].reviewer == row.resolution.reviewer
    assert row.runtime_evidence[0].artifact_reference == row.resolution.evidence_url
    assert row.runtime_link_status == "legacy_unlinked"
    assert row.runtime_evidence[0].runtime_evidence_id is None


def test_live_origin_cannot_turn_legacy_unscoped_observations_into_accepted_context():
    bundle = constructed_bundle(legacy=True)
    bundle.review.input_origin = ReviewInputOrigin.LIVE_PUBLIC_GITHUB
    bundle.review.repository_visibility = RepositoryVisibility.VERIFIED_PUBLIC
    with pytest.raises(ValueError):
        projection(bundle)


@pytest.mark.parametrize("side", ["previous", "current"])
def test_serialized_live_snapshot_rejects_legacy_unscoped_observations(side):
    data = projection(constructed_bundle(legacy=True)).model_dump(mode="json")
    data[side]["input_origin"] = ReviewInputOrigin.LIVE_PUBLIC_GITHUB.value
    with pytest.raises(ValidationError):
        context_type().model_validate(data)


@pytest.mark.parametrize("linked_claim", ["legacy_unlinked", "no_link"])
def test_forged_linked_row_claim_cannot_invent_a_runtime_identity(linked_claim):
    bundle = constructed_bundle(legacy=True)
    if linked_claim == "no_link":
        bundle.resolutions = []
        bundle = regated(bundle)
    row = projection(bundle).record_changes[0].current
    assert row.runtime_link_status == linked_claim
    data = row.model_dump(mode="json")
    data["runtime_link_status"] = "linked"
    restored = type(row).model_validate(data)
    assert restored.runtime_link_status == linked_claim
    assert restored.runtime_evidence[0].runtime_evidence_id is None


@pytest.mark.parametrize("forgery", ["invented_delta", "hidden_delta", "altered_context"])
def test_new_recorded_context_cannot_contradict_existing_enum_deltas(forgery):
    previous = constructed_bundle()
    current = previous.model_copy(deep=True)
    current.resolutions[0] = current.resolutions[0].model_copy(update={
        "decision": HumanDecision.REJECTED_FINDING,
        "runtime_evidence_id": None,
        "claimed_evidence_level": None,
    })
    current = regated(current)
    changed = compare_reviews(previous, current).model_dump(mode="json")
    unchanged = compare_reviews(previous, previous).model_dump(mode="json")
    if forgery == "hidden_delta":
        data = changed
        data["changed_human_resolutions"] = []
    elif forgery == "invented_delta":
        data = unchanged
        data["changed_human_resolutions"] = changed["changed_human_resolutions"]
    else:
        data = unchanged
        data["decision_context_comparison"] = changed["decision_context_comparison"]
    # Both snapshots and their links are independently valid: rejection must be
    # the disagreement between the new projection and the original enum output.
    context_type().model_validate(data["decision_context_comparison"])
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(data)


def test_canonical_order_keeps_duplicate_unlinked_observations_and_ignores_list_order():
    bundle = constructed_bundle(legacy=True)
    second = bundle.runtime_evidence[0].model_copy(deep=True)
    second.result = "Constructed distinct second recorded result"
    second.criterion_id = "AC-02"
    bundle.runtime_evidence.extend([
        bundle.runtime_evidence[0].model_copy(deep=True), second,
    ])
    bundle.resolutions.append(HumanResolution(
        criterion_id="AC-02", decision=HumanDecision.REJECTED_FINDING,
        comment="Constructed separate record", evidence_url=None,
        claimed_evidence_level=None, runtime_evidence_id=None,
        reviewer="Constructed automated reviewer", timestamp=RECORDED_AT,
    ))
    bundle = regated(bundle)
    shuffled = bundle.model_copy(deep=True)
    shuffled.runtime_evidence.reverse()
    shuffled.resolutions.reverse()
    forward = projection(bundle)
    backward = projection(shuffled)
    assert forward.model_dump_json() == backward.model_dump_json()
    assert len(forward.current.runtime_evidence) == 3
    rows = {row.criterion_id: row for row in forward.record_changes}
    assert len(rows["AC-01"].current.runtime_evidence) == 2
    assert rows["AC-02"].current.runtime_link_status == "no_link"


def test_snapshot_and_derived_rows_detach_nested_sources():
    bundle = constructed_bundle()
    before = bundle.model_dump_json()
    context = projection(bundle)
    context.current.runtime_evidence[0].limitations.append("Constructed detached mutation")
    context.current.resolutions[0].comment = "Constructed detached note"
    context.current.criteria_source_provenance = (
        context.current.criteria_source_provenance.model_copy(
            update={"confirmed_by": "Constructed detached confirmer"}
        )
    )
    context.current.criterion_ids.append("AC-CONSTRUCTED-DETACHED")
    assert bundle.model_dump_json() == before
    assert (
        context.previous.runtime_evidence[0].limitations
        == bundle.runtime_evidence[0].limitations
    )
    # Row records are inspectable projections; editing one must not silently edit
    # the authoritative snapshot from which future derived rows are recomputed.
    fresh = projection(bundle)
    row = fresh.record_changes[0].current
    row.runtime_evidence[0].limitations.append("Constructed row-only mutation")
    row.resolution.comment = "Constructed row-only note"
    assert fresh.current.runtime_evidence == bundle.runtime_evidence
    assert fresh.current.resolutions == bundle.resolutions


def test_unknown_historical_revision_is_retained_without_inventing_current_revision():
    bundle = constructed_bundle()
    bundle.criteria_revision_number = "unknown"
    result = compare_reviews(bundle, bundle)
    assert result.decision_context_comparison.previous.criteria_revision_number == "unknown"
    assert result.decision_context_comparison.current.criteria_revision_number == "unknown"
    assert ReviewComparison.model_validate_json(result.model_dump_json()) == result


def test_same_decision_changed_context_preserves_all_original_deltas_gates_and_source_bytes():
    previous = constructed_bundle()
    current = previous.model_copy(deep=True)
    current.resolutions[0].comment = "Constructed changed note with unchanged enum"
    current.resolutions[0].timestamp += timedelta(seconds=1)
    current.runtime_evidence[0].limitations.append("Constructed additional limitation")
    current = regated(current)
    before = previous.model_dump_json(), current.model_dump_json()
    baseline = compare_reviews(previous, previous).model_dump(mode="json")
    result = compare_reviews(previous, current)
    contextual = result.model_dump(mode="json")
    baseline.pop("decision_context_comparison")
    contextual.pop("decision_context_comparison")
    assert contextual == baseline
    assert result.changed_human_resolutions == []
    assert result.criteria_requiring_decision_review == []
    assert result.previous_gate == previous.gate.verdict
    assert result.current_gate == current.gate.verdict
    assert result.decision_context_comparison.record_changes[0].kind == "recorded_context_changed"
    export_comparison_json(result)
    assert before == (previous.model_dump_json(), current.model_dump_json())


def test_comparison_never_opens_fetches_or_executes_recorded_artifact(monkeypatch, tmp_path):
    bundle = constructed_bundle()
    artifact = tmp_path / "constructed-observation.py"
    artifact.write_text("raise AssertionError('Constructed target must never execute')\n")
    bundle.runtime_evidence[0].artifact_reference = str(artifact)
    bundle = regated(bundle)
    api = context_type()

    def forbidden(*args, **kwargs):
        raise AssertionError("Comparison must not access or execute artifact contents")

    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(io, "open", forbidden)
        guard.setattr(socket.socket, "connect", forbidden)
        guard.setattr(urllib.request, "urlopen", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(os, "system", forbidden)
        context = api.from_bundles(bundle, bundle)
        result = compare_reviews(bundle, bundle)
        exported = export_comparison_json(result)
    assert context.current.runtime_evidence[0].artifact_reference == str(artifact)
    assert str(artifact) in exported
