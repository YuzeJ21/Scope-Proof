"""ScopeProof's five-step local Streamlit review workbench."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from hashlib import sha256
from pathlib import Path

import streamlit as st

from scopeproof_core.alpha.models import AlphaQualification, ParticipantRole
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
from scopeproof_core.reporting.exporters import export_csv, export_json, export_markdown
from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.reviews.lifecycle import (
    ResolutionEventStatus,
    append_resolution,
    append_runtime_evidence,
    attach_analysis,
    confirm_criteria,
    new_review_state,
    resolution_event_statuses,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    RULESET_VERSION,
    Criterion,
    EvidenceLevel,
    HumanDecision,
    IngestionState,
    Priority,
    PullRequestSnapshot,
    ResolutionEvent,
    Review,
    ReviewBundle,
    ReviewState,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import (
    JsonReviewStore,
    UnsafeReviewStore,
    UnsupportedRecordVersion,
    default_local_review_directory,
)
from scopeproof_core.verification.service import build_findings

st.set_page_config(page_title="ScopeProof", page_icon="🔎", layout="wide")

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
    "review_save_notice": None,
    "replace_unsaved_review_confirmed": False,
    "replace_unsaved_review_reset_pending": False,
    "review_reopen_notice": None,
    "delete_saved_review_confirmed": False,
    "delete_saved_review_reset_pending": False,
    "saved_review_delete_notice": None,
    "source_load_notice": None,
}
for state_key, default in _STATE_DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default


def _reset_analysis() -> None:
    st.session_state["criteria_confirmed"] = False
    st.session_state["bundle"] = None
    st.session_state["resolutions"] = []
    st.session_state["review_state"] = None
    st.session_state["reopened_review_id"] = None
    st.session_state["saved_review_fingerprint"] = None
    st.session_state["review_save_notice"] = None
    st.session_state["replace_unsaved_review_reset_pending"] = True


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
    return sha256(state.model_dump_json().encode("utf-8")).hexdigest()


def _review_matches_local_save(state: ReviewState) -> bool:
    saved_fingerprint = st.session_state["saved_review_fingerprint"]
    return bool(saved_fingerprint and saved_fingerprint == _review_state_fingerprint(state))


def _record_reopened_source_reload(snapshot: PullRequestSnapshot) -> None:
    """Compare a reopened review with the same PR before invalidating its analysis."""
    state: ReviewState | None = st.session_state["review_state"]
    reopened_id: str | None = st.session_state["reopened_review_id"]
    st.session_state["source_reload_notice"] = None
    if (
        state is not None
        and reopened_id == state.review.review_id
        and state.review.repository == snapshot.repository
        and state.review.pr_number == snapshot.pr_number
    ):
        st.session_state["source_reload_notice"] = JsonReviewStore.detect_head_change(
            state, snapshot
        )


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
    st.session_state["review_save_notice"] = None
    st.session_state["replace_unsaved_review_reset_pending"] = True


def _analyze() -> ReviewBundle:
    snapshot = st.session_state["snapshot"]
    criteria = st.session_state["criteria"]
    review = Review(
        repository=snapshot.repository,
        pr_number=snapshot.pr_number,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
        check_state=snapshot.check_state,
        criteria_confirmed=st.session_state["criteria_confirmed"],
        ingestion_state=snapshot.ingestion_state,
        ingestion_warnings=snapshot.warnings,
        skipped_files=snapshot.skipped_files,
    )
    evidence = retrieve_evidence(snapshot, criteria)
    findings = build_findings(criteria, evidence, snapshot.ingestion_state)
    resolutions = st.session_state["resolutions"]
    gate = evaluate_gate(review, criteria, findings, resolutions)
    return ReviewBundle(
        review=review,
        source_text=st.session_state["source_text"],
        criteria=criteria,
        evidence=evidence,
        findings=findings,
        resolutions=resolutions,
        gate=gate,
    )


def _status_label(value: str) -> str:
    return value.replace("_", " ").title()


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
        st.markdown(f"{snapshot.repository} · PR #{snapshot.pr_number}")
        st.caption("Head SHA")
        st.code(snapshot.head_sha, language=None)
        st.caption(
            f"{changed_file_count} changed {changed_file_label} fetched · "
            f"{_status_label(snapshot.ingestion_state.value)} ingestion"
        )


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

st.title("ScopeProof")
st.subheader("Prove the PR matches the product intent.")
st.markdown(
    "> ScopeProof surfaces auditable candidate evidence. "
    "It does not replace QA or prove correctness."
)
st.caption("No paid LLM API. Deterministic rules. Human acceptance stays visible.")

current_review_state: ReviewState | None = st.session_state["review_state"]
has_pending_criteria_draft = _criteria_draft_pending(st.session_state["criteria"])
has_pending_criteria_authoring_draft = _criteria_authoring_draft_pending()
has_pending_requirements_draft = _requirements_draft_pending()
has_pending_criterion_detail_draft = _criterion_detail_draft_pending()
has_pending_review_input = (
    has_pending_criteria_draft
    or has_pending_criteria_authoring_draft
    or has_pending_requirements_draft
    or has_pending_criterion_detail_draft
)
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

storage_directory = default_local_review_directory()
review_store = JsonReviewStore(Path(storage_directory))
try:
    saved_review_ids = review_store.list_review_ids()
except (OSError, UnsafeReviewStore):
    saved_review_ids = []
    review_store_available = False
else:
    review_store_available = True
with st.expander("Reopen saved review", expanded=False):
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
                current = st.session_state["review_state"]
                if current is not None and current.review.review_id == reopen_id:
                    st.session_state["saved_review_fingerprint"] = None
                    st.session_state["saved_review_delete_notice"] = (
                        "Saved review deleted. The open review remains available as "
                        "unsaved work."
                    )
                else:
                    st.session_state["saved_review_delete_notice"] = (
                        "Saved review deleted."
                    )
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

st.header("1 · Start Review")
st.markdown("**PR → Criteria → Evidence → Decisions → Outcome**")
st.caption(
    "Five bounded stages keep source ownership, human confirmation, evidence analysis, "
    "decisions, and outcomes separate."
)
review_path = st.radio(
    "Review path",
    options=["Confirmed public-alpha review", "Technical smoke only"],
    index=1,
    key="review_path",
    help="A technical smoke checks the workflow but is not user validation.",
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
alpha_qualification_ready = True
if review_path == "Confirmed public-alpha review":
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
    alpha_qualification_ready = False
    if (
        pr_url_is_valid
        and requirements_source_url.strip()
        and source_owner_confirmed
        and no_confidential_information
    ):
        try:
            AlphaQualification(
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
else:
    st.info(
        "Technical smoke only — this can check ingestion and reporting, but it is not "
        "user validation and must not be described as a confirmed alpha outcome."
    )
github_token = st.text_input(
    "Optional GitHub token",
    type="password",
    help="Used only in this session to increase free GitHub rate limits. Never exported or saved.",
    key="github_token",
)
load_column, fetch_column = st.columns(2)
with load_column:
    if st.button(
        "Load deliberately constructed demo",
        key="load_demo",
        disabled=replacement_blocked,
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
        _reset_analysis()
        st.rerun()
with fetch_column:
    if st.button(
        "Fetch public PR",
        key="fetch_pr",
        disabled=(
            not pr_url_is_valid
            or not alpha_qualification_ready
            or replacement_blocked
        ),
        use_container_width=True,
    ):
        try:
            snapshot = GitHubClient(token=github_token or None).fetch_pull_request(pr_url)
            _record_reopened_source_reload(snapshot)
            st.session_state["snapshot"] = snapshot
            _reset_analysis()
            st.session_state["source_load_notice"] = (
                "Public PR loaded. Add and confirm criteria before analysis."
            )
            st.rerun()
        except GitHubIngestionError as error:
            st.error(
                f"{error} No review data was changed. Verify that the PR is public and "
                "try again. Use the optional token only if GitHub reports a rate limit."
            )

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

st.caption(
    f"Local review storage: `{storage_directory}`. Records stay under your user-owned "
    "ScopeProof folder; GitHub tokens are never stored."
)

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
    analysis_continuation_placeholder = st.empty()
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
        text_column, priority_column, level_column, actions_column = st.columns([5, 2, 2, 2])
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
    for criterion_id in blank_criterion_ids:
        st.warning(f"{criterion_id}: Criterion text cannot be blank.")
    warnings = validate_criteria(edited_criteria)
    for warning in warnings:
        st.warning(f"{warning.criterion_id}: {warning.message}")
    criteria_edits_pending = _criteria_draft_pending(criteria)
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
    if st.button(
        "Confirm criteria",
        key="confirm_criteria",
        disabled=bool(blank_criterion_ids)
        or (st.session_state["criteria_confirmed"] and not criteria_edits_pending),
    ):
        state: ReviewState | None = st.session_state["review_state"]
        try:
            if state is not None:
                state = revise_criteria(
                    state, edited_criteria, st.session_state["source_text"]
                )
                state = confirm_criteria(state)
        except ValueError:
            st.error(
                "Criteria could not be confirmed. The current review remains unchanged. "
                "Verify the edited criteria and try again."
            )
        else:
            if state is not None:
                st.session_state["review_state"] = state
            st.session_state["criteria"] = edited_criteria
            st.session_state["criteria_confirmed"] = True
            st.session_state["bundle"] = None if state is None else state.bundle
            criteria_edits_pending = False
            st.rerun()

if criteria_edits_pending:
    st.warning(
        "Criteria edits are pending confirmation. Visible evidence and verdict still use "
        "the last confirmed criteria. Confirm the updated set before rerunning analysis."
    )
elif st.session_state["criteria_confirmed"]:
    st.success("Criteria confirmed by the reviewer.")
else:
    st.caption("Analysis remains locked until the criterion set is explicitly confirmed.")

analysis_disabled = not (
    st.session_state["snapshot"] is not None
    and st.session_state["criteria_confirmed"]
    and bool(st.session_state["criteria"])
    and not criteria_edits_pending
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
st.header("3 · Evidence Matrix")
if bundle is None:
    st.info("Confirm criteria and run analysis to generate the evidence matrix.")
else:
    st.caption(
        "Evidence levels: E0 = no candidate found; "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification; E4 = explicit human acceptance. "
        "Levels describe evidence type, not correctness."
    )
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    resolution_by_id = {
        resolution.criterion_id: resolution for resolution in bundle.resolutions
    }
    status_filter = st.multiselect(
        "Filter status",
        options=["evidence_found", "partial", "missing", "needs_review"],
        format_func=_status_label,
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
    blocking_criteria = set(bundle.gate.blocking_criteria)
    matrix = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        if status_filter and finding.status.value not in status_filter:
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
                "Priority": _status_label(criterion.priority.value),
                "Status": _status_label(finding.status.value),
                "Evidence": finding.evidence_level.value,
                "Human resolution": (
                    _status_label(resolution_by_id[criterion.criterion_id].decision.value)
                    if criterion.criterion_id in resolution_by_id
                    else "Unresolved"
                ),
            }
        )
    table_headers = [
        "Criterion",
        "Requirement",
        "Priority",
        "Status",
        "Evidence",
        "Human resolution",
    ]
    table_lines = [
        "| " + " | ".join(table_headers) + " |",
        "|" + "|".join("---" for _ in table_headers) + "|",
    ]
    for row in matrix:
        cells = [
            str(row[header]).replace("|", "\\|").replace("\n", " ")
            for header in table_headers
        ]
        table_lines.append("| " + " | ".join(cells) + " |")
    st.markdown("\n".join(table_lines))
    if not matrix:
        st.info("No criteria match the current filters.")

    st.header("4 · Criterion Detail")
    selected_id = st.selectbox(
        "Inspect criterion",
        options=[criterion.criterion_id for criterion in bundle.criteria],
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
    st.markdown(f"### {selected_id} · {selected_criterion.text}")
    st.markdown(f"**Provisional status:** {_status_label(selected_finding.status.value)}")
    st.markdown(
        f"**Required evidence:** {selected_criterion.required_evidence_level.value} · "
        f"**Observed evidence:** {selected_finding.evidence_level.value} · "
        f"**Confidence:** {selected_finding.confidence_band.value.title()} · "
        f"**Candidates:** {len(selected_finding.evidence_ids)} · "
        f"**Human resolution:** {selected_resolution}"
    )
    st.write(selected_finding.reason)
    if selected_finding.missing_evidence:
        st.markdown("**Missing evidence**")
        for missing in selected_finding.missing_evidence:
            st.markdown(f"- {missing}")
    st.markdown("**Recommended next action**")
    st.info(selected_finding.recommended_action)
    st.code(selected_finding.recommended_action, language=None)
    st.markdown("### Candidate evidence")
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    if not selected_finding.evidence_ids:
        st.caption("No candidate evidence is linked to this provisional finding.")
    for evidence_id in selected_finding.evidence_ids:
        item = evidence_by_id[evidence_id]
        with st.expander(f"{item.file_path}:L{item.line_start} · {item.evidence_type.value}"):
            st.code(item.excerpt)
            st.markdown(f"[Open immutable GitHub evidence]({item.permalink})")
            st.markdown(f"**Matching rationale:** {item.relevance_reason}")
            st.caption(f"Matching rule: {item.matching_rule}")
            for limitation in item.limitations:
                st.caption(f"Limitation: {limitation}")

    runtime_evidence_save_notice = st.session_state.pop(
        "runtime_evidence_save_notice", None
    )

    st.markdown("### Manual runtime evidence")
    st.caption(
        f"This record will be attached to {selected_id} — {selected_criterion.text}. "
        "Record a human-supplied observation only. ScopeProof does not run PR code "
        "or infer runtime results."
    )
    runtime_artifact = st.text_input(
        "Artifact or URL (required)", key="runtime_artifact_reference"
    )
    runtime_scenario = st.text_area(
        "Runtime scenario (required)", key="runtime_scenario"
    )
    runtime_environment = st.text_input(
        "Environment (required)", key="runtime_environment"
    )
    runtime_result = st.text_input(
        "Observed result (required)", key="runtime_result"
    )
    runtime_reviewer = st.text_input(
        "Runtime reviewer (required)", key="runtime_reviewer"
    )
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
        "E4 means explicit human acceptance. Saving this record does not resolve the "
        "criterion or record final review acceptance. "
        "Artifact, scenario, environment, observed result, and reviewer are required. "
        "Limitations are optional."
    )
    if runtime_evidence_save_notice is not None:
        st.success(runtime_evidence_save_notice)
    required_runtime_fields = (
        ("Artifact or URL", runtime_artifact),
        ("Runtime scenario", runtime_scenario),
        ("Environment", runtime_environment),
        ("Observed result", runtime_result),
        ("Runtime reviewer", runtime_reviewer),
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
        "Save manual runtime evidence",
        key="save_runtime_evidence",
        disabled=not runtime_evidence_ready,
    ):
        if review_state is None:
            st.error("Run analysis before recording manual runtime evidence.")
        else:
            try:
                runtime_evidence = RuntimeEvidence(
                    criterion_id=selected_id,
                    artifact_reference=runtime_artifact,
                    scenario=runtime_scenario,
                    environment=runtime_environment,
                    result=runtime_result,
                    reviewer=runtime_reviewer,
                    evidence_level=runtime_level,
                    limitations=[
                        line.strip() for line in runtime_limitations.splitlines() if line.strip()
                    ],
                )
                review_state = append_runtime_evidence(review_state, runtime_evidence)
                st.session_state["review_state"] = review_state
                st.session_state["bundle"] = review_state.bundle
                bundle = review_state.bundle
                st.session_state["runtime_evidence_form_reset_pending"] = True
                st.session_state["runtime_evidence_save_notice"] = (
                    "Manual runtime evidence appended without changing static findings."
                )
                st.rerun()
            except ValueError:
                st.error(
                    "Runtime evidence could not be saved. Check every required field and "
                    "select E3 or E4."
                )
    selected_runtime = [
        item for item in bundle.runtime_evidence if item.criterion_id == selected_id
    ]
    for item in selected_runtime:
        artifact_reference = render_artifact_reference_markdown(item.artifact_reference)
        recorded_at = item.model_dump(mode="json")["timestamp"]
        with st.container(border=True):
            st.markdown(f"{artifact_reference} — {item.scenario}")
            st.markdown(f"**Environment:** {item.environment}")
            st.markdown(f"**Observed result:** {item.result}")
            st.markdown(f"**Evidence level:** {item.evidence_level.value}")
            st.markdown(f"**Reviewer:** {item.reviewer}")
            st.markdown(f"**Recorded at (UTC):** {recorded_at}")
            st.markdown("**Limitations**")
            if item.limitations:
                for limitation in item.limitations:
                    st.markdown(f"- {limitation}")
            else:
                st.caption("No limitations recorded.")

    resolution_save_notice = st.session_state.pop("resolution_save_notice", None)

    decision_reviewer = st.text_input(
        "Decision reviewer (required)",
        value="Local reviewer",
        key="decision_reviewer",
    )
    decision_reviewer_ready = bool(decision_reviewer.strip())
    if not decision_reviewer_ready:
        st.caption("Decision reviewer is required for an attributable audit event.")

    st.markdown(
        "### Criterion resolution\n\n"
        f"This decision will be recorded for {selected_id} — {selected_criterion.text}. "
        "It does not record final review acceptance."
    )
    decision_options = [
        HumanDecision.ACCEPTED,
        HumanDecision.CHANGE_REQUIRED,
        HumanDecision.REJECTED_FINDING,
        HumanDecision.MANUALLY_VERIFIED,
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
    if resolution_save_notice is not None:
        st.success(resolution_save_notice)
    manual_level = None
    if decision is HumanDecision.MANUALLY_VERIFIED:
        manual_level = st.selectbox(
            "Externally verified evidence level",
            options=[EvidenceLevel.E2, EvidenceLevel.E3, EvidenceLevel.E4],
            key="manual_evidence_level",
        )
    manual_verification_ready = (
        decision is not HumanDecision.MANUALLY_VERIFIED or bool(resolution_note.strip())
    )
    if not manual_verification_ready:
        st.caption(
            "Reviewer note is required for manual verification. Describe what was verified."
        )
    if st.button(
        "Save resolution",
        key="save_resolution",
        disabled=(
            decision is None
            or not manual_verification_ready
            or not decision_reviewer_ready
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
                    claimed_evidence_level=manual_level,
                    reviewer=decision_reviewer.strip(),
                )
                review_state = append_resolution(review_state, event)
            except ValueError:
                st.error(
                    "Criterion resolution could not be recorded. The review remains unchanged. "
                    "Verify the active review state and try again."
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

    final_acceptance_save_notice = st.session_state.pop(
        "final_acceptance_save_notice", None
    )
    final_acceptance_recorded = bool(
        review_state is not None and review_state.review.final_acceptance
    )

    st.markdown("### Final review acceptance")
    st.caption(
        "This records a review-level acceptance event. It does not resolve individual criteria "
        "or override the deterministic gate. Review every criterion and its evidence before "
        "recording final acceptance."
    )
    if st.button(
        "Record final acceptance",
        key="record_final_acceptance",
        disabled=final_acceptance_recorded or not decision_reviewer_ready,
    ):
        if review_state is None:
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
                    f"**Current · revision {event.criteria_revision_number}**"
                    if event_status is ResolutionEventStatus.CURRENT
                    else (
                        f"{status_labels[event_status]} · revision "
                        f"{event.criteria_revision_number}"
                    )
                )
                st.markdown(
                    f"- {status} — {target}: {outcome} — "
                    f"{event.comment or 'No note provided'}"
                )
                recorded_at = event.model_dump(mode="json")["timestamp"]
                metadata = f"Reviewer: {event.reviewer} · Recorded at (UTC): {recorded_at}"
                if event.claimed_evidence_level is not None:
                    metadata += (
                        f" · Claimed evidence level: {event.claimed_evidence_level.value}"
                    )
                st.caption(metadata)
        else:
            st.caption("No human decisions have been recorded yet.")

    st.header("5 · Summary & Export")
    st.markdown("### Record the alpha outcome")
    st.caption(
        "After the participant reviews the evidence and decisions, record exactly one "
        "truthful outcome. This does not prove correctness, market demand, or repeat use."
    )
    st.markdown(
        "- `found_useful_gap` — surfaced a useful requirement-evidence gap\n"
        "- `showed_only_known_information` — added no useful new information\n"
        "- `created_friction` — created material friction; record the stage"
    )
    st.code(
        "scopeproof alpha outcome CASE_ID --review-id REVIEW_ID --head-sha HEAD_SHA "
        "--result found_useful_gap",
        language=None,
    )
    st.caption(
        "See docs/alpha/outcome-form.md. Report and quotation permissions are separate "
        "and off by default."
    )
    review_save_notice = st.session_state.pop("review_save_notice", None)
    review_matches_local_save = bool(
        review_state is not None
        and _review_matches_local_save(review_state)
        and not has_pending_review_input
    )
    if review_state is not None:
        st.caption(
            "Current review ID — save this review before using the ID in a future session."
        )
        st.code(review_state.review.review_id, language=None)
        if has_pending_criteria_draft:
            st.caption(
                "Pending criteria edits are not saved or exported. Confirm or discard them "
                "before relying on this review ID."
            )
        if has_pending_criteria_authoring_draft:
            st.caption(
                "Pending add or split criterion inputs are not saved or exported. Submit or "
                "clear them before relying on this review ID."
            )
        if has_pending_requirements_draft:
            st.caption(
                "Pending requirements changes are not saved or exported. Prepare or discard "
                "them before relying on this review ID."
            )
        if has_pending_criterion_detail_draft:
            st.caption(
                "Pending criterion-detail inputs are not saved or exported. Submit or clear "
                "them before relying on this review ID."
            )
        if review_matches_local_save:
            st.caption("Saved locally — current review matches the last local save.")
        elif not has_pending_review_input:
            st.caption("Unsaved changes — save locally before relying on this review ID.")
    if review_state is not None and not review_store_available:
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
    if review_state is not None and st.button(
        "Save local review",
        key="save_review",
        disabled=(
            review_matches_local_save
            or has_pending_review_input
            or not review_store_available
        ),
    ):
        try:
            review_store.save(review_state)
        except (OSError, ValueError):
            st.error(
                "The review could not be saved locally. The current review remains open "
                "as unsaved work. Verify the local review directory and review integrity, "
                "then try again."
            )
        else:
            st.session_state["saved_review_fingerprint"] = _review_state_fingerprint(
                review_state
            )
            st.session_state["review_save_notice"] = (
                f"Review saved locally. ID: {review_state.review.review_id}."
            )
            st.rerun()
    if review_save_notice is not None:
        st.success(review_save_notice)
    verdict = _status_label(bundle.gate.verdict.value)
    st.markdown(f"## Verdict: **{verdict}**")
    if bundle.gate.reason_codes:
        labels = [_status_label(code) for code in bundle.gate.reason_codes]
        st.write("Gate reasons: " + " · ".join(labels))
    guidance = gate_guidance(bundle.gate)
    if guidance:
        st.markdown("### What to do next")
        for message in guidance:
            st.markdown(f"- {message}")
    st.caption(
        f"Head SHA {bundle.review.head_sha} · Ruleset {bundle.review.ruleset_version} · "
        "results are reproducible from the exported review"
    )
    export_source = review_state if review_state is not None else bundle
    markdown_report = export_markdown(export_source)
    json_report = export_json(export_source)
    csv_report = export_csv(export_source)
    markdown_column, json_column, csv_column = st.columns(3)
    with markdown_column:
        st.download_button(
            "Download Markdown",
            markdown_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.md",
            mime="text/markdown",
            disabled=has_pending_review_input,
        )
    with json_column:
        st.download_button(
            "Download JSON",
            json_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.json",
            mime="application/json",
            disabled=has_pending_review_input,
        )
    with csv_column:
        st.download_button(
            "Download CSV",
            csv_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.csv",
            mime="text/csv",
            disabled=has_pending_review_input,
        )

st.divider()
st.caption(
    "The bundled CSV export case is a deliberately constructed demo, "
    "not a real production incident."
)

has_source = st.session_state["snapshot"] is not None
has_criteria = bool(st.session_state["criteria"])
criteria_are_confirmed = (
    st.session_state["criteria_confirmed"] and not criteria_edits_pending
)
has_analysis = bundle is not None
sidebar_ruleset_version = (
    bundle.review.ruleset_version if bundle is not None else RULESET_VERSION
)

with st.sidebar:
    st.header("Review status")
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
