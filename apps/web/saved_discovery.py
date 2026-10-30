"""Explicit, bounded, session-only previews of asserted local saved metadata."""

from __future__ import annotations

import streamlit as st

from apps.web.saved_comparison import clear_saved_comparison_selection
from scopeproof_core.storage.discovery import (
    SavedReviewDiscoveryEntry,
    discover_saved_review_page,
    matching_saved_review_ids,
    saved_review_ids_fingerprint,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def _clear_targets() -> None:
    st.session_state["saved_reopen_review_id"] = None
    st.session_state["delete_saved_review_confirmed"] = False
    clear_saved_comparison_selection()
    st.session_state["saved_discovery_notice"] = (
        "Saved review choices cleared. Select a record again before reopening or comparing."
    )


def clear_saved_delete_confirmation() -> None:
    """A new reopen target never inherits another target's deletion consent."""
    st.session_state["delete_saved_review_confirmed"] = False


def _page_changed() -> None:
    _clear_targets()
    st.session_state["saved_discovery_loaded_page"] = None
    st.session_state["saved_discovery_query"] = ""


def render_saved_discovery(
    store: JsonReviewStore,
    saved_review_ids: list[str],
) -> tuple[list[str], dict[str, SavedReviewDiscoveryEntry]]:
    """Default to IDs; load and search only an explicitly requested ten-record page."""
    inventory = saved_review_ids_fingerprint(saved_review_ids)
    previous = st.session_state.get("saved_discovery_inventory")
    if previous is not None and previous != inventory:
        if st.session_state.get("saved_discovery_loaded_page") is not None:
            _page_changed()
            st.info(
                "Saved record inventory changed. Select a review again; reload details if needed."
            )
        elif st.session_state.get("saved_reopen_review_id") not in saved_review_ids:
            st.session_state["saved_reopen_review_id"] = None
            clear_saved_delete_confirmation()
    st.session_state["saved_discovery_inventory"] = inventory
    pages = max(1, (len(saved_review_ids) + 9) // 10)
    if st.session_state.get("saved_discovery_page", 1) > pages:
        st.session_state["saved_discovery_page"] = 1
    page_number = st.number_input(
        "Saved details page",
        min_value=1,
        max_value=pages,
        value=1,
        step=1,
        key="saved_discovery_page",
        on_change=_page_changed,
    )
    st.caption(
        "Load up to 10 saved records on this page, limited to 1 MiB per record "
        "and 10 MiB per request. Details are asserted local saved metadata."
    )
    if st.button("Load saved review details", key="load_saved_review_details"):
        _clear_targets()
        try:
            page = discover_saved_review_page(store, page_index=int(page_number) - 1)
        except (OSError, ValueError):
            st.session_state["saved_discovery_loaded_page"] = None
            st.warning("Saved details are unavailable. Refresh the record list or use a review ID.")
        else:
            if page.candidate_ids_fingerprint != inventory:
                st.session_state["saved_discovery_loaded_page"] = None
                st.warning("Saved record inventory changed. Refresh before loading details again.")
            else:
                st.session_state["saved_discovery_loaded_page"] = page
    notice = st.session_state.pop("saved_discovery_notice", None)
    if notice is not None:
        st.info(notice)
    page = st.session_state.get("saved_discovery_loaded_page")
    query = st.text_input(
        "Search loaded page by repository, PR, head, revision or ID",
        key="saved_discovery_query",
        max_chars=200,
        disabled=page is None,
        on_change=_clear_targets,
    )
    st.checkbox(
        "Enter a review ID directly",
        key="saved_discovery_direct_id",
        on_change=_clear_targets,
        help="Reopen a record outside the loaded page or its preview limits using full validation.",
    )
    if page is None:
        return saved_review_ids, {}
    entries = {entry.review_id: entry for entry in page.entries}
    visible = matching_saved_review_ids(page, query)
    st.caption(
        f"Loaded page {page.page_index + 1} of {pages}: {len(page.entries)} of "
        f"{page.total_review_count} candidate records; {len(visible)} match on this loaded page. "
        "Search covers this page only. Metadata unavailable means preview limits or validation "
        "prevented details. Details are a loaded snapshot; refresh to update them. "
        "Opening or comparing a record still performs full validation."
    )
    if not visible:
        st.info(
            "No matches on this loaded page. Choose another page or enter a review ID directly."
        )
    return visible, entries


def render_saved_review_summary(entry: SavedReviewDiscoveryEntry | None) -> None:
    """Render bounded metadata as inert text, without gate or fresh-source claims."""
    if entry is None or entry.metadata is None:
        return
    metadata = entry.metadata
    st.text(
        f"Local saved repository: {metadata.repository}\nPR: #{metadata.pr_number}\n"
        f"Head: {metadata.head_sha}\nCriteria revision: {metadata.criteria_revision_number}\n"
        f"Active analysis recorded: {'yes' if metadata.has_active_analysis else 'no'}\n"
        f"Retained historical analyses: {metadata.retained_history_count}"
    )
