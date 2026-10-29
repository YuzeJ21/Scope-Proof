import pytest

from scopeproof_core.retrieval.engine import retrieve_evidence, retrieve_evidence_with_diagnostics
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    Criterion,
    EvidenceItem,
    LineChangeType,
    RetrievedFile,
)
from tests.candidate_selection_fixture import selection_criteria, selection_snapshot


@pytest.mark.parametrize(
    ("line_count", "accepted", "omitted"),
    [(0, 0, 0), (1, 1, 0), (7, 7, 0), (8, 8, 0), (9, 8, 1), (12, 8, 4)],
)
def test_selection_completeness_counts_eligible_matches_before_the_cap(
    line_count: int, accepted: int, omitted: int
) -> None:
    snapshot = selection_snapshot(line_count)

    result = retrieve_evidence_with_diagnostics(snapshot, selection_criteria())

    diagnostic = result.diagnostics[0]
    assert diagnostic.inspectable_line_count == line_count
    assert diagnostic.term_overlap_line_count == line_count
    assert diagnostic.accepted_candidate_count == accepted
    assert diagnostic.eligible_candidate_count == line_count
    assert diagnostic.candidate_limit == 8
    assert diagnostic.omitted_candidate_count == omitted
    assert [item.line_start for item in result.evidence] == list(range(1, accepted + 1))
    assert [item.evidence_id for item in result.evidence] == [
        f"EV-AC-01-{number:02d}" for number in range(1, accepted + 1)
    ]
    assert all(item.relevance_score == 1.0 for item in result.evidence)
    assert diagnostic.outcome.value == ("candidates_found" if accepted else "no_inspectable_lines")


