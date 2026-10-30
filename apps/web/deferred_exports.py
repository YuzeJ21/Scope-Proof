"""Click-time export revalidation for the local ScopeProof workbench."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from scopeproof_core.reviews.comparison import ReviewComparison
from scopeproof_core.reviews.saved_comparison import (
    SavedComparisonSelection,
    locked_saved_comparison,
)
from scopeproof_core.schemas.models import ReviewBundle, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

ExportSource = ReviewState | ReviewBundle
ExportRenderer = Callable[[ExportSource], str]
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


def deferred_saved_comparison_export(
    selection: SavedComparisonSelection,
    renderer: Callable[[ReviewComparison], str],
    *,
    store: JsonReviewStore,
    lease: SavedComparisonExportLease,
) -> Callable[[], str]:
    captured = selection.model_copy(deep=True)
    message = (
        "ScopeProof comparison export was blocked because a saved review or selection changed. "
        "Reopen the current review and select the baseline again before exporting."
    )

    def render() -> str:
        if lease.selection != captured:
            raise DeferredExportUnavailable(message)
        try:
            with locked_saved_comparison(store, captured) as comparison:
                rendered = renderer(comparison)
                if lease.selection != captured:
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
) -> Callable[[], str]:
    """Return a click-time renderer that refuses stale persisted review state."""

    captured = source.model_copy(deep=True)

    def render() -> str:
        authoritative: ExportSource = captured
        if isinstance(captured, ReviewState) and expected_fingerprint is not None:
            try:
                with store.locked_load(captured.review.review_id) as persisted:
                    if JsonReviewStore.state_fingerprint(persisted) != expected_fingerprint:
                        raise DeferredExportUnavailable(_EXPORT_REVALIDATION_MESSAGE)
                    return renderer(persisted)
            except (OSError, ValueError):
                raise DeferredExportUnavailable(_EXPORT_REVALIDATION_MESSAGE) from None
        return renderer(authoritative)

    return render
