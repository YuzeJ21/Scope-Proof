"""Read-only comparison selections bound to complete validated saved records."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from scopeproof_core.reviews.comparison import (
    ComparisonIncompatible,
    ComparisonRejectionReason,
    ReviewComparison,
    compare_reviews,
)
from scopeproof_core.reviews.criteria_comparison import (
    RecordedCriteriaDiff,
    analysis_criteria_snapshot,
    criteria_snapshot_fingerprint,
)
from scopeproof_core.schemas.models import LocalReviewId, ReviewBundle, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SavedComparisonUnavailable(ValueError):
    """A previously selected saved comparison no longer matches its record snapshot."""


class SavedComparisonIncompatible(ComparisonIncompatible):
    """A criteria-related refusal with eligibility for the requirements-only comparison."""

    def __init__(self, rejection: ComparisonIncompatible, *, requirements_available: bool) -> None:
        super().__init__(rejection.reason, str(rejection))
        self.requirements_available = requirements_available


class SavedComparisonSelection(BaseModel):
    """Session-only reference; the whole record hash also binds history position."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_review_id: LocalReviewId
    baseline_review_id: LocalReviewId
    current_fingerprint: Fingerprint
    baseline_fingerprint: Fingerprint
    history_index: Annotated[StrictInt, Field(ge=0)] | None = None


class SavedRequirementsReport(RecordedCriteriaDiff):
    """Portable requirements context bound to an explicitly selected saved pair."""

    selection: SavedComparisonSelection
    baseline_criteria_fingerprint: Fingerprint
    current_criteria_fingerprint: Fingerprint

    @model_validator(mode="after")
    def _selected_records(self) -> SavedRequirementsReport:
        if (
            self.previous.review_id != self.selection.baseline_review_id
            or self.current.review_id != self.selection.current_review_id
            or self.previous.review_id == self.current.review_id
        ):
            raise ValueError("requirements report requires two selected owning records")
        if (
            criteria_snapshot_fingerprint(self.previous) != self.baseline_criteria_fingerprint
            or criteria_snapshot_fingerprint(self.current) != self.current_criteria_fingerprint
        ):
            raise ValueError("requirements snapshot differs from the selected saved analysis")
        return self


def _baseline_bundle(state: ReviewState, history_index: int | None) -> ReviewBundle:
    if history_index is not None:
        if history_index >= len(state.analysis_history):
            raise ValueError("selected saved analysis history is unavailable")
        return state.analysis_history[history_index]
    if state.bundle is None:
        raise ValueError("saved comparison requires an active analysis in both saved reviews")
    return state.bundle


def _require_selected_identity(state: ReviewState, review_id: str) -> None:
    if state.review.review_id != review_id:
        raise SavedComparisonUnavailable("saved filename and owning review identity differ")


def _compare(
    current: ReviewState,
    baseline: ReviewState,
    history_index: int | None,
) -> ReviewComparison:
    if current.bundle is None:
        raise ValueError("saved comparison requires an active analysis in the current review")
    try:
        return compare_reviews(_baseline_bundle(baseline, history_index), current.bundle)
    except ComparisonIncompatible as error:
        if error.reason not in {
            ComparisonRejectionReason.DIFFERENT_CRITERIA,
            ComparisonRejectionReason.DIFFERENT_CRITERIA_SOURCE,
        }:
            raise
        # Both records are still locked. Check the same projection the explicit action uses.
        try:
            _compare_requirements(current, baseline, history_index)
        except ValueError:
            requirements_available = False
        else:
            requirements_available = True
        raise SavedComparisonIncompatible(
            error, requirements_available=requirements_available,
        ) from error


def _compare_requirements(
    current: ReviewState, baseline: ReviewState, history_index: int | None,
) -> RecordedCriteriaDiff:
    if current.bundle is None or current.review.review_id == baseline.review.review_id:
        raise ValueError("requirements comparison needs another saved record and active analysis")
    return RecordedCriteriaDiff(
        previous=analysis_criteria_snapshot(_baseline_bundle(baseline, history_index)),
        current=analysis_criteria_snapshot(current.bundle),
    )


