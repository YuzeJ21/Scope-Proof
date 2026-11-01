"""Explicit read-only saved requirements changes, separate from evidence comparison."""

from collections.abc import Callable

import streamlit as st

from apps.web.deferred_exports import (
    CriteriaComparisonExportLease,
    deferred_criteria_comparison_export,
)
from scopeproof_core.reporting.criteria_comparison import (
    export_criteria_comparison_json,
    export_criteria_comparison_markdown,
)
from scopeproof_core.reviews.criteria_comparison import (
    CRITERIA_COMPARISON_BOUNDARY,
    locked_criteria_comparison,
    prepare_criteria_comparison,
)
from scopeproof_core.reviews.historical_analysis import HistoricalAnalysisSelection
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore


def clear_criteria_comparison() -> None:
    lease = st.session_state.get("criteria_comparison_export_lease")
    if lease is not None:
        lease.invalidate()
    st.session_state["criteria_comparison_selection"] = None


def render_criteria_comparison(
    current: ReviewState,
    historical: HistoricalAnalysisSelection,
    *,
    store: JsonReviewStore,
    readable_markdown: Callable[[str], str],
) -> None:
    if "criteria_comparison_export_lease" not in st.session_state:
        st.session_state["criteria_comparison_export_lease"] = CriteriaComparisonExportLease()
    st.caption(
        "Optionally inspect recorded requirements changes against the current saved revision. "
        "This does not compare evidence or include unsaved drafts."
    )
    if st.button("Compare with saved current criteria", key="compare_saved_criteria"):
        clear_criteria_comparison()
        try:
            selection = prepare_criteria_comparison(store, current, historical.history_index)
            if selection.historical != historical:
                raise ValueError("historical selection differs from saved criteria")
            st.session_state["criteria_comparison_selection"] = selection
            st.session_state["criteria_comparison_export_lease"].selection = selection
        except (OSError, ValueError):
            st.warning("Saved requirements are unavailable or changed. Reopen and compare again.")
    selection = st.session_state.get("criteria_comparison_selection")
    if selection is None:
        return
    try:
        if selection.historical != historical:
            raise ValueError("requirements comparison no longer matches historical selection")
        with locked_criteria_comparison(store, selection) as report:
            st.markdown("### Saved criteria revision changes")
            st.warning(CRITERIA_COMPARISON_BOUNDARY)
            with st.container(key="criteria_comparison_preview"):
                st.markdown(readable_markdown(export_criteria_comparison_markdown(report)))
            for label, renderer, suffix, mime in (
                ("JSON", export_criteria_comparison_json, "json", "application/json"),
                ("Markdown", export_criteria_comparison_markdown, "md", "text/markdown"),
            ):
                st.download_button(
                    f"Download criteria changes {label}",
                    data=deferred_criteria_comparison_export(
                        selection, renderer, store=store,
                        lease=st.session_state["criteria_comparison_export_lease"],
                    ), file_name=(
                        f"{historical.review_id}-history-{historical.history_index + 1}"
                        f"-criteria-changes.{suffix}"
                    ), mime=mime, key=f"download_criteria_changes_{suffix}", on_click="ignore",
                )
    except (OSError, ValueError):
        clear_criteria_comparison()
        st.warning("Saved requirements are unavailable or changed. Reopen and compare again.")
