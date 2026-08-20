import csv
import io
import json
from datetime import UTC, datetime

import pytest

from scopeproof_core.criteria.confirmation import (
    build_criteria_source_provenance,
    normalized_criteria_sha256,
)
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
    CIObservation,
    ConfidenceBand,
    Criterion,
    CriterionRetrievalDiagnostic,
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
    JUnitEvidenceBoundary,
    JUnitEvidenceImport,
    RepositoryVisibility,
    ResearchContext,
    ResolutionEvent,
    RetrievalOutcome,
    Review,
    ReviewBundle,
    ReviewInputOrigin,
    RuntimeEvidence,
)


def add_junit_import(bundle: ReviewBundle) -> ReviewBundle:
    bundle = bundle.model_copy(deep=True)
    bundle.review.head_sha = "a" * 40
    bundle.evidence[0].commit_sha = bundle.review.head_sha
    bundle.evidence[0].permalink = (
        "https://github.com/acme/widget/blob/"
        f"{bundle.review.head_sha}/src/export.py#L42-L42"
    )
    bundle.criteria_revision_number = 1
    provenance = bundle.review.criteria_source_provenance
    assert provenance is not None
    bundle.junit_evidence_imports = [
        JUnitEvidenceImport(
            schema_version="junit-import-v1",
            evidence_boundary=JUnitEvidenceBoundary(),
            import_id="junit-import-001",
            repository=bundle.review.repository,
            pr_number=bundle.review.pr_number,
            head_sha=bundle.review.head_sha,
            criteria_revision_number=1,
            confirmed_criteria_sha256=normalized_criteria_sha256(bundle.criteria),
            criteria_source_provenance=provenance,
            artifact_sha256="b" * 64,
            imported_by="=ASSERTED <owner>",
            imported_at=datetime(2026, 8, 20, tzinfo=UTC),
            totals={
                "total": 2,
                "passed": 1,
                "failures": 1,
                "errors": 0,
                "skipped": 0,
            },
            test_cases=[
                {
                    "test_case_id": "suite-0001-case-0001",
                    "suite_id": "suite-0001",
                    "suite_name": "<suite>",
                    "class_name": None,
                    "test_name": "=test_pass",
                    "status": "passed",
                },
                {
                    "test_case_id": "suite-0001-case-0002",
                    "suite_id": "suite-0001",
                    "suite_name": "<suite>",
                    "class_name": "tests.<Unsafe>",
                    "test_name": "test_fail **claim**",
                    "status": "failure",
                },
            ],
            criterion_mappings=[
                {
                    "criterion_id": "AC-01",
                    "test_case_ids": [
                        "suite-0001-case-0001",
                        "suite-0001-case-0002",
                    ],
                }
            ],
            parser_warnings=["@warning <unsafe>"],
            limitations=["+external result only <unsafe>"],
        )
    ]
    return ReviewBundle.model_validate(bundle.model_dump(mode="python"))


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
    bundle = ReviewBundle(
        review=review,
        source_text="Failed export shows an error",
        criteria=[criterion],
        evidence=[evidence],
        retrieval_diagnostics=[
            CriterionRetrievalDiagnostic(
                criterion_id="AC-01",
                outcome=RetrievalOutcome.CANDIDATES_FOUND,
                searched_terms=["error", "export", "fail"],
                exact_identifiers=[],
                searched_paths=["src/export.py"],
                searched_evidence_types=[EvidenceType.IMPLEMENTATION],
                changed_file_count=1,
                unchanged_candidate_file_count=0,
                inspectable_line_count=1,
                exact_identifier_match_line_count=0,
                term_overlap_line_count=1,
                below_threshold_line_count=0,
                accepted_candidate_count=1,
            )
        ],
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
    bundle.review.criteria_source_provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_revision="issue-6@revision-42<script>",
        source_text=bundle.source_text,
        criteria=bundle.criteria,
        confirmed_by="Product owner",
        confirmed_at=datetime(2026, 7, 11, 11, 55, tzinfo=UTC),
    )
    return ReviewBundle.model_validate(bundle.model_dump(mode="python"))


def rebind_criteria_source_provenance(bundle: ReviewBundle) -> None:
    provenance = bundle.review.criteria_source_provenance
    assert provenance is not None
    bundle.review.criteria_source_provenance = build_criteria_source_provenance(
        source_uri=provenance.source_uri,
        source_revision=provenance.source_revision,
        source_text=bundle.source_text,
        criteria=bundle.criteria,
        confirmed_by=provenance.confirmed_by,
        confirmed_at=provenance.confirmed_at,
    )


