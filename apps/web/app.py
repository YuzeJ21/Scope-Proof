"""ScopeProof's five-step local Streamlit review workbench."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import streamlit as st

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
from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.reviews.lifecycle import (
    ResolutionEventStatus,
    append_resolution,
    append_runtime_evidence,
    confirm_criteria,
    new_review_state,
    resolution_event_statuses,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    Criterion,
    EvidenceLevel,
    HumanDecision,
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


if st.session_state["replace_unsaved_review_reset_pending"]:
    st.session_state["replace_unsaved_review_confirmed"] = False
    st.session_state["replace_unsaved_review_reset_pending"] = False

st.title("ScopeProof")
st.subheader("Prove the PR matches the product intent.")
st.markdown(
    "> ScopeProof surfaces auditable candidate evidence. "
    "It does not replace QA or prove correctness."
)
st.caption("No paid LLM API. Deterministic rules. Human acceptance stays visible.")

current_review_state: ReviewState | None = st.session_state["review_state"]
has_unsaved_review = bool(
    current_review_state is not None
    and not _review_matches_local_save(current_review_state)
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

storage_directory = default_local_review_directory()
review_store = JsonReviewStore(Path(storage_directory))
with st.expander("Reopen saved review", expanded=False):
    reopen_id = st.text_input("Review ID", key="reopen_review_id")
    if st.button(
        "Reopen local review",
        key="reopen_review",
        disabled=not reopen_id.strip() or replacement_blocked,
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
review_reopen_notice = st.session_state.pop("review_reopen_notice", None)
if review_reopen_notice is not None:
    st.success(review_reopen_notice)

st.header("1 · Start Review")
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
        disabled=not pr_url_is_valid or replacement_blocked,
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
            st.error(str(error))

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

requirements_text = st.text_area(
    "Product requirements or acceptance criteria",
    height=150,
    key="requirements_input",
    help="Use one independently judgeable behavior per line. ScopeProof will not invent criteria.",
)
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
        or replacement_blocked
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
if not criteria:
    st.info("Load the demo or prepare at least one criterion to continue.")
else:
    st.caption(
        "Evidence levels set the minimum proof needed for each criterion: "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification. Static PR analysis can produce "
        "only E1 or E2."
    )
    new_criterion_text = st.text_input("Add criterion", key="new_criterion_text")
    if st.button(
        "Add criterion",
        key="add_criterion_ui",
        disabled=not new_criterion_text.strip() or replacement_blocked,
    ):
        st.session_state["criteria"] = add_criterion(criteria, new_criterion_text)
        _reset_analysis()
        st.success("Criterion added. Confirm the updated set before analysis.")
        st.rerun()
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
            or replacement_blocked
        ),
    ):
        split_texts = [line.strip() for line in split_text.splitlines() if line.strip()]
        st.session_state["criteria"] = split_criterion(criteria, split_target, split_texts)
        _reset_analysis()
        st.success("Criterion split. Confirm the updated set before analysis.")
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
                st.session_state["criteria"] = remove_criterion(criteria, criterion.criterion_id)
                _reset_analysis()
                st.success("Criterion removed. Confirm the updated set before analysis.")
                st.rerun()
            if position > 0 and st.button(
                f"Move {criterion.criterion_id} up",
                key=f"move_up_{criterion.criterion_id}",
                disabled=replacement_blocked,
            ):
                order = [item.criterion_id for item in criteria]
                order[position - 1], order[position] = order[position], order[position - 1]
                st.session_state["criteria"] = reorder_criteria(criteria, order)
                _reset_analysis()
                st.success("Criterion order changed. Confirm the updated set before analysis.")
                st.rerun()
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
    criteria_edits_pending = bool(blank_criterion_ids) or edited_criteria != criteria
    if st.button(
        "Confirm criteria",
        key="confirm_criteria",
        disabled=bool(blank_criterion_ids),
    ):
        state: ReviewState | None = st.session_state["review_state"]
        if state is not None:
            state = revise_criteria(state, edited_criteria, st.session_state["source_text"])
            state = confirm_criteria(state)
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
)
if st.button("Run deterministic analysis", key="run_analysis", disabled=analysis_disabled):
    bundle = _analyze()
    st.session_state["bundle"] = bundle
    st.session_state["review_state"] = new_review_state(bundle)
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

    if st.session_state.pop("runtime_evidence_form_reset_pending", False):
        st.session_state["runtime_artifact_reference"] = ""
        st.session_state["runtime_scenario"] = ""
        st.session_state["runtime_environment"] = ""
        st.session_state["runtime_result"] = ""
        st.session_state["runtime_reviewer"] = ""
        st.session_state["runtime_limitations"] = ""
        st.session_state["runtime_evidence_level"] = EvidenceLevel.E3
    runtime_evidence_save_notice = st.session_state.pop(
        "runtime_evidence_save_notice", None
    )

    st.markdown("### Manual runtime evidence")
    st.caption(
        f"This record will be attached to {selected_id} — {selected_criterion.text}."
    )
    st.caption(
        "Record a human-supplied observation only. ScopeProof does not run PR code "
        "or infer runtime results."
    )
    runtime_artifact = st.text_input("Artifact or URL", key="runtime_artifact_reference")
    runtime_scenario = st.text_area("Runtime scenario", key="runtime_scenario")
    runtime_environment = st.text_input("Environment", key="runtime_environment")
    runtime_result = st.text_input("Observed result", key="runtime_result")
    runtime_reviewer = st.text_input("Runtime reviewer", key="runtime_reviewer")
    runtime_limitations = st.text_area("Runtime limitations", key="runtime_limitations")
    runtime_level = st.selectbox(
        "Runtime evidence level",
        options=[EvidenceLevel.E3, EvidenceLevel.E4],
        key="runtime_evidence_level",
    )
    st.caption(
        "E3 means manually recorded external runtime verification. "
        "E4 means explicit human acceptance. Saving this record does not resolve the "
        "criterion or record final review acceptance."
    )
    st.caption(
        "Artifact, scenario, environment, observed result, and reviewer are required. "
        "Limitations are optional."
    )
    if runtime_evidence_save_notice is not None:
        st.success(runtime_evidence_save_notice)
    runtime_evidence_ready = all(
        value.strip()
        for value in (
            runtime_artifact,
            runtime_scenario,
            runtime_environment,
            runtime_result,
            runtime_reviewer,
        )
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
        st.markdown(
            f"- [{item.artifact_reference}]({item.artifact_reference}) — {item.scenario} "
            f"({item.environment}: {item.result}; {item.evidence_level.value})"
        )

    if st.session_state.pop("resolution_form_reset_pending", False):
        st.session_state["resolution_decision"] = None
        st.session_state["resolution_note"] = ""
        st.session_state.pop("manual_evidence_level", None)
    resolution_save_notice = st.session_state.pop("resolution_save_notice", None)

    st.markdown("### Criterion resolution")
    st.caption(
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
    if st.button(
        "Save resolution",
        key="save_resolution",
        disabled=decision is None,
    ):
        if review_state is None:
            st.error("Run analysis before recording a human resolution.")
        else:
            assert decision is not None
            event = ResolutionEvent(
                criterion_id=selected_id,
                decision=decision,
                comment=resolution_note,
                claimed_evidence_level=manual_level,
            )
            review_state = append_resolution(review_state, event)
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
        disabled=final_acceptance_recorded,
    ):
        if review_state is None:
            st.error("Run analysis before recording final acceptance.")
        else:
            review_state = append_resolution(
                review_state,
                ResolutionEvent(
                    final_acceptance=True,
                    comment="Reviewer recorded final acceptance",
                ),
            )
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
        else:
            st.caption("No human decisions have been recorded yet.")

    st.header("5 · Summary & Export")
    review_save_notice = st.session_state.pop("review_save_notice", None)
    review_matches_local_save = bool(
        review_state is not None and _review_matches_local_save(review_state)
    )
    if review_state is not None:
        st.caption(
            "Current review ID — save this review before using the ID in a future session."
        )
        st.code(review_state.review.review_id, language=None)
        if review_matches_local_save:
            st.caption("Saved locally — current review matches the last local save.")
        else:
            st.caption("Unsaved changes — save locally before relying on this review ID.")
    if review_state is not None and st.button(
        "Save local review",
        key="save_review",
        disabled=review_matches_local_save,
    ):
        review_store.save(review_state)
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
        )
    with json_column:
        st.download_button(
            "Download JSON",
            json_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.json",
            mime="application/json",
        )
    with csv_column:
        st.download_button(
            "Download CSV",
            csv_report,
            file_name=f"scopeproof-pr-{bundle.review.pr_number}.csv",
            mime="text/csv",
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

with st.sidebar:
    st.header("Review status")
    st.markdown(
        "Complete — Source loaded"
        if has_source
        else (
            "Next — Reload source to rerun analysis"
            if has_analysis
            else "Next — Load a public PR or demo"
        )
    )
    st.markdown(
        "Complete — Criteria prepared"
        if has_criteria
        else "Locked — Prepare at least one criterion"
    )
    st.markdown(
        "Next — Confirm updated criteria"
        if criteria_edits_pending
        else (
            "Complete — Criteria confirmed"
            if criteria_are_confirmed
            else ("Next — Confirm criteria" if has_criteria else "Locked — Confirm criteria")
        )
    )
    st.markdown(
        "Complete — Analysis generated"
        if has_analysis
        else (
            "Next — Run deterministic analysis"
            if criteria_are_confirmed
            else "Locked — Run deterministic analysis"
        )
    )
    st.markdown(
        "Complete — Review and export available"
        if has_analysis
        else "Locked — Review and export"
    )
    st.divider()
    st.caption("Ruleset 1.0.0 · local-first · public repositories only")
