"""Explicit multi-criterion JUnit draft controls; saved imports remain immutable."""

from __future__ import annotations

import streamlit as st

from scopeproof_core.importers.junit import JUnitMappingSelection, ParsedJUnitArtifact
from scopeproof_core.importers.junit_draft import (
    JUnitMappingDraft,
    build_drafted_junit_import,
    extend_junit_mapping_draft,
    new_junit_mapping_draft,
    remove_junit_mapping_criterion,
)
from scopeproof_core.schemas.models import JUnitEvidenceImport, ReviewState


def _reset_controls() -> None:
    st.session_state["junit_mapping_target"] = None
    st.session_state["junit_mapping_scopes"] = []
    st.session_state["junit_mapping_remove_criterion"] = None


def clear_junit_mapping_draft() -> None:
    st.session_state["junit_mapping_draft"] = None
    st.session_state["junit_mapping_controls_reset_pending"] = False
    _reset_controls()


def render_junit_mapping_draft(
    state: ReviewState | None,
    artifact_bytes: bytes | None,
    parsed: ParsedJUnitArtifact | None,
    *,
    scope_ids: list[str],
    scope_labels: dict[str, str],
    importer: str,
    limitations: list[str],
) -> JUnitEvidenceImport | None:
    if st.session_state.pop("junit_mapping_controls_reset_pending", False):
        _reset_controls()
    draft = st.session_state.get("junit_mapping_draft")
    fresh = None
    if state is not None and artifact_bytes is not None and parsed is not None:
        try:
            fresh = new_junit_mapping_draft(state, artifact_bytes)
            if fresh.artifact_sha256 != parsed.artifact_sha256:
                raise ValueError("parsed artifact changed")
            if draft is not None:
                draft = JUnitMappingDraft.model_validate(draft.model_dump(mode="python"))
        except (AttributeError, TypeError, ValueError):
            fresh = None
    if fresh is None:
        clear_junit_mapping_draft()
        draft = None
    elif draft is None or (
        draft.state_fingerprint, draft.artifact_sha256
    ) != (fresh.state_fingerprint, fresh.artifact_sha256):
        if draft is not None:
            st.info("JUnit artifact or review changed. Previous mapping choices were cleared.")
        clear_junit_mapping_draft()
        draft = fresh
        st.session_state["junit_mapping_draft"] = draft

    notice = st.session_state.pop("junit_mapping_notice", None)
    if notice is not None:
        st.info(notice)
    criteria = (
        [] if state is None else [item.criterion_id for item in state.criteria_revision.criteria]
    )
    target = st.selectbox(
        "JUnit mapping target criterion", options=criteria, index=None,
        placeholder="Explicitly choose a confirmed criterion", key="junit_mapping_target",
        disabled=draft is None,
    )
    scopes = st.multiselect(
        "Map JUnit scopes to the selected criterion", options=scope_ids,
        format_func=lambda scope: scope_labels.get(scope, scope), key="junit_mapping_scopes",
        disabled=draft is None,
    )
    st.caption(
        "Choose a mapping target here, add its scopes to the draft, then repeat for another "
        "criterion before one import. Test names never establish this relationship. "
        "Changing the main inspected criterion clears unsaved criterion-detail inputs."
    )
    if st.button(
        "Add selected scopes to mapping draft", key="stage_junit_mapping",
        disabled=draft is None or target is None or not scopes or not importer.strip(),
    ):
        try:
            assert state is not None and artifact_bytes is not None and draft is not None
            staged = extend_junit_mapping_draft(
                state, artifact_bytes, draft,
                [JUnitMappingSelection(scope_id=scope, criterion_id=target) for scope in scopes],
                importer=importer,
            )
        except (TypeError, ValueError):
            st.error(
                "Mapping could not be staged. Check the target, selected scopes and existing "
                "artifact imports. One test case cannot belong to multiple criteria. "
                "Previous staged mappings were preserved."
            )
        else:
            st.session_state["junit_mapping_draft"] = staged
            st.session_state["junit_mapping_controls_reset_pending"] = True
            st.session_state["junit_mapping_notice"] = (
                "Mapping staged only; no import was recorded."
            )
            st.rerun()

    candidate = None
    if draft is not None and draft.selections:
        try:
            assert state is not None and artifact_bytes is not None
            candidate = build_drafted_junit_import(
                state, artifact_bytes, draft, importer=importer, limitations=limitations,
            )
        except (TypeError, ValueError):
            st.info(
                "Staged mappings are not importable. Check the importer, limitations and artifact."
            )
    with st.container(key="junit_mapping_preview"):
        st.caption("Staged JUnit mappings (not imported)")
        if draft is None or not draft.selections:
            st.caption("No mappings staged. Nothing will be inferred or imported.")
        elif candidate is not None:
            for mapping in candidate.criterion_mappings:
                st.text(
                    f"Criterion: {mapping.criterion_id} · "
                    f"{len(mapping.test_case_ids)} mapped test case(s)"
                )
                st.code("\n".join(mapping.test_case_ids), language=None, wrap_lines=True)
        else:
            for selection in draft.selections:
                st.text(f"Criterion: {selection.criterion_id}")
                st.code(selection.scope_id, language=None, wrap_lines=True)
    staged_criteria = sorted({item.criterion_id for item in draft.selections}) if draft else []
    removal = st.selectbox(
        "Staged criterion to remove", options=staged_criteria, index=None,
        key="junit_mapping_remove_criterion", disabled=not staged_criteria,
    )
    if st.button(
        "Remove criterion mapping from draft", key="remove_junit_mapping", disabled=removal is None,
    ):
        try:
            assert state is not None and artifact_bytes is not None and draft is not None
            revised = remove_junit_mapping_criterion(state, artifact_bytes, draft, removal)
        except (TypeError, ValueError):
            st.error("Staged mapping changed. Refresh and explicitly choose the mappings again.")
        else:
            st.session_state["junit_mapping_draft"] = revised
            st.session_state["junit_mapping_controls_reset_pending"] = True
            st.session_state["junit_mapping_notice"] = (
                "Criterion removed from draft; saved imports unchanged."
            )
            st.rerun()
    if st.button(
        "Clear staged JUnit mappings", key="clear_junit_mappings",
        disabled=draft is None or not (draft.selections or target is not None or scopes),
    ):
        assert fresh is not None
        st.session_state["junit_mapping_draft"] = fresh
        st.session_state["junit_mapping_controls_reset_pending"] = True
        st.session_state["junit_mapping_notice"] = "Draft cleared; saved imports unchanged."
        st.rerun()
    if target is not None or scopes:
        st.caption("Add or clear the current target/scopes before saving the staged import.")
        return None
    return candidate
