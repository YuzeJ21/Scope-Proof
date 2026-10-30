"""Re-review must explain scope work even when candidates and status do not change."""

import json

import pytest
from pydantic import ValidationError

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import (
    export_comparison_json,
    export_comparison_markdown,
)
from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.schemas.models import (
    ChangedFileScope,
    FileScopeDecision,
    IngestionState,
    ReviewBundle,
)
from tests.reviews.test_comparison import bundle_with, evidence

OLD = "a" * 40
NEW = "b" * 40


def scoped_bundle(head: str, *extra_paths: str) -> ReviewBundle:
    bundle = bundle_with(evidence("candidate", sha=head), head_sha=head)
    assert bundle.review.changed_file_inventory is not None
    bundle.review.changed_file_inventory.files.extend(
        ChangedFileScope(path=path, status="added") for path in extra_paths
    )
    return revalidated(bundle)


def revalidated(bundle: ReviewBundle) -> ReviewBundle:
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, bundle.file_scope_decisions,
    )
    return ReviewBundle.model_validate(bundle.model_dump(mode="python"))


def decide(bundle: ReviewBundle, path: str, disposition: str) -> ReviewBundle:
    bundle.criteria_revision_number = 1
    provenance = bundle.review.criteria_source_provenance
    assert provenance is not None
    bundle.file_scope_decisions.append(FileScopeDecision(
        review_id=bundle.review.review_id, head_sha=bundle.review.head_sha,
        criteria_revision_number=1,
        normalized_criteria_sha256=provenance.normalized_criteria_sha256,
        path=path, disposition=disposition,
        criterion_id="AC-01" if disposition == "within_confirmed_criteria" else None,
        note="Constructed scope note", reviewer="Constructed reviewer",
    ))
    return revalidated(bundle)


def test_added_uncited_file_changes_report_when_candidate_counts_and_gate_do_not() -> None:
    previous = scoped_bundle(OLD)
    current = scoped_bundle(NEW)
    before = compare_reviews(previous, current)
    current = scoped_bundle(NEW, "src/unrelated.py")
    after = compare_reviews(previous, current)

    assert after.current_gate == before.current_gate
    assert after.evidence_change_counts == before.evidence_change_counts
    payload = json.loads(export_comparison_json(after))
    scope = payload["file_scope"]
    assert scope["current"]["unresolved_paths"] == ["src/unrelated.py"]
    assert scope["inventory_changes"] == [{
        "path": "src/unrelated.py", "kind": "added_to_inventory", "previous": None,
        "current": {"path": "src/unrelated.py", "status": "added", "previous_path": None},
    }]
    assert "src/unrelated.py" in export_comparison_markdown(after)


@pytest.mark.parametrize("unknown_side", ["previous", "current", "both"])
def test_unknown_inventory_never_becomes_a_known_empty_delta(unknown_side: str) -> None:
    previous, current = scoped_bundle(OLD), scoped_bundle(NEW, "generated/output.py")
    if unknown_side in {"previous", "both"}:
        previous.review.changed_file_inventory = None
    if unknown_side in {"current", "both"}:
        current.review.changed_file_inventory = None
    comparison = compare_reviews(revalidated(previous), revalidated(current))
    scope = comparison.file_scope
    assert scope is not None
    assert scope.inventory_changes is None
    unknown = scope.previous if unknown_side == "previous" else scope.current
    assert unknown.unresolved_paths is None
    assert "unknown" in export_comparison_markdown(comparison).lower()


def test_native_rename_metadata_and_absent_paths_do_not_infer_content_or_deletion() -> None:
    previous, current = scoped_bundle(OLD, "old.py"), scoped_bundle(NEW, "new.py")
    inventory = current.review.changed_file_inventory
    assert inventory is not None
    inventory.files[-1].status = "renamed"
    inventory.files[-1].previous_path = "old.py"
    inventory.files[0].previous_path = "earlier/export.py"
    scope = compare_reviews(previous, revalidated(current)).file_scope
    assert scope is not None
    assert [(row.path, row.kind) for row in scope.inventory_changes] == [
        ("new.py", "added_to_inventory"), ("old.py", "absent_from_current_inventory"),
        ("src/export.py", "metadata_changed"),
    ]
    assert scope.inventory_changes[0].current.previous_path == "old.py"
    assert scope.current.unresolved_paths == ["new.py"]


