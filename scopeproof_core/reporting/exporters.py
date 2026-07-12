"""Render one validated review bundle into consistent report formats."""

from __future__ import annotations

import csv
import html
import io
import json
from collections import defaultdict

from scopeproof_core.schemas.models import EvidenceItem, ReviewBundle, ReviewState

ExportableReview = ReviewBundle | ReviewState


def _bundle_and_state(value: ExportableReview) -> tuple[ReviewBundle, ReviewState | None]:
    if isinstance(value, ReviewState):
        if value.bundle is None:
            raise ValueError("A confirmed analysis is required before exporting a review state")
        return value.bundle, value
    return value, None


def export_json(bundle: ExportableReview) -> str:
    """Return canonical, diff-friendly JSON without adapter state or credentials."""
    payload = bundle.model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_markdown(bundle: ExportableReview) -> str:
    """Return a PR-comment-friendly report with evidence and limitations."""
    bundle, state = _bundle_and_state(bundle)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    resolution_by_id = {resolution.criterion_id: resolution for resolution in bundle.resolutions}
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    verdict = bundle.gate.verdict.value.replace("_", " ").title()
    lines = [
        "# ScopeProof Acceptance Review",
        "",
        f"**Verdict:** {verdict}",
        f"**Repository:** `{bundle.review.repository}`",
        f"**Pull request:** #{bundle.review.pr_number}",
        f"**Head SHA:** `{bundle.review.head_sha}`",
        f"**Ruleset:** `{bundle.review.ruleset_version}`",
        "",
        (
            "> ScopeProof surfaces auditable candidate evidence. "
            "It does not replace QA or prove correctness."
        ),
        "",
        "## Evidence Matrix",
        "",
        "| Criterion | Priority | Status | Level | Human decision |",
        "|---|---|---|---|---|",
    ]
    if state is not None:
        lines.insert(7, f"**Criteria revision: {state.criteria_revision.number}**")
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        resolution = resolution_by_id.get(criterion.criterion_id)
        decision = resolution.decision.value if resolution else "Unresolved"
        lines.append(
            f"| {criterion.criterion_id}: {criterion.text} | {criterion.priority.value} | "
            f"{finding.status.value} | {finding.evidence_level.value} | {decision} |"
        )

    lines.extend(["", "## Criterion Details", ""])
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        lines.extend(
            [
                f"### {criterion.criterion_id} — {criterion.text}",
                "",
                f"**Finding:** {finding.status.value}",
                f"**Reason:** {finding.reason}",
            ]
        )
        if finding.missing_evidence:
            lines.extend(
                ["", "**Missing evidence:**", *[f"- {item}" for item in finding.missing_evidence]]
            )
        candidates = [evidence_by_id[item_id] for item_id in finding.evidence_ids]
        if candidates:
            lines.extend(["", "**Candidate evidence:**"])
            for candidate in candidates:
                lines.append(
                    f"- [{candidate.file_path}:L{candidate.line_start}]({candidate.permalink}) — "
                    f"{candidate.relevance_reason}"
                )
                lines.append(f"  - Excerpt: `{candidate.excerpt}`")
                for limitation in candidate.limitations:
                    lines.append(f"  - Limitation: {limitation}")
        resolution = resolution_by_id.get(criterion.criterion_id)
        if resolution:
            lines.extend(
                [
                    "",
                    f"**Human resolution:** {resolution.decision.value}",
                    f"**Reviewer note:** {resolution.comment or 'No note provided'}",
                ]
            )
        lines.extend(["", f"**Recommended action:** {finding.recommended_action}", ""])

    if bundle.runtime_evidence:
        lines.extend(["## Manual Runtime Evidence", ""])
        for item in bundle.runtime_evidence:
            lines.extend(
                [
                    f"- **{item.criterion_id}** — "
                    f"[{item.artifact_reference}]({item.artifact_reference})",
                    f"  - Scenario: {item.scenario}",
                    f"  - Environment: {item.environment}; result: {item.result}; "
                    f"reviewer: {item.reviewer}; level: {item.evidence_level.value}",
                    f"  - Limitations: {', '.join(item.limitations) or 'None recorded'}",
                ]
            )
        lines.append("")

    if bundle.gate.reason_codes:
        lines.extend(
            ["## Gate Reasons", "", *[f"- `{code}`" for code in bundle.gate.reason_codes], ""]
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
            lines.append(f"- {target}: {outcome} — {event.comment or 'No note provided'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _links(items: list[EvidenceItem]) -> str:
    return " | ".join(item.permalink for item in items)


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
        "head_sha",
        "ruleset_version",
        "criteria_revision",
        "verdict",
        "criterion_id",
        "criterion",
        "priority",
        "status",
        "evidence_level",
        "confidence_band",
        "evidence_links",
        "missing_evidence",
        "human_decision",
        "reviewer_comment",
        "recommended_action",
        "runtime_artifacts",
        "runtime_result",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        resolution = resolution_by_id.get(criterion.criterion_id)
        runtime_items = [
            item for item in bundle.runtime_evidence if item.criterion_id == criterion.criterion_id
        ]
        writer.writerow(
            {
                "review_id": bundle.review.review_id,
                "repository": bundle.review.repository,
                "pr_number": bundle.review.pr_number,
                "head_sha": bundle.review.head_sha,
                "ruleset_version": bundle.review.ruleset_version,
                "criteria_revision": state.criteria_revision.number if state else 1,
                "verdict": bundle.gate.verdict.value,
                "criterion_id": criterion.criterion_id,
                "criterion": criterion.text,
                "priority": criterion.priority.value,
                "status": finding.status.value,
                "evidence_level": finding.evidence_level.value,
                "confidence_band": finding.confidence_band.value,
                "evidence_links": _links(evidence_by_criterion[criterion.criterion_id]),
                "missing_evidence": " | ".join(finding.missing_evidence),
                "human_decision": resolution.decision.value if resolution else "",
                "reviewer_comment": resolution.comment if resolution else "",
                "recommended_action": finding.recommended_action,
                "runtime_artifacts": " | ".join(item.artifact_reference for item in runtime_items),
                "runtime_result": " | ".join(item.result for item in runtime_items),
            }
        )
    return output.getvalue()


def export_html(value: ExportableReview) -> str:
    """Render a self-contained local acceptance report without executable content."""
    bundle, state = _bundle_and_state(value)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    rows = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        evidence = "<br>".join(
            (
                f'<a href="{html.escape(evidence_by_id[item_id].permalink, quote=True)}">'
                f"{html.escape(evidence_by_id[item_id].file_path)}"
                f":L{evidence_by_id[item_id].line_start}</a>"
                f"<br><code>{html.escape(evidence_by_id[item_id].excerpt)}</code>"
            )
            for item_id in finding.evidence_ids
        ) or "No candidate evidence"
        rows.append(
            "<tr>"
            f"<td>{html.escape(criterion.criterion_id)}</td>"
            f"<td>{html.escape(criterion.text)}</td>"
            f"<td>{html.escape(criterion.priority.value)}</td>"
            f"<td>{html.escape(finding.status.value)}</td>"
            f"<td>{html.escape(finding.evidence_level.value)}</td>"
            f"<td>{evidence}</td>"
            "</tr>"
        )
    revision = state.criteria_revision.number if state else 1
    verdict = html.escape(bundle.gate.verdict.value.replace("_", " ").title())
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8">',
            "<title>ScopeProof Acceptance Review</title>",
            "<style>body{font-family:system-ui;margin:2rem;color:#172033}"
            "table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd5e1;"
            "padding:.55rem;text-align:left}th{background:#eff6ff}.note{color:#475569}</style>",
            "</head><body>",
            "<h1>ScopeProof Acceptance Review</h1>",
            f"<p><strong>Verdict:</strong> {verdict}</p>",
            f"<p>Repository: <code>{html.escape(bundle.review.repository)}</code> · "
            f"PR #{bundle.review.pr_number} · Head SHA "
            f"<code>{html.escape(bundle.review.head_sha)}</code> · "
            f"Criteria revision {revision}</p>",
            "<p class=\"note\">ScopeProof surfaces auditable candidate evidence. "
            "It does not replace QA or prove correctness.</p>",
            "<table><thead><tr><th>ID</th><th>Criterion</th><th>Priority</th>"
            "<th>Status</th><th>Level</th><th>Evidence</th></tr></thead><tbody>",
            *rows,
            "</tbody></table>",
            *(
                [
                    "<h2>Manual Runtime Evidence</h2><ul>",
                    *[
                        "<li>"
                        f"{html.escape(item.criterion_id)}: "
                        f"<a href=\"{html.escape(item.artifact_reference, quote=True)}\">"
                        f"{html.escape(item.artifact_reference)}</a> — "
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
