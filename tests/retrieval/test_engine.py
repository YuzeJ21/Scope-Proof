import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import scopeproof_core.retrieval.engine as retrieval_engine
from scopeproof_core.retrieval.engine import (
    _evidence_type,
    classify_changed_path_evidence_type,
    retrieve_evidence,
)
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    Criterion,
    EvidenceType,
    LineChangeType,
    PullRequestSnapshot,
    RetrievedFile,
)


def r001_structural_snapshot() -> PullRequestSnapshot:
    payload = json.loads(
        (Path(__file__).parents[1] / "fixtures" / "r001_structural_pr.json").read_text(
            encoding="utf-8"
        )
    )
    return PullRequestSnapshot.model_validate(payload)


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


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/test_widget.py", EvidenceType.TEST),
        ("DOCS/guide.txt", EvidenceType.DOCUMENTATION),
        ("src/alembic/versions/v1.py", EvidenceType.CONTRACT),
        ("src/widget.py", EvidenceType.IMPLEMENTATION),
        ("src/evaluations/widget.py", EvidenceType.IMPLEMENTATION),
    ],
)
def test_public_path_classifier_preserves_existing_file_classifier(
    path: str, expected: EvidenceType
) -> None:
    file = ChangedFile(path=path, status="modified")

    assert classify_changed_path_evidence_type(path) is expected
    assert _evidence_type(file) is expected


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


def test_path_segment_classification_is_casefolded_but_not_substring_matched() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "EVALS/export_result.yaml",
                [(LineChangeType.ADDED, 3, "scenario: export evidence result")],
            ),
            changed_file(
                "DOCS/export_result.txt",
                [(LineChangeType.ADDED, 4, "Export evidence result guidance")],
            ),
            changed_file(
                "evaluations/export_result.yaml",
                [(LineChangeType.ADDED, 5, "scenario: export evidence result")],
            ),
        ]
    )
    criterion = Criterion(criterion_id="AC-99", text="Export evidence result")

    evidence = retrieve_evidence(snapshot, [criterion])

    by_path = {item.file_path: item for item in evidence}
    assert by_path["EVALS/export_result.yaml"].evidence_type is EvidenceType.TEST
    assert by_path["EVALS/export_result.yaml"].evidence_level.value == "E2"
    assert (
        "Candidate test/eval definition shows test intent, not execution"
        in by_path["EVALS/export_result.yaml"].limitations
    )
    assert by_path["DOCS/export_result.txt"].evidence_type is EvidenceType.DOCUMENTATION
    assert by_path["evaluations/export_result.yaml"].evidence_type is EvidenceType.IMPLEMENTATION


@pytest.mark.parametrize("segment", ["test", "tests", "eval", "evals"])
def test_exact_test_and_eval_path_segments_are_e2_candidates(segment: str) -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                f"source/{segment}/export_result.yaml",
                [(LineChangeType.ADDED, 3, "scenario: export evidence result")],
            )
        ]
    )

    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-99", text="Export evidence result")]
    )

    assert evidence[0].evidence_type is EvidenceType.TEST
    assert evidence[0].evidence_level.value == "E2"


@pytest.mark.parametrize("segment", ["contest", "evaluations"])
def test_nonexact_test_and_eval_path_segments_remain_non_test_candidates(segment: str) -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                f"source/{segment}/export_result.yaml",
                [(LineChangeType.ADDED, 3, "scenario: export evidence result")],
            )
        ]
    )

    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-99", text="Export evidence result")]
    )

    assert evidence[0].evidence_type is EvidenceType.IMPLEMENTATION
    assert evidence[0].evidence_level.value == "E1"


