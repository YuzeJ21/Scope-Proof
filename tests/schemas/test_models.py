from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    CheckState,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    Finding,
    FindingStatus,
    IngestionState,
    Priority,
    PullRequestSnapshot,
    Review,
)
from scopeproof_core.version import __version__


def candidate_evidence_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "evidence_id": "EV-1",
        "criterion_id": "AC-01",
        "evidence_type": EvidenceType.IMPLEMENTATION,
        "evidence_level": EvidenceLevel.E1,
        "file_path": "src/export.py",
        "line_start": 2,
        "line_end": 4,
        "commit_sha": "head123",
        "permalink": "https://github.com/acme/repo/blob/head123/src/export.py#L2-L4",
        "excerpt": "def export_csv():",
        "matching_rule": "identifier",
        "relevance_reason": "Matched export_csv",
        "relevance_score": 0.9,
        "limitations": ["Candidate evidence does not prove runtime behavior"],
    }
    payload.update(overrides)
    return payload


def finding_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "criterion_id": "AC-01",
        "status": FindingStatus.MISSING,
        "reason": "No candidate evidence was found.",
        "missing_evidence": ["Required evidence level E1"],
        "contradictions": [],
        "recommended_action": "Add or identify candidate evidence.",
    }
    payload.update(overrides)
    return payload


def test_evidence_rejects_line_range_without_sha() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="EV-1",
            criterion_id="AC-01",
            evidence_type=EvidenceType.IMPLEMENTATION,
            evidence_level=EvidenceLevel.E1,
            file_path="src/export.py",
            line_start=2,
            line_end=4,
            commit_sha="",
            permalink="https://github.com/acme/repo/blob/sha/src/export.py#L2-L4",
            excerpt="def export_csv():",
            matching_rule="identifier",
            relevance_reason="Matched export_csv",
            relevance_score=0.9,
        )


def test_evidence_rejects_reversed_line_range() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="EV-1",
            criterion_id="AC-01",
            evidence_type=EvidenceType.IMPLEMENTATION,
            evidence_level=EvidenceLevel.E1,
            file_path="src/export.py",
            line_start=8,
            line_end=4,
            commit_sha="head123",
            permalink="https://github.com/acme/repo/blob/head123/src/export.py#L8-L4",
            excerpt="def export_csv():",
            matching_rule="identifier",
            relevance_reason="Matched export_csv",
            relevance_score=0.9,
        )


@pytest.mark.parametrize(
    "field",
    [
        "evidence_id",
        "criterion_id",
        "file_path",
        "commit_sha",
        "permalink",
        "excerpt",
        "matching_rule",
        "relevance_reason",
    ],
)
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_candidate_evidence_context_rejects_blank_required_text(
    field: str, blank: str
) -> None:
    with pytest.raises(ValidationError, match="must contain non-whitespace text"):
        EvidenceItem.model_validate(candidate_evidence_payload(**{field: blank}))


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_candidate_evidence_context_rejects_blank_limitation(blank: str) -> None:
    with pytest.raises(ValidationError, match="limitations must contain non-whitespace text"):
        EvidenceItem.model_validate(candidate_evidence_payload(limitations=[blank]))


def test_candidate_evidence_context_preserves_valid_text_exactly() -> None:
    item = EvidenceItem.model_validate(
        candidate_evidence_payload(
            excerpt="  def export_csv():  ",
            relevance_reason="  Matched export_csv  ",
            limitations=["  Requires reviewer confirmation  "],
        )
    )

    assert item.excerpt == "  def export_csv():  "
    assert item.relevance_reason == "  Matched export_csv  "
    assert item.limitations == ["  Requires reviewer confirmation  "]


def test_candidate_evidence_context_allows_no_limitations() -> None:
    item = EvidenceItem.model_validate(candidate_evidence_payload(limitations=[]))

    assert item.limitations == []


@pytest.mark.parametrize("field", ["reason", "recommended_action"])
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_finding_context_rejects_blank_required_text(field: str, blank: str) -> None:
    with pytest.raises(ValidationError, match="must contain non-whitespace text"):
        Finding.model_validate(finding_payload(**{field: blank}))


@pytest.mark.parametrize("field", ["missing_evidence", "contradictions"])
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_finding_context_rejects_blank_list_member(field: str, blank: str) -> None:
    with pytest.raises(
        ValidationError, match="finding context must contain non-whitespace text"
    ):
        Finding.model_validate(finding_payload(**{field: [blank]}))


def test_finding_context_preserves_valid_text_exactly() -> None:
    finding = Finding.model_validate(
        finding_payload(
            reason="  No candidate evidence was found.  ",
            recommended_action="  Add candidate evidence.  ",
            missing_evidence=["  Required evidence level E1  "],
            contradictions=["  Conflicting implementation  "],
        )
    )

    assert finding.reason == "  No candidate evidence was found.  "
    assert finding.recommended_action == "  Add candidate evidence.  "
    assert finding.missing_evidence == ["  Required evidence level E1  "]
    assert finding.contradictions == ["  Conflicting implementation  "]


def test_finding_context_allows_empty_optional_lists() -> None:
    finding = Finding.model_validate(finding_payload(missing_evidence=[], contradictions=[]))

    assert finding.missing_evidence == []
    assert finding.contradictions == []


def test_review_requires_confirmed_criteria_before_analysis() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
    )
    assert review.criteria_confirmed is False
    assert review.can_analyze is False


def test_confirmed_complete_review_can_analyze() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        criteria_confirmed=True,
        ingestion_state=IngestionState.COMPLETE,
    )
    assert review.can_analyze is True


def test_review_preserves_ingestion_limitations_with_backward_compatible_defaults() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        ingestion_state=IngestionState.PARTIAL,
        ingestion_warnings=["File limit reached; skipped 2 changed files."],
        skipped_files=["src/one.py", "src/two.py"],
    )

    reopened = Review.model_validate_json(review.model_dump_json())
    historical = Review.model_validate(
        {
            "repository": "acme/repo",
            "pr_number": 7,
            "base_sha": "base",
            "head_sha": "head",
        }
    )

    assert reopened.ingestion_warnings == ["File limit reached; skipped 2 changed files."]
    assert reopened.skipped_files == ["src/one.py", "src/two.py"]
    assert historical.ingestion_warnings == []
    assert historical.skipped_files == []


def test_new_review_records_current_package_version() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
    )

    assert review.tool_version == __version__


def test_review_round_trip_preserves_historical_tool_version() -> None:
    historical = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        tool_version="0.1.0",
    )

    reopened = Review.model_validate_json(historical.model_dump_json())
    assert reopened.tool_version == "0.1.0"


def test_snapshot_round_trip_preserves_changed_lines() -> None:
    snapshot = PullRequestSnapshot(
        repository="acme/repo",
        pr_number=7,
        title="Export CSV",
        description="Adds CSV export",
        html_url="https://github.com/acme/repo/pull/7",
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        fetched_at=datetime.now(UTC),
        files=[],
    )
    assert PullRequestSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot


def test_criterion_defaults_to_must_have_e1() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    assert criterion.priority is Priority.MUST_HAVE
    assert criterion.required_evidence_level is EvidenceLevel.E1


@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_criterion_rejects_blank_normalized_text(text: str) -> None:
    with pytest.raises(ValidationError):
        Criterion(criterion_id="AC-01", text=text)


def test_criterion_normalizes_nonblank_text_before_validation() -> None:
    criterion = Criterion(criterion_id="AC-01", text="  Export CSV  ")

    assert criterion.text == "Export CSV"
