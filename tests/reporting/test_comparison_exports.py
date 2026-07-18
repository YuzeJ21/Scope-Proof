import json

import pytest
from pydantic import ValidationError

from scopeproof_core.reporting.exporters import (
    export_comparison_json,
    export_comparison_markdown,
)
from scopeproof_core.reviews.comparison import (
    EvidenceChange,
    EvidenceChangeKind,
    EvidenceReference,
    ReviewComparison,
)
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    GateVerdict,
)


def reference(
    evidence_id: str,
    *,
    sha: str,
    path: str = "src/export.py",
    line: int = 4,
    excerpt: str = "export_csv()",
) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        criterion_id="AC-01",
        commit_sha=sha,
        file_path=path,
        line_start=line,
        line_end=line,
        excerpt=excerpt,
        permalink=f"https://github.com/acme/widget/blob/{sha}/{path}#L{line}-L{line}",
        evidence_type=EvidenceType.IMPLEMENTATION,
        evidence_level=EvidenceLevel.E1,
        source_scope=EvidenceSourceScope.CHANGED_FILE,
        matching_rule="keyword_overlap",
        relevance_reason="Matched export",
    )


def example_comparison() -> ReviewComparison:
    old = reference("EV-old", sha="old")
    new = reference("EV-new", sha="new", line=8, excerpt="safe_export_csv()")
    return ReviewComparison(
        previous_head_sha="old",
        current_head_sha="new",
        evidence_changes=[
            EvidenceChange(
                criterion_id="AC-01",
                kind=EvidenceChangeKind.MODIFIED,
                previous=old,
                current=new,
                reason="Candidate excerpt changed; review the current evidence.",
            ),
            EvidenceChange(
                criterion_id="AC-01",
                kind=EvidenceChangeKind.ADDED,
                current=reference("EV-added", sha="new", path="src/added.py"),
                reason="Candidate appears only in the current review.",
            ),
            EvidenceChange(
                criterion_id="AC-01",
                kind=EvidenceChangeKind.REMOVED,
                previous=reference("EV-removed", sha="old", path="src/removed.py"),
                reason="Candidate appears only in the previous review.",
            ),
        ],
        changed_finding_statuses=[],
        changed_human_resolutions=[],
        previous_gate=GateVerdict.BLOCKED,
        current_gate=GateVerdict.NEEDS_REVIEW,
        ruleset_version_changed=False,
    )


def test_comparison_json_is_validated_deterministic_and_counted() -> None:
    comparison = example_comparison()

    first = export_comparison_json(comparison)
    second = export_comparison_json(comparison)
    payload = json.loads(first)

    assert first == second
    assert first.endswith("\n")
    assert payload["previous_head_sha"] == "old"
    assert payload["current_head_sha"] == "new"
    assert payload["evidence_change_counts"]["modified"] == 1
    assert payload["evidence_change_counts"]["added"] == 1
    assert payload["evidence_change_counts"]["removed"] == 1
    assert payload["evidence_changes"][0]["previous"]["commit_sha"] == "old"
    assert payload["evidence_changes"][0]["current"]["commit_sha"] == "new"


def test_comparison_markdown_shows_two_sides_and_evidence_boundary() -> None:
    report = export_comparison_markdown(example_comparison())

    assert "# ScopeProof Re-review Comparison" in report
    assert "Previous head" in report and "old" in report
    assert "Current head" in report and "new" in report
    assert "Modified: 1" in report
    assert "Previous candidate" in report
    assert "Current candidate" in report
    assert "EV-old" in report and "EV-new" in report
    assert "does not prove criterion satisfaction" in report
    assert "review the current evidence" in report.lower()


def test_comparison_markdown_escapes_repository_controlled_text() -> None:
    comparison = example_comparison()
    unsafe = reference(
        "EV-unsafe",
        sha="new",
        path="src/<script>.py",
        excerpt="**claim** <img src=x>",
    )
    comparison.evidence_changes.append(
        EvidenceChange(
            criterion_id="AC-01",
            kind=EvidenceChangeKind.ADDED,
            current=unsafe,
            reason="Candidate <b>appears</b> only in the current review.",
        )
    )

    report = export_comparison_markdown(comparison)

    assert "<script>" not in report
    assert "<img src=x>" not in report
    assert "<b>appears</b>" not in report
    assert "&lt;script&gt;" in report
    assert "&lt;img src=x&gt;" in report


@pytest.mark.parametrize(
    "exporter", [export_comparison_json, export_comparison_markdown]
)
def test_comparison_exporters_revalidate_mutated_input(exporter) -> None:
    comparison = example_comparison()
    change = comparison.evidence_changes[1]
    invalid = change.model_copy(update={"previous": change.current})
    comparison.evidence_changes[1] = invalid

    with pytest.raises(ValidationError, match="added evidence changes"):
        exporter(comparison)
