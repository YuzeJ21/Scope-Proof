"""Explicit, reproducible ScopeProof gate truth table."""

from scopeproof_core.schemas.models import (
    CheckState,
    Criterion,
    Finding,
    FindingStatus,
    GateDecision,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    IngestionState,
    Priority,
    Review,
)

_RESOLVED_DECISIONS = {
    HumanDecision.ACCEPTED,
    HumanDecision.ACCEPTED_EXCEPTION,
    HumanDecision.MANUALLY_VERIFIED,
    HumanDecision.NOT_IN_SCOPE,
}


def evaluate_gate(
    review: Review,
    criteria: list[Criterion],
    findings: list[Finding],
    resolutions: list[HumanResolution],
) -> GateDecision:
    """Return the highest-severity verdict supported by explicit reason codes."""
    finding_by_id = {finding.criterion_id: finding for finding in findings}
    resolution_by_id = {resolution.criterion_id: resolution for resolution in resolutions}

    blocking: set[str] = set()
    conditional: set[str] = set()
    unresolved: set[str] = set()
    exceptions: set[str] = set()
    reason_codes: list[str] = []
    ingestion_limitations_present = bool(review.ingestion_warnings or review.skipped_files)

    if review.check_state is CheckState.FAILING:
        reason_codes.append("required_checks_failing")

    for criterion in criteria:
        finding = finding_by_id.get(criterion.criterion_id)
        resolution = resolution_by_id.get(criterion.criterion_id)
        decision = resolution.decision if resolution else None

        if decision is HumanDecision.CHANGE_REQUIRED:
            blocking.add(criterion.criterion_id)
            continue
        if decision is HumanDecision.ACCEPTED_EXCEPTION:
            exceptions.add(criterion.criterion_id)
            conditional.add(criterion.criterion_id)
            continue
        if decision is HumanDecision.NOT_IN_SCOPE:
            exceptions.add(criterion.criterion_id)
            continue
        if decision in {HumanDecision.ACCEPTED, HumanDecision.MANUALLY_VERIFIED}:
            continue

        if finding is None:
            unresolved.add(criterion.criterion_id)
        elif finding.status in {FindingStatus.MISSING, FindingStatus.PARTIAL}:
            if criterion.priority is Priority.MUST_HAVE:
                blocking.add(criterion.criterion_id)
            else:
                conditional.add(criterion.criterion_id)
        elif finding.status is FindingStatus.NEEDS_REVIEW or (
            criterion.priority is Priority.MUST_HAVE and decision not in _RESOLVED_DECISIONS
        ):
            unresolved.add(criterion.criterion_id)

    if blocking:
        reason_codes.append("blocking_criteria")
    if conditional:
        reason_codes.append("conditional_criteria")
    if unresolved:
        reason_codes.append("unresolved_criteria")

    if review.check_state is CheckState.FAILING or blocking:
        verdict = GateVerdict.BLOCKED
    else:
        if not review.criteria_confirmed:
            reason_codes.append("criteria_not_confirmed")
        if review.ingestion_state is IngestionState.PARTIAL:
            reason_codes.append("partial_ingestion")
        elif review.ingestion_state is IngestionState.FAILED:
            reason_codes.append("ingestion_failed")
        if review.check_state in {CheckState.PENDING, CheckState.UNAVAILABLE}:
            reason_codes.append("checks_not_passing")
        if ingestion_limitations_present and review.ingestion_state is IngestionState.COMPLETE:
            reason_codes.append("ingestion_limitations_present")

        needs_review = bool(
            unresolved
            or not review.criteria_confirmed
            or review.ingestion_state is not IngestionState.COMPLETE
            or ingestion_limitations_present
            or review.check_state in {CheckState.PENDING, CheckState.UNAVAILABLE}
        )
        if needs_review:
            verdict = GateVerdict.NEEDS_REVIEW
        elif conditional or exceptions:
            verdict = GateVerdict.CONDITIONAL
        elif not review.final_acceptance:
            verdict = GateVerdict.NEEDS_REVIEW
            reason_codes.append("final_acceptance_required")
        else:
            verdict = GateVerdict.READY

    return GateDecision(
        verdict=verdict,
        blocking_criteria=sorted(blocking),
        conditional_criteria=sorted(conditional),
        unresolved_criteria=sorted(unresolved),
        resolved_exceptions=sorted(exceptions),
        reason_codes=list(dict.fromkeys(reason_codes)),
    )
