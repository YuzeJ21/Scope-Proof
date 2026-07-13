import pytest

from scopeproof_core.gates.guidance import decision_guidance, gate_guidance
from scopeproof_core.schemas.models import GateDecision, GateVerdict, HumanDecision


@pytest.mark.parametrize(
    ("decision", "expected_text"),
    [
        (
            HumanDecision.ACCEPTED,
            "Records reviewer acceptance and treats this criterion as resolved.",
        ),
        (
            HumanDecision.ACCEPTED_EXCEPTION,
            "Records an explicit exception and makes the review conditional.",
        ),
        (
            HumanDecision.CHANGE_REQUIRED,
            "Makes this criterion blocking until a later decision replaces it.",
        ),
        (
            HumanDecision.REJECTED_FINDING,
            "Rejects the provisional finding but does not resolve this criterion; its finding "
            "status continues to control the gate.",
        ),
        (
            HumanDecision.MANUALLY_VERIFIED,
            "Records external manual verification at the selected evidence level and treats this "
            "criterion as resolved.",
        ),
        (
            HumanDecision.NOT_IN_SCOPE,
            "Records a scope exception, removes this criterion from active blocking and "
            "unresolved checks, and can leave the review conditional.",
        ),
    ],
)
def test_decision_guidance_maps_every_human_decision(
    decision: HumanDecision, expected_text: str
) -> None:
    assert decision_guidance(decision) == expected_text


@pytest.mark.parametrize(
    ("reason_code", "expected_text"),
    [
        (
            "required_checks_failing",
            "Review the failing required GitHub checks before acceptance; ScopeProof does not "
            "rerun or diagnose them.",
        ),
        (
            "blocking_criteria",
            "Review required changes or missing or partial evidence for blocking criteria: AC-01.",
        ),
        (
            "conditional_criteria",
            "Explicitly review conditional criteria or accepted exceptions before acceptance: "
            "AC-02.",
        ),
        (
            "unresolved_criteria",
            "Record an explicit human decision for unresolved criteria: AC-03. ScopeProof does not "
            "decide them.",
        ),
        (
            "criteria_not_confirmed",
            "Confirm the normalized criterion set before relying on the analysis.",
        ),
        (
            "partial_ingestion",
            "Retry public-repository ingestion or document the missing repository data before "
            "relying on the review.",
        ),
        (
            "ingestion_failed",
            "Check the public PR URL and access, then retry ingestion; ScopeProof does not execute "
            "PR code.",
        ),
        (
            "checks_not_passing",
            "Wait for required GitHub checks to pass or become available before acceptance.",
        ),
        (
            "final_acceptance_required",
            "Record final acceptance only after a reviewer has reviewed every criterion and its "
            "evidence.",
        ),
    ],
)
def test_gate_guidance_maps_every_known_reason(reason_code: str, expected_text: str) -> None:
    decision = GateDecision(
        verdict=GateVerdict.BLOCKED,
        blocking_criteria=["AC-01"],
        conditional_criteria=["AC-02"],
        unresolved_criteria=["AC-03"],
        reason_codes=[reason_code],
    )

    assert gate_guidance(decision) == [expected_text]


def test_gate_guidance_preserves_reason_order_and_deduplicates() -> None:
    decision = GateDecision(
        verdict=GateVerdict.BLOCKED,
        blocking_criteria=["AC-02", "AC-01"],
        unresolved_criteria=["AC-04", "AC-03"],
        reason_codes=["unresolved_criteria", "blocking_criteria", "unresolved_criteria"],
    )

    assert gate_guidance(decision) == [
        "Record an explicit human decision for unresolved criteria: AC-03, AC-04. ScopeProof does "
        "not decide them.",
        "Review required changes or missing or partial evidence for blocking criteria: AC-01, "
        "AC-02.",
    ]


def test_gate_guidance_keeps_unknown_reason_visible() -> None:
    decision = GateDecision(
        verdict=GateVerdict.NEEDS_REVIEW,
        reason_codes=["future_reason"],
    )

    assert gate_guidance(decision) == [
        "Review gate reason `future_reason` before acceptance."
    ]


def test_gate_guidance_states_when_criterion_ids_are_missing() -> None:
    decision = GateDecision(
        verdict=GateVerdict.BLOCKED,
        reason_codes=["blocking_criteria"],
    )

    assert gate_guidance(decision) == [
        "Review required changes or missing or partial evidence for blocking criteria: none "
        "recorded."
    ]
