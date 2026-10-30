"""Explicit, attributable static references kept apart from automatic candidates."""

from __future__ import annotations

from hashlib import sha256

import streamlit as st

from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.reviews.reference_audit import (
    correct_reviewer_selected_reference,
    reference_status,
    withdraw_reviewer_selected_reference,
)
from scopeproof_core.reviews.selected_references import (
    MAX_REFERENCE_LINE_BYTES,
    MAX_REFERENCE_PAGE_LINES,
    REVIEWER_SELECTED_REFERENCE_BOUNDARY,
    append_reviewer_selected_reference,
    selectable_reference_page,
    selectable_reference_sources,
)
from scopeproof_core.schemas.models import (
    MAX_REVIEWER_SELECTED_REFERENCES,
    MAX_SELECTED_REFERENCE_EVENTS,
    MAX_SELECTED_REFERENCE_RECORDS,
    EvidenceSourceScope,
    PullRequestSnapshot,
    RetrievedFile,
    ReviewBundle,
    ReviewState,
    SelectableReferenceLine,
)
from scopeproof_core.storage.json_store import JsonReviewStore

_DRAFT_KEYS = (
    "selected_reference_target",
    "selected_reference_reason",
    "selected_reference_source",
    "selected_reference_line",
    "selected_reference_reviewer",
    "selected_reference_rationale",
)


def selected_reference_draft_pending() -> bool:
    return st.session_state.get("selected_reference_action", "Add") != "Add" or any(
        st.session_state.get(key) not in (None, "") for key in _DRAFT_KEYS
    )


def clear_selected_reference_draft() -> None:
    st.session_state["selected_reference_action"] = "Add"
    st.session_state["selected_reference_target"] = None
    st.session_state["selected_reference_reason"] = ""
    st.session_state["selected_reference_source"] = None
    st.session_state["selected_reference_line"] = None
    st.session_state["selected_reference_page"] = None
    st.session_state["selected_reference_reviewer"] = ""
    st.session_state["selected_reference_rationale"] = ""


def _action_changed() -> None:
    # Widget callbacks run before rendering, so reset dependent widgets here.
    action = st.session_state["selected_reference_action"]
    clear_selected_reference_draft()
    st.session_state["selected_reference_action"] = action
    st.session_state["selected_reference_context_notice"] = (
        "Previous reference action inputs were cleared because the action changed."
    )


def _target_changed() -> None:
    st.session_state["selected_reference_context_notice"] = (
        "Previous reference action inputs were cleared because the target changed."
    )
    st.session_state["selected_reference_source"] = None
    st.session_state["selected_reference_line"] = None
    st.session_state["selected_reference_page"] = None
    st.session_state["selected_reference_reviewer"] = ""
    st.session_state["selected_reference_rationale"] = ""
    st.session_state["selected_reference_reason"] = ""


def _source_changed() -> None:
    st.session_state["selected_reference_page"] = (
        0 if st.session_state.get("selected_reference_source") else None
    )
    st.session_state["selected_reference_line"] = None


def _page_changed() -> None:
    st.session_state["selected_reference_line"] = None


def _source_key(scope: EvidenceSourceScope, path: str) -> str:
    return f"{scope.value}:{path}"


def _source_label(value: str) -> str:
    scope, path = value.split(":", 1)
    label = "Changed file" if scope == "changed_file" else "Unchanged file"
    return f"{label} · {path}"


def render_selected_reference_records(bundle: ReviewBundle, criterion_id: str) -> None:
    references = [r for r in bundle.reviewer_selected_references if r.criterion_id == criterion_id]
    st.markdown("### Reviewer-selected references")
    st.caption(REVIEWER_SELECTED_REFERENCE_BOUNDARY)
    if not references:
        st.caption("No reviewer-selected references recorded for this criterion.")
    for reference in references:
        status = reference_status(
            bundle.reviewer_selected_references,
            bundle.selected_reference_events,
            reference.reference_id,
        ).title()
        with st.expander(
            f"Selected reference · {reference.file_path}:{reference.line_number} · {status}"
        ):
            st.caption("Reference status")
            st.text(status)
            st.caption("Reference ID")
            st.code(reference.reference_id, language=None)
            st.caption("Criterion and confirmed revision")
            st.text(f"{reference.criterion_id} · revision {reference.criteria_revision_number}")
            st.caption("Source head")
            st.code(reference.head_sha, language=None)
            st.caption("Static source type and level")
            st.text(f"{reference.evidence_type.value} · {reference.evidence_level.value}")
            st.code(reference.excerpt)
            st.markdown(render_artifact_reference_markdown(reference.permalink))
            st.caption("Selected by")
            st.text(reference.reviewer)
            st.caption("Selection rationale")
            st.text(reference.rationale)
            st.caption("Recorded at")
            st.text(reference.selected_at.isoformat())
            for event in bundle.selected_reference_events:
                if reference.reference_id not in (
                    event.reference_id,
                    event.replacement_reference_id,
                ):
                    continue
                st.caption("Selected-reference audit event")
                st.code(event.event_id, language=None)
                st.text(event.action.title())
                st.caption("Original reference ID")
                st.code(event.reference_id, language=None)
                if event.replacement_reference_id:
                    st.caption("Replacement reference ID")
                    st.code(event.replacement_reference_id, language=None)
                st.caption("Action recorded by")
                st.text(event.reviewer)
                st.caption("Action reason")
                st.text(event.reason)
                st.caption("Action recorded at")
                st.text(event.occurred_at.isoformat())


