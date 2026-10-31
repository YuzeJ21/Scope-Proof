"""Independent-review reproductions: recorded fields never come from defaults."""

import pytest
from pydantic import ValidationError

from scopeproof_core.reporting.exporters import export_comparison_json
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.reviews.decision_context_comparison import (
    CriterionDecisionContext,
    DecisionContextSnapshot,
)
from scopeproof_core.schemas.models import HumanResolution, RuntimeEvidence
from tests.reviews.test_decision_context_comparison import decision_bundle


@pytest.mark.parametrize("collection", ["resolutions", "runtime_evidence"])
@pytest.mark.parametrize("container", [tuple, iter])
def test_non_list_projection_collections_cannot_supply_missing_recorded_timestamps(
    collection, container,
):
    bundle = decision_bundle()
    payload = compare_reviews(bundle, bundle).model_dump(mode="python")
    for side in ("previous", "current"):
        snapshot = payload["decision_context_comparison"][side]
        del snapshot[collection][0]["timestamp"]
        snapshot[collection] = container(snapshot[collection])
    with pytest.raises(ValidationError):
        result = ReviewComparison.model_validate(payload)
        export_comparison_json(result)


@pytest.mark.parametrize("collection,model", [
    ("resolutions", HumanResolution), ("runtime_evidence", RuntimeEvidence),
])
def test_mutated_snapshot_instances_revalidate_complete_nested_records(collection, model):
    bundle = decision_bundle()
    snapshot = compare_reviews(bundle, bundle).decision_context_comparison.current
    payload = getattr(snapshot, collection)[0].model_dump(mode="python")
    payload.pop("timestamp")
    # Simulates caller code bypassing validation before the public model boundary.
    incomplete = model.model_construct(**payload)
    incomplete.__dict__.pop("timestamp", None)
    mutated = snapshot.model_copy(update={collection: [incomplete]})
    with pytest.raises(ValidationError):
        DecisionContextSnapshot.model_validate(mutated)


def test_mutated_row_instance_recomputes_link_status_and_revalidates_nested_fields():
    bundle = decision_bundle()
    row = compare_reviews(bundle, bundle).decision_context_comparison.record_changes[0].current
    payload = row.resolution.model_dump(mode="python")
    payload.pop("timestamp")
    incomplete = HumanResolution.model_construct(**payload)
    incomplete.__dict__.pop("timestamp", None)
    mutated = row.model_copy(update={"resolution": incomplete})
    with pytest.raises(ValidationError):
        CriterionDecisionContext.model_validate(mutated)


@pytest.mark.parametrize("container", [tuple, iter])
def test_standalone_row_rejects_incomplete_runtime_collection_iterables(container):
    bundle = decision_bundle()
    row = compare_reviews(bundle, bundle).decision_context_comparison.record_changes[0].current
    payload = row.model_dump(mode="python")
    payload["runtime_evidence"][0].pop("timestamp")
    payload["runtime_evidence"] = container(payload["runtime_evidence"])
    with pytest.raises(ValidationError):
        CriterionDecisionContext.model_validate(payload)


def test_complete_existing_projection_instances_round_trip_without_aliasing_or_new_defaults():
    bundle = decision_bundle()
    snapshot = compare_reviews(bundle, bundle).decision_context_comparison.current
    copied = DecisionContextSnapshot.model_validate(snapshot)
    assert copied == snapshot
    copied.runtime_evidence[0].limitations.append("Constructed detached revalidation")
    assert copied.runtime_evidence != snapshot.runtime_evidence
    row = compare_reviews(bundle, bundle).decision_context_comparison.record_changes[0].current
    assert CriterionDecisionContext.model_validate(row) == row
