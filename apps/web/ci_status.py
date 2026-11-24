"""Display external CI results for the active analysis without changing the review."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from os import getenv
from pathlib import Path
from threading import Event

import streamlit as st

from apps.web.deferred_exports import DeferredExportUnavailable, ExportRenderer, ExportSource
from apps.web.launcher import CI_MANIFEST_DIR_ENV, is_ci_loopback_host
from scopeproof_core.reporting.ci_snapshot import (
    build_ci_status_snapshot,
    export_ci_status_snapshot_html,
)
from scopeproof_core.reporting.references import render_artifact_reference_markdown
from scopeproof_core.reviews.ci_handoff import load_exact_ci_manifest_with_sha256
from scopeproof_core.reviews.ci_status import (
    CI_STATUS_LABELS,
    EXACT_HEAD_PATTERN,
    MAX_CI_STATUS_BYTES,
    CIFollowUpSummary,
    CIStatusManifest,
    criterion_ci_statuses,
    load_ci_status_manifest,
    summarize_ci_follow_up,
)
from scopeproof_core.schemas.models import ReviewBundle, ReviewState, normalized_criteria_sha256

_SNAPSHOT_EXPIRED = (
    "CI snapshot expired because the review or manifest changed. "
    "Refresh CI status and use the current download."
)


def retire_ci_snapshot_download() -> None:
    """Revoke the visible download before a new review or upload can replace it."""
    lease = st.session_state.get("ci_snapshot_download_expired")
    if lease is not None:
        lease.set()
        st.session_state.pop("ci_snapshot_download_expired", None)


def _render_snapshot_download(
    bundle: ReviewBundle,
    manifest: CIStatusManifest,
    *,
    manifest_sha256: str,
    handoff_directory: Path | None,
    prepare_download: Callable[[ExportRenderer], Callable[[], str]],
) -> None:
    review = bundle.review
    if not any(run.head_sha == review.head_sha for run in manifest.runs):
        st.caption("Download requires a CI manifest with at least one run for the reviewed commit.")
        return
    snapshot = build_ci_status_snapshot(
        bundle, manifest, manifest_sha256=manifest_sha256,
        source="manual-upload" if handoff_directory is None else "configured-local",
    )
    lease = Event()
    st.session_state["ci_snapshot_download_expired"] = lease

    def require_current(source: ExportSource) -> None:
        if lease.is_set():
            raise DeferredExportUnavailable(_SNAPSHOT_EXPIRED)
        if handoff_directory is not None:
            authoritative = source.bundle if isinstance(source, ReviewState) else source
            if authoritative is None:
                raise DeferredExportUnavailable(_SNAPSHOT_EXPIRED)
            try:
                _, current_digest = load_exact_ci_manifest_with_sha256(
                    handoff_directory, authoritative,
                )
            except (OSError, ValueError):
                raise DeferredExportUnavailable(_SNAPSHOT_EXPIRED) from None
            if current_digest != manifest_sha256 or lease.is_set():
                raise DeferredExportUnavailable(_SNAPSHOT_EXPIRED)

    def render(source: ExportSource) -> str:
        require_current(source)
        report = export_ci_status_snapshot_html(snapshot)
        require_current(source)
        return report

    st.download_button(
        "Download CI snapshot",
        data=prepare_download(render),
        file_name=(
            f"scopeproof-ci-pr-{review.pr_number}-{review.head_sha[:12]}-{manifest_sha256[:12]}.html"
        ),
        mime="application/octet-stream",
        key="download_ci_snapshot",
        on_click="ignore",
    )


def _render_ci_follow_up(follow_up: CIFollowUpSummary) -> None:
    st.subheader("CI follow-up")
    if follow_up.tests:
        st.table(
            [
                {
                    "Expected test": test.test_id,
                    "Mapped criteria": ", ".join(test.criterion_ids),
                    "CI status": CI_STATUS_LABELS[test.status],
                    "Why": test.reason,
                    "CI runs": ", ".join(test.run_ids),
                }
                for test in follow_up.tests
            ],
            hide_index=True,
        )
    else:
        st.caption("All mapped CI tests reported a pass for this commit.")
    if follow_up.unmapped_criterion_ids:
        criteria = ", ".join(follow_up.unmapped_criterion_ids)
        st.caption(f"No CI tests are mapped to {criteria}.")


def render_criterion_ci_status(
    bundle: ReviewBundle, *, available: bool,
    prepare_download: Callable[[ExportRenderer], Callable[[], str]] | None = None,
) -> None:
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
        configured_directory = (
            getenv(CI_MANIFEST_DIR_ENV) if is_ci_loopback_host(st.get_option("server.address"))
            else None
        )
        handoff_directory = Path(configured_directory) if configured_directory else None
        if handoff_directory:
            st.button("Refresh CI status", key=f"criterion_ci_refresh_{widget_suffix}")
        uploaded = st.file_uploader(
            "CI status manifest",
            type=["json"],
            key=f"criterion_ci_manifest_{widget_suffix}",
            max_upload_size=2,
            help="Upload a local JSON manifest up to 1 MiB. It is only used in this session.",
            on_change=retire_ci_snapshot_download,
        )
        manifest = None
        manifest_sha256 = None
        if uploaded is not None:
            if uploaded.size > MAX_CI_STATUS_BYTES:
                st.error("The CI status manifest exceeds the 1 MiB limit.")
            else:
                payload = uploaded.getvalue()
                try:
                    manifest = load_ci_status_manifest(payload)
                except ValueError:
                    st.error("The file does not match the CI status manifest format.")
                else:
                    manifest_sha256 = hashlib.sha256(payload).hexdigest()
        elif handoff_directory:
            try:
                manifest, manifest_sha256 = load_exact_ci_manifest_with_sha256(
                    handoff_directory, bundle,
                )
            except FileNotFoundError:
                st.caption("No local CI manifest was found for this exact review.")
            except (OSError, ValueError):
                st.error("The local CI manifest could not be loaded for this exact review.")
            else:
                st.caption("CI source: configured local manifest.")

        try:
            statuses = criterion_ci_statuses(bundle, manifest)
        except ValueError:
            st.error(
                "The CI status manifest does not match this review or its confirmed criteria."
            )
            manifest = None
            statuses = criterion_ci_statuses(bundle)
        if uploaded is not None and manifest is not None and handoff_directory:
            st.caption("CI source: manual upload.")
        st.table(
            [
                {"Criterion": item.criterion_id, "CI status": CI_STATUS_LABELS[item.status]}
                for item in statuses
            ],
            hide_index=True,
        )
        if manifest is None:
            st.caption("Upload a matching CI manifest to see exact-commit results.")
            return
        if not statuses:
            return
        follow_up = summarize_ci_follow_up(statuses)
        _render_ci_follow_up(follow_up)
        if prepare_download is not None:
            assert manifest_sha256 is not None
            _render_snapshot_download(
                bundle, manifest, manifest_sha256=manifest_sha256,
                handoff_directory=handoff_directory if uploaded is None else None,
                prepare_download=prepare_download,
            )

        by_criterion = {item.criterion_id: item for item in statuses}
        criterion_id = st.selectbox(
            "Inspect CI criterion", list(by_criterion), key=f"criterion_ci_inspect_{widget_suffix}",
        )
        tests = by_criterion[criterion_id].tests
        if not tests:
            st.caption("The manifest does not identify expected tests for this criterion.")
        else:
            st.dataframe(
                [
                    {
                        "Expected test": test.test_id,
                        "CI status": CI_STATUS_LABELS[test.status],
                        "Why": test.reason,
                        "CI runs": ", ".join(test.run_ids),
                    }
                    for test in tests
                ],
                hide_index=True,
            )
        run_ids = {run_id for test in (*follow_up.tests, *tests) for run_id in test.run_ids}
        for run in manifest.runs:
            if run.run_id in run_ids:
                st.text(f"CI run {run.run_id} · {run.head_sha}")
                st.markdown(render_artifact_reference_markdown(run.source_url))
