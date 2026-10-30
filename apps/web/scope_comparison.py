"""Display-only scope context for the existing re-review journey."""

import streamlit as st

from scopeproof_core.reviews.scope_comparison import FileScopeComparison


def render_file_scope_comparison(scope: FileScopeComparison | None) -> None:
    st.markdown("#### Changed-file scope changes")
    st.caption(
        "Inventory metadata does not establish file-content equality, source deletion or "
        "acceptance. No prior scope decision is carried forward."
    )
    if scope is None:
        st.warning("Scope context is unknown in this older comparison.")
        return
    for label, snapshot in (("Previous", scope.previous), ("Current", scope.current)):
        if snapshot.ingestion_state.value != "complete" or (
            snapshot.skipped_files or snapshot.ingestion_warnings
        ):
            st.warning(
                f"{label} ingestion: {snapshot.ingestion_state.value.capitalize()} · "
                f"{len(snapshot.skipped_files)} skipped path(s) · "
                f"{len(snapshot.ingestion_warnings)} limitation(s). "
                "See inventory details; skipped paths were not inspected."
            )
    unresolved = scope.current.unresolved_paths
    if unresolved is None:
        st.warning("Current changed-file inventory is unknown; scope work cannot be enumerated.")
    elif unresolved:
        st.warning(f"Current head: {len(unresolved)} unresolved inspected file(s).")
        for path in unresolved:
            st.code(path, language=None)
        st.markdown("[Review current file scope](#changed-file-scope)")
    else:
        st.caption(
            "No unresolved inspected paths. This does not establish complete ingestion "
            "or acceptance."
        )
    if scope.previously_decided_paths_now_unresolved:
        st.text("Previously decided paths now unresolved:")
        for path in scope.previously_decided_paths_now_unresolved:
            st.code(path, language=None)
    changes = scope.inventory_changes
    if changes is None:
        st.warning("Inventory differences are unknown because an inventory is unavailable.")
    elif not changes:
        st.caption("No recorded inventory metadata differences.")
    with st.expander("Inventory changes and prior scope decisions", expanded=bool(changes)):
        for change in changes or []:
            st.text(f"{change.kind.replace('_', ' ').capitalize()}: {change.path}")
            for label, item in (("Previous", change.previous), ("Current", change.current)):
                if item is not None:
                    st.text(
                        f"{label} status: {item.status}; "
                        f"previous path: {item.previous_path or 'Not recorded'}"
                    )
        for label, snapshot in (("Previous", scope.previous), ("Current", scope.current)):
            st.caption(f"{label} ingestion: {snapshot.ingestion_state.value.capitalize()}")
            if snapshot.inventory is None:
                st.caption(f"{label} inventory: unknown")
            for path in snapshot.skipped_files:
                st.text(f"{label} skipped, uninspected path: {path}")
            for warning in snapshot.ingestion_warnings:
                st.text(f"{label} ingestion limitation: {warning}")
            for decision in snapshot.latest_decisions:
                st.text(
                    f"{label} scope decision: {decision.path}\n"
                    f"Disposition: {decision.disposition}\n"
                    f"Reviewer: {decision.reviewer}\n"
                    f"Recorded: {decision.timestamp.isoformat()}\n"
                    f"Head: {decision.head_sha}\n"
                    f"Criteria revision: {decision.criteria_revision_number}\n"
                    f"Criterion: {decision.criterion_id or 'Not applicable'}\n"
                    f"Event: {decision.event_id}\nExplanation: {decision.note}"
                )
    st.caption(
        "A within-criteria decision still needs a candidate citation. Skipped paths remain "
        "uninspected. Review current evidence before any new decision."
    )
