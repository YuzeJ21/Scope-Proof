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


def _next_identifier(criteria: list[Criterion]) -> str:
    highest = max((int(item.criterion_id.removeprefix("AC-")) for item in criteria), default=0)
    return f"AC-{highest + 1:02d}"


def add_criterion(criteria: list[Criterion], text: str) -> list[Criterion]:
    """Append a user-authored criterion without renumbering existing audit IDs."""
    return [*criteria, Criterion(criterion_id=_next_identifier(criteria), text=text)]


def remove_criterion(criteria: list[Criterion], criterion_id: str) -> list[Criterion]:
    """Remove one criterion while preserving every other stable identifier."""
    updated = [item for item in criteria if item.criterion_id != criterion_id]
    if len(updated) == len(criteria):
        raise ValueError(f"Unknown criterion {criterion_id}")
    return updated


def split_criterion(
    criteria: list[Criterion], criterion_id: str, texts: list[str]
) -> list[Criterion]:
    """Keep the original ID for the first split and assign new IDs to later parts."""
    if len(texts) < 2 or any(not text.strip() for text in texts):
        raise ValueError("splitting requires at least two non-empty criterion texts")
    target_index = next(
        (index for index, item in enumerate(criteria) if item.criterion_id == criterion_id), None
    )
    if target_index is None:
        raise ValueError(f"Unknown criterion {criterion_id}")
    original = criteria[target_index]
    replacement = [original.model_copy(update={"text": texts[0].strip()})]
    working = [*criteria]
    for text in texts[1:]:
        identifier = _next_identifier(working + replacement)
        replacement.append(
            original.model_copy(update={"criterion_id": identifier, "text": text.strip()})
        )
    return [*criteria[:target_index], *replacement, *criteria[target_index + 1 :]]


def reorder_criteria(criteria: list[Criterion], ordered_ids: list[str]) -> list[Criterion]:
    """Apply an explicit complete order so accidental drops cannot be hidden."""
    existing = {item.criterion_id: item for item in criteria}
    if len(ordered_ids) != len(criteria) or set(ordered_ids) != set(existing):
        raise ValueError("ordered_ids must contain every criterion identifier exactly once")
    return [existing[criterion_id] for criterion_id in ordered_ids]
