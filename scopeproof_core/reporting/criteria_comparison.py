"""Validated, inert requirements-only handoff; no acceptance report policy changes."""

import json
import re
from collections.abc import Callable

from scopeproof_core.build_identity import current_core_source_identity
from scopeproof_core.reporting.exporters import _escape_markdown_text, _render_markdown_code
from scopeproof_core.reviews.criteria_comparison import (
    CRITERIA_COMPARISON_BOUNDARY,
    CriteriaRevisionComparison,
    RecordedCriteriaDiff,
)
from scopeproof_core.reviews.saved_comparison import SavedRequirementsReport
from scopeproof_core.schemas.models import RULESET_VERSION
from scopeproof_core.version import __version__


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
        f"- Repository: {code(report.selection.repository)}",
        f"- Pull request: {report.selection.pr_number}",
        f"- Retained history position: {historical.history_index + 1}",
        f"- Saved-state fingerprint: {code(historical.state_fingerprint)}",
        f"- Historical analysis fingerprint: {code(historical.analysis_fingerprint)}",
        f"- Previous criteria fingerprint: {code(report.selection.previous_criteria_fingerprint)}",
        f"- Current criteria fingerprint: {code(report.selection.current_criteria_fingerprint)}",
        f"- Validation tool: {code(report.validation_tool_version)}",
        f"- Validation ruleset: {code(report.validation_ruleset_version)}",
        f"- Validation core source: {code(report.validation_source_identity.sha256)}",
    ]
    return "\n".join([*lines, *_requirements_lines(report, code)])


def _literal_markdown_code(value: str) -> str:
    """Render untrusted recorded values as literal CommonMark code spans."""
    normalized = value.replace("\r", " ").replace("\n", " ")
    delimiter = "`" * (max(map(len, re.findall(r"`+", normalized)), default=0) + 1)
    return f"{delimiter} {normalized} {delimiter}"


def export_saved_requirements_markdown(report: SavedRequirementsReport) -> str:
    report = SavedRequirementsReport.model_validate(report.model_dump(mode="python"))
    selection = report.selection
    code = _literal_markdown_code
    location = (
        f"Retained history position {selection.history_index + 1}"
        if selection.history_index is not None else "Active analysis"
    )
    lines = [
        "# ScopeProof Saved Requirements Comparison", "",
        f"> {CRITERIA_COMPARISON_BOUNDARY}", "",
        f"- Repository: {code(report.current.repository)}",
        f"- Pull request: {report.current.pr_number}",
        f"- Baseline saved record: {code(selection.baseline_review_id)}",
        f"- Baseline analysis: {location}",
        f"- Baseline saved-state fingerprint: {code(selection.baseline_fingerprint)}",
        f"- Baseline criteria fingerprint: {code(report.baseline_criteria_fingerprint)}",
        f"- Current saved record: {code(selection.current_review_id)}",
        f"- Current saved-state fingerprint: {code(selection.current_fingerprint)}",
        f"- Current criteria fingerprint: {code(report.current_criteria_fingerprint)}",
        f"- Validation tool: {code(__version__)}",
        f"- Validation ruleset: {code(RULESET_VERSION)}",
        f"- Validation core source: {code(current_core_source_identity().sha256)}",
    ]
    return "\n".join([*lines, *_requirements_lines(report, code)])


def _requirements_lines(report: RecordedCriteriaDiff, code: Callable[[str], str]) -> list[str]:
    lines = [
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
    return lines
