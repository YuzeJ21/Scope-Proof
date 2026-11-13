"""Inert loaded diff inspection and target-bound scope-form drafts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from unicodedata import category
from uuid import uuid4

import streamlit as st

from scopeproof_core.gates.evaluator import unresolved_changed_file_paths
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.scope_file_preview import build_scope_file_preview
from scopeproof_core.schemas.models import (
    LineChangeType,
    PullRequestSnapshot,
    ReviewBundle,
    ReviewState,
)


@dataclass(frozen=True)
class ScopeFileSelection:
    """Session-only identity for a file decision and its independently paged preview."""

    path: str | None = None
    generation: int = 0
    preview_generation: int = 0
    event_id: str = ""

    def key(self, widget: str) -> str:
        return f"{widget}_{self.generation}"

    @property
    def page_key(self) -> str:
        return f"scope_preview_page_{self.preview_generation}"


def scope_file_selection() -> ScopeFileSelection:
    return st.session_state.get("scope_file_selection", ScopeFileSelection())


def discard_scope_decision_draft(expected: ScopeFileSelection | None = None) -> None:
    """Replace the form's widget identities, preserving the file and diff page."""
    selected = scope_file_selection()
    if expected is None or selected == expected:
        st.session_state["scope_file_selection"] = replace(
            selected, generation=selected.generation + 1, event_id=str(uuid4()),
        )


def reconcile_scope_file_selection(current: ReviewState | None) -> None:
    """Resolve an incoming widget change before using the file or draft on this rerun."""
    selected = scope_file_selection()
    if selected.path is not None and current is not None and current.bundle is not None and any(
        item.event_id == selected.event_id for item in current.bundle.file_scope_decisions
    ):
        # A rerun can interrupt a save after the new state has been assigned.
        discard_scope_decision_draft(selected)
        return
    key = selected.key("scope_file_path")
    requested = st.session_state.get(key, selected.path)
    if requested == selected.path:
        return
    if scope_draft_pending():
        st.session_state[key] = selected.path
        return
    _replace_scope_file_selection(requested)


def reset_scope_file_selection() -> None:
    _replace_scope_file_selection(None)


def _replace_scope_file_selection(path: str | None) -> None:
    generation = scope_file_selection().generation + 1
    st.session_state["scope_file_selection"] = ScopeFileSelection(
        path, generation, generation, str(uuid4()),
    )


def prepare_scope_draft_context(
    state: ReviewState | None, snapshot: PullRequestSnapshot | None,
) -> None:
    payload = (
        "" if state is None else state.review.model_dump_json()
        + state.criteria_revision.model_dump_json()
    ) + ("" if snapshot is None else snapshot.model_dump_json())
    context = sha256(payload.encode("utf-8")).hexdigest()
    if st.session_state.get("scope_draft_context") != context:
        reset_scope_file_selection()
        st.session_state["scope_draft_context"] = context


def scope_draft_pending() -> bool:
    """Read edits for this selection, excluding the shared reviewer field."""
    selected = scope_file_selection()
    if selected.path is None:
        return False
    disposition = st.session_state.get(selected.key("scope_disposition"))
    note = st.session_state.get(selected.key("scope_note"), "")
    criterion_id = (
        st.session_state.get(selected.key("scope_criterion_id"))
        if disposition == "within_confirmed_criteria" else None
    )
    return bool(disposition or note or criterion_id)


def _visible_content(content: str) -> str:
    # Preserve physical record boundaries without presenting separators as extra source lines.
    return "".join(
        (f"\\u{ord(character):04x}" if ord(character) <= 0xffff
         else f"\\U{ord(character):08x}")
        if character != "\t" and category(character) in {"Cc", "Cf", "Zl", "Zp"}
        else character
        for character in content
    )


def render_scope_overview(bundle: ReviewBundle) -> None:
    """Surface recorded file scope independently of the gate's reason precedence."""
    unresolved = unresolved_changed_file_paths(
        bundle.review, bundle.findings, bundle.evidence, bundle.file_scope_decisions,
    )
    if unresolved is None:
        st.text("Changed-file scope: Inventory unavailable for this analysis.")
    else:
        st.text(f"Unresolved inspected changed files: {len(unresolved)}")
        if not unresolved:
            return
        preview = sorted(unresolved)[:3]
        st.text("\n".join(
            _visible_content(path.replace("\\", "\\\\")).replace("\t", "\\t") for path in preview
        ))
        remaining = len(unresolved) - len(preview)
        if remaining:
            st.caption(f"{remaining} more in changed-file scope.")
    st.markdown("[Go to changed-file scope](#changed-file-scope)")


def render_scope_file_preview(
    state: ReviewState | None,
    snapshot: PullRequestSnapshot | None,
    selection: ScopeFileSelection,
    *,
    source_allowed: bool = True,
) -> None:
    if selection.path is None:
        return
    path = selection.path
    with st.container(key="scope_file_preview"):
        st.caption("Loaded changed-file diff")
        st.caption(
            "Static diff context, not a full file, runtime verification or a scope decision. "
            "Only ingested diff records are shown; gaps may exist. "
            "Control/separator characters are shown as escapes."
        )
        try:
            if state is None:
                raise ValueError("no active saved review")
            state = validated_review_state(state)
            inventory = state.review.changed_file_inventory
            recorded_file = next(
                (item for item in inventory.files if item.path == path), None,
            ) if inventory is not None else None
            if recorded_file is None:
                raise ValueError("no recorded selected-file metadata")
        except ValueError:
            st.info("Recorded file metadata and loaded source are unavailable for this analysis.")
            return
        st.text(f"{state.review.repository} · PR #{state.review.pr_number}")
        st.code(recorded_file.path, language=None, wrap_lines=True)
        st.text(f"Recorded change status: {recorded_file.status}")
        if recorded_file.previous_path is not None:
            st.text("Recorded previous path")
            st.code(recorded_file.previous_path, language=None, wrap_lines=True)
        st.caption("Recorded PR base identity; the diff's old-side commit was not retained.")
        st.code(state.review.base_sha, language=None, wrap_lines=True)
        st.caption("Recorded head (added/context-line coordinates)")
        st.code(state.review.head_sha, language=None, wrap_lines=True)
        if snapshot is None or not source_allowed:
            st.info(
                "Loaded source is unavailable. Use Load matching reviewed source "
                "to inspect this saved analysis."
            )
            return
        try:
            preview = build_scope_file_preview(
                state, snapshot, path, page_index=st.session_state.get(selection.page_key, 0),
            )
        except ValueError:
            st.info(
                "Loaded source is unavailable for this active analysis. "
                "Load matching reviewed source or explicitly re-review; no diff was inferred."
            )
            return
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
            key=selection.page_key,
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
                f"{prefix} {'old diff' if removed else 'head'} line {coordinate} | {content}"
            )
        st.code("\n".join(rendered), language=None, wrap_lines=True)
