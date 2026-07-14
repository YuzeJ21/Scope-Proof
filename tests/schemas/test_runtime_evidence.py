import pytest

from scopeproof_core.schemas.models import EvidenceLevel, RuntimeEvidence

REQUIRED_RUNTIME_TEXT_FIELDS = [
    "artifact_reference",
    "scenario",
    "environment",
    "result",
    "reviewer",
]


def runtime_evidence_payload() -> dict:
    return {
        "criterion_id": "AC-01",
        "artifact_reference": "https://example.test/run/42",
        "scenario": "Export CSV with an active filter",
        "environment": "staging",
        "result": "passed",
        "reviewer": "A reviewer",
        "evidence_level": EvidenceLevel.E3,
    }


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


@pytest.mark.parametrize("field_name", REQUIRED_RUNTIME_TEXT_FIELDS)
def test_runtime_evidence_rejects_whitespace_only_required_text(field_name: str) -> None:
    payload = runtime_evidence_payload()
    payload[field_name] = " \t\n "

    with pytest.raises(ValueError, match="must contain non-whitespace text"):
        RuntimeEvidence(**payload)


@pytest.mark.parametrize("field_name", REQUIRED_RUNTIME_TEXT_FIELDS)
def test_runtime_evidence_preserves_nonblank_text_exactly(field_name: str) -> None:
    payload = runtime_evidence_payload()
    payload[field_name] = "  retained evidence text  "

    evidence = RuntimeEvidence(**payload)

    assert getattr(evidence, field_name) == "  retained evidence text  "
