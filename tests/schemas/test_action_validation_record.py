from datetime import UTC, datetime

import pytest

from scopeproof_core.schemas.models import ActionValidationRecord

BASE_SHA = "1" * 40
HEAD_SHA = "2" * 40
OTHER_SHA = "3" * 40


def record_data() -> dict:
    return {
        "repository": "acme/demo",
        "requirements_base_sha": BASE_SHA,
        "non_fork_pr_url": "https://github.com/acme/demo/pull/12",
        "non_fork_head_sha": HEAD_SHA,
        "non_fork_run_url": "https://github.com/acme/demo/actions/runs/1",
        "non_fork_comment_count": 1,
        "scopeproof_comment_marker": f"<!-- scopeproof:{HEAD_SHA} -->",
        "rerun_url": "https://github.com/acme/demo/actions/runs/2",
        "rerun_head_sha": HEAD_SHA,
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


def test_action_validation_record_allows_a_single_account_fork_exclusion() -> None:
    non_fork_only = record_data() | {"fork_status": "excluded"}
    non_fork_only.pop("fork_pr_url")
    non_fork_only.pop("fork_run_url")
    non_fork_only.pop("fork_comment_count")

    record = ActionValidationRecord.model_validate(non_fork_only)

    assert record.fork_status == "excluded"
    assert record.fork_pr_url is None


def test_action_validation_record_rejects_rerun_that_changes_head_or_comment_count() -> None:
    changed_head = record_data() | {"rerun_head_sha": OTHER_SHA}
    with pytest.raises(ValueError, match="same head SHA"):
        ActionValidationRecord.model_validate(changed_head)

    duplicated_comment = record_data() | {"rerun_comment_count": 2}
    with pytest.raises(ValueError, match="same comment count"):
        ActionValidationRecord.model_validate(duplicated_comment)


def test_action_validation_record_rejects_links_from_another_repository() -> None:
    mixed_repository = record_data() | {
        "fork_run_url": "https://github.com/other/demo/actions/runs/3"
    }

    with pytest.raises(ValueError, match="same repository"):
        ActionValidationRecord.model_validate(mixed_repository)


def test_action_validation_record_requires_marker_for_the_verified_head() -> None:
    wrong_marker = record_data() | {
        "scopeproof_comment_marker": f"<!-- scopeproof:{OTHER_SHA} -->"
    }

    with pytest.raises(ValueError, match="comment marker"):
        ActionValidationRecord.model_validate(wrong_marker)


@pytest.mark.parametrize("blank_value", ["   ", "\t", "\n"])
def test_action_validation_record_rejects_blank_validated_by(blank_value: str) -> None:
    payload = record_data() | {"validated_by": blank_value}

    with pytest.raises(ValueError, match="non-whitespace"):
        ActionValidationRecord.model_validate(payload)


@pytest.mark.parametrize(
    "invalid_sha",
    ["", "   ", "x", "not-a-sha", "g" * 40, "a" * 39, "a" * 41, "A" * 40],
)
@pytest.mark.parametrize(
    "field_name",
    ["requirements_base_sha", "non_fork_head_sha", "rerun_head_sha"],
)
def test_action_validation_record_rejects_invalid_commit_sha_shape(
    field_name: str, invalid_sha: str
) -> None:
    payload = record_data()
    payload[field_name] = invalid_sha
    if field_name in {"non_fork_head_sha", "rerun_head_sha"}:
        payload["non_fork_head_sha"] = invalid_sha
        payload["rerun_head_sha"] = invalid_sha
        payload["scopeproof_comment_marker"] = f"<!-- scopeproof:{invalid_sha} -->"

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        ActionValidationRecord.model_validate(payload)


def test_action_validation_record_preserves_valid_commit_shas_exactly() -> None:
    record = ActionValidationRecord.model_validate(record_data())

    assert record.requirements_base_sha == BASE_SHA
    assert record.non_fork_head_sha == HEAD_SHA
    assert record.rerun_head_sha == HEAD_SHA
    assert record.scopeproof_comment_marker == f"<!-- scopeproof:{HEAD_SHA} -->"


@pytest.mark.parametrize("blank_value", ["   ", "\t", "\n"])
def test_action_validation_record_rejects_blank_limitation(blank_value: str) -> None:
    payload = record_data() | {"limitations": ["Public demo only", blank_value]}

    with pytest.raises(ValueError, match="limitation"):
        ActionValidationRecord.model_validate(payload)


def test_action_validation_record_preserves_valid_human_context() -> None:
    payload = record_data() | {
        "validated_by": "  Demo repository owner  ",
        "limitations": ["  Public demo only  "],
    }

    record = ActionValidationRecord.model_validate(payload)

    assert record.validated_by == "  Demo repository owner  "
    assert record.limitations == ["  Public demo only  "]


@pytest.mark.parametrize(
    ("repository", "url_prefix"),
    [
        (" / ", "https://github.com/ / "),
        ("ac me/de mo", "https://github.com/ac me/de mo"),
        (" acme/demo", "https://github.com/ acme/demo"),
        ("acme/demo\t", "https://github.com/acme/demo\t"),
    ],
)
def test_action_validation_record_rejects_noncanonical_repository_identity(
    repository: str, url_prefix: str
) -> None:
    payload = record_data() | {
        "repository": repository,
        "non_fork_pr_url": f"{url_prefix}/pull/12",
        "non_fork_run_url": f"{url_prefix}/actions/runs/1",
        "rerun_url": f"{url_prefix}/actions/runs/2",
        "fork_pr_url": f"{url_prefix}/pull/13",
        "fork_run_url": f"{url_prefix}/actions/runs/3",
    }

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        ActionValidationRecord.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "non_fork_pr_url",
        "non_fork_run_url",
        "rerun_url",
        "fork_pr_url",
        "fork_run_url",
    ],
)
def test_action_validation_record_rejects_noncanonical_github_url_field(
    field_name: str,
) -> None:
    payload = record_data()
    suffix = "/pull/12" if field_name.endswith("pr_url") else "/actions/runs/1"
    payload[field_name] = f"https://github.com/ac me/demo{suffix}"

    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        ActionValidationRecord.model_validate(payload)


def test_action_validation_record_accepts_supported_slug_characters() -> None:
    payload = record_data() | {
        "repository": "acme-team/demo.repo_name",
        "non_fork_pr_url": "https://github.com/acme-team/demo.repo_name/pull/12",
        "non_fork_run_url": "https://github.com/acme-team/demo.repo_name/actions/runs/1",
        "rerun_url": "https://github.com/acme-team/demo.repo_name/actions/runs/2",
        "fork_pr_url": "https://github.com/acme-team/demo.repo_name/pull/13",
        "fork_run_url": "https://github.com/acme-team/demo.repo_name/actions/runs/3",
    }

    record = ActionValidationRecord.model_validate(payload)

    assert record.repository == "acme-team/demo.repo_name"
