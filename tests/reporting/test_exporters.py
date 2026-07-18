import csv
import io
import json
from datetime import UTC, datetime

import pytest

from scopeproof_core.gates import validation as gate_validation
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
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
    IngestionState,
    ResolutionEvent,
    Review,
    ReviewBundle,
    RuntimeEvidence,
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
        runtime_evidence=[
            RuntimeEvidence(
                criterion_id="AC-01",
                artifact_reference="https://example.test/runs/7",
                scenario="Failed export shows its error state",
                environment="staging",
                result="passed",
                reviewer="QA reviewer",
                evidence_level=EvidenceLevel.E3,
                timestamp=datetime(2026, 7, 11, 12, 10, tzinfo=UTC),
                limitations=["Manually supplied"],
            )
        ],
        findings=[finding],
        resolutions=[resolution],
        gate=gate,
    )


def example_state():
    bundle = example_bundle()
    resolution = bundle.resolutions[0]
    bundle.resolutions = []
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )
    state = new_review_state(bundle)
    return append_resolution(
        state,
        ResolutionEvent(
            event_id="review-event-1",
            criterion_id=resolution.criterion_id,
            decision=resolution.decision,
            comment=resolution.comment,
            evidence_url=resolution.evidence_url,
            claimed_evidence_level=resolution.claimed_evidence_level,
            reviewer=resolution.reviewer,
            timestamp=resolution.timestamp,
        ),
    )


@pytest.mark.parametrize(
    "exporter",
    [export_json, export_markdown, export_csv, export_html],
)
def test_exporters_revalidate_active_review_state_identity(exporter) -> None:
    state = example_state()
    divergent = state.model_copy(
        update={
            "review": state.review.model_copy(update={"head_sha": "different-head"})
        }
    )

    with pytest.raises(
        ValueError, match="active bundle review must match lifecycle review"
    ):
        exporter(divergent)


@pytest.mark.parametrize(
    "exporter",
    [export_json, export_markdown, export_csv, export_html],
)
def test_exporters_revalidate_direct_review_bundle(exporter) -> None:
    bundle = example_bundle()
    bundle.review = bundle.review.model_copy(update={"base_sha": " "})

    with pytest.raises(ValueError, match="review identity must contain non-whitespace text"):
        exporter(bundle)


def test_exports_agree_on_review_identity_verdict_and_criteria() -> None:
    bundle = example_bundle()
    created_at = bundle.review.model_dump(mode="json")["created_at"]
    json_report = export_json(bundle)
    markdown_report = export_markdown(bundle)
    csv_report = export_csv(bundle)
    html_report = export_html(bundle)
    outputs = [json_report, markdown_report, csv_report, html_report]
    for output in outputs:
        semantic_output = output.replace("\\", "")
        assert bundle.review.review_id in semantic_output
        assert bundle.review.base_sha in semantic_output
        assert created_at in semantic_output
        assert "head123" in semantic_output
        assert "AC-01" in semantic_output
    assert "blocked" in json_report.lower()
    assert "blocked" in csv_report.lower()
    assert "Action required" in markdown_report
    assert "Action required" in html_report


def test_human_readable_exports_use_reviewer_owned_coverage_language() -> None:
    bundle = example_bundle()

    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert "**Review status:** Action required" in markdown
    assert "| Evidence status | Evidence types | Reviewer decision |" in markdown
    assert "Weak candidate" in markdown
    assert csv_row["review_status"] == "Action required"
    assert csv_row["evidence_status"] == "Weak candidate"
    assert json.loads(csv_row["evidence_types"]) == ["Implementation"]
    assert "<strong>Review status:</strong> Action required" in html_report
    assert "<th>Evidence status</th><th>Evidence types</th>" in html_report
    assert "<td>Weak candidate</td><td>Implementation</td>" in html_report


def test_exports_preserve_tool_and_ruleset_provenance() -> None:
    bundle = example_bundle()

    for output in (
        export_json(bundle),
        export_markdown(bundle),
        export_csv(bundle),
        export_html(bundle),
    ):
        assert bundle.review.tool_version in output
        assert bundle.review.ruleset_version in output


