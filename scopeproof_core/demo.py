"""Offline, deliberately constructed ScopeProof launch demonstration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scopeproof_core.criteria.confirmation import (
    CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
    build_criteria_source_provenance,
)
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
from scopeproof_core.schemas.models import (
    Criterion,
    HumanResolution,
    PullRequestSnapshot,
    Review,
    ReviewBundle,
)
from scopeproof_core.verification.service import build_findings

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = _ROOT / "evals" / "fixtures" / "csv_export_pr.json"
_LABELS = _ROOT / "evals" / "labels" / "csv_export_expected.json"


def load_demo_snapshot() -> PullRequestSnapshot:
    """Load the offline public-PR-shaped fixture."""
    return PullRequestSnapshot.model_validate_json(_FIXTURE.read_text(encoding="utf-8"))


def load_demo_labels() -> dict:
    return json.loads(_LABELS.read_text(encoding="utf-8"))


def build_review(snapshot: PullRequestSnapshot, labels: dict) -> ReviewBundle:
    """Run the product analysis path against one fixture and its human labels."""
    criteria = [Criterion.model_validate(item) for item in labels["criteria"]]
    source_text = labels["source_text"]
    provenance = build_criteria_source_provenance(
        source_uri=CONSTRUCTED_DEMO_CRITERIA_SOURCE_URI,
        source_revision=labels.get("fixture"),
        source_text=source_text,
        criteria=criteria,
        confirmed_by="ScopeProof constructed demo",
        confirmed_at=datetime(2026, 7, 12, tzinfo=UTC),
    )
    review = Review(
        repository=snapshot.repository,
        pr_number=snapshot.pr_number,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
        check_state=snapshot.check_state,
        ci_observation=snapshot.ci_observation,
        criteria_confirmed=labels.get("criteria_confirmed", True),
        criteria_source_provenance=provenance,
        ingestion_state=snapshot.ingestion_state,
        ingestion_warnings=snapshot.warnings,
        skipped_files=snapshot.skipped_files,
        final_acceptance=labels.get("final_acceptance", False),
    )
    retrieval_result = retrieve_evidence_with_diagnostics(snapshot, criteria)
    evidence = retrieval_result.evidence
    findings = build_findings(criteria, evidence, snapshot.ingestion_state)
    resolutions = [
        HumanResolution.model_validate(item) for item in labels.get("resolutions", [])
    ]
    gate = evaluate_gate(review, criteria, findings, resolutions)
    return ReviewBundle(
        review=review,
        source_text=source_text,
        criteria=criteria,
        evidence=evidence,
        retrieval_diagnostics=retrieval_result.diagnostics,
        findings=findings,
        resolutions=resolutions,
        gate=gate,
    )


def build_review_from_paths(fixture_path: Path, label_path: Path) -> ReviewBundle:
    """Load one fixture-label pair without relying on demo-only module state."""
    snapshot = PullRequestSnapshot.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    labels = json.loads(label_path.read_text(encoding="utf-8"))
    return build_review(snapshot, labels)


def build_demo_review() -> ReviewBundle:
    """Run the production analysis path over the controlled omission fixture."""
    return build_review(load_demo_snapshot(), load_demo_labels())
