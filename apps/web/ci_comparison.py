"""Compare explicit CI inputs using the same projection and export as the CLI."""

from __future__ import annotations

import json
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from threading import Event

import streamlit as st

from apps.web.deferred_exports import DeferredExportUnavailable, ExportRenderer, ExportSource
from scopeproof_core.reporting.ci_comparison import export_ci_comparison_html
from scopeproof_core.reviews.ci_comparison import CI_COMPARISON_BOUNDARY, compare_ci_status
from scopeproof_core.reviews.ci_handoff import load_exact_ci_manifest_with_payload
from scopeproof_core.reviews.ci_status import CI_STATUS_LABELS, MAX_CI_STATUS_BYTES
from scopeproof_core.schemas.models import ReviewBundle, ReviewState

_LEASE_KEY = "ci_comparison_download_expired"
_EXPIRED = (
    "CI comparison expired because the review or an input changed. "
    "Refresh CI status and use the current comparison download."
)
_CHANGES = {
    "added": "Introduced", "removed": "Removed", "changed": "Changed", "unchanged": "Retained",
}


def retire_ci_comparison_download() -> None:
    """Revoke callbacks already handed to Streamlit before replacing their context."""
    lease = st.session_state.pop(_LEASE_KEY, None)
    if lease is not None:
        lease.set()


def render_ci_comparison(
    bundle: ReviewBundle,
    *,
    current_payload: bytes,
    current_upload: BytesIO | None,
    handoff_directory: Path | None,
    widget_suffix: str,
    prepare_download: Callable[[ExportRenderer], Callable[[], str]] | None,
) -> None:
    if not st.checkbox(
        "Compare with a previous CI manifest", key=f"ci_comparison_mode_{widget_suffix}",
        on_change=retire_ci_comparison_download,
    ):
        return
    st.caption(
        "Current input: the CI status manifest displayed above. "
        "Upload the previous input explicitly."
    )
    previous_upload = st.file_uploader(
        "Previous CI status manifest", type=["json"],
        key=f"ci_comparison_previous_{widget_suffix}", max_upload_size=2,
        help="Upload a JSON manifest up to 1 MiB for the same criteria and reviewed commit.",
        on_change=retire_ci_comparison_download,
    )
    if previous_upload is None:
        return
    if previous_upload.size > MAX_CI_STATUS_BYTES:
        st.error("The previous CI status manifest exceeds the 1 MiB limit.")
        return
    try:
        previous_payload = previous_upload.getvalue()
        comparison = compare_ci_status(bundle, previous_payload, current_payload)
    except (OSError, ValueError):
        st.error(
            "The comparison inputs must be valid CI manifests for this review, "
            "its confirmed criteria and exact reviewed commit."
        )
        return

    st.subheader("CI context comparison")
    st.caption(CI_COMPARISON_BOUNDARY)
    st.text(f"Previous input SHA-256 · {comparison.previous_sha256}")
    st.text(f"Current input SHA-256 · {comparison.current_sha256}")
    st.table([
        {
            "Expected test": f"`{row.test_id}`",
            "Context change": _CHANGES[row.change],
            "Previous criteria": ", ".join(row.previous_criterion_ids),
            "Current criteria": ", ".join(row.current_criterion_ids),
            "Previous result": (
                CI_STATUS_LABELS[row.previous.status] if row.previous else "Not mapped"
            ),
            "Current result": CI_STATUS_LABELS[row.current.status] if row.current else "Not mapped",
            "Previous runs": (
                ", ".join(f"`{run}`" for run in row.previous.run_ids) if row.previous else ""
            ),
            "Current runs": (
                ", ".join(f"`{run}`" for run in row.current.run_ids) if row.current else ""
            ),
        }
        for row in comparison.test_changes()
    ], hide_index=True)
    st.dataframe([
        {
            "Run assertion": row.run_id, "Context change": _CHANGES[row.change],
            "Previous commit": row.previous.head_sha if row.previous else "",
            "Current commit": row.current.head_sha if row.current else "",
            "Previous source": row.previous.source_url if row.previous else "",
            "Current source": row.current.source_url if row.current else "",
            "Previous outcomes": (
                json.dumps(row.previous.outcomes, sort_keys=True)
                if row.previous else "No previous run"
            ),
            "Current outcomes": (
                json.dumps(row.current.outcomes, sort_keys=True)
                if row.current else "No current run"
            ),
        }
        for row in comparison.run_changes()
    ], hide_index=True, key="ci_comparison_runs")
    st.caption(
        "Run outcomes are reported assertions. A changed run record can leave the "
        "effective test result unchanged; an empty outcome map is shown as {}."
    )
    if prepare_download is None:
        st.caption("Resolve pending review inputs before downloading the CI comparison.")
        return

    lease = Event()
    st.session_state[_LEASE_KEY] = lease

    def require_current(source: ExportSource) -> ReviewBundle:
        authoritative = source.bundle if isinstance(source, ReviewState) else source
        if lease.is_set() or authoritative is None:
            raise DeferredExportUnavailable(_EXPIRED)
        try:
            if previous_upload.getvalue() != previous_payload:
                raise DeferredExportUnavailable(_EXPIRED)
            if current_upload is not None:
                if current_upload.getvalue() != current_payload:
                    raise DeferredExportUnavailable(_EXPIRED)
            elif handoff_directory is not None:
                _, payload = load_exact_ci_manifest_with_payload(handoff_directory, authoritative)
                if payload != current_payload:
                    raise DeferredExportUnavailable(_EXPIRED)
            else:
                raise DeferredExportUnavailable(_EXPIRED)
        except (OSError, ValueError):
            raise DeferredExportUnavailable(_EXPIRED) from None
        if lease.is_set():
            raise DeferredExportUnavailable(_EXPIRED)
        return authoritative

    def render(source: ExportSource) -> str:
        authoritative = require_current(source)
        report = export_ci_comparison_html(
            compare_ci_status(authoritative, previous_payload, current_payload),
        )
        require_current(source)
        return report

    st.download_button(
        "Download CI comparison", data=prepare_download(render),
        file_name=(
            f"scopeproof-ci-comparison-pr-{bundle.review.pr_number}-"
            f"{bundle.review.head_sha[:12]}-{comparison.previous_sha256[:12]}-"
            f"{comparison.current_sha256[:12]}.html"
        ),
        mime="application/octet-stream", key="download_ci_comparison", on_click="ignore",
    )
