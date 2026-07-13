"""ScopeProof's five-step local Streamlit review workbench."""

from __future__ import annotations

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
from scopeproof_core.gates.guidance import gate_guidance
from scopeproof_core.github.client import GitHubClient, GitHubIngestionError
from scopeproof_core.reporting.exporters import export_csv, export_json, export_markdown
from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    append_runtime_evidence,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    Criterion,
    EvidenceLevel,
    HumanDecision,
    Priority,
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
}
for state_key, default in _STATE_DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default


def _reset_analysis() -> None:
    st.session_state["criteria_confirmed"] = False
    st.session_state["bundle"] = None
    st.session_state["resolutions"] = []
    st.session_state["review_state"] = None


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


st.title("ScopeProof")
st.subheader("Prove the PR matches the product intent.")
st.markdown(
    "> ScopeProof surfaces auditable candidate evidence. "
    "It does not replace QA or prove correctness."
)
st.caption("No paid LLM API. Deterministic rules. Human acceptance stays visible.")

storage_directory = default_local_review_directory()
review_store = JsonReviewStore(Path(storage_directory))
st.markdown("### Reopen saved review")
reopen_id = st.text_input("Review ID", key="reopen_review_id")
if st.button("Reopen local review", key="reopen_review", disabled=not reopen_id.strip()):
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
        st.success("Review reopened from local storage after validation.")

st.header("1 · Start Review")
pr_url = st.text_input(
    "Public GitHub pull request URL",
    placeholder="https://github.com/owner/repository/pull/123",
    key="pr_url",
)
github_token = st.text_input(
    "Optional GitHub token",
    type="password",
    help="Used only in this session to increase free GitHub rate limits. Never exported or saved.",
    key="github_token",
)
load_column, fetch_column = st.columns(2)
with load_column:
    if st.button("Load deliberately constructed demo", key="load_demo", use_container_width=True):
        labels = load_demo_labels()
        st.session_state["snapshot"] = load_demo_snapshot()
        st.session_state["source_text"] = labels["source_text"]
        st.session_state["requirements_input"] = labels["source_text"]
        st.session_state["criteria"] = [
            Criterion.model_validate(item) for item in labels["criteria"]
        ]
        _reset_analysis()
with fetch_column:
    if st.button(
        "Fetch public PR",
        key="fetch_pr",
        disabled=not bool(pr_url.strip()),
        use_container_width=True,
    ):
        try:
            st.session_state["snapshot"] = GitHubClient(
                token=github_token or None
            ).fetch_pull_request(pr_url)
            _reset_analysis()
            st.success("Public PR loaded. Add and confirm criteria before analysis.")
        except GitHubIngestionError as error:
            st.error(str(error))

requirements_text = st.text_area(
    "Product requirements or acceptance criteria",
    height=150,
    key="requirements_input",
    help="Use one independently judgeable behavior per line. ScopeProof will not invent criteria.",
)
if st.button(
    "Prepare criteria",
    key="prepare_criteria",
    disabled=not bool(requirements_text.strip()),
):
    st.session_state["source_text"] = requirements_text
    _prepare_from_text(requirements_text)

st.caption(
    f"Local review storage: `{storage_directory}`. Records stay under your user-owned "
    "ScopeProof folder; GitHub tokens are never stored."
)

st.header("2 · Confirm Criteria")
criteria: list[Criterion] = st.session_state["criteria"]
if not criteria:
    st.info("Load the demo or prepare at least one criterion to continue.")
else:
    new_criterion_text = st.text_input("Add criterion", key="new_criterion_text")
    if st.button(
        "Add criterion",
        key="add_criterion_ui",
        disabled=not new_criterion_text.strip(),
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
        disabled=len([line for line in split_text.splitlines() if line.strip()]) < 2,
    ):
        split_texts = [line.strip() for line in split_text.splitlines() if line.strip()]
        st.session_state["criteria"] = split_criterion(criteria, split_target, split_texts)
        _reset_analysis()
        st.success("Criterion split. Confirm the updated set before analysis.")
        st.rerun()
    edited_criteria: list[Criterion] = []
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
                f"Remove {criterion.criterion_id}", key=f"remove_{criterion.criterion_id}"
            ):
                st.session_state["criteria"] = remove_criterion(criteria, criterion.criterion_id)
                _reset_analysis()
                st.success("Criterion removed. Confirm the updated set before analysis.")
                st.rerun()
            if position > 0 and st.button(
                f"Move {criterion.criterion_id} up", key=f"move_up_{criterion.criterion_id}"
            ):
                order = [item.criterion_id for item in criteria]
                order[position - 1], order[position] = order[position], order[position - 1]
                st.session_state["criteria"] = reorder_criteria(criteria, order)
                _reset_analysis()
                st.success("Criterion order changed. Confirm the updated set before analysis.")
                st.rerun()
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
    for warning in warnings:
        st.warning(f"{warning.criterion_id}: {warning.message}")
    if st.button(
        "Confirm criteria",
        key="confirm_criteria",
        disabled=any(not item.text.strip() for item in edited_criteria),
    ):
        state: ReviewState | None = st.session_state["review_state"]
        if state is not None:
            state = revise_criteria(state, edited_criteria, st.session_state["source_text"])
            state = confirm_criteria(state)
            st.session_state["review_state"] = state
        st.session_state["criteria"] = edited_criteria
        st.session_state["criteria_confirmed"] = True
        st.session_state["bundle"] = None if state is None else state.bundle
        st.success("Criteria confirmed. Analysis can now begin.")

