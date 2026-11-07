"""Explicit, session-only selection of validated saved comparison baselines."""

from __future__ import annotations

import streamlit as st

from apps.web.deferred_exports import SavedComparisonExportLease, deferred_saved_requirements_export
from apps.web.scope_file_preview import scope_draft_pending
from scopeproof_core.reporting.criteria_comparison import export_saved_requirements_markdown
from scopeproof_core.reviews.comparison import (
    ComparisonIncompatible,
    ComparisonRejectionReason,
    ReviewComparison,
)
from scopeproof_core.reviews.criteria_comparison import (
    CRITERIA_COMPARISON_BOUNDARY,
    RecordedCriteriaDiff,
)
from scopeproof_core.reviews.saved_comparison import (
    SavedComparisonSelection,
    locked_saved_comparison,
    locked_saved_requirements_comparison,
    prepare_saved_comparison,
    prepare_saved_requirements_comparison,
)
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.discovery import (
    SavedReviewDiscoveryEntry,
    format_saved_review_label,
    load_discovered_review,
)
from scopeproof_core.storage.json_store import JsonReviewStore

_COMPARISON_REFUSAL_GUIDANCE = {
    ComparisonRejectionReason.DIFFERENT_REPOSITORY: (
        "The recorded repository identifiers differ. Choose a baseline from the same repository."
    ),
    ComparisonRejectionReason.DIFFERENT_PULL_REQUEST: (
        "The recorded pull request numbers differ. Choose a baseline from the same pull request."
    ),
    ComparisonRejectionReason.MISSING_EXACT_HEAD: (
        "One analysis lacks the full reviewed head required for evidence comparison. "
        "Use analyses that record their full reviewed heads."
    ),
    ComparisonRejectionReason.DIFFERENT_CRITERIA: (
        "The confirmed criterion definitions differ. "
        "Evidence comparison requires the same definitions in the same order."
    ),
    ComparisonRejectionReason.MISSING_CRITERIA_SOURCE: (
        "One analysis is missing confirmed criteria source provenance. "
        "Use analyses with recorded confirmed sources."
    ),
    ComparisonRejectionReason.DIFFERENT_CRITERIA_SOURCE: (
        "The recorded criteria source provenance differs. "
        "Evidence comparison requires matching source details."
    ),
}


def clear_saved_comparison_selection(*, clear_choice: bool = True) -> None:
    """Invalidate callbacks without accessing Streamlit state from download workers."""
    for lease_key in ("saved_comparison_export_lease", "saved_requirements_export_lease"):
        lease = st.session_state.get(lease_key)
        if lease is not None:
            lease.invalidate()
    st.session_state["saved_comparison_selection"] = None
    st.session_state["saved_requirements_selection"] = None
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


def _clear_scope_draft() -> None:
    clear_saved_comparison_selection()
    for key in ("scope_file_path", "scope_disposition", "scope_criterion_id"):
        st.session_state[key] = None
    st.session_state["scope_note"] = ""


