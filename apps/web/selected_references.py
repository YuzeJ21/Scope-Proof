"""Explicit, attributable static references kept apart from automatic candidates."""

from __future__ import annotations

from hashlib import sha256

import streamlit as st

from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.reviews.selected_references import (
    MAX_REFERENCE_LINE_BYTES,
    MAX_SELECTABLE_REFERENCE_LINES,
    REVIEWER_SELECTED_REFERENCE_BOUNDARY,
    append_reviewer_selected_reference,
    selectable_reference_lines,
)
from scopeproof_core.schemas.models import (
    EvidenceSourceScope,
    PullRequestSnapshot,
    RetrievedFile,
    ReviewBundle,
    ReviewState,
)
from scopeproof_core.storage.json_store import JsonReviewStore

_DRAFT_KEYS = (
    "selected_reference_source",
    "selected_reference_line",
    "selected_reference_reviewer",
    "selected_reference_rationale",
)


def selected_reference_draft_pending() -> bool:
    return any(st.session_state.get(key) not in (None, "") for key in _DRAFT_KEYS)


def clear_selected_reference_draft() -> None:
    st.session_state["selected_reference_source"] = None
    st.session_state["selected_reference_line"] = None
    st.session_state["selected_reference_reviewer"] = ""
    st.session_state["selected_reference_rationale"] = ""


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
        with st.expander(f"Selected reference · {reference.file_path}:{reference.line_number}"):
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
        if snapshot is None:
            st.caption(
                "Load matching source before adding a reference. Saved references remain available."
            )
            return None
        if state.review.final_acceptance:
            st.caption("Revoke final acceptance before adding a source reference.")
            return None
        try:
            lines = selectable_reference_lines(state, snapshot, unchanged_files=unchanged_files)
        except ValueError:
            st.warning("Matching inspectable source is unavailable for this confirmed review.")
            return None
        if not lines:
            st.caption("No inspectable source lines are available for explicit selection.")
            return None
        st.caption(
            f"Bounded source view: first {MAX_SELECTABLE_REFERENCE_LINES:,} eligible lines; "
            f"at most {MAX_REFERENCE_LINE_BYTES:,} UTF-8 bytes per line. "
            "Removed, skipped, truncated and ambiguous sources are unavailable."
        )
        st.text(f"Criterion {criterion_id} · revision {state.criteria_revision.number}")
        st.code(state.review.head_sha, language=None)
        sources = list(
            dict.fromkeys(_source_key(line.source_scope, line.file_path) for line in lines)
        )
        source = st.selectbox(
            "Reference source",
            sources,
            index=None,
            key="selected_reference_source",
            format_func=_source_label,
        )
        if source != st.session_state.get("selected_reference_previous_source"):
            st.session_state["selected_reference_line"] = None
            st.session_state["selected_reference_previous_source"] = source
        source_lines = [
            line for line in lines if _source_key(line.source_scope, line.file_path) == source
        ]
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
                f"{selected.evidence_type.value} · {selected.evidence_level.value} "
                "· static reference"
            )
            st.code(selected.excerpt)
        reviewer = st.text_input(
            "Reference reviewer (required)", key="selected_reference_reviewer", max_chars=200
        )
        rationale = st.text_area(
            "Why this reference matters", key="selected_reference_rationale", max_chars=2000
        )
        if blocked:
            st.caption(
                "Resolve other pending review inputs or local save conflicts before recording."
            )
        if st.button(
            "Save selected reference",
            key="save_selected_reference",
            disabled=blocked or selected is None or not reviewer.strip() or not rationale.strip(),
        ):
            try:
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
