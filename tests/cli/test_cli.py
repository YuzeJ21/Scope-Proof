from pathlib import Path

from scopeproof_core.cli import main


def test_benchmark_command_prints_execution_derived_metrics(capsys) -> None:
    assert main(["benchmark"]) == 0
    output = capsys.readouterr().out
    assert '"executed_case_count": 12' in output
    assert '"must_have_false_ready": 0' in output


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
