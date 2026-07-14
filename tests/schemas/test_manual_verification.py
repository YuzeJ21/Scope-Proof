import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
)


def manual_resolution(comment: str) -> HumanResolution:
    return HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment=comment,
        claimed_evidence_level=EvidenceLevel.E4,
    )


def manual_event(comment: str) -> ResolutionEvent:
    return ResolutionEvent(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment=comment,
        claimed_evidence_level=EvidenceLevel.E4,
    )


@pytest.mark.parametrize("factory", [manual_resolution, manual_event])
@pytest.mark.parametrize("comment", ["", "   ", "\t\n"])
def test_manual_verification_rejects_blank_reviewer_note(factory, comment: str) -> None:
    with pytest.raises(
        ValidationError,
        match="manually verified decisions require a reviewer note",
    ):
        factory(comment)


@pytest.mark.parametrize("factory", [manual_resolution, manual_event])
def test_manual_verification_preserves_nonblank_reviewer_note(factory) -> None:
    value = factory("  Verified in staging  ")

    assert value.comment == "  Verified in staging  "


@pytest.mark.parametrize("model", [HumanResolution, ResolutionEvent])
def test_other_human_decisions_keep_optional_reviewer_note(model) -> None:
    value = model(
        criterion_id="AC-01",
        decision=HumanDecision.ACCEPTED,
    )

    assert value.comment == ""