def test_r001_structural_matches_diversify_relevant_static_evidence() -> None:
    snapshot = r001_structural_snapshot()
    criterion = Criterion(criterion_id="AC-99", text="Export evidence result")

    evidence = retrieve_evidence(snapshot, [criterion])

    assert len(evidence) == 8
    assert [(item.evidence_type, item.file_path, item.line_start) for item in evidence[:3]] == [
        (EvidenceType.DOCUMENTATION, "docs/INSTRUCTIONS.md", 1),
        (EvidenceType.TEST, "evals/export_result.yaml", 4),
        (EvidenceType.IMPLEMENTATION, "src/export.py", 42),
    ]
    assert evidence[1].evidence_level.value == "E2"
    assert (
        "Candidate test/eval definition shows test intent, not execution"
        in evidence[1].limitations
    )
    assert all(
        item.evidence_type not in {EvidenceType.CI, EvidenceType.RUNTIME} for item in evidence
    )
    assert all(item.commit_sha == snapshot.head_sha for item in evidence)
    assert all(f"/blob/{snapshot.head_sha}/" in item.permalink for item in evidence)


def test_r001_structural_diversity_order_is_stable_and_does_not_force_noise() -> None:
    snapshot = r001_structural_snapshot()
    criterion = Criterion(criterion_id="AC-99", text="Export evidence result")

    first = retrieve_evidence(snapshot, [criterion])
    second = retrieve_evidence(snapshot, [criterion])

    assert [item.evidence_id for item in first] == [item.evidence_id for item in second]
    assert [item.permalink for item in first] == [item.permalink for item in second]
    assert all(item.file_path != "notes/unrelated.txt" for item in first)


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


def test_retrieval_adds_one_inspectable_neighbor_on_each_side() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/export.py",
                [
                    (LineChangeType.CONTEXT, 40, "def prepare_rows():"),
                    (LineChangeType.ADDED, 41, "    filtered_rows = active_rows()"),
                    (LineChangeType.ADDED, 42, "    return export_csv(filtered_rows)"),
                    (LineChangeType.CONTEXT, 43, "def unrelated_footer():"),
                ],
            )
        ]
    )

    evidence = retrieve_evidence(
        snapshot, [Criterion(criterion_id="AC-01", text="Export CSV filtered rows")]
    )

    matched = next(item for item in evidence if item.line_start == 42)
    assert matched.excerpt == "return export_csv(filtered_rows)"
    assert matched.context_excerpt == (
        "    filtered_rows = active_rows()\n"
        "    return export_csv(filtered_rows)\n"
        "def unrelated_footer():"
    )
    assert matched.line_start == matched.line_end == 42


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


def test_retrieval_result_reports_candidate_search_scope_without_changing_evidence() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/export.py",
                [(LineChangeType.ADDED, 42, "def export_csv(rows):")],
            )
        ]
    )
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")

    result = retrieval_engine.retrieve_evidence_with_diagnostics(snapshot, [criterion])

    assert result.evidence == retrieve_evidence(snapshot, [criterion])
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.criterion_id == "AC-01"
    assert diagnostic.outcome.value == "candidates_found"
    assert diagnostic.searched_terms == ["csv", "export"]
    assert diagnostic.exact_identifiers == []
    assert diagnostic.searched_paths == ["src/export.py"]
    assert diagnostic.searched_evidence_types == [EvidenceType.IMPLEMENTATION]
    assert diagnostic.changed_file_count == 1
    assert diagnostic.unchanged_candidate_file_count == 0
    assert diagnostic.inspectable_line_count == 1
    assert diagnostic.exact_identifier_match_line_count == 0
    assert diagnostic.term_overlap_line_count == 1
    assert diagnostic.below_threshold_line_count == 0
    assert diagnostic.accepted_candidate_count == 1


def test_retrieval_result_reports_no_searchable_terms_for_each_criterion() -> None:
    snapshot = snapshot_with_files([])
    criterion = Criterion(criterion_id="AC-01", text="The user should be on the current")

    result = retrieval_engine.retrieve_evidence_with_diagnostics(snapshot, [criterion])

    assert result.evidence == []
    assert result.diagnostics[0].outcome.value == "no_searchable_terms"
    assert result.diagnostics[0].searched_terms == []
    assert result.diagnostics[0].inspectable_line_count == 0


