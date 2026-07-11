"""ScopeProof's five-step local Streamlit review workbench."""

from __future__ import annotations

import streamlit as st

from scopeproof_core.criteria.service import parse_criteria, validate_criteria
from scopeproof_core.demo import load_demo_labels, load_demo_snapshot
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.github.client import GitHubClient, GitHubIngestionError
from scopeproof_core.reporting.exporters import export_csv, export_json, export_markdown
from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.schemas.models import (
    Criterion,
    EvidenceLevel,
    HumanDecision,
    HumanResolution,
    Priority,
    Review,
    ReviewBundle,
)
from scopeproof_core.verification.service import build_findings

st.set_page_config(page_title="ScopeProof", page_icon="🔎", layout="wide")

_STATE_DEFAULTS = {
    "snapshot": None,
    "criteria": [],
    "criteria_confirmed": False,
    "bundle": None,
    "active_step": 1,
    "source_text": "",
    "resolutions": [],
}
for state_key, default in _STATE_DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default


def _reset_analysis() -> None:
    st.session_state["criteria_confirmed"] = False
    st.session_state["bundle"] = None
    st.session_state["resolutions"] = []


def _prepare_from_text(text: str) -> None:
    drafts = parse_criteria(text)
    st.session_state["criteria"] = [
        Criterion(criterion_id=draft.criterion_id, text=draft.text) for draft in drafts
    ]
    _reset_analysis()
    st.session_state["active_step"] = 2


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


with st.sidebar:
    st.header("Review workflow")
    steps = [
        "1. Start Review",
        "2. Confirm Criteria",
        "3. Evidence Matrix",
        "4. Criterion Detail",
        "5. Summary & Export",
    ]
    for index, label in enumerate(steps, start=1):
        marker = "●" if index == st.session_state["active_step"] else "○"
        st.markdown(f"{marker} {label}")
    st.divider()
    st.caption("Ruleset 1.0.0 · local-first · public repositories only")

st.title("ScopeProof")
st.subheader("Prove the PR matches the product intent.")
st.markdown(
    "> ScopeProof surfaces auditable candidate evidence. "
    "It does not replace QA or prove correctness."
)
st.caption("No paid LLM API. Deterministic rules. Human acceptance stays visible.")

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
        st.session_state["active_step"] = 2
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
    value=st.session_state["source_text"],
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

st.header("2 · Confirm Criteria")
criteria: list[Criterion] = st.session_state["criteria"]
if not criteria:
    st.info("Load the demo or prepare at least one criterion to continue.")
else:
    edited_criteria: list[Criterion] = []
    for criterion in criteria:
        text_column, priority_column, level_column = st.columns([5, 2, 2])
        with text_column:
            edited_text = st.text_input(
                criterion.criterion_id,
                value=criterion.text,
                key=f"criterion_text_{criterion.criterion_id}",
            )
        with priority_column:
            priority = st.selectbox(
                "Priority",
                options=list(Priority),
                index=list(Priority).index(criterion.priority),
                format_func=lambda item: _status_label(item.value),
                key=f"criterion_priority_{criterion.criterion_id}",
            )
        with level_column:
            level = st.selectbox(
                "Required evidence",
                options=[EvidenceLevel.E1, EvidenceLevel.E2, EvidenceLevel.E3],
                index=[EvidenceLevel.E1, EvidenceLevel.E2, EvidenceLevel.E3].index(
                    criterion.required_evidence_level
                ),
                key=f"criterion_level_{criterion.criterion_id}",
            )
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
        st.session_state["criteria"] = edited_criteria
        st.session_state["criteria_confirmed"] = True
        st.session_state["bundle"] = None
        st.session_state["active_step"] = 3
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
    st.session_state["bundle"] = _analyze()
    st.session_state["active_step"] = 3

bundle: ReviewBundle | None = st.session_state["bundle"]
st.header("3 · Evidence Matrix")
if bundle is None:
    st.info("Confirm criteria and run analysis to generate the evidence matrix.")
else:
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    matrix = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
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
    st.markdown("| Criterion | Requirement | Priority | Status | Evidence | Confidence |")
    st.markdown("|---|---|---|---|---|---|")
    for row in matrix:
        st.markdown(
            f"| {row['Criterion']} | {row['Requirement']} | {row['Priority']} | "
            f"{row['Status']} | {row['Evidence']} | {row['Confidence']} |"
        )
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
    if st.button("Save resolution", key="save_resolution"):
        resolution = HumanResolution(
            criterion_id=selected_id,
            decision=decision,
            comment=resolution_note,
            claimed_evidence_level=manual_level,
        )
        current = [item for item in bundle.resolutions if item.criterion_id != selected_id]
        current.append(resolution)
        st.session_state["resolutions"] = current
        bundle.resolutions = current
        bundle.gate = evaluate_gate(bundle.review, bundle.criteria, bundle.findings, current)
        st.session_state["bundle"] = bundle
        st.success("Human resolution saved in the local review record.")

    st.header("5 · Summary & Export")
    verdict = _status_label(bundle.gate.verdict.value)
    st.markdown(f"## Verdict: **{verdict}**")
    if bundle.gate.reason_codes:
        st.write("Gate reasons: " + ", ".join(bundle.gate.reason_codes))
    st.caption(
        f"Head SHA {bundle.review.head_sha} · Ruleset {bundle.review.ruleset_version} · "
        "results are reproducible from the exported review"
    )
    markdown_report = export_markdown(bundle)
    json_report = export_json(bundle)
    csv_report = export_csv(bundle)
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