def test_exports_preserve_ingestion_limitations_and_escape_html() -> None:
    bundle = example_bundle()
    bundle.review.ingestion_state = IngestionState.PARTIAL
    bundle.review.ingestion_warnings = [
        "![remote image](https://example.invalid/pixel.png)",
        "=HYPERLINK(\"https://example.invalid\",\"warning\")",
    ]
    bundle.review.skipped_files = [
        "src/one.py",
        "src/<unsafe>|two.py",
        "=HYPERLINK(\"https://example.invalid\",\"path\")",
        "src/literal | delimiter.py",
    ]

    json_report = export_json(bundle)
    markdown_report = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert json.loads(json_report)["review"]["skipped_files"] == bundle.review.skipped_files
    assert "## Ingestion Limitations" in markdown_report
    assert "- ![remote image]" not in markdown_report
    assert "- <code>![remote image]" in markdown_report
    assert "src/&lt;unsafe&gt;|two.py" in markdown_report
    assert csv_row["ingestion_state"] == "partial"
    assert json.loads(csv_row["ingestion_warnings"]) == bundle.review.ingestion_warnings
    assert json.loads(csv_row["skipped_files"]) == bundle.review.skipped_files
    assert not csv_row["ingestion_warnings"].startswith(("=", "+", "-", "@"))
    assert not csv_row["skipped_files"].startswith(("=", "+", "-", "@"))
    assert "src/&lt;unsafe&gt;|two.py" in html_report
    assert "src/<unsafe>" not in html_report


def test_markdown_keeps_all_untrusted_review_text_inert() -> None:
    bundle = example_bundle()
    active_markdown = "![remote](https://example.invalid/pixel.png)"
    bundle.source_text = active_markdown
    bundle.criteria[0].text = active_markdown
    bundle.findings[0].reason = active_markdown
    bundle.findings[0].missing_evidence = [active_markdown]
    bundle.findings[0].recommended_action = active_markdown
    bundle.evidence[0].file_path = f"src/{active_markdown}.py"
    bundle.evidence[0].excerpt = active_markdown
    bundle.evidence[0].relevance_reason = active_markdown
    bundle.evidence[0].limitations = [active_markdown]
    bundle.resolutions[0].comment = active_markdown
    bundle.runtime_evidence[0].scenario = active_markdown
    bundle.runtime_evidence[0].environment = active_markdown
    bundle.runtime_evidence[0].result = active_markdown
    bundle.runtime_evidence[0].reviewer = active_markdown
    bundle.runtime_evidence[0].limitations = [active_markdown]

    report = export_markdown(bundle)

    assert report.count(active_markdown) == 1
    assert f"<code>{active_markdown}</code>" in report
    assert r"\!\[remote\]\(" in report


def test_markdown_neutralizes_links_html_formatting_and_autolinks() -> None:
    bundle = example_bundle()
    bundle.source_text = (
        "[link](https://example.invalid/link) <img src=x> **bold** _emphasis_ "
        "`code` ~~strike~~ https://example.invalid/plain"
    )

    report = export_markdown(bundle)

    for active_syntax in (
        "[link](https://example.invalid/link)",
        "<img src=x>",
        "**bold**",
        "_emphasis_",
        "`code`",
        "~~strike~~",
        "https://example.invalid/plain",
    ):
        assert active_syntax not in report


def test_csv_neutralizes_formula_cells_and_serializes_lists_reversibly() -> None:
    bundle = example_bundle()
    bundle.review.review_id = '=HYPERLINK("https://example.invalid","review")'
    bundle.review.base_sha = "+SUM(1,1)"
    bundle.source_text = '-HYPERLINK("https://example.invalid","source")'
    bundle.criteria[0].text = '@HYPERLINK("https://example.invalid","criterion")'
    bundle.findings[0].reason = "\t=1+1"
    bundle.findings[0].missing_evidence = ["=1+1", "literal | delimiter"]
    bundle.findings[0].recommended_action = "\r=1+1"
    bundle.resolutions[0].comment = "+1+1"
    bundle.runtime_evidence[0].artifact_reference = "=1+1"
    bundle.runtime_evidence[0].result = "@1+1"

    row = next(csv.DictReader(io.StringIO(export_csv(bundle), newline="")))

    for field in (
        "review_id",
        "base_sha",
        "requirements_source_text",
        "criterion",
        "concern",
        "reviewer_comment",
        "recommended_action",
    ):
        assert row[field].startswith("'")
        assert not row[field].startswith(("=", "+", "-", "@", "\t", "\r"))
    assert json.loads(row["missing_evidence"]) == bundle.findings[0].missing_evidence
    assert json.loads(row["runtime_artifacts"]) == ["=1+1"]
    assert json.loads(row["runtime_result"]) == ["@1+1"]