def _render_source_selection(
    state: ReviewState,
    snapshot: PullRequestSnapshot,
    criterion_id: str,
    unchanged_files: list[RetrievedFile] | None,
) -> SelectableReferenceLine | None:
    try:
        catalog = selectable_reference_sources(state, snapshot, unchanged_files=unchanged_files)
    except ValueError:
        st.warning("Matching inspectable source is unavailable for this confirmed review.")
        return None
    if not catalog:
        st.caption("No inspectable source lines are available for explicit selection.")
        return None
    st.caption(
        f"Bounded source view: {MAX_REFERENCE_PAGE_LINES:,} eligible lines per file page; "
        f"at most {MAX_REFERENCE_LINE_BYTES:,} UTF-8 bytes per line. "
        "Removed, skipped, truncated and ambiguous sources are unavailable."
    )
    st.text(f"Criterion {criterion_id} · revision {state.criteria_revision.number}")
    st.code(state.review.head_sha, language=None)
    sources = {_source_key(item.source_scope, item.file_path): item for item in catalog}
    source = st.selectbox(
        "Reference source",
        list(sources),
        index=None,
        key="selected_reference_source",
        format_func=_source_label,
        on_change=_source_changed,
    )
    selected_source = sources.get(source)
    page_count = (
        (selected_source.eligible_line_count + MAX_REFERENCE_PAGE_LINES - 1)
        // MAX_REFERENCE_PAGE_LINES
        if selected_source is not None
        else 0
    )
    page_index = st.selectbox(
        "Reference page",
        list(range(page_count)),
        index=0 if page_count else None,
        key="selected_reference_page",
        format_func=lambda index: f"Page {index + 1} of {page_count}",
        disabled=selected_source is None,
        on_change=_page_changed,
    )
    source_lines = []
    if selected_source is not None and page_index is not None:
        try:
            page = selectable_reference_page(
                state,
                snapshot,
                source_scope=selected_source.source_scope,
                file_path=selected_source.file_path,
                page_index=page_index,
                unchanged_files=unchanged_files,
            )
        except ValueError:
            st.warning("This source page is unavailable. Refresh the source selection.")
            return None
        source_lines = page.lines
        first = page_index * MAX_REFERENCE_PAGE_LINES + 1
        st.caption(
            f"{first:,} to {first + len(source_lines) - 1:,} of "
            f"{page.source.eligible_line_count:,} eligible lines in this file. "
            "Reference line values are physical Git line numbers."
        )
    number = st.selectbox(
        "Reference line",
        [line.line_number for line in source_lines],
        index=None,
        key="selected_reference_line",
        disabled=source is None,
    )
    selected = next((line for line in source_lines if line.line_number == number), None)
    if selected is not None:
        st.caption(
            f"{selected.evidence_type.value} · {selected.evidence_level.value} · static reference"
        )
        st.code(selected.excerpt)
    return selected


