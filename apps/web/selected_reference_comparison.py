"""Read-only recorded reference context in the saved re-review journey."""

import streamlit as st

from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.reviews.selected_reference_comparison import (
    SELECTED_REFERENCE_COMPARISON_BOUNDARY,
    SelectedReferenceComparison,
)


def render_selected_reference_comparison(context: SelectedReferenceComparison | None) -> None:
    st.markdown("#### Reviewer-selected reference comparison")
    st.caption(SELECTED_REFERENCE_COMPARISON_BOUNDARY)
    if context is None:
        st.info("Selected-reference context was not included in this older comparison.")
        return
    counts = context.change_counts
    st.markdown(
        f"**Recorded reference context:** Identical record: {counts.identical_record} · "
        f"Only previous: {counts.only_previous} · Only current: {counts.only_current}"
    )
    if not context.previous and not context.current:
        st.caption("No selected references recorded in either analysis.")
    for change in context.record_changes:
        reference = change.current or change.previous
        with st.expander(
            f"{change.kind.replace('_', ' ').title()} · {reference.criterion_id} · "
            f"{reference.file_path}:{reference.line_number}"
        ):
            for label, item in (
                ("Previous selected reference", change.previous),
                ("Current selected reference", change.current),
            ):
                if item is None:
                    continue
                st.markdown(f"**{label}**")
                st.caption("Reference and owning review IDs")
                st.text(f"{item.reference_id} · {item.review_id}")
                st.caption("Criterion, confirmed revision and static source type")
                st.text(
                    f"{item.criterion_id} · revision {item.criteria_revision_number} · "
                    f"{item.evidence_type.value} · {item.evidence_level.value} · "
                    f"{item.source_scope.value}"
                )
                st.caption("Source head")
                st.code(item.head_sha, language=None, wrap_lines=True)
                st.code(item.excerpt, language=None, wrap_lines=True)
                st.markdown(render_artifact_reference_markdown(item.permalink))
                st.caption("Selected by")
                st.text(item.reviewer)
                st.caption("Selection rationale")
                st.text(item.rationale)
                st.caption("Recorded at")
                st.text(item.selected_at.isoformat())
                st.caption("Confirmed criteria source and excerpt digest")
                st.text(item.criteria_source_provenance.source_uri)
                st.code(item.excerpt_sha256, language=None, wrap_lines=True)
