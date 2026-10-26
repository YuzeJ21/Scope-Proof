"""Human-readable exports retain the scope basis for an exact-head Ready gate."""

import csv
import io
import json
from pathlib import Path

from scopeproof_core.demo import build_review_from_paths
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import export_csv, export_html, export_markdown
from scopeproof_core.schemas.models import FileScopeDecision, GateVerdict


def scope_bundle():
    root = Path(__file__).resolve().parents[2] / "evals"
    return build_review_from_paths(
        root / "fixtures/scope_expansion_pr.json",
        root / "labels/benchmark_scope_expansion.json",
    )


def test_ready_exports_show_file_decision_rationale_and_binding() -> None:
    bundle = scope_bundle()
    bundle.criteria_revision_number = 1
    bundle.file_scope_decisions = [FileScopeDecision(
        review_id=bundle.review.review_id,
        path="src/auth.py",
        head_sha=bundle.review.head_sha,
        criteria_revision_number=1,
        normalized_criteria_sha256=(
            bundle.review.criteria_source_provenance.normalized_criteria_sha256
        ),
        disposition="outside_confirmed_criteria",
        note="=ignored <script>alert(1)</script> after criteria review",
        reviewer="Fixture reviewer",
    )]
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, bundle.file_scope_decisions,
    )
    assert bundle.gate.verdict is GateVerdict.READY

    markdown = export_markdown(bundle)
    page = export_html(bundle)
    row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert "Changed-file Scope" in markdown and "src/auth.py" in markdown
    assert "Fixture reviewer" in markdown and bundle.review.head_sha in markdown
    assert "<script>" not in markdown
    assert "Changed-file Scope" in page and "src/auth.py" in page
    assert "Fixture reviewer" in page and bundle.review.head_sha in page
    assert "<script>" not in page
    assert row["changed_file_inventory_state"] == "verified"
    decisions = json.loads(row["file_scope_decisions"])
    assert decisions[0]["note"].startswith("=ignored")
    assert decisions[0]["review_id"] == bundle.review.review_id


def test_unknown_historical_inventory_is_visible_in_exports() -> None:
    bundle = scope_bundle()
    bundle.review.changed_file_inventory = None
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence,
    )
    assert bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert "unknown legacy inventory" in export_markdown(bundle)
    assert "unknown legacy inventory" in export_html(bundle)
    row = next(csv.DictReader(io.StringIO(export_csv(bundle))))
    assert row["changed_file_inventory_state"] == "unknown legacy inventory"
