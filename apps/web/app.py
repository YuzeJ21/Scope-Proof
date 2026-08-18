"""ScopeProof's five-step local Streamlit review workbench."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from uuid import uuid4

import streamlit as st

from apps.web.deferred_exports import deferred_review_export
from apps.web.view_models import default_criterion_detail_id, group_candidate_evidence
from scopeproof_core.alpha.models import (
    AlphaFrictionStage,
    AlphaOutcome,
    AlphaQualification,
    AlphaQualificationInput,
    ParticipantRole,
)
from scopeproof_core.alpha.service import ensure_alpha_case, record_alpha_outcome
from scopeproof_core.alpha.storage import (
    JsonAlphaCaseStore,
    default_alpha_case_directory,
)
from scopeproof_core.criteria.confirmation import (
    build_criteria_source_provenance,
    canonical_criteria_sha256,
    source_text_sha256,
)
from scopeproof_core.criteria.service import (
    add_criterion,
    parse_criteria,
    remove_criterion,
    reorder_criteria,
    split_criterion,
    validate_criteria,
)
from scopeproof_core.demo import load_demo_labels, load_demo_snapshot
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.guidance import decision_guidance, gate_guidance
from scopeproof_core.github.client import (
    GitHubClient,
    GitHubIngestionError,
    InvalidPullRequestUrl,
    parse_pr_url,
)
from scopeproof_core.presentation import (
    EvidenceStatus,
    criterion_coverage_rows,
    evidence_status_text,
    review_status_label,
)
from scopeproof_core.reporting.exporters import (
    export_comparison_json,
    export_comparison_markdown,
    export_csv,
    export_json,
    export_markdown,
)
from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
from scopeproof_core.reviews.comparison import (
    EvidenceReference,
    ReviewComparison,
    compare_reviews,
)
from scopeproof_core.reviews.lifecycle import (
    ResolutionEventStatus,
    acceptance_requires_comment,
    append_external_verification,
    append_resolution,
    attach_analysis,
    can_record_final_acceptance,
    confirm_criteria,
    new_review_state,
    resolution_event_statuses,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
    RULESET_VERSION,
    CheckState,
    Criterion,
    EvidenceLevel,
    EvidenceSourceScope,
    HumanDecision,
    IngestionState,
    Priority,
    PullRequestSnapshot,
    ResolutionEvent,
    Review,
    ReviewBundle,
    ReviewInputOrigin,
    ReviewState,
    RuntimeEvidence,
    require_verified_public_origin,
)
from scopeproof_core.storage.json_store import (
    JsonReviewStore,
    StaleReviewState,
    UnsafeReviewStore,
    UnsupportedRecordVersion,
    default_local_review_directory,
)
from scopeproof_core.verification.service import build_findings

st.set_page_config(page_title="ScopeProof", page_icon="🔎", layout="wide")
st.markdown(
    """
    <style>
    :where(
        button,
        a,
        input,
        textarea,
        select,
        [role="button"],
        [role="checkbox"],
        [role="combobox"],
        [tabindex]
    ):focus-visible {
        outline: 3px solid #ffbf47 !important;
        outline-offset: 3px !important;
        box-shadow: 0 0 0 2px #0e1117 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    :root {
        --scopeproof-background: #0d0f12;
        --scopeproof-surface: #171a1f;
        --scopeproof-text: #f7f7f2;
        --scopeproof-lime: #d8ff63;
        --scopeproof-cyan: #8cecff;
        --scopeproof-warning: #ffad66;
    }
    [data-testid="stAppViewContainer"] {
        background: var(--scopeproof-background);
        color: var(--scopeproof-text);
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 76rem;
        padding-block: 2rem 4rem;
    }
    [data-testid="stMainBlockContainer"] > div {
        gap: 1.25rem;
    }
    h1, h2, h3 {
        color: var(--scopeproof-text);
        letter-spacing: -0.02em;
    }
    h1 {
        border-bottom: 1px solid color-mix(in srgb, var(--scopeproof-cyan) 35%, transparent);
        padding-bottom: 0.35rem;
    }
    a {
        color: var(--scopeproof-cyan);
    }
    button {
        border-radius: 0.6rem;
    }
    [data-testid="stButton"] > button[kind="primary"] {
        background: var(--scopeproof-lime);
        border-color: var(--scopeproof-lime);
        color: #0d0f12;
    }
    [data-testid="stExpander"] details,
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--scopeproof-surface);
        border-color: color-mix(in srgb, var(--scopeproof-cyan) 28%, transparent);
        border-radius: 0.75rem;
    }
    [data-testid="stAlert"] {
        border-left: 3px solid var(--scopeproof-warning);
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation: none !important;
            scroll-behavior: auto !important;
            transition: none !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

_STATE_DEFAULTS = {
    "snapshot": None,
    "criteria": [],
    "criteria_confirmed": False,
    "bundle": None,
    "source_text": "",
    "requirements_input": "",
    "resolutions": [],
    "review_state": None,
    "reopened_review_id": None,
    "source_reload_notice": None,
    "saved_review_fingerprint": None,
    "failed_review_save_fingerprint": None,
    "review_save_conflict": False,
    "deleted_review_save_fingerprint": None,
    "review_save_notice": None,
    "replace_unsaved_review_confirmed": False,
    "replace_unsaved_review_reset_pending": False,
    "review_reopen_notice": None,
    "delete_saved_review_confirmed": False,
    "delete_saved_review_reset_pending": False,
    "saved_review_delete_notice": None,
    "source_load_notice": None,
    "alpha_case_id": None,
    "alpha_case_notice": None,
    "alpha_outcome_notice": None,
    "candidate_files": [],
    "comparison_base_bundle": None,
    "criteria_source_provenance": None,
    "criteria_source_mode": "standard",
    "criteria_source_draft": None,
    "criteria_source_widget_sync_pending": None,
    "source_widget_sync_pending": None,
}
for state_key, default in _STATE_DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default

_criteria_source_widget_sync = st.session_state["criteria_source_widget_sync_pending"]
if _criteria_source_widget_sync is not None:
    for _widget_key, _widget_value in _criteria_source_widget_sync.items():
        st.session_state[_widget_key] = _widget_value
    st.session_state["criteria_source_widget_sync_pending"] = None

_source_widget_sync = st.session_state["source_widget_sync_pending"]
if _source_widget_sync is not None:
    for _widget_key, _widget_value in _source_widget_sync.items():
        st.session_state[_widget_key] = _widget_value
    st.session_state["source_widget_sync_pending"] = None

_active_source_provenance = st.session_state["criteria_source_provenance"]
_criteria_source_draft = st.session_state["criteria_source_draft"]
if _criteria_source_draft is not None:
    for _draft_key, _draft_value in _criteria_source_draft.items():
        if _draft_key not in st.session_state:
            st.session_state[_draft_key] = _draft_value
elif _active_source_provenance is not None:
    if "criteria_source_reference" not in st.session_state:
        st.session_state["criteria_source_reference"] = (
            _active_source_provenance.source_uri
        )
    if "criteria_source_revision" not in st.session_state:
        st.session_state["criteria_source_revision"] = (
            _active_source_provenance.source_revision or ""
        )
    if "criteria_source_confirmer" not in st.session_state:
        st.session_state["criteria_source_confirmer"] = (
            _active_source_provenance.confirmed_by
        )


def _reset_analysis() -> None:
    st.session_state["criteria_confirmed"] = False
    st.session_state["bundle"] = None
    st.session_state["resolutions"] = []
    st.session_state["review_state"] = None
    st.session_state["reopened_review_id"] = None
    st.session_state["saved_review_fingerprint"] = None
    st.session_state["failed_review_save_fingerprint"] = None
    st.session_state["review_save_conflict"] = False
    st.session_state["deleted_review_save_fingerprint"] = None
    st.session_state["review_save_notice"] = None
    st.session_state["criteria_source_provenance"] = None
    st.session_state["criteria_source_widget_sync_pending"] = None
    st.session_state["source_widget_sync_pending"] = None
    st.session_state["replace_unsaved_review_reset_pending"] = True


def _remember_criteria_source_draft() -> None:
    """Preserve raw source fields across reruns that occur before their widgets render."""

    if st.session_state.get("alpha_feedback_mode", False):
        source_reference = str(
            st.session_state.get("requirements_source_url", "")
        )
    elif st.session_state.get("criteria_source_mode") == "demo":
        source_reference = CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI
    else:
        source_reference = str(
            st.session_state.get("criteria_source_reference", "")
        )
    st.session_state["criteria_source_draft"] = {
        "criteria_source_reference": source_reference,
        "criteria_source_revision": str(
            st.session_state.get("criteria_source_revision", "")
        ),
        "criteria_source_confirmer": str(
            st.session_state.get("criteria_source_confirmer", "")
        ),
    }


def _apply_criteria_update(
    operation: Callable[[], list[Criterion]],
    success_message: str,
    *,
    consumed_input_keys: tuple[str, ...] = (),
) -> None:
    try:
        updated_criteria = operation()
    except ValueError:
        st.error(
            "Criteria could not be updated. The current review remains unchanged. "
            "Verify the edit and try again."
        )
    else:
        st.session_state["criteria"] = updated_criteria
        if consumed_input_keys:
            st.session_state["criteria_authoring_reset_keys"] = consumed_input_keys
        _reset_analysis()
        st.success(success_message)
        st.rerun()


def _review_state_fingerprint(state: ReviewState) -> str:
    """Return a deterministic session-only identity for a validated review state."""
    return JsonReviewStore.state_fingerprint(state)


def _review_matches_local_save(state: ReviewState) -> bool:
    saved_fingerprint = st.session_state["saved_review_fingerprint"]
    return bool(saved_fingerprint and saved_fingerprint == _review_state_fingerprint(state))


def _persist_review_state(state: ReviewState, store: JsonReviewStore) -> bool:
    fingerprint = _review_state_fingerprint(state)
    try:
        store.save(
            state,
            expected_fingerprint=st.session_state["saved_review_fingerprint"],
        )
    except StaleReviewState:
        st.session_state["failed_review_save_fingerprint"] = fingerprint
        st.session_state["review_save_conflict"] = True
        return False
    except (OSError, ValueError):
        st.session_state["failed_review_save_fingerprint"] = fingerprint
        st.session_state["review_save_conflict"] = False
        return False
    st.session_state["saved_review_fingerprint"] = fingerprint
    st.session_state["failed_review_save_fingerprint"] = None
    st.session_state["review_save_conflict"] = False
    st.session_state["deleted_review_save_fingerprint"] = None
    return True


def _autosave_review_if_eligible(
    *,
    state: ReviewState | None,
    store: JsonReviewStore,
    store_available: bool,
    has_pending_review_input: bool,
) -> bool:
    if state is None or not store_available or has_pending_review_input:
        return False
    fingerprint = _review_state_fingerprint(state)
    suppressed = {
        st.session_state["saved_review_fingerprint"],
        st.session_state["failed_review_save_fingerprint"],
        st.session_state["deleted_review_save_fingerprint"],
    }
    if fingerprint in suppressed:
        return False
    if not _persist_review_state(state, store):
        return False
    st.session_state["review_save_notice"] = (
        f"Review saved automatically. ID: {state.review.review_id}."
    )
    return True


def _refresh_clean_review_from_local_store(
    state: ReviewState | None,
    *,
    store: JsonReviewStore,
    store_available: bool,
    has_pending_review_input: bool,
) -> ReviewState | None:
    """Refresh a clean open review before rendering or exporting persisted truth."""

    if state is None:
        return state
    expected_fingerprint = st.session_state["saved_review_fingerprint"]
    current_fingerprint = _review_state_fingerprint(state)
    if not store_available:
        if expected_fingerprint:
            st.session_state["saved_review_fingerprint"] = None
            st.session_state["failed_review_save_fingerprint"] = current_fingerprint
            st.session_state["review_save_conflict"] = True
        return state
    if not expected_fingerprint or current_fingerprint != expected_fingerprint:
        return state
    try:
        with store.locked_load(state.review.review_id) as persisted:
            persisted_fingerprint = _review_state_fingerprint(persisted)
            if persisted_fingerprint == expected_fingerprint:
                return state
            if has_pending_review_input:
                st.session_state["failed_review_save_fingerprint"] = current_fingerprint
                st.session_state["review_save_conflict"] = True
                return state
            _hydrate_reopened_review(persisted)
            st.session_state["review_save_notice"] = (
                "Review refreshed from local storage after an external update."
            )
            return persisted
    except FileNotFoundError:
        st.session_state["saved_review_fingerprint"] = None
        st.session_state["deleted_review_save_fingerprint"] = current_fingerprint
        st.session_state["review_save_conflict"] = False
        return state
    except (OSError, ValueError):
        st.session_state["saved_review_fingerprint"] = None
        st.session_state["failed_review_save_fingerprint"] = current_fingerprint
        st.session_state["review_save_conflict"] = True
        return state


@contextmanager
def _locked_review_status_snapshot(
    state: ReviewState | None,
    *,
    store: JsonReviewStore,
    store_available: bool,
    has_pending_review_input: bool,
) -> Iterator[ReviewState | None]:
    """Hold persisted review truth stable through Summary status rendering."""

    if state is None or not store_available:
        yield _refresh_clean_review_from_local_store(
            state,
            store=store,
            store_available=store_available,
            has_pending_review_input=has_pending_review_input,
        )
        return
    expected_fingerprint = st.session_state["saved_review_fingerprint"]
    current_fingerprint = _review_state_fingerprint(state)
    if not expected_fingerprint or current_fingerprint != expected_fingerprint:
        yield state
        return
    lock_stack = ExitStack()
    try:
        persisted = lock_stack.enter_context(
            store.locked_load(state.review.review_id)
        )
    except FileNotFoundError:
        lock_stack.close()
        st.session_state["saved_review_fingerprint"] = None
        st.session_state["deleted_review_save_fingerprint"] = current_fingerprint
        st.session_state["review_save_conflict"] = False
        yield state
        return
    except (OSError, ValueError):
        lock_stack.close()
        st.session_state["saved_review_fingerprint"] = None
        st.session_state["failed_review_save_fingerprint"] = current_fingerprint
        st.session_state["review_save_conflict"] = True
        yield state
        return
    try:
        persisted_fingerprint = _review_state_fingerprint(persisted)
        if persisted_fingerprint == expected_fingerprint:
            refreshed = state
        elif has_pending_review_input:
            st.session_state["failed_review_save_fingerprint"] = current_fingerprint
            st.session_state["review_save_conflict"] = True
            refreshed = state
        else:
            _hydrate_reopened_review(persisted)
            st.session_state["review_save_notice"] = (
                "Review refreshed from local storage after an external update."
            )
            refreshed = persisted
        yield refreshed
    finally:
        lock_stack.close()


def _mark_open_review_deleted(review_id: str) -> bool:
    current: ReviewState | None = st.session_state["review_state"]
    if current is None or current.review.review_id != review_id:
        return False
    current_fingerprint = _review_state_fingerprint(current)
    st.session_state["saved_review_fingerprint"] = None
    st.session_state["deleted_review_save_fingerprint"] = current_fingerprint
    st.session_state["review_save_conflict"] = False
    if st.session_state["failed_review_save_fingerprint"] == current_fingerprint:
        st.session_state["failed_review_save_fingerprint"] = None
    return True


def _render_local_review_storage(
    state: ReviewState,
    *,
    store: JsonReviewStore,
    store_available: bool,
    has_pending_review_input: bool,
    pending_messages: list[str],
) -> None:
    current_fingerprint = _review_state_fingerprint(state)
    review_matches_local_save = bool(
        _review_matches_local_save(state) and not has_pending_review_input
    )
    save_failed = (
        st.session_state["failed_review_save_fingerprint"] == current_fingerprint
    )
    save_conflict = bool(st.session_state["review_save_conflict"] and save_failed)
    save_deleted = (
        st.session_state["deleted_review_save_fingerprint"] == current_fingerprint
    )
    with st.expander("Local review storage", expanded=save_failed):
        st.caption(f"Storage directory: `{default_local_review_directory()}`")
        st.caption("Current review ID")
        st.code(state.review.review_id, language=None)
        for message in pending_messages:
            st.caption(message)
        if not store_available:
            export_availability = (
                "exports remain unavailable until pending review inputs are confirmed, "
                "submitted, discarded, or cleared."
                if has_pending_review_input
                else "exports remain available."
            )
            st.warning(
                "Local saving is unavailable. The current review remains open as unsaved work, "
                f"and {export_availability} Verify that the ScopeProof review directory is a "
                "regular local directory; ScopeProof will recheck it on the next interaction."
            )
        elif review_matches_local_save:
            st.caption("Saved locally — current review matches local storage.")
        elif save_conflict:
            st.warning(
                "The saved review changed outside this workbench. Reopen it before saving "
                "again so newer lifecycle events are not overwritten. This open review "
                "remains available as unsaved work."
            )
        elif save_failed:
            st.error(
                "The review could not be saved locally. The current review remains open as "
                "unsaved work. Verify the local review directory and review integrity, then "
                "try again."
            )
        elif save_deleted:
            st.caption("Deleted locally — use Save now to recreate this review.")
        save_label = "Retry local save" if save_failed else "Save now"
        save_clicked = st.button(
            save_label,
            key="save_review",
            disabled=(
                review_matches_local_save
                or has_pending_review_input
                or not store_available
                or save_conflict
            ),
        )
        if save_clicked:
            if _persist_review_state(state, store):
                st.session_state["review_save_notice"] = (
                    f"Review saved locally. ID: {state.review.review_id}."
                )
                st.rerun()
            else:
                if st.session_state["review_save_conflict"]:
                    st.warning(
                        "The saved review changed outside this workbench. Reopen it before "
                        "saving again so newer lifecycle events are not overwritten. This "
                        "open review remains available as unsaved work."
                    )
                else:
                    st.error(
                        "The review could not be saved locally. The current review remains "
                        "open as unsaved work. Verify the local review directory and review "
                        "integrity, then try again."
                    )


def _record_reopened_source_reload(snapshot: PullRequestSnapshot) -> None:
    """Compare a reopened review with the same PR before invalidating its analysis."""
    state: ReviewState | None = st.session_state["review_state"]
    reopened_id: str | None = st.session_state["reopened_review_id"]
    st.session_state["source_reload_notice"] = None
    st.session_state["comparison_base_bundle"] = None
    if (
        state is not None
        and reopened_id == state.review.review_id
        and state.review.repository == snapshot.repository
        and state.review.pr_number == snapshot.pr_number
    ):
        notice = JsonReviewStore.detect_head_change(state, snapshot)
        st.session_state["source_reload_notice"] = notice
        if state.bundle is not None:
            st.session_state["comparison_base_bundle"] = state.bundle.model_copy(deep=True)


def _prepare_from_text(text: str) -> None:
    drafts = parse_criteria(text)
    st.session_state["criteria"] = [
        Criterion(criterion_id=draft.criterion_id, text=draft.text) for draft in drafts
    ]
    _reset_analysis()


def _hydrate_reopened_review(state: ReviewState) -> None:
    """Restore persisted review state without claiming its source snapshot is loaded."""
    st.session_state["snapshot"] = None
    st.session_state["criteria"] = state.criteria_revision.criteria
    st.session_state["criteria_confirmed"] = state.review.criteria_confirmed
    st.session_state["bundle"] = state.bundle
    st.session_state["source_text"] = state.criteria_revision.source_text
    st.session_state["requirements_input"] = state.criteria_revision.source_text
    st.session_state["resolutions"] = []
    st.session_state["review_state"] = state
    st.session_state["reopened_review_id"] = state.review.review_id
    st.session_state["source_reload_notice"] = None
    st.session_state["saved_review_fingerprint"] = _review_state_fingerprint(state)
    st.session_state["failed_review_save_fingerprint"] = None
    st.session_state["review_save_conflict"] = False
    st.session_state["deleted_review_save_fingerprint"] = None
    st.session_state["review_save_notice"] = None
    st.session_state["candidate_files"] = []
    unchanged_candidate_paths = (
        sorted(
            {
                item.file_path
                for item in state.bundle.evidence
                if item.source_scope is EvidenceSourceScope.UNCHANGED_CANDIDATE
            }
        )
        if state.bundle is not None
        else []
    )
    st.session_state["source_widget_sync_pending"] = {
        "pr_url": (
            f"https://github.com/{state.review.repository}/pull/"
            f"{state.review.pr_number}"
        ),
        "candidate_paths": "\n".join(unchanged_candidate_paths),
    }
    st.session_state["comparison_base_bundle"] = None
    st.session_state["alpha_case_id"] = None
    provenance = state.review.criteria_source_provenance
    st.session_state["criteria_source_provenance"] = provenance
    st.session_state["criteria_source_mode"] = (
        "demo"
        if provenance is not None
        and provenance.source_uri == CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI
        else "standard"
    )
    st.session_state["criteria_source_reference"] = (
        provenance.source_uri if provenance is not None else ""
    )
    st.session_state["criteria_source_revision"] = (
        provenance.source_revision or "" if provenance is not None else ""
    )
    st.session_state["criteria_source_confirmer"] = (
        provenance.confirmed_by if provenance is not None else ""
    )
    st.session_state["criteria_source_draft"] = {
        "criteria_source_reference": st.session_state["criteria_source_reference"],
        "criteria_source_revision": st.session_state["criteria_source_revision"],
        "criteria_source_confirmer": st.session_state["criteria_source_confirmer"],
    }
    st.session_state["replace_unsaved_review_reset_pending"] = True


def _analyze() -> ReviewBundle:
    snapshot = st.session_state["snapshot"]
    criteria = st.session_state["criteria"]
    input_origin = (
        ReviewInputOrigin.CONSTRUCTED_DEMO
        if st.session_state["criteria_source_mode"] == "demo"
        else ReviewInputOrigin.LIVE_PUBLIC_GITHUB
    )
    require_verified_public_origin(snapshot.repository_visibility, input_origin)
    review = Review(
        repository=snapshot.repository,
        repository_visibility=snapshot.repository_visibility,
        pr_number=snapshot.pr_number,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
        check_state=snapshot.check_state,
        ci_observation=snapshot.ci_observation,
        criteria_confirmed=st.session_state["criteria_confirmed"],
        criteria_source_provenance=st.session_state["criteria_source_provenance"],
        ingestion_state=snapshot.ingestion_state,
        ingestion_warnings=snapshot.warnings,
        skipped_files=snapshot.skipped_files,
        input_origin=input_origin,
    )
    retrieval_result = retrieve_evidence_with_diagnostics(
        snapshot, criteria, unchanged_files=st.session_state["candidate_files"]
    )
    evidence = retrieval_result.evidence
    findings = build_findings(criteria, evidence, snapshot.ingestion_state)
    resolutions = st.session_state["resolutions"]
    gate = evaluate_gate(review, criteria, findings, resolutions)
    return ReviewBundle(
        review=review,
        source_text=st.session_state["source_text"],
        criteria=criteria,
        evidence=evidence,
        retrieval_diagnostics=retrieval_result.diagnostics,
        findings=findings,
        resolutions=resolutions,
        gate=gate,
    )


def _status_label(value: str) -> str:
    return value.replace("_", " ").title()


def _render_comparison_reference(
    label: str, reference: EvidenceReference | None
) -> None:
    """Render one validated comparison reference without trusting its text as Markdown."""

    if reference is None:
        return
    st.markdown(f"**{label}**")
    st.caption("Immutable location")
    st.code(
        f"{reference.file_path}:L{reference.line_start}-L{reference.line_end}"
        f" @ {reference.commit_sha}",
        language=None,
    )
    st.caption("Candidate excerpt")
    st.code(reference.excerpt, language=None)
    st.markdown(render_artifact_reference_markdown(reference.permalink))


def _criteria_draft_pending(criteria: list[Criterion]) -> bool:
    return any(
        not str(
            st.session_state.get(f"criterion_text_{item.criterion_id}", item.text)
        ).strip()
        or st.session_state.get(f"criterion_text_{item.criterion_id}", item.text)
        != item.text
        or st.session_state.get(
            f"criterion_priority_{item.criterion_id}", item.priority
        )
        != item.priority
        or st.session_state.get(
            f"criterion_level_{item.criterion_id}", item.required_evidence_level
        )
        != item.required_evidence_level
        for item in criteria
    )


def _clear_criteria_draft(criteria: list[Criterion]) -> None:
    for item in criteria:
        st.session_state[f"criterion_text_{item.criterion_id}"] = item.text
        st.session_state[f"criterion_priority_{item.criterion_id}"] = item.priority
        st.session_state[f"criterion_level_{item.criterion_id}"] = (
            item.required_evidence_level
        )


def _criteria_authoring_draft_pending() -> bool:
    return any(
        bool(str(st.session_state.get(key, "")).strip())
        for key in ("new_criterion_text", "split_criterion_text")
    )


def _clear_criteria_authoring_drafts(keys: tuple[str, ...]) -> None:
    for key in keys:
        st.session_state[key] = ""


def _requirements_draft_pending() -> bool:
    return st.session_state.get("requirements_input", "") != st.session_state.get(
        "source_text", ""
    )


def _criteria_source_draft_pending(criteria: list[Criterion]) -> bool:
    """Return whether typed source identity differs from the confirmed snapshot."""

    provenance = st.session_state.get("criteria_source_provenance")
    if provenance is None:
        return False
    if st.session_state.get("alpha_feedback_mode", False):
        source_reference = str(
            st.session_state.get("requirements_source_url", "")
        ).strip()
    elif st.session_state.get("criteria_source_mode") == "demo":
        source_reference = CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI
    else:
        source_reference = str(
            st.session_state.get("criteria_source_reference", "")
        ).strip()
    source_revision = (
        str(st.session_state.get("criteria_source_revision", "")).strip() or None
    )
    confirmer = str(st.session_state.get("criteria_source_confirmer", "")).strip()
    return bool(
        source_reference != provenance.source_uri
        or source_revision != provenance.source_revision
        or confirmer != provenance.confirmed_by
        or source_text_sha256(st.session_state.get("source_text", ""))
        != provenance.source_text_sha256
        or canonical_criteria_sha256(criteria)
        != provenance.normalized_criteria_sha256
    )


def _clear_requirements_draft() -> None:
    st.session_state["requirements_input"] = st.session_state["source_text"]


def _criterion_detail_draft_pending() -> bool:
    runtime_text_keys = (
        "runtime_artifact_reference",
        "runtime_scenario",
        "runtime_environment",
        "runtime_result",
        "runtime_reviewer",
        "runtime_limitations",
    )
    return any(
        bool(str(st.session_state.get(key, ""))) for key in runtime_text_keys
    ) or (
        st.session_state.get("runtime_evidence_level", EvidenceLevel.E3)
        != EvidenceLevel.E3
    ) or (
        st.session_state.get("resolution_decision") is not None
        or bool(str(st.session_state.get("resolution_note", "")))
        or "manual_evidence_level" in st.session_state
    )


def _clear_runtime_evidence_draft() -> None:
    runtime_text_keys = (
        "runtime_artifact_reference",
        "runtime_scenario",
        "runtime_environment",
        "runtime_result",
        "runtime_reviewer",
        "runtime_limitations",
    )
    for key in runtime_text_keys:
        st.session_state[key] = ""
    st.session_state["runtime_evidence_level"] = EvidenceLevel.E3


def _clear_resolution_draft() -> None:
    st.session_state["resolution_decision"] = None
    st.session_state["resolution_note"] = ""
    st.session_state.pop("manual_evidence_level", None)


def _clear_criterion_detail_drafts() -> bool:
    """Clear unsaved target-specific inputs and report whether any draft existed."""
    had_pending_input = _criterion_detail_draft_pending()
    _clear_runtime_evidence_draft()
    _clear_resolution_draft()
    return had_pending_input


def _render_sidebar_step(text: str, anchor: str | None = None) -> None:
    st.markdown(f"[{text}]({anchor})" if anchor is not None else text)


def _render_loaded_source_identity(snapshot: PullRequestSnapshot) -> None:
    changed_file_count = len(snapshot.files)
    changed_file_label = "file" if changed_file_count == 1 else "files"
    with st.container(border=True):
        st.markdown("**Loaded source**")
        st.text(f"{snapshot.repository} · PR #{snapshot.pr_number}")
        st.caption("Head SHA")
        st.code(snapshot.head_sha, language=None)
        st.caption(
            f"{changed_file_count} changed {changed_file_label} fetched · "
            f"{_status_label(snapshot.ingestion_state.value)} ingestion"
        )


def _render_ci_observation_summary(bundle: ReviewBundle) -> None:
    observation = bundle.review.ci_observation
    with st.container(border=True):
        st.markdown("**Observed CI and verification boundary**")
        st.caption(f"Observed CI: {_status_label(observation.state.value)}")
        st.caption(
            f"Collection: {'Complete' if observation.collection_complete else 'Incomplete'}"
        )
        st.caption(
            f"{observation.total_check_runs} total · "
            f"{observation.successful_check_runs} successful · "
            f"{observation.pending_check_runs} pending · "
            f"{observation.failing_check_runs} failing · "
            f"{observation.neutral_check_runs} neutral · "
            f"{observation.skipped_check_runs} skipped · "
            f"{observation.concrete_legacy_status_count} concrete legacy statuses"
        )
        st.caption("Deterministic reason")
        st.text(observation.reason)
        st.caption(
            "Runtime verification: "
            f"{bundle.runtime_verification_state.value.replace('_', ' ').capitalize()}"
        )
        if (
            observation.state is not CheckState.PASSING
            or not observation.collection_complete
            or observation.skipped_check_runs > 0
        ):
            if observation.state is not CheckState.PASSING or not observation.collection_complete:
                st.warning(
                    "Observed CI has a limiting state. Review its deterministic reason before "
                    "relying on the gate."
                )
            if observation.skipped_check_runs > 0:
                st.warning(
                    "Observed CI includes skipped checks. Skipped checks were not executed; "
                    "review its deterministic reason and CI details before relying on the gate."
                )

    with st.expander("CI details and evidence boundary", expanded=False):
        if observation.skipped_check_names:
            st.caption("Skipped CI checks (unexecuted)")
            for name in observation.skipped_check_names:
                st.text(name)
        if observation.collection_notes:
            st.caption("CI collection diagnostics")
            for note in observation.collection_notes:
                st.text(note)
        st.caption(
            "Static candidates and observed CI do not establish runtime verification. "
            "Runtime evidence and reviewer decisions remain separate."
        )
        if bundle.research_context is not None:
            st.caption("Public engineering research · Stage 1 credit: 0")
            st.caption("Case ID")
            st.code(bundle.research_context.case_id, language=None)
            st.text(bundle.research_context.boundary_note)


def _render_ingestion_limitations(source: PullRequestSnapshot | Review | None) -> None:
    if source is None or source.ingestion_state is not IngestionState.PARTIAL:
        return
    ingestion_warnings = (
        source.warnings
        if isinstance(source, PullRequestSnapshot)
        else source.ingestion_warnings
    )
    st.warning(
        "Partial PR ingestion: ScopeProof did not inspect every changed file. Results remain "
        "bounded to the files retrieved, and the gate cannot be Ready. Narrow or split the PR, "
        "then reload it for a complete review."
    )
    if ingestion_warnings:
        st.caption("Ingestion details reported by the repository adapter:")
        for warning in ingestion_warnings:
            st.code(warning, language=None)
    if source.skipped_files:
        with st.expander(f"Skipped changed files ({len(source.skipped_files)})"):
            st.caption("These paths were not inspected and are not evidence for any criterion.")
            for path in source.skipped_files:
                st.code(path, language=None)


if st.session_state["replace_unsaved_review_reset_pending"]:
    st.session_state["replace_unsaved_review_confirmed"] = False
    st.session_state["replace_unsaved_review_reset_pending"] = False
if st.session_state["delete_saved_review_reset_pending"]:
    st.session_state["delete_saved_review_reset_pending"] = False
    st.session_state["saved_reopen_review_id"] = None
    st.session_state["delete_saved_review_confirmed"] = False
if st.session_state.pop("runtime_evidence_form_reset_pending", False):
    _clear_runtime_evidence_draft()
if st.session_state.pop("resolution_form_reset_pending", False):
    _clear_resolution_draft()
if st.session_state.pop("criteria_draft_reset_pending", False):
    _clear_criteria_draft(st.session_state["criteria"])
criteria_authoring_reset_keys = st.session_state.pop(
    "criteria_authoring_reset_keys", ()
)
if criteria_authoring_reset_keys:
    _clear_criteria_authoring_drafts(criteria_authoring_reset_keys)
if st.session_state.pop("requirements_draft_reset_pending", False):
    _clear_requirements_draft()

storage_directory = default_local_review_directory()
review_store = JsonReviewStore(Path(storage_directory))
try:
    saved_review_ids = review_store.list_review_ids()
except (OSError, UnsafeReviewStore):
    saved_review_ids = []
    review_store_available = False
else:
    review_store_available = True

current_review_state: ReviewState | None = st.session_state["review_state"]
has_pending_criteria_draft = _criteria_draft_pending(st.session_state["criteria"])
has_pending_criteria_authoring_draft = _criteria_authoring_draft_pending()
has_pending_requirements_draft = _requirements_draft_pending()
has_pending_criterion_detail_draft = _criterion_detail_draft_pending()
has_pending_criteria_source = _criteria_source_draft_pending(
    st.session_state["criteria"]
)
has_missing_active_provenance = bool(
    current_review_state is not None
    and current_review_state.review.criteria_source_provenance is None
)
has_pending_review_input = (
    has_pending_criteria_draft
    or has_pending_criteria_authoring_draft
    or has_pending_requirements_draft
    or has_pending_criterion_detail_draft
    or has_pending_criteria_source
    or has_missing_active_provenance
)
current_review_state = _refresh_clean_review_from_local_store(
    current_review_state,
    store=review_store,
    store_available=review_store_available,
    has_pending_review_input=has_pending_review_input,
)
pending_storage_messages: list[str] = []
if has_pending_criteria_draft:
    pending_storage_messages.append(
        "Pending criteria edits are not saved or exported. Confirm or discard them "
        "before relying on this review ID."
    )
if has_pending_criteria_authoring_draft:
    pending_storage_messages.append(
        "Pending add or split criterion inputs are not saved or exported. Submit or "
        "clear them before relying on this review ID."
    )
if has_pending_requirements_draft:
    pending_storage_messages.append(
        "Pending requirements changes are not saved or exported. Prepare or discard "
        "them before relying on this review ID."
    )
if has_pending_criterion_detail_draft:
    pending_storage_messages.append(
        "Pending criterion-detail inputs are not saved or exported. Submit or clear "
        "them before relying on this review ID."
    )
if has_pending_criteria_source:
    pending_storage_messages.append(
        "Pending criteria source changes are not saved or exported. Reconfirm the source "
        "snapshot before relying on this review ID."
    )
if has_missing_active_provenance:
    pending_storage_messages.append(
        "This legacy review has no criteria source provenance. Reconfirm the source "
        "snapshot before saving, exporting, or recording final acceptance."
    )
autosaved = _autosave_review_if_eligible(
    state=current_review_state,
    store=review_store,
    store_available=review_store_available,
    has_pending_review_input=has_pending_review_input,
)
if autosaved and current_review_state is not None:
    saved_review_ids = sorted(
        {*saved_review_ids, current_review_state.review.review_id}
    )

st.title("ScopeProof")
st.markdown(
    "**See which acceptance criteria have credible PR evidence—and which still need review.**"
)
st.markdown(
    "> ScopeProof surfaces auditable candidate evidence. "
    "It does not replace QA or prove correctness."
)
st.caption("No paid LLM API. Deterministic rules. Human acceptance stays visible.")

has_unsaved_review = bool(
    current_review_state is not None
    and (
        not _review_matches_local_save(current_review_state)
        or has_pending_review_input
    )
)
if has_unsaved_review:
    st.warning(
        "The current review has unsaved changes. Replacing it will discard unsaved changes."
    )
    replace_unsaved_review_confirmed = st.checkbox(
        "Allow replacing the unsaved current review",
        key="replace_unsaved_review_confirmed",
    )
else:
    st.session_state["replace_unsaved_review_confirmed"] = False
    replace_unsaved_review_confirmed = False
replacement_blocked = has_unsaved_review and not replace_unsaved_review_confirmed
authoring_submission_blocked = bool(
    current_review_state is not None
    and (
        not _review_matches_local_save(current_review_state)
        or has_pending_criteria_draft
        or has_pending_requirements_draft
        or has_pending_criterion_detail_draft
    )
    and not replace_unsaved_review_confirmed
)
requirements_submission_blocked = bool(
    current_review_state is not None
    and (
        not _review_matches_local_save(current_review_state)
        or has_pending_criteria_draft
        or has_pending_criteria_authoring_draft
        or has_pending_criterion_detail_draft
    )
    and not replace_unsaved_review_confirmed
)

st.header("1 · Start Review")
st.markdown("**Public PR → Confirm criteria → Review coverage → Record decisions → Export**")
st.caption(
    "Five bounded stages keep source loading, human confirmation, candidate analysis, "
    "reviewer decisions, and exports separate."
)
pr_url = st.text_input(
    "Public GitHub pull request URL",
    placeholder="https://github.com/owner/repository/pull/123",
    key="pr_url",
)
pr_url_is_valid = False
if pr_url.strip():
    try:
        parse_pr_url(pr_url)
    except InvalidPullRequestUrl:
        st.warning(
            "Enter a public GitHub pull request URL in this format: "
            "`https://github.com/OWNER/REPO/pull/NUMBER`."
        )
    else:
        pr_url_is_valid = True
fetch_action_placeholder = st.empty()
alpha_feedback_mode = bool(st.session_state.get("alpha_feedback_mode", False))

with st.container(border=True):
    st.markdown("**Deliberately constructed demonstration**")
    st.caption(
        "A visible practice-data path. Any saved record remains constructed-demo-tagged and "
        "segregated from genuine review claims. It is not a public PR, customer case, production "
        "result, or validation claim."
    )
    if st.button(
        "Load deliberately constructed demo",
        key="load_demo",
        disabled=replacement_blocked or alpha_feedback_mode,
        use_container_width=True,
    ):
        labels = load_demo_labels()
        snapshot = load_demo_snapshot()
        _record_reopened_source_reload(snapshot)
        st.session_state["snapshot"] = snapshot
        st.session_state["source_text"] = labels["source_text"]
        st.session_state["requirements_input"] = labels["source_text"]
        st.session_state["criteria"] = [
            Criterion.model_validate(item) for item in labels["criteria"]
        ]
        st.session_state["candidate_files"] = []
        st.session_state["criteria_source_mode"] = "demo"
        st.session_state["criteria_source_reference"] = (
            CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI
        )
        st.session_state["criteria_source_revision"] = ""
        st.session_state["criteria_source_confirmer"] = ""
        st.session_state["criteria_source_draft"] = {
            "criteria_source_reference": CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
            "criteria_source_revision": "",
            "criteria_source_confirmer": "",
        }
        _reset_analysis()
        st.rerun()

with st.expander("Advanced source options", expanded=False):
    github_token = st.text_input(
        "Optional GitHub token",
        type="password",
        help=(
            "Used only in this session to increase free GitHub rate limits. "
            "Never exported or saved."
        ),
        key="github_token",
    )
    candidate_paths_text = st.text_area(
        "Bounded unchanged candidate paths (optional)",
        key="candidate_paths",
        help=(
            "One explicit repository-relative file path per line. ScopeProof does not "
            "infer paths or scan the repository."
        ),
    )
    candidate_paths = list(
        dict.fromkeys(
            line.strip() for line in candidate_paths_text.splitlines() if line.strip()
        )
    )
    st.caption("At most eight explicit UTF-8 text files are fetched at the PR head SHA.")

requirements_source_url = ""
with st.expander("Research and historical options", expanded=False):
    st.caption(
        "Stage 1 is closed and external feedback is not required for owner-led Stage 2. "
        "This optional research path is separate from the standard product workflow."
    )
    alpha_feedback_mode = st.checkbox(
        "Collect local alpha feedback for this review",
        value=False,
        key="alpha_feedback_mode",
    )
    if alpha_feedback_mode:
        st.caption(
            "Qualification is session-only. Confirm a genuine public case before fetching; "
            "ScopeProof does not store these preflight fields here."
        )
        requirements_source_url = st.text_input(
            "Public requirements source URL",
            placeholder="https://github.com/owner/repository/issues/123",
            key="requirements_source_url",
        )
        participant_role = st.selectbox(
            "Participant role",
            options=[role.value for role in ParticipantRole],
            key="participant_role",
        )
        source_owner_confirmed = st.checkbox(
            "I am the source owner or directly authorized to confirm these requirements",
            key="source_owner_confirmed",
        )
        no_confidential_information = st.checkbox(
            "This review contains no confidential information, secrets, or private links",
            key="no_confidential_information",
        )

alpha_qualification_ready = True
alpha_qualification_input: AlphaQualificationInput | None = None
alpha_qualification: AlphaQualification | None = None
if alpha_feedback_mode:
    alpha_qualification_ready = False
    if (
        pr_url_is_valid
        and requirements_source_url.strip()
        and source_owner_confirmed
        and no_confidential_information
    ):
        try:
            alpha_qualification_input = AlphaQualificationInput(
                public_pr_url=pr_url,
                requirements_source_url=requirements_source_url,
                participant_role=ParticipantRole(participant_role),
                source_owner_confirmed=True,
                no_confidential_information=True,
            )
        except ValueError:
            st.warning("Use a public HTTPS requirements source and a canonical public PR URL.")
        else:
            alpha_qualification_ready = True
    loaded_for_alpha = st.session_state["snapshot"]
    if alpha_qualification_input is not None and loaded_for_alpha is not None:
        try:
            alpha_owner, alpha_repository, alpha_pr_number = parse_pr_url(
                alpha_qualification_input.public_pr_url
            )
            if (
                f"{alpha_owner}/{alpha_repository}" != loaded_for_alpha.repository
                or alpha_pr_number != loaded_for_alpha.pr_number
            ):
                raise ValueError("alpha qualification must match the loaded public PR")
            alpha_qualification = AlphaQualification(
                **alpha_qualification_input.model_dump(mode="python"),
                repository_visibility=loaded_for_alpha.repository_visibility,
            )
        except ValueError:
            alpha_qualification = None
else:
    st.caption("Standard review mode does not create participant research records.")

reopened_review = st.session_state["review_state"]
fetch_action_label = (
    "Check current head"
    if reopened_review is not None
    and st.session_state["reopened_review_id"] == reopened_review.review.review_id
    else "Fetch public PR"
)
if fetch_action_placeholder.button(
    fetch_action_label,
    key="fetch_pr",
    disabled=(
        not pr_url_is_valid
        or not alpha_qualification_ready
        or replacement_blocked
    ),
    use_container_width=True,
):
    try:
        client = GitHubClient(token=github_token or None)
        snapshot = client.fetch_pull_request(pr_url)
        candidate_files = client.fetch_candidate_files(
            snapshot.repository, snapshot.head_sha, candidate_paths
        )
        _record_reopened_source_reload(snapshot)
        st.session_state["snapshot"] = snapshot
        st.session_state["candidate_files"] = candidate_files
        st.session_state["alpha_case_id"] = None
        st.session_state["criteria_source_mode"] = "standard"
        st.session_state["criteria_source_reference"] = ""
        st.session_state["criteria_source_revision"] = ""
        st.session_state["criteria_source_confirmer"] = ""
        st.session_state["criteria_source_draft"] = {
            "criteria_source_reference": "",
            "criteria_source_revision": "",
            "criteria_source_confirmer": "",
        }
        _reset_analysis()
        st.session_state["source_load_notice"] = (
            "Public PR loaded. Add and confirm criteria before analysis."
        )
        st.rerun()
    except (GitHubIngestionError, ValueError) as error:
        st.error(
            f"{error} No review data was changed. Verify that the PR is public and "
            "try again. Use the optional token only if GitHub reports a rate limit."
        )

with st.expander("Resume a saved review", expanded=False):
    if not review_store_available:
        reopen_id = ""
        st.error(
            "Local review storage is unavailable. Verify that the ScopeProof review directory "
            "is a regular local directory."
        )
    elif saved_review_ids:
        reopen_id = st.selectbox(
            "Saved review ID",
            options=saved_review_ids,
            index=None,
            placeholder="Select a saved review",
            key="saved_reopen_review_id",
        )
        record_label = "review" if len(saved_review_ids) == 1 else "reviews"
        st.caption(
            f"{len(saved_review_ids)} saved local {record_label} found. "
            "The selected record is validated when opened."
        )
    else:
        reopen_id = st.text_input("Review ID", key="reopen_review_id")
        st.caption("No saved local reviews found.")
    if st.button(
        "Reopen local review",
        key="reopen_review",
        disabled=not reopen_id or replacement_blocked or not review_store_available,
    ):
        try:
            reopened_state = review_store.load(reopen_id.strip())
        except FileNotFoundError:
            st.error("No saved review was found for that review ID.")
        except UnsupportedRecordVersion:
            st.error("This saved review requires a different ScopeProof record version.")
        except (OSError, ValueError):
            st.error("The saved review could not be opened. Verify its ID and record integrity.")
        else:
            _hydrate_reopened_review(reopened_state)
            st.session_state["review_reopen_notice"] = (
                "Review reopened from local storage after validation."
            )
            st.rerun()
    if saved_review_ids and reopen_id and review_store_available:
        delete_confirmed = st.checkbox(
            "Permanently delete the selected local review",
            key="delete_saved_review_confirmed",
        )
        if st.button(
            "Delete saved review",
            key="delete_saved_review",
            disabled=not delete_confirmed,
        ):
            try:
                review_store.delete(reopen_id)
            except FileNotFoundError:
                _mark_open_review_deleted(reopen_id)
                st.session_state["saved_review_delete_notice"] = (
                    "The selected saved review was already removed. Refresh the saved "
                    "review list."
                )
            except (OSError, ValueError):
                st.session_state["saved_review_delete_notice"] = (
                    "The saved review could not be deleted. Verify the local review "
                    "directory and try again."
                )
            else:
                if _mark_open_review_deleted(reopen_id):
                    st.session_state["saved_review_delete_notice"] = (
                        "Saved review deleted. The open review remains available as "
                        "unsaved work."
                    )
                else:
                    st.session_state["saved_review_delete_notice"] = (
                        "Saved review deleted."
                    )
            if not has_pending_requirements_draft:
                st.session_state["requirements_draft_reset_pending"] = True
            st.session_state["delete_saved_review_reset_pending"] = True
            st.rerun()
saved_review_delete_notice = st.session_state.pop("saved_review_delete_notice", None)
if saved_review_delete_notice is not None:
    if saved_review_delete_notice.startswith("Saved review deleted."):
        st.success(saved_review_delete_notice)
    else:
        st.warning(saved_review_delete_notice)
review_reopen_notice = st.session_state.pop("review_reopen_notice", None)
if review_reopen_notice is not None:
    st.success(review_reopen_notice)

source_load_notice = st.session_state.pop("source_load_notice", None)
if source_load_notice is not None:
    st.success(source_load_notice)

source_reload_notice = st.session_state["source_reload_notice"]
if source_reload_notice is not None and source_reload_notice.changed:
    st.warning(
        f"PR head changed from {source_reload_notice.saved_head_sha} to "
        f"{source_reload_notice.current_head_sha}. Prior saved evidence remains anchored "
        "to the old head. Reconfirm criteria and run a new review; do not reuse old evidence."
    )
elif source_reload_notice is not None:
    st.info(
        f"PR source reloaded at the same head SHA: {source_reload_notice.current_head_sha}. "
        "Reconfirm criteria and run a new review before relying on current results."
    )

loaded_snapshot = st.session_state["snapshot"]
if loaded_snapshot is not None:
    _render_loaded_source_identity(loaded_snapshot)

ingestion_limitations_source = st.session_state["snapshot"]
if ingestion_limitations_source is None and current_review_state is not None:
    ingestion_limitations_source = current_review_state.review
_render_ingestion_limitations(ingestion_limitations_source)

requirements_text = st.text_area(
    "Product requirements or acceptance criteria",
    height=150,
    key="requirements_input",
    help="Use one independently judgeable behavior per line. ScopeProof will not invent criteria.",
)
requirements_draft_discard_notice = st.session_state.pop(
    "requirements_draft_discard_notice", None
)
if requirements_draft_discard_notice is not None:
    st.success(requirements_draft_discard_notice)
if has_pending_requirements_draft and st.button(
    "Discard unprepared requirements changes",
    key="discard_requirements_draft",
):
    st.session_state["requirements_draft_reset_pending"] = True
    st.session_state["requirements_draft_discard_notice"] = (
        "Unprepared requirements changes discarded without changing the review."
    )
    st.rerun()
requirements_are_prepared = (
    bool(st.session_state["criteria"])
    and st.session_state["bundle"] is None
    and requirements_text == st.session_state["source_text"]
)
if st.button(
    "Prepare criteria",
    key="prepare_criteria",
    disabled=(
        not bool(requirements_text.strip())
        or requirements_submission_blocked
        or requirements_are_prepared
    ),
):
    st.session_state["source_text"] = requirements_text
    _prepare_from_text(requirements_text)
    st.rerun()

if requirements_are_prepared and not st.session_state["criteria_confirmed"]:
    st.success("Criteria prepared. Review the set before explicitly confirming it.")
    st.markdown("[Continue to 2 · Confirm Criteria](#2-confirm-criteria)")

st.header("2 · Confirm Criteria")
criteria: list[Criterion] = st.session_state["criteria"]
edited_criteria = criteria
criteria_edits_pending = False
analysis_continuation_placeholder = None
if not criteria:
    st.info("Load the demo or prepare at least one criterion to continue.")
else:
    st.caption(
        "The source owner must review and explicitly confirm the normalized criteria "
        "before analysis. "
        "Evidence levels set the minimum proof needed for each criterion: "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification. Static PR analysis can produce "
        "only E1 or E2."
    )
    with st.container(border=True):
        st.markdown("**Criteria source**")
        if alpha_feedback_mode:
            criteria_source_reference = requirements_source_url.strip()
            st.caption("Public requirements source")
            if criteria_source_reference:
                st.code(criteria_source_reference, language=None)
            else:
                st.caption("Enter the public requirements URL in the alpha session above.")
        else:
            criteria_source_reference = st.text_input(
                "Source reference",
                key="criteria_source_reference",
                disabled=st.session_state["criteria_source_mode"] == "demo",
                on_change=_remember_criteria_source_draft,
                help=(
                    "Use the public HTTPS requirements location. The bundled demo uses its "
                    "explicit constructed-source reference."
                ),
            ).strip()
        with st.expander("Source revision (optional)", expanded=False):
            st.caption(
                "Add an issue edit, document revision, or other immutable source version "
                "when one is available."
            )
            criteria_source_revision = st.text_input(
                "Revision identifier",
                key="criteria_source_revision",
                on_change=_remember_criteria_source_draft,
            ).strip()
        criteria_source_confirmer = st.text_input(
            "Confirmed by",
            key="criteria_source_confirmer",
            on_change=_remember_criteria_source_draft,
            help="Name or role of the human who checked this normalized criterion set.",
        ).strip()
        st.caption(
            "Confirmation binds the exact source text and ordered normalized criteria to "
            "this source snapshot."
        )
    criteria_summary_placeholder = st.empty()
    criteria_validation_placeholder = st.container()
    confirm_action_placeholder = st.empty()
    analysis_continuation_placeholder = st.empty()
    criterion_validation_placeholders = {}
    with st.expander("Add or split criteria", expanded=False):
        new_criterion_text = st.text_input("Add criterion", key="new_criterion_text")
        if st.button(
            "Add criterion",
            key="add_criterion_ui",
            disabled=not new_criterion_text.strip() or authoring_submission_blocked,
        ):
            _apply_criteria_update(
                partial(add_criterion, criteria, new_criterion_text),
                "Criterion added. Confirm the updated set before analysis.",
                consumed_input_keys=("new_criterion_text",),
            )
        split_target = st.selectbox(
            "Split criterion",
            options=[item.criterion_id for item in criteria],
            key="split_criterion_id",
        )
        split_text = st.text_area(
            "Split criterion into one behavior per line",
            key="split_criterion_text",
        )
        if st.button(
            "Split criterion",
            key="split_criterion_ui",
            disabled=(
                len([line for line in split_text.splitlines() if line.strip()]) < 2
                or authoring_submission_blocked
            ),
        ):
            split_texts = [line.strip() for line in split_text.splitlines() if line.strip()]
            _apply_criteria_update(
                partial(split_criterion, criteria, split_target, split_texts),
                "Criterion split. Confirm the updated set before analysis.",
                consumed_input_keys=("split_criterion_text",),
            )
    criteria_authoring_clear_notice = st.session_state.pop(
        "criteria_authoring_clear_notice", None
    )
    if criteria_authoring_clear_notice is not None:
        st.success(criteria_authoring_clear_notice)
    if has_pending_criteria_authoring_draft and st.button(
        "Clear unsubmitted add and split inputs",
        key="clear_criteria_authoring_drafts",
    ):
        st.session_state["criteria_authoring_reset_keys"] = (
            "new_criterion_text",
            "split_criterion_text",
        )
        st.session_state["criteria_authoring_clear_notice"] = (
            "Unsubmitted add and split inputs cleared without changing the review."
        )
        st.rerun()
    edited_criteria: list[Criterion] = []
    blank_criterion_ids: list[str] = []
    for position, criterion in enumerate(criteria):
        displayed_priority = st.session_state.get(
            f"criterion_priority_{criterion.criterion_id}", criterion.priority
        )
        displayed_level = st.session_state.get(
            f"criterion_level_{criterion.criterion_id}", criterion.required_evidence_level
        )
        editor_label = (
            f"{criterion.criterion_id} · {_status_label(displayed_priority.value)} · "
            f"{displayed_level.value}"
        )
        with st.expander(editor_label, expanded=False):
            st.caption("Confirmed requirement")
            st.text(criterion.text)
            text_column, priority_column, level_column, actions_column = st.columns(
                [5, 2, 2, 2]
            )
            with text_column:
                edited_text = st.text_input(
                    criterion.criterion_id,
                    value=criterion.text,
                    key=f"criterion_text_{criterion.criterion_id}",
                )
            with priority_column:
                priority = st.selectbox(
                    f"Priority for {criterion.criterion_id}",
                    options=list(Priority),
                    index=list(Priority).index(criterion.priority),
                    format_func=lambda item: _status_label(item.value),
                    key=f"criterion_priority_{criterion.criterion_id}",
                )
            with level_column:
                level = st.selectbox(
                    f"Required evidence for {criterion.criterion_id}",
                    options=[EvidenceLevel.E1, EvidenceLevel.E2, EvidenceLevel.E3],
                    index=[EvidenceLevel.E1, EvidenceLevel.E2, EvidenceLevel.E3].index(
                        criterion.required_evidence_level
                    ),
                    key=f"criterion_level_{criterion.criterion_id}",
                )
            with actions_column:
                if st.button(
                    f"Remove {criterion.criterion_id}",
                    key=f"remove_{criterion.criterion_id}",
                    disabled=replacement_blocked,
                ):
                    _apply_criteria_update(
                        partial(remove_criterion, criteria, criterion.criterion_id),
                        "Criterion removed. Confirm the updated set before analysis.",
                    )
                if position > 0 and st.button(
                    f"Move {criterion.criterion_id} up",
                    key=f"move_up_{criterion.criterion_id}",
                    disabled=replacement_blocked,
                ):
                    order = [item.criterion_id for item in criteria]
                    order[position - 1], order[position] = order[position], order[position - 1]
                    _apply_criteria_update(
                        partial(reorder_criteria, criteria, order),
                        "Criterion order changed. Confirm the updated set before analysis.",
                    )
            criterion_validation_placeholders[criterion.criterion_id] = st.empty()
        if not edited_text.strip():
            blank_criterion_ids.append(criterion.criterion_id)
            edited_criteria.append(criterion)
        else:
            edited_criteria.append(
                Criterion(
                    criterion_id=criterion.criterion_id,
                    text=edited_text,
                    priority=priority,
                    criterion_type=criterion.criterion_type,
                    source_span=criterion.source_span,
                    required_evidence_level=level,
                )
            )
    warnings = validate_criteria(edited_criteria)
    criteria_edits_pending = _criteria_draft_pending(criteria)
    criteria_summary_placeholder.caption(
        f"Criteria: {len(criteria)} · "
        f"Confirmation: {'Confirmed' if st.session_state['criteria_confirmed'] else 'Required'} · "
        f"Pending edits: {'Present' if criteria_edits_pending else 'None'}"
    )
    with criteria_validation_placeholder:
        for criterion_id in blank_criterion_ids:
            st.warning(f"{criterion_id}: Criterion text cannot be blank.")
        for warning in warnings:
            st.warning(f"{warning.criterion_id}: {warning.message}")

    warnings_by_criterion: dict[str, list[str]] = {
        criterion.criterion_id: [] for criterion in criteria
    }
    for criterion_id in blank_criterion_ids:
        warnings_by_criterion[criterion_id].append("Criterion text cannot be blank.")
    for warning in warnings:
        warnings_by_criterion[warning.criterion_id].append(warning.message)
    for criterion_id, placeholder in criterion_validation_placeholders.items():
        with placeholder.container():
            for message in warnings_by_criterion[criterion_id]:
                st.warning(message)

    st.caption(
        "Typing or pressing Enter only stages draft changes. Use the explicit action below "
        "to apply edits and bind the confirmed criteria snapshot."
    )
    confirm_clicked = confirm_action_placeholder.button(
        "Apply edits and confirm criteria",
        key="confirm_criteria",
        disabled=(
            bool(blank_criterion_ids)
            or not criteria_source_reference
            or not criteria_source_confirmer
            or (
                st.session_state["criteria_confirmed"]
                and not criteria_edits_pending
                and not has_pending_criteria_source
                and not has_missing_active_provenance
            )
        ),
        use_container_width=True,
    )
    criteria_draft_discard_notice = st.session_state.pop(
        "criteria_draft_discard_notice", None
    )
    if criteria_draft_discard_notice is not None:
        st.success(criteria_draft_discard_notice)
    if criteria_edits_pending and st.button(
        "Discard unconfirmed criteria edits",
        key="discard_criteria_draft",
    ):
        st.session_state["criteria_draft_reset_pending"] = True
        st.session_state["criteria_draft_discard_notice"] = (
            "Unconfirmed criteria edits discarded without changing the review."
        )
        st.rerun()
    if confirm_clicked:
        state: ReviewState | None = st.session_state["review_state"]
        alpha_case = None
        try:
            if state is not None and (
                state.bundle is not None
                or state.criteria_revision.criteria != edited_criteria
                or state.criteria_revision.source_text
                != st.session_state["source_text"]
                or (
                    state.review.criteria_source_provenance is not None
                    and has_pending_criteria_source
                )
            ):
                state = revise_criteria(
                    state, edited_criteria, st.session_state["source_text"]
                )
            provenance = build_criteria_source_provenance(
                source_uri=criteria_source_reference,
                source_revision=criteria_source_revision or None,
                source_text=st.session_state["source_text"],
                criteria=edited_criteria,
                confirmed_by=criteria_source_confirmer,
                confirmed_at=datetime.now(UTC),
            )
            if state is not None:
                state = confirm_criteria(state, provenance)
            if alpha_feedback_mode:
                if alpha_qualification is None:
                    raise ValueError("alpha qualification is incomplete")
                loaded_for_alpha = st.session_state["snapshot"]
                if loaded_for_alpha is None:
                    raise ValueError("alpha qualification requires a loaded public PR")
                alpha_owner, alpha_repository, alpha_pr_number = parse_pr_url(
                    alpha_qualification.public_pr_url
                )
                if (
                    f"{alpha_owner}/{alpha_repository}" != loaded_for_alpha.repository
                    or alpha_pr_number != loaded_for_alpha.pr_number
                ):
                    raise ValueError("alpha qualification must match the loaded public PR")
                alpha_store = JsonAlphaCaseStore(default_alpha_case_directory())
                alpha_case = ensure_alpha_case(
                    store=alpha_store,
                    # A repeated confirmation represents changed authoritative input.
                    # Preserve the prior immutable alpha case and create a new snapshot.
                    case_id=None,
                    public_pr_url=alpha_qualification.public_pr_url,
                    requirements_source_url=str(
                        alpha_qualification.requirements_source_url
                    ),
                    participant_role=alpha_qualification.participant_role,
                    source_owner_confirmed=True,
                    no_confidential_information=True,
                    confirmed_criteria=[item.text for item in edited_criteria],
                    confirmed_criterion_snapshot=edited_criteria,
                    criteria_source_provenance=provenance,
                    repository_visibility=alpha_qualification.repository_visibility,
                )
        except ValueError:
            st.error(
                "Criteria could not be confirmed. The current review remains unchanged. "
                "Verify the edited criteria and try again."
            )
        else:
            if alpha_case is not None:
                st.session_state["alpha_case_id"] = alpha_case.case_id
                st.session_state["alpha_case_notice"] = (
                    f"Alpha case created locally: {alpha_case.case_id}."
                )
            if state is not None:
                st.session_state["review_state"] = state
            st.session_state["criteria"] = edited_criteria
            st.session_state["criteria_confirmed"] = True
            st.session_state["criteria_source_provenance"] = provenance
            st.session_state["criteria_source_draft"] = {
                "criteria_source_reference": provenance.source_uri,
                "criteria_source_revision": provenance.source_revision or "",
                "criteria_source_confirmer": provenance.confirmed_by,
            }
            st.session_state["criteria_source_widget_sync_pending"] = {
                "criteria_source_reference": provenance.source_uri,
                "criteria_source_revision": provenance.source_revision or "",
                "criteria_source_confirmer": provenance.confirmed_by,
                **(
                    {"requirements_source_url": provenance.source_uri}
                    if alpha_feedback_mode
                    else {}
                ),
            }
            st.session_state["bundle"] = None if state is None else state.bundle
            criteria_edits_pending = False
            st.rerun()

alpha_case_notice = st.session_state.pop("alpha_case_notice", None)
if alpha_case_notice is not None:
    st.success(alpha_case_notice)

if has_missing_active_provenance:
    st.warning(
        "This legacy review has no criteria source provenance. Enter the source reference "
        "and confirmer, then reconfirm before analysis, export, or final acceptance."
    )
elif has_pending_criteria_source:
    st.warning(
        "Criteria source changes are pending confirmation. The saved review still uses the "
        "last confirmed source snapshot. Reconfirm before analysis, export, or acceptance."
    )
elif criteria_edits_pending:
    st.warning(
        "Criteria edits are pending confirmation. Visible evidence and verdict still use "
        "the last confirmed criteria. Confirm the updated set before rerunning analysis."
    )
elif st.session_state["criteria_confirmed"]:
    st.success("Criteria confirmed by the reviewer.")
else:
    st.caption("Analysis remains locked until the criterion set is explicitly confirmed.")

active_criteria_source = st.session_state.get("criteria_source_provenance")
if active_criteria_source is not None:
    with st.expander("Confirmed criteria source", expanded=False):
        st.caption("Source reference")
        st.code(active_criteria_source.source_uri, language=None)
        st.caption("Source revision")
        st.text(active_criteria_source.source_revision or "Not supplied")
        st.caption("Exact source text SHA-256")
        st.code(active_criteria_source.source_text_sha256, language=None)
        st.caption("Ordered normalized criteria SHA-256")
        st.code(active_criteria_source.normalized_criteria_sha256, language=None)
        st.caption("Confirmed by")
        st.text(active_criteria_source.confirmed_by)
        st.caption("Confirmed at (UTC)")
        st.text(active_criteria_source.model_dump(mode="json")["confirmed_at"])

analysis_disabled = not (
    st.session_state["snapshot"] is not None
    and st.session_state["criteria_confirmed"]
    and bool(st.session_state["criteria"])
    and not criteria_edits_pending
    and not has_pending_criteria_source
    and not has_missing_active_provenance
    and (
        st.session_state["review_state"] is None
        or st.session_state["review_state"].bundle is None
    )
)
if not analysis_disabled and analysis_continuation_placeholder is not None:
    analysis_continuation_placeholder.markdown(
        "[Continue to run deterministic analysis](#run-deterministic-analysis)"
    )
st.markdown("### Run deterministic analysis")
if st.button("Run deterministic analysis", key="run_analysis", disabled=analysis_disabled):
    try:
        bundle = _analyze()
        existing_state = st.session_state["review_state"]
        state = (
            new_review_state(bundle)
            if existing_state is None
            else attach_analysis(existing_state, bundle)
        )
    except ValueError:
        st.error(
            "Analysis could not be completed. No review state was changed. Verify the "
            "confirmed criteria and loaded source, then try again."
        )
    else:
        st.session_state["review_state"] = state
        st.session_state["bundle"] = state.bundle
        st.session_state["source_reload_notice"] = None
        st.rerun()

review_state: ReviewState | None = st.session_state["review_state"]
bundle: ReviewBundle | None = review_state.bundle if review_state else st.session_state["bundle"]
review_matches_local_save = bool(
    review_state is not None
    and _review_matches_local_save(review_state)
    and not has_pending_review_input
)
review_save_notice = st.session_state.pop("review_save_notice", None)
st.header("3 · Evidence Matrix")
if bundle is None:
    st.info("Confirm criteria and run analysis to generate the evidence matrix.")
    if review_save_notice is not None:
        st.success(review_save_notice)
    if review_state is not None:
        criterion_detail_draft_clear_notice = st.session_state.pop(
            "criterion_detail_draft_clear_notice", None
        )
        if criterion_detail_draft_clear_notice is not None:
            st.success(criterion_detail_draft_clear_notice)
        if has_pending_criterion_detail_draft:
            st.warning(
                "Pending criterion inputs are not part of the review, local save, or exports. "
                "Clear them to continue with this revised review."
            )
            if st.button(
                "Clear pending criterion inputs",
                key="clear_criterion_detail_drafts",
            ):
                _clear_criterion_detail_drafts()
                st.session_state["criterion_detail_draft_clear_notice"] = (
                    "Pending criterion inputs cleared without changing the review."
                )
                st.rerun()
        _render_local_review_storage(
            review_state,
            store=review_store,
            store_available=review_store_available,
            has_pending_review_input=has_pending_review_input,
            pending_messages=pending_storage_messages,
        )
else:
    comparison_base: ReviewBundle | None = st.session_state["comparison_base_bundle"]
    comparison: ReviewComparison | None = None
    if comparison_base is not None:
        try:
            comparison = compare_reviews(comparison_base, bundle)
        except ValueError:
            st.session_state["comparison_base_bundle"] = None
            st.warning(
                "The previous review cannot be compared with this analysis because the pull "
                "request, exact head identity, confirmed criteria, or criteria source changed. "
                "No prior decisions were carried forward."
            )
    if comparison is not None:
        st.markdown("### Re-review comparison")
        st.caption(f"Previous head: {comparison.previous_head_sha}")
        st.caption(f"Current head: {comparison.current_head_sha}")
        st.markdown(
            f"**Review status:** {_status_label(comparison.previous_gate.value)} → "
            f"{_status_label(comparison.current_gate.value)}"
        )
        st.markdown(
            "**Candidate changes:** "
            f"Modified: {comparison.evidence_change_counts.modified} · "
            f"Relocated: {comparison.evidence_change_counts.relocated} · "
            f"Added: {comparison.evidence_change_counts.added} · "
            f"Removed: {comparison.evidence_change_counts.removed} · "
            f"Unchanged: {comparison.evidence_change_counts.unchanged}"
        )
        st.caption(
            "Candidate comparison does not prove criterion satisfaction. Review the current "
            "evidence before recording a new decision."
        )
        comparison_markdown_column, comparison_json_column = st.columns(2)
        with comparison_markdown_column:
            st.download_button(
                "Download comparison Markdown",
                export_comparison_markdown(comparison),
                file_name=(
                    f"scopeproof-pr-{bundle.review.pr_number}-comparison.md"
                ),
                mime="text/markdown",
                key="download_comparison_markdown",
            )
        with comparison_json_column:
            st.download_button(
                "Download comparison JSON",
                export_comparison_json(comparison),
                file_name=(
                    f"scopeproof-pr-{bundle.review.pr_number}-comparison.json"
                ),
                mime="application/json",
                key="download_comparison_json",
            )
        changed_evidence = [
            change
            for change in comparison.evidence_changes
            if change.kind.value != "unchanged"
        ]
        unchanged_evidence = [
            change
            for change in comparison.evidence_changes
            if change.kind.value == "unchanged"
        ]
        for evidence_change in changed_evidence:
            with st.container(border=True):
                st.markdown(
                    f"**{evidence_change.criterion_id} · "
                    f"{_status_label(evidence_change.kind.value)}**"
                )
                st.caption(evidence_change.reason)
                _render_comparison_reference(
                    "Previous candidate", evidence_change.previous
                )
                _render_comparison_reference("Current candidate", evidence_change.current)
        if unchanged_evidence:
            with st.expander(
                f"Unchanged candidates ({len(unchanged_evidence)})",
                expanded=False,
            ):
                st.caption(
                    "Exact immutable candidate references match across both reviews. "
                    "This does not carry forward a human decision."
                )
                for evidence_change in unchanged_evidence:
                    with st.container(border=True):
                        st.markdown(f"**{evidence_change.criterion_id} · Unchanged**")
                        st.caption(evidence_change.reason)
                        _render_comparison_reference(
                            "Previous candidate", evidence_change.previous
                        )
                        _render_comparison_reference(
                            "Current candidate", evidence_change.current
                        )
        if comparison.changed_finding_statuses:
            st.markdown("**Changed criterion findings**")
            for change in comparison.changed_finding_statuses:
                previous = (
                    _status_label(change.previous_status.value)
                    if change.previous_status is not None
                    else "None"
                )
                current = (
                    _status_label(change.current_status.value)
                    if change.current_status is not None
                    else "None"
                )
                st.markdown(f"- {change.criterion_id}: {previous} → {current}")
        if comparison.changed_human_resolutions:
            st.markdown("**Changed reviewer decisions**")
            for change in comparison.changed_human_resolutions:
                previous = (
                    _status_label(change.previous_decision.value)
                    if change.previous_decision is not None
                    else "None"
                )
                current = (
                    _status_label(change.current_decision.value)
                    if change.current_decision is not None
                    else "None"
                )
                st.markdown(f"- {change.criterion_id}: {previous} → {current}")
        if comparison.criteria_requiring_decision_review:
            st.warning(
                "Prior decisions must be revisited for: "
                + ", ".join(comparison.criteria_requiring_decision_review)
                + ". ScopeProof never carries acceptance to a changed head."
            )
        st.caption(
            "Ruleset changed between reviews."
            if comparison.ruleset_version_changed
            else "Ruleset unchanged between reviews."
        )
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    diagnostic_by_id = {
        diagnostic.criterion_id: diagnostic
        for diagnostic in bundle.retrieval_diagnostics
    }
    resolution_by_id = {
        resolution.criterion_id: resolution for resolution in bundle.resolutions
    }
    coverage_by_id = {
        row.criterion_id: row for row in criterion_coverage_rows(bundle)
    }
    blocking_criteria = set(bundle.gate.blocking_criteria)
    unresolved_ids = [
        criterion.criterion_id
        for criterion in bundle.criteria
        if criterion.criterion_id not in resolution_by_id
    ]
    recorded_decisions = len(bundle.criteria) - len(unresolved_ids)
    st.markdown("### Decision progress")
    st.caption(
        f"Decisions recorded: {recorded_decisions} of {len(bundle.criteria)}."
    )
    if unresolved_ids:
        st.markdown("### Unresolved criteria queue")
        st.caption(
            "Review candidate evidence and record an explicit human decision for each item."
        )
        for criterion_id in unresolved_ids:
            criterion = next(
                item for item in bundle.criteria if item.criterion_id == criterion_id
            )
            with st.container(border=True):
                st.markdown(f"**{criterion_id}**")
                st.text(criterion.text)
                evidence_status = evidence_status_text(
                    coverage_by_id[criterion_id].evidence_status
                )
                st.caption(
                    f"Candidate evidence: {evidence_status}"
                )
                st.caption(
                    "Observed runtime evidence and the human acceptance decision remain "
                    "separate from static implementation or test candidates."
                )
                st.text(finding_by_id[criterion_id].recommended_action)
                if st.button(
                    f"Review {criterion_id}",
                    key=f"review_unresolved_{criterion_id}",
                ):
                    st.session_state["selected_criterion"] = criterion_id
                    st.rerun()
    else:
        st.success("A current human decision is recorded for every active criterion.")
    st.caption(
        "Evidence status describes deterministic candidates, not correctness. Evidence types "
        "keep implementation, test, and externally recorded runtime observations separate."
    )
    _render_ci_observation_summary(bundle)
    evidence_strength_counts = {
        EvidenceStatus.STRONG_CANDIDATE: 0,
        EvidenceStatus.WEAK_CANDIDATE: 0,
        EvidenceStatus.NO_CANDIDATE: 0,
        EvidenceStatus.ANALYSIS_INCOMPLETE: 0,
    }
    for row in coverage_by_id.values():
        if row.evidence_status in evidence_strength_counts:
            evidence_strength_counts[row.evidence_status] += 1
    st.markdown(
        "**Candidate strength:** "
        f"Strong {evidence_strength_counts[EvidenceStatus.STRONG_CANDIDATE]} · "
        f"Weak {evidence_strength_counts[EvidenceStatus.WEAK_CANDIDATE]} · "
        f"None {evidence_strength_counts[EvidenceStatus.NO_CANDIDATE]} · "
        f"Incomplete {evidence_strength_counts[EvidenceStatus.ANALYSIS_INCOMPLETE]}"
    )
    with st.expander("Filter evidence matrix (optional)", expanded=False):
        status_filter = st.multiselect(
            "Filter evidence status",
            options=list(EvidenceStatus),
            format_func=evidence_status_text,
            key="status_filter",
        )
        priority_filter = st.multiselect(
            "Filter priority",
            options=list(Priority),
            format_func=lambda item: _status_label(item.value),
            key="priority_filter",
        )
        blocking_only = st.checkbox(
            "Show blocking criteria only",
            key="blocking_only",
        )
        evidence_level_filter = st.multiselect(
            "Filter evidence level",
            options=list(EvidenceLevel),
            format_func=lambda item: item.value,
            key="evidence_level_filter",
        )
    matrix = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        coverage = coverage_by_id[criterion.criterion_id]
        if status_filter and coverage.evidence_status not in status_filter:
            continue
        if priority_filter and criterion.priority not in priority_filter:
            continue
        if blocking_only and criterion.criterion_id not in blocking_criteria:
            continue
        if evidence_level_filter and finding.evidence_level not in evidence_level_filter:
            continue
        matrix.append(
            {
                "Criterion": criterion.criterion_id,
                "Requirement": criterion.text,
                "Priority": coverage.priority,
                "Evidence status": evidence_status_text(coverage.evidence_status),
                "Evidence types": ", ".join(coverage.evidence_types) or "None",
                "Reviewer decision": coverage.reviewer_decision,
                "Candidate count": len(finding.evidence_ids),
                "Rationale": finding.reason,
                "Missing evidence": finding.missing_evidence,
                "Recommended action": finding.recommended_action,
            }
        )
    if not matrix:
        st.info("No criteria match the current filters.")
    else:
        st.caption(
            "Each evidence card preserves the criterion, requirement, priority, evidence "
            "status, evidence types, and reviewer decision without hiding mobile content."
        )
        for row in matrix:
            with st.container(border=True):
                st.markdown(f"**Criterion:** {row['Criterion']}")
                st.caption("Requirement")
                st.text(row["Requirement"])
                st.caption(f"Priority: {row['Priority']}")
                st.caption(f"Evidence status: {row['Evidence status']}")
                st.caption(f"Evidence types: {row['Evidence types']}")
                st.caption(f"Reviewer decision: {row['Reviewer decision']}")
                st.caption(f"Candidate count: {row['Candidate count']}")
                st.caption("Why ScopeProof classified it this way")
                st.text(row["Rationale"])
                if row["Missing evidence"]:
                    st.caption("Missing evidence")
                    for missing in row["Missing evidence"]:
                        st.text(missing)
                st.caption("Recommended next action")
                st.code(row["Recommended action"], language=None)
                if st.button(
                    "Inspect this criterion",
                    key=f"inspect_matrix_{row['Criterion']}",
                ):
                    st.session_state["selected_criterion"] = row["Criterion"]
                    st.rerun()

    st.header("4 · Criterion Detail")
    criterion_ids = [criterion.criterion_id for criterion in bundle.criteria]
    selected_criterion = st.session_state.get("selected_criterion")
    if selected_criterion not in criterion_ids:
        st.session_state["selected_criterion"] = default_criterion_detail_id(
            criterion_ids=criterion_ids,
            unresolved_ids=unresolved_ids,
            blocking_ids=blocking_criteria,
            selected_id=selected_criterion,
        )
    selected_id = st.selectbox(
        "Inspect criterion",
        options=criterion_ids,
        key="selected_criterion",
    )
    assert review_state is not None
    criterion_detail_target = (
        review_state.review.review_id,
        review_state.review.head_sha,
        review_state.criteria_revision.number,
        selected_id,
    )
    previous_criterion_detail_target = st.session_state.get(
        "criterion_detail_form_target"
    )
    criterion_detail_target_changed_with_draft = (
        previous_criterion_detail_target is not None
        and previous_criterion_detail_target != criterion_detail_target
        and _clear_criterion_detail_drafts()
    )
    st.session_state["criterion_detail_form_target"] = criterion_detail_target
    if criterion_detail_target_changed_with_draft:
        st.session_state["criterion_detail_form_reset_notice"] = (
            "Unsaved runtime evidence or resolution inputs were cleared because the review "
            f"target changed. Re-enter them for {selected_id} before saving."
        )
        st.rerun()
    criterion_detail_form_reset_notice = st.session_state.pop(
        "criterion_detail_form_reset_notice", None
    )
    if criterion_detail_form_reset_notice is not None:
        st.info(criterion_detail_form_reset_notice)
    criterion_detail_draft_clear_notice = st.session_state.pop(
        "criterion_detail_draft_clear_notice", None
    )
    if criterion_detail_draft_clear_notice is not None:
        st.success(criterion_detail_draft_clear_notice)
    if _criterion_detail_draft_pending():
        st.warning(
            "Pending criterion inputs are not part of the review, local save, or exports. "
            "Submit them through the matching form or clear them before continuing."
        )
        if st.button(
            "Clear pending criterion inputs",
            key="clear_criterion_detail_drafts",
        ):
            _clear_criterion_detail_drafts()
            st.session_state["criterion_detail_draft_clear_notice"] = (
                "Pending criterion inputs cleared without changing the review."
            )
            st.rerun()
    selected_criterion = next(
        criterion for criterion in bundle.criteria if criterion.criterion_id == selected_id
    )
    selected_finding = finding_by_id[selected_id]
    selected_resolution = (
        _status_label(resolution_by_id[selected_id].decision.value)
        if selected_id in resolution_by_id
        else "Unresolved"
    )
    st.markdown("### Selected criterion")
    st.caption("Criterion ID")
    st.code(selected_id, language=None)
    st.caption("Confirmed requirement")
    st.text(selected_criterion.text)
    evidence_column, decision_column = st.columns([3, 2], gap="large")
    selected_coverage = coverage_by_id[selected_id]
    with evidence_column:
        st.markdown("### Evidence")
        st.caption("Evidence status")
        st.text(evidence_status_text(selected_coverage.evidence_status))
        st.caption("Required evidence")
        st.text(selected_criterion.required_evidence_level.value)
        st.caption("Observed evidence")
        st.text(selected_finding.evidence_level.value)
        st.caption("Confidence")
        st.text(selected_finding.confidence_band.value.title())
        st.caption("Candidate count")
        st.text(str(len(selected_finding.evidence_ids)))
        st.caption("Human resolution")
        st.text(selected_resolution)
        st.caption("Finding rationale")
        st.text(selected_finding.reason)
        st.markdown("### How ScopeProof searched")
        selected_diagnostic = diagnostic_by_id.get(selected_id)
        if selected_diagnostic is None:
            st.caption("Retrieval diagnostics were not recorded for this review.")
        else:
            st.caption("Search outcome")
            st.text(_status_label(selected_diagnostic.outcome.value))
            st.caption("Searched terms")
            st.text(", ".join(selected_diagnostic.searched_terms) or "None")
            st.caption("Exact identifiers")
            st.text(", ".join(selected_diagnostic.exact_identifiers) or "None")
            st.caption("Searched evidence types")
            st.text(
                ", ".join(
                    _status_label(item.value)
                    for item in selected_diagnostic.searched_evidence_types
                )
                or "None"
            )
            st.caption("Searched paths")
            st.text(str(len(selected_diagnostic.searched_paths)))
            if selected_diagnostic.searched_paths:
                with st.expander("Inspect searched paths"):
                    st.code("\n".join(selected_diagnostic.searched_paths), language=None)
            st.caption("Retrieval counts")
            st.text(
                "Inspectable lines: "
                f"{selected_diagnostic.inspectable_line_count} · "
                "Term-overlap lines: "
                f"{selected_diagnostic.term_overlap_line_count} · "
                "Below-threshold lines: "
                f"{selected_diagnostic.below_threshold_line_count} · "
                "Accepted candidates: "
                f"{selected_diagnostic.accepted_candidate_count}"
            )
            st.caption(
                "Search diagnostics explain retrieval; they are not evidence that the criterion "
                "is satisfied or missing from the repository."
            )
        if selected_finding.missing_evidence:
            st.markdown("**Missing evidence**")
            for missing in selected_finding.missing_evidence:
                st.text(missing)
        st.markdown("**Recommended next action**")
        st.code(selected_finding.recommended_action, language=None)
        st.markdown("### Candidate evidence")
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
        if not selected_finding.evidence_ids:
            st.caption("No candidate evidence is linked to this provisional finding.")
        selected_items = [
            evidence_by_id[evidence_id] for evidence_id in selected_finding.evidence_ids
        ]
        for group_number, group in enumerate(group_candidate_evidence(selected_items), start=1):
            group_label = (
                f"Evidence group {group_number} · {_status_label(group.evidence_type.value)} · "
                f"{len(group.items)} {'item' if len(group.items) == 1 else 'items'}"
            )
            with st.expander(group_label, expanded=False):
                st.caption("Repository path")
                st.code(group.file_path, language=None)
                for item in group.items:
                    with st.container(border=True):
                        st.caption("Evidence ID")
                        st.code(item.evidence_id, language=None)
                        st.caption(
                            f"Lines {item.line_start}-{item.line_end} · "
                            f"Level {item.evidence_level.value}"
                        )
                        if item.evidence_type.value == "test":
                            st.caption(
                                "Test/eval definition shows intent, not executed verification."
                            )
                        st.code(item.excerpt)
                        if item.context_excerpt:
                            st.caption("Bounded context")
                            st.code(item.context_excerpt)
                        st.markdown(render_artifact_reference_markdown(item.permalink))
                        st.caption("Matching rationale")
                        st.text(item.relevance_reason)
                        st.caption("Matching rule")
                        st.text(item.matching_rule)
                        for limitation in item.limitations:
                            st.caption("Limitation")
                            st.text(limitation)

    with decision_column:
        resolution_save_notice = st.session_state.pop("resolution_save_notice", None)

        st.markdown("### Criterion resolution")
        st.caption("This decision will be recorded for the selected criterion above.")
        st.caption("It does not record final review acceptance.")
        decision_reviewer = st.text_input(
            "Decision reviewer (required)",
            value="Local reviewer",
            key="decision_reviewer",
        )
        decision_reviewer_ready = bool(decision_reviewer.strip())
        if not decision_reviewer_ready:
            st.caption("Decision reviewer is required for an attributable audit event.")
        decision_options = [
            HumanDecision.ACCEPTED,
            HumanDecision.CHANGE_REQUIRED,
            HumanDecision.REJECTED_FINDING,
            HumanDecision.ACCEPTED_EXCEPTION,
            HumanDecision.NOT_IN_SCOPE,
        ]
        decision = st.selectbox(
            "Human decision",
            options=decision_options,
            index=None,
            placeholder="Select a decision",
            format_func=lambda item: _status_label(item.value),
            key="resolution_decision",
        )
        if decision is None:
            st.caption("Select a decision to see its deterministic gate impact.")
        else:
            st.caption(f"Decision impact: {decision_guidance(decision)}")
        resolution_note = st.text_area("Reviewer note", key="resolution_note")
        acceptance_below_required = decision is not None and acceptance_requires_comment(
            decision,
            selected_finding.evidence_level,
            selected_criterion.required_evidence_level,
        )
        if acceptance_below_required:
            st.warning("Accept despite insufficient candidate evidence")
            st.caption(
                f"Required {selected_criterion.required_evidence_level.value} · "
                f"observed {selected_finding.evidence_level.value}"
            )
            st.caption(
                "Add a reviewer note explaining the inspected basis for acceptance. "
                "The note does not raise the evidence level."
            )
        resolution_note_ready = bool(resolution_note.strip()) or not acceptance_below_required
        if resolution_save_notice is not None:
            st.success(resolution_save_notice)
        if st.button(
            "Save resolution",
            key="save_resolution",
            disabled=(
                decision is None
                or not decision_reviewer_ready
                or not resolution_note_ready
            ),
        ):
            if review_state is None:
                st.error("Run analysis before recording a human resolution.")
            else:
                assert decision is not None
                try:
                    event = ResolutionEvent(
                        criterion_id=selected_id,
                        decision=decision,
                        comment=resolution_note,
                        reviewer=decision_reviewer.strip(),
                    )
                    review_state = append_resolution(review_state, event)
                except ValueError:
                    st.error(
                        "Criterion resolution could not be recorded. The review remains "
                        "unchanged. Verify the active review state and try again."
                    )
                else:
                    st.session_state["review_state"] = review_state
                    st.session_state["bundle"] = review_state.bundle
                    bundle = review_state.bundle
                    st.session_state["resolution_form_reset_pending"] = True
                    st.session_state["resolution_save_notice"] = (
                        "Human resolution appended to the local review history."
                    )
                    st.rerun()

        runtime_evidence_save_notice = st.session_state.pop("runtime_evidence_save_notice", None)
        if runtime_evidence_save_notice is not None:
            st.success(runtime_evidence_save_notice)

        with st.expander(
            "Record optional external verification (E3/E4)",
            expanded=False,
        ):
            st.caption(
                "Record a human-supplied observation only. ScopeProof does not run PR code or "
                "infer runtime results. Saving records runtime evidence and its "
                "manual-verification decision atomically."
            )
            st.caption("This record will be attached to the selected criterion.")
            st.caption(
                "Runtime evidence identity is bound automatically to the active review."
            )
            runtime_artifact = st.text_input(
                "Artifact or URL (required)", key="runtime_artifact_reference"
            )
            runtime_scenario = st.text_area("Runtime scenario (required)", key="runtime_scenario")
            runtime_environment = st.text_input("Environment (required)", key="runtime_environment")
            runtime_result = st.text_input("Observed result (required)", key="runtime_result")
            runtime_reviewer = st.text_input("Runtime reviewer (required)", key="runtime_reviewer")
            normalized_runtime_reviewer = runtime_reviewer.strip()
            runtime_limitations = st.text_area(
                "Runtime limitations (optional)", key="runtime_limitations"
            )
            runtime_level = st.selectbox(
                "Runtime evidence level",
                options=[EvidenceLevel.E3, EvidenceLevel.E4],
                key="runtime_evidence_level",
            )
            st.caption(
                "E3 means manually recorded external runtime verification. "
                "E4 means explicit human acceptance. Saving resolves this criterion as manually "
                "verified but does not record final review acceptance. "
                "Artifact, scenario, environment, observed result, and reviewer are required. "
                "Limitations are optional."
            )
            required_runtime_fields = (
                ("Artifact or URL", runtime_artifact),
                ("Runtime scenario", runtime_scenario),
                ("Environment", runtime_environment),
                ("Observed result", runtime_result),
                ("Runtime reviewer", normalized_runtime_reviewer),
            )
            missing_runtime_fields = [
                label for label, value in required_runtime_fields if not value.strip()
            ]
            runtime_evidence_ready = not missing_runtime_fields
            if missing_runtime_fields:
                st.caption(
                    "Complete required fields to enable Save: "
                    + ", ".join(missing_runtime_fields)
                    + "."
                )
            if st.button(
                "Save external verification",
                key="save_runtime_evidence",
                disabled=not runtime_evidence_ready,
            ):
                if review_state is None:
                    st.error("Run analysis before recording external verification.")
                else:
                    try:
                        runtime_evidence_id = str(uuid4())
                        runtime_evidence = RuntimeEvidence(
                            runtime_evidence_id=runtime_evidence_id,
                            repository=review_state.review.repository,
                            pr_number=review_state.review.pr_number,
                            head_sha=review_state.review.head_sha,
                            criterion_id=selected_id,
                            artifact_reference=runtime_artifact,
                            scenario=runtime_scenario,
                            environment=runtime_environment,
                            result=runtime_result,
                            reviewer=normalized_runtime_reviewer,
                            evidence_level=runtime_level,
                            limitations=[
                                line.strip()
                                for line in runtime_limitations.splitlines()
                                if line.strip()
                            ],
                        )
                        verification_event = ResolutionEvent(
                            criterion_id=selected_id,
                            decision=HumanDecision.MANUALLY_VERIFIED,
                            comment=f"Externally observed result: {runtime_result.strip()}",
                            claimed_evidence_level=runtime_level,
                            runtime_evidence_id=runtime_evidence_id,
                            reviewer=normalized_runtime_reviewer,
                        )
                        review_state = append_external_verification(
                            review_state, runtime_evidence, verification_event
                        )
                        st.session_state["review_state"] = review_state
                        st.session_state["bundle"] = review_state.bundle
                        bundle = review_state.bundle
                        st.session_state["runtime_evidence_form_reset_pending"] = True
                        st.session_state["runtime_evidence_save_notice"] = (
                            "External verification and reviewer decision recorded together."
                        )
                        st.rerun()
                    except ValueError:
                        st.error(
                            "External verification could not be saved. Check every required "
                            "field and select E3 or E4."
                        )
        selected_runtime = [
            item for item in bundle.runtime_evidence if item.criterion_id == selected_id
        ]
        with st.expander(
            f"Recorded runtime evidence ({len(selected_runtime)})",
            expanded=False,
        ):
            if not selected_runtime:
                st.caption("No runtime evidence has been recorded for this criterion.")
            for item in selected_runtime:
                recorded_at = item.model_dump(mode="json")["timestamp"]
                with st.container(border=True):
                    if item.runtime_evidence_id is None:
                        st.warning("Legacy unlinked; re-record at the active head")
                    else:
                        st.caption("Runtime evidence ID")
                        st.code(item.runtime_evidence_id, language=None)
                        st.caption("Bound repository and pull request")
                        st.text(f"{item.repository} · PR #{item.pr_number}")
                        st.caption("Bound head")
                        st.code(item.head_sha, language=None)
                    st.caption("Artifact reference")
                    st.markdown(render_artifact_reference_markdown(item.artifact_reference))
                    st.caption("Runtime scenario")
                    st.text(item.scenario)
                    st.caption("Environment")
                    st.text(item.environment)
                    st.caption("Observed result")
                    st.text(item.result)
                    st.caption("Evidence level")
                    st.text(item.evidence_level.value)
                    st.caption("Reviewer")
                    st.text(item.reviewer)
                    st.caption("Recorded at (UTC)")
                    st.text(recorded_at)
                    st.caption("Limitations")
                    if item.limitations:
                        for limitation in item.limitations:
                            st.text(limitation)
                    else:
                        st.caption("No limitations recorded.")

    final_acceptance_save_notice = st.session_state.pop("final_acceptance_save_notice", None)
    final_acceptance_recorded = bool(
        review_state is not None and review_state.review.final_acceptance
    )
    final_acceptance_eligible = bool(
        review_state is not None and can_record_final_acceptance(review_state)
    )
    runtime_reconfirmation_required = bool(
        review_state is not None
        and review_state.bundle is not None
        and "runtime_verification_reconfirmation_required"
        in review_state.bundle.gate.reason_codes
    )

    st.markdown("### Final review acceptance")
    st.caption(
        "This records a review-level acceptance event. It does not resolve individual criteria "
        "or override the deterministic gate. Review every criterion and its evidence before "
        "recording final acceptance."
    )
    if final_acceptance_recorded and runtime_reconfirmation_required:
        st.warning(
            "Revoke final acceptance before recording new E3/E4 verification at the active "
            "head."
        )
    if not final_acceptance_recorded and not final_acceptance_eligible:
        st.caption("Resolve every active criterion before recording final acceptance.")
    if st.button(
        "Record final acceptance",
        key="record_final_acceptance",
        disabled=(
            final_acceptance_recorded
            or not final_acceptance_eligible
            or not decision_reviewer_ready
            or has_pending_review_input
        ),
    ):
        if has_pending_review_input:
            st.error(
                "Final acceptance cannot be recorded while review inputs are pending. "
                "Submit or clear them before trying again."
            )
        elif review_state is None:
            st.error("Run analysis before recording final acceptance.")
        else:
            try:
                review_state = append_resolution(
                    review_state,
                    ResolutionEvent(
                        final_acceptance=True,
                        comment="Reviewer recorded final acceptance",
                        reviewer=decision_reviewer.strip(),
                    ),
                )
            except ValueError:
                st.error(
                    "Final acceptance could not be recorded. The review remains unchanged. "
                    "Verify the active review state and try again."
                )
            else:
                st.session_state["review_state"] = review_state
                st.session_state["bundle"] = review_state.bundle
                bundle = review_state.bundle
                st.session_state["final_acceptance_save_notice"] = (
                    "Final acceptance appended to the local review history."
                )
                st.rerun()
    if final_acceptance_recorded and st.button(
        "Revoke final acceptance",
        key="revoke_final_acceptance",
        disabled=(not decision_reviewer_ready or has_pending_review_input),
    ):
        if has_pending_review_input:
            st.error(
                "Final acceptance cannot be revoked while review inputs are pending. "
                "Submit or clear them before trying again."
            )
        elif review_state is None:
            st.error("Run analysis before revoking final acceptance.")
        else:
            try:
                review_state = append_resolution(
                    review_state,
                    ResolutionEvent(
                        final_acceptance=False,
                        comment="Reviewer revoked final acceptance",
                        reviewer=decision_reviewer.strip(),
                    ),
                )
            except ValueError:
                st.error(
                    "Final acceptance could not be revoked. The review remains unchanged. "
                    "Verify the active review state and try again."
                )
            else:
                st.session_state["review_state"] = review_state
                st.session_state["bundle"] = review_state.bundle
                bundle = review_state.bundle
                st.session_state["final_acceptance_save_notice"] = (
                    "Final acceptance revocation appended to the local review history."
                )
                st.rerun()
    if final_acceptance_save_notice is not None:
        st.success(final_acceptance_save_notice)

    if review_state is not None:
        st.markdown("### Resolution history")
        if review_state.resolution_events:
            st.caption(
                "Current events are the latest recorded inputs for the active revision. "
                "Superseded and prior-revision events remain audit history and do not "
                "independently control the gate."
            )
            event_statuses = resolution_event_statuses(
                review_state.resolution_events,
                active_revision_number=review_state.criteria_revision.number,
            )
            status_labels = {
                ResolutionEventStatus.CURRENT: "Current",
                ResolutionEventStatus.SUPERSEDED: "Superseded",
                ResolutionEventStatus.PRIOR_REVISION: "Prior revision",
            }
            for event, event_status in zip(
                review_state.resolution_events, event_statuses, strict=True
            ):
                target = event.criterion_id or "Final acceptance"
                outcome = (
                    _status_label(event.decision.value)
                    if event.decision
                    else "Recorded"
                    if event.final_acceptance
                    else "Not recorded"
                )
                status = (
                    f"Current · revision {event.criteria_revision_number}"
                    if event_status is ResolutionEventStatus.CURRENT
                    else (
                        f"{status_labels[event_status]} · revision {event.criteria_revision_number}"
                    )
                )
                recorded_at = event.model_dump(mode="json")["timestamp"]
                with st.container(border=True):
                    st.caption("Event status")
                    st.text(status)
                    st.caption("Target")
                    st.code(target, language=None)
                    st.caption("Outcome")
                    st.text(outcome)
                    st.caption("Reviewer comment")
                    st.text(event.comment or "No note provided")
                    st.caption("Reviewer")
                    st.text(event.reviewer)
                    st.caption("Recorded at (UTC)")
                    st.text(recorded_at)
                    if event.claimed_evidence_level is not None:
                        st.caption("Claimed evidence level")
                        st.text(event.claimed_evidence_level.value)
                    if event.decision is HumanDecision.MANUALLY_VERIFIED:
                        st.caption("Runtime evidence link")
                        if event.runtime_evidence_id is None:
                            st.warning("Legacy unlinked; re-record at the active head")
                        else:
                            st.code(event.runtime_evidence_id, language=None)
        else:
            st.caption("No human decisions have been recorded yet.")

    with _locked_review_status_snapshot(
        review_state,
        store=review_store,
        store_available=review_store_available,
        has_pending_review_input=has_pending_review_input,
    ) as status_review_state:
        if status_review_state is not None:
            review_state = status_review_state
            if status_review_state.bundle is not None:
                bundle = status_review_state.bundle
        st.header("5 · Summary & Export")
        review_truth_conflict = bool(
            review_state is not None
            and st.session_state["review_save_conflict"]
            and st.session_state["failed_review_save_fingerprint"]
            == _review_state_fingerprint(review_state)
        )
        review_status = (
            "Refresh required"
            if review_truth_conflict
            else review_status_label(bundle.gate.verdict)
        )
        st.markdown(f"**Review status: {review_status}**")
        if review_truth_conflict:
            st.warning(
                "The persisted review could not be revalidated. Reopen it before relying on the "
                "status or exporting this review."
            )
        if bundle.gate.reason_codes:
            labels = [_status_label(code) for code in bundle.gate.reason_codes]
            st.write("Gate reasons: " + " · ".join(labels))
        guidance = gate_guidance(bundle.gate)
        if guidance:
            st.markdown("### What to do next")
            for message in guidance:
                st.text(message)
        if unresolved_ids:
            if st.button(
                "Review next unresolved criterion",
                key="review_next_unresolved_summary",
                use_container_width=True,
            ):
                st.session_state["selected_criterion"] = unresolved_ids[0]
                st.rerun()
        elif not final_acceptance_recorded:
            st.markdown(
                "[Record final acceptance after reviewing every criterion]"
                "(#final-review-acceptance)"
            )
        else:
            st.caption("Save the validated review locally or download an export below.")
        st.caption(
            f"Head SHA {bundle.review.head_sha} · Ruleset {bundle.review.ruleset_version} · "
            "results are reproducible from the exported review"
        )
    if has_pending_review_input:
        st.warning(
            "Resolve, submit, discard, or clear pending inputs before exporting the "
            "authoritative review."
        )
    export_source = review_state if review_state is not None else bundle
    export_has_provenance = bundle.review.criteria_source_provenance is not None
    expected_export_fingerprint = (
        st.session_state["saved_review_fingerprint"]
        if review_state is not None
        and _review_matches_local_save(review_state)
        else None
    )
    if export_has_provenance:
        markdown_report = deferred_review_export(
            export_source,
            export_markdown,
            store=review_store,
            expected_fingerprint=expected_export_fingerprint,
        )
        json_report = deferred_review_export(
            export_source,
            export_json,
            store=review_store,
            expected_fingerprint=expected_export_fingerprint,
        )
        csv_report = deferred_review_export(
            export_source,
            export_csv,
            store=review_store,
            expected_fingerprint=expected_export_fingerprint,
        )
    else:
        markdown_report = ""
        json_report = ""
        csv_report = ""
    markdown_column, json_column, csv_column = st.columns(3)
    with markdown_column:
        st.download_button(
            "Download Markdown",
            markdown_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.md",
            mime="text/markdown",
            disabled=(
                has_pending_review_input
                or review_truth_conflict
                or not export_has_provenance
            ),
            key="download_markdown",
        )
    with json_column:
        st.download_button(
            "Download JSON",
            json_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.json",
            mime="application/json",
            disabled=(
                has_pending_review_input
                or review_truth_conflict
                or not export_has_provenance
            ),
            key="download_json",
        )
    with csv_column:
        st.download_button(
            "Download CSV",
            csv_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.csv",
            mime="text/csv",
            disabled=(
                has_pending_review_input
                or review_truth_conflict
                or not export_has_provenance
            ),
            key="download_csv",
        )
    if review_save_notice is not None:
        st.success(review_save_notice)
    if review_state is not None:
        _render_local_review_storage(
            review_state,
            store=review_store,
            store_available=review_store_available,
            has_pending_review_input=has_pending_review_input,
            pending_messages=pending_storage_messages,
        )
    if alpha_feedback_mode and st.session_state["alpha_case_id"] is not None:
        with st.expander("Alpha feedback outcome (optional)"):
            st.caption(
                "Record one voluntary outcome for this local case. This is participant "
                "feedback, not proof of correctness, market demand, or repeat use."
            )
            st.code(st.session_state["alpha_case_id"], language=None)
            alpha_store = JsonAlphaCaseStore(default_alpha_case_directory())
            try:
                alpha_record = alpha_store.load(st.session_state["alpha_case_id"])
            except (OSError, ValueError):
                st.warning(
                    "The local alpha case is unavailable. The review and exports remain "
                    "unchanged."
                )
            else:
                if alpha_record.outcome is not None:
                    st.success(
                        "Alpha feedback completed locally: "
                        f"{_status_label(alpha_record.outcome.value)}."
                    )
                else:
                    alpha_outcome = st.selectbox(
                        "Participant outcome",
                        options=list(AlphaOutcome),
                        index=None,
                        placeholder="Select one outcome",
                        format_func=lambda item: _status_label(item.value),
                        key="alpha_outcome",
                    )
                    friction_stage = None
                    if alpha_outcome is AlphaOutcome.CREATED_FRICTION:
                        friction_stage = st.selectbox(
                            "Friction stage",
                            options=list(AlphaFrictionStage),
                            format_func=lambda item: _status_label(item.value),
                            key="alpha_friction_stage",
                        )
                    outcome_notes = st.text_area(
                        "Outcome notes (optional)", key="alpha_outcome_notes"
                    )
                    report_consent = st.checkbox(
                        "Allow this case in an anonymized aggregate report",
                        value=False,
                        key="alpha_report_consent",
                    )
                    quote_consent = st.checkbox(
                        "Allow a direct quotation from the optional notes",
                        value=False,
                        key="alpha_quote_consent",
                    )
                    alpha_outcome_ready = bool(
                        alpha_outcome is not None
                        and review_state is not None
                        and review_matches_local_save
                    )
                    if not review_matches_local_save:
                        st.caption(
                            "Save the current review locally before recording participant "
                            "feedback."
                        )
                    if st.button(
                        "Record alpha outcome",
                        key="record_alpha_outcome",
                        disabled=not alpha_outcome_ready,
                    ):
                        assert review_state is not None
                        assert alpha_outcome is not None
                        try:
                            completed_alpha_record = record_alpha_outcome(
                                alpha_record,
                                review_state=review_state,
                                outcome=alpha_outcome,
                                friction_stage=friction_stage,
                                outcome_notes=outcome_notes.strip() or None,
                                report_consent=report_consent,
                                quote_consent=quote_consent,
                            )
                            alpha_store.update(completed_alpha_record)
                        except (OSError, ValueError):
                            st.error(
                                "Alpha feedback could not be recorded. The review and "
                                "existing alpha case remain unchanged."
                            )
                        else:
                            st.session_state["alpha_outcome_notice"] = (
                                "Alpha feedback outcome recorded locally."
                            )
                            st.rerun()
            alpha_outcome_notice = st.session_state.pop("alpha_outcome_notice", None)
            if alpha_outcome_notice is not None:
                st.success(alpha_outcome_notice)

st.divider()
if bundle is None or bundle.review.input_origin is ReviewInputOrigin.CONSTRUCTED_DEMO:
    st.caption(
        "The bundled CSV export case is a deliberately constructed demo, "
        "not a real production incident."
    )

has_source = st.session_state["snapshot"] is not None
has_criteria = bool(st.session_state["criteria"])
criteria_are_confirmed = (
    st.session_state["criteria_confirmed"]
    and not criteria_edits_pending
    and not has_pending_criteria_source
    and not has_missing_active_provenance
)
has_analysis = bundle is not None
sidebar_ruleset_version = (
    bundle.review.ruleset_version if bundle is not None else RULESET_VERSION
)

with st.sidebar:
    st.markdown("**Review status**")
    if has_source:
        _render_sidebar_step("Complete — Source loaded", "#1-start-review")
    elif has_analysis:
        _render_sidebar_step(
            "Next — Reload source to rerun analysis", "#1-start-review"
        )
    else:
        _render_sidebar_step("Next — Load a public PR or demo", "#1-start-review")
    if has_criteria:
        _render_sidebar_step("Complete — Criteria prepared", "#2-confirm-criteria")
    else:
        _render_sidebar_step("Locked — Prepare at least one criterion")
    if criteria_edits_pending:
        _render_sidebar_step("Next — Confirm updated criteria", "#2-confirm-criteria")
    elif criteria_are_confirmed:
        _render_sidebar_step("Complete — Criteria confirmed", "#2-confirm-criteria")
    elif has_criteria:
        _render_sidebar_step("Next — Confirm criteria", "#2-confirm-criteria")
    else:
        _render_sidebar_step("Locked — Confirm criteria")
    if has_analysis:
        _render_sidebar_step("Complete — Analysis generated", "#3-evidence-matrix")
    elif criteria_are_confirmed:
        _render_sidebar_step(
            "Next — Run deterministic analysis", "#run-deterministic-analysis"
        )
    else:
        _render_sidebar_step("Locked — Run deterministic analysis")
    if has_analysis and has_pending_review_input:
        _render_sidebar_step("Pending — Resolve inputs before export")
    elif has_analysis:
        _render_sidebar_step("Available — Review evidence and export")
    else:
        _render_sidebar_step("Locked — Review and export")
    st.divider()
    st.caption(
        f"Ruleset {sidebar_ruleset_version} · local-first · public repositories only"
    )
