"""Explicit source continuation and volatile authority after fresh contradictions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import streamlit as st

from apps.web.saved_comparison import clear_saved_comparison_selection
from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.github.client import (
    GitHubClient,
    GitHubIngestionError,
    PrivateOrInaccessibleRepository,
)
from scopeproof_core.reviews.source_attachment import (
    SourceAttachmentUnavailable,
    prepare_saved_source_attachment,
    required_source_candidate_paths,
    review_source_context_fingerprint,
    validate_review_source_snapshot,
    validate_source_attachment,
)
from scopeproof_core.schemas.models import ReviewInputOrigin, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore


@dataclass
class SourceAuthorityGuard:
    """A reopened context cannot discard known contradictions by clearing a draft."""

    conflicts: set[str] = field(default_factory=set)

    def allows_context(self, context: str) -> bool:
        return context not in self.conflicts

    def allows(self, state: ReviewState | None) -> bool:
        if state is None:
            return True
        try:
            return self.allows_context(review_source_context_fingerprint(state))
        except ValueError:
            return False

    def block(self, state: ReviewState) -> None:
        self.conflicts.add(review_source_context_fingerprint(state))

    def restore(self, state: ReviewState) -> None:
        self.conflicts.discard(review_source_context_fingerprint(state))


def source_authority_guard() -> SourceAuthorityGuard:
    if "source_authority_guard" not in st.session_state:
        st.session_state["source_authority_guard"] = SourceAuthorityGuard()
    return st.session_state["source_authority_guard"]


def source_authority_check(state: ReviewState | None) -> Callable[[], bool]:
    guard = source_authority_guard()
    if state is None:
        return lambda: True
    try:
        context = review_source_context_fingerprint(state)
    except ValueError:
        return lambda: False
    return lambda: guard.allows_context(context)


def clear_source_attachment() -> None:
    # The observation guard survives hydration/replacement of the same saved context.
    st.session_state["review_source_attachment"] = None


def _block_source_context(state: ReviewState) -> None:
    source_authority_guard().block(state)
    clear_source_attachment()
    st.session_state["snapshot"] = None
    st.session_state["candidate_files"] = []
    clear_saved_comparison_selection()


def validate_current_source_attachment(state: ReviewState | None) -> None:
    attachment = st.session_state.get("review_source_attachment")
    if attachment is None:
        return
    if state is None:
        clear_source_attachment()
        return
    try:
        snapshot = st.session_state.get("snapshot")
        if snapshot is None:
            raise SourceAttachmentUnavailable("Attached source is no longer available.")
        validate_source_attachment(state, attachment, snapshot, st.session_state["candidate_files"])
    except ValueError:
        _block_source_context(state)
        st.session_state["reviewed_source_error"] = (
            "Attached source changed or expired. "
            "Load matching source again or use explicit re-review."
        )


def render_source_attachment(
    state: ReviewState | None,
    *,
    store: JsonReviewStore,
    current_is_saved: bool,
    has_pending_inputs: bool,
    token: str | None,
    research_mode: bool = False,
) -> None:
    if state is None or st.session_state.get("reopened_review_id") != state.review.review_id:
        return
    notice = st.session_state.pop("reviewed_source_notice", None)
    if notice:
        st.success(notice)
    error = st.session_state.pop("reviewed_source_error", None)
    if error:
        st.error(error)
    if not source_authority_guard().allows(state):
        st.warning(
            "Fresh source observations conflict with this saved analysis. Its gate is historical. "
            "Current status, final acceptance and exports require explicit re-review "
            "or matching source."
        )
    try:
        paths = required_source_candidate_paths(state)
    except ValueError as unavailable:
        paths = []
        unavailable_message = str(unavailable)
    else:
        unavailable_message = None
    st.caption(
        "Load source for this saved analysis without replacing its criteria, decisions or gate. "
        "Only recorded unchanged-file paths are restored; this does not refresh the analysis."
    )
    st.text(
        f"Reviewed source: {state.review.repository} PR {state.review.pr_number} "
        f"at {state.review.head_sha}"
    )
    if paths:
        st.caption("Recorded unchanged source paths")
        st.code("\n".join(paths), language=None)
    if unavailable_message:
        st.caption(unavailable_message)
    if not st.button(
        "Load matching reviewed source",
        key="load_reviewed_source",
        disabled=(
            not current_is_saved
            or has_pending_inputs
            or research_mode
            or unavailable_message is not None
        ),
    ):
        return
    fingerprint = JsonReviewStore.state_fingerprint(state)
    origin = state.review.input_origin
    try:
        if origin is ReviewInputOrigin.CONSTRUCTED_DEMO:
            snapshot = load_demo_snapshot()
            validate_review_source_snapshot(state, snapshot, source_origin=origin)
            if paths:
                raise SourceAttachmentUnavailable(
                    "The constructed demo loader does not provide these unchanged source files."
                )
            candidates = []
        else:
            client = GitHubClient(token=token or None)
            url = f"https://github.com/{state.review.repository}/pull/{state.review.pr_number}"
            snapshot = client.fetch_pull_request(url)
            validate_review_source_snapshot(state, snapshot, source_origin=origin)
            candidates = client.fetch_candidate_files(snapshot.repository, snapshot.head_sha, paths)
        attachment = prepare_saved_source_attachment(
            store,
            state,
            snapshot=snapshot,
            candidate_files=candidates,
            source_origin=origin,
            expected_state_fingerprint=fingerprint,
        )
    except SourceAttachmentUnavailable as unavailable:
        if unavailable.observed_conflict:
            _block_source_context(state)
        st.session_state["reviewed_source_error"] = (
            str(unavailable) + " The saved analysis was not changed."
        )
        # A fetch may race a saved-record update. Reconcile at the top of a fresh
        # render, before comparison and criteria widgets have been instantiated.
        st.rerun()
    except PrivateOrInaccessibleRepository as unavailable:
        if unavailable.observed_non_public:
            _block_source_context(state)
        st.session_state["reviewed_source_error"] = (
            "Matching source could not be loaded. The saved analysis was not changed."
        )
        st.rerun()
    except (GitHubIngestionError, OSError, ValueError):
        st.session_state["reviewed_source_error"] = (
            "Matching source could not be loaded. The saved analysis was not changed."
        )
        st.rerun()
    st.session_state["snapshot"] = attachment.snapshot
    st.session_state["candidate_files"] = list(attachment.candidate_files)
    st.session_state["review_source_attachment"] = attachment
    source_authority_guard().restore(state)
    st.session_state["reviewed_source_notice"] = (
        "Matching reviewed source loaded. Saved analysis and decisions were preserved."
    )
    st.rerun()
