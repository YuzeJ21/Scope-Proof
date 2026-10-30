import json
from pathlib import Path

from scopeproof_core.demo import build_review_from_paths
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.lifecycle import (
    append_file_scope_decision,
    append_resolution,
    new_review_state,
)
from scopeproof_core.schemas.models import (
    FileScopeDecision,
    GateVerdict,
    HumanDecision,
    ResolutionEvent,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def test_version_four_ready_reopens_with_unknown_file_scope_and_preserved_events(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2] / "evals"
    bundle = build_review_from_paths(
        root / "fixtures/scope_expansion_pr.json",
        root / "labels/benchmark_scope_expansion.json",
    )
    bundle.review.final_acceptance = False
    bundle.resolutions = []
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, [], bundle.evidence
    )
    state = new_review_state(bundle)
    state = append_resolution(state, ResolutionEvent(
        criterion_id="AC-01", decision=HumanDecision.ACCEPTED,
        comment="CSV candidate reviewed", reviewer="Historical reviewer",
    ))
    state = append_file_scope_decision(state, FileScopeDecision(
        review_id=state.review.review_id,
        path="src/auth.py", head_sha=state.review.head_sha,
        criteria_revision_number=1, disposition="outside_confirmed_criteria",
        normalized_criteria_sha256=(
            state.review.criteria_source_provenance.normalized_criteria_sha256
        ),
        note="Historical scope review", reviewer="Historical reviewer",
    ))
    state = append_resolution(state, ResolutionEvent(
        final_acceptance=True, reviewer="Historical reviewer",
    ))
    assert state.bundle.gate.verdict is GateVerdict.READY

    store = JsonReviewStore(tmp_path / "reviews")
    path = store.save(state)
    old = json.loads(path.read_text(encoding="utf-8"))
    old["record_version"] = 4
    old["state"]["review"].pop("changed_file_inventory")
    old["state"]["bundle"]["review"].pop("changed_file_inventory")
    old["state"]["bundle"].pop("file_scope_decisions")
    path.write_text(json.dumps(old), encoding="utf-8")

    reopened = store.load(state.review.review_id)
    assert reopened.review.final_acceptance is True
    assert reopened.resolution_events == state.resolution_events
    assert reopened.review.changed_file_inventory is None
    assert reopened.bundle.file_scope_decisions == []
    assert reopened.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert "changed_file_inventory_unknown" in reopened.bundle.gate.reason_codes

    resaved = store.save(reopened)
    assert json.loads(resaved.read_text(encoding="utf-8"))["record_version"] == 6
    assert store.load(state.review.review_id).bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
