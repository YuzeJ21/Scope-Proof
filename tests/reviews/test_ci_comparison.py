"""Compare supplied context without inventing chronology, execution or acceptance."""

import pytest

from scopeproof_core.reviews.ci_comparison import CIStatusComparison, compare_ci_status
from scopeproof_core.reviews.ci_status import CIStatusManifest, CIStatusRun
from tests.ci_comparison_fixture import ci_comparison_inputs


def comparison_inputs():
    state, previous, current, _, _ = ci_comparison_inputs()
    return state, previous, current


def _compare(bundle, previous, current):
    return compare_ci_status(
        bundle, (previous.model_dump_json(indent=2) + "\n").encode(),
        (current.model_dump_json(indent=2) + "\n").encode(),
    )


def test_targeted_context_changes_only_row_access_and_preserves_review():
    state, previous, current = comparison_inputs()
    before = state.model_dump(mode="python")
    comparison = _compare(state.bundle, previous, current)
    rows = {row.test_id: row for row in comparison.test_changes()}
    assert {key: row.change for key, row in rows.items()} == {
        "category_filter": "unchanged", "csv_header": "unchanged", "row_entitlement": "changed",
    }
    row = rows["row_entitlement"]
    assert row.previous.status == "skipped" and row.current.status == "failed"
    assert row.previous.run_ids == ("B",) and row.current.run_ids == ("B-targeted",)
    assert rows["category_filter"].current.run_ids == ("B",)
    assert rows["csv_header"].current.run_ids == ("B",)
    assert [(row.run_id, row.change) for row in comparison.run_changes()] == [
        ("A", "unchanged"), ("B", "unchanged"), ("B-targeted", "added"),
    ]
    assert state.model_dump(mode="python") == before
    assert comparison.bundle.gate.verdict.value == "blocked"
    assert not comparison.bundle.review.final_acceptance


def test_identical_context_has_no_changes_and_round_trips_through_pydantic():
    state, previous, _ = comparison_inputs()
    comparison = _compare(state.bundle, previous, previous)
    assert all(row.change == "unchanged" for row in comparison.test_changes())
    assert all(row.change == "unchanged" for row in comparison.run_changes())
    restored = CIStatusComparison.model_validate_json(comparison.model_dump_json())
    assert restored == comparison


@pytest.mark.parametrize("side", ["previous", "current"])
@pytest.mark.parametrize("field", ["repository", "pr_number", "criteria_sha256", "head_sha"])
def test_each_manifest_must_match_the_same_exact_confirmed_review(side, field):
    state, previous, current = comparison_inputs()
    data = (previous if side == "previous" else current).model_dump(mode="python")
    if field == "head_sha":
        for run in data["runs"]:
            run["head_sha"] = "d" * 40
    else:
        data[field] = {"repository": "other/repo", "pr_number": 9,
                       "criteria_sha256": "0" * 64}[field]
    wrong = CIStatusManifest.model_validate(data)
    with pytest.raises(ValueError):
        _compare(
            state.bundle, wrong if side == "previous" else previous,
            wrong if side == "current" else current,
        )


def test_reused_run_id_with_modified_assertions_is_not_retained_context():
    state, previous, _ = comparison_inputs()
    current = previous.model_copy(deep=True)
    current.runs[-1].source_url = "https://ci.example.invalid/changed-run-reference"
    comparison = _compare(state.bundle, previous, current)
    rows = {row.test_id: row for row in comparison.test_changes()}
    assert rows["category_filter"].previous == rows["category_filter"].current
    assert rows["category_filter"].change == "changed"
    assert comparison.run_changes()[-1].change == "changed"


def test_conflicting_exact_build_reports_stay_unknown():
    state, previous, current = comparison_inputs()
    current.runs.append(CIStatusRun(
        run_id="conflicting-report", head_sha=state.review.head_sha,
        source_url="https://ci.example.invalid/conflicting-report",
        outcomes={"row_entitlement": "passed"},
    ))
    comparison = _compare(state.bundle, previous, current)
    row = next(row for row in comparison.test_changes() if row.test_id == "row_entitlement")
    assert row.current.status == "unknown"
    assert row.current.run_ids == ("B-targeted", "conflicting-report")
    assert "conflict" in row.current.reason
    assert comparison.bundle.gate.verdict.value == "blocked"


def test_removed_and_added_mappings_are_not_passes_or_implicit_skips():
    state, previous, current = comparison_inputs()
    data = current.model_dump(mode="python")
    del data["expected_tests"]["AC-01"]
    data["expected_tests"]["AC-03"].append("missing_check")
    for run in data["runs"]:
        run["outcomes"].pop("category_filter", None)
    current = CIStatusManifest.model_validate(data)
    comparison = _compare(state.bundle, previous, current)
    rows = {row.test_id: row for row in comparison.test_changes()}
    assert rows["category_filter"].change == "removed"
    assert rows["category_filter"].current is None
    assert rows["missing_check"].change == "added"
    assert rows["missing_check"].previous is None
    assert rows["missing_check"].current.status == "unknown"
    assert rows["missing_check"].current_criterion_ids == ("AC-03",)


def test_shared_test_is_shown_once_and_mapping_changes_are_explicit():
    state, previous, current = comparison_inputs()
    current.expected_tests["AC-02"].append("category_filter")
    comparison = _compare(state.bundle, previous, current)
    rows = comparison.test_changes()
    assert len(rows) == 3
    row = next(row for row in rows if row.test_id == "category_filter")
    assert row.change == "changed"
    assert row.previous_criterion_ids == ("AC-01",)
    assert row.current_criterion_ids == ("AC-01", "AC-02")


def test_reversed_file_order_reports_removed_assertions_without_chronology_inference():
    state, previous, current = comparison_inputs()
    comparison = _compare(state.bundle, current, previous)
    row = next(row for row in comparison.test_changes() if row.test_id == "row_entitlement")
    assert row.previous.status == "failed" and row.current.status == "skipped"
    assert comparison.run_changes()[-1].change == "removed"


def test_manifest_order_and_outcome_key_order_do_not_create_semantic_changes():
    state, previous, _ = comparison_inputs()
    data = previous.model_dump(mode="python")
    data["runs"].reverse()
    for run in data["runs"]:
        run["outcomes"] = dict(reversed(list(run["outcomes"].items())))
    comparison = _compare(
        state.bundle, previous, CIStatusManifest.model_validate(data),
    )
    assert all(row.change == "unchanged" for row in comparison.test_changes())
    assert all(row.change == "unchanged" for row in comparison.run_changes())


def test_old_build_result_for_a_new_mapping_stays_stale():
    state, previous, current = comparison_inputs()
    current.expected_tests["AC-03"].append("stale_only")
    current.runs[0].outcomes["stale_only"] = "passed"
    comparison = _compare(state.bundle, previous, current)
    row = next(row for row in comparison.test_changes() if row.test_id == "stale_only")
    assert row.change == "added"
    assert row.current.status == "stale" and row.current.run_ids == ("A",)
    assert comparison.bundle.gate.verdict.value == "blocked"


def test_unconfirmed_review_cannot_be_used_to_compare_ci():
    state, previous, current = comparison_inputs()
    bundle = state.bundle.model_copy(update={
        "review": state.bundle.review.model_copy(update={"criteria_confirmed": False}),
    })
    with pytest.raises(ValueError):
        _compare(bundle, previous, current)
