from itertools import combinations

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


RUNTIME_IDENTITY = {
    "runtime_evidence_id": "runtime-001",
    "repository": "octocat/Hello-World",
    "pr_number": 42,
    "head_sha": "a" * 40,
}


def test_runtime_evidence_accepts_complete_runtime_identity() -> None:
    evidence = RuntimeEvidence(**runtime_evidence_payload(), **RUNTIME_IDENTITY)

    assert evidence.runtime_evidence_id == "runtime-001"
    assert evidence.repository == "octocat/Hello-World"
    assert evidence.pr_number == 42
    assert evidence.head_sha == "a" * 40


@pytest.mark.parametrize(
    "present_fields",
    [
        present_fields
        for field_count in range(1, len(RUNTIME_IDENTITY))
        for present_fields in combinations(RUNTIME_IDENTITY, field_count)
    ],
)
def test_runtime_evidence_rejects_partial_runtime_identity(
    present_fields: tuple[str, ...],
) -> None:
    partial_identity = {
        field_name: RUNTIME_IDENTITY[field_name] for field_name in present_fields
    }

    with pytest.raises(ValueError, match="all be present or all be absent"):
        RuntimeEvidence(**runtime_evidence_payload(), **partial_identity)


@pytest.mark.parametrize("field_name", ["runtime_evidence_id", "head_sha"])
def test_runtime_evidence_rejects_blank_runtime_identity_text(field_name: str) -> None:
    identity = {**RUNTIME_IDENTITY, field_name: " \t\n "}

    with pytest.raises(ValueError, match="must contain non-whitespace text"):
        RuntimeEvidence(**runtime_evidence_payload(), **identity)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("repository", "not-a-repository"),
        ("pr_number", 0),
    ],
)
def test_runtime_evidence_reuses_review_identity_validation(
    field_name: str, invalid_value: object
) -> None:
    identity = {**RUNTIME_IDENTITY, field_name: invalid_value}

    with pytest.raises(ValueError):
        RuntimeEvidence(**runtime_evidence_payload(), **identity)


@pytest.mark.parametrize("field_name", ["runtime_evidence_id", "head_sha"])
def test_runtime_evidence_preserves_nonblank_runtime_identity_text(
    field_name: str,
) -> None:
    identity = {**RUNTIME_IDENTITY, field_name: "  retained identity  "}

    evidence = RuntimeEvidence(**runtime_evidence_payload(), **identity)

    assert getattr(evidence, field_name) == "  retained identity  "


def test_runtime_evidence_accepts_absent_identity_as_legacy_unscoped_data() -> None:
    evidence = RuntimeEvidence(**runtime_evidence_payload())

    assert evidence.runtime_evidence_id is None
    assert evidence.repository is None
    assert evidence.pr_number is None
    assert evidence.head_sha is None


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


def test_runtime_evidence_rejects_whitespace_only_limitation() -> None:
    payload = runtime_evidence_payload()
    payload["limitations"] = ["Manual observation only", " \t\n "]

    with pytest.raises(ValueError, match="limitations must contain non-whitespace text"):
        RuntimeEvidence(**payload)


def test_runtime_evidence_preserves_nonblank_limitation_exactly() -> None:
    payload = runtime_evidence_payload()
    payload["limitations"] = ["  retained limitation text  "]

    evidence = RuntimeEvidence(**payload)

    assert evidence.limitations == ["  retained limitation text  "]


def test_runtime_evidence_accepts_empty_limitations() -> None:
    payload = runtime_evidence_payload()
    payload["limitations"] = []

    evidence = RuntimeEvidence(**payload)

    assert evidence.limitations == []
