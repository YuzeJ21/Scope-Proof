import hashlib
import json
from pathlib import Path

import pytest

from scopeproof_core.alpha.rehearsal_storage import JsonAlphaRehearsalStore
from scopeproof_core.alpha.storage import JsonAlphaCaseStore
from scopeproof_core.cli import main
from scopeproof_core.evals.comparison_runner import run_bundled_comparison_benchmark
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.version import __version__


def action_evidence_data() -> dict:
    base_sha = "1" * 40
    head_sha = "2" * 40
    return {
        "repository": "acme/demo",
        "requirements_base_sha": base_sha,
        "non_fork_pr_url": "https://github.com/acme/demo/pull/12",
        "non_fork_head_sha": head_sha,
        "non_fork_run_url": "https://github.com/acme/demo/actions/runs/1",
        "non_fork_comment_count": 1,
        "scopeproof_comment_marker": f"<!-- scopeproof:{head_sha} -->",
        "rerun_url": "https://github.com/acme/demo/actions/runs/2",
        "rerun_head_sha": head_sha,
        "rerun_comment_count": 1,
        "fork_pr_url": "https://github.com/acme/demo/pull/13",
        "fork_run_url": "https://github.com/acme/demo/actions/runs/3",
        "fork_comment_count": 0,
        "validated_by": "Demo owner",
        "validated_at": "2026-07-11T00:00:00Z",
        "limitations": ["Public demo only"],
    }


def test_cli_reports_shared_version_without_a_subcommand(capsys) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == f"scopeproof {__version__}\n"


def test_benchmark_command_prints_execution_derived_metrics(capsys) -> None:
    assert main(["benchmark"]) == 0
    output = capsys.readouterr().out
    assert '"executed_case_count": 12' in output
    assert '"must_have_false_ready": 0' in output
    assert '"evidence_quality_metrics"' in output
    assert '"criterion_agreement_rate": 1.0' in output


