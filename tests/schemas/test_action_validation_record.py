from datetime import UTC, datetime

import pytest

from scopeproof_core.schemas.models import ActionValidationRecord


def record_data() -> dict:
    return {
        "repository": "acme/demo",
        "requirements_base_sha": "base123",
        "non_fork_pr_url": "https://github.com/acme/demo/pull/12",
        "non_fork_head_sha": "head123",
        "non_fork_run_url": "https://github.com/acme/demo/actions/runs/1",
        "non_fork_comment_count": 1,
        "rerun_url": "https://github.com/acme/demo/actions/runs/2",
        "rerun_head_sha": "head123",
        "rerun_comment_count": 1,
        "fork_pr_url": "https://github.com/acme/demo/pull/13",
        "fork_run_url": "https://github.com/acme/demo/actions/runs/3",
        "fork_comment_count": 0,
        "validated_by": "Demo repository owner",
        "validated_at": datetime(2026, 7, 11, tzinfo=UTC),
        "limitations": ["Public demo only"],
    }


def test_action_validation_record_requires_idempotent_same_head_rerun() -> None:
    record = ActionValidationRecord.model_validate(record_data())

    assert record.rerun_comment_count == record.non_fork_comment_count


def test_action_validation_record_rejects_rerun_that_changes_head_or_comment_count() -> None:
    changed_head = record_data() | {"rerun_head_sha": "different"}
    with pytest.raises(ValueError, match="same head SHA"):
        ActionValidationRecord.model_validate(changed_head)

    duplicated_comment = record_data() | {"rerun_comment_count": 2}
    with pytest.raises(ValueError, match="same comment count"):
        ActionValidationRecord.model_validate(duplicated_comment)
