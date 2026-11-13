"""Click-time export revalidation for the local ScopeProof workbench."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TypeVar

from scopeproof_core.reviews.comparison import ReviewComparison
from scopeproof_core.reviews.criteria_comparison import (
    CriteriaComparisonSelection,
    CriteriaRevisionComparison,
    locked_criteria_comparison,
)
from scopeproof_core.reviews.historical_analysis import (
    HistoricalAnalysisReport,
    HistoricalAnalysisSelection,
    locked_historical_analysis,
)
from scopeproof_core.reviews.saved_comparison import (
    SavedComparisonSelection,
    SavedRequirementsReport,
    locked_saved_comparison,
    locked_saved_requirements_report,
)
from scopeproof_core.schemas.models import ReviewBundle, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

ExportSource = ReviewState | ReviewBundle
ExportRenderer = Callable[[ExportSource], str]
_SavedReport = TypeVar("_SavedReport")
_EXPORT_REVALIDATION_MESSAGE = (
    "ScopeProof export was blocked because the saved review could not be revalidated. "
    "Rerun the workbench and reopen the review before exporting."
)


class DeferredExportUnavailable(RuntimeError):
    """Raised when a click-time export cannot reproduce persisted review truth."""


@dataclass
class SavedComparisonExportLease:
    """Volatile per-session guard shared with older deferred download callbacks."""

    selection: SavedComparisonSelection | None = None
    generation: int = 0

    def invalidate(self) -> None:
        self.generation += 1
        self.selection = None


@dataclass
class HistoricalAnalysisExportLease:
    """Session generation shared by historical selection and existing callbacks."""

    selection: HistoricalAnalysisSelection | None = None
    generation: int = 0

    def invalidate(self) -> None:
        self.generation += 1
        self.selection = None


@dataclass
class CriteriaComparisonExportLease:
    """Volatile generation revokes already rendered requirements downloads."""

    selection: CriteriaComparisonSelection | None = None
    generation: int = 0

    def invalidate(self) -> None:
        self.generation += 1
        self.selection = None


def deferred_criteria_comparison_export(
    selection: CriteriaComparisonSelection,
    renderer: Callable[[CriteriaRevisionComparison], str],
    *,
    store: JsonReviewStore,
    lease: CriteriaComparisonExportLease,
) -> Callable[[], str]:
    captured = selection.model_copy(deep=True)
    generation = lease.generation
    message = "Saved criteria changed or selection expired. Reopen and explicitly compare again."

    def render() -> str:
        if lease.generation != generation or lease.selection != captured:
            raise DeferredExportUnavailable(message)
        try:
            with locked_criteria_comparison(store, captured) as report:
                rendered = renderer(report)
                if lease.generation != generation or lease.selection != captured:
                    raise DeferredExportUnavailable(message)
                return rendered
        except (OSError, ValueError):
            raise DeferredExportUnavailable(message) from None

    return render


def deferred_historical_export(
    selection: HistoricalAnalysisSelection,
    renderer: Callable[[HistoricalAnalysisReport], str],
    *,
    store: JsonReviewStore,
    lease: HistoricalAnalysisExportLease,
) -> Callable[[], str]:
    captured = selection.model_copy(deep=True)
    generation = lease.generation
    message = (
        "Historical export was blocked because the saved record or selection changed. "
        "Reopen the review and select its retained analysis again."
    )

    def render() -> str:
        if lease.generation != generation or lease.selection != captured:
            raise DeferredExportUnavailable(message)
        try:
            with locked_historical_analysis(store, captured) as report:
                rendered = renderer(report)
                if lease.generation != generation or lease.selection != captured:
                    raise DeferredExportUnavailable(message)
                return rendered
        except (OSError, ValueError):
            raise DeferredExportUnavailable(message) from None

    return render


def deferred_saved_comparison_export(
    selection: SavedComparisonSelection,
    renderer: Callable[[ReviewComparison], str],
    *,
    store: JsonReviewStore,
    lease: SavedComparisonExportLease,
) -> Callable[[], str]:
    return _deferred_saved_selection_export(
        selection, renderer, store=store, lease=lease, load=locked_saved_comparison,
        message=(
            "ScopeProof comparison export was blocked because a saved review or selection "
            "changed. Reopen the current review and select the baseline again before exporting."
        ),
    )


def deferred_saved_requirements_export(
    selection: SavedComparisonSelection,
    renderer: Callable[[SavedRequirementsReport], str],
    *,
    store: JsonReviewStore,
    lease: SavedComparisonExportLease,
) -> Callable[[], str]:
    return _deferred_saved_selection_export(
        selection, renderer, store=store, lease=lease, load=locked_saved_requirements_report,
        message="Saved requirements changed or selection expired. Select the baseline again.",
    )


def _deferred_saved_selection_export(
    selection: SavedComparisonSelection,
    renderer: Callable[[_SavedReport], str],
    *,
    store: JsonReviewStore,
    lease: SavedComparisonExportLease,
    load: Callable[
        [JsonReviewStore, SavedComparisonSelection], AbstractContextManager[_SavedReport]
    ],
    message: str,
) -> Callable[[], str]:
    captured = selection.model_copy(deep=True)
    generation = lease.generation

    def render() -> str:
        if lease.generation != generation or lease.selection != captured:
            raise DeferredExportUnavailable(message)
        try:
            with load(store, captured) as report:
                rendered = renderer(report)
                if lease.generation != generation or lease.selection != captured:
                    raise DeferredExportUnavailable(message)
                return rendered
        except (OSError, ValueError):
            raise DeferredExportUnavailable(message) from None

    return render


def deferred_review_export(
    source: ExportSource,
    renderer: ExportRenderer,
    *,
    store: JsonReviewStore,
    expected_fingerprint: str | None,
    authority_check: Callable[[], bool] | None = None,
    expired_by_acceptance_note: Callable[[], bool] | None = None,
    expired_by_scope_draft: Callable[[], bool] | None = None,
) -> Callable[[], str]:
    """Return a click-time renderer that refuses stale persisted review state."""

    captured = source.model_copy(deep=True)

    def require_authority() -> None:
        if expired_by_acceptance_note is not None and expired_by_acceptance_note():
            raise DeferredExportUnavailable(
                "This download expired when the final acceptance note opened. "
                "Submit or clear the note and use the current download button."
            )
        if expired_by_scope_draft is not None and expired_by_scope_draft():
            raise DeferredExportUnavailable(
                "This download expired when a file-scope decision was drafted. "
                "Save or discard the draft and use the current download button."
            )
        if authority_check is not None and not authority_check():
            raise DeferredExportUnavailable(
                "ScopeProof export was blocked because fresh source observations require re-review."
            )

    def render() -> str:
        require_authority()
        authoritative: ExportSource = captured
        if isinstance(captured, ReviewState) and expected_fingerprint is not None:
            try:
                with store.locked_load(captured.review.review_id) as persisted:
                    if JsonReviewStore.state_fingerprint(persisted) != expected_fingerprint:
                        raise DeferredExportUnavailable(_EXPORT_REVALIDATION_MESSAGE)
                    rendered = renderer(persisted)
                    require_authority()
                    return rendered
            except (OSError, ValueError):
                raise DeferredExportUnavailable(_EXPORT_REVALIDATION_MESSAGE) from None
        rendered = renderer(authoritative)
        require_authority()
        return rendered

    return render