def test_comparison_benchmark_command_reports_constructed_boundary(capsys) -> None:
    assert main(["comparison-benchmark"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["executed_case_count"] == 2
    assert payload["actual_counts"]["unchanged"] == 1
    assert payload["actual_counts"] == payload["expected_counts"]
    assert payload["mismatches"] == []
    assert payload["evidence_boundary"] == "deliberately constructed engineering evidence"
    assert payload["does_not_advance_stage_1"] is True


def test_comparison_benchmark_command_returns_nonzero_for_mismatch(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    result = run_bundled_comparison_benchmark().model_copy(
        update={"mismatches": ["unchanged-reference: unchanged: expected 1, got 0"]}
    )
    monkeypatch.setattr(
        "scopeproof_core.cli.run_bundled_comparison_benchmark", lambda: result
    )

    assert main(["comparison-benchmark"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["mismatches"] == [
        "unchanged-reference: unchanged: expected 1, got 0"
    ]


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
    record = next((tmp_path / "reviews").glob("*.json"))
    state = JsonReviewStore(tmp_path / "reviews").load(record.stem)
    assert state.review.tool_version == __version__
    assert state.bundle is not None
    assert state.bundle.review.tool_version == __version__


def test_partial_fixture_review_reports_and_persists_ingestion_limitations(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    fixture_payload = json.loads(
        Path("evals/fixtures/complete_implementation_pr.json").read_text(encoding="utf-8")
    )
    fixture_payload.update(
        {
            "ingestion_state": "partial",
            "warnings": ["File limit reached; skipped 1 changed files."],
            "skipped_files": ["src/skipped.py"],
        }
    )
    fixture = tmp_path / "partial.json"
    fixture.write_text(json.dumps(fixture_payload), encoding="utf-8")

    assert main(
        [
            "review",
            "--fixture",
            str(fixture),
            "--requirements",
            str(requirements),
            "--storage-dir",
            str(tmp_path / "reviews"),
        ]
    ) == 0

    metadata = json.loads(capsys.readouterr().out)
    state = JsonReviewStore(tmp_path / "reviews").load(metadata["review_id"])
    assert metadata["ingestion_state"] == "partial"
    assert metadata["ingestion_warnings"] == fixture_payload["warnings"]
    assert metadata["skipped_files"] == fixture_payload["skipped_files"]
    assert state.review.ingestion_warnings == fixture_payload["warnings"]
    assert state.review.skipped_files == fixture_payload["skipped_files"]


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


def test_list_command_reports_empty_absent_local_store(tmp_path: Path, capsys) -> None:
    store_dir = tmp_path / "reviews"

    assert main(["list", "--storage-dir", str(store_dir)]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "review_ids": [],
        "storage_dir": str(store_dir),
    }
    assert not store_dir.exists()


def test_list_command_returns_sorted_safe_ids_without_parsing_records(
    tmp_path: Path, capsys
) -> None:
    store_dir = tmp_path / "reviews"
    store_dir.mkdir()
    (store_dir / "z-review.json").write_text("not json", encoding="utf-8")
    (store_dir / "a-review.json").write_text("also not json", encoding="utf-8")
    (store_dir / "ignored.txt").write_text("not a record", encoding="utf-8")

    assert main(["list", "--storage-dir", str(store_dir)]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "review_ids": ["a-review", "z-review"],
        "storage_dir": str(store_dir),
    }


def test_list_command_fails_closed_for_unsafe_store_root(
    tmp_path: Path, capsys
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    store_dir = tmp_path / "reviews"
    store_dir.symlink_to(outside, target_is_directory=True)

    with pytest.raises(SystemExit) as raised:
        main(["list", "--storage-dir", str(store_dir)])

    assert raised.value.code == 2
    captured = capsys.readouterr()
    assert "scopeproof: error:" in captured.err
    assert "symbolic link" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_delete_command_removes_one_saved_local_review(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    store_dir = tmp_path / "reviews"
    assert main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--storage-dir",
            str(store_dir),
        ]
    ) == 0
    review_id = json.loads(capsys.readouterr().out)["review_id"]

    assert main(["delete", review_id, "--storage-dir", str(store_dir)]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "deleted_review_id": review_id,
        "storage_dir": str(store_dir),
    }
    assert not (store_dir / f"{review_id}.json").exists()


@pytest.mark.parametrize("review_id", ["missing-review", "../invalid-review"])
def test_delete_command_reports_invalid_or_missing_id_without_deleting_neighbor(
    tmp_path: Path, capsys, review_id: str
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    store_dir = tmp_path / "reviews"
    assert main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--storage-dir",
            str(store_dir),
        ]
    ) == 0
    neighbor_id = json.loads(capsys.readouterr().out)["review_id"]

    with pytest.raises(SystemExit) as raised:
        main(["delete", review_id, "--storage-dir", str(store_dir)])

    assert raised.value.code == 2
    captured = capsys.readouterr()
    assert "scopeproof: error:" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert (store_dir / f"{neighbor_id}.json").is_file()


def test_action_evidence_command_validates_owner_supplied_record(tmp_path: Path, capsys) -> None:
    evidence_path = tmp_path / "action-evidence.json"
    evidence_path.write_text(json.dumps(action_evidence_data()), encoding="utf-8")

    assert main(["validate-action-evidence", str(evidence_path)]) == 0
    assert '"repository": "acme/demo"' in capsys.readouterr().out


def test_action_evidence_command_rejects_blank_owner_context(tmp_path: Path, capsys) -> None:
    evidence_path = tmp_path / "blank-action-evidence.json"
    payload = action_evidence_data() | {"validated_by": "   "}
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(["validate-action-evidence", str(evidence_path)])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "non-whitespace" in captured.err
    assert '"repository"' not in captured.out


def test_action_evidence_command_rejects_invalid_commit_sha(tmp_path: Path, capsys) -> None:
    evidence_path = tmp_path / "invalid-sha-action-evidence.json"
    payload = action_evidence_data() | {
        "non_fork_head_sha": "not-a-sha",
        "scopeproof_comment_marker": "<!-- scopeproof:not-a-sha -->",
        "rerun_head_sha": "not-a-sha",
    }
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(["validate-action-evidence", str(evidence_path)])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "string_pattern_mismatch" in captured.err
    assert captured.out == ""


def test_action_evidence_command_rejects_noncanonical_repository_identity(
    tmp_path: Path, capsys
) -> None:
    evidence_path = tmp_path / "invalid-repository-action-evidence.json"
    payload = action_evidence_data() | {
        "repository": "ac me/demo",
        "non_fork_pr_url": "https://github.com/ac me/demo/pull/12",
        "non_fork_run_url": "https://github.com/ac me/demo/actions/runs/1",
        "rerun_url": "https://github.com/ac me/demo/actions/runs/2",
        "fork_pr_url": "https://github.com/ac me/demo/pull/13",
        "fork_run_url": "https://github.com/ac me/demo/actions/runs/3",
    }
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(["validate-action-evidence", str(evidence_path)])

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "string_pattern_mismatch" in captured.err
    assert '"repository"' not in captured.out


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


def test_requirements_confirmation_command_rejects_blank_confirmer(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the demo.\n", encoding="utf-8")
    confirmation = tmp_path / "confirmation.json"
    confirmation.write_text(
        json.dumps(
            {
                "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
                "confirmed_by": "   ",
                "confirmed_at": "2026-07-12T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as error:
        main(
            [
                "validate-requirements-confirmation",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(confirmation),
            ]
        )

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "confirmed_by must contain non-whitespace text" in captured.err
    assert captured.out == ""


def _initialize_alpha_case(tmp_path: Path, capsys) -> tuple[Path, str]:
    requirements = tmp_path / "alpha-requirements.txt"
    requirements.write_text("Export CSV\nShow an error state\n", encoding="utf-8")
    store = tmp_path / "alpha-cases"
    assert main(
        [
            "alpha",
            "init",
            "--pr",
            "https://github.com/acme/repo/pull/7",
            "--requirements-source",
            "https://github.com/acme/repo/issues/6",
            "--participant-role",
            "qa",
            "--requirements",
            str(requirements),
            "--source-owner-confirmed",
            "--confirmed-no-confidential-information",
            "--storage-dir",
            str(store),
        ]
    ) == 0
    case_id = json.loads(capsys.readouterr().out)["case_id"]
    return store, case_id


def test_alpha_init_creates_validated_local_record(tmp_path: Path, capsys) -> None:
    store_dir, case_id = _initialize_alpha_case(tmp_path, capsys)

    record = JsonAlphaCaseStore(store_dir).load(case_id)

    assert record.confirmed_criteria == ["Export CSV", "Show an error state"]
    assert record.source_owner_confirmed is True
    assert record.no_confidential_information is True


def _initialize_owner_rehearsal(tmp_path: Path, capsys) -> tuple[Path, str, dict]:
    requirements = tmp_path / "rehearsal-requirements.txt"
    requirements.write_text("Export CSV\nShow an error state\n", encoding="utf-8")
    store = tmp_path / "alpha-rehearsals"
    assert main(
        [
            "owner-rehearsal",
            "init",
            "--pr",
            "https://github.com/acme/repo/pull/7",
            "--requirements-source",
            "https://example.com/requirements.txt",
            "--criteria-authority",
            "Repository owner approval",
            "--requirements",
            str(requirements),
            "--source-owner-confirmed",
            "--confirmed-no-confidential-information",
            "--storage-dir",
            str(store),
        ]
    ) == 0
    created = json.loads(capsys.readouterr().out)
    return store, created["rehearsal_id"], created


def test_owner_rehearsal_init_persists_fixed_exclusion_and_show_reloads_record(
    tmp_path: Path, capsys
) -> None:
    store_dir, rehearsal_id, created = _initialize_owner_rehearsal(tmp_path, capsys)

    record = JsonAlphaRehearsalStore(store_dir).load(rehearsal_id)

    assert record.confirmed_criteria == ["Export CSV", "Show an error state"]
    assert created["submission_mode"] == "owner_rehearsal"
    assert created["eligible_for_stage_1"] is False
    assert created["external_participant"] is False
    assert created["external_validation"] is False
    assert "engineering evidence only" in created["exclusion_reason"]

    assert main(
        [
            "owner-rehearsal",
            "show",
            rehearsal_id,
            "--storage-dir",
            str(store_dir),
        ]
    ) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown == record.model_dump(mode="json")


@pytest.mark.parametrize(
    "omitted_flag",
    [
        "--criteria-authority",
        "--source-owner-confirmed",
        "--confirmed-no-confidential-information",
    ],
)
def test_owner_rehearsal_init_requires_authority_and_confirmations(
    tmp_path: Path, capsys, omitted_flag: str
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    arguments = [
        "owner-rehearsal",
        "init",
        "--pr",
        "https://github.com/acme/repo/pull/7",
        "--requirements-source",
        "https://example.com/requirements.txt",
        "--criteria-authority",
        "Repository owner approval",
        "--requirements",
        str(requirements),
        "--source-owner-confirmed",
        "--confirmed-no-confidential-information",
    ]
    if omitted_flag == "--criteria-authority":
        index = arguments.index(omitted_flag)
        del arguments[index : index + 2]
    else:
        arguments.remove(omitted_flag)

    with pytest.raises(SystemExit) as error:
        main(arguments)

    assert error.value.code == 2
    assert omitted_flag in capsys.readouterr().err


def test_owner_rehearsal_init_rejects_duplicate_and_genuine_only_flags(
    tmp_path: Path, capsys
) -> None:
    store_dir, rehearsal_id, _ = _initialize_owner_rehearsal(tmp_path, capsys)
    persisted_before = JsonAlphaRehearsalStore(store_dir).load(rehearsal_id)
    requirements = tmp_path / "rehearsal-requirements.txt"
    common_arguments = [
        "owner-rehearsal",
        "init",
        "--pr",
        "https://github.com/acme/repo/pull/7",
        "--requirements-source",
        "https://example.com/requirements.txt",
        "--criteria-authority",
        "Repository owner approval",
        "--requirements",
        str(requirements),
        "--source-owner-confirmed",
        "--confirmed-no-confidential-information",
        "--storage-dir",
        str(store_dir),
    ]

    with pytest.raises(SystemExit) as duplicate:
        main(common_arguments)
    assert duplicate.value.code == 2
    capsys.readouterr()
    assert JsonAlphaRehearsalStore(store_dir).load(rehearsal_id) == persisted_before

    for flag in ("--result", "--head-sha", "--participant-role", "--report-consent"):
        with pytest.raises(SystemExit) as rejected:
            arguments = (
                [*common_arguments, flag, "value"]
                if flag != "--report-consent"
                else [*common_arguments, flag]
            )
            main(arguments)
        assert rejected.value.code == 2
        assert "unrecognized arguments" in capsys.readouterr().err


def test_alpha_init_requires_confidentiality_confirmation(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "alpha",
                "init",
                "--pr",
                "https://github.com/acme/repo/pull/7",
                "--requirements-source",
                "https://github.com/acme/repo/issues/6",
                "--participant-role",
                "qa",
                "--requirements",
                str(requirements),
                "--source-owner-confirmed",
            ]
        )

    assert error.value.code == 2
    assert "--confirmed-no-confidential-information" in capsys.readouterr().err


def test_alpha_init_requires_source_owner_confirmation(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "alpha",
                "init",
                "--pr",
                "https://github.com/acme/repo/pull/7",
                "--requirements-source",
                "https://github.com/acme/repo/issues/6",
                "--participant-role",
                "qa",
                "--requirements",
                str(requirements),
                "--confirmed-no-confidential-information",
            ]
        )

    assert error.value.code == 2
    assert "--source-owner-confirmed" in capsys.readouterr().err


def test_alpha_outcome_and_consent_gated_public_summary(
    tmp_path: Path, capsys
) -> None:
    store_dir, case_id = _initialize_alpha_case(tmp_path, capsys)
    notes = tmp_path / "outcome.txt"
    notes.write_text("The report showed only information already known.\n", encoding="utf-8")

    assert main(
        [
            "alpha",
            "outcome",
            case_id,
            "--review-id",
            "review-7",
            "--head-sha",
            "a" * 40,
            "--result",
            "showed_only_known_information",
            "--notes-file",
            str(notes),
            "--report-consent",
            "--storage-dir",
            str(store_dir),
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["outcome"] == "showed_only_known_information"

    assert main(
        [
            "alpha",
            "show",
            case_id,
            "--public-summary",
            "--storage-dir",
            str(store_dir),
        ]
    ) == 0
    public = json.loads(capsys.readouterr().out)
    assert "outcome_notes" not in public
    assert "publication_consent" not in public


def test_alpha_public_summary_refuses_without_report_consent(
    tmp_path: Path, capsys
) -> None:
    store_dir, case_id = _initialize_alpha_case(tmp_path, capsys)
    assert main(
        [
            "alpha",
            "outcome",
            case_id,
            "--review-id",
            "review-7",
            "--head-sha",
            "a" * 40,
            "--result",
            "found_useful_gap",
            "--storage-dir",
            str(store_dir),
        ]
    ) == 0
    capsys.readouterr()

    with pytest.raises(SystemExit) as error:
        main(
            [
                "alpha",
                "show",
                case_id,
                "--public-summary",
                "--storage-dir",
                str(store_dir),
            ]
        )

    assert error.value.code == 2
    assert "report publication consent" in capsys.readouterr().err


def test_alpha_friction_requires_stage(tmp_path: Path, capsys) -> None:
    store_dir, case_id = _initialize_alpha_case(tmp_path, capsys)

    with pytest.raises(SystemExit) as error:
        main(
            [
                "alpha",
                "outcome",
                case_id,
                "--review-id",
                "review-7",
                "--head-sha",
                "a" * 40,
                "--result",
                "created_friction",
                "--storage-dir",
                str(store_dir),
            ]
        )

    assert error.value.code == 2
    assert "friction stage" in capsys.readouterr().err