def test_junit_import_exports_are_complete_inert_and_non_gating() -> None:
    bundle = add_junit_import(example_bundle())
    second_import = bundle.junit_evidence_imports[0].model_copy(
        update={
            "import_id": "junit-import-002",
            "artifact_sha256": "c" * 64,
            "imported_by": "second owner",
            "parser_warnings": ["second warning"],
            "limitations": ["second limitation"],
        }
    )
    bundle.junit_evidence_imports.append(second_import)
    bundle = ReviewBundle.model_validate(bundle.model_dump(mode="python"))

    json_report = export_json(bundle)
    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)
    rendered = "\n".join((json_report, markdown, str(csv_row), html_report))

    assert "b" * 64 in rendered
    assert bundle.review.head_sha in rendered
    assert "suite-0001-case-0001" in rendered
    assert "passed" in rendered
    assert "=ASSERTED <owner>" in json_report
    json_payload = json.loads(json_report)
    assert json_payload["junit_evidence_imports"][0]["evidence_boundary"] == {
        "source": "externally_supplied",
        "gate_effect": "non_gating",
        "execution": "not_executed_by_scopeproof",
        "artifact_digest_scope": "imported_bytes_only",
        "importer_identity": "asserted_not_authenticated",
        "criterion_mapping": "organizational_context_not_proof",
    }
    assert "## Imported External Test Results" in markdown
    assert "Imported external test results" in html_report
    assert "RAW-JUNIT-OUTPUT-SENTINEL" not in rendered
    assert "FAILURE-BODY-SENTINEL" not in rendered
    assert "/private/local/results.xml" not in rendered
    assert "<suite>" not in markdown
    assert "<suite>" not in html_report
    assert "&lt;suite&gt;" in markdown
    assert "&lt;suite&gt;" in html_report
    assert csv_row["junit_artifact_digests"] == json.dumps(["b" * 64, "c" * 64])
    csv_cases = json.loads(csv_row["junit_mapped_cases"])
    assert {
        (item["import_id"], item["artifact_sha256"], item["imported_by"])
        for item in csv_cases
    } == {
        ("junit-import-001", "b" * 64, "'=ASSERTED <owner>"),
        ("junit-import-002", "c" * 64, "second owner"),
    }
    assert "externally supplied, non-gating context" in csv_row[
        "junit_evidence_boundary"
    ].lower()
    assert "did not execute" in csv_row["junit_evidence_boundary"].lower()
    assert "imported bytes only" in csv_row["junit_evidence_boundary"].lower()
    assert "asserted, not authenticated" in csv_row["junit_evidence_boundary"].lower()
    assert "organizational context, not proof" in csv_row["junit_evidence_boundary"].lower()
    assert csv_row["junit_importers"].startswith("[")
    assert "'=ASSERTED <owner>" in csv_row["junit_importers"]
    assert json.loads(csv_row["junit_parser_warnings"]) == [
        {
            "artifact_sha256": "b" * 64,
            "import_id": "junit-import-001",
            "warning": "'@warning <unsafe>",
        },
        {
            "artifact_sha256": "c" * 64,
            "import_id": "junit-import-002",
            "warning": "second warning",
        },
    ]
    assert json.loads(csv_row["junit_limitations"]) == [
        {
            "artifact_sha256": "b" * 64,
            "import_id": "junit-import-001",
            "limitation": "'+external result only <unsafe>",
        },
        {
            "artifact_sha256": "c" * 64,
            "import_id": "junit-import-002",
            "limitation": "second limitation",
        },
    ]
    assert bundle.gate.verdict.value in rendered


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