def _render_saved_requirements(
    diff: RecordedCriteriaDiff, selection: SavedComparisonSelection,
) -> None:
    st.markdown("### Saved requirements comparison")
    st.warning(CRITERIA_COMPARISON_BOUNDARY)
    st.text(f"{diff.current.repository} · PR #{diff.current.pr_number}")
    location = (
        f"History {selection.history_index + 1}" if selection.history_index is not None
        else "Active analysis"
    )
    st.text(f"Baseline analysis: {location}")
    st.text(f"Recorded source text changed: {'Yes' if diff.source_text_changed else 'No'}")
    st.text(
        f"Recorded source provenance changed: {'Yes' if diff.source_provenance_changed else 'No'}"
    )
    st.text(f"Shared criterion order changed: {'Yes' if diff.criterion_order_changed else 'No'}")
    for change in diff.criterion_changes:
        st.text(
            f"{change.criterion_id} · {change.kind.replace('_', ' ').capitalize()}\n"
            f"Baseline position: {change.previous_position or 'None'}\n"
            f"Current position: {change.current_position or 'None'}\n"
            f"Changed fields: {', '.join(change.changed_fields) or 'None'}"
        )
    for label, snapshot in (
        ("Baseline recorded requirements", diff.previous),
        ("Current recorded requirements", diff.current),
    ):
        st.markdown(f"#### {label}")
        st.text(f"Saved record: {snapshot.review_id}")
        st.text(f"Recorded head: {snapshot.head_sha}")
        st.text(f"Criteria revision: {snapshot.revision_number}")
        st.text(f"Confirmation: {'Confirmed (asserted)' if snapshot.confirmed else 'Unconfirmed'}")
        provenance = snapshot.source_provenance
        if provenance is None:
            st.text("Recorded source provenance unavailable")
        else:
            st.text(f"Source reference: {provenance.source_uri}")
            st.text(f"Source revision: {provenance.source_revision or 'Not recorded'}")
            st.text(
                f"Confirmed by: {provenance.confirmed_by} · {provenance.confirmed_at.isoformat()}"
            )
        st.caption("Recorded source text")
        st.text(snapshot.source_text)
        st.caption("Recorded criterion definitions")
        for criterion in snapshot.criteria:
            st.text(
                f"{criterion.criterion_id} · {criterion.priority.value} · "
                f"{criterion.required_evidence_level.value}\n{criterion.text}\n"
                f"Type: {criterion.criterion_type.value} · "
                f"Origin: {criterion.criterion_source.value}\n"
                f"Source span: {criterion.source_span or 'Not recorded'}"
            )


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
    requirements_lease = st.session_state.setdefault(
        "saved_requirements_export_lease", SavedComparisonExportLease(),
    )
    has_scope_draft = scope_draft_pending(current)
    eligible = (
        current is not None and current.bundle is not None
        and current_is_saved and not has_scope_draft
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
        if has_scope_draft:
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
            except ComparisonIncompatible as error:
                st.warning(
                    "Selected saved analysis cannot be compared. "
                    + _COMPARISON_REFUSAL_GUIDANCE[error.reason]
                )
                if baseline_id != current.review.review_id and error.reason in {
                    ComparisonRejectionReason.DIFFERENT_CRITERIA,
                    ComparisonRejectionReason.DIFFERENT_CRITERIA_SOURCE,
                }:
                    st.caption(
                        "Use Compare saved requirements to inspect the recorded differences."
                    )
            except (OSError, ValueError):
                st.warning(
                    "Selected saved analysis cannot be compared. The selected comparison "
                    "could not be validated. Reopen the current review and select the "
                    "baseline again."
                )
            else:
                st.session_state["saved_comparison_selection"] = selection

        if baseline_id is not None and baseline_id != current.review.review_id:
            requirements_clicked = st.button(
                "Compare saved requirements", key="compare_saved_requirements",
                disabled=not eligible or not has_analysis,
            )
            if requirements_clicked and eligible and has_analysis:
                _analysis_changed()
                try:
                    st.session_state["saved_requirements_selection"] = (
                        prepare_saved_requirements_comparison(
                            store, current, baseline_id, history_index=history_index,
                            expected_baseline_fingerprint=expected_baseline_fingerprint,
                        )
                    )
                except (OSError, ValueError):
                    st.warning(
                        "Saved requirements could not be compared. Select available analyses "
                        "from the same pull request."
                    )
        requirements_selection = st.session_state.get("saved_requirements_selection")
        if requirements_selection is not None and eligible:
            try:
                with locked_saved_requirements_comparison(store, requirements_selection) as diff:
                    _render_saved_requirements(diff, requirements_selection)
                    requirements_lease.selection = requirements_selection
                    st.download_button(
                        "Download requirements comparison",
                        data=deferred_saved_requirements_export(
                            requirements_selection, export_saved_requirements_markdown,
                            store=store, lease=requirements_lease,
                        ),
                        file_name=f"{requirements_selection.current_review_id}-requirements.md",
                        mime="text/markdown",
                        key="download_saved_requirements_markdown", on_click="ignore",
                    )
            except (OSError, ValueError):
                clear_saved_comparison_selection(clear_choice=False)
                st.warning("Saved requirements changed or became unavailable. Select again.")

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
