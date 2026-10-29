"""Deliberately constructed inputs for candidate-selection completeness tests."""

from datetime import UTC, datetime

from scopeproof_core.demo import build_review
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    CIObservation,
    CIReasonCode,
    Criterion,
    EvidenceLevel,
    LineChangeType,
    PullRequestSnapshot,
    RepositoryVisibility,
    ReviewBundle,
)


def selection_snapshot(line_count: int = 12) -> PullRequestSnapshot:
    """Return a constructed public-PR-shaped snapshot, never a live observation."""
    return PullRequestSnapshot(
        repository="acme/widget",
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        pr_number=7,
        title="Constructed CSV export candidate-selection example",
        description="Constructed test input, not evidence of an observed public PR.",
        html_url="https://github.com/acme/widget/pull/7",
        base_sha="b" * 40,
        head_sha="a" * 40,
        check_state=CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.PASSING,
            reason="Constructed successful check metadata; no runtime verification.",
            reason_code=CIReasonCode.SUCCESSFUL_CHECK_RUNS,
            total_check_runs=1,
            successful_check_runs=1,
        ),
        fetched_at=datetime(2026, 10, 29, 12, tzinfo=UTC),
        files=[
            ChangedFile(
                path="src/export.py",
                status="added",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED,
                        line_number=number,
                        content=f"export_csv(row_{number})",
                    )
                    for number in range(1, line_count + 1)
                ],
            )
        ],
    )


def selection_criteria() -> list[Criterion]:
    return [
        Criterion(
            criterion_id="AC-01",
            text="Export CSV",
            required_evidence_level=EvidenceLevel.E1,
        )
    ]


def selection_bundle(line_count: int = 12) -> ReviewBundle:
    """Use the production analysis path with explicitly constructed confirmation."""
    return build_review(
        selection_snapshot(line_count),
        {
            "fixture": "constructed-candidate-selection",
            "deliberately_constructed_demo": True,
            "source_text": "Export CSV",
            "criteria": [item.model_dump(mode="json") for item in selection_criteria()],
            "criteria_confirmed": True,
            "resolutions": [],
        },
    )