def test_latest_scope_decision_and_citations_control_unresolved_not_file_names() -> None:
    previous = decide(scoped_bundle(OLD, "generated/output.py"),
                      "generated/output.py", "outside_confirmed_criteria")
    current = decide(scoped_bundle(NEW, "generated/output.py"),
                     "generated/output.py", "outside_confirmed_criteria")
    current = decide(current, "generated/output.py", "within_confirmed_criteria")
    before_previous, before_current = previous.model_dump(), current.model_dump()
    scope = compare_reviews(previous, current).file_scope
    assert scope is not None
    assert scope.previous.unresolved_paths == []
    assert scope.current.cited_paths == ["src/export.py"]
    assert scope.current.unresolved_paths == ["generated/output.py"]
    assert len(scope.current.latest_decisions) == 1
    assert scope.current.latest_decisions[0].disposition == "within_confirmed_criteria"
    assert scope.previously_decided_paths_now_unresolved == ["generated/output.py"]
    assert previous.model_dump() == before_previous
    assert current.model_dump() == before_current


def test_fresh_explicit_outside_decision_resolves_scope_without_transferring_old_one() -> None:
    previous = decide(scoped_bundle(OLD, "notes.md"), "notes.md", "outside_confirmed_criteria")
    current = scoped_bundle(NEW, "notes.md")
    scope = compare_reviews(previous, current).file_scope
    assert scope.current.unresolved_paths == ["notes.md"]
    assert scope.current.latest_decisions == []
    assert scope.previously_decided_paths_now_unresolved == ["notes.md"]
    current = decide(current, "notes.md", "outside_confirmed_criteria")
    scope = compare_reviews(previous, current).file_scope
    assert scope.current.unresolved_paths == []
    assert scope.previously_decided_paths_now_unresolved == []


def test_known_empty_inventory_and_partial_ingestion_are_separate_facts() -> None:
    previous, current = bundle_with(head_sha=OLD), bundle_with(head_sha=NEW)
    current.review.ingestion_state = IngestionState.PARTIAL
    current.review.skipped_files = ["oversized.bin"]
    current.review.ingestion_warnings = ["File skipped: size limit"]
    comparison = compare_reviews(previous, revalidated(current))
    scope = comparison.file_scope
    assert scope.inventory_changes == []
    assert scope.current.unresolved_paths == []
    assert scope.current.skipped_files == ["oversized.bin"]
    assert scope.current.ingestion_state is IngestionState.PARTIAL
    report = export_comparison_markdown(comparison)
    assert "oversized.bin" in report and "partial" in report
    assert "File skipped\\: size limit" in report
    assert "content" in report.lower() and "acceptance" in report.lower()


@pytest.mark.parametrize("field,value", [
    ("head_sha", "c" * 40), ("review_id", "foreign-review"),
    ("criteria_revision_number", 2), ("normalized_criteria_sha256", "c" * 64),
    ("path", "not-in-inventory.py"),
])
def test_export_rejects_mutated_scope_decision_identity(field: str, value: object) -> None:
    current = decide(scoped_bundle(NEW, "notes.md"), "notes.md", "outside_confirmed_criteria")
    comparison = compare_reviews(scoped_bundle(OLD), current)
    setattr(comparison.file_scope.current.latest_decisions[0], field, value)
    with pytest.raises(ValidationError):
        export_comparison_json(comparison)
    with pytest.raises(ValidationError):
        export_comparison_markdown(comparison)


def test_export_rejects_mutated_inventory_and_comparison_head() -> None:
    comparison = compare_reviews(scoped_bundle(OLD), scoped_bundle(NEW))
    comparison.file_scope.current.inventory.head_sha = "c" * 40
    with pytest.raises(ValidationError):
        export_comparison_json(comparison)
    comparison.file_scope.current.inventory.head_sha = NEW
    comparison.current_head_sha = "c" * 40
    with pytest.raises(ValidationError):
        export_comparison_json(comparison)


def test_serialized_derived_scope_fields_are_recomputed_and_paths_are_canonical() -> None:
    comparison = compare_reviews(scoped_bundle(OLD), scoped_bundle(NEW, "z.py", "a.py"))
    payload = json.loads(export_comparison_json(comparison))
    payload.pop("evidence_change_counts")
    payload["file_scope"]["current"]["unresolved_paths"] = []
    payload["file_scope"]["inventory_changes"] = []
    scope = ReviewComparison.model_validate(payload).file_scope
    assert scope.current.unresolved_paths == ["a.py", "z.py"]
    assert [item.path for item in scope.inventory_changes] == ["a.py", "z.py"]


