"""Offline, deliberately constructed ScopeProof launch demonstration."""

from __future__ import annotations

import json
from pathlib import Path

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.schemas.models import (
    Criterion,
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


def build_demo_review() -> ReviewBundle:
    """Run the production analysis path over the controlled omission fixture."""
    snapshot = load_demo_snapshot()
    labels = load_demo_labels()
    criteria = [Criterion.model_validate(item) for item in labels["criteria"]]
    review = Review(
        repository=snapshot.repository,
        pr_number=snapshot.pr_number,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
        check_state=snapshot.check_state,
        criteria_confirmed=True,
        ingestion_state=snapshot.ingestion_state,
    )
    evidence = retrieve_evidence(snapshot, criteria)
    findings = build_findings(criteria, evidence, snapshot.ingestion_state)
    gate = evaluate_gate(review, criteria, findings, [])
    return ReviewBundle(
        review=review,
        source_text=labels["source_text"],
        criteria=criteria,
        evidence=evidence,
        findings=findings,
        gate=gate,
    )