def test_exports_include_one_inert_criteria_source_snapshot() -> None:
    bundle = example_bundle()

    json_report = json.loads(export_json(bundle))
    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert json_report["review"]["criteria_source_provenance"] == {
        "confirmed_at": "2026-07-11T11:55:00Z",
        "confirmed_by": "Product owner",
        "normalized_criteria_sha256": (
            "ff334af327af005cd3fd82da8279ea6b5453358ff1dba3df0c4a7da968445fac"
        ),
        "source_revision": "issue-6@revision-42<script>",
        "source_text_sha256": ("b730e7b20d415f6d64948e1dd59807d4d20fd82615f2b9efc3a71798b926d57b"),
        "source_uri": "https://example.test/requirements",
    }
    assert markdown.count("## Criteria Source") == 1
    assert (
        "| Source reference | <code>https://example.test/requirements</code> |"
        in markdown
    )
    assert "[https://example.test/requirements" not in markdown
    assert "| Revision | <code>issue-6@revision-42&lt;script&gt;</code> |" in markdown
    assert "| Confirmed by | <code>Product owner</code> |" in markdown
    assert "| Confirmed at (UTC) | <code>2026-07-11T11:55:00Z</code> |" in markdown
    assert csv_row["criteria_source_uri"] == "https://example.test/requirements"
    assert csv_row["criteria_source_revision"] == "issue-6@revision-42<script>"
    assert csv_row["criteria_source_text_sha256"] == (
        "b730e7b20d415f6d64948e1dd59807d4d20fd82615f2b9efc3a71798b926d57b"
    )
    assert csv_row["criteria_normalized_criteria_sha256"] == (
        "ff334af327af005cd3fd82da8279ea6b5453358ff1dba3df0c4a7da968445fac"
    )
    assert csv_row["criteria_confirmed_by"] == "Product owner"
    assert csv_row["criteria_confirmed_at"] == "2026-07-11T11:55:00Z"
    assert html_report.count("<h2>Criteria Source</h2>") == 1
    assert '<a href="https://example.test/requirements' not in html_report
    assert "<code>https://example.test/requirements</code>" in html_report
    assert "issue-6@revision-42&lt;script&gt;" in html_report


@pytest.mark.parametrize("exporter", [export_json, export_markdown, export_csv, export_html])
def test_exports_reject_current_review_without_criteria_source_provenance(
    exporter,
) -> None:
    bundle = example_bundle()
    bundle.review.criteria_source_provenance = None

    with pytest.raises(ValueError, match=r"^criteria source provenance is required for export$"):
        exporter(bundle)


def test_exports_render_missing_optional_source_revision_as_not_supplied() -> None:
    bundle = example_bundle()
    assert bundle.review.criteria_source_provenance is not None
    bundle.review.criteria_source_provenance = bundle.review.criteria_source_provenance.model_copy(
        update={"source_revision": None}
    )

    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert "| Revision | Not supplied |" in markdown
    assert csv_row["criteria_source_revision"] == ""
    assert "<td>Revision</td><td>Not supplied</td>" in html_report


@pytest.mark.parametrize("exporter", [export_json, export_markdown, export_csv, export_html])
def test_exports_reject_source_text_changed_after_confirmation(exporter) -> None:
    bundle = example_bundle()
    bundle.source_text = "Changed after confirmation"

    with pytest.raises(
        ValueError, match="criteria source provenance does not match source text"
    ):
        exporter(bundle)


def test_criteria_source_metadata_is_inert_in_human_and_spreadsheet_exports() -> None:
    bundle = example_bundle()
    assert bundle.review.criteria_source_provenance is not None
    hostile_revision = "</td><script>alert(1)</script>"
    hostile_confirmer = '=HYPERLINK("https://example.invalid","owner")'
    bundle.review.criteria_source_provenance = (
        bundle.review.criteria_source_provenance.model_copy(
            update={
                "source_revision": hostile_revision,
                "confirmed_by": hostile_confirmer,
            }
        )
    )

    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert hostile_revision not in markdown
    assert hostile_revision not in html_report
    assert "&lt;/td&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in markdown
    assert "&lt;/td&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in html_report
    assert csv_row["criteria_confirmed_by"].startswith("'=")


def linked_runtime_bundle() -> ReviewBundle:
    bundle = example_bundle()
    runtime_item = bundle.runtime_evidence[0].model_copy(
        update={
            "runtime_evidence_id": "runtime-evidence-7",
            "repository": bundle.review.repository,
            "pr_number": bundle.review.pr_number,
            "head_sha": bundle.review.head_sha,
        }
    )
    bundle.runtime_evidence = [runtime_item]
    bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Observed the controlled export scenario",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=runtime_item.runtime_evidence_id,
            reviewer=runtime_item.reviewer,
            timestamp=datetime(2026, 7, 11, 12, 11, tzinfo=UTC),
        )
    ]
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )
    return ReviewBundle.model_validate(bundle.model_dump(mode="python"))


@pytest.mark.parametrize(
    "exporter",
    [export_json, export_markdown, export_csv, export_html],
)
def test_exporters_revalidate_active_review_state_identity(exporter) -> None:
    state = example_state()
    divergent = state.model_copy(
        update={"review": state.review.model_copy(update={"head_sha": "different-head"})}
    )

    with pytest.raises(ValueError, match="active bundle review must match lifecycle review"):
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


