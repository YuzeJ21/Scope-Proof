"""Source-free whole-import mapping drafts and explicit correction requests."""

import json

import streamlit as st

from scopeproof_core.reviews.junit_audit import effective_junit_mappings
from scopeproof_core.reviews.junit_correction import (
    new_junit_correction_draft,
    remove_junit_correction_group,
    replace_junit_correction_group,
)
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

_DEFAULTS = {
    "junit_correction_target": None, "junit_correction_draft": None,
    "junit_correction_criterion": None, "junit_correction_cases": [],
    "junit_correction_remove": None, "junit_correction_reviewer": "",
    "junit_correction_reason": "", "junit_correction_confirm": False,
    "junit_correction_dirty": False, "junit_correction_error": None,
}


def clear_junit_correction_draft() -> None:
    for key, value in _DEFAULTS.items():
        st.session_state[key] = [] if isinstance(value, list) else value


def prepare_junit_correction_context(state: ReviewState | None, criterion_id: str | None) -> None:
    context = (
        (JsonReviewStore.state_fingerprint(state), criterion_id) if state is not None else None
    )
    if st.session_state.get("junit_correction_context") != context:
        clear_junit_correction_draft()
        st.session_state["junit_correction_context"] = context


def junit_correction_draft_pending() -> bool:
    return any(bool(st.session_state.get(key)) for key in (
        "junit_correction_dirty", "junit_correction_criterion", "junit_correction_cases",
        "junit_correction_remove", "junit_correction_reviewer", "junit_correction_reason",
        "junit_correction_confirm",
    ))


def _invalidate_confirmation() -> None:
    st.session_state["junit_correction_confirm"] = False


def _select_target(state: ReviewState) -> None:
    target = st.session_state.get("junit_correction_target")
    clear_junit_correction_draft()
    st.session_state["junit_correction_target"] = target
    if target is not None:
        try:
            st.session_state["junit_correction_draft"] = new_junit_correction_draft(state, target)
        except ValueError:
            st.session_state["junit_correction_error"] = "Reopen a current active import to edit."


def _stage_group(state: ReviewState, remove: bool) -> None:
    _invalidate_confirmation()
    draft = st.session_state.get("junit_correction_draft")
    if draft is None:
        return
    try:
        if remove:
            updated = remove_junit_correction_group(
                state, draft, st.session_state.get("junit_correction_remove"),
            )
        else:
            updated = replace_junit_correction_group(
                state, draft, st.session_state.get("junit_correction_criterion"),
                sorted(st.session_state.get("junit_correction_cases", [])),
            )
    except ValueError:
        st.session_state["junit_correction_error"] = (
            "Mapping could not be staged. Choose retained cases and confirmed criteria; "
            "remove an existing group before assigning its cases elsewhere."
        )
        return
    st.session_state["junit_correction_draft"] = updated
    st.session_state["junit_correction_dirty"] = list(updated.criterion_mappings) != (
        effective_junit_mappings(state.bundle, updated.import_id)
    )
    st.session_state["junit_correction_criterion"] = None
    st.session_state["junit_correction_cases"] = []
    st.session_state["junit_correction_remove"] = None
    st.session_state["junit_correction_error"] = None


def _preview(label, mappings) -> None:
    st.caption(label)
    st.code(json.dumps([x.model_dump(mode="json") for x in mappings], indent=2),
            language="json", wrap_lines=True)


def render_junit_correction(state: ReviewState, *, disabled: bool) -> dict | None:
    with st.expander("Correct saved JUnit mappings", key="junit_correction_panel"):
        st.caption(
            "Correct the whole import's organizational mappings while retaining original results "
            "and mapping history. This changes no gate or reviewer decision. "
            "Attribution is asserted, not authenticated."
        )
        active = state.bundle.active_junit_import_ids if state.bundle is not None else []
        target = st.selectbox(
            "JUnit import to correct", active, index=None, key="junit_correction_target",
            on_change=_select_target, args=(state,), placeholder="Choose one active saved import",
        )
        draft = st.session_state.get("junit_correction_draft")
        if target is not None and draft is not None:
            item = next(x for x in state.bundle.junit_evidence_imports if x.import_id == target)
            _preview("Original mappings (retained)", item.criterion_mappings)
            _preview("Current effective mappings", effective_junit_mappings(state.bundle, target))
            _preview("Staged corrected mappings", draft.criterion_mappings)
            st.caption("Affected criteria across current and staged mappings")
            st.text(", ".join(sorted({x.criterion_id for x in (
                *effective_junit_mappings(state.bundle, target), *draft.criterion_mappings,
            )})))
        groups = [x.criterion_id for x in draft.criterion_mappings] if draft else []
        remove = st.selectbox(
            "Remove mapped criterion", groups, index=None, key="junit_correction_remove",
            on_change=_invalidate_confirmation,
        )
        st.button("Remove criterion mapping", key="remove_junit_correction_group",
                  disabled=disabled or draft is None or remove is None,
                  on_click=_stage_group, args=(state, True))
        criteria = (
            [x.criterion_id for x in state.bundle.criteria] if state.bundle is not None else []
        )
        criterion = st.selectbox(
            "Correction criterion", criteria, index=None, key="junit_correction_criterion",
            on_change=_invalidate_confirmation,
        )
        cases = {x.test_case_id: x for x in item.test_cases} if target and draft else {}
        selected_cases = st.multiselect(
            "Correction test cases", list(cases), key="junit_correction_cases",
            format_func=lambda case_id: f"{case_id} · {cases[case_id].test_name}",
            on_change=_invalidate_confirmation,
        )
        st.button("Stage criterion mapping", key="stage_junit_correction_group",
                  disabled=disabled or draft is None or criterion is None or not selected_cases,
                  on_click=_stage_group, args=(state, False))
        reviewer = st.text_input("Correction reviewer", key="junit_correction_reviewer")
        reason = st.text_area("Correction reason", key="junit_correction_reason")
        confirmed = st.checkbox(
            "I confirm these mappings for the whole import", key="junit_correction_confirm",
        )
        error = st.session_state.get("junit_correction_error")
        if error:
            st.error(error)
        if disabled:
            st.info("Clear other drafts and reopen a current saved review before correction.")
        unstaged = bool(criterion is not None or selected_cases or remove is not None)
        ready = bool(draft and draft.criterion_mappings and st.session_state.get(
            "junit_correction_dirty",
        ) and not unstaged and confirmed and reviewer.strip() and reason.strip())
        if st.button("Save corrected JUnit mappings", key="save_junit_correction",
                     disabled=disabled or not ready) and not disabled and ready:
            return dict(
                import_id=target, criterion_mappings=list(draft.criterion_mappings),
                reviewer=reviewer, reason=reason,
                expected_state_fingerprint=draft.state_fingerprint,
                confirm_whole_import=True,
            )
    return None
