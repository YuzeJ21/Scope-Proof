"""Deterministic operator guidance derived from validated gate reasons."""

from scopeproof_core.schemas.models import GateDecision, HumanDecision

_DECISION_GUIDANCE = {
    HumanDecision.ACCEPTED: (
        "Records reviewer acceptance and treats this criterion as resolved."
    ),
    HumanDecision.ACCEPTED_EXCEPTION: (
        "Records an explicit exception and marks this criterion conditional."
    ),
    HumanDecision.CHANGE_REQUIRED: (
        "Makes this criterion blocking until a later decision replaces it."
    ),
    HumanDecision.REJECTED_FINDING: (
        "Rejects the provisional finding but does not resolve this criterion; its finding status "
        "continues to control the gate."
    ),
    HumanDecision.MANUALLY_VERIFIED: (
        "Records external manual verification at the selected evidence level and treats this "
        "criterion as resolved."
    ),
    HumanDecision.NOT_IN_SCOPE: (
        "Records a scope exception, removes this criterion from active blocking and unresolved "
        "checks, and contributes a Conditional outcome when no higher-severity reason exists."
    ),
}


def _criterion_ids(values: list[str]) -> str:
    return ", ".join(sorted(values)) or "none recorded"


def decision_guidance(decision: HumanDecision) -> str:
    """Explain a human decision's existing deterministic gate effect."""
    return _DECISION_GUIDANCE[decision]


def gate_guidance(gate: GateDecision) -> list[str]:
    """Explain recorded gate reasons without changing or resolving the gate."""
    messages: list[str] = []
    seen: set[str] = set()
    for code in gate.reason_codes:
        if code in seen:
            continue
        seen.add(code)
        if code == "required_checks_failing":
            message = (
                "Review the failing required GitHub checks before acceptance; ScopeProof does not "
                "rerun or diagnose them."
            )
        elif code == "blocking_criteria":
            message = (
                "Review required changes or missing or partial evidence for blocking criteria: "
                f"{_criterion_ids(gate.blocking_criteria)}."
            )
        elif code == "conditional_criteria":
            message = (
                "Explicitly review conditional criteria or accepted exceptions before acceptance: "
                f"{_criterion_ids(gate.conditional_criteria)}."
            )
        elif code == "unresolved_criteria":
            message = (
                "Record an explicit human decision for unresolved criteria: "
                f"{_criterion_ids(gate.unresolved_criteria)}. ScopeProof does not decide them."
            )
        elif code == "criteria_not_confirmed":
            message = "Confirm the normalized criterion set before relying on the analysis."
        elif code == "partial_ingestion":
            message = (
                "Retry public-repository ingestion or document the missing repository data before "
                "relying on the review."
            )
        elif code == "ingestion_failed":
            message = (
                "Check the public PR URL and access, then retry ingestion; ScopeProof does not "
                "execute PR code."
            )
        elif code == "ingestion_limitations_present":
            message = (
                "Treat the review as incomplete because ingestion limitations were recorded; "
                "reload the PR before acceptance."
            )
        elif code == "checks_not_passing":
            message = (
                "Wait for required GitHub checks to pass or become available before acceptance."
            )
        elif code == "final_acceptance_required":
            message = (
                "Record final acceptance only after a reviewer has reviewed every criterion and "
                "its evidence."
            )
        else:
            message = f"Review gate reason `{code}` before acceptance."
        messages.append(message)
    return messages