def _prepare_saved_selection(
    store: JsonReviewStore,
    current: ReviewState,
    baseline_review_id: str,
    compare: Callable[[ReviewState, ReviewState, int | None], object],
    *,
    history_index: int | None = None,
    expected_baseline_fingerprint: Fingerprint | None = None,
) -> SavedComparisonSelection:
    expected_current = store.state_fingerprint(current)
    with store.locked_load_many((current.review.review_id, baseline_review_id)) as (
        saved_current,
        baseline,
    ):
        _require_selected_identity(saved_current, current.review.review_id)
        _require_selected_identity(baseline, baseline_review_id)
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
        compare(saved_current, baseline, selection.history_index)
        return selection


def prepare_saved_comparison(
    store: JsonReviewStore, current: ReviewState, baseline_review_id: str, *,
    history_index: int | None = None, expected_baseline_fingerprint: Fingerprint | None = None,
) -> SavedComparisonSelection:
    """Explicitly select compatible saved truth, rejecting unsaved current changes."""
    return _prepare_saved_selection(
        store, current, baseline_review_id, _compare, history_index=history_index,
        expected_baseline_fingerprint=expected_baseline_fingerprint,
    )


def prepare_saved_requirements_comparison(
    store: JsonReviewStore, current: ReviewState, baseline_review_id: str, *,
    history_index: int | None = None, expected_baseline_fingerprint: Fingerprint | None = None,
) -> SavedComparisonSelection:
    """Select recorded requirements independently of evidence compatibility."""
    return _prepare_saved_selection(
        store, current, baseline_review_id, _compare_requirements, history_index=history_index,
        expected_baseline_fingerprint=expected_baseline_fingerprint,
    )


@contextmanager
def _locked_saved_selection(
    store: JsonReviewStore,
    selection: SavedComparisonSelection,
) -> Iterator[tuple[ReviewState, ReviewState, int | None]]:
    selection = SavedComparisonSelection.model_validate(selection.model_dump(mode="python"))
    with store.locked_load_many((selection.current_review_id, selection.baseline_review_id)) as (
        current,
        baseline,
    ):
        _require_selected_identity(current, selection.current_review_id)
        _require_selected_identity(baseline, selection.baseline_review_id)
        if (
            store.state_fingerprint(current) != selection.current_fingerprint
            or store.state_fingerprint(baseline) != selection.baseline_fingerprint
        ):
            raise SavedComparisonUnavailable("saved comparison changed; select the baseline again")
        yield current, baseline, selection.history_index


@contextmanager
def locked_saved_comparison(
    store: JsonReviewStore, selection: SavedComparisonSelection,
) -> Iterator[ReviewComparison]:
    """Revalidate both selected records and hold their locks through the consumer."""
    with _locked_saved_selection(store, selection) as (current, baseline, index):
        yield _compare(current, baseline, index)


@contextmanager
def locked_saved_requirements_comparison(
    store: JsonReviewStore, selection: SavedComparisonSelection,
) -> Iterator[RecordedCriteriaDiff]:
    """Hold both saved records stable while inspecting recorded requirements."""
    with _locked_saved_selection(store, selection) as (current, baseline, index):
        yield _compare_requirements(current, baseline, index)


@contextmanager
def locked_saved_requirements_report(
    store: JsonReviewStore, selection: SavedComparisonSelection,
) -> Iterator[SavedRequirementsReport]:
    """Revalidate both saved records and keep them stable through report generation."""
    selection = SavedComparisonSelection.model_validate(selection.model_dump(mode="python"))
    with locked_saved_requirements_comparison(store, selection) as diff:
        yield SavedRequirementsReport(
            selection=selection, previous=diff.previous, current=diff.current,
            baseline_criteria_fingerprint=criteria_snapshot_fingerprint(diff.previous),
            current_criteria_fingerprint=criteria_snapshot_fingerprint(diff.current),
        )
