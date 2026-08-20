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
from scopeproof_core.reviews.comparison import (
    EvidenceReference,
    ReviewComparison,
)
from scopeproof_core.schemas.models import (
    JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION,
    CriteriaSourceProvenance,
    CriterionRetrievalDiagnostic,
    EvidenceItem,
    HumanDecision,
    JUnitCaseResult,
    JUnitEvidenceImport,
    ReviewBundle,
    ReviewState,
)

ExportableReview = ReviewBundle | ReviewState

_MARKDOWN_PUNCTUATION = frozenset(set(string.punctuation) - {"&", ";"})
_SPREADSHEET_FORMULA_PREFIXES = frozenset(("=", "+", "-", "@", "\t", "\r"))
_RETRIEVAL_BOUNDARY = (
    "Search diagnostics explain retrieval; they are not evidence that the criterion "
    "is satisfied or missing from the repository."
)
_RETRIEVAL_FALLBACK = "Retrieval diagnostics were not recorded for this review."
_LEGACY_RUNTIME_LINK = "Legacy unlinked; re-record at the active head"
_EXPORT_PROVENANCE_REQUIRED = "criteria source provenance is required for export"


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
        validated = ReviewState.model_validate(value.model_dump(mode="python"))
        if validated.review.criteria_source_provenance is None:
            raise ValueError(_EXPORT_PROVENANCE_REQUIRED)
        return validated_review_state(validated)
    validated = ReviewBundle.model_validate(value.model_dump(mode="python"))
    if validated.review.criteria_source_provenance is None:
        raise ValueError(_EXPORT_PROVENANCE_REQUIRED)
    return validated_review_bundle(validated)


def _bundle_and_state(value: ExportableReview) -> tuple[ReviewBundle, ReviewState | None]:
    value = _validated_exportable(value)
    if isinstance(value, ReviewState):
        if value.bundle is None:
            raise ValueError("A confirmed analysis is required before exporting a review state")
        return value.bundle, value
    return value, None


def _criteria_source_provenance(bundle: ReviewBundle) -> CriteriaSourceProvenance:
    """Return the provenance already required at the shared export boundary."""
    provenance = bundle.review.criteria_source_provenance
    if provenance is None:  # Defensive: callers should enter through _validated_exportable.
        raise ValueError(_EXPORT_PROVENANCE_REQUIRED)
    return provenance


def _provenance_timestamp(provenance: CriteriaSourceProvenance) -> str:
    return provenance.model_dump(mode="json")["confirmed_at"]


def _retrieval_outcome_label(diagnostic: CriterionRetrievalDiagnostic) -> str:
    return diagnostic.outcome.value.replace("_", " ").title()


def _retrieval_diagnostic_markdown(
    diagnostic: CriterionRetrievalDiagnostic | None,
) -> list[str]:
    if diagnostic is None:
        return ["", "**How ScopeProof searched:**", _RETRIEVAL_FALLBACK]
    searched_paths = (
        ", ".join(_render_markdown_code(path) for path in diagnostic.searched_paths) or "None"
    )
    return [
        "",
        "**How ScopeProof searched:**",
        f"- Outcome: {_retrieval_outcome_label(diagnostic)}",
        "- Searched terms: "
        + (", ".join(_render_markdown_code(term) for term in diagnostic.searched_terms) or "None"),
        "- Exact identifiers: "
        + (
            ", ".join(
                _render_markdown_code(identifier) for identifier in diagnostic.exact_identifiers
            )
            or "None"
        ),
        f"- Searched paths: {searched_paths}",
        "- Searched evidence types: "
        + (
            ", ".join(
                _escape_markdown_text(item.value) for item in diagnostic.searched_evidence_types
            )
            or "None"
        ),
        (
            "- Counts: "
            f"{diagnostic.inspectable_line_count} inspectable lines; "
            f"{diagnostic.exact_identifier_match_line_count} exact-identifier matches; "
            f"{diagnostic.term_overlap_line_count} term-overlap lines; "
            f"{diagnostic.below_threshold_line_count} below threshold; "
            f"{diagnostic.accepted_candidate_count} accepted candidates."
        ),
        _RETRIEVAL_BOUNDARY,
    ]


def _retrieval_diagnostic_html(
    criterion_id: str,
    diagnostic: CriterionRetrievalDiagnostic | None,
) -> str:
    heading = f"<h3>{html.escape(criterion_id)} — How ScopeProof searched</h3>"
    if diagnostic is None:
        return heading + f"<p>{html.escape(_RETRIEVAL_FALLBACK)}</p>"
    searched_paths = (
        ", ".join(f"<code>{html.escape(path)}</code>" for path in diagnostic.searched_paths)
        or "None"
    )
    searched_terms = (
        ", ".join(f"<code>{html.escape(term)}</code>" for term in diagnostic.searched_terms)
        or "None"
    )
    exact_identifiers = (
        ", ".join(
            f"<code>{html.escape(identifier)}</code>"
            for identifier in diagnostic.exact_identifiers
        )
        or "None"
    )
    evidence_types = (
        ", ".join(html.escape(item.value) for item in diagnostic.searched_evidence_types)
        or "None"
    )
    return "".join(
        [
            heading,
            "<ul>",
            f"<li>Outcome: {html.escape(_retrieval_outcome_label(diagnostic))}</li>",
            f"<li>Searched terms: {searched_terms}</li>",
            f"<li>Exact identifiers: {exact_identifiers}</li>",
            f"<li>Searched paths: {searched_paths}</li>",
            f"<li>Searched evidence types: {evidence_types}</li>",
            "<li>Counts: "
            f"{diagnostic.inspectable_line_count} inspectable lines; "
            f"{diagnostic.exact_identifier_match_line_count} exact-identifier matches; "
            f"{diagnostic.term_overlap_line_count} term-overlap lines; "
            f"{diagnostic.below_threshold_line_count} below threshold; "
            f"{diagnostic.accepted_candidate_count} accepted candidates.</li>",
            "</ul>",
            f'<p class="note">{html.escape(_RETRIEVAL_BOUNDARY)}</p>',
        ]
    )


