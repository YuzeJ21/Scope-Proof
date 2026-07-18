"""Render one validated review bundle into consistent report formats."""

from __future__ import annotations

import csv
import html
import io
import json
import string
from collections import defaultdict

from scopeproof_core.gates.guidance import gate_guidance
from scopeproof_core.gates.validation import (
    validated_review_bundle,
    validated_review_state,
)
from scopeproof_core.presentation import (
    criterion_coverage_rows,
    evidence_status_text,
    review_status_label,
)
from scopeproof_core.reporting.references import (
    is_linkable_artifact_reference,
    render_artifact_reference_markdown,
)
from scopeproof_core.schemas.models import EvidenceItem, ReviewBundle, ReviewState

ExportableReview = ReviewBundle | ReviewState

_MARKDOWN_PUNCTUATION = frozenset(set(string.punctuation) - {"&", ";"})
_SPREADSHEET_FORMULA_PREFIXES = frozenset(("=", "+", "-", "@", "\t", "\r"))


def _escape_markdown_text(value: str) -> str:
    """Keep untrusted text readable without activating Markdown or raw HTML."""
    normalized = value.replace("\r", " ").replace("\n", " ")
    escaped = html.escape(normalized, quote=False)
    return "".join(
        f"\\{character}" if character in _MARKDOWN_PUNCTUATION else character
        for character in escaped
    )


def _render_markdown_code(value: str) -> str:
    """Render untrusted repository text as inert HTML code within Markdown."""
    normalized = value.replace("\r", " ").replace("\n", " ")
    return f"<code>{html.escape(normalized, quote=True)}</code>"


def _csv_text(value: str) -> str:
    """Prevent spreadsheet software from interpreting exported text as a formula."""
    candidate = value.lstrip(" ")
    if candidate and candidate[0] in _SPREADSHEET_FORMULA_PREFIXES:
        return f"'{value}"
    return value


def _validated_exportable(value: ExportableReview) -> ExportableReview:
    """Revalidate mutable model input before rendering an export artifact."""
    if isinstance(value, ReviewState):
        return validated_review_state(value)
    return validated_review_bundle(value)


def _bundle_and_state(value: ExportableReview) -> tuple[ReviewBundle, ReviewState | None]:
    value = _validated_exportable(value)
    if isinstance(value, ReviewState):
        if value.bundle is None:
            raise ValueError("A confirmed analysis is required before exporting a review state")
        return value.bundle, value
    return value, None


