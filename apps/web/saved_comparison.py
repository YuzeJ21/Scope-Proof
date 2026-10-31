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
from scopeproof_core.storage.discovery import (
    SavedReviewDiscoveryEntry,
    format_saved_review_label,
    load_discovered_review,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def clear_saved_comparison_selection(*, clear_choice: bool = True) -> None:
    """Invalidate callbacks without accessing Streamlit state from download workers."""
    lease = st.session_state.get("saved_comparison_export_lease")
    if lease is not None:
        lease.invalidate()
    st.session_state["saved_comparison_selection"] = None
    if clear_choice:
        st.session_state["saved_comparison_baseline"] = None
        st.session_state["saved_comparison_analysis"] = None
        st.session_state["saved_comparison_analysis_context"] = None


def _baseline_changed() -> None:
    _analysis_changed()
    st.session_state["saved_comparison_analysis"] = None
    st.session_state["saved_comparison_analysis_context"] = None


def _analysis_changed() -> None:
    clear_saved_comparison_selection(clear_choice=False)
    st.session_state["comparison_base_bundle"] = None


def _render_foreign_analysis_selector(
    store: JsonReviewStore, baseline_id: str, *, eligible: bool,
    expected_preview_fingerprint: str | None = None,
) -> tuple[int | None, str | None, bool]:
    """Load only the chosen record and bind displayed positions to its complete snapshot."""
    try:
        baseline = load_discovered_review(
            store, baseline_id, expected_fingerprint=expected_preview_fingerprint,
        )
        fingerprint = store.state_fingerprint(baseline)
    except (OSError, ValueError):
        _analysis_changed()
        st.session_state["saved_comparison_analysis"] = None
        st.session_state["saved_comparison_analysis_context"] = (baseline_id, "unavailable")
        st.warning(
            "Selected saved record is unavailable or changed since its preview. "
            "Refresh saved details and select its baseline again."
        )
        st.selectbox(
            "Baseline analysis", options=[], index=None, disabled=True,
            key="saved_comparison_analysis",
        )
        return None, None, False

    options: dict[str, tuple[int | None, str]] = {}
    if baseline.bundle is not None:
        options["active"] = (
            None, f"Active analysis · criteria revision {baseline.bundle.criteria_revision_number} "
            f"· head {baseline.bundle.review.head_sha}",
        )
    for index, historical in enumerate(baseline.analysis_history):
        options[f"history:{index}"] = (
            index, f"History {index + 1} · criteria revision {historical.criteria_revision_number} "
            f"· head {historical.review.head_sha}",
        )
    context = (baseline_id, fingerprint)
    previous_context = st.session_state.get("saved_comparison_analysis_context")
    if previous_context != context:
        _analysis_changed()
        st.session_state["saved_comparison_analysis"] = (
            "active" if previous_context is None and "active" in options else None
        )
        st.session_state["saved_comparison_analysis_context"] = context
        if previous_context is not None:
            st.warning("Saved baseline changed. Select its analysis again before comparing.")
    if not options:
        st.caption("No active or retained historical analysis is available in this saved record.")
    st.text(f"Baseline source record: {baseline_id}")
    choice = st.selectbox(
        "Baseline analysis", options=list(options), index=None,
        key="saved_comparison_analysis", format_func=lambda value: options[value][1],
        placeholder="Select an analysis from this saved record",
        disabled=not eligible or not options, on_change=_analysis_changed,
    )
    return (
        options[choice][0] if choice is not None else None,
        fingerprint,
        choice is not None,
    )


def _scope_draft_pending(current: ReviewState | None) -> bool:
    """Submitted controls remain populated; only a differing/unsubmitted form is a draft."""
    path = st.session_state.get("scope_file_path")
    disposition = st.session_state.get("scope_disposition")
    note = st.session_state.get("scope_note", "")
    criterion_id = (
        st.session_state.get("scope_criterion_id")
        if disposition == "within_confirmed_criteria" else None
    )
    if not any((path, disposition, note, criterion_id)):
        return False
    latest = (
        {item.path: item for item in current.bundle.file_scope_decisions}.get(path)
        if current is not None and current.bundle is not None else None
    )
    return latest is None or (
        latest.disposition, latest.criterion_id, latest.note, latest.reviewer
    ) != (
        disposition, criterion_id, note,
        st.session_state.get("decision_reviewer", "").strip(),
    )


def _clear_scope_draft() -> None:
    clear_saved_comparison_selection()
    for key in ("scope_file_path", "scope_disposition", "scope_criterion_id"):
        st.session_state[key] = None
    st.session_state["scope_note"] = ""


def render_saved_comparison_selector(
    current: ReviewState | None,
    *,
    store: JsonReviewStore,
    saved_review_ids: list[str],
    current_is_saved: bool,
    discovery_entries: dict[str, SavedReviewDiscoveryEntry] | None = None,
) -> tuple[ReviewComparison | None, SavedComparisonSelection | None]:
    """Read selected saved truth on each rerun; return no stale or unapplied comparison."""
    if "saved_comparison_export_lease" not in st.session_state:
        st.session_state["saved_comparison_export_lease"] = SavedComparisonExportLease()
    scope_draft_pending = _scope_draft_pending(current)
    eligible = (
        current is not None and current.bundle is not None
        and current_is_saved and not scope_draft_pending
    )
    context = (
        current.review.review_id if current is not None else None,
        store.state_fingerprint(current) if eligible else None,
    )
    if st.session_state.get("saved_comparison_context") != context:
        clear_saved_comparison_selection()
        st.session_state["saved_comparison_context"] = context
    if current is None:
        return None, None

    entries = discovery_entries or {}
    sources: dict[str, tuple[str, int | None, str]] = {
        f"saved:{review_id}": (review_id, None, (
            format_saved_review_label(entries[review_id])
            if review_id in entries else f"Saved review · {review_id}"
        ))
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
            "Choose another saved review, then its active or historical analysis, or choose "
            "a retained analysis from this review. Comparing is read-only; "
            "it does not reload GitHub, rerun analysis or carry forward a decision."
        )
        if not eligible:
            clear_saved_comparison_selection()
            st.info(
                "Saved comparison requires a saved active analysis with no pending inputs "
                "or save conflict. Save or reopen the review before selecting a baseline."
            )
        if scope_draft_pending:
            st.info(
                "Unsubmitted file-scope inputs are not part of the saved review. Save the "
                "scope decision below or clear those inputs before comparing."
            )
            st.button(
                "Clear pending file-scope inputs", key="clear_saved_comparison_scope_draft",
                on_click=_clear_scope_draft,
            )
        if not sources:
            st.caption("No other saved review or historical analysis is available.")
        candidate = st.selectbox(
            "Comparison baseline", options=list(sources), index=None,
            placeholder="Select a saved analysis", key="saved_comparison_baseline",
            format_func=lambda key: sources[key][2], disabled=not eligible or not sources,
            on_change=_baseline_changed,
        )
        has_analysis = candidate is not None
        baseline_id, history_index, _ = sources.get(candidate, (None, None, ""))
        expected_baseline_fingerprint = None
        if baseline_id is not None and baseline_id != current.review.review_id:
            history_index, expected_baseline_fingerprint, has_analysis = (
                _render_foreign_analysis_selector(
                    store, baseline_id, eligible=eligible,
                    expected_preview_fingerprint=(
                        entries[baseline_id].metadata.state_fingerprint
                        if baseline_id in entries and entries[baseline_id].metadata is not None
                        else None
                    ),
                )
            )
        elif baseline_id is not None:
            expected_baseline_fingerprint = store.state_fingerprint(current)
        if st.button(
            "Compare selected saved analysis", key="compare_saved_analysis",
            disabled=not eligible or not has_analysis,
        ):
            _analysis_changed()
            try:
                selection = prepare_saved_comparison(
                    store, current, baseline_id, history_index=history_index,
                    expected_baseline_fingerprint=expected_baseline_fingerprint,
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
