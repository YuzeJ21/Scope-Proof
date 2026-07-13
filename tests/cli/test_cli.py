import hashlib
import json
from pathlib import Path

import pytest

from scopeproof_core.cli import main


def test_benchmark_command_prints_execution_derived_metrics(capsys) -> None:
    assert main(["benchmark"]) == 0
    output = capsys.readouterr().out
    assert '"executed_case_count": 12' in output
    assert '"must_have_false_ready": 0' in output
    assert '"evidence_quality_metrics"' in output
    assert '"criterion_agreement_rate": 1.0' in output


def test_fixture_review_saves_validated_local_record(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")

    result = main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--storage-dir",
            str(tmp_path / "reviews"),
        ]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert '"review_id"' in output
    assert '"report"' not in output
    assert list((tmp_path / "reviews").glob("*.json"))


def test_review_can_write_markdown_report_in_one_command(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    report = tmp_path / "scopeproof-review.md"

    assert (
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(requirements),
                "--storage-dir",
                str(tmp_path / "reviews"),
                "--report",
                str(report),
            ]
        )
        == 0
    )

    metadata = json.loads(capsys.readouterr().out)
    assert metadata["report"] == str(report)
    assert "ScopeProof Acceptance Review" in report.read_text(encoding="utf-8")
    assert list((tmp_path / "reviews").glob("*.json"))


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [(".json", '"review"'), (".csv", "review_id"), (".html", "<!doctype html>")],
)
def test_review_report_suffix_selects_existing_exporter(
    tmp_path: Path, capsys, suffix: str, expected: str
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    report = tmp_path / f"scopeproof-review{suffix}"

    assert (
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(requirements),
                "--storage-dir",
                str(tmp_path / "reviews"),
                "--report",
                str(report),
            ]
        )
        == 0
    )

    capsys.readouterr()
    assert expected in report.read_text(encoding="utf-8").lower()


def test_review_refuses_to_overwrite_report_before_reading_inputs(
    tmp_path: Path, capsys
) -> None:
    report = tmp_path / "existing.md"
    report.write_text("keep me", encoding="utf-8")

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--fixture",
                str(tmp_path / "missing-fixture.json"),
                "--requirements",
                str(tmp_path / "missing-requirements.txt"),
                "--report",
                str(report),
            ]
        )

    assert raised.value.code == 2
    stderr = capsys.readouterr().err
    assert "report path already exists" in stderr
    assert "Traceback" not in stderr
    assert report.read_text(encoding="utf-8") == "keep me"


def test_review_rejects_unsupported_report_suffix_before_reading_inputs(
    tmp_path: Path, capsys
) -> None:
    report = tmp_path / "report.txt"

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--fixture",
                str(tmp_path / "missing-fixture.json"),
                "--requirements",
                str(tmp_path / "missing-requirements.txt"),
                "--report",
                str(report),
            ]
        )

    assert raised.value.code == 2
    stderr = capsys.readouterr().err
    assert "report path must end in .md, .json, .csv, or .html" in stderr
    assert "Traceback" not in stderr
    assert not report.exists()


def test_review_reports_invalid_pr_url_without_traceback(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")

    with pytest.raises(SystemExit) as raised:
        main(["review", "--pr", "not-a-github-pr", "--requirements", str(requirements)])

    assert raised.value.code == 2
    stderr = capsys.readouterr().err
    assert "scopeproof: error:" in stderr
    assert "Expected https://github.com/OWNER/REPO/pull/NUMBER" in stderr
    assert "Traceback" not in stderr


def test_review_reports_missing_requirements_without_traceback(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing-requirements.txt"

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--pr",
                "https://github.com/YuzeJ21/Scope-Proof/pull/22",
                "--requirements",
                str(missing),
            ]
        )

    assert raised.value.code == 2
    stderr = capsys.readouterr().err
    assert "scopeproof: error:" in stderr
    assert str(missing) in stderr
    assert "Traceback" not in stderr


def test_export_command_reads_saved_review_without_credentials(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    storage = tmp_path / "reviews"
    main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--storage-dir",
            str(storage),
        ]
    )
    record = next(storage.glob("*.json"))
    review_id = record.stem

    assert main(["export", review_id, "--storage-dir", str(storage), "--format", "markdown"]) == 0
    output = capsys.readouterr().out
    assert "ScopeProof Acceptance Review" in output
    assert "ghp_" not in output


def test_export_command_supports_self_contained_html(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    storage = tmp_path / "reviews"
    main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--storage-dir",
            str(storage),
        ]
    )
    review_id = next(storage.glob("*.json")).stem

    assert main(["export", review_id, "--storage-dir", str(storage), "--format", "html"]) == 0
    assert "<!doctype html>" in capsys.readouterr().out.lower()


def test_action_evidence_command_validates_owner_supplied_record(tmp_path: Path, capsys) -> None:
    evidence_path = tmp_path / "action-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "repository": "acme/demo",
                "requirements_base_sha": "base123",
                "non_fork_pr_url": "https://github.com/acme/demo/pull/12",
                "non_fork_head_sha": "head123",
                "non_fork_run_url": "https://github.com/acme/demo/actions/runs/1",
                "non_fork_comment_count": 1,
                "scopeproof_comment_marker": "<!-- scopeproof:head123 -->",
                "rerun_url": "https://github.com/acme/demo/actions/runs/2",
                "rerun_head_sha": "head123",
                "rerun_comment_count": 1,
                "fork_pr_url": "https://github.com/acme/demo/pull/13",
                "fork_run_url": "https://github.com/acme/demo/actions/runs/3",
                "fork_comment_count": 0,
                "validated_by": "Demo owner",
                "validated_at": "2026-07-11T00:00:00Z",
                "limitations": ["Public demo only"],
            }
        ),
        encoding="utf-8",
    )

    assert main(["validate-action-evidence", str(evidence_path)]) == 0
    assert '"repository": "acme/demo"' in capsys.readouterr().out


def test_requirements_confirmation_command_validates_bound_record(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the demo.\n", encoding="utf-8")
    confirmation = tmp_path / "confirmation.json"
    confirmation.write_text(
        json.dumps(
            {
                "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
                "confirmed_by": "Demo owner",
                "confirmed_at": "2026-07-12T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    assert main(
        [
            "validate-requirements-confirmation",
            "--requirements",
            str(requirements),
            "--confirmation",
            str(confirmation),
        ]
    ) == 0
    assert '"confirmed_by": "Demo owner"' in capsys.readouterr().out
