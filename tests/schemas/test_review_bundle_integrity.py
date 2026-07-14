from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    CheckState,
    ConfidenceBand,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    Finding,
    FindingStatus,
    GateDecision,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
    Review,
    ReviewBundle,
    RuntimeEvidence,
)


def test_resolution_event_rejects_a_blank_event_id() -> None:
    with pytest.raises(ValidationError, match="event ID must contain non-whitespace text"):
        ResolutionEvent(event_id="   ", final_acceptance=False)


@pytest.mark.parametrize("reviewer", ["", "   ", "\t\n"])
def test_resolution_event_rejects_a_blank_reviewer(reviewer: str) -> None:
    with pytest.raises(ValidationError, match="reviewer must contain non-whitespace text"):
        ResolutionEvent(final_acceptance=False, reviewer=reviewer)


def valid_bundle() -> ReviewBundle:
    criterion = Criterion(criterion_id="AC-01", text="Failed export shows an error")
    evidence = EvidenceItem(
        evidence_id="EV-AC-01-01",
        criterion_id="AC-01",
        evidence_type=EvidenceType.IMPLEMENTATION,
        evidence_level=EvidenceLevel.E1,
        file_path="src/export.py",
        line_start=42,
        line_end=42,
        commit_sha="head123",
        permalink="https://github.com/acme/widget/blob/head123/src/export.py#L42",
        excerpt="def export_csv(rows):",
        matching_rule="keyword_overlap",
        relevance_reason="Matched export",
        relevance_score=0.5,
        limitations=["Candidate evidence does not prove runtime behavior"],
    )
    return ReviewBundle(
        review=Review(
            review_id="review-1",
            repository="acme/widget",
            pr_number=7,
            base_sha="base123",
            head_sha="head123",
            check_state=CheckState.PASSING,
            criteria_confirmed=True,
        ),
        source_text="Failed export shows an error",
        criteria=[criterion],
        evidence=[evidence],
        runtime_evidence=[
            RuntimeEvidence(
                criterion_id="AC-01",
                artifact_reference="https://example.test/runs/7",
                scenario="Failed export shows its error state",
                environment="staging",
                result="passed",
                reviewer="QA reviewer",
                evidence_level=EvidenceLevel.E3,
                timestamp=datetime(2026, 7, 14, tzinfo=UTC),
            )
        ],
        findings=[
            Finding(
                criterion_id="AC-01",
                status=FindingStatus.PARTIAL,
                evidence_level=EvidenceLevel.E1,
                confidence_band=ConfidenceBand.MEDIUM,
                reason="Only the export path was found.",
                evidence_ids=[evidence.evidence_id],
                missing_evidence=["Failure-path test"],
                recommended_action="Add a failure-path test.",
            )
        ],
        resolutions=[
            HumanResolution(
                criterion_id="AC-01",
                decision=HumanDecision.CHANGE_REQUIRED,
                comment="Must fix before merge",
            )
        ],
        gate=GateDecision(
            verdict=GateVerdict.BLOCKED,
            blocking_criteria=["AC-01"],
            reason_codes=["blocking_criteria"],
        ),
    )


def bundle_payload() -> dict[str, object]:
    return valid_bundle().model_dump(mode="python")


def test_review_bundle_integrity_allows_valid_json_round_trip() -> None:
    bundle = valid_bundle()

    assert ReviewBundle.model_validate_json(bundle.model_dump_json()) == bundle


@pytest.mark.parametrize("source_text", ["", "   ", "\t", "\n\r"])
def test_review_bundle_rejects_blank_requirements_source(source_text: str) -> None:
    payload = bundle_payload()
    payload["source_text"] = source_text

    with pytest.raises(
        ValidationError, match="requirements source must contain non-whitespace text"
    ):
        ReviewBundle.model_validate(payload)


def test_review_bundle_preserves_valid_requirements_source() -> None:
    source_text = "  Failed export shows an error\n"
    payload = bundle_payload()
    payload["source_text"] = source_text

    assert ReviewBundle.model_validate(payload).source_text == source_text