if st.session_state["criteria_confirmed"]:
    st.success("Criteria confirmed by the reviewer.")
else:
    st.caption("Analysis remains locked until the criterion set is explicitly confirmed.")

analysis_disabled = not (
    st.session_state["snapshot"] is not None
    and st.session_state["criteria_confirmed"]
    and bool(st.session_state["criteria"])
)
if st.button("Run deterministic analysis", key="run_analysis", disabled=analysis_disabled):
    bundle = _analyze()
    st.session_state["bundle"] = bundle
    st.session_state["review_state"] = new_review_state(bundle)

review_state: ReviewState | None = st.session_state["review_state"]
bundle: ReviewBundle | None = review_state.bundle if review_state else st.session_state["bundle"]
st.header("3 · Evidence Matrix")
if bundle is None:
    st.info("Confirm criteria and run analysis to generate the evidence matrix.")
else:
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
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
    matrix = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        if status_filter and finding.status.value not in status_filter:
            continue
        if priority_filter and criterion.priority not in priority_filter:
            continue
        matrix.append(
            {
                "Criterion": criterion.criterion_id,
                "Requirement": criterion.text,
                "Priority": _status_label(criterion.priority.value),
                "Status": _status_label(finding.status.value),
                "Evidence": finding.evidence_level.value,
                "Confidence": finding.confidence_band.value.title(),
            }
        )
    table_headers = ["Criterion", "Requirement", "Priority", "Status", "Evidence", "Confidence"]
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
    for row in matrix:
        st.markdown(f"**{row['Criterion']} — {row['Status']}** · {row['Requirement']}")

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
    st.markdown(f"### {selected_id} · {selected_criterion.text}")
    st.markdown(f"**Provisional status:** {_status_label(selected_finding.status.value)}")
    st.write(selected_finding.reason)
    if selected_finding.missing_evidence:
        st.markdown("**Missing evidence**")
        for missing in selected_finding.missing_evidence:
            st.markdown(f"- {missing}")
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    for evidence_id in selected_finding.evidence_ids:
        item = evidence_by_id[evidence_id]
        with st.expander(f"{item.file_path}:L{item.line_start} · {item.evidence_type.value}"):
            st.code(item.excerpt)
            st.markdown(f"[Open immutable GitHub evidence]({item.permalink})")
            st.write(item.relevance_reason)
            for limitation in item.limitations:
                st.caption(f"Limitation: {limitation}")

    st.markdown("### Manual runtime evidence")
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
        "Artifact, scenario, environment, observed result, and reviewer are required. "
        "Limitations are optional."
    )
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
                st.success("Manual runtime evidence appended without changing static findings.")
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
    resolution_note = st.text_area("Reviewer note", key="resolution_note")
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
            st.success("Human resolution appended to the local review history.")

    if st.button("Record final acceptance", key="record_final_acceptance"):
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
            st.success("Final acceptance appended to the local review history.")

    if review_state is not None:
        st.markdown("### Resolution history")
        if review_state.resolution_events:
            for event in review_state.resolution_events:
                target = event.criterion_id or "Final acceptance"
                outcome = event.decision.value if event.decision else str(event.final_acceptance)
                st.markdown(f"- {target}: {outcome} — {event.comment or 'No note provided'}")
        else:
            st.caption("No human decisions have been recorded yet.")

    st.header("5 · Summary & Export")
    if review_state is not None and st.button("Save local review", key="save_review"):
        review_store.save(review_state)
        st.success("Review saved locally.")
    verdict = _status_label(bundle.gate.verdict.value)
    st.markdown(f"## Verdict: **{verdict}**")
    if bundle.gate.reason_codes:
        st.write("Gate reasons: " + ", ".join(bundle.gate.reason_codes))
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
criteria_are_confirmed = st.session_state["criteria_confirmed"]
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
        "Complete — Criteria confirmed"
        if criteria_are_confirmed
        else ("Next — Confirm criteria" if has_criteria else "Locked — Confirm criteria")
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
