"""CSV handoffs retain the validated review's actionable gate explanation."""

import csv
import io
import json

import pytest

from scopeproof_core.demo import (
    build_demo_review,
    build_review,
    load_demo_labels,
    load_demo_snapshot,
)
from scopeproof_core.reporting.exporters import export_csv
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.schemas.models import (
    CheckState,
    HumanDecision,
    PullRequestSnapshot,
    ResolutionEvent,
)

_GATE_COLUMNS = [
    "gate_reason_codes",
    "gate_blocking_criteria",
    "gate_conditional_criteria",
    "gate_unresolved_criteria",
    "gate_resolved_exceptions",
    "gate_guidance",
]


def _accept_all(state):
    for criterion in state.bundle.criteria:
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                reviewer="Synthetic reviewer",
                comment="Synthetic decision accepting the recorded evidence limitation.",
            ),
        )
    return state


def _rows(value):
    rendered = export_csv(value)
    reader = csv.DictReader(io.StringIO(rendered))
    rows = list(reader)
    assert reader.fieldnames[-6:] == _GATE_COLUMNS
    assert reader.fieldnames[-7] == "junit_limitations"
    assert reader.fieldnames[:5] == [
        "review_id", "repository", "repository_visibility", "pr_number", "base_sha"
    ]
    return rendered, rows


@pytest.mark.parametrize("as_state", [True, False], ids=["state", "bundle"])
def test_csv_explains_missing_final_acceptance_after_every_criterion_is_accepted(
    as_state,
):
    state = _accept_all(new_review_state(build_demo_review()))
    value = state if as_state else state.bundle
    before = value.model_dump(mode="json")

    rendered, rows = _rows(value)

    assert len(rows) == 4
    assert [row["criterion_id"] for row in rows] == ["AC-01", "AC-02", "AC-03", "AC-04"]
    for row in rows:
        assert row["human_decision"] == "accepted"
        assert row["review_status"] == "Review incomplete"
        assert row["verdict"] == "needs_review"
        assert row["review_id"] == state.review.review_id
        assert row["head_sha"] == state.review.head_sha
        assert json.loads(row["gate_reason_codes"]) == ["final_acceptance_required"]
        for column in _GATE_COLUMNS[1:5]:
            assert json.loads(row[column]) == []
        assert json.loads(row["gate_guidance"]) == [
            "Record final acceptance only after a reviewer has reviewed every criterion and "
            "its evidence."
        ]
    assert export_csv(value) == rendered
    assert value.model_dump(mode="json") == before


def test_csv_distinguishes_blocking_conditional_unresolved_and_resolved_exceptions():
    state = new_review_state(build_demo_review())
    state = append_resolution(
        state,
        ResolutionEvent(
            criterion_id="AC-04",
            decision=HumanDecision.ACCEPTED_EXCEPTION,
            reviewer="Synthetic reviewer",
            comment='Accepted synthetic exception: =SUM(1,2), "review later"\nnext line.',
        ),
    )
    before = state.model_dump(mode="json")

    rendered, rows = _rows(state)

    assert len(rows) == 4
    for row in rows:
        assert row["verdict"] == "blocked"
        assert json.loads(row["gate_reason_codes"]) == [
            "blocking_criteria", "conditional_criteria", "unresolved_criteria"
        ]
        assert json.loads(row["gate_blocking_criteria"]) == ["AC-02", "AC-03"]
        assert json.loads(row["gate_conditional_criteria"]) == ["AC-04"]
        assert json.loads(row["gate_unresolved_criteria"]) == ["AC-01"]
        assert json.loads(row["gate_resolved_exceptions"]) == ["AC-04"]
        assert json.loads(row["gate_guidance"]) == [
            "Review required changes or missing or partial evidence for blocking criteria: "
            "AC-02, AC-03.",
            "Explicitly review conditional criteria or accepted exceptions before acceptance: "
            "AC-04.",
            "Record an explicit human decision for unresolved criteria: AC-01. "
            "ScopeProof does not decide them.",
        ]
    assert rows[3]["human_decision"] == "accepted_exception"
    assert rows[3]["reviewer_comment"] == (
        'Accepted synthetic exception: =SUM(1,2), "review later"\nnext line.'
    )
    assert export_csv(state) == rendered
    assert state.model_dump(mode="json") == before


def test_csv_keeps_failing_ci_action_when_no_criterion_remains_unresolved():
    snapshot_data = load_demo_snapshot().model_dump(mode="python")
    snapshot_data["check_state"] = CheckState.FAILING
    snapshot_data["ci_observation"] = {
        "state": CheckState.FAILING,
        "reason": "Constructed failing CI observation.",
        "reason_code": "failing_check_runs",
        "total_check_runs": 1,
        "failing_check_runs": 1,
    }
    snapshot = PullRequestSnapshot.model_validate(snapshot_data)
    state = _accept_all(new_review_state(build_review(snapshot, load_demo_labels())))
    before = state.model_dump(mode="json")

    _, rows = _rows(state)

    assert len(rows) == 4
    for row in rows:
        assert row["human_decision"] == "accepted"
        assert row["review_status"] == "Action required"
        assert json.loads(row["gate_reason_codes"]) == ["required_checks_failing"]
        for column in _GATE_COLUMNS[1:5]:
            assert json.loads(row[column]) == []
        assert json.loads(row["gate_guidance"]) == [
            "Review the failing required GitHub checks before acceptance; "
            "ScopeProof does not rerun or diagnose them."
        ]
    assert state.model_dump(mode="json") == before
