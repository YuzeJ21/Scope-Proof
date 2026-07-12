import pytest

from scopeproof_core.schemas.models import EvidenceLevel, RuntimeEvidence


def test_manual_runtime_evidence_requires_complete_human_supplied_context() -> None:
    evidence = RuntimeEvidence(
        criterion_id="AC-01",
        artifact_reference="https://example.test/run/42",
        scenario="Export CSV with an active filter",
        environment="staging",
        result="passed",
        reviewer="A reviewer",
        evidence_level=EvidenceLevel.E3,
        limitations=["Manual observation only"],
    )

    assert evidence.evidence_level is EvidenceLevel.E3


def test_runtime_evidence_rejects_static_evidence_level() -> None:
    with pytest.raises(ValueError, match="E3 or E4"):
        RuntimeEvidence(
            criterion_id="AC-01",
            artifact_reference="artifact-42",
            scenario="Export CSV",
            environment="staging",
            result="passed",
            reviewer="A reviewer",
            evidence_level=EvidenceLevel.E1,
        )
