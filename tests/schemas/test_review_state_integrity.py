from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import ReviewState

ACTIVE_REVIEW_OVERRIDES = [
    {"review_id": "different-review"},
    {"repository": "acme/different"},
    {"pr_number": 999},
    {"base_sha": "different-base"},
    {"head_sha": "different-head"},
    {"check_state": "failing"},
    {"criteria_confirmed": False},
    {"ingestion_state": "partial", "ingestion_warnings": ["Different warning"]},
    {"ingestion_state": "partial", "skipped_files": ["src/different.py"]},
    {"final_acceptance": True},
    {"created_at": datetime(2020, 1, 1, tzinfo=UTC)},
    {"tool_version": "0.0.0-history"},
    {"ruleset_version": "0.0.0-history"},
]


@pytest.mark.parametrize("review_overrides", ACTIVE_REVIEW_OVERRIDES)
def test_review_state_rejects_divergent_active_bundle_review(review_overrides) -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["review"].update(review_overrides)

    with pytest.raises(
        ValidationError, match="active bundle review must match lifecycle review"
    ):
        ReviewState.model_validate(payload)


def test_review_state_accepts_matching_active_bundle_review() -> None:
    state = new_review_state(build_demo_review())

    reopened = ReviewState.model_validate_json(state.model_dump_json())

    assert reopened == state


def test_review_state_rejects_active_bundle_with_unconfirmed_revision() -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["criteria_revision"]["confirmed"] = False
    payload["criteria_revision"]["confirmed_at"] = None
    payload["review"]["criteria_confirmed"] = False
    payload["bundle"]["review"]["criteria_confirmed"] = False

    with pytest.raises(
        ValidationError, match="active bundle requires a confirmed criteria revision"
    ):
        ReviewState.model_validate(payload)


def test_review_state_rejects_active_bundle_with_divergent_revision_criteria() -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["criteria_revision"]["criteria"][0]["text"] = (
        "Different but valid acceptance criterion"
    )

    with pytest.raises(
        ValidationError, match="active bundle criteria must match the active revision"
    ):
        ReviewState.model_validate(payload)


def test_review_state_rejects_active_bundle_with_divergent_revision_source() -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["criteria_revision"]["source_text"] = (
        "Different but valid requirements source"
    )

    with pytest.raises(
        ValidationError, match="active bundle source must match the active revision"
    ):
        ReviewState.model_validate(payload)


def test_new_review_state_does_not_alias_active_revision_criteria() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    original_bundle_text = state.bundle.criteria[0].text

    state.criteria_revision.criteria[0].text = (
        "Different unanalyzed acceptance criterion"
    )

    assert state.bundle.criteria[0].text == original_bundle_text
    with pytest.raises(
        ValidationError, match="active bundle criteria must match the active revision"
    ):
        ReviewState.model_validate(state.model_dump(mode="python"))


def test_new_review_state_does_not_alias_active_review_identity() -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    original_bundle_head = state.bundle.review.head_sha

    state.review.head_sha = "different-but-valid-head"

    assert state.bundle.review.head_sha == original_bundle_head
    with pytest.raises(
        ValidationError, match="active bundle review must match lifecycle review"
    ):
        ReviewState.model_validate(state.model_dump(mode="python"))


def test_review_state_rejects_divergent_revision_confirmation() -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["review"]["criteria_confirmed"] = False
    payload["bundle"]["review"]["criteria_confirmed"] = False

    with pytest.raises(
        ValidationError, match="criteria confirmation must match the active revision"
    ):
        ReviewState.model_validate(payload)


def test_review_state_accepts_bundleless_pending_revision() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        state.criteria_revision.source_text,
    )

    reopened = ReviewState.model_validate_json(revised.model_dump_json())

    assert reopened.bundle is None
    assert reopened.analysis_history == [state.bundle]
