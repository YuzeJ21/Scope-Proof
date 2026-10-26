"""Changed-file scope is an explicit reviewer decision, never a path heuristic."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from scopeproof_core.demo import build_review, build_review_from_paths
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.schemas.models import (
    FileScopeDecision,
    GateVerdict,
    IngestionState,
    PullRequestSnapshot,
    ReviewBundle,
)

ROOT = Path(__file__).resolve().parents[2] / "evals"


def scope_bundle() -> ReviewBundle:
    return build_review_from_paths(
        ROOT / "fixtures/scope_expansion_pr.json",
        ROOT / "labels/benchmark_scope_expansion.json",
    )


def decision(
    bundle: ReviewBundle,
    path: str = "src/auth.py",
    *,
    head_sha: str = "head-scope-001",
    disposition: str = "outside_confirmed_criteria",
    criterion_id: str | None = None,
) -> FileScopeDecision:
    return FileScopeDecision(
        review_id=bundle.review.review_id,
        path=path,
        head_sha=head_sha,
        criteria_revision_number=1,
        normalized_criteria_sha256=(
            bundle.review.criteria_source_provenance.normalized_criteria_sha256
        ),
        disposition=disposition,
        criterion_id=criterion_id,
        note="Reviewed this exact-head change against the confirmed CSV criterion.",
        reviewer="Fixture reviewer",
    )


def test_explicit_outside_criteria_decision_resolves_uncited_file() -> None:
    bundle = scope_bundle()
    bundle.criteria_revision_number = 1
    item = decision(bundle)
    gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, [item],
    )

    assert gate.verdict is GateVerdict.READY
    validated = ReviewBundle.model_validate(
        {**bundle.model_dump(mode="python"), "file_scope_decisions": [item], "gate": gate}
    )
    assert validated.file_scope_decisions == [item]


def test_orphan_candidate_does_not_cite_changed_file() -> None:
    bundle = scope_bundle()
    orphan = bundle.evidence[0].model_copy(deep=True)
    orphan.evidence_id = "EV-ORPHAN"
    orphan.file_path = "src/auth.py"
    orphan.permalink = (
        "https://github.com/scopeproof/bench/blob/head-scope-001/src/auth.py#L10-L10"
    )
    bundle.evidence.append(orphan)
    bundle.retrieval_diagnostics = []
    gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence,
    )
    assert gate.verdict is GateVerdict.NEEDS_REVIEW


def test_decision_requires_known_confirmed_revision() -> None:
    bundle = scope_bundle()
    item = decision(bundle)
    gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, [item],
    )
    with pytest.raises(ValidationError, match="criteria revision"):
        ReviewBundle.model_validate({
            **bundle.model_dump(mode="python"), "file_scope_decisions": [item],
            "gate": gate,
        })


def test_decision_cannot_move_between_reviews_or_confirmed_criteria() -> None:
    bundle = scope_bundle()
    bundle.criteria_revision_number = 1
    item = decision(bundle)
    for altered in [
        item.model_copy(update={"review_id": "other-review"}),
        item.model_copy(update={"normalized_criteria_sha256": "0" * 64}),
    ]:
        gate = evaluate_gate(
            bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
            bundle.evidence, [altered],
        )
        assert gate.verdict is GateVerdict.NEEDS_REVIEW
        with pytest.raises(ValidationError, match="file scope decision"):
            ReviewBundle.model_validate({
                **bundle.model_dump(mode="python"),
                "file_scope_decisions": [altered], "gate": gate,
            })


def test_within_criteria_decision_cannot_substitute_for_citation() -> None:
    bundle = scope_bundle()
    gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence,
        [decision(bundle, disposition="within_confirmed_criteria", criterion_id="AC-01")],
    )
    assert gate.verdict is GateVerdict.NEEDS_REVIEW
    assert "uncited_changed_files" in gate.reason_codes


@pytest.mark.parametrize("path", ["generated/client.py", "docs/other.md", "src/new_name.py"])
def test_file_names_do_not_imply_outside_scope(path: str) -> None:
    snapshot = PullRequestSnapshot.model_validate_json(
        (ROOT / "fixtures/scope_expansion_pr.json").read_text(encoding="utf-8")
    )
    snapshot.files[1].path = path
    if path == "src/new_name.py":
        snapshot.files[1].status = "renamed"
        snapshot.files[1].previous_path = "src/old_name.py"
    labels = __import__("json").loads(
        (ROOT / "labels/benchmark_scope_expansion.json").read_text(encoding="utf-8")
    )
    bundle = build_review(snapshot, labels)

    assert bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert {item.path for item in bundle.review.changed_file_inventory.files} == {
        "src/export.py", path,
    }
    if path == "src/new_name.py":
        renamed = bundle.review.changed_file_inventory.files[1]
        assert (renamed.status, renamed.previous_path) == ("renamed", "src/old_name.py")


def test_skipped_file_stays_partial_even_with_decision() -> None:
    bundle = scope_bundle()
    review = bundle.review.model_copy(deep=True)
    review.ingestion_state = IngestionState.PARTIAL
    review.skipped_files = ["src/skipped.py"]
    gate = evaluate_gate(
        review, bundle.criteria, bundle.findings, bundle.resolutions,
        bundle.evidence, [decision(bundle)],
    )
    assert gate.verdict is GateVerdict.NEEDS_REVIEW
    assert "partial_ingestion" in gate.reason_codes


def test_unknown_inventory_is_distinct_from_verified_empty_inventory() -> None:
    bundle = scope_bundle()
    unknown = bundle.review.model_copy(update={"changed_file_inventory": None})
    assert evaluate_gate(
        unknown, bundle.criteria, bundle.findings, bundle.resolutions, bundle.evidence
    ).verdict is GateVerdict.NEEDS_REVIEW
    assert "changed_file_inventory_unknown" in evaluate_gate(
        unknown, bundle.criteria, bundle.findings, bundle.resolutions, bundle.evidence
    ).reason_codes

    empty = bundle.review.model_copy(deep=True)
    empty.changed_file_inventory.files = []
    assert evaluate_gate(
        empty, bundle.criteria, bundle.findings, bundle.resolutions, []
    ).verdict is GateVerdict.READY


def test_wrong_head_or_path_decision_is_rejected() -> None:
    bundle = scope_bundle()
    bundle.criteria_revision_number = 1
    for item in [
        decision(bundle, head_sha="other-head"),
        decision(bundle, path="src/never_changed.py"),
    ]:
        with pytest.raises(ValidationError, match="file scope decision"):
            ReviewBundle.model_validate({
                **bundle.model_dump(mode="python"), "file_scope_decisions": [item],
            })


def test_inventory_head_must_match_review() -> None:
    bundle = scope_bundle()
    payload = bundle.review.model_dump(mode="python")
    payload["changed_file_inventory"]["head_sha"] = "other-head"
    with pytest.raises(ValidationError, match="inventory head"):
        bundle.review.model_validate(payload)
