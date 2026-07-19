from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import CheckState, CIObservation, ReviewBundle, ReviewState

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

COERCIVE_REVISION_VALUES = [True, False, "1", "01", 1.0, 2.0]


@pytest.mark.parametrize("review_overrides", ACTIVE_REVIEW_OVERRIDES)
def test_review_state_rejects_divergent_active_bundle_review(review_overrides) -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["review"].update(review_overrides)
    if "check_state" in review_overrides:
        # Keep the deliberately divergent lifecycle review schema-valid so this
        # test reaches the ReviewState integrity boundary.
        payload["review"]["ci_observation"]["state"] = review_overrides["check_state"]
        payload["review"]["ci_observation"] = CIObservation(
            state=CheckState.FAILING,
            reason="Fixture",
            total_check_runs=1,
            failing_check_runs=1,
        ).model_dump(mode="python")

    with pytest.raises(
        ValidationError, match="active bundle review must match lifecycle review"
    ):
        ReviewState.model_validate(payload)


def test_review_state_accepts_matching_active_bundle_review() -> None:
    state = new_review_state(build_demo_review())

    reopened = ReviewState.model_validate_json(state.model_dump_json())

    assert reopened == state


def test_standalone_review_bundle_defaults_to_unknown_criteria_revision() -> None:
    bundle = build_demo_review()

    assert bundle.criteria_revision_number == "unknown"


def test_standalone_review_bundle_accepts_strict_positive_integer_revision() -> None:
    payload = build_demo_review().model_dump(mode="python")
    payload["criteria_revision_number"] = 1

    bundle = ReviewBundle.model_validate(payload)

    assert bundle.criteria_revision_number == 1


@pytest.mark.parametrize("revision_number", COERCIVE_REVISION_VALUES)
def test_review_bundle_rejects_coercive_criteria_revision_values(
    revision_number: object,
) -> None:
    payload = build_demo_review().model_dump(mode="python")
    payload["criteria_revision_number"] = revision_number

    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)


@pytest.mark.parametrize("revision_number", [0, -1])
def test_review_bundle_rejects_non_positive_known_criteria_revision(
    revision_number: int,
) -> None:
    payload = build_demo_review().model_dump(mode="python")
    payload["criteria_revision_number"] = revision_number

    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)


@pytest.mark.parametrize("bundle_revision", [2, "unknown"])
def test_review_state_rejects_active_bundle_revision_mismatch(
    bundle_revision: int | str,
) -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["bundle"]["criteria_revision_number"] = bundle_revision

    with pytest.raises(
        ValidationError,
        match="active bundle revision must match the active criteria revision",
    ):
        ReviewState.model_validate(payload)


@pytest.mark.parametrize("bundle_revision", COERCIVE_REVISION_VALUES)
def test_review_state_rejects_coercive_active_bundle_revision(
    bundle_revision: object,
) -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["bundle"]["criteria_revision_number"] = bundle_revision

    with pytest.raises(ValidationError):
        ReviewState.model_validate(payload)


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


@pytest.mark.parametrize("historical_revision", [2, 3])
def test_review_state_rejects_known_historical_revision_at_or_above_active_revision(
    historical_revision: int,
) -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        state.criteria_revision.source_text,
    )
    payload = revised.model_dump(mode="python")
    payload["analysis_history"][0]["criteria_revision_number"] = historical_revision

    with pytest.raises(
        ValidationError,
        match="historical bundle revisions must be lower than the active revision",
    ):
        ReviewState.model_validate(payload)


@pytest.mark.parametrize("known_revisions", [[1, 1], [2, 1]])
def test_review_state_rejects_duplicate_or_decreasing_known_history(
    known_revisions: list[int],
) -> None:
    state = new_review_state(build_demo_review())
    revision_two = revise_criteria(
        state,
        state.criteria_revision.criteria,
        state.criteria_revision.source_text,
    )
    payload = revision_two.model_dump(mode="python")
    historical = payload["analysis_history"][0]
    payload["criteria_revision"]["number"] = 3
    payload["analysis_history"] = [historical.copy(), historical.copy()]
    for bundle, revision_number in zip(
        payload["analysis_history"], known_revisions, strict=True
    ):
        bundle["criteria_revision_number"] = revision_number

    with pytest.raises(
        ValidationError,
        match="known historical bundle revisions must be unique and strictly increasing",
    ):
        ReviewState.model_validate(payload)


def test_review_state_preserves_unknown_historical_revision() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        state.criteria_revision.source_text,
    )
    payload = revised.model_dump(mode="python")
    payload["analysis_history"][0]["criteria_revision_number"] = "unknown"

    reopened = ReviewState.model_validate(payload)

    assert reopened.analysis_history[0].criteria_revision_number == "unknown"


@pytest.mark.parametrize("historical_revision", COERCIVE_REVISION_VALUES)
def test_review_state_rejects_coercive_historical_bundle_revision(
    historical_revision: object,
) -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        state.criteria_revision.source_text,
    )
    payload = revised.model_dump(mode="python")
    payload["analysis_history"][0]["criteria_revision_number"] = historical_revision

    with pytest.raises(ValidationError):
        ReviewState.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("review_id", "foreign-review"),
        ("repository", "other/repository"),
        ("pr_number", 999),
    ],
)
def test_review_state_rejects_foreign_historical_lineage(
    field_name: str, value: object
) -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    payload = revised.model_dump(mode="python")
    payload["analysis_history"][0]["review"][field_name] = value

    with pytest.raises(
        ValidationError,
        match="historical bundle review lineage must match lifecycle review",
    ):
        ReviewState.model_validate(payload)


def test_review_state_allows_historical_commit_provenance() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    payload = revised.model_dump(mode="python")
    payload["analysis_history"][0]["review"]["base_sha"] = "historical-base"
    payload["analysis_history"][0]["review"]["head_sha"] = "historical-head"

    reopened = ReviewState.model_validate(payload)

    assert reopened.analysis_history[0].review.head_sha == "historical-head"
