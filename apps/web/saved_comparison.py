"""Explicit, session-only selection of validated saved comparison baselines."""

from __future__ import annotations

import streamlit as st

from apps.web.deferred_exports import SavedComparisonExportLease
from scopeproof_core.reviews.comparison import ReviewComparison
from scopeproof_core.reviews.saved_comparison import (
    SavedComparisonSelection,
    locked_saved_comparison,
    prepare_saved_comparison,
)
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore


def clear_saved_comparison_selection(*, clear_choice: bool = True) -> None:
    """Invalidate callbacks without accessing Streamlit state from download workers."""
    lease = st.session_state.get("saved_comparison_export_lease")
    if lease is not None:
        lease.selection = None
    st.session_state["saved_comparison_selection"] = None
    if clear_choice:
        st.session_state["saved_comparison_baseline"] = None


def _baseline_changed() -> None:
    clear_saved_comparison_selection(clear_choice=False)
    st.session_state["comparison_base_bundle"] = None


def render_saved_comparison_selector(
    current: ReviewState | None,
    *,
    store: JsonReviewStore,
    saved_review_ids: list[str],
    current_is_saved: bool,
) -> tuple[ReviewComparison | None, SavedComparisonSelection | None]:
    """Read selected saved truth on each rerun; return no stale or unapplied comparison."""
    if "saved_comparison_export_lease" not in st.session_state:
        st.session_state["saved_comparison_export_lease"] = SavedComparisonExportLease()
    eligible = current is not None and current.bundle is not None and current_is_saved
    context = (
        current.review.review_id if current is not None else None,
        store.state_fingerprint(current) if eligible else None,
    )
    if st.session_state.get("saved_comparison_context") != context:
        clear_saved_comparison_selection()
        st.session_state["saved_comparison_context"] = context
    if current is None:
        return None, None

    sources: dict[str, tuple[str, int | None, str]] = {
        f"saved:{review_id}": (review_id, None, f"Saved review · {review_id}")
        for review_id in sorted(saved_review_ids) if review_id != current.review.review_id
    }
    for index, historical in enumerate(current.analysis_history):
        sources[f"history:{index}"] = (
            current.review.review_id, index,
            f"History {index + 1} · criteria revision {historical.criteria_revision_number} "
            f"· head {historical.review.head_sha}",
        )
    candidate = st.session_state.get("saved_comparison_baseline")
    if candidate is not None and candidate not in sources:
        clear_saved_comparison_selection()

    comparison = None
    with st.expander("Compare saved analyses", expanded=candidate is not None):
        st.text(
            f"Current saved review: {current.review.review_id}\n"
            f"Head: {current.review.head_sha}\n"
            f"Criteria revision: {current.criteria_revision.number}"
        )
        st.caption(
            "Choose another saved review or a retained analysis. Comparing is read-only; "
            "it does not reload GitHub, rerun analysis or carry forward a decision."
        )
        if not eligible:
            clear_saved_comparison_selection()
            st.info(
                "Saved comparison requires a saved active analysis with no pending inputs "
                "or save conflict. Save or reopen the review before selecting a baseline."
            )
        if not sources:
            st.caption("No other saved review or historical analysis is available.")
        candidate = st.selectbox(
            "Comparison baseline", options=list(sources), index=None,
            placeholder="Select a saved analysis", key="saved_comparison_baseline",
            format_func=lambda key: sources[key][2], disabled=not eligible or not sources,
            on_change=_baseline_changed,
        )
        if st.button(
            "Compare selected saved analysis", key="compare_saved_analysis",
            disabled=not eligible or candidate is None,
        ):
            _baseline_changed()
            baseline_id, history_index, _ = sources[candidate]
            try:
                selection = prepare_saved_comparison(
                    store, current, baseline_id, history_index=history_index,
                )
            except (OSError, ValueError):
                st.warning(
                    "Selected saved analysis cannot be compared. Choose analyses from the "
                    "same pull request with identical confirmed criteria and criteria source, "
                    "and verify both saved records are available. The current review is unchanged."
                )
            else:
                st.session_state["saved_comparison_selection"] = selection

        selection = st.session_state.get("saved_comparison_selection")
        if selection is not None and eligible:
            try:
                with locked_saved_comparison(store, selection) as validated:
                    comparison = validated
            except (OSError, ValueError):
                clear_saved_comparison_selection(clear_choice=False)
                selection = None
                st.warning(
                    "Saved comparison expired because a saved record changed or became "
                    "unavailable. Select the baseline again to compare current saved truth."
                )
            else:
                previous = comparison.file_scope.previous
                location = (
                    f"History {selection.history_index + 1}"
                    if selection.history_index is not None else "Active analysis"
                )
                st.text(
                    f"Baseline record: {selection.baseline_review_id}\n"
                    f"Analysis: {location}\nHead: {comparison.previous_head_sha}\n"
                    f"Criteria revision: {previous.criteria_revision_number}"
                )
        st.session_state["saved_comparison_export_lease"].selection = selection
    return comparison, selection
