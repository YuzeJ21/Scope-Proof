"""Explicit historical-only JSON and Markdown, retaining normal export eligibility."""

from __future__ import annotations

import json

from scopeproof_core.reporting.exporters import (
    _render_markdown_code,
    _validated_exportable,
    export_markdown,
)
from scopeproof_core.reviews.historical_analysis import HistoricalAnalysisReport


def _validated_report(report: HistoricalAnalysisReport) -> HistoricalAnalysisReport:
    report = HistoricalAnalysisReport.model_validate(report.model_dump(mode="python"))
    _validated_exportable(report.analysis)
    return report


def export_historical_json(report: HistoricalAnalysisReport) -> str:
    validated = _validated_report(report)
    return json.dumps(validated.model_dump(mode="json"), sort_keys=True, indent=2,
                      ensure_ascii=False) + "\n"


def export_historical_markdown(report: HistoricalAnalysisReport) -> str:
    report = _validated_report(report)
    analysis = report.analysis
    selection = report.selection
    body = export_markdown(analysis)
    if not body.startswith("# ScopeProof Acceptance Review\n"):
        raise ValueError("historical report requires the supported bundle report format")
    body = body.replace(
        "# ScopeProof Acceptance Review", "## Historical acceptance-review details", 1,
    )
    body = body.replace(
        "**Review status:**", "**Historical review status (installed policy):**", 1,
    )
    lines = [
        "# ScopeProof Historical Analysis", "", f"> {report.boundary}", "",
        f"- Owning record: {_render_markdown_code(selection.review_id)}",
        f"- Retained history position: {selection.history_index + 1}",
        f"- Head: {_render_markdown_code(analysis.review.head_sha)}",
        f"- Criteria revision: {analysis.criteria_revision_number}",
        f"- Saved-state fingerprint: {_render_markdown_code(selection.state_fingerprint)}",
        f"- Analysis fingerprint: {_render_markdown_code(selection.analysis_fingerprint)}",
        f"- Validation tool: {_render_markdown_code(report.validation_tool_version)}",
        f"- Validation ruleset: {_render_markdown_code(report.validation_ruleset_version)}",
        "- Validation core source: "
        f"{_render_markdown_code(report.validation_source_identity.sha256)}",
        "", body,
    ]
    return "\n".join(lines).rstrip() + "\n"
