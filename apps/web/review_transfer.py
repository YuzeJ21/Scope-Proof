"""Explicit local saved-record handoff without replacing the open workbench review."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import streamlit as st

from apps.web.deferred_exports import DeferredExportUnavailable
from scopeproof_core.storage.atomic_files import MAX_SAVED_RECORD_BYTES
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.storage.transfer import (
    ReviewTransferPreview,
    import_review_bytes,
    inspect_review_bytes,
    read_review_transfer,
)


@dataclass
class ReviewTransferDownloadLease:
    """A shared volatile lease revokes callbacks from older rendered selections."""

    review_id: str | None = None
    record_sha256: str | None = None
    generation: int = 0

    def clear(self) -> None:
        self.generation += 1
        self.review_id = None
        self.record_sha256 = None


def deferred_record_download(
    store: JsonReviewStore, lease: ReviewTransferDownloadLease,
) -> Callable[[], bytes]:
    review_id, digest, generation = lease.review_id, lease.record_sha256, lease.generation
    message = "Saved record or selection changed. Prepare the saved review download again."

    def render() -> bytes:
        if (not review_id or not digest or lease.generation != generation
                or lease.review_id != review_id or lease.record_sha256 != digest):
            raise DeferredExportUnavailable(message)
        try:
            raw, _ = read_review_transfer(store, review_id, expected_sha256=digest)
        except (OSError, ValueError):
            raise DeferredExportUnavailable(message) from None
        if lease.generation != generation:
            raise DeferredExportUnavailable(message)
        return raw

    return render


def _clear_import_preview() -> None:
    st.session_state["transfer_import_preview"] = None
    st.session_state["confirm_transfer_import"] = False
    st.session_state.pop("transfer_import_notice", None)


def _uploaded_bytes(uploaded) -> bytes:
    if uploaded is None or uploaded.size > MAX_SAVED_RECORD_BYTES:
        raise ValueError("record upload exceeds byte limit or is missing")
    raw = uploaded.getvalue()
    if len(raw) > MAX_SAVED_RECORD_BYTES:
        raise ValueError("record upload exceeds byte limit")
    return raw


def _render_preview(preview: ReviewTransferPreview) -> None:
    receipt = preview.receipt
    facts = [
        ("Repository", preview.repository), ("Pull request", str(preview.pr_number)),
        ("Review ID", receipt.review_id), ("Recorded head", receipt.head_sha),
        ("Original record version", str(receipt.record_version)),
        ("Original saved time", receipt.saved_at or "Unknown"),
        ("Review created", preview.review_created_at.isoformat()),
        ("Recorded input origin", preview.input_origin.value),
        ("Recorded producer version", preview.producer_tool_version),
        ("Recorded producer ruleset", preview.producer_ruleset_version),
        ("Recorded producer source", preview.producer_source_identity.sha256
            if preview.producer_source_identity else "Unknown"),
        ("Criteria revision", str(preview.criteria_revision_number)),
        ("Criteria confirmation", "Confirmed" if preview.criteria_confirmed else "Unconfirmed"),
        ("Criteria count", str(preview.criterion_count)),
        ("Active analysis", "Present" if preview.has_active_analysis else "None"),
        ("Retained analyses", str(receipt.analysis_history_count)),
        ("Recorded decision events", str(preview.resolution_event_count)),
        ("Record bytes", str(receipt.record_bytes)), ("Content SHA-256", receipt.record_sha256),
    ]
    if preview.criteria_source is not None:
        facts.extend([
            ("Recorded criteria source", preview.criteria_source.source_uri),
            ("Asserted criteria confirmer", preview.criteria_source.confirmed_by),
        ])
    primary = {
        "Repository", "Pull request", "Review ID", "Recorded head",
        "Criteria confirmation", "Active analysis", "Retained analyses",
    }
    for label, value in facts:
        if label in primary:
            st.caption(label)
            st.text(value)
    with st.expander("Recorded provenance and file details", expanded=False):
        for label, value in facts:
            if label not in primary:
                st.caption(label)
                st.text(value)
    st.caption(receipt.boundary_note)


def render_review_transfer(
    store: JsonReviewStore, *, selected_review_id: str | None,
    store_available: bool, has_pending_inputs: bool,
) -> None:
    """Render preparation/download and inspection/import; reopening remains explicit."""
    lease = st.session_state.setdefault("transfer_download_lease", ReviewTransferDownloadLease())
    target = selected_review_id.strip() if selected_review_id else None
    if lease.review_id != target or has_pending_inputs or not store_available:
        lease.clear()
        st.session_state["transfer_download_preview"] = None
    st.markdown("#### Transfer a saved review")
    st.caption(
        "Complete saved records include requirements, excerpts, recorded decisions and history. "
        "Only saved content is included. Import adds a local record; it never replaces open work."
    )
    if st.button(
        "Prepare saved review download", key="prepare_transfer_download",
        disabled=not target or not store_available or has_pending_inputs,
    ):
        lease.clear()
        st.session_state["transfer_download_preview"] = None
        try:
            _, preview = read_review_transfer(store, target)
        except (OSError, ValueError):
            st.error(
                "Saved record could not be prepared. Check its ID and integrity, then try again."
            )
        else:
            lease.review_id = target
            lease.record_sha256 = preview.receipt.record_sha256
            st.session_state["transfer_download_preview"] = preview
    download_preview = st.session_state.get("transfer_download_preview")
    if download_preview is not None:
        st.caption("Complete saved record ready. Analysis report downloads are separate.")
        st.text(f"Review {download_preview.receipt.review_id}")
        st.text(f"Content SHA-256 {download_preview.receipt.record_sha256}")
        st.download_button(
            "Download saved review record", data=deferred_record_download(store, lease),
            file_name=f"scopeproof-review-{download_preview.receipt.review_id}.json",
            mime="application/json", key="download_saved_record", on_click="ignore",
        )
    if has_pending_inputs:
        st.caption(
            "Submit or clear pending review inputs before preparing a saved-record download."
        )

    if st.session_state.pop("transfer_reset_confirmation", False):
        st.session_state["confirm_transfer_import"] = False
    notice = st.session_state.get("transfer_import_notice")
    if notice:
        if notice[0] == "success":
            st.success(notice[1])
        else:
            st.error(notice[1])
    uploaded = st.file_uploader(
        "Saved review record to import", type=["json"], accept_multiple_files=False,
        key="transfer_upload", on_change=_clear_import_preview, max_upload_size=68,
        disabled=not store_available,
        help="Complete saved-record JSON, up to 64 MiB. Ordinary report JSON cannot be imported.",
    )
    st.caption("Saved-record payload limit: 64 MiB. Larger files remain unsaved.")
    if st.button(
        "Inspect uploaded review", key="inspect_transfer_upload",
        disabled=uploaded is None or not store_available,
    ):
        _clear_import_preview()
        try:
            preview = inspect_review_bytes(_uploaded_bytes(uploaded))
        except (OSError, ValueError):
            st.error(
                "Uploaded review could not be inspected. Use a valid supported saved record "
                "within 64 MiB. No record was imported."
            )
        else:
            st.session_state["transfer_import_preview"] = preview
    preview = st.session_state.get("transfer_import_preview")
    if preview is None:
        return
    with st.container(border=True, key="transfer_import_preview_panel"):
        st.markdown("##### Uploaded saved-record preview")
        _render_preview(preview)
        confirmed = st.checkbox(
            "Import this inspected saved record under its original review ID",
            key="confirm_transfer_import",
        )
        if st.button(
            "Import inspected review", key="import_transfer_upload",
            disabled=not confirmed or not store_available,
        ):
            try:
                receipt = import_review_bytes(
                    store, _uploaded_bytes(uploaded),
                    expected_sha256=preview.receipt.record_sha256,
                )
            except FileExistsError:
                notice = ("error", "A local record with this review ID already exists. "
                          "Nothing was overwritten. Use a separate store to inspect a collision.")
            except (OSError, ValueError):
                notice = ("error", "Import could not be completed. Inspect the current file again "
                          "and verify local storage. No existing record was replaced.")
            else:
                notice = ("success", f"Saved review imported: {receipt.review_id}. "
                          "Select its ID and choose Reopen local review when ready. "
                          "Open work remains unchanged.")
            st.session_state["transfer_import_notice"] = notice
            st.session_state["transfer_reset_confirmation"] = True
            st.rerun()
