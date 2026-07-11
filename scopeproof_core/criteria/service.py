"""Preserve user-authored criteria while surfacing structural warnings."""

import re

from scopeproof_core.schemas.models import Criterion, CriterionDraft, CriterionWarning

_LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_COMPOUND_MARKERS = re.compile(r"\b(?:and|以及|并且|同时)\b", re.IGNORECASE)


def parse_criteria(text: str) -> list[CriterionDraft]:
    """Treat each non-empty input line as one user-owned criterion."""
    prepared: list[str] = []
    for raw_line in text.splitlines():
        line = _LIST_MARKER.sub("", raw_line).strip()
        if line:
            prepared.append(line)
    return [
        CriterionDraft(criterion_id=f"AC-{index:02d}", text=line)
        for index, line in enumerate(prepared, start=1)
    ]


def validate_criteria(criteria: list[Criterion]) -> list[CriterionWarning]:
    """Return warnings without rewriting, splitting, or inventing requirements."""
    warnings: list[CriterionWarning] = []
    seen: dict[str, str] = {}
    for criterion in criteria:
        normalized = " ".join(criterion.text.casefold().split())
        if _COMPOUND_MARKERS.search(criterion.text):
            warnings.append(
                CriterionWarning(
                    criterion_id=criterion.criterion_id,
                    code="compound_criterion",
                    message="This may describe more than one independently judgeable behavior.",
                )
            )
        if normalized in seen:
            warnings.append(
                CriterionWarning(
                    criterion_id=criterion.criterion_id,
                    code="duplicate_criterion",
                    message=f"This duplicates {seen[normalized]} after whitespace normalization.",
                )
            )
        else:
            seen[normalized] = criterion.criterion_id
        if len(criterion.text) > 240:
            warnings.append(
                CriterionWarning(
                    criterion_id=criterion.criterion_id,
                    code="long_criterion",
                    message="Consider shortening this criterion while preserving its meaning.",
                )
            )
    return warnings
