from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    CheckState,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    IngestionState,
    Priority,
    PullRequestSnapshot,
    Review,
)
from scopeproof_core.version import __version__


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
