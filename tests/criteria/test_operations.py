import pytest

from scopeproof_core.criteria.service import (
    add_criterion,
    remove_criterion,
    reorder_criteria,
    split_criterion,
)
from scopeproof_core.schemas.models import Criterion


def criteria() -> list[Criterion]:
    return [
        Criterion(criterion_id="AC-01", text="Export CSV"),
        Criterion(criterion_id="AC-03", text="Record analytics"),
    ]


def test_add_criterion_uses_next_stable_identifier_without_renumbering_existing() -> None:
    updated = add_criterion(criteria(), "Show an error")
    assert [item.criterion_id for item in updated] == ["AC-01", "AC-03", "AC-04"]
    assert updated[-1].text == "Show an error"


def test_remove_criterion_preserves_other_stable_identifiers() -> None:
    assert [item.criterion_id for item in remove_criterion(criteria(), "AC-01")] == ["AC-03"]


def test_split_replaces_one_criterion_with_two_new_stable_items() -> None:
    updated = split_criterion(
        [Criterion(criterion_id="AC-01", text="Export CSV and record analytics")],
        "AC-01",
        ["Export CSV", "Record analytics"],
    )
    assert [(item.criterion_id, item.text) for item in updated] == [
        ("AC-01", "Export CSV"),
        ("AC-02", "Record analytics"),
    ]


def test_reorder_requires_each_existing_identifier_exactly_once() -> None:
    updated = reorder_criteria(criteria(), ["AC-03", "AC-01"])
    assert [item.criterion_id for item in updated] == ["AC-03", "AC-01"]
    with pytest.raises(ValueError):
        reorder_criteria(criteria(), ["AC-01"])
