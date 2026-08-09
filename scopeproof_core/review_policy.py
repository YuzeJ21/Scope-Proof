"""Shared fail-closed policies for human review decisions."""

from scopeproof_core.schemas.models import EvidenceLevel, HumanDecision


def acceptance_requires_comment(
    decision: HumanDecision,
    observed_level: EvidenceLevel,
    required_level: EvidenceLevel,
) -> bool:
    """Return whether a low-evidence acceptance needs attributable rationale."""

    return (
        decision is HumanDecision.ACCEPTED
        and observed_level.rank < required_level.rank
    )