def _junit_mapping_cases(
    evidence_import: JUnitEvidenceImport, criterion_id: str
) -> list[JUnitCaseResult]:
    mapped_ids = {
        case_id
        for mapping in evidence_import.criterion_mappings
        if mapping.criterion_id == criterion_id
        for case_id in mapping.test_case_ids
    }
    return [
        item for item in evidence_import.test_cases if item.test_case_id in mapped_ids
    ]


def _junit_import_markdown(bundle: ReviewBundle) -> list[str]:
    lines = [
        "## Imported External Test Results",
        "",
        JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION,
        "",
    ]
    if not bundle.junit_evidence_imports:
        return [*lines, "No external JUnit results were imported.", ""]
    for evidence_import in bundle.junit_evidence_imports:
        lines.extend(
            [
                f"### Import {_render_markdown_code(evidence_import.import_id)}",
                "",
                f"- Artifact SHA-256: {_render_markdown_code(evidence_import.artifact_sha256)}",
                f"- Bound head: {_render_markdown_code(evidence_import.head_sha)}",
                f"- Asserted importer: {_render_markdown_code(evidence_import.imported_by)}",
                "- Computed totals: "
                f"{evidence_import.totals.total} total; "
                f"{evidence_import.totals.passed} passed; "
                f"{evidence_import.totals.failures} failed; "
                f"{evidence_import.totals.errors} errors; "
                f"{evidence_import.totals.skipped} skipped.",
                "- Explicit mappings:",
            ]
        )
        cases_by_id = {
            item.test_case_id: item for item in evidence_import.test_cases
        }
        for mapping in evidence_import.criterion_mappings:
            lines.append(f"  - Criterion {_render_markdown_code(mapping.criterion_id)}")
            for case_id in mapping.test_case_ids:
                case = cases_by_id[case_id]
                lines.append(
                    "    - "
                    f"{_render_markdown_code(case.test_case_id)} · "
                    f"{_render_markdown_code(case.status.value)} · "
                    f"{_render_markdown_code(case.suite_name)} · "
                    f"{_render_markdown_code(case.test_name)}"
                )
        if evidence_import.parser_warnings:
            lines.append("- Parser warnings:")
            lines.extend(
                f"  - {_render_markdown_code(item)}"
                for item in evidence_import.parser_warnings
            )
        lines.append("- Limitations:")
        lines.extend(
            f"  - {_render_markdown_code(item)}" for item in evidence_import.limitations
        )
        lines.append("")
    return lines


def _junit_import_html(bundle: ReviewBundle) -> list[str]:
    lines = [
        "<h2>Imported external test results</h2>",
        f'<p class="note">{html.escape(JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION)}</p>',
    ]
    if not bundle.junit_evidence_imports:
        return [*lines, "<p>No external JUnit results were imported.</p>"]
    for evidence_import in bundle.junit_evidence_imports:
        cases_by_id = {
            item.test_case_id: item for item in evidence_import.test_cases
        }
        lines.extend(
            [
                f"<h3>Import <code>{html.escape(evidence_import.import_id)}</code></h3>",
                "<ul>",
                "<li>Artifact SHA-256: "
                f"<code>{html.escape(evidence_import.artifact_sha256)}</code></li>",
                f"<li>Bound head: <code>{html.escape(evidence_import.head_sha)}</code></li>",
                "<li>Asserted importer: "
                f"<code>{html.escape(evidence_import.imported_by)}</code></li>",
                "<li>Explicit mappings:<ul>",
            ]
        )
        for mapping in evidence_import.criterion_mappings:
            lines.append(
                f"<li>Criterion <code>{html.escape(mapping.criterion_id)}</code><ul>"
            )
            for case_id in mapping.test_case_ids:
                case = cases_by_id[case_id]
                lines.append(
                    "<li>"
                    f"<code>{html.escape(case.test_case_id)}</code> · "
                    f"<code>{html.escape(case.status.value)}</code> · "
                    f"<code>{html.escape(case.suite_name)}</code> · "
                    f"<code>{html.escape(case.test_name)}</code></li>"
                )
            lines.append("</ul></li>")
        lines.extend(["</ul></li>"])
        if evidence_import.parser_warnings:
            lines.extend(
                [
                    "<li>Parser warnings:<ul>",
                    *[
                        f"<li><code>{html.escape(item)}</code></li>"
                        for item in evidence_import.parser_warnings
                    ],
                    "</ul></li>",
                ]
            )
        lines.extend(
            [
                "<li>Limitations:<ul>",
                *[
                    f"<li><code>{html.escape(item)}</code></li>"
                    for item in evidence_import.limitations
                ],
                "</ul></li>",
                "</ul>",
            ]
        )
    return lines