@pytest.mark.parametrize(
    "exporter",
    [export_json, export_markdown, export_csv, export_html],
)
def test_exporters_reject_forged_runtime_identity(exporter) -> None:
    bundle = linked_runtime_bundle()
    bundle.runtime_evidence[0].head_sha = "foreign-head"

    with pytest.raises(ValueError, match="runtime evidence identity must match the owning review"):
        exporter(bundle)


@pytest.mark.parametrize(
    "exporter",
    [export_json, export_markdown, export_csv, export_html],
)
def test_exporters_reject_forged_manual_runtime_link(exporter) -> None:
    bundle = linked_runtime_bundle()
    bundle.resolutions[0].runtime_evidence_id = "forged-runtime-link"

    with pytest.raises(ValueError, match="resolution runtime evidence ID must resolve"):
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


def test_human_readable_exports_show_bounded_context_without_changing_line_link() -> None:
    bundle = example_bundle()
    bundle.evidence[0].context_excerpt = (
        "def prepare_rows():\ndef export_csv(rows):\n    return filtered_rows"
    )

    markdown = export_markdown(bundle)
    html_report = export_html(bundle)

    assert "Context: <code>def prepare_rows(): def export_csv(rows):" in markdown
    assert "<pre>def prepare_rows():\ndef export_csv(rows):" in html_report
    assert "src/export.py#L42-L42" in markdown
    assert "src/export.py#L42-L42" in html_report


def test_exports_render_retrieval_diagnostics_as_non_evidence_metadata() -> None:
    bundle = example_bundle()

    json_report = json.loads(export_json(bundle))
    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert json_report["retrieval_diagnostics"][0]["outcome"] == "candidates_found"
    assert "**How ScopeProof searched:**" in markdown
    assert "Outcome: Candidates Found" in markdown
    assert "Searched paths: <code>src/export.py</code>" in markdown
    assert (
        "Search diagnostics explain retrieval; they are not evidence that the criterion "
        "is satisfied or missing from the repository."
    ) in markdown
    csv_diagnostic = json.loads(csv_row["retrieval_diagnostic"])
    assert csv_diagnostic["outcome"] == "candidates_found"
    assert csv_diagnostic["accepted_candidate_count"] == 1
    assert "<h3>AC-01 — How ScopeProof searched</h3>" in html_report
    assert "Candidates Found" in html_report
    assert (
        "Search diagnostics explain retrieval; they are not evidence that the criterion "
        "is satisfied or missing from the repository."
    ) in html_report


def test_historical_exports_do_not_invent_retrieval_diagnostics() -> None:
    payload = example_bundle().model_dump(mode="python")
    payload["retrieval_diagnostics"] = []
    bundle = ReviewBundle.model_validate(payload)

    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    fallback = "Retrieval diagnostics were not recorded for this review"
    assert fallback in markdown
    assert json.loads(csv_row["retrieval_diagnostic"]) is None
    assert fallback in html_report