def test_exports_preserve_confirmed_requirement_source() -> None:
    bundle = example_bundle()
    bundle.source_text = "Confirmed requirement source:\nFailed export shows an error"
    json_report = export_json(bundle)
    markdown_report = export_markdown(bundle)
    csv_report = export_csv(bundle)
    html_report = export_html(bundle)

    assert json.loads(json_report)["source_text"] == bundle.source_text
    assert "> Confirmed requirement source\\:" in markdown_report
    assert "> Failed export shows an error" in markdown_report
    csv_row = next(csv.DictReader(io.StringIO(csv_report)))
    assert csv_row["requirements_source_text"] == bundle.source_text
    assert bundle.source_text in html_report
    assert bundle.criteria[0].criterion_source.value in json_report
    assert bundle.criteria[0].criterion_source.value in csv_report
    assert "User confirmed" in markdown_report
    assert "User confirmed" in html_report


def test_human_readable_exports_keep_historical_tool_version() -> None:
    bundle = example_bundle()
    bundle.review.tool_version = "0.1.0"

    for output in (export_markdown(bundle), export_csv(bundle), export_html(bundle)):
        assert "0.1.0" in output


def test_repeated_exports_preserve_deterministic_review_identity() -> None:
    bundle = example_bundle()

    for exporter in (export_json, export_markdown, export_csv, export_html):
        assert exporter(bundle) == exporter(bundle)


def test_runtime_artifact_identifiers_and_non_web_schemes_are_plain_text() -> None:
    for reference in (
        "artifact-42",
        "relative/run-42",
        "file:///tmp/run-42",
        "javascript:alert(1)",
    ):
        bundle = example_bundle()
        bundle.runtime_evidence[0].artifact_reference = reference

        markdown_report = export_markdown(bundle)
        html_report = export_html(bundle)

        assert reference in markdown_report.replace("\\", "")
        assert f"[{reference}](" not in markdown_report
        assert reference in html_report
        assert f'href="{reference}"' not in html_report


def test_runtime_http_artifact_reference_remains_clickable() -> None:
    bundle = example_bundle()
    reference = "https://example.test/runs/7?case=(export)"
    bundle.runtime_evidence[0].artifact_reference = reference

    assert f"](<{reference}>)" in export_markdown(bundle)
    assert f'<a href="{reference}">{reference}</a>' in export_html(bundle)


def test_bypassed_unsafe_candidate_permalink_is_rendered_as_inert_text() -> None:
    bundle = example_bundle()
    unsafe = 'javascript:alert(1)\"><img src=x>'
    bundle.evidence[0].permalink = unsafe

    markdown = export_markdown(bundle)
    html_report = export_html(bundle)

    assert f"]({unsafe})" not in markdown
    assert "javascript\\:alert\\(1\\)" in markdown
    assert f'href="{unsafe}"' not in html_report
    assert "javascript:alert(1)&quot;&gt;&lt;img src=x&gt;" in html_report


def test_runtime_artifact_reference_stays_exact_in_json_and_csv() -> None:
    bundle = example_bundle()
    reference = "artifact-42"
    bundle.runtime_evidence[0].artifact_reference = reference

    assert json.loads(export_json(bundle))["runtime_evidence"][0]["artifact_reference"] == reference
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert json.loads(csv_row["runtime_artifacts"]) == [reference]


def test_markdown_groups_version_provenance_before_criteria_revision() -> None:
    markdown = export_markdown(example_state())

    assert markdown.index("**Tool version:**") < markdown.index("**Ruleset:**")
    assert markdown.index("**Ruleset:**") < markdown.index("**Criteria revision:")


def test_json_is_stable_and_contains_ruleset_version() -> None:
    payload = json.loads(export_json(example_bundle()))
    assert payload["review"]["ruleset_version"] == "1.0.0"
    assert payload["gate"]["verdict"] == "blocked"
    assert export_json(example_bundle()) == export_json(example_bundle())


