"""Explicit whole-import withdrawal draft and inert recorded audit presentation."""

import streamlit as st

from scopeproof_core.reviews.junit_audit import (
    junit_import_status,
    junit_import_withdrawal_event,
    junit_withdrawal_fields,
)
from scopeproof_core.schemas.models import ReviewBundle, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

_KEYS = ("junit_withdrawal_target", "junit_withdrawal_reviewer", "junit_withdrawal_reason")


def junit_withdrawal_draft_pending() -> bool:
    return any(bool(st.session_state.get(key)) for key in _KEYS)


def clear_junit_withdrawal_draft() -> None:
    for key in _KEYS:
        st.session_state[key] = None if key == _KEYS[0] else ""


def prepare_junit_withdrawal_context(state: ReviewState | None, criterion_id: str | None) -> None:
    context = (
        (JsonReviewStore.state_fingerprint(state), criterion_id) if state is not None else None
    )
    if st.session_state.get("junit_withdrawal_context") != context:
        clear_junit_withdrawal_draft()
        st.session_state["junit_withdrawal_context"] = context


def render_junit_import_audit(bundle: ReviewBundle, import_id: str) -> None:
    st.caption("Import status")
    st.text(junit_import_status(bundle, import_id).title())
    event = junit_import_withdrawal_event(bundle, import_id)
    if event is not None:
        st.caption("Retained original; withdrawn from current imported context.")
        for label, value in junit_withdrawal_fields(event):
            st.caption(label)
            st.text(value)


def render_junit_withdrawal(state: ReviewState, *, disabled: bool) -> dict[str, str] | None:
    """Return explicit request values; parent commits them under the store mutation lock."""
    with st.expander("Withdraw a saved JUnit import", expanded=False, key="junit_withdrawal_panel"):
        st.caption(
            "Whole-import withdrawal retains the original results and every criterion mapping. "
            "It changes no gate or reviewer decision, frees no history slot, and does not permit "
            "reimporting the same artifact. Attribution is asserted, not authenticated."
        )
        active = state.bundle.active_junit_import_ids if state.bundle is not None else []
        target = st.selectbox(
            "Active JUnit import",
            options=active,
            index=None,
            key="junit_withdrawal_target",
            placeholder="Choose one whole import",
        )
        if target is not None:
            item = next(
                item for item in state.bundle.junit_evidence_imports if item.import_id == target
            )
            st.caption("This whole-import action affects every mapped criterion")
            st.text(", ".join(mapping.criterion_id for mapping in item.criterion_mappings))
        reviewer = st.text_input("Withdrawal reviewer", key="junit_withdrawal_reviewer")
        reason = st.text_area("Withdrawal reason", key="junit_withdrawal_reason")
        if disabled:
            st.info("Clear other drafts and reopen a current saved review before withdrawal.")
        clicked = st.button(
            "Withdraw selected JUnit import",
            key="withdraw_junit_import",
            disabled=disabled or target is None or not reviewer.strip() or not reason.strip(),
        )
        if clicked and not disabled and target is not None:
            context = st.session_state.get("junit_withdrawal_context")
            if context is None:
                return None
            return dict(
                import_id=target,
                reviewer=reviewer,
                reason=reason,
                expected_state_fingerprint=context[0],
            )
    return None