def export_json(bundle: ExportableReview) -> str:
    """Return canonical, diff-friendly JSON without adapter state or credentials."""
    payload = _validated_exportable(bundle).model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _validated_comparison(comparison: ReviewComparison) -> ReviewComparison:
    """Revalidate mutable comparison input before rendering an export artifact."""

    return ReviewComparison.model_validate(
        comparison.model_dump(mode="python", exclude={"evidence_change_counts"})
    )


def export_comparison_json(comparison: ReviewComparison) -> str:
    """Return canonical JSON for a validated re-review comparison."""

    payload = _validated_comparison(comparison).model_dump(mode="json")
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _comparison_reference_markdown(label: str, reference: EvidenceReference) -> list[str]:
    location = f"{_escape_markdown_text(reference.file_path)}:L{reference.line_start}"
    if is_linkable_artifact_reference(reference.permalink):
        destination = html.escape(reference.permalink, quote=True)
        rendered_location = f"[{location}](<{destination}>)"
    else:
        rendered_location = f"{location} — permalink: {_escape_markdown_text(reference.permalink)}"
    return [
        f"- **{label}:** {rendered_location}",
        f"  - Evidence ID: {_render_markdown_code(reference.evidence_id)}",
        f"  - Commit: {_render_markdown_code(reference.commit_sha)}",
        f"  - Excerpt: {_render_markdown_code(reference.excerpt)}",
    ]


