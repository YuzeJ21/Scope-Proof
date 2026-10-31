"""Read-only recorded decisions, kept separate from automatic candidate deltas."""

from __future__ import annotations

import streamlit as st

from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.reviews.decision_context_comparison import (
    DECISION_CONTEXT_COMPARISON_BOUNDARY,
    CriterionDecisionContext,
    DecisionContextComparison,
)


def _render_row(row: CriterionDecisionContext, distinction: str) -> None:
    st.caption("Criterion and recorded distinction")
    st.text(row.criterion_id)
    st.text(distinction.replace("_", " "))
    resolution = row.resolution
    if resolution is None:
        st.caption("No criterion decision recorded in this snapshot.")
    else:
        st.caption("Recorded decision")
        st.text(resolution.decision.value)
        st.caption("Decision note")
        st.text(resolution.comment or "No note recorded.")
        st.caption("Asserted decision reviewer")
        st.text(resolution.reviewer)
        st.caption("Decision recorded at")
        st.text(resolution.timestamp.isoformat())
        st.caption("Claimed decision evidence level")
        st.text(
            resolution.claimed_evidence_level.value
            if resolution.claimed_evidence_level else "Not claimed"
        )
        st.caption("Decision evidence reference")
        if resolution.evidence_url:
            st.markdown(render_artifact_reference_markdown(resolution.evidence_url))
        else:
            st.caption("Not recorded")
        st.caption("Decision runtime ID")
        st.code(resolution.runtime_evidence_id or "Not recorded", language=None, wrap_lines=True)
    st.caption("Runtime relationship")
    st.text({
        "linked": "Explicit runtime ID link",
        "legacy_unlinked": "Legacy unlinked; relationship to an observation unknown",
        "no_link": "No explicit runtime ID link",
    }[row.runtime_link_status])
    if not row.runtime_evidence:
        st.caption("No runtime observations recorded for this criterion.")
    for item in row.runtime_evidence:
        with st.container(border=True):
            st.caption("Retained recorded runtime observation")
            st.caption("Runtime ID")
            st.code(item.runtime_evidence_id or "Legacy unlinked", language=None, wrap_lines=True)
            st.caption("Bound repository and PR")
            st.text(
                f"{item.repository} · PR #{item.pr_number}"
                if item.repository is not None else "Not recorded; legacy unlinked"
            )
            st.caption("Bound head")
            st.code(item.head_sha or "Not recorded", language=None, wrap_lines=True)
            st.caption("Artifact reference")
            st.markdown(render_artifact_reference_markdown(item.artifact_reference))
            for label, value in (
                ("Recorded scenario", item.scenario),
                ("Recorded environment", item.environment),
                ("Recorded result", item.result),
                ("Asserted observation reviewer", item.reviewer),
                ("Recorded evidence level", item.evidence_level.value),
                ("Observation recorded at", item.timestamp.isoformat()),
            ):
                st.caption(label)
                st.text(value)
            st.caption("Recorded limitations")
            for limitation in item.limitations:
                st.text(limitation)
            if not item.limitations:
                st.caption("None recorded (not a completeness claim).")


def render_decision_context_comparison(context: DecisionContextComparison | None) -> None:
    st.markdown("### Recorded decision and runtime context")
    st.caption(DECISION_CONTEXT_COMPARISON_BOUNDARY)
    st.caption(
        "Latest criterion decisions and retained runtime records only; review-level final "
        "acceptance and full decision-event history are outside this section."
    )
    if context is None:
        st.info("Decision context was not included in this older comparison.")
        return
    changes = context.record_changes
    if not changes:
        st.info("No criterion decisions or runtime observations recorded on either side.")
    st.markdown(
        f"Changed recorded context: {sum(r.kind == 'recorded_context_changed' for r in changes)} · "
        f"Only previous: {sum(r.kind == 'only_previous' for r in changes)} · "
        f"Only current: {sum(r.kind == 'only_current' for r in changes)} · "
        "Identical recorded context: "
        f"{sum(r.kind == 'identical_recorded_context' for r in changes)}"
    )
    for side in ("previous", "current"):
        snapshot = getattr(context, side)
        with st.expander(f"{side.title()} decision context"):
            st.caption("Owning saved analysis")
            st.text(f"{snapshot.repository} · PR #{snapshot.pr_number}")
            st.text(snapshot.review_id)
            st.text(f"Criteria revision: {snapshot.criteria_revision_number}")
            st.caption("Owning head")
            st.code(snapshot.head_sha, language=None, wrap_lines=True)
            st.caption("Recorded input origin")
            st.text(snapshot.input_origin.value)
            provenance = snapshot.criteria_source_provenance
            for label, value in (
                ("Criteria source", provenance.source_uri),
                ("Criteria source revision", provenance.source_revision or "Not recorded"),
                ("Criteria confirmed by", provenance.confirmed_by),
                ("Criteria confirmed at", provenance.confirmed_at.isoformat()),
            ):
                st.caption(label)
                st.text(value)
            st.caption("Source-text digest")
            st.code(provenance.source_text_sha256, language=None, wrap_lines=True)
            st.caption("Normalized criteria digest")
            st.code(provenance.normalized_criteria_sha256, language=None, wrap_lines=True)
            for change in changes:
                row = getattr(change, side)
                if row is not None:
                    _render_row(row, change.kind)