def test_scope_markdown_renders_untrusted_paths_notes_and_warnings_inertly() -> None:
    path = "[click](https://host.invalid)/<script>.py"
    current = decide(scoped_bundle(NEW, path), path, "outside_confirmed_criteria")
    current.file_scope_decisions[-1].note = "<script>alert(1)</script> [go](https://evil.invalid)"
    current.review.ingestion_warnings = ["<img src=x onerror=alert(1)>"]
    current.review.ingestion_state = IngestionState.PARTIAL
    report = export_comparison_markdown(compare_reviews(scoped_bundle(OLD), revalidated(current)))
    assert "<script>" not in report and "<img " not in report
    assert "<code>[click](https://host.invalid)/&lt;script&gt;.py</code>" in report
    assert "[go](https://evil.invalid)" not in report
    assert "Constructed reviewer" in report


def test_export_rejects_fabricated_scope_citation_without_linked_changed_file_evidence() -> None:
    comparison = compare_reviews(scoped_bundle(OLD), scoped_bundle(NEW, "notes.md"))
    comparison.file_scope.current.cited_paths = ["notes.md", "src/export.py"]
    for exporter in (export_comparison_json, export_comparison_markdown):
        with pytest.raises(ValidationError):
            exporter(comparison)


def test_export_rejects_scope_decision_for_a_foreign_criterion() -> None:
    current = decide(scoped_bundle(NEW, "notes.md"), "notes.md", "within_confirmed_criteria")
    comparison = compare_reviews(scoped_bundle(OLD), current)
    comparison.file_scope.current.latest_decisions[0].criterion_id = "nonexistent"
    for exporter in (export_comparison_json, export_comparison_markdown):
        with pytest.raises(ValidationError):
            exporter(comparison)


@pytest.mark.parametrize("mutation", ["digest", "complete_with_skip", "complete_with_warning"])
def test_export_rejects_contradictory_scope_context(mutation: str) -> None:
    comparison = compare_reviews(scoped_bundle(OLD), scoped_bundle(NEW))
    if mutation == "digest":
        comparison.file_scope.current.normalized_criteria_sha256 = "c" * 64
    elif mutation == "complete_with_skip":
        comparison.file_scope.current.skipped_files = ["large.bin"]
    else:
        comparison.file_scope.current.ingestion_warnings = ["File limit"]
    for exporter in (export_comparison_json, export_comparison_markdown):
        with pytest.raises(ValidationError):
            exporter(comparison)


def test_unknown_previous_inventory_still_exports_known_current_inventory_metadata() -> None:
    previous, current = scoped_bundle(OLD), scoped_bundle(NEW)
    previous.review.changed_file_inventory = None
    report = export_comparison_markdown(compare_reviews(revalidated(previous), current))
    current_section = report.split("### Current Scope", 1)[1]
    assert "src/export.py" in current_section and "modified" in current_section
    empty = export_comparison_markdown(compare_reviews(bundle_with(head_sha=OLD),
                                                      bundle_with(head_sha=NEW)))
    assert "Known empty inventory" in empty


@pytest.mark.parametrize("mutation", [
    "blank_review", "duplicate_citations", "duplicate_decisions", "missing_finding",
    "foreign_evidence", "noncanonical_criteria", "different_criteria",
])
def test_export_rejects_inconsistent_scope_projection(mutation: str) -> None:
    current = decide(scoped_bundle(NEW, "notes.md"), "notes.md", "outside_confirmed_criteria")
    comparison = compare_reviews(scoped_bundle(OLD), current)
    snapshot = comparison.file_scope.current
    if mutation == "blank_review":
        snapshot.review_id = " "
    elif mutation == "duplicate_citations":
        snapshot.cited_paths *= 2
    elif mutation == "duplicate_decisions":
        snapshot.latest_decisions *= 2
    elif mutation == "missing_finding":
        snapshot.finding_evidence_ids = {}
    elif mutation == "foreign_evidence":
        snapshot.finding_evidence_ids = {"AC-01": ["foreign-candidate"]}
    elif mutation == "noncanonical_criteria":
        snapshot.criterion_ids = ["AC-01", "AC-01"]
    else:
        snapshot.criterion_ids = ["AC-01", "AC-02"]
        snapshot.finding_evidence_ids["AC-02"] = []
    with pytest.raises(ValidationError):
        export_comparison_json(comparison)


def test_scope_projection_is_order_independent_and_detached_from_input_inventory() -> None:
    previous, current = scoped_bundle(OLD), scoped_bundle(NEW, "z.py", "a.py")
    first = compare_reviews(previous, current)
    current.review.changed_file_inventory.files.reverse()
    second = compare_reviews(previous, current)
    assert export_comparison_json(first) == export_comparison_json(second)
    first.file_scope.current.inventory.files[0].status = "removed"
    assert all(item.status != "removed" for item in current.review.changed_file_inventory.files)
