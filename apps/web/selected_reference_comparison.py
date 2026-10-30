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
    for index, change in enumerate(context.record_changes, start=1):
        reference = change.current or change.previous
        with st.expander(f"{change.kind.replace('_', ' ').title()} · Reference {index}"):
            st.caption("Exact criterion and source location")
            st.text(f"{reference.criterion_id} · {reference.file_path}:{reference.line_number}")
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
                provenance = item.criteria_source_provenance
                st.caption("Criteria source")
                st.text(provenance.source_uri)
                st.caption("Criteria source revision")
                st.code(
                    provenance.source_revision or "(not recorded)", language=None, wrap_lines=True
                )
                st.caption("Criteria confirmed by")
                st.text(provenance.confirmed_by)
                st.caption("Criteria confirmed at")
                st.text(provenance.confirmed_at.isoformat())
                st.caption("Criteria source-text digest")
                st.code(provenance.source_text_sha256, language=None, wrap_lines=True)
                st.caption("Normalized criteria digest")
                st.code(provenance.normalized_criteria_sha256, language=None, wrap_lines=True)
                st.caption("Excerpt digest")
                st.code(item.excerpt_sha256, language=None, wrap_lines=True)
