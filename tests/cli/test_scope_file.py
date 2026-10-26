from pathlib import Path

import pytest

from scopeproof_core.cli import main
from scopeproof_core.demo import build_review_from_paths
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.storage.json_store import JsonReviewStore


def test_cli_records_exact_head_scope_decision(tmp_path: Path, capsys) -> None:
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
    store = JsonReviewStore(tmp_path / "reviews")
    store.save(state)
    note = tmp_path / "note.txt"
    note.write_text("Reviewed the auth change against confirmed CSV criteria.", encoding="utf-8")

    assert main([
        "scope-file", state.review.review_id,
        "--head-sha", state.review.head_sha,
        "--path", "src/auth.py",
        "--disposition", "outside_confirmed_criteria",
        "--reviewer", "CLI reviewer",
        "--comment-file", str(note),
        "--storage-dir", str(store.directory),
    ]) == 0

    reopened = store.load(state.review.review_id)
    assert reopened.bundle.file_scope_decisions[-1].head_sha == "head-scope-001"
    assert reopened.bundle.file_scope_decisions[-1].reviewer == "CLI reviewer"
    assert "head-scope-001" in capsys.readouterr().out


def test_cli_rejects_stale_expected_head(tmp_path: Path) -> None:
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
    store = JsonReviewStore(tmp_path / "reviews")
    state = new_review_state(bundle)
    store.save(state)
    note = tmp_path / "note.txt"
    note.write_text("Reviewed scope", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([
            "scope-file", state.review.review_id, "--head-sha", "stale-head",
            "--path", "src/auth.py", "--disposition", "outside_confirmed_criteria",
            "--reviewer", "CLI reviewer", "--comment-file", str(note),
            "--storage-dir", str(store.directory),
        ])
    assert error.value.code == 2
    assert store.load(state.review.review_id).bundle.file_scope_decisions == []
