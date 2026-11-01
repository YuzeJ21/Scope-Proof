"""Validated, inert requirements-only handoff; no acceptance report policy changes."""

import json

from scopeproof_core.reporting.exporters import _escape_markdown_text, _render_markdown_code
from scopeproof_core.reviews.criteria_comparison import CriteriaRevisionComparison


def _validated(report: CriteriaRevisionComparison) -> CriteriaRevisionComparison:
    return CriteriaRevisionComparison.model_validate(report.model_dump(mode="python"))


def export_criteria_comparison_json(report: CriteriaRevisionComparison) -> str:
    return json.dumps(_validated(report).model_dump(mode="json"), sort_keys=True,
                      indent=2, ensure_ascii=False) + "\n"


def export_criteria_comparison_markdown(report: CriteriaRevisionComparison) -> str:
    report = _validated(report)
    historical = report.selection.historical
    code = _render_markdown_code
    lines = [
        "# ScopeProof Criteria Revision Changes", "", f"> {report.boundary}", "",
        f"- Owning saved record: {code(historical.review_id)}",
        f"- Retained history position: {historical.history_index + 1}",
        f"- Saved-state fingerprint: {code(historical.state_fingerprint)}",
        f"- Historical analysis fingerprint: {code(historical.analysis_fingerprint)}",
        f"- Previous criteria fingerprint: {code(report.selection.previous_criteria_fingerprint)}",
        f"- Current criteria fingerprint: {code(report.selection.current_criteria_fingerprint)}",
        f"- Validation tool: {code(report.validation_tool_version)}",
        f"- Validation ruleset: {code(report.validation_ruleset_version)}",
        f"- Validation core source: {code(report.validation_source_identity.sha256)}",
        "", "## Recorded changes", "",
        f"- Exact source text changed: {report.source_text_changed}",
        f"- Recorded provenance changed: {report.source_provenance_changed}",
        f"- Relative order of shared criterion IDs changed: {report.criterion_order_changed}", "",
    ]
    for row in report.criterion_changes:
        lines.extend([
            f"### {code(row.criterion_id)}", "",
            f"- Record distinction: {code(row.kind)}",
            f"- Previous position: {row.previous_position}",
            f"- Current position: {row.current_position}",
            "- Changed fields: " + (", ".join(code(field) for field in row.changed_fields)
                                    or "None"), "",
        ])
    for label, snapshot in (("Previous recorded criteria", report.previous),
                            ("Current saved criteria", report.current)):
        lines.extend([
            f"## {label}", "", f"- Saved head context: {code(snapshot.head_sha)}",
            f"- Criteria revision: {snapshot.revision_number}",
            "- Confirmation: " + ("Confirmed (asserted)" if snapshot.confirmed else "Unconfirmed"),
            "", "### Complete source text (line order preserved)", "",
        ])
        # Escape each physical line separately, preserving blank lines and CR/LF distinctions
        # in the exact JSON snapshot; rendered prose does not claim byte-identical whitespace.
        lines.extend(f"> {code(line)}" for line in snapshot.source_text.splitlines())
        lines.extend(["", "### Recorded source provenance", ""])
        if snapshot.source_provenance is None:
            lines.extend(["Not recorded; provenance remains unknown.", ""])
        else:
            for key, value in snapshot.source_provenance.model_dump(mode="json").items():
                lines.append(f"- {code(key)}: {code(str(value))}")
            lines.append("")
        lines.extend(["### Complete ordered criterion records", ""])
        for position, item in enumerate(snapshot.criteria, 1):
            lines.extend([f"#### Position {position}: {code(item.criterion_id)}", ""])
            for key, value in item.model_dump(mode="json").items():
                lines.append(f"- {code(key)}: {code(str(value))}")
            lines.append("")
        if not snapshot.criteria:
            lines.extend(["No criterion records in this saved revision.", ""])
    lines.extend([_escape_markdown_text(
        "Fingerprints check recorded consistency; they do not authenticate an actor or source. "
        "Requirements-only comparison does not relax full acceptance-report export policy."
    ), ""])
    return "\n".join(lines)
