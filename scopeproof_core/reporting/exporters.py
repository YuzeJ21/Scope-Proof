"""Render one validated review bundle into consistent report formats."""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict

from scopeproof_core.schemas.models import EvidenceItem, ReviewBundle


def export_json(bundle: ReviewBundle) -> str:
    """Return canonical, diff-friendly JSON without adapter state or credentials."""
    payload = bundle.model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_markdown(bundle: ReviewBundle) -> str:
    """Return a PR-comment-friendly report with evidence and limitations."""
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

    if bundle.gate.reason_codes:
        lines.extend(
            ["## Gate Reasons", "", *[f"- `{code}`" for code in bundle.gate.reason_codes], ""]
        )
    return "\n".join(lines).rstrip() + "\n"


def _links(items: list[EvidenceItem]) -> str:
    return " | ".join(item.permalink for item in items)


def export_csv(bundle: ReviewBundle) -> str:
    """Return one flat audit row per criterion."""
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
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        resolution = resolution_by_id.get(criterion.criterion_id)
        writer.writerow(
            {
                "review_id": bundle.review.review_id,
                "repository": bundle.review.repository,
                "pr_number": bundle.review.pr_number,
                "head_sha": bundle.review.head_sha,
                "ruleset_version": bundle.review.ruleset_version,
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
            }
        )
    return output.getvalue()