def test_exports_make_observed_ci_research_and_verification_boundaries_inspectable() -> None:
    payload = example_bundle().model_dump(mode="python")
    payload["review"]["ci_observation"] = CIObservation(
        state=CheckState.UNAVAILABLE,
        reason="Only skipped checks were observed; execution is unavailable.",
        total_check_runs=2,
        skipped_check_runs=2,
        skipped_check_names=["eval", "integration"],
        collection_complete=True,
    ).model_dump(mode="python")
    payload["review"]["check_state"] = CheckState.UNAVAILABLE
    payload["evidence"][0]["evidence_type"] = EvidenceType.TEST
    payload["evidence"][0]["evidence_level"] = EvidenceLevel.E2
    payload["evidence"][0]["limitations"] = [
        "Test definition shows intent, not executed verification."
    ]
    payload["research_context"] = ResearchContext(
        case_id="R-001",
        boundary_note="Public engineering research does not advance Stage 1.",
    ).model_dump(mode="python")
    payload["runtime_evidence"] = []
    bundle = ReviewBundle.model_validate(payload)

    json_report = json.loads(export_json(bundle))
    markdown = export_markdown(bundle)
    semantic_markdown = markdown.replace("\\", "")
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert json_report["research_context"]["stage1_credit"] is False
    assert json_report["candidate_evidence_proves_correctness"] is False
    assert json_report["runtime_verification_state"] == "not_recorded"
    assert json_report["reviewer_decision_state"] == "recorded"
    assert "**Observed CI:** unavailable" in markdown
    assert "Observed 2 skipped check runs; it does not prove passing." in semantic_markdown
    assert "**Skipped CI checks:** eval, integration" in markdown
    assert "Test (E2; test/eval definition shows intent, not execution)" in markdown
    assert "No manual runtime verification was recorded" in markdown
    assert "**Reviewer decision:** Change required" in markdown
    assert "public engineering research" in markdown.lower()
    assert "does not advance Stage 1" in markdown
    assert csv_row["ci_state"] == "unavailable"
    assert csv_row["ci_skipped_check_names"] == '["eval", "integration"]'
    assert csv_row["research_case_id"] == "R-001"
    assert csv_row["stage1_credit"] == "False"
    assert csv_row["candidate_evidence_proves_correctness"] == "False"
    assert csv_row["runtime_verification_state"] == "not_recorded"
    assert csv_row["reviewer_decision_state"] == "recorded"
    assert "Observed CI: <code>unavailable</code>" in html_report
    assert "Test (E2; test/eval definition shows intent, not execution)" in html_report
    assert "No manual runtime verification was recorded" in html_report
    assert "Public engineering research" in html_report


def test_exports_surface_collection_diagnostics_as_inert_separate_data() -> None:
    hostile_notes = [
        "![remote](https://example.invalid/pixel.png)",
        '=HYPERLINK("https://example.invalid", "open")',
    ]
    payload = example_bundle().model_dump(mode="python")
    payload["review"]["check_state"] = CheckState.UNAVAILABLE
    payload["review"]["ci_observation"] = CIObservation(
        state=CheckState.UNAVAILABLE,
        reason="Caller-controlled reason must be replaced.",
        total_check_runs=1,
        successful_check_runs=1,
        collection_complete=False,
        collection_notes=hostile_notes,
    ).model_dump(mode="python")
    bundle = ReviewBundle.model_validate(payload)

    json_report = json.loads(export_json(bundle))
    markdown = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert json_report["review"]["ci_observation"]["collection_notes"] == hostile_notes
    assert "**CI collection diagnostics:**" in markdown
    assert "\\!\\[remote\\]" in markdown
    assert "![remote]" not in markdown
    assert '<ul aria-label="CI collection diagnostics">' in html_report
    assert "&quot;https://example.invalid&quot;" in html_report
    assert json.loads(csv_row["ci_collection_notes"]) == hostile_notes
    assert not csv_row["ci_collection_notes"].startswith(("=", "+", "-", "@"))


def test_export_json_and_csv_derive_recorded_runtime_state_from_manual_evidence() -> None:
    bundle = example_bundle()

    json_report = json.loads(export_json(bundle))
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))

    assert json_report["runtime_verification_state"] == "recorded"
    assert csv_row["runtime_verification_state"] == "recorded"


def test_json_and_human_exports_project_runtime_identity_and_link_state() -> None:
    bundle = linked_runtime_bundle()
    runtime_item = bundle.runtime_evidence[0]

    json_report = json.loads(export_json(bundle))
    markdown = export_markdown(bundle)
    html_report = export_html(bundle)

    assert json_report["runtime_evidence"][0] == runtime_item.model_dump(mode="json")
    assert json_report["resolutions"][0]["runtime_evidence_id"] == runtime_item.runtime_evidence_id
    assert "Runtime evidence ID: <code>runtime-evidence-7</code>" in markdown
    assert "Repository / PR: <code>acme/widget</code> / #7" in markdown
    assert "Bound head: <code>head123</code>" in markdown
    assert "Manual resolution link: <code>runtime-evidence-7</code>" in markdown
    assert "Runtime evidence ID:</strong> <code>runtime-evidence-7</code>" in html_report
    assert "Repository / PR:</strong> <code>acme/widget</code> / #7" in html_report
    assert "Bound head:</strong> <code>head123</code>" in html_report
    assert "Manual resolution link:</strong> <code>runtime-evidence-7</code>" in html_report


