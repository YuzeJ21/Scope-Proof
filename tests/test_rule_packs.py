import pytest

from scopeproof_core.rule_packs import available_rule_packs, criteria_from_rule_packs
from scopeproof_core.schemas.models import CriterionSource


def test_rule_pack_criteria_are_explicitly_implicit_and_stably_identified() -> None:
    criteria = criteria_from_rule_packs(["analytics"])

    assert criteria[0].criterion_id == "AC-90"
    assert criteria[0].criterion_source is CriterionSource.IMPLICIT_RULE_PACK
    assert criteria[0].text.startswith("Implicit local rule —")
    assert available_rule_packs()[3].name == "analytics"


def test_unknown_rule_pack_is_rejected_instead_of_silently_ignored() -> None:
    with pytest.raises(ValueError, match="Unknown rule pack"):
        criteria_from_rule_packs(["security"])