def test_identifier_rejected_term_overlap_is_not_an_eligible_candidate() -> None:
    snapshot = selection_snapshot(0)
    snapshot.files[0].lines = [
        ChangedLine(
            change_type=LineChangeType.ADDED,
            line_number=1,
            content='track("record_export_event")',
        )
    ]

    result = retrieve_evidence_with_diagnostics(
        snapshot, [Criterion(criterion_id="AC-01", text="Record research_exported")]
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.inspectable_line_count == 1
    assert diagnostic.term_overlap_line_count == 1
    assert diagnostic.exact_identifier_match_line_count == 0
    assert diagnostic.below_threshold_line_count == 0
    assert diagnostic.eligible_candidate_count == 0
    assert diagnostic.accepted_candidate_count == 0
    assert diagnostic.omitted_candidate_count == 0
    assert diagnostic.candidate_limit == 8
    assert diagnostic.outcome.value == "exact_identifier_not_found"
    assert result.evidence == []


def test_below_threshold_overlap_is_not_an_eligible_candidate() -> None:
    snapshot = selection_snapshot(0)
    snapshot.files[0].lines = [
        ChangedLine(change_type=LineChangeType.ADDED, line_number=1, content="export = True"),
        ChangedLine(change_type=LineChangeType.REMOVED, line_number=2, content="export_csv()"),
        ChangedLine(change_type=LineChangeType.ADDED, line_number=None, content="export_csv()"),
    ]

    result = retrieve_evidence_with_diagnostics(
        snapshot,
        [Criterion(criterion_id="AC-01", text="Export archive report dashboard widget safely")],
    )

    diagnostic = result.diagnostics[0]
    assert diagnostic.inspectable_line_count == 1
    assert diagnostic.term_overlap_line_count == 1
    assert diagnostic.below_threshold_line_count == 1
    assert diagnostic.eligible_candidate_count == 0
    assert diagnostic.accepted_candidate_count == 0
    assert diagnostic.omitted_candidate_count == 0
    assert diagnostic.outcome.value == "below_relevance_threshold"
    assert result.evidence == []


def test_mixed_types_and_unchanged_candidates_preserve_the_full_ordered_evidence_payload() -> None:
    snapshot = selection_snapshot(9)
    snapshot.files.extend(
        [
            ChangedFile(
                path="tests/test_export.py",
                status="added",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED,
                        line_number=20,
                        content="assert export_csv(rows)",
                    )
                ],
            ),
            ChangedFile(
                path="schema/export.json",
                status="added",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED,
                        line_number=30,
                        content='{"export": "CSV"}',
                    )
                ],
            ),
        ]
    )
    unchanged = [
        RetrievedFile(
            path="docs/export.md",
            content="Export guidance",
            commit_sha="a" * 40,
            retrieval_reason="Constructed bounded document candidate",
        )
    ]

    result = retrieve_evidence_with_diagnostics(
        snapshot, selection_criteria(), unchanged_files=unchanged
    )

    # Literal selection order: diversify types first, then fill from sorted matches.
    selected = [
        ("contract", "schema/export.json", 30, '{"export": "CSV"}', 1.0),
        ("implementation", "src/export.py", 1, "export_csv(row_1)", 1.0),
        ("test", "tests/test_export.py", 20, "assert export_csv(rows)", 1.0),
        ("documentation", "docs/export.md", 1, "Export guidance", 0.5),
        ("implementation", "src/export.py", 2, "export_csv(row_2)", 1.0),
        ("implementation", "src/export.py", 3, "export_csv(row_3)", 1.0),
        ("implementation", "src/export.py", 4, "export_csv(row_4)", 1.0),
        ("implementation", "src/export.py", 5, "export_csv(row_5)", 1.0),
    ]
    expected = []
    for index, (kind, path, line, excerpt, score) in enumerate(selected, start=1):
        scope = "unchanged_candidate" if path == "docs/export.md" else "changed_file"
        limitations = ["Candidate evidence does not prove the criterion is satisfied"]
        if scope == "unchanged_candidate":
            limitations.insert(0, "Evidence comes from a bounded unchanged candidate file")
        if kind == "test":
            limitations.extend(
                [
                    "Candidate test evidence requires reviewer confirmation",
                    "Candidate test/eval definition shows test intent, not execution",
                ]
            )
        context = excerpt
        if path == "src/export.py":
            context = "\n".join(
                f"export_csv(row_{number})" for number in range(max(1, line - 1), line + 2)
            )
        expected.append(
            EvidenceItem(
                evidence_id=f"EV-AC-01-{index:02d}",
                criterion_id="AC-01",
                evidence_type=kind,
                evidence_level="E2" if kind == "test" else "E1",
                source_scope=scope,
                file_path=path,
                line_start=line,
                line_end=line,
                commit_sha="a" * 40,
                permalink=(
                    f"https://github.com/acme/widget/blob/{'a' * 40}/{path}#L{line}-L{line}"
                ),
                excerpt=excerpt,
                context_excerpt=context,
                matching_rule="keyword_overlap",
                relevance_reason=(
                    "Matched terms: export" if score == 0.5 else "Matched terms: csv, export"
                ),
                relevance_score=score,
                limitations=limitations,
            )
        )
    assert [item.model_dump_json() for item in result.evidence] == [
        item.model_dump_json() for item in expected
    ]
    assert result.evidence == retrieve_evidence(
        snapshot, selection_criteria(), unchanged_files=unchanged
    )
    diagnostic = result.diagnostics[0]
    assert diagnostic.inspectable_line_count == 12
    assert diagnostic.eligible_candidate_count == 12
    assert diagnostic.accepted_candidate_count == 8
    assert diagnostic.candidate_limit == 8
    assert diagnostic.omitted_candidate_count == 4
    assert diagnostic.changed_file_count == 3
    assert diagnostic.unchanged_candidate_file_count == 1


def test_duplicate_matching_lines_preserve_existing_deduplication() -> None:
    snapshot = selection_snapshot(1)
    snapshot.files[0].lines.append(snapshot.files[0].lines[0].model_copy(deep=True))

    result = retrieve_evidence_with_diagnostics(snapshot, selection_criteria())

    assert [item.line_start for item in result.evidence] == [1]
    diagnostic = result.diagnostics[0]
    assert diagnostic.inspectable_line_count == 2
    assert diagnostic.eligible_candidate_count == 2
    assert diagnostic.accepted_candidate_count == 1
    assert diagnostic.candidate_limit == 8
    assert diagnostic.omitted_candidate_count == 1