def test_review_bundle_integrity_rejects_duplicate_criterion_ids() -> None:
    payload = bundle_payload()
    payload["criteria"].append(payload["criteria"][0].copy())

    with pytest.raises(ValidationError, match="criterion IDs must be unique"):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_duplicate_evidence_ids() -> None:
    payload = bundle_payload()
    payload["evidence"].append(payload["evidence"][0].copy())

    with pytest.raises(ValidationError, match="evidence IDs must be unique"):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_evidence_for_unknown_criterion() -> None:
    payload = bundle_payload()
    payload["evidence"][0]["criterion_id"] = "AC-99"

    with pytest.raises(
        ValidationError, match="evidence criterion IDs must reference known criteria"
    ):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_duplicate_finding_ids() -> None:
    payload = bundle_payload()
    payload["findings"].append(payload["findings"][0].copy())

    with pytest.raises(ValidationError, match="finding criterion IDs must be unique"):
        ReviewBundle.model_validate(payload)


@pytest.mark.parametrize("findings", [[], [{"criterion_id": "AC-99"}]])
def test_review_bundle_integrity_requires_one_finding_per_criterion(
    findings: list[dict[str, str]],
) -> None:
    payload = bundle_payload()
    if findings:
        extra = payload["findings"][0].copy()
        extra.update(findings[0])
        payload["findings"].append(extra)
    else:
        payload["findings"] = []

    with pytest.raises(ValidationError, match="findings must match criteria exactly"):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_duplicate_finding_evidence_references() -> None:
    payload = bundle_payload()
    payload["findings"][0]["evidence_ids"] *= 2

    with pytest.raises(ValidationError, match="finding evidence references must be unique"):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_dangling_evidence_reference() -> None:
    payload = bundle_payload()
    payload["findings"][0]["evidence_ids"] = ["EV-MISSING"]

    with pytest.raises(ValidationError, match="finding evidence references must resolve"):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_cross_criterion_evidence_reference() -> None:
    payload = bundle_payload()
    payload["criteria"].append(
        Criterion(criterion_id="AC-02", text="Export succeeds").model_dump(mode="python")
    )
    payload["findings"].append(
        Finding(
            criterion_id="AC-02",
            status=FindingStatus.MISSING,
            reason="No candidate found.",
            missing_evidence=["Implementation evidence"],
            recommended_action="Add implementation evidence.",
        ).model_dump(mode="python")
    )
    payload["evidence"][0]["criterion_id"] = "AC-02"

    with pytest.raises(ValidationError, match="finding evidence must belong to the same criterion"):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_runtime_evidence_for_unknown_criterion() -> None:
    payload = bundle_payload()
    payload["runtime_evidence"][0]["criterion_id"] = "AC-99"

    with pytest.raises(
        ValidationError, match="runtime evidence criterion IDs must reference known criteria"
    ):
        ReviewBundle.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("repository", " / "),
        ("base_sha", "   "),
        ("head_sha", "\t"),
    ],
)
def test_review_bundle_integrity_rejects_invalid_review_identity(
    field_name: str, invalid_value: str
) -> None:
    payload = bundle_payload()
    payload["review"][field_name] = invalid_value

    with pytest.raises(ValidationError):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_duplicate_resolution_ids() -> None:
    payload = bundle_payload()
    payload["resolutions"].append(payload["resolutions"][0].copy())

    with pytest.raises(ValidationError, match="resolution criterion IDs must be unique"):
        ReviewBundle.model_validate(payload)


def test_review_bundle_integrity_rejects_resolution_for_unknown_criterion() -> None:
    payload = bundle_payload()
    payload["resolutions"][0]["criterion_id"] = "AC-99"

    with pytest.raises(
        ValidationError, match="resolution criterion IDs must reference known criteria"
    ):
        ReviewBundle.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "blocking_criteria",
        "conditional_criteria",
        "unresolved_criteria",
        "resolved_exceptions",
    ],
)
def test_review_bundle_integrity_rejects_duplicate_gate_references(field: str) -> None:
    payload = bundle_payload()
    payload["gate"][field] = ["AC-01", "AC-01"]

    with pytest.raises(ValidationError, match=f"{field} must contain unique criterion IDs"):
        ReviewBundle.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "blocking_criteria",
        "conditional_criteria",
        "unresolved_criteria",
        "resolved_exceptions",
    ],
)
def test_review_bundle_integrity_rejects_unknown_gate_references(field: str) -> None:
    payload = bundle_payload()
    payload["gate"][field] = ["AC-99"]

    with pytest.raises(ValidationError, match=f"{field} must reference known criteria"):
        ReviewBundle.model_validate(payload)
