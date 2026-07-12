import json
from pathlib import Path

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
    assert list((tmp_path / "reviews").glob("*.json"))


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
