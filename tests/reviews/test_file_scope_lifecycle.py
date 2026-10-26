from pathlib import Path

import pytest

from scopeproof_core.demo import build_review_from_paths
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reviews.lifecycle import (
    append_file_scope_decision,
    append_resolution,
    can_record_final_acceptance,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    Criterion,
    FileScopeDecision,
    GateVerdict,
    HumanDecision,
    ResolutionEvent,
    ReviewBundle,
)


def scope_state():
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
    return new_review_state(bundle)


def scope_decision(state, *, head_sha="head-scope-001", path="src/auth.py"):
    return FileScopeDecision(
        review_id=state.review.review_id,
        path=path,
        head_sha=head_sha,
        criteria_revision_number=1,
        normalized_criteria_sha256=(
            state.review.criteria_source_provenance.normalized_criteria_sha256
        ),
        disposition="outside_confirmed_criteria",
        note="Reviewed the auth change; it is outside the confirmed CSV criterion.",
        reviewer="Fixture reviewer",
    )


def test_uncited_file_needs_attributable_decision_before_final_acceptance() -> None:
    state = scope_state()
    state = append_resolution(
        state,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            reviewer="Fixture reviewer",
            comment="CSV candidate reviewed",
        ),
    )
    assert not can_record_final_acceptance(state)

    state = append_file_scope_decision(state, scope_decision(state))
    assert can_record_final_acceptance(state)
    assert state.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
    assert state.bundle.file_scope_decisions[0].reviewer == "Fixture reviewer"

    state = append_resolution(
        state,
        ResolutionEvent(
            final_acceptance=True,
            reviewer="Fixture reviewer",
        ),
    )
    assert state.bundle.gate.verdict is GateVerdict.READY


def test_file_decision_rejects_wrong_head_and_unknown_path() -> None:
    state = scope_state()
    for item in [
        scope_decision(state, head_sha="other"),
        scope_decision(state, path="src/not-in-pr.py"),
    ]:
        with pytest.raises(ValueError):
            append_file_scope_decision(state, item)
    assert state.bundle.file_scope_decisions == []


def test_file_decision_history_is_append_only_and_latest_controls_gate() -> None:
    state = scope_state()
    state = append_file_scope_decision(state, scope_decision(state))
    newer = scope_decision(state)
    newer.disposition = "within_confirmed_criteria"
    newer.criterion_id = "AC-01"
    state = append_file_scope_decision(state, newer)

    assert len(state.bundle.file_scope_decisions) == 2
    assert "uncited_changed_files" in state.bundle.gate.reason_codes


def test_criteria_revision_preserves_old_file_decision_only_in_history() -> None:
    state = scope_state()
    state = append_file_scope_decision(state, scope_decision(state))
    revised = revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )

    assert revised.bundle is None
    assert revised.analysis_history[-1].file_scope_decisions == state.bundle.file_scope_decisions
    assert revised.review.criteria_confirmed is False


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"note": "   "}, "requires a reviewer and explanation"),
        ({"reviewer": "   "}, "requires a reviewer and explanation"),
        (
            {"disposition": "within_confirmed_criteria", "criterion_id": None},
            "within-criteria decision requires a criterion ID",
        ),
        ({"criterion_id": "AC-01"}, "outside-criteria decision cannot cite"),
    ],
)
def test_file_decision_schema_rejects_ambiguous_review(
    changes: dict[str, object], message: str
) -> None:
    decision = scope_decision(scope_state())
    with pytest.raises(ValueError, match=message):
        FileScopeDecision.model_validate({**decision.model_dump(), **changes})


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"criterion_id": "AC-UNKNOWN", "disposition": "within_confirmed_criteria"},
            "criterion must be confirmed",
        ),
        ({"criteria_revision_number": 2}, "must match criteria revision"),
    ],
)
def test_bundle_rejects_file_scope_decision_outside_confirmed_binding(
    changes: dict[str, object], message: str
) -> None:
    state = scope_state()
    bundle = state.bundle.model_copy(deep=True)
    decision = scope_decision(state)
    bundle.file_scope_decisions = [
        FileScopeDecision.model_validate(
            {
                **decision.model_dump(),
                **changes,
            }
        )
    ]
    with pytest.raises(ValueError, match=message):
        ReviewBundle.model_validate(bundle.model_dump(mode="python"))


def test_bundle_rejects_duplicate_file_scope_decision_events() -> None:
    state = scope_state()
    bundle = state.bundle.model_copy(deep=True)
    decision = scope_decision(state)
    bundle.file_scope_decisions = [decision, decision.model_copy(deep=True)]
    with pytest.raises(ValueError, match="event IDs must be unique"):
        ReviewBundle.model_validate(bundle.model_dump(mode="python"))
