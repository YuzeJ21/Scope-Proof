"""Display external CI results for the active analysis without changing the review."""

from __future__ import annotations

import hashlib
import json
import re

import streamlit as st

from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.reviews.ci_status import (
    EXACT_HEAD_PATTERN,
    MAX_CI_STATUS_BYTES,
    criterion_ci_statuses,
    load_ci_status_manifest,
)
from scopeproof_core.schemas.models import ReviewBundle, normalized_criteria_sha256

_STATUS_LABEL = {
    "passed": "Passed",
    "failed": "Failed",
    "skipped": "Explicitly skipped",
    "stale": "Stale",
    "unknown": "Unknown",
}


def render_criterion_ci_status(bundle: ReviewBundle, *, available: bool) -> None:
    """Display a session upload scoped to the confirmed criteria and reviewed commit."""
    review = bundle.review
    with st.expander(
        "CI status by criterion", key="criterion_ci_status_panel", on_change="rerun",
    ):
        if not available:
            st.caption("Refresh this review to see CI status for its reviewed commit.")
            return
        if not review.criteria_confirmed or not re.fullmatch(EXACT_HEAD_PATTERN, review.head_sha):
            st.caption("CI status requires confirmed criteria and a full reviewed commit SHA.")
            return

        criteria_digest = normalized_criteria_sha256(bundle.criteria)
        identity = (
            review.review_id, review.repository, review.pr_number, review.head_sha,
            criteria_digest,
        )
        widget_suffix = hashlib.sha256(json.dumps(identity).encode("utf-8")).hexdigest()
        st.caption(
            "Use a manifest from a CI source you trust. ScopeProof displays externally "
            "supplied results and does not verify who produced them, run tests, or change "
            "the review or its acceptance decision."
        )
        st.text(f"Reviewed pull request · {review.repository} #{review.pr_number}")
        st.text(f"Reviewed commit · {review.head_sha}")
        st.text(f"Confirmed criteria SHA-256 · {criteria_digest}")
        uploaded = st.file_uploader(
            "CI status manifest",
            type=["json"],
            key=f"criterion_ci_manifest_{widget_suffix}",
            max_upload_size=2,
            help="Upload a local JSON manifest up to 1 MiB. It is only used in this session.",
        )
        manifest = None
        if uploaded is not None:
            if uploaded.size > MAX_CI_STATUS_BYTES:
                st.error("The CI status manifest exceeds the 1 MiB limit.")
            else:
                try:
                    manifest = load_ci_status_manifest(uploaded.getvalue())
                except ValueError:
                    st.error("The file does not match the CI status manifest format.")

        try:
            statuses = criterion_ci_statuses(bundle, manifest)
        except ValueError:
            st.error(
                "The CI status manifest does not match this review or its confirmed criteria."
            )
            manifest = None
            statuses = criterion_ci_statuses(bundle)
        st.table(
            [
                {"Criterion": item.criterion_id, "CI status": _STATUS_LABEL[item.status]}
                for item in statuses
            ],
            hide_index=True,
        )
        if manifest is None:
            st.caption("Upload a matching CI manifest to see exact-commit results.")
            return
        if not statuses:
            return

        by_criterion = {item.criterion_id: item for item in statuses}
        criterion_id = st.selectbox(
            "Inspect CI criterion", list(by_criterion), key=f"criterion_ci_inspect_{widget_suffix}",
        )
        tests = by_criterion[criterion_id].tests
        if not tests:
            st.caption("The manifest does not identify expected tests for this criterion.")
            return
        st.dataframe(
            [
                {
                    "Expected test": test.test_id,
                    "CI status": _STATUS_LABEL[test.status],
                    "Why": test.reason,
                    "CI runs": ", ".join(test.run_ids),
                }
                for test in tests
            ],
            hide_index=True,
        )
        run_ids = {run_id for test in tests for run_id in test.run_ids}
        for run in manifest.runs:
            if run.run_id in run_ids:
                st.text(f"CI run {run.run_id} · {run.head_sha}")
                st.markdown(render_artifact_reference_markdown(run.source_url))