def test_human_and_csv_exports_label_legacy_unlinked_manual_resolution() -> None:
    bundle = example_bundle()
    bundle.resolutions = [
        HumanResolution(
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Legacy runtime observation",
            claimed_evidence_level=EvidenceLevel.E3,
            reviewer="QA reviewer",
        )
    ]
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
    )
    warning = "Legacy unlinked; re-record at the active head"

    assert warning in export_markdown(bundle)
    assert warning in export_html(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert csv_row["manual_runtime_evidence_id"] == warning


def test_csv_runtime_identity_arrays_preserve_positional_order_and_formula_safety() -> None:
    bundle = linked_runtime_bundle()
    first = bundle.runtime_evidence[0].model_copy(update={"runtime_evidence_id": "=runtime-one"})
    second = bundle.runtime_evidence[0].model_copy(
        update={
            "runtime_evidence_id": "+runtime-two",
            "artifact_reference": "artifact-two",
            "result": "second result",
        }
    )
    bundle.runtime_evidence = [first, second]
    bundle.resolutions[0].runtime_evidence_id = second.runtime_evidence_id
    bundle = ReviewBundle.model_validate(bundle.model_dump(mode="python"))

    row = next(csv.DictReader(io.StringIO(export_csv(bundle))))

    assert json.loads(row["runtime_evidence_ids"]) == ["=runtime-one", "+runtime-two"]
    assert json.loads(row["runtime_repositories"]) == ["acme/widget", "acme/widget"]
    assert json.loads(row["runtime_pr_numbers"]) == [7, 7]
    assert json.loads(row["runtime_head_shas"]) == ["head123", "head123"]
    assert row["manual_runtime_evidence_id"] == "'+runtime-two"


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


def test_json_export_preserves_verified_public_repository_provenance() -> None:
    bundle = example_bundle()
    bundle.review = Review.model_validate(
        {
            **bundle.review.model_dump(mode="python"),
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            "input_origin": ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
        }
    )

    payload = json.loads(export_json(bundle))

    assert payload["review"]["repository_visibility"] == "verified_public"


def test_human_readable_exports_preserve_verified_public_repository_provenance() -> None:
    bundle = example_bundle()
    bundle.review = Review.model_validate(
        {
            **bundle.review.model_dump(mode="python"),
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            "input_origin": ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
        }
    )

    markdown_report = export_markdown(bundle)
    csv_row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    html_report = export_html(bundle)

    assert "**Repository visibility:** <code>verified_public</code>" in markdown_report
    assert csv_row["repository_visibility"] == "verified_public"
    assert "Repository visibility: <code>verified_public</code>" in html_report


def test_exports_preserve_ingestion_limitations_and_escape_html() -> None:
    bundle = example_bundle()
    bundle.review.ingestion_state = IngestionState.PARTIAL
    bundle.review.ingestion_warnings = [
        "![remote image](https://example.invalid/pixel.png)",
        '=HYPERLINK("https://example.invalid","warning")',
    ]
    bundle.review.skipped_files = [
        "src/one.py",
        "src/<unsafe>|two.py",
        '=HYPERLINK("https://example.invalid","path")',
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
    rebind_criteria_source_provenance(bundle)

    report = export_markdown(bundle)

    assert report.count(active_markdown) == 1
    assert f"<code>{active_markdown}</code>" in report
    assert r"\!\[remote\]\(" in report


def test_markdown_escapes_untrusted_skipped_ci_check_names() -> None:
    payload = example_bundle().model_dump(mode="python")
    payload["review"]["check_state"] = CheckState.UNAVAILABLE
    payload["review"]["ci_observation"] = CIObservation(
        reason="No executable check result was observed.",
        total_check_runs=1,
        skipped_check_runs=1,
        skipped_check_names=["![remote](https://example.invalid/pixel.png)"],
    ).model_dump(mode="python")
    bundle = ReviewBundle.model_validate(payload)

    report = export_markdown(bundle)

    assert "![remote](https://example.invalid/pixel.png)" not in report
    assert r"\!\[remote\]\(" in report


def test_markdown_neutralizes_links_html_formatting_and_autolinks() -> None:
    bundle = example_bundle()
    bundle.source_text = (
        "[link](https://example.invalid/link) <img src=x> **bold** _emphasis_ "
        "`code` ~~strike~~ https://example.invalid/plain"
    )
    rebind_criteria_source_provenance(bundle)

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
    rebind_criteria_source_provenance(bundle)

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
    rebind_criteria_source_provenance(bundle)
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
    unsafe = 'javascript:alert(1)"><img src=x>'
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
    assert "| Change required | medium | 1 | Only the export path was found. |" in markdown.replace(
        "\\", ""
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
    rebind_criteria_source_provenance(bundle)

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