def export_comparison_markdown(comparison: ReviewComparison) -> str:
    """Render an inspectable, evidence-bound re-review comparison."""

    comparison = _validated_comparison(comparison)
    counts = comparison.evidence_change_counts
    lines = [
        "# ScopeProof Re-review Comparison",
        "",
        f"**Previous head:** {_render_markdown_code(comparison.previous_head_sha)}",
        f"**Current head:** {_render_markdown_code(comparison.current_head_sha)}",
        f"**Previous review status:** {_render_markdown_code(comparison.previous_gate.value)}",
        f"**Current review status:** {_render_markdown_code(comparison.current_gate.value)}",
        "",
        (
            "> ScopeProof compares auditable candidate references. Candidate comparison does not "
            "prove criterion satisfaction."
        ),
        "",
        "## Evidence Change Counts",
        "",
        f"- Modified: {counts.modified}",
        f"- Relocated: {counts.relocated}",
        f"- Added: {counts.added}",
        f"- Removed: {counts.removed}",
        f"- Unchanged: {counts.unchanged}",
        "",
        "## Evidence Changes",
        "",
    ]
    for change in comparison.evidence_changes:
        kind = change.kind.value.replace("_", " ").title()
        lines.extend(
            [
                f"### {_escape_markdown_text(change.criterion_id)} — {kind}",
                "",
                f"**Reason:** {_escape_markdown_text(change.reason)}",
            ]
        )
        if change.previous is not None:
            lines.extend(_comparison_reference_markdown("Previous candidate", change.previous))
        if change.current is not None:
            lines.extend(_comparison_reference_markdown("Current candidate", change.current))
        if change.kind.value != "unchanged":
            lines.append("- Review the current evidence before recording a new decision.")
        lines.append("")

    lines.extend(
        [
            "## Imported External Test Result Changes",
            "",
            JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION,
            "",
        ]
    )
    if not comparison.junit_import_changes:
        lines.extend(["No imported JUnit context was present in either review.", ""])
    for change in comparison.junit_import_changes:
        lines.extend(
            [
                "### "
                f"{_render_markdown_code(change.artifact_sha256)} — "
                f"{_escape_markdown_text(change.kind.value.replace('_', ' ').title())}",
                "",
            ]
        )
        for label, reference in (
            ("Previous import", change.previous),
            ("Current import", change.current),
        ):
            if reference is None:
                continue
            lines.extend(
                [
                    f"- **{label}:** {_render_markdown_code(reference.import_id)}",
                    f"  - Bound head: {_render_markdown_code(reference.head_sha)}",
                    "  - Asserted importer: "
                    f"{_render_markdown_code(reference.asserted_importer)}",
                    "  - Explicit mappings:",
                ]
            )
            for mapping in reference.mappings:
                lines.append(
                    f"    - {_render_markdown_code(mapping.criterion_id)}: "
                    + ", ".join(
                        _render_markdown_code(case_id)
                        for case_id in mapping.test_case_ids
                    )
                )
        lines.append("")

    if comparison.changed_finding_statuses:
        lines.extend(["## Changed Criterion Findings", ""])
        for change in comparison.changed_finding_statuses:
            previous = change.previous_status.value if change.previous_status else "none"
            current = change.current_status.value if change.current_status else "none"
            lines.append(
                f"- {_escape_markdown_text(change.criterion_id)}: "
                f"{_render_markdown_code(previous)} → {_render_markdown_code(current)}"
            )
        lines.append("")
    if comparison.changed_human_resolutions:
        lines.extend(["## Changed Reviewer Decisions", ""])
        for change in comparison.changed_human_resolutions:
            previous = change.previous_decision.value if change.previous_decision else "none"
            current = change.current_decision.value if change.current_decision else "none"
            lines.append(
                f"- {_escape_markdown_text(change.criterion_id)}: "
                f"{_render_markdown_code(previous)} → {_render_markdown_code(current)}"
            )
        lines.append("")
    if comparison.criteria_requiring_decision_review:
        lines.extend(
            [
                "## Prior Decisions Requiring Review",
                "",
                *[
                    f"- {_escape_markdown_text(criterion_id)}"
                    for criterion_id in comparison.criteria_requiring_decision_review
                ],
                "",
                (
                    "ScopeProof never carries acceptance to a changed head. Review current "
                    "evidence and record a new decision."
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## Comparison Boundary",
            "",
            (
                "This report describes deterministic candidate-reference changes only. It does "
                "not carry forward a prior human decision or replace review of the current head."
            ),
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def export_markdown(bundle: ExportableReview) -> str:
    """Return a PR-comment-friendly report with evidence and limitations."""
    bundle, state = _bundle_and_state(bundle)
    provenance = _criteria_source_provenance(bundle)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    resolution_by_id = {resolution.criterion_id: resolution for resolution in bundle.resolutions}
    linked_runtime_ids = {
        resolution.runtime_evidence_id
        for resolution in bundle.resolutions
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED
        and resolution.runtime_evidence_id is not None
    }
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    diagnostic_by_id = {
        diagnostic.criterion_id: diagnostic for diagnostic in bundle.retrieval_diagnostics
    }
    review_status = review_status_label(bundle.gate.verdict)
    coverage_by_id = {row.criterion_id: row for row in criterion_coverage_rows(bundle)}
    review_created_at = bundle.review.model_dump(mode="json")["created_at"]
    lines = [
        "# ScopeProof Acceptance Review",
        "",
        f"**Review status:** {review_status}",
        f"**Review ID:** {_render_markdown_code(bundle.review.review_id)}",
        f"**Repository:** {_render_markdown_code(bundle.review.repository)}",
        "**Repository visibility:** "
        f"{_render_markdown_code(bundle.review.repository_visibility.value)}",
        f"**Pull request:** #{bundle.review.pr_number}",
        f"**Base SHA:** {_render_markdown_code(bundle.review.base_sha)}",
        f"**Head SHA:** {_render_markdown_code(bundle.review.head_sha)}",
        f"**Review created:** {_render_markdown_code(review_created_at)}",
        f"**Tool version:** {_render_markdown_code(bundle.review.tool_version)}",
        f"**Ruleset:** {_render_markdown_code(bundle.review.ruleset_version)}",
        f"**Ingestion state:** {_render_markdown_code(bundle.review.ingestion_state.value)}",
        f"**Observed CI:** {bundle.review.ci_observation.state.value}",
        f"**Observed CI reason:** {_escape_markdown_text(bundle.review.ci_observation.reason)}",
        "**Observed CI check runs:** "
        f"{bundle.review.ci_observation.total_check_runs} total; "
        f"{bundle.review.ci_observation.successful_check_runs} successful; "
        f"{bundle.review.ci_observation.pending_check_runs} pending; "
        f"{bundle.review.ci_observation.failing_check_runs} failing; "
        f"{bundle.review.ci_observation.neutral_check_runs} neutral; "
        f"{bundle.review.ci_observation.skipped_check_runs} skipped; "
        f"{bundle.review.ci_observation.concrete_legacy_status_count} concrete legacy statuses.",
        "**CI collection completeness:** "
        f"{'complete' if bundle.review.ci_observation.collection_complete else 'incomplete'}",
        *(
            [
                "**CI collection diagnostics:**",
                *[
                    f"  - {_escape_markdown_text(note)}"
                    for note in bundle.review.ci_observation.collection_notes
                ],
            ]
            if bundle.review.ci_observation.collection_notes
            else []
        ),
        *(
            [
                "**Skipped CI checks:** "
                + ", ".join(
                    _escape_markdown_text(name)
                    for name in bundle.review.ci_observation.skipped_check_names
                )
            ]
            if bundle.review.ci_observation.skipped_check_names
            else []
        ),
        *([f"**Criteria revision: {state.criteria_revision.number}**"] if state else []),
        "",
        (
            "> ScopeProof surfaces auditable candidate evidence. "
            "It does not replace QA or prove correctness."
        ),
        "",
        "## Criteria Source",
        "",
        "| Field | Confirmed snapshot |",
        "|---|---|",
        f"| Source reference | {_render_markdown_code(provenance.source_uri)} |",
        "| Revision | "
        + (
            _render_markdown_code(provenance.source_revision)
            if provenance.source_revision is not None
            else "Not supplied"
        )
        + " |",
        f"| Source-text SHA-256 | {_render_markdown_code(provenance.source_text_sha256)} |",
        "| Normalized-criteria SHA-256 | "
        f"{_render_markdown_code(provenance.normalized_criteria_sha256)} |",
        f"| Confirmed by | {_render_markdown_code(provenance.confirmed_by)} |",
        f"| Confirmed at (UTC) | {_render_markdown_code(_provenance_timestamp(provenance))} |",
        "",
        *(
            [
                "## Research Boundary",
                "",
                f"**Case ID:** {_render_markdown_code(bundle.research_context.case_id)}",
                "**Classification:** public engineering research",
                "**Stage 1 credit:** 0 (permanently excluded)",
                _escape_markdown_text(bundle.research_context.boundary_note),
                "",
            ]
            if bundle.research_context is not None
            else []
        ),
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
        *[f"> {_escape_markdown_text(line)}" for line in (bundle.source_text.splitlines() or [""])],
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
        criterion_label = _escape_markdown_text(f"{criterion.criterion_id}: {criterion.text}")
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
                f"**Evidence status:** {evidence_status_text(coverage.evidence_status)}",
                f"**Reason:** {_escape_markdown_text(finding.reason)}",
            ]
        )
        lines.extend(_retrieval_diagnostic_markdown(diagnostic_by_id.get(criterion.criterion_id)))
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
                    f"- {candidate_reference} — {_escape_markdown_text(candidate.relevance_reason)}"
                )
                lines.append(f"  - Type and level: {_candidate_evidence_label(candidate)}")
                lines.append(f"  - Excerpt: {_render_markdown_code(candidate.excerpt)}")
                if candidate.context_excerpt:
                    lines.append(f"  - Context: {_render_markdown_code(candidate.context_excerpt)}")
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
            if resolution.decision is HumanDecision.MANUALLY_VERIFIED:
                lines.append(
                    "**Manual resolution link:** "
                    + (
                        _render_markdown_code(resolution.runtime_evidence_id)
                        if resolution.runtime_evidence_id is not None
                        else _LEGACY_RUNTIME_LINK
                    )
                )
        lines.extend(
            [
                "",
                f"**Recommended action:** {_escape_markdown_text(finding.recommended_action)}",
                "",
            ]
        )

    lines.extend(_junit_import_markdown(bundle))
    lines.extend(
        [
            "## Runtime Verification Boundary",
            "",
            (
                "Manual runtime evidence is recorded separately below. Observed CI and static "
                "candidates do not establish runtime verification."
                if bundle.runtime_evidence
                else "No manual runtime verification was recorded. Observed CI and static "
                "candidates do not establish runtime verification."
            ),
            "",
        ]
    )
    if bundle.runtime_evidence:
        lines.extend(["## Manual Runtime Evidence", ""])
        for item in bundle.runtime_evidence:
            if item.runtime_evidence_id is None:
                identity_lines = [
                    f"  - Runtime identity: {_LEGACY_RUNTIME_LINK}",
                    f"  - Manual resolution link: {_LEGACY_RUNTIME_LINK}",
                ]
            else:
                identity_lines = [
                    f"  - Runtime evidence ID: {_render_markdown_code(item.runtime_evidence_id)}",
                    "  - Repository / PR: "
                    f"{_render_markdown_code(item.repository or '')} / #{item.pr_number}",
                    f"  - Bound head: {_render_markdown_code(item.head_sha or '')}",
                    "  - Manual resolution link: "
                    + (
                        _render_markdown_code(item.runtime_evidence_id)
                        if item.runtime_evidence_id in linked_runtime_ids
                        else "Not linked to a current manual resolution"
                    ),
                ]
            lines.extend(
                [
                    f"- **{_escape_markdown_text(item.criterion_id)}** — "
                    f"{render_artifact_reference_markdown(item.artifact_reference)}",
                    *identity_lines,
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
                event.decision.value if event.decision else str(event.final_acceptance).lower()
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
    context = f"<br><pre>{html.escape(item.context_excerpt)}</pre>" if item.context_excerpt else ""
    return (
        f"{reference}<br>{html.escape(_candidate_evidence_label(item))}"
        f"<br><code>{html.escape(item.excerpt)}</code>{context}"
    )


def _candidate_evidence_label(item: EvidenceItem) -> str:
    """Name static candidate evidence without claiming it was executed."""
    label = f"{item.evidence_type.value.title()} ({item.evidence_level.value}"
    if item.evidence_type.value == "test":
        label += "; test/eval definition shows intent, not execution"
    return label + ")"


def export_csv(bundle: ExportableReview) -> str:
    """Return one flat audit row per criterion."""
    bundle, state = _bundle_and_state(bundle)
    provenance = _criteria_source_provenance(bundle)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    resolution_by_id = {resolution.criterion_id: resolution for resolution in bundle.resolutions}
    diagnostic_by_id = {
        diagnostic.criterion_id: diagnostic for diagnostic in bundle.retrieval_diagnostics
    }
    evidence_by_criterion: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in bundle.evidence:
        evidence_by_criterion[item.criterion_id].append(item)

    fieldnames = [
        "review_id",
        "repository",
        "repository_visibility",
        "pr_number",
        "base_sha",
        "head_sha",
        "review_created_at",
        "tool_version",
        "ruleset_version",
        "ingestion_state",
        "ingestion_warnings",
        "skipped_files",
        "ci_state",
        "ci_reason",
        "ci_total_check_runs",
        "ci_successful_check_runs",
        "ci_pending_check_runs",
        "ci_failing_check_runs",
        "ci_neutral_check_runs",
        "ci_skipped_check_runs",
        "ci_concrete_legacy_status_count",
        "ci_skipped_check_names",
        "ci_collection_complete",
        "ci_collection_notes",
        "research_case_id",
        "research_classification",
        "stage1_credit",
        "research_boundary_note",
        "candidate_evidence_proves_correctness",
        "runtime_verification_state",
        "reviewer_decision_state",
        "criteria_revision",
        "criteria_source_uri",
        "criteria_source_revision",
        "criteria_source_text_sha256",
        "criteria_normalized_criteria_sha256",
        "criteria_confirmed_by",
        "criteria_confirmed_at",
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
        "candidate_evidence",
        "confidence_band",
        "evidence_count",
        "concern",
        "evidence_links",
        "retrieval_diagnostic",
        "missing_evidence",
        "human_decision",
        "reviewer_decision",
        "reviewer_comment",
        "recommended_action",
        "runtime_artifacts",
        "runtime_result",
        "runtime_evidence_ids",
        "runtime_repositories",
        "runtime_pr_numbers",
        "runtime_head_shas",
        "manual_runtime_evidence_id",
        "junit_artifact_digests",
        "junit_mapped_cases",
        "junit_evidence_boundary",
        "junit_importers",
        "junit_parser_warnings",
        "junit_limitations",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\r\n")
    writer.writeheader()
    coverage_by_id = {row.criterion_id: row for row in criterion_coverage_rows(bundle)}
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        resolution = resolution_by_id.get(criterion.criterion_id)
        coverage = coverage_by_id[criterion.criterion_id]
        runtime_items = [
            item for item in bundle.runtime_evidence if item.criterion_id == criterion.criterion_id
        ]
        junit_imports = [
            item
            for item in bundle.junit_evidence_imports
            if any(
                mapping.criterion_id == criterion.criterion_id
                for mapping in item.criterion_mappings
            )
        ]
        writer.writerow(
            {
                "review_id": _csv_text(bundle.review.review_id),
                "repository": _csv_text(bundle.review.repository),
                "repository_visibility": bundle.review.repository_visibility.value,
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
                "ci_state": bundle.review.ci_observation.state.value,
                "ci_reason": _csv_text(bundle.review.ci_observation.reason),
                "ci_total_check_runs": bundle.review.ci_observation.total_check_runs,
                "ci_successful_check_runs": bundle.review.ci_observation.successful_check_runs,
                "ci_pending_check_runs": bundle.review.ci_observation.pending_check_runs,
                "ci_failing_check_runs": bundle.review.ci_observation.failing_check_runs,
                "ci_neutral_check_runs": bundle.review.ci_observation.neutral_check_runs,
                "ci_skipped_check_runs": bundle.review.ci_observation.skipped_check_runs,
                "ci_concrete_legacy_status_count": (
                    bundle.review.ci_observation.concrete_legacy_status_count
                ),
                "ci_skipped_check_names": json.dumps(
                    bundle.review.ci_observation.skipped_check_names, ensure_ascii=False
                ),
                "ci_collection_complete": bundle.review.ci_observation.collection_complete,
                "ci_collection_notes": _csv_text(
                    json.dumps(
                        bundle.review.ci_observation.collection_notes,
                        ensure_ascii=False,
                    )
                ),
                "research_case_id": _csv_text(bundle.research_context.case_id)
                if bundle.research_context
                else "",
                "research_classification": bundle.research_context.classification
                if bundle.research_context
                else "",
                "stage1_credit": bundle.research_context.stage1_credit
                if bundle.research_context
                else "",
                "research_boundary_note": _csv_text(bundle.research_context.boundary_note)
                if bundle.research_context
                else "",
                "candidate_evidence_proves_correctness": (
                    bundle.candidate_evidence_proves_correctness
                ),
                "runtime_verification_state": bundle.runtime_verification_state.value,
                "reviewer_decision_state": bundle.reviewer_decision_state.value,
                "criteria_revision": state.criteria_revision.number if state else 1,
                "criteria_source_uri": _csv_text(provenance.source_uri),
                "criteria_source_revision": (
                    _csv_text(provenance.source_revision)
                    if provenance.source_revision is not None
                    else ""
                ),
                "criteria_source_text_sha256": provenance.source_text_sha256,
                "criteria_normalized_criteria_sha256": (provenance.normalized_criteria_sha256),
                "criteria_confirmed_by": _csv_text(provenance.confirmed_by),
                "criteria_confirmed_at": _provenance_timestamp(provenance),
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
                "candidate_evidence": json.dumps(
                    [
                        {
                            "evidence_id": item.evidence_id,
                            "type": item.evidence_type.value,
                            "level": item.evidence_level.value,
                            "boundary": _candidate_evidence_label(item),
                        }
                        for item in evidence_by_criterion[criterion.criterion_id]
                    ],
                    ensure_ascii=False,
                ),
                "confidence_band": finding.confidence_band.value,
                "evidence_count": len(finding.evidence_ids),
                "concern": _csv_text(finding.reason),
                "evidence_links": json.dumps(
                    [item.permalink for item in evidence_by_criterion[criterion.criterion_id]],
                    ensure_ascii=False,
                ),
                "retrieval_diagnostic": json.dumps(
                    (
                        diagnostic_by_id[criterion.criterion_id].model_dump(mode="json")
                        if criterion.criterion_id in diagnostic_by_id
                        else None
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "missing_evidence": json.dumps(finding.missing_evidence, ensure_ascii=False),
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
                "runtime_evidence_ids": json.dumps(
                    [item.runtime_evidence_id for item in runtime_items],
                    ensure_ascii=False,
                ),
                "runtime_repositories": json.dumps(
                    [item.repository for item in runtime_items], ensure_ascii=False
                ),
                "runtime_pr_numbers": json.dumps(
                    [item.pr_number for item in runtime_items], ensure_ascii=False
                ),
                "runtime_head_shas": json.dumps(
                    [item.head_sha for item in runtime_items], ensure_ascii=False
                ),
                "manual_runtime_evidence_id": _csv_text(
                    resolution.runtime_evidence_id or _LEGACY_RUNTIME_LINK
                )
                if resolution is not None and resolution.decision is HumanDecision.MANUALLY_VERIFIED
                else "",
                "junit_artifact_digests": json.dumps(
                    [item.artifact_sha256 for item in junit_imports],
                    ensure_ascii=False,
                ),
                "junit_mapped_cases": json.dumps(
                    [
                        {
                            "import_id": _csv_text(evidence_import.import_id),
                            "artifact_sha256": evidence_import.artifact_sha256,
                            "imported_by": _csv_text(evidence_import.imported_by),
                            "test_case_id": _csv_text(case.test_case_id),
                            "status": case.status.value,
                            "suite_name": _csv_text(case.suite_name),
                            "test_name": _csv_text(case.test_name),
                        }
                        for evidence_import in junit_imports
                        for case in _junit_mapping_cases(
                            evidence_import, criterion.criterion_id
                        )
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "junit_evidence_boundary": _csv_text(
                    JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION
                )
                if junit_imports
                else "",
                "junit_importers": json.dumps(
                    [_csv_text(item.imported_by) for item in junit_imports],
                    ensure_ascii=False,
                ),
                "junit_parser_warnings": json.dumps(
                    [
                        {
                            "import_id": _csv_text(item.import_id),
                            "artifact_sha256": item.artifact_sha256,
                            "warning": _csv_text(warning),
                        }
                        for item in junit_imports
                        for warning in item.parser_warnings
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "junit_limitations": json.dumps(
                    [
                        {
                            "import_id": _csv_text(item.import_id),
                            "artifact_sha256": item.artifact_sha256,
                            "limitation": _csv_text(limitation),
                        }
                        for item in junit_imports
                        for limitation in item.limitations
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
    return output.getvalue()


def export_html(value: ExportableReview) -> str:
    """Render a self-contained local acceptance report without executable content."""
    bundle, state = _bundle_and_state(value)
    provenance = _criteria_source_provenance(bundle)
    finding_by_id = {finding.criterion_id: finding for finding in bundle.findings}
    evidence_by_id = {item.evidence_id: item for item in bundle.evidence}
    diagnostic_by_id = {
        diagnostic.criterion_id: diagnostic for diagnostic in bundle.retrieval_diagnostics
    }
    coverage_by_id = {row.criterion_id: row for row in criterion_coverage_rows(bundle)}
    rows = []
    diagnostic_sections = []
    for criterion in bundle.criteria:
        finding = finding_by_id[criterion.criterion_id]
        coverage = coverage_by_id[criterion.criterion_id]
        evidence = (
            "<br>".join(
                _render_candidate_reference_html(evidence_by_id[item_id])
                for item_id in finding.evidence_ids
            )
            or "No candidate evidence"
        )
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
        diagnostic_sections.append(
            _retrieval_diagnostic_html(
                criterion.criterion_id,
                diagnostic_by_id.get(criterion.criterion_id),
            )
        )
    revision = state.criteria_revision.number if state else 1
    review_status = html.escape(review_status_label(bundle.gate.verdict))
    review_created_at = bundle.review.model_dump(mode="json")["created_at"]
    guidance = gate_guidance(bundle.gate)
    linked_runtime_ids = {
        resolution.runtime_evidence_id
        for resolution in bundle.resolutions
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED
        and resolution.runtime_evidence_id is not None
    }
    manual_resolution_links = [
        "<li>"
        f"{html.escape(resolution.criterion_id)} — "
        "<strong>Manual resolution link:</strong> "
        + (
            f"<code>{html.escape(resolution.runtime_evidence_id)}</code>"
            if resolution.runtime_evidence_id is not None
            else html.escape(_LEGACY_RUNTIME_LINK)
        )
        + "</li>"
        for resolution in bundle.resolutions
        if resolution.decision is HumanDecision.MANUALLY_VERIFIED
    ]
    runtime_evidence_items = []
    for item in bundle.runtime_evidence:
        if item.runtime_evidence_id is None:
            identity = (
                f"<br><strong>Runtime identity:</strong> {html.escape(_LEGACY_RUNTIME_LINK)}"
                f"<br><strong>Manual resolution link:</strong> "
                f"{html.escape(_LEGACY_RUNTIME_LINK)}"
            )
        else:
            resolution_link = (
                f"<code>{html.escape(item.runtime_evidence_id)}</code>"
                if item.runtime_evidence_id in linked_runtime_ids
                else "Not linked to a current manual resolution"
            )
            identity = (
                "<br><strong>Runtime evidence ID:</strong> "
                f"<code>{html.escape(item.runtime_evidence_id)}</code>"
                "<br><strong>Repository / PR:</strong> "
                f"<code>{html.escape(item.repository or '')}</code> / #{item.pr_number}"
                "<br><strong>Bound head:</strong> "
                f"<code>{html.escape(item.head_sha or '')}</code>"
                f"<br><strong>Manual resolution link:</strong> {resolution_link}"
            )
        runtime_evidence_items.append(
            "<li>"
            f"{html.escape(item.criterion_id)}: "
            f"{_render_artifact_reference_html(item.artifact_reference)} — "
            f"{html.escape(item.scenario)}; {html.escape(item.environment)}; "
            f"{html.escape(item.result)}; {html.escape(item.reviewer)}; "
            f"{html.escape(item.evidence_level.value)}{identity}</li>"
        )
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
            "Repository visibility: "
            f"<code>{html.escape(bundle.review.repository_visibility.value)}</code> · "
            f"PR #{bundle.review.pr_number} · Base SHA "
            f"<code>{html.escape(bundle.review.base_sha)}</code> · Head SHA "
            f"<code>{html.escape(bundle.review.head_sha)}</code> · "
            f"Review created <code>{html.escape(review_created_at)}</code> · "
            f"Tool <code>{html.escape(bundle.review.tool_version)}</code> · "
            f"Ruleset <code>{html.escape(bundle.review.ruleset_version)}</code> · "
            f"Ingestion <code>{html.escape(bundle.review.ingestion_state.value)}</code> · "
            f"Criteria revision {revision}</p>",
            '<p class="note">ScopeProof surfaces auditable candidate evidence. '
            "It does not replace QA or prove correctness.</p>",
            "<h2>Criteria Source</h2>",
            '<table aria-label="Criteria Source"><tbody>',
            "<tr><td>Source reference</td><td><code>"
            f"{html.escape(provenance.source_uri)}</code></td></tr>",
            "<tr><td>Revision</td><td>"
            + (
                f"<code>{html.escape(provenance.source_revision)}</code>"
                if provenance.source_revision is not None
                else "Not supplied"
            )
            + "</td></tr>",
            "<tr><td>Source-text SHA-256</td><td><code>"
            f"{html.escape(provenance.source_text_sha256)}</code></td></tr>",
            "<tr><td>Normalized-criteria SHA-256</td><td><code>"
            f"{html.escape(provenance.normalized_criteria_sha256)}</code></td></tr>",
            "<tr><td>Confirmed by</td><td><code>"
            f"{html.escape(provenance.confirmed_by)}</code></td></tr>",
            "<tr><td>Confirmed at (UTC)</td><td><code>"
            f"{html.escape(_provenance_timestamp(provenance))}</code></td></tr>",
            "</tbody></table>",
            "<h2>Observed CI</h2>",
            "<p>Observed CI: <code>"
            f"{html.escape(bundle.review.ci_observation.state.value)}</code><br>"
            f"Reason: {html.escape(bundle.review.ci_observation.reason)}<br>"
            "Check runs: "
            f"{bundle.review.ci_observation.total_check_runs} total; "
            f"{bundle.review.ci_observation.successful_check_runs} successful; "
            f"{bundle.review.ci_observation.pending_check_runs} pending; "
            f"{bundle.review.ci_observation.failing_check_runs} failing; "
            f"{bundle.review.ci_observation.neutral_check_runs} neutral; "
            f"{bundle.review.ci_observation.skipped_check_runs} skipped; "
            f"{bundle.review.ci_observation.concrete_legacy_status_count} "
            "concrete legacy statuses.<br>"
            "Collection: "
            f"{'complete' if bundle.review.ci_observation.collection_complete else 'incomplete'}"
            + (
                "<br>Skipped CI checks: "
                + html.escape(", ".join(bundle.review.ci_observation.skipped_check_names))
                if bundle.review.ci_observation.skipped_check_names
                else ""
            )
            + "</p>",
            *(
                [
                    '<ul aria-label="CI collection diagnostics">',
                    *[
                        f"<li>{html.escape(note)}</li>"
                        for note in bundle.review.ci_observation.collection_notes
                    ],
                    "</ul>",
                ]
                if bundle.review.ci_observation.collection_notes
                else []
            ),
            *(
                [
                    "<h2>Research Boundary</h2>",
                    "<p>Public engineering research<br>"
                    f"Case ID: <code>{html.escape(bundle.research_context.case_id)}</code><br>"
                    "Stage 1 credit: 0 (permanently excluded)<br>"
                    f"{html.escape(bundle.research_context.boundary_note)}</p>",
                ]
                if bundle.research_context is not None
                else []
            ),
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
            "<h2>Retrieval Diagnostics</h2>",
            *diagnostic_sections,
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
                    "<h2>Manual Resolution Links</h2><ul>",
                    *manual_resolution_links,
                    "</ul>",
                ]
                if manual_resolution_links
                else []
            ),
            *(
                [
                    "<h2>Manual Runtime Evidence</h2><ul>",
                    *runtime_evidence_items,
                    "</ul>",
                ]
                if bundle.runtime_evidence
                else []
            ),
            *_junit_import_html(bundle),
            "<h2>Runtime Verification Boundary</h2>",
            "<p>"
            + (
                "Manual runtime evidence is recorded separately. Observed CI and static "
                "candidates do not establish runtime verification."
                if bundle.runtime_evidence
                else "No manual runtime verification was recorded. Observed CI and static "
                "candidates do not establish runtime verification."
            )
            + "</p>",
            "</body></html>",
        ]
    )
