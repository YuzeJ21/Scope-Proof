"""Read-only comparison selections bound to complete validated saved records."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.schemas.models import LocalReviewId, ReviewBundle, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SavedComparisonUnavailable(ValueError):
    """A previously selected saved comparison no longer matches its record snapshot."""


class SavedComparisonSelection(BaseModel):
    """Session-only reference; the whole record hash also binds history position."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_review_id: LocalReviewId
    baseline_review_id: LocalReviewId
    current_fingerprint: Fingerprint
    baseline_fingerprint: Fingerprint
    history_index: Annotated[StrictInt, Field(ge=0)] | None = None


def _baseline_bundle(state: ReviewState, history_index: int | None) -> ReviewBundle:
    if history_index is not None:
        if history_index >= len(state.analysis_history):
            raise ValueError("selected saved analysis history is unavailable")
        return state.analysis_history[history_index]
    if state.bundle is None:
        raise ValueError("saved comparison requires an active analysis in both saved reviews")
    return state.bundle


def _compare(
    current: ReviewState,
    baseline: ReviewState,
    history_index: int | None,
) -> ReviewComparison:
    if current.bundle is None:
        raise ValueError("saved comparison requires an active analysis in the current review")
    return compare_reviews(_baseline_bundle(baseline, history_index), current.bundle)


def prepare_saved_comparison(
    store: JsonReviewStore,
    current: ReviewState,
    baseline_review_id: str,
    *,
    history_index: int | None = None,
    expected_baseline_fingerprint: Fingerprint | None = None,
) -> SavedComparisonSelection:
    """Explicitly select compatible saved truth, rejecting unsaved current changes."""
    expected_current = store.state_fingerprint(current)
    with store.locked_load_many((current.review.review_id, baseline_review_id)) as (
        saved_current,
        baseline,
    ):
        current_fingerprint = store.state_fingerprint(saved_current)
        if current_fingerprint != expected_current:
            raise SavedComparisonUnavailable(
                "current saved review changed; reopen and select again"
            )
        baseline_fingerprint = store.state_fingerprint(baseline)
        selection = SavedComparisonSelection(
            current_review_id=saved_current.review.review_id,
            baseline_review_id=baseline.review.review_id,
            current_fingerprint=current_fingerprint,
            baseline_fingerprint=(
                baseline_fingerprint
                if expected_baseline_fingerprint is None else expected_baseline_fingerprint
            ),
            history_index=history_index,
        )
        if baseline_fingerprint != selection.baseline_fingerprint:
            raise SavedComparisonUnavailable("selected saved baseline changed; select again")
        _compare(saved_current, baseline, selection.history_index)
        return selection


@contextmanager
def locked_saved_comparison(
    store: JsonReviewStore,
    selection: SavedComparisonSelection,
) -> Iterator[ReviewComparison]:
    """Revalidate both selected records and hold their locks through the consumer."""
    selection = SavedComparisonSelection.model_validate(selection.model_dump(mode="python"))
    with store.locked_load_many((selection.current_review_id, selection.baseline_review_id)) as (
        current,
        baseline,
    ):
        if (
            store.state_fingerprint(current) != selection.current_fingerprint
            or store.state_fingerprint(baseline) != selection.baseline_fingerprint
        ):
            raise SavedComparisonUnavailable("saved comparison changed; select the baseline again")
        yield _compare(current, baseline, selection.history_index)