def test_csv_emits_one_flattened_row_per_criterion() -> None:
    bundle = example_bundle()
    rows = list(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert len(rows) == 1
    assert rows[0]["review_id"] == bundle.review.review_id
    assert rows[0]["base_sha"] == bundle.review.base_sha
    assert rows[0]["head_sha"] == bundle.review.head_sha
    assert rows[0]["review_created_at"] == bundle.review.model_dump(mode="json")["created_at"]
    assert rows[0]["requirements_source_text"] == bundle.source_text
    assert rows[0]["criterion_source"] == bundle.criteria[0].criterion_source.value
    assert rows[0]["tool_version"] == bundle.review.tool_version
    assert rows[0]["ruleset_version"] == bundle.review.ruleset_version
    assert rows[0]["criterion_id"] == "AC-01"
    assert rows[0]["status"] == "partial"
    assert rows[0]["evidence_count"] == "1"
    assert rows[0]["concern"] == bundle.findings[0].reason
    assert "Failure-path test" in rows[0]["missing_evidence"]
    assert "src/export.py#L42-L42" in rows[0]["evidence_links"]


def test_markdown_contains_disclaimer_and_human_resolution() -> None:
    markdown = export_markdown(example_bundle())
    assert "does not replace QA" in markdown
    assert "Must fix before merge" in markdown
    assert "Candidate evidence" in markdown
    assert "Manual Runtime Evidence" in markdown
    assert "https://example.test/runs/7" in markdown


def test_human_readable_exports_complete_the_evidence_matrix_contract() -> None:
    bundle = example_bundle()
    markdown = export_markdown(bundle)
    html_report = export_html(bundle)

    assert "| Reviewer decision | Confidence | Count | Concern |" in markdown
    assert (
        "| Change required | medium | 1 | Only the export path was found. |"
        in markdown.replace("\\", "")
    )
    assert "<th>Reviewer decision</th><th>Confidence</th><th>Count</th>" in html_report
    assert "<th>Concern</th>" in html_report
    assert "<td>medium</td><td>1</td>" in html_report
    assert "<td>Only the export path was found.</td>" in html_report
    assert "<td>Change required</td>" in html_report


def test_candidate_evidence_count_excludes_manual_runtime_evidence() -> None:
    bundle = example_bundle()
    assert len(bundle.evidence) == 1
    assert len(bundle.runtime_evidence) == 1

    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert csv_row["evidence_count"] == "1"


def test_human_readable_exports_label_unresolved_human_decision() -> None:
    bundle = example_bundle().model_copy(update={"resolutions": []})

    assert "Unresolved" in export_markdown(bundle)
    assert "Unresolved" in export_html(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert csv_row["human_decision"] == ""


def test_markdown_keeps_gate_reasons_and_adds_recovery_guidance() -> None:
    markdown = export_markdown(example_bundle())

    assert "## Review Status Reasons" in markdown
    assert "<code>blocking_criteria</code>" in markdown
    assert "## What To Do Next" in markdown
    assert "blocking criteria: AC-01" in markdown.replace("\\", "")


def test_html_keeps_gate_reasons_and_adds_escaped_recovery_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = example_bundle()
    bundle.gate.reason_codes.append("future_<reason>")
    monkeypatch.setattr(
        gate_validation,
        "evaluate_gate",
        lambda *_args: bundle.gate,
    )

    report = export_html(bundle)

    assert "Review Status Reasons" in report
    assert "blocking_criteria" in report
    assert "future_&lt;reason&gt;" in report
    assert "What To Do Next" in report
    assert "blocking criteria: AC-01" in report
    assert "Review gate reason `future_&lt;reason&gt;` before acceptance." in report


def test_html_escapes_review_identity_values() -> None:
    bundle = example_bundle()
    bundle.review.review_id = "review-<identity>"
    bundle.review.base_sha = "base<&>"

    report = export_html(bundle)

    assert "review-&lt;identity&gt;" in report
    assert "base&lt;&amp;&gt;" in report
    assert "review-<identity>" not in report
    assert "base<&>" not in report


def test_html_escapes_confirmed_requirement_source_text() -> None:
    bundle = example_bundle()
    bundle.source_text = "User requires <safe & auditable> output"

    report = export_html(bundle)

    assert "User requires &lt;safe &amp; auditable&gt; output" in report
    assert bundle.source_text not in report


def test_html_escapes_evidence_matrix_concern() -> None:
    bundle = example_bundle()
    bundle.findings[0].reason = "Concern <script>alert('unsafe')</script>"

    report = export_html(bundle)

    assert "Concern &lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;" in report
    assert "<script>alert('unsafe')</script>" not in report


def test_exports_never_include_token_shaped_secret() -> None:
    for output in (
        export_json(example_bundle()),
        export_markdown(example_bundle()),
        export_csv(example_bundle()),
    ):
        assert "ghp_" not in output
    assert "authorization" not in output.lower()


def test_csv_exposes_runtime_evidence_separately_from_static_candidates() -> None:
    row = next(csv.DictReader(io.StringIO(export_csv(example_bundle()))))

    assert json.loads(row["runtime_artifacts"]) == ["https://example.test/runs/7"]
    assert json.loads(row["runtime_result"]) == ["passed"]
