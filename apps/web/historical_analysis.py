"""Read-only saved history; no active-analysis replacement or decision controls."""

from __future__ import annotations

import html
import re

import streamlit as st

from apps.web.deferred_exports import HistoricalAnalysisExportLease, deferred_historical_export
from scopeproof_core.reporting.historical_analysis import (
    export_historical_json,
    export_historical_markdown,
)
from scopeproof_core.reviews.historical_analysis import (
    HISTORICAL_ANALYSIS_BOUNDARY,
    HistoricalAnalysisReport,
    locked_historical_analysis,
    prepare_historical_analysis,
)
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore


def clear_historical_analysis_selection(*, clear_choice: bool = True) -> None:
    lease = st.session_state.get("historical_analysis_export_lease")
    if lease is not None:
        lease.invalidate()
    st.session_state["historical_analysis_selection"] = None
    if clear_choice:
        # Reopen/reset can occur after an earlier widget rendered. Defer its reset.
        st.session_state["historical_analysis_reset_pending"] = True


def _choice_changed() -> None:
    clear_historical_analysis_selection(clear_choice=False)


def _readable_markdown(markdown: str) -> str:
    """Convert generated code tags to inert code spans; keep unsafe HTML disabled."""
    def code(match: re.Match[str]) -> str:
        value = html.unescape(match.group(1))
        line_start = markdown.rfind("\n", 0, match.start()) + 1
        if markdown[line_start:match.start()].lstrip().startswith("|"):
            value = value.replace("|", r"\|")
        delimiter = "`" * (max((len(part) for part in re.findall(r"`+", value)), default=0) + 1)
        return f"{delimiter} {value} {delimiter}"

    return re.sub(r"<code>(.*?)</code>", code, markdown, flags=re.DOTALL)


def _render_identity(report: HistoricalAnalysisReport) -> None:
    analysis = report.analysis
    st.markdown("### Historical recorded analysis")
    st.warning(HISTORICAL_ANALYSIS_BOUNDARY)
    st.caption("Historical owning record and pull request")
    st.text(report.selection.review_id)
    st.text(f"{analysis.review.repository} · PR #{analysis.review.pr_number}")
    st.caption("Historical head")
    st.code(analysis.review.head_sha, language=None, wrap_lines=True)
    st.text(f"Criteria revision: {analysis.criteria_revision_number}")
    st.caption("Recorded historical producer")
    st.text(f"Tool {analysis.review.tool_version} · ruleset {analysis.review.ruleset_version}")
    identity = analysis.review.analysis_source_identity
    st.code(identity.sha256 if identity else "Not captured", language=None, wrap_lines=True)
    st.caption("Current validation context")
    st.text(f"Tool {report.validation_tool_version} · ruleset {report.validation_ruleset_version}")
    st.code(report.validation_source_identity.sha256, language=None, wrap_lines=True)


def render_historical_analysis_selector(
    current: ReviewState | None, *, store: JsonReviewStore, current_is_saved: bool,
) -> None:
    if "historical_analysis_export_lease" not in st.session_state:
        st.session_state["historical_analysis_export_lease"] = HistoricalAnalysisExportLease()
    eligible = current is not None and current_is_saved
    context = (
        str(store.directory.absolute()),
        current.review.review_id if current is not None else None,
        store.state_fingerprint(current) if eligible else None,
    )
    if context != st.session_state.get("historical_analysis_context"):
        clear_historical_analysis_selection()
        st.session_state["historical_analysis_context"] = context
        st.session_state["historical_analysis_unavailable"] = False
    if st.session_state.pop("historical_analysis_reset_pending", False):
        st.session_state["historical_analysis_index"] = None
        st.session_state["historical_analysis_unavailable"] = False
    if current is None:
        return
    histories = current.analysis_history
    with st.expander(
        "Inspect retained analysis",
        expanded=st.session_state.get("historical_analysis_index") is not None,
    ):
        st.caption(HISTORICAL_ANALYSIS_BOUNDARY)
        st.text(f"Opened saved record: {current.review.review_id}")
        st.caption(
            "Choose a retained analysis independently of current criteria or an active analysis. "
            "This reads saved history only; current draft inputs do not enter its report."
        )
        if not eligible:
            st.info("Save or reopen the record before inspecting its retained analyses.")
        if not histories:
            st.info("No retained analyses are recorded in this saved review.")
        unavailable = st.session_state.get("historical_analysis_unavailable", False)
        index = st.selectbox(
            "Retained historical analysis", options=list(range(len(histories))), index=None,
            format_func=lambda value: (
                f"History {value + 1} · criteria revision "
                f"{histories[value].criteria_revision_number} · head "
                f"{histories[value].review.head_sha}"
            ),
            key="historical_analysis_index", on_change=_choice_changed,
            disabled=not eligible or not histories or unavailable,
        )
        if st.button(
            "Inspect selected historical analysis", key="inspect_historical_analysis",
            disabled=not eligible or index is None or unavailable,
        ):
            _choice_changed()
            try:
                selection = prepare_historical_analysis(store, current, index)
            except (OSError, ValueError):
                st.session_state["historical_analysis_unavailable"] = True
                st.warning("Saved history is unavailable or changed. Reopen and select it again.")
            else:
                st.session_state["historical_analysis_selection"] = selection
                st.session_state["historical_analysis_export_lease"].selection = selection
        selection = st.session_state.get("historical_analysis_selection")
        if selection is None:
            return
        try:
            with locked_historical_analysis(store, selection) as report:
                _render_identity(report)
                if report.analysis.review.criteria_source_provenance is None:
                    st.warning(
                        "Historical criteria source provenance was not recorded. Full report "
                        "preview and downloads remain unavailable under the existing export policy."
                    )
                    return
                st.markdown(_readable_markdown(export_historical_markdown(report)))
                lease = st.session_state["historical_analysis_export_lease"]
                for label, renderer, suffix, mime in (
                    ("JSON", export_historical_json, "json", "application/json"),
                    ("Markdown", export_historical_markdown, "md", "text/markdown"),
                ):
                    filename = (
                        f"{selection.review_id}-history-{selection.history_index + 1}.{suffix}"
                    )
                    st.download_button(
                        f"Download historical {label}",
                        data=deferred_historical_export(
                            selection, renderer, store=store, lease=lease,
                        ),
                        file_name=filename,
                        mime=mime, key=f"download_historical_{suffix}", on_click="ignore",
                    )
        except (OSError, ValueError):
            _choice_changed()
            st.session_state["historical_analysis_unavailable"] = True
            st.warning("Saved history is unavailable or changed. Reopen and select it again.")
