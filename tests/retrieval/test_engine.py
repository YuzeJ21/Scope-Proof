from datetime import UTC, datetime

from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    Criterion,
    EvidenceType,
    LineChangeType,
    PullRequestSnapshot,
)


def snapshot_with_files(files: list[ChangedFile]) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        repository="acme/widget",
        pr_number=7,
        title="Export CSV",
        description="Adds export",
        html_url="https://github.com/acme/widget/pull/7",
        base_sha="base123",
        head_sha="head123",
        check_state=CheckState.PASSING,
        fetched_at=datetime.now(UTC),
        files=files,
    )


def changed_file(path: str, lines: list[tuple[LineChangeType, int, str]]) -> ChangedFile:
    return ChangedFile(
        path=path,
        status="modified",
        lines=[
            ChangedLine(change_type=kind, line_number=number, content=content)
            for kind, number, content in lines
        ],
    )


def test_retrieval_links_identifier_and_excludes_deleted_lines() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/analytics.py",
                [
                    (LineChangeType.REMOVED, 4, 'track("research_exported_old")'),
                    (LineChangeType.ADDED, 5, 'track("research_exported")'),
                ],
            )
        ]
    )
    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-01", text="Record research_exported")]
    )
    assert [item.excerpt for item in evidence] == ['track("research_exported")']
    assert all(item.commit_sha == "head123" for item in evidence)
    assert evidence[0].matching_rule == "exact_identifier"


def test_test_filename_alone_does_not_create_test_evidence() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "tests/test_export.py",
                [(LineChangeType.ADDED, 3, "def test_unrelated_dashboard_title():")],
            )
        ]
    )
    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-01", text="Failed export shows an error")]
    )
    assert not any(item.evidence_type is EvidenceType.TEST for item in evidence)


def test_matching_test_line_is_e2_candidate_evidence() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "tests/test_export.py",
                [(LineChangeType.ADDED, 3, "def test_export_csv_download():")],
            )
        ]
    )
    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-01", text="User can export CSV")]
    )
    assert evidence[0].evidence_type is EvidenceType.TEST
    assert evidence[0].evidence_level.value == "E2"
    assert "Candidate test evidence requires reviewer confirmation" in evidence[0].limitations


def test_evidence_permalink_is_anchored_to_head_sha_and_lines() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/export.py",
                [(LineChangeType.ADDED, 42, "def export_csv(rows):")],
            )
        ]
    )
    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-01", text="Export CSV")]
    )
    assert evidence[0].permalink == (
        "https://github.com/acme/widget/blob/head123/src/export.py#L42-L42"
    )


def test_evidence_permalink_encodes_repository_controlled_path_characters() -> None:
    snapshot = snapshot_with_files(
        [
            ChangedFile(
                path="src/export #unsafe>.py",
                status="modified",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED,
                        line_number=42,
                        content="def export_csv(rows):",
                    )
                ],
            )
        ]
    )
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")

    evidence = retrieve_evidence(snapshot, [criterion])

    assert evidence[0].file_path == "src/export #unsafe>.py"
    assert evidence[0].permalink == (
        "https://github.com/acme/widget/blob/head123/src/export%20%23unsafe%3E.py#L42-L42"
    )


def test_ci_is_not_created_as_criterion_evidence() -> None:
    snapshot = snapshot_with_files([])
    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-01", text="Export CSV")]
    )
    assert evidence == []