def export_json(bundle: ExportableReview) -> str:
    """Return canonical, diff-friendly JSON without adapter state or credentials."""
    payload = _validated_exportable(bundle).model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_markdown(bundle: ExportableReview) -> str:
    """Return a PR-comment-friendly report with evidence and limitations."""
    bundle, state = _bundle_and_state(bundle)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    resolution_by_id = {resolution.criterion_id: resolution for resolution in bundle.resolutions}
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    review_status = review_status_label(bundle.gate.verdict)
    coverage_by_id = {
        row.criterion_id: row for row in criterion_coverage_rows(bundle)
    }
    review_created_at = bundle.review.model_dump(mode="json")["created_at"]
    lines = [
        "# ScopeProof Acceptance Review",
        "",
        f"**Review status:** {review_status}",
        f"**Review ID:** {_render_markdown_code(bundle.review.review_id)}",
        f"**Repository:** {_render_markdown_code(bundle.review.repository)}",
        f"**Pull request:** #{bundle.review.pr_number}",
        f"**Base SHA:** {_render_markdown_code(bundle.review.base_sha)}",
        f"**Head SHA:** {_render_markdown_code(bundle.review.head_sha)}",
        f"**Review created:** {_render_markdown_code(review_created_at)}",
        f"**Tool version:** {_render_markdown_code(bundle.review.tool_version)}",
        f"**Ruleset:** {_render_markdown_code(bundle.review.ruleset_version)}",
        f"**Ingestion state:** {_render_markdown_code(bundle.review.ingestion_state.value)}",
        *([f"**Criteria revision: {state.criteria_revision.number}**"] if state else []),
        "",
        (
            "> ScopeProof surfaces auditable candidate evidence. "
            "It does not replace QA or prove correctness."
        ),
        "",
        *(
            [
                "## Ingestion Limitations",
                "",
                *[
                    f"- {_render_markdown_code(warning)}"
                    for warning in bundle.review.ingestion_warnings
                ],
                *(
                    [
                        "",
                        "**Skipped changed files (not inspected):**",
                        *[
                            f"- {_render_markdown_code(path)}"
                            for path in bundle.review.skipped_files
                        ],
                    ]
                    if bundle.review.skipped_files
                    else []
                ),
                "",
            ]
            if bundle.review.ingestion_warnings or bundle.review.skipped_files
            else []
        ),
        "## Confirmed Requirements Source",
        "",
        *[
            f"> {_escape_markdown_text(line)}"
            for line in (bundle.source_text.splitlines() or [""])
        ],
        "",
        "## Evidence Matrix",
        "",
        (
            "| Criterion | Source | Priority | Evidence status | Evidence types | "
            "Reviewer decision | Confidence | Count | Concern |"
        ),
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        row = coverage_by_id[criterion.criterion_id]
        criterion_label = _escape_markdown_text(
            f"{criterion.criterion_id}: {criterion.text}"
        )
        concern = _escape_markdown_text(finding.reason)
        lines.append(
            f"| {criterion_label} | "
            f"{row.source} | {row.priority} | "
            f"{evidence_status_text(row.evidence_status)} | "
            f"{', '.join(row.evidence_types) or 'None'} | {row.reviewer_decision} | "
            f"{finding.confidence_band.value} | {row.candidate_count} | {concern} |"
        )

    lines.extend(["", "## Criterion Details", ""])
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        coverage = coverage_by_id[criterion.criterion_id]
        lines.extend(
            [
                f"### {_escape_markdown_text(f'{criterion.criterion_id} — {criterion.text}')}",
                "",
                "**Evidence status:** "
                f"{evidence_status_text(coverage.evidence_status)}",
                f"**Reason:** {_escape_markdown_text(finding.reason)}",
            ]
        )
        if finding.missing_evidence:
            lines.extend(
                [
                    "",
                    "**Missing evidence:**",
                    *[f"- {_escape_markdown_text(item)}" for item in finding.missing_evidence],
                ]
            )
        candidates = [evidence_by_id[item_id] for item_id in finding.evidence_ids]
        if candidates:
            lines.extend(["", "**Candidate evidence:**"])
            for candidate in candidates:
                candidate_label = (
                    f"{_escape_markdown_text(candidate.file_path)}:L{candidate.line_start}"
                )
                if is_linkable_artifact_reference(candidate.permalink):
                    destination = html.escape(candidate.permalink, quote=True)
                    candidate_reference = f"[{candidate_label}](<{destination}>)"
                else:
                    candidate_reference = (
                        f"{candidate_label} — permalink: "
                        f"{_escape_markdown_text(candidate.permalink)}"
                    )
                lines.append(
                    f"- {candidate_reference} — "
                    f"{_escape_markdown_text(candidate.relevance_reason)}"
                )
                lines.append(f"  - Excerpt: {_render_markdown_code(candidate.excerpt)}")
                for limitation in candidate.limitations:
                    lines.append(f"  - Limitation: {_escape_markdown_text(limitation)}")
        resolution = resolution_by_id.get(criterion.criterion_id)
        if resolution:
            lines.extend(
                [
                    "",
                    f"**Reviewer decision:** {coverage.reviewer_decision}",
                    "**Reviewer note:** "
                    f"{_escape_markdown_text(resolution.comment or 'No note provided')}",
                ]
            )
        lines.extend(
            [
                "",
                f"**Recommended action:** {_escape_markdown_text(finding.recommended_action)}",
                "",
            ]
        )

    if bundle.runtime_evidence:
        lines.extend(["## Manual Runtime Evidence", ""])
        for item in bundle.runtime_evidence:
            lines.extend(
                [
                    f"- **{_escape_markdown_text(item.criterion_id)}** — "
                    f"{render_artifact_reference_markdown(item.artifact_reference)}",
                    f"  - Scenario: {_escape_markdown_text(item.scenario)}",
                    f"  - Environment: {_escape_markdown_text(item.environment)}; "
                    f"result: {_escape_markdown_text(item.result)}; "
                    f"reviewer: {_escape_markdown_text(item.reviewer)}; "
                    f"level: {_escape_markdown_text(item.evidence_level.value)}",
                    "  - Limitations: "
                    f"{_escape_markdown_text(', '.join(item.limitations) or 'None recorded')}",
                ]
            )
        lines.append("")

    if bundle.gate.reason_codes:
        lines.extend(
            [
                "## Review Status Reasons",
                "",
                *[f"- {_render_markdown_code(code)}" for code in bundle.gate.reason_codes],
                "",
            ]
        )
    guidance = gate_guidance(bundle.gate)
    if guidance:
        lines.extend(
            [
                "## What To Do Next",
                "",
                *[f"- {_escape_markdown_text(message)}" for message in guidance],
                "",
            ]
        )
    if state is not None:
        lines.extend(["## Resolution History", ""])
        for event in state.resolution_events:
            target = event.criterion_id or "Final acceptance"
            outcome = (
                event.decision.value
                if event.decision
                else str(event.final_acceptance).lower()
            )
            history = f"{target}: {outcome} — {event.comment or 'No note provided'}"
            lines.append(f"- {_escape_markdown_text(history)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_artifact_reference_html(value: str) -> str:
    label = html.escape(value)
    if not is_linkable_artifact_reference(value):
        return label
    return f'<a href="{html.escape(value, quote=True)}">{label}</a>'


def _render_candidate_reference_html(item: EvidenceItem) -> str:
    label = f"{html.escape(item.file_path)}:L{item.line_start}"
    if is_linkable_artifact_reference(item.permalink):
        reference = f'<a href="{html.escape(item.permalink, quote=True)}">{label}</a>'
    else:
        reference = f"{label}<br><code>{html.escape(item.permalink)}</code>"
    return f"{reference}<br><code>{html.escape(item.excerpt)}</code>"


def export_csv(bundle: ExportableReview) -> str:
    """Return one flat audit row per criterion."""
    bundle, state = _bundle_and_state(bundle)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    resolution_by_id = {resolution.criterion_id: resolution for resolution in bundle.resolutions}
    evidence_by_criterion: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in bundle.evidence:
        evidence_by_criterion[item.criterion_id].append(item)

    fieldnames = [
        "review_id",
        "repository",
        "pr_number",
        "base_sha",
        "head_sha",
        "review_created_at",
        "tool_version",
        "ruleset_version",
        "ingestion_state",
        "ingestion_warnings",
        "skipped_files",
        "criteria_revision",
        "requirements_source_text",
        "verdict",
        "review_status",
        "criterion_id",
        "criterion",
        "criterion_source",
        "priority",
        "status",
        "evidence_status",
        "evidence_level",
        "evidence_types",
        "confidence_band",
        "evidence_count",
        "concern",
        "evidence_links",
        "missing_evidence",
        "human_decision",
        "reviewer_decision",
        "reviewer_comment",
        "recommended_action",
        "runtime_artifacts",
        "runtime_result",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\r\n")
    writer.writeheader()
    coverage_by_id = {
        row.criterion_id: row for row in criterion_coverage_rows(bundle)
    }
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        resolution = resolution_by_id.get(criterion.criterion_id)
        coverage = coverage_by_id[criterion.criterion_id]
        runtime_items = [
            item for item in bundle.runtime_evidence if item.criterion_id == criterion.criterion_id
        ]
        writer.writerow(
            {
                "review_id": _csv_text(bundle.review.review_id),
                "repository": _csv_text(bundle.review.repository),
                "pr_number": bundle.review.pr_number,
                "base_sha": _csv_text(bundle.review.base_sha),
                "head_sha": _csv_text(bundle.review.head_sha),
                "review_created_at": bundle.review.model_dump(mode="json")["created_at"],
                "tool_version": _csv_text(bundle.review.tool_version),
                "ruleset_version": _csv_text(bundle.review.ruleset_version),
                "ingestion_state": bundle.review.ingestion_state.value,
                "ingestion_warnings": json.dumps(
                    bundle.review.ingestion_warnings, ensure_ascii=False
                ),
                "skipped_files": json.dumps(bundle.review.skipped_files, ensure_ascii=False),
                "criteria_revision": state.criteria_revision.number if state else 1,
                "requirements_source_text": _csv_text(bundle.source_text),
                "verdict": bundle.gate.verdict.value,
                "review_status": review_status_label(bundle.gate.verdict),
                "criterion_id": _csv_text(criterion.criterion_id),
                "criterion": _csv_text(criterion.text),
                "criterion_source": criterion.criterion_source.value,
                "priority": criterion.priority.value,
                "status": finding.status.value,
                "evidence_status": evidence_status_text(coverage.evidence_status),
                "evidence_level": finding.evidence_level.value,
                "evidence_types": json.dumps(coverage.evidence_types, ensure_ascii=False),
                "confidence_band": finding.confidence_band.value,
                "evidence_count": len(finding.evidence_ids),
                "concern": _csv_text(finding.reason),
                "evidence_links": json.dumps(
                    [
                        item.permalink
                        for item in evidence_by_criterion[criterion.criterion_id]
                    ],
                    ensure_ascii=False,
                ),
                "missing_evidence": json.dumps(
                    finding.missing_evidence, ensure_ascii=False
                ),
                "human_decision": resolution.decision.value if resolution else "",
                "reviewer_decision": coverage.reviewer_decision,
                "reviewer_comment": _csv_text(resolution.comment) if resolution else "",
                "recommended_action": _csv_text(finding.recommended_action),
                "runtime_artifacts": json.dumps(
                    [item.artifact_reference for item in runtime_items], ensure_ascii=False
                ),
                "runtime_result": json.dumps(
                    [item.result for item in runtime_items], ensure_ascii=False
                ),
            }
        )
    return output.getvalue()


def export_html(value: ExportableReview) -> str:
    """Render a self-contained local acceptance report without executable content."""
    bundle, state = _bundle_and_state(value)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    coverage_by_id = {
        row.criterion_id: row for row in criterion_coverage_rows(bundle)
    }
    rows = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        coverage = coverage_by_id[criterion.criterion_id]
        evidence = "<br>".join(
            _render_candidate_reference_html(evidence_by_id[item_id])
            for item_id in finding.evidence_ids
        ) or "No candidate evidence"
        rows.append(
            "<tr>"
            f"<td>{html.escape(criterion.criterion_id)}</td>"
            f"<td>{html.escape(criterion.text)}</td>"
            f"<td>{html.escape(coverage.source)}</td>"
            f"<td>{html.escape(coverage.priority)}</td>"
            f"<td>{html.escape(evidence_status_text(coverage.evidence_status))}</td>"
            f"<td>{html.escape(', '.join(coverage.evidence_types) or 'None')}</td>"
            f"<td>{html.escape(coverage.reviewer_decision)}</td>"
            f"<td>{html.escape(finding.confidence_band.value)}</td>"
            f"<td>{len(finding.evidence_ids)}</td>"
            f"<td>{html.escape(finding.reason)}</td>"
            f"<td>{evidence}</td>"
            "</tr>"
        )
    revision = state.criteria_revision.number if state else 1
    review_status = html.escape(review_status_label(bundle.gate.verdict))
    review_created_at = bundle.review.model_dump(mode="json")["created_at"]
    guidance = gate_guidance(bundle.gate)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8">',
            "<title>ScopeProof Acceptance Review</title>",
            "<style>body{font-family:system-ui;margin:2rem;color:#172033}"
            "table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd5e1;"
            "padding:.55rem;text-align:left}th{background:#eff6ff}.note{color:#475569}"
            "pre{white-space:pre-wrap}</style>",
            "</head><body>",
            "<h1>ScopeProof Acceptance Review</h1>",
            f"<p><strong>Review status:</strong> {review_status}</p>",
            f"<p>Review ID: <code>{html.escape(bundle.review.review_id)}</code> · "
            f"Repository: <code>{html.escape(bundle.review.repository)}</code> · "
            f"PR #{bundle.review.pr_number} · Base SHA "
            f"<code>{html.escape(bundle.review.base_sha)}</code> · Head SHA "
            f"<code>{html.escape(bundle.review.head_sha)}</code> · "
            f"Review created <code>{html.escape(review_created_at)}</code> · "
            f"Tool <code>{html.escape(bundle.review.tool_version)}</code> · "
            f"Ruleset <code>{html.escape(bundle.review.ruleset_version)}</code> · "
            f"Ingestion <code>{html.escape(bundle.review.ingestion_state.value)}</code> · "
            f"Criteria revision {revision}</p>",
            "<p class=\"note\">ScopeProof surfaces auditable candidate evidence. "
            "It does not replace QA or prove correctness.</p>",
            *(
                [
                    "<h2>Ingestion Limitations</h2><ul>",
                    *[
                        f"<li>{html.escape(warning)}</li>"
                        for warning in bundle.review.ingestion_warnings
                    ],
                    *[
                        f"<li>Skipped changed file: <code>{html.escape(path)}</code></li>"
                        for path in bundle.review.skipped_files
                    ],
                    "</ul>",
                ]
                if bundle.review.ingestion_warnings or bundle.review.skipped_files
                else []
            ),
            "<h2>Confirmed Requirements Source</h2>",
            f"<pre>{html.escape(bundle.source_text)}</pre>",
            "<table><thead><tr><th>ID</th><th>Criterion</th><th>Source</th><th>Priority</th>"
            "<th>Evidence status</th><th>Evidence types</th><th>Reviewer decision</th>"
            "<th>Confidence</th><th>Count</th><th>Concern</th>"
            "<th>Evidence</th></tr></thead><tbody>",
            *rows,
            "</tbody></table>",
            *(
                [
                    "<h2>Review Status Reasons</h2><ul>",
                    *[
                        f"<li><code>{html.escape(code)}</code></li>"
                        for code in bundle.gate.reason_codes
                    ],
                    "</ul>",
                ]
                if bundle.gate.reason_codes
                else []
            ),
            *(
                [
                    "<h2>What To Do Next</h2><ul>",
                    *[f"<li>{html.escape(message)}</li>" for message in guidance],
                    "</ul>",
                ]
                if guidance
                else []
            ),
            *(
                [
                    "<h2>Manual Runtime Evidence</h2><ul>",
                    *[
                        "<li>"
                        f"{html.escape(item.criterion_id)}: "
                        f"{_render_artifact_reference_html(item.artifact_reference)} — "
                        f"{html.escape(item.scenario)}; {html.escape(item.environment)}; "
                        f"{html.escape(item.result)}; {html.escape(item.reviewer)}; "
                        f"{html.escape(item.evidence_level.value)}</li>"
                        for item in bundle.runtime_evidence
                    ],
                    "</ul>",
                ]
                if bundle.runtime_evidence
                else []
            ),
            "</body></html>",
        ]
    )
