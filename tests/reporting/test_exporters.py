import csv
import io
import json
from datetime import UTC, datetime

from scopeproof_core.reporting.exporters import export_csv, export_json, export_markdown
from scopeproof_core.schemas.models import (
    CheckState,
    ConfidenceBand,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    Finding,
    FindingStatus,
    GateDecision,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    Review,
    ReviewBundle,
)


def example_bundle() -> ReviewBundle:
    review = Review(
        review_id="review-1",
        repository="acme/widget",
        pr_number=7,
        base_sha="base123",
        head_sha="head123",
        check_state=CheckState.PASSING,
        criteria_confirmed=True,
        created_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
    )
    criterion = Criterion(criterion_id="AC-01", text="Failed export shows an error")
    evidence = EvidenceItem(
        evidence_id="EV-AC-01-01",
        criterion_id="AC-01",
        evidence_type=EvidenceType.IMPLEMENTATION,
        evidence_level=EvidenceLevel.E1,
        file_path="src/export.py",
        line_start=42,
        line_end=42,
        commit_sha="head123",
        permalink="https://github.com/acme/widget/blob/head123/src/export.py#L42-L42",
        excerpt="def export_csv(rows):",
        matching_rule="keyword_overlap",
        relevance_reason="Matched export",
        relevance_score=0.5,
        limitations=["No error branch found"],
    )
    finding = Finding(
        criterion_id="AC-01",
        status=FindingStatus.PARTIAL,
        evidence_level=EvidenceLevel.E1,
        confidence_band=ConfidenceBand.MEDIUM,
        reason="Only the export path was found.",
        evidence_ids=[evidence.evidence_id],
        missing_evidence=["Failure-path test", "User-visible error state"],
        recommended_action="Add error handling and a failure-path test.",
    )
    resolution = HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.CHANGE_REQUIRED,
        comment="Must fix before merge",
        timestamp=datetime(2026, 7, 11, 12, 5, tzinfo=UTC),
    )
    gate = GateDecision(
        verdict=GateVerdict.BLOCKED,
        blocking_criteria=["AC-01"],
        reason_codes=["blocking_criteria"],
    )
    return ReviewBundle(
        review=review,
        source_text="Failed export shows an error",
        criteria=[criterion],
        evidence=[evidence],
        findings=[finding],
        resolutions=[resolution],
        gate=gate,
    )


def test_exports_agree_on_verdict_head_sha_and_criteria() -> None:
    bundle = example_bundle()
    outputs = [export_json(bundle), export_markdown(bundle), export_csv(bundle)]
    for output in outputs:
        assert "blocked" in output.lower()
        assert "head123" in output
        assert "AC-01" in output


def test_json_is_stable_and_contains_ruleset_version() -> None:
    payload = json.loads(export_json(example_bundle()))
    assert payload["review"]["ruleset_version"] == "1.0.0"
    assert payload["gate"]["verdict"] == "blocked"
    assert export_json(example_bundle()) == export_json(example_bundle())


def test_csv_emits_one_flattened_row_per_criterion() -> None:
    rows = list(csv.DictReader(io.StringIO(export_csv(example_bundle()))))
    assert len(rows) == 1
    assert rows[0]["criterion_id"] == "AC-01"
    assert rows[0]["status"] == "partial"
    assert "Failure-path test" in rows[0]["missing_evidence"]
    assert "src/export.py#L42-L42" in rows[0]["evidence_links"]


def test_markdown_contains_disclaimer_and_human_resolution() -> None:
    markdown = export_markdown(example_bundle())
    assert "does not replace QA" in markdown
    assert "Must fix before merge" in markdown
    assert "Candidate evidence" in markdown


def test_exports_never_include_token_shaped_secret() -> None:
    for output in (
        export_json(example_bundle()),
        export_markdown(example_bundle()),
        export_csv(example_bundle()),
    ):
        assert "ghp_" not in output
        assert "authorization" not in output.lower()