def render_selected_references(
    state: ReviewState,
    snapshot: PullRequestSnapshot | None,
    criterion_id: str,
    unchanged_files: list[RetrievedFile] | None = None,
    *,
    blocked: bool = False,
) -> ReviewState | None:
    """Return a core-validated transition only after explicit source/line/save input."""
    source_bytes = "" if snapshot is None else snapshot.model_dump_json()
    source_bytes += "".join(f.model_dump_json() for f in (unchanged_files or []))
    context = (
        state.review.review_id,
        state.review.head_sha,
        state.criteria_revision.number,
        criterion_id,
        sha256(source_bytes.encode("utf-8")).hexdigest(),
    )
    prior_context = st.session_state.get("selected_reference_context")
    st.session_state["selected_reference_context"] = context
    if (
        prior_context is not None
        and prior_context != context
        and selected_reference_draft_pending()
    ):
        clear_selected_reference_draft()
        st.session_state["selected_reference_context_notice"] = (
            "Unsaved source reference inputs were cleared because their source or target changed."
        )
        st.rerun()
    notice = st.session_state.pop("selected_reference_context_notice", None)
    if notice:
        st.info(notice)
    save_notice = st.session_state.pop("selected_reference_save_notice", None)
    if save_notice:
        st.success(save_notice)
    with st.expander("Select a source reference", expanded=selected_reference_draft_pending()):
        st.caption(REVIEWER_SELECTED_REFERENCE_BOUNDARY)
        active_count = len(state.bundle.active_reviewer_selected_reference_ids)
        retained_count = len(state.bundle.reviewer_selected_references)
        event_count = len(state.bundle.selected_reference_events)
        st.caption(
            f"{active_count} of {MAX_REVIEWER_SELECTED_REFERENCES} active references · "
            f"{retained_count} of {MAX_SELECTED_REFERENCE_RECORDS} retained references · "
            f"{event_count} of {MAX_SELECTED_REFERENCE_EVENTS} audit events"
        )
        history_full = retained_count >= MAX_SELECTED_REFERENCE_RECORDS
        events_full = event_count >= MAX_SELECTED_REFERENCE_EVENTS
        if history_full:
            st.caption(
                "Retained reference history is full. Add and Correct are unavailable. "
                "Withdraw remains available for active references."
            )
        if events_full:
            st.caption("Audit event history is full. Further reference actions are unavailable.")
        action = st.selectbox(
            "Selected-reference action",
            ["Add", "Correct", "Withdraw"],
            key="selected_reference_action",
            on_change=_action_changed,
        )
        if state.review.final_acceptance:
            st.caption("Revoke final acceptance before changing a source reference.")
            return None
        target = None
        if action != "Add":
            active_ids = set(state.bundle.active_reviewer_selected_reference_ids)
            targets = {
                r.reference_id: r
                for r in state.bundle.reviewer_selected_references
                if r.criterion_id == criterion_id and r.reference_id in active_ids
            }
            target = st.selectbox(
                "Active reference to change",
                list(targets),
                index=None,
                key="selected_reference_target",
                on_change=_target_changed,
                format_func=lambda value: (
                    f"{targets[value].file_path}:{targets[value].line_number} · {value}"
                ),
            )
            if not targets:
                st.caption("No active selected references are available for this criterion.")
        if action != "Withdraw" and snapshot is None:
            st.caption(
                "Load matching source before adding or correcting a reference. "
                "Saved references remain available for withdrawal."
            )
            return None
        selected = None
        if action != "Withdraw":
            selected = _render_source_selection(state, snapshot, criterion_id, unchanged_files)
        reviewer = st.text_input(
            "Reference reviewer (required)", key="selected_reference_reviewer", max_chars=200
        )
        rationale = ""
        if action != "Withdraw":
            rationale = st.text_area(
                "Why this reference matters", key="selected_reference_rationale", max_chars=2000
            )
        reason = ""
        if action != "Add":
            reason = st.text_area(
                "Reason for reference action (required)",
                key="selected_reference_reason",
                max_chars=2000,
            )
        if blocked:
            st.caption(
                "Resolve other pending review inputs or local save conflicts before recording."
            )
        if st.button(
            "Save selected reference",
            key="save_selected_reference",
            disabled=blocked
            or (action != "Withdraw" and history_full)
            or (action != "Add" and events_full)
            or (action == "Add" and active_count >= MAX_REVIEWER_SELECTED_REFERENCES)
            or not reviewer.strip()
            or (action != "Withdraw" and (selected is None or not rationale.strip()))
            or (action != "Add" and (target is None or not reason.strip())),
        ):
            try:
                fingerprint = JsonReviewStore.state_fingerprint(state)
                if action == "Withdraw":
                    return withdraw_reviewer_selected_reference(
                        state,
                        reference_id=target,
                        reviewer=reviewer,
                        reason=reason,
                        expected_state_fingerprint=fingerprint,
                    )
                if action == "Correct":
                    return correct_reviewer_selected_reference(
                        state,
                        reference_id=target,
                        snapshot=snapshot,
                        selected=selected,
                        reviewer=reviewer,
                        reason=reason,
                        rationale=rationale,
                        expected_state_fingerprint=fingerprint,
                        unchanged_files=unchanged_files,
                    )
                return append_reviewer_selected_reference(
                    state,
                    snapshot=snapshot,
                    selected=selected,
                    criterion_id=criterion_id,
                    reviewer=reviewer,
                    rationale=rationale,
                    expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
                    unchanged_files=unchanged_files,
                )
            except ValueError:
                st.error(
                    "The source reference could not be recorded. "
                    "Review the source and current record, then try again."
                )
        return None
