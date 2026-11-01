"""Inert loaded diff inspection and target-bound scope-form drafts."""

from __future__ import annotations

from hashlib import sha256

import streamlit as st

from scopeproof_core.reviews.scope_file_preview import build_scope_file_preview
from scopeproof_core.schemas.models import LineChangeType, PullRequestSnapshot, ReviewState


def scope_file_changed() -> None:
    """A note and disposition belong only to the file the operator selected."""
    st.session_state["scope_disposition"] = None
    st.session_state["scope_criterion_id"] = None
    st.session_state["scope_note"] = ""
    st.session_state["scope_preview_page"] = 0


def prepare_scope_draft_context(
    state: ReviewState | None, snapshot: PullRequestSnapshot | None,
) -> None:
    payload = (
        "" if state is None else state.review.model_dump_json()
        + state.criteria_revision.model_dump_json()
    ) + ("" if snapshot is None else snapshot.model_dump_json())
    context = sha256(payload.encode("utf-8")).hexdigest()
    if st.session_state.get("scope_draft_context") != context:
        st.session_state["scope_file_path"] = None
        scope_file_changed()
        st.session_state["scope_draft_context"] = context


def _visible_content(content: str) -> str:
    # Preserve physical record boundaries without presenting separators as extra source lines.
    return "".join(
        f"\\u{ord(character):04x}" if (
            (ord(character) < 32 and character != "\t")
            or character in "\x7f\x85\u2028\u2029"
        ) else character
        for character in content
    )


def render_scope_file_preview(
    state: ReviewState | None,
    snapshot: PullRequestSnapshot | None,
    path: str | None,
    *,
    source_allowed: bool = True,
) -> None:
    if path is None:
        return
    with st.container(key="scope_file_preview"):
        st.caption("Loaded changed-file diff")
        st.caption(
            "Static diff context, not a full file, runtime verification or a scope decision. "
            "Only ingested diff records are shown; gaps may exist. "
            "Control/separator characters are shown as escapes."
        )
        if state is None or snapshot is None or not source_allowed:
            st.info(
                "Loaded source is unavailable. Use Load matching reviewed source "
                "to inspect this saved analysis."
            )
            return
        try:
            preview = build_scope_file_preview(
                state, snapshot, path, page_index=st.session_state.get("scope_preview_page", 0),
            )
        except ValueError:
            st.info(
                "Loaded source is unavailable for this active analysis. "
                "Load matching reviewed source or explicitly re-review; no diff was inferred."
            )
            return
        st.text(f"{preview.repository} · PR #{preview.pr_number}")
        st.code(preview.path, language=None, wrap_lines=True)
        st.text(f"Recorded change status: {preview.status}")
        if preview.previous_path is not None:
            st.text("Recorded previous path")
            st.code(preview.previous_path, language=None, wrap_lines=True)
        st.caption("Base (removed-line coordinates)")
        st.code(preview.base_sha, language=None, wrap_lines=True)
        st.caption("Head (added/context-line coordinates)")
        st.code(preview.head_sha, language=None, wrap_lines=True)
        if preview.availability != "available":
            reasons = {
                "skipped": "The file was skipped during ingestion; no content is shown.",
                "truncated": "The ingested diff is truncated; no content is shown.",
                "unsupported_status": "This recorded change status has no supported preview.",
                "ambiguous_coordinates": "The loaded diff has ambiguous records or coordinates.",
                "no_lines": "No inspectable diff records were ingested for this file.",
            }
            st.info(reasons[preview.availability])
            return
        st.selectbox(
            "Changed-file diff page", options=list(range(preview.page_count)),
            format_func=lambda index: f"Page {index + 1} of {preview.page_count}",
            key="scope_preview_page",
        )
        start = preview.page_index * 100
        st.caption(
            f"Showing diff records {start + 1}-{start + len(preview.lines)} "
            f"of {preview.total_line_count}; at most 100 records per page."
        )
        rendered = []
        for line in preview.lines:
            removed = line.change_type is LineChangeType.REMOVED
            prefix = "-" if removed else "+" if line.change_type is LineChangeType.ADDED else " "
            coordinate = "unknown" if line.line_number is None else str(line.line_number)
            content = (
                "[Content omitted: exceeds 4,096 UTF-8 bytes]" if line.content is None
                else _visible_content(line.content)
            )
            rendered.append(
                f"{prefix} {'base' if removed else 'head'} line {coordinate} | {content}"
            )
        st.code("\n".join(rendered), language=None, wrap_lines=True)
