"""Click-time export revalidation for the local ScopeProof workbench."""

from __future__ import annotations

from collections.abc import Callable

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
                persisted = store.load(captured.review.review_id)
            except (OSError, ValueError):
                raise DeferredExportUnavailable(
                    _EXPORT_REVALIDATION_MESSAGE
                ) from None
            if JsonReviewStore.state_fingerprint(persisted) != expected_fingerprint:
                raise DeferredExportUnavailable(
                    _EXPORT_REVALIDATION_MESSAGE
                )
            authoritative = persisted
        return renderer(authoritative)

    return render
