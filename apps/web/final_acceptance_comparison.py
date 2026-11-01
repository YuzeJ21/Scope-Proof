"""Show recorded acceptance flags without reconstructing missing event attribution."""

import streamlit as st

from scopeproof_core.reviews.final_acceptance_comparison import (
    FINAL_ACCEPTANCE_COMPARISON_BOUNDARY,
    FinalAcceptanceComparison,
)


def render_final_acceptance_comparison(context: FinalAcceptanceComparison | None) -> None:
    st.markdown("### Recorded final acceptance")
    st.caption(FINAL_ACCEPTANCE_COMPARISON_BOUNDARY)
    if context is None:
        st.info("Recorded final acceptance was not included in this older comparison.")
        return
    context = FinalAcceptanceComparison.model_validate(context.model_dump(mode="python"))
    st.text(f"Recorded value changed: {'Yes' if context.recorded_value_changed else 'No'}")
    st.caption(
        "Event attribution, actor, timestamp, rationale and event association are unavailable "
        "in analysis snapshots. No does not establish revocation or that acceptance never happened."
    )
    for side in ("previous", "current"):
        snapshot = getattr(context, side)
        with st.expander(f"{side.title()} recorded final acceptance"):
            value = "Yes" if snapshot.recorded_final_acceptance else "No"
            st.text(f"Recorded final acceptance: {value}")
            st.text(f"{snapshot.repository} · PR #{snapshot.pr_number}")
            st.text(snapshot.review_id)
            st.caption("Owning head")
            st.code(snapshot.head_sha, language=None, wrap_lines=True)
            st.text(f"Criteria revision: {snapshot.criteria_revision_number}")
            st.text(f"Recorded input origin: {snapshot.input_origin.value}")
            st.caption("Normalized criteria digest")
            st.code(snapshot.normalized_criteria_sha256, language=None, wrap_lines=True)
            st.text("Criterion IDs: " + ", ".join(snapshot.criterion_ids))
