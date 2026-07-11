"""Explicit opt-in local Definition-of-Done criterion packs."""

from __future__ import annotations

from pydantic import BaseModel

from scopeproof_core.schemas.models import Criterion, CriterionSource, CriterionType, Priority


class RulePack(BaseModel):
    """A local heuristic pack that never becomes a user source requirement by default."""

    name: str
    display_name: str
    criteria: list[Criterion]


def _criterion(
    criterion_id: str, text: str, criterion_type: CriterionType = CriterionType.BEHAVIOR
) -> Criterion:
    return Criterion(
        criterion_id=criterion_id,
        text=f"Implicit local rule — {text}",
        priority=Priority.SHOULD_HAVE,
        criterion_type=criterion_type,
        criterion_source=CriterionSource.IMPLICIT_RULE_PACK,
    )


_RULE_PACKS = [
    RulePack(
        name="error-state",
        display_name="Error state",
        criteria=[
            _criterion("AC-87", "provide a user-visible error state", CriterionType.ERROR_STATE)
        ],
    ),
    RulePack(
        name="loading-state",
        display_name="Loading state",
        criteria=[
            _criterion(
                "AC-88", "provide a user-visible loading state", CriterionType.NON_FUNCTIONAL
            )
        ],
    ),
    RulePack(
        name="empty-state",
        display_name="Empty state",
        criteria=[
            _criterion("AC-89", "provide a user-visible empty state", CriterionType.ERROR_STATE)
        ],
    ),
    RulePack(
        name="analytics",
        display_name="Analytics",
        criteria=[
            _criterion("AC-90", "emit the relevant analytics event", CriterionType.ANALYTICS)
        ],
    ),
    RulePack(
        name="authorization",
        display_name="Authorization",
        criteria=[
            _criterion(
                "AC-91",
                "enforce authorization for the changed capability",
                CriterionType.PERMISSION,
            )
        ],
    ),
    RulePack(
        name="api-documentation",
        display_name="API documentation",
        criteria=[
            _criterion("AC-92", "document the changed public API", CriterionType.DOCUMENTATION)
        ],
    ),
    RulePack(
        name="migrations",
        display_name="Migrations",
        criteria=[_criterion("AC-93", "include an appropriate migration", CriterionType.MIGRATION)],
    ),
]


def available_rule_packs() -> list[RulePack]:
    """Return validated copies of all locally available packs in display order."""

    return [pack.model_copy(deep=True) for pack in _RULE_PACKS]


def criteria_from_rule_packs(names: list[str]) -> list[Criterion]:
    """Return only explicitly requested packs, refusing unknown pack names."""

    packs_by_name = {pack.name: pack for pack in _RULE_PACKS}
    unknown = sorted(set(names) - set(packs_by_name))
    if unknown:
        raise ValueError(f"Unknown rule pack: {', '.join(unknown)}")
    criteria: list[Criterion] = []
    for name in names:
        pack_criteria = packs_by_name[name].criteria
        criteria.extend(criterion.model_copy(deep=True) for criterion in pack_criteria)
    return criteria
