"""Pure constructed JUnit audit data; no filesystem, network or application IO."""

from datetime import UTC, datetime

from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.importers.junit import JUnitMappingSelection, build_junit_evidence_import
from scopeproof_core.reviews.lifecycle import append_junit_evidence_import, new_review_state
from scopeproof_core.schemas.models import (
    CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
    ChangedFileInventory,
    CheckState,
    CIObservation,
    Criterion,
    IngestionState,
    Review,
    ReviewBundle,
    ReviewInputOrigin,
    ReviewState,
)
from scopeproof_core.verification.service import build_findings

JUNIT_AUDIT_XML = (
    b'<testsuite name="CONSTRUCTED audit suite">'
    b'<testcase name="CONSTRUCTED pass"/>'
    b'<testcase name="CONSTRUCTED failure"><failure/></testcase>'
    b'</testsuite>'
)


def junit_audit_state() -> ReviewState:
    """Return one confirmed constructed analysis with a real two-criterion import."""
    timestamp = datetime(2026, 11, 1, 12, tzinfo=UTC)
    criteria = [
        Criterion(criterion_id="AC-01", text="CONSTRUCTED export behavior"),
        Criterion(criterion_id="AC-02", text="CONSTRUCTED failure behavior"),
    ]
    source = "CONSTRUCTED export behavior; CONSTRUCTED failure behavior"
    provenance = build_criteria_source_provenance(
        source_uri=CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
        source_revision="constructed-junit-audit-v1",
        source_text=source,
        criteria=criteria,
        confirmed_by="CONSTRUCTED criteria actor",
        confirmed_at=timestamp,
    )
    review = Review(
        review_id="constructed-junit-audit-review",
        repository="constructed/audit-example",
        pr_number=17,
        base_sha="b" * 40,
        head_sha="a" * 40,
        input_origin=ReviewInputOrigin.CONSTRUCTED_DEMO,
        created_at=timestamp,
        criteria_confirmed=True,
        criteria_source_provenance=provenance,
        changed_file_inventory=ChangedFileInventory(head_sha="a" * 40, files=[]),
        check_state=CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.PASSING,
            reason="CONSTRUCTED passing CI metadata; no real execution is asserted",
            total_check_runs=1,
            successful_check_runs=1,
        ),
    )
    findings = build_findings(criteria, [], IngestionState.COMPLETE)
    state = new_review_state(
        ReviewBundle(
            review=review,
            source_text=source,
            criteria=criteria,
            evidence=[],
            findings=findings,
            gate=evaluate_gate(review, criteria, findings, [], []),
        )
    )
    imported = build_junit_evidence_import(
        state,
        JUNIT_AUDIT_XML,
        [
            JUnitMappingSelection(scope_id="suite-0001-case-0001", criterion_id="AC-01"),
            JUnitMappingSelection(scope_id="suite-0001-case-0002", criterion_id="AC-02"),
        ],
        importer="CONSTRUCTED JUnit actor",
        import_id="constructed-junit-import",
        imported_at=timestamp,
    )
    return append_junit_evidence_import(state, imported)