def test_retrieval_result_reports_no_inspectable_lines() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/export.py",
                [(LineChangeType.REMOVED, 42, "def export_csv(rows):")],
            )
        ]
    )

    result = retrieval_engine.retrieve_evidence_with_diagnostics(
        snapshot,
        [Criterion(criterion_id="AC-01", text="Export CSV")],
    )

    assert result.evidence == []
    assert result.diagnostics[0].outcome.value == "no_inspectable_lines"
    assert result.diagnostics[0].searched_paths == ["src/export.py"]
    assert result.diagnostics[0].inspectable_line_count == 0


def test_retrieval_result_reports_missing_exact_identifier_before_overlap() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/analytics.py",
                [(LineChangeType.ADDED, 5, 'track("record_export_event")')],
            )
        ]
    )

    result = retrieval_engine.retrieve_evidence_with_diagnostics(
        snapshot,
        [Criterion(criterion_id="AC-01", text="Record research_exported")],
    )

    diagnostic = result.diagnostics[0]
    assert result.evidence == []
    assert diagnostic.outcome.value == "exact_identifier_not_found"
    assert diagnostic.exact_identifiers == ["research_exported"]
    assert diagnostic.exact_identifier_match_line_count == 0
    assert diagnostic.term_overlap_line_count == 1
    assert diagnostic.below_threshold_line_count == 0


def test_retrieval_result_reports_no_term_overlap() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/unrelated.py",
                [(LineChangeType.ADDED, 5, "def render_dashboard():")],
            )
        ]
    )

    result = retrieval_engine.retrieve_evidence_with_diagnostics(
        snapshot,
        [Criterion(criterion_id="AC-01", text="Export CSV")],
    )

    diagnostic = result.diagnostics[0]
    assert result.evidence == []
    assert diagnostic.outcome.value == "no_term_overlap"
    assert diagnostic.term_overlap_line_count == 0
    assert diagnostic.below_threshold_line_count == 0


def test_retrieval_result_reports_lines_below_existing_threshold() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "src/export.py",
                [(LineChangeType.ADDED, 5, "export = True")],
            )
        ]
    )

    result = retrieval_engine.retrieve_evidence_with_diagnostics(
        snapshot,
        [
            Criterion(
                criterion_id="AC-01",
                text="Export archive report dashboard widget safely",
            )
        ],
    )

    diagnostic = result.diagnostics[0]
    assert result.evidence == []
    assert diagnostic.outcome.value == "below_relevance_threshold"
    assert diagnostic.term_overlap_line_count == 1
    assert diagnostic.below_threshold_line_count == 1


def test_retrieval_result_sorts_changed_and_unchanged_search_scope() -> None:
    snapshot = snapshot_with_files(
        [
            changed_file(
                "tests/test_export.py",
                [(LineChangeType.ADDED, 3, "def test_export_csv():")],
            ),
            changed_file(
                "src/export.py",
                [(LineChangeType.ADDED, 42, "def export_csv(rows):")],
            ),
        ]
    )
    unchanged = RetrievedFile(
        path="docs/export.md",
        content="Export CSV guidance",
        commit_sha=snapshot.head_sha,
        retrieval_reason="Requirement names this document",
    )

    result = retrieval_engine.retrieve_evidence_with_diagnostics(
        snapshot,
        [Criterion(criterion_id="AC-01", text="Export CSV")],
        unchanged_files=[unchanged],
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.searched_paths == [
        "docs/export.md",
        "src/export.py",
        "tests/test_export.py",
    ]
    assert diagnostic.searched_evidence_types == [
        EvidenceType.DOCUMENTATION,
        EvidenceType.IMPLEMENTATION,
        EvidenceType.TEST,
    ]
    assert diagnostic.changed_file_count == 2
    assert diagnostic.unchanged_candidate_file_count == 1
    assert diagnostic.inspectable_line_count == 3
    assert diagnostic.term_overlap_line_count == 3
    assert diagnostic.accepted_candidate_count == 3
