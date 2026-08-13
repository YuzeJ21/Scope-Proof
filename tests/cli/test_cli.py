import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from threading import Event
from unittest.mock import patch

import pytest

import scopeproof_core.cli as cli_module
import scopeproof_core.storage.atomic_files as atomic_files_module
from scopeproof_core.alpha.rehearsal_storage import JsonAlphaRehearsalStore
from scopeproof_core.alpha.storage import JsonAlphaCaseStore
from scopeproof_core.cli import _build_bundle, main
from scopeproof_core.criteria.confirmation import (
    build_criteria_source_provenance,
    read_exact_utf8_text,
)
from scopeproof_core.criteria.service import parse_criteria
from scopeproof_core.demo import build_demo_review, build_review_from_paths
from scopeproof_core.evals.comparison_runner import run_bundled_comparison_benchmark
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.github.client import GitHubPaginationError
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    append_resolution,
    attach_analysis,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    CriteriaSourceProvenance,
    Criterion,
    EvidenceLevel,
    HumanDecision,
    LifecycleMutationMetadata,
    PullRequestSnapshot,
    RepositoryVisibility,
    ResolutionEvent,
    ReviewInputOrigin,
    RuntimeEvidence,
)
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


def write_requirements_confirmation(
    requirements: Path,
    *,
    source_uri: str = "https://example.test/requirements",
    source_revision: str | None = "revision-42",
) -> Path:
    source_text = read_exact_utf8_text(requirements)
    criteria = [
        Criterion(criterion_id=draft.criterion_id, text=draft.text)
        for draft in parse_criteria(source_text)
    ]
    confirmation = build_criteria_source_provenance(
        source_uri=source_uri,
        source_revision=source_revision,
        source_text=source_text,
        criteria=criteria,
        confirmed_by="Demo owner",
        confirmed_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    path = requirements.with_name(f"{requirements.stem}-confirmation.json")
    path.write_text(confirmation.model_dump_json(indent=2), encoding="utf-8")
    return path


def test_review_requires_explicit_confirmation_before_github_fetch(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(
        "scopeproof_core.cli.GitHubClient.fetch_pull_request",
        lambda _self, pr: calls.append(pr),
    )

    with pytest.raises(SystemExit) as error:
        main(
            [
                "review",
                "--pr",
                "https://github.com/acme/repo/pull/7",
                "--requirements",
                str(requirements),
            ]
        )

    assert error.value.code == 2
    assert "--confirmation" in capsys.readouterr().err
    assert calls == []


@pytest.mark.parametrize("malformation", ["changed", "malformed"])
def test_review_rejects_invalid_confirmation_before_fixture_ingestion(
    tmp_path: Path, capsys, malformation: str
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    confirmation = write_requirements_confirmation(requirements)
    if malformation == "changed":
        requirements.write_text("Changed requirement\n", encoding="utf-8")
    else:
        confirmation.write_text("not-json", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "review",
                "--fixture",
                str(tmp_path / "fixture-must-not-be-read.json"),
                "--requirements",
                str(requirements),
                "--confirmation",
                str(confirmation),
            ]
        )

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert "confirmation" in stderr or "Invalid JSON" in stderr
    assert "fixture-must-not-be-read" not in stderr


def test_review_rejects_stale_confirmation_before_github_fetch(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    confirmation = write_requirements_confirmation(requirements)
    requirements.write_text("Changed requirement\n", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(
        "scopeproof_core.cli.GitHubClient.fetch_pull_request",
        lambda _self, pr: calls.append(pr),
    )

    with pytest.raises(SystemExit):
        main(
            [
                "review",
                "--pr",
                "https://github.com/acme/repo/pull/7",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(confirmation),
            ]
        )

    assert calls == []
    assert "source_text_sha256" in capsys.readouterr().err


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
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
            "--storage-dir",
            str(tmp_path / "reviews"),
        ]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert '"review_id"' in output
    assert '"report"' not in output
    metadata = json.loads(output)
    assert metadata["criteria_source_provenance"]["source_uri"] == (
        "https://example.test/requirements"
    )
    record = next((tmp_path / "reviews").glob("*.json"))
    state = JsonReviewStore(tmp_path / "reviews").load(record.stem)
    assert state.review.tool_version == __version__
    assert state.bundle is not None
    assert state.review.criteria_source_provenance is not None
    assert (
        state.review.criteria_source_provenance
        == state.criteria_revision.source_provenance
        == state.bundle.review.criteria_source_provenance
    )
    assert state.bundle.review.tool_version == __version__
    assert len(state.bundle.retrieval_diagnostics) == len(state.bundle.criteria) == 1
    diagnostic = state.bundle.retrieval_diagnostics[0]
    assert diagnostic.criterion_id == "AC-01"
    assert diagnostic.accepted_candidate_count == len(state.bundle.evidence)


def test_live_review_rejects_unverified_snapshot_without_saving(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    snapshot = PullRequestSnapshot(
        repository="acme/repo",
        pr_number=7,
        title="Export CSV",
        html_url="https://github.com/acme/repo/pull/7",
        base_sha="b" * 40,
        head_sha="a" * 40,
    )
    monkeypatch.setattr(
        "scopeproof_core.cli.GitHubClient.fetch_pull_request",
        lambda _self, _pr: snapshot,
    )
    storage = tmp_path / "reviews"

    with pytest.raises(SystemExit) as error:
        main(
            [
                "review",
                "--pr",
                "https://github.com/acme/repo/pull/7",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "verified public" in capsys.readouterr().err
    assert not storage.exists()


def test_live_review_pagination_failure_preserves_storage_and_report(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    confirmation = write_requirements_confirmation(requirements)
    storage = tmp_path / "reviews"
    storage.mkdir()
    sentinel = storage / "existing-record.json"
    sentinel.write_bytes(b'{"preserved":true}\n')
    before = sentinel.read_bytes()
    report = tmp_path / "must-not-exist.json"
    monkeypatch.setattr(
        "scopeproof_core.cli.GitHubClient.fetch_pull_request",
        lambda _self, _pr: (_ for _ in ()).throw(
            GitHubPaginationError("GitHub pagination target was rejected.")
        ),
    )

    with pytest.raises(SystemExit) as error:
        main(
            [
                "review",
                "--pr",
                "https://github.com/acme/repo/pull/7",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(confirmation),
                "--storage-dir",
                str(storage),
                "--report",
                str(report),
            ]
        )

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert "pagination target was rejected" in stderr
    assert "Traceback" not in stderr
    assert sentinel.read_bytes() == before
    assert list(storage.iterdir()) == [sentinel]
    assert not report.exists()


def test_live_review_persists_verified_public_snapshot_provenance(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    snapshot = PullRequestSnapshot(
        repository="acme/repo",
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        pr_number=7,
        title="Export CSV",
        html_url="https://github.com/acme/repo/pull/7",
        base_sha="b" * 40,
        head_sha="a" * 40,
    )
    monkeypatch.setattr(
        "scopeproof_core.cli.GitHubClient.fetch_pull_request",
        lambda _self, _pr: snapshot,
    )
    storage = tmp_path / "reviews"

    assert main(
        [
            "review",
            "--pr",
            "https://github.com/acme/repo/pull/7",
            "--requirements",
            str(requirements),
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
            "--storage-dir",
            str(storage),
        ]
    ) == 0

    review_id = json.loads(capsys.readouterr().out)["review_id"]
    state = JsonReviewStore(storage).load(review_id)
    assert state.review.repository_visibility is RepositoryVisibility.VERIFIED_PUBLIC
    assert state.bundle is not None
    assert state.bundle.review.repository_visibility is RepositoryVisibility.VERIFIED_PUBLIC


def test_fixture_review_preserves_exact_crlf_requirements_digest(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    raw = b"Export CSV\r\n"
    requirements.write_bytes(raw)
    source_text = raw.decode("utf-8")
    criteria = [
        Criterion(criterion_id=draft.criterion_id, text=draft.text)
        for draft in parse_criteria(source_text)
    ]
    confirmation = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_text=source_text,
        criteria=criteria,
        confirmed_by="Demo owner",
        confirmed_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    confirmation_path = tmp_path / "confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    assert main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--confirmation",
            str(confirmation_path),
            "--storage-dir",
            str(tmp_path / "reviews"),
        ]
    ) == 0

    capsys.readouterr()
    record = next((tmp_path / "reviews").glob("*.json"))
    state = JsonReviewStore(tmp_path / "reviews").load(record.stem)
    assert state.criteria_revision.source_text == source_text
    assert state.review.criteria_source_provenance is not None
    assert state.review.criteria_source_provenance.source_text_sha256 == (
        sha256(raw).hexdigest()
    )


def test_fixture_review_metadata_reports_validated_ci_observation(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")

    assert main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
            "--storage-dir",
            str(tmp_path / "reviews"),
        ]
    ) == 0

    metadata = json.loads(capsys.readouterr().out)
    assert metadata["ci_state"] == "passing"
    assert metadata["ci_reason"] == (
        "Observed 1 successful completed check run; no concrete legacy statuses."
    )
    assert metadata["skipped_check_names"] == []
    assert metadata["ci_collection_complete"] is True
    assert metadata["ci_total_check_runs"] == 1
    assert metadata["ci_successful_check_runs"] == 1
    assert metadata["ci_skipped_check_runs"] == 0
    assert "research_case_id" not in metadata
    assert "research_classification" not in metadata
    assert "stage1_credit" not in metadata


def test_fixture_review_cannot_self_assert_verified_public_visibility(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    fixture_payload = json.loads(
        Path("evals/fixtures/complete_implementation_pr.json").read_text(encoding="utf-8")
    )
    fixture_payload["repository_visibility"] = "verified_public"
    fixture = tmp_path / "self-asserted-public.json"
    fixture.write_text(json.dumps(fixture_payload), encoding="utf-8")
    storage = tmp_path / "reviews"

    assert main(
        [
            "review",
            "--fixture",
            str(fixture),
            "--requirements",
            str(requirements),
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
            "--storage-dir",
            str(storage),
        ]
    ) == 0

    review_id = json.loads(capsys.readouterr().out)["review_id"]
    state = JsonReviewStore(storage).load(review_id)
    assert state.review.repository_visibility is RepositoryVisibility.UNVERIFIED
    assert state.bundle is not None
    assert state.bundle.review.repository_visibility is RepositoryVisibility.UNVERIFIED


def test_fixture_review_metadata_reports_ci_collection_notes(tmp_path: Path, capsys) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    fixture_payload = json.loads(
        Path("evals/fixtures/complete_implementation_pr.json").read_text(encoding="utf-8")
    )
    fixture_payload["check_state"] = "unavailable"
    fixture_payload["ci_observation"] = {
        "state": "unavailable",
        "reason": "Untrusted caller text.",
        "total_check_runs": 1,
        "successful_check_runs": 1,
        "collection_complete": False,
        "collection_notes": ["GitHub check-runs response contained malformed entries"],
    }
    fixture = tmp_path / "incomplete-ci.json"
    fixture.write_text(json.dumps(fixture_payload), encoding="utf-8")

    assert main(
        [
            "review",
            "--fixture",
            str(fixture),
            "--requirements",
            str(requirements),
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
            "--storage-dir",
            str(tmp_path / "reviews"),
        ]
    ) == 0

    metadata = json.loads(capsys.readouterr().out)
    assert metadata["ci_collection_notes"] == [
        "GitHub check-runs response contained malformed entries"
    ]


def test_fixture_review_persists_fixed_public_engineering_research_context(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")

    assert main(
        [
            "review",
            "--fixture",
            "evals/fixtures/complete_implementation_pr.json",
            "--requirements",
            str(requirements),
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
            "--research-case-id",
            "R-001",
            "--storage-dir",
            str(tmp_path / "reviews"),
        ]
    ) == 0

    metadata = json.loads(capsys.readouterr().out)
    state = JsonReviewStore(tmp_path / "reviews").load(metadata["review_id"])
    assert metadata["research_case_id"] == "R-001"
    assert metadata["research_classification"] == "public_engineering_research"
    assert metadata["stage1_credit"] is False
    assert metadata["candidate_evidence_proves_correctness"] is False
    assert metadata["candidate_evidence_boundary"] == (
        "Candidate evidence does not prove correctness."
    )
    assert metadata["runtime_verification_state"] == "not_recorded"
    assert metadata["reviewer_decision_state"] == "unresolved"
    assert metadata["candidate_evidence"]
    assert set(metadata["candidate_evidence"][0]) == {
        "criterion_id",
        "evidence_type",
        "evidence_level",
    }
    assert metadata["gate_reason_codes"]
    assert "blocking_criteria" in metadata
    assert state.bundle is not None
    assert state.bundle.research_context is not None
    assert state.bundle.research_context.case_id == "R-001"


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
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
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
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
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
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
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
                "--confirmation",
                str(tmp_path / "missing-confirmation.json"),
                "--report",
                str(report),
            ]
        )

    assert raised.value.code == 2
    stderr = capsys.readouterr().err
    assert "report path already exists" in stderr
    assert "Traceback" not in stderr
    assert report.read_text(encoding="utf-8") == "keep me"


def test_review_report_final_publication_does_not_overwrite_racing_target(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    report = tmp_path / "racing.md"
    original_renderer = cli_module.EXPORT_RENDERERS["markdown"]

    def racing_renderer(state):
        rendered = original_renderer(state)
        report.write_bytes(b"owner-created bytes\n")
        return rendered

    monkeypatch.setitem(cli_module.EXPORT_RENDERERS, "markdown", racing_renderer)

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
                "--storage-dir",
                str(tmp_path / "reviews"),
                "--report",
                str(report),
            ]
        )

    assert raised.value.code == 2
    assert "already exists" in capsys.readouterr().err
    assert report.read_bytes() == b"owner-created bytes\n"
    assert not any(path.suffix == ".tmp" for path in tmp_path.iterdir())
    assert not list((tmp_path / "reviews").glob("*.json"))


def test_review_rolls_back_report_when_review_persistence_fails(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    report = tmp_path / "report.md"
    invalid_storage = tmp_path / "not-a-directory"
    invalid_storage.write_text("owner bytes\n", encoding="utf-8")

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
                "--storage-dir",
                str(invalid_storage),
                "--report",
                str(report),
            ]
        )

    assert raised.value.code == 2
    assert "review store path must be a directory" in capsys.readouterr().err
    assert not report.exists()
    assert invalid_storage.read_bytes() == b"owner bytes\n"


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_review_rollback_removes_owned_report_temporary_after_cleanup_denial(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    report = tmp_path / "report.md"
    invalid_storage = tmp_path / "not-a-directory"
    invalid_storage.write_text("owner bytes\n", encoding="utf-8")
    original_cleanup = atomic_files_module._quarantine_and_remove_at
    denied = False

    def deny_first_report_temporary_cleanup(
        directory_fd: int, name: str, *args, **kwargs
    ) -> None:
        nonlocal denied
        if name.endswith(".tmp") and not denied:
            denied = True
            raise PermissionError("simulated report temporary cleanup denial")
        original_cleanup(directory_fd, name, *args, **kwargs)

    monkeypatch.setattr(
        atomic_files_module,
        "_quarantine_and_remove_at",
        deny_first_report_temporary_cleanup,
    )

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
                "--storage-dir",
                str(invalid_storage),
                "--report",
                str(report),
            ]
        )

    assert raised.value.code == 2
    assert denied is True
    assert "review store path must be a directory" in capsys.readouterr().err
    assert not report.exists()
    assert not list(tmp_path.glob("*.tmp"))
    assert invalid_storage.read_bytes() == b"owner bytes\n"


def test_review_rolls_back_report_when_persistence_is_interrupted(
    tmp_path: Path,
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    report = tmp_path / "report.md"
    storage = tmp_path / "reviews"

    with (
        patch.object(cli_module.JsonReviewStore, "save", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
                "--storage-dir",
                str(storage),
                "--report",
                str(report),
            ]
        )

    assert not report.exists()
    assert not list(storage.glob("*.json"))


def test_review_keeps_report_when_persistence_committed_before_teardown_failure(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    report = tmp_path / "report.md"
    storage = tmp_path / "reviews"
    original_save = JsonReviewStore.save

    def commit_then_fail(store, state, **kwargs):
        original_save(store, state, **kwargs)
        raise OSError("simulated post-commit teardown failure")

    monkeypatch.setattr(JsonReviewStore, "save", commit_then_fail)

    assert (
        main(
            [
                "review",
                "--fixture",
                "evals/fixtures/complete_implementation_pr.json",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(write_requirements_confirmation(requirements)),
                "--storage-dir",
                str(storage),
                "--report",
                str(report),
            ]
        )
        == 0
    )

    metadata = json.loads(capsys.readouterr().out)
    review_id = metadata["review_id"]
    assert JsonReviewStore(storage).load(review_id).review.review_id == review_id
    assert metadata["record"] == str(storage / f"{review_id}.json")
    assert report.exists()


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
                "--confirmation",
                str(tmp_path / "missing-confirmation.json"),
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
    confirmation = write_requirements_confirmation(requirements)

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "review",
                "--pr",
                "not-a-github-pr",
                "--requirements",
                str(requirements),
                "--confirmation",
                str(confirmation),
            ]
        )

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
                "--confirmation",
                str(tmp_path / "missing-confirmation.json"),
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
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
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
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
            "--storage-dir",
            str(storage),
        ]
    )
    review_id = next(storage.glob("*.json")).stem

    assert main(["export", review_id, "--storage-dir", str(storage), "--format", "html"]) == 0
    assert "<!doctype html>" in capsys.readouterr().out.lower()


def test_export_command_serializes_with_concurrent_final_acceptance_revocation(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    store = JsonReviewStore(storage)
    accepted = new_review_state(build_demo_review())
    assert accepted.bundle is not None
    for criterion in accepted.bundle.criteria:
        accepted = append_resolution(
            accepted,
            ResolutionEvent(
                event_id=f"cli-export-accepted-{criterion.criterion_id}",
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment="CLI export concurrency fixture acceptance",
                reviewer="CLI export fixture",
            ),
        )
    accepted = append_resolution(
        accepted,
        ResolutionEvent(
            event_id="cli-export-final-acceptance",
            final_acceptance=True,
            comment="CLI export concurrency fixture final acceptance",
            reviewer="CLI export fixture",
        ),
    )
    store.save(accepted)
    renderer_entered = Event()
    release_renderer = Event()
    mutation_started = Event()
    mutation_finished = Event()
    json_renderer = cli_module.EXPORT_RENDERERS["json"]

    def blocking_renderer(state):
        renderer_entered.set()
        assert release_renderer.wait(timeout=2)
        return json_renderer(state)

    monkeypatch.setitem(cli_module.EXPORT_RENDERERS, "json", blocking_renderer)

    def revoke_final_acceptance():
        mutation_started.set()
        revoked, _ = store.mutate(
            accepted.review.review_id,
            lambda state: append_resolution(
                state,
                ResolutionEvent(
                    event_id="concurrent-cli-export-revocation",
                    final_acceptance=False,
                    comment="Concurrent revocation during CLI export",
                    reviewer="CLI reviewer",
                ),
            ),
        )
        mutation_finished.set()
        return revoked

    with ThreadPoolExecutor(max_workers=2) as executor:
        export_future = executor.submit(
            main,
            [
                "export",
                accepted.review.review_id,
                "--storage-dir",
                str(storage),
                "--format",
                "json",
            ],
        )
        try:
            assert renderer_entered.wait(timeout=2)
            mutation_future = executor.submit(revoke_final_acceptance)
            assert mutation_started.wait(timeout=2)
            assert not mutation_finished.wait(timeout=0.2)
        finally:
            release_renderer.set()
        assert export_future.result(timeout=2) == 0
        revoked = mutation_future.result(timeout=2)

    exported = json.loads(capsys.readouterr().out)
    assert exported["review"]["final_acceptance"] is True
    assert revoked.review.final_acceptance is False


def _save_demo_review(tmp_path: Path) -> tuple[Path, str]:
    storage = tmp_path / "reviews"
    state = new_review_state(build_demo_review())
    JsonReviewStore(storage).save(state)
    return storage, state.review.review_id


def test_resolve_command_appends_validated_resolution_and_reports_gate(
    tmp_path: Path, capsys
) -> None:
    storage, review_id = _save_demo_review(tmp_path)

    assert main(
        [
            "resolve",
            review_id,
            "--criterion-id",
            "AC-01",
            "--decision",
            HumanDecision.ACCEPTED.value,
            "--reviewer",
            "CLI reviewer",
            "--storage-dir",
            str(storage),
        ]
    ) == 0

    payload = LifecycleMutationMetadata.model_validate_json(
        capsys.readouterr().out
    ).model_dump(mode="json")
    saved = JsonReviewStore(storage).load(review_id)
    assert payload["review_id"] == review_id
    assert payload["head_sha"] == saved.review.head_sha
    assert payload["event_id"] == saved.resolution_events[-1].event_id
    assert payload["verdict"] == saved.bundle.gate.verdict.value
    assert payload["gate_reason_codes"] == saved.bundle.gate.reason_codes
    assert saved.bundle.resolutions[0].decision is HumanDecision.ACCEPTED
    assert saved.bundle.resolutions[0].reviewer == "CLI reviewer"


def test_resolve_command_rejects_manual_verification_without_mutation(
    tmp_path: Path, capsys
) -> None:
    storage, review_id = _save_demo_review(tmp_path)
    record = storage / f"{review_id}.json"
    before = record.read_bytes()

    with pytest.raises(SystemExit) as error:
        main(
            [
                "resolve",
                review_id,
                "--criterion-id",
                "AC-01",
                "--decision",
                HumanDecision.MANUALLY_VERIFIED.value,
                "--reviewer",
                "CLI reviewer",
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "manually_verified" in capsys.readouterr().err
    assert record.read_bytes() == before


def test_resolve_command_requires_comment_for_low_evidence_acceptance_atomically(
    tmp_path: Path, capsys
) -> None:
    storage, review_id = _save_demo_review(tmp_path)
    record = storage / f"{review_id}.json"
    before = record.read_bytes()

    with pytest.raises(SystemExit) as error:
        main(
            [
                "resolve",
                review_id,
                "--criterion-id",
                "AC-03",
                "--decision",
                HumanDecision.ACCEPTED.value,
                "--reviewer",
                "CLI reviewer",
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "reviewer comment" in capsys.readouterr().err
    assert record.read_bytes() == before


def test_verify_runtime_command_atomically_appends_matching_evidence_and_resolution(
    tmp_path: Path, capsys
) -> None:
    storage, review_id = _save_demo_review(tmp_path)
    comment = tmp_path / "runtime-comment.txt"
    comment.write_text("Observed the constructed export scenario.", encoding="utf-8")

    assert main(
        [
            "verify-runtime",
            review_id,
            "--criterion-id",
            "AC-03",
            "--level",
            EvidenceLevel.E3.value,
            "--reviewer",
            "Runtime reviewer",
            "--artifact-reference",
            "https://example.test/runtime/42",
            "--scenario",
            "Exercise the missing-evidence behavior",
            "--environment",
            "local constructed fixture",
            "--result",
            "Observed expected behavior",
            "--comment-file",
            str(comment),
            "--limitation",
            "Constructed fixture only",
            "--limitation",
            "No target code executed",
            "--storage-dir",
            str(storage),
        ]
    ) == 0

    payload = LifecycleMutationMetadata.model_validate_json(
        capsys.readouterr().out
    ).model_dump(mode="json")
    saved = JsonReviewStore(storage).load(review_id)
    runtime = saved.bundle.runtime_evidence[0]
    resolution = next(
        item for item in saved.bundle.resolutions if item.criterion_id == "AC-03"
    )
    assert payload["event_id"] == saved.resolution_events[-1].event_id
    assert runtime.runtime_evidence_id == resolution.runtime_evidence_id
    assert runtime.repository == saved.review.repository
    assert runtime.pr_number == saved.review.pr_number
    assert runtime.head_sha == saved.review.head_sha
    assert runtime.reviewer == resolution.reviewer == "Runtime reviewer"
    assert runtime.limitations == ["Constructed fixture only", "No target code executed"]
    assert resolution.decision is HumanDecision.MANUALLY_VERIFIED
    assert resolution.claimed_evidence_level is EvidenceLevel.E3


@pytest.mark.parametrize(
    ("criterion_id", "level", "comment_text"),
    [
        ("AC-03", EvidenceLevel.E2.value, "Observed scenario"),
        ("AC-99", EvidenceLevel.E3.value, "Observed scenario"),
        ("AC-03", EvidenceLevel.E3.value, "   \n"),
    ],
)
def test_verify_runtime_command_rejects_invalid_input_without_mutation(
    tmp_path: Path,
    capsys,
    criterion_id: str,
    level: str,
    comment_text: str,
) -> None:
    storage, review_id = _save_demo_review(tmp_path)
    record = storage / f"{review_id}.json"
    before = record.read_bytes()
    comment = tmp_path / "runtime-comment.txt"
    comment.write_text(comment_text, encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "verify-runtime",
                review_id,
                "--criterion-id",
                criterion_id,
                "--level",
                level,
                "--reviewer",
                "Runtime reviewer",
                "--artifact-reference",
                "https://example.test/runtime/42",
                "--scenario",
                "Exercise the scenario",
                "--environment",
                "local constructed fixture",
                "--result",
                "Observed expected behavior",
                "--comment-file",
                str(comment),
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "Traceback" not in capsys.readouterr().err
    assert record.read_bytes() == before


def _save_final_acceptance_ready_review(tmp_path: Path) -> tuple[Path, str]:
    storage = tmp_path / "reviews"
    state = new_review_state(build_demo_review())
    for criterion in state.bundle.criteria:
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id=criterion.criterion_id,
                decision=(
                    HumanDecision.ACCEPTED
                    if criterion.criterion_id in {"AC-01", "AC-02"}
                    else HumanDecision.ACCEPTED_EXCEPTION
                ),
                comment="Reviewed the criterion and its explicit evidence boundary.",
                reviewer="Fixture reviewer",
            ),
        )
    JsonReviewStore(storage).save(state)
    return storage, state.review.review_id


def test_final_acceptance_command_accepts_and_revokes_through_lifecycle(
    tmp_path: Path, capsys
) -> None:
    storage, review_id = _save_final_acceptance_ready_review(tmp_path)

    assert main(
        [
            "final-acceptance",
            review_id,
            "--accept",
            "--reviewer",
            "Final reviewer",
            "--storage-dir",
            str(storage),
        ]
    ) == 0
    accepted_payload = LifecycleMutationMetadata.model_validate_json(
        capsys.readouterr().out
    ).model_dump(mode="json")
    accepted = JsonReviewStore(storage).load(review_id)
    assert accepted.review.final_acceptance is True
    assert accepted_payload["event_id"] == accepted.resolution_events[-1].event_id

    assert main(
        [
            "final-acceptance",
            review_id,
            "--revoke",
            "--reviewer",
            "Final reviewer",
            "--storage-dir",
            str(storage),
        ]
    ) == 0
    revoked_payload = LifecycleMutationMetadata.model_validate_json(
        capsys.readouterr().out
    ).model_dump(mode="json")
    revoked = JsonReviewStore(storage).load(review_id)
    assert revoked.review.final_acceptance is False
    assert revoked_payload["event_id"] == revoked.resolution_events[-1].event_id


def test_final_acceptance_command_rejects_premature_acceptance_without_mutation(
    tmp_path: Path, capsys
) -> None:
    storage, review_id = _save_demo_review(tmp_path)
    record = storage / f"{review_id}.json"
    before = record.read_bytes()

    with pytest.raises(SystemExit) as error:
        main(
            [
                "final-acceptance",
                review_id,
                "--accept",
                "--reviewer",
                "Final reviewer",
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "prerequisites" in capsys.readouterr().err
    assert record.read_bytes() == before


def test_final_acceptance_command_requires_exactly_one_action(
    tmp_path: Path, capsys
) -> None:
    storage, review_id = _save_demo_review(tmp_path)

    with pytest.raises(SystemExit) as missing:
        main(
            [
                "final-acceptance",
                review_id,
                "--reviewer",
                "Final reviewer",
                "--storage-dir",
                str(storage),
            ]
        )
    assert missing.value.code == 2
    assert "one of the arguments --accept --revoke is required" in capsys.readouterr().err

    with pytest.raises(SystemExit) as conflicting:
        main(
            [
                "final-acceptance",
                review_id,
                "--accept",
                "--revoke",
                "--reviewer",
                "Final reviewer",
                "--storage-dir",
                str(storage),
            ]
        )
    assert conflicting.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


@pytest.mark.parametrize(
    "command_name",
    ["resolve", "verify-runtime", "final-acceptance", "compare"],
)
def test_lifecycle_commands_reject_malformed_record_envelope_without_traceback(
    tmp_path: Path,
    capsys,
    command_name: str,
) -> None:
    storage = tmp_path / "reviews"
    storage.mkdir()
    record = storage / "broken-review.json"
    record.write_text('{"record_version": 4}', encoding="utf-8")
    before = record.read_bytes()
    comment = tmp_path / "comment.txt"
    comment.write_text("Constructed reviewer note", encoding="utf-8")
    commands = {
        "resolve": [
            "resolve",
            "broken-review",
            "--criterion-id",
            "AC-01",
            "--decision",
            HumanDecision.REJECTED_FINDING.value,
            "--reviewer",
            "CLI reviewer",
        ],
        "verify-runtime": [
            "verify-runtime",
            "broken-review",
            "--criterion-id",
            "AC-01",
            "--level",
            EvidenceLevel.E3.value,
            "--reviewer",
            "CLI reviewer",
            "--artifact-reference",
            "https://example.test/runtime/42",
            "--scenario",
            "Constructed scenario",
            "--environment",
            "Constructed environment",
            "--result",
            "Constructed result",
            "--comment-file",
            str(comment),
        ],
        "final-acceptance": [
            "final-acceptance",
            "broken-review",
            "--revoke",
            "--reviewer",
            "CLI reviewer",
        ],
        "compare": ["compare", "broken-review", "broken-review"],
    }

    with pytest.raises(SystemExit) as error:
        main([*commands[command_name], "--storage-dir", str(storage)])

    stderr = capsys.readouterr().err
    assert error.value.code == 2
    assert "record envelope" in stderr
    assert "Traceback" not in stderr
    assert record.read_bytes() == before


def _save_comparison_reviews(tmp_path: Path) -> tuple[Path, str, str]:
    storage = tmp_path / "reviews"
    store = JsonReviewStore(storage)
    previous = new_review_state(
        build_review_from_paths(
            Path("evals/comparisons/previous_pr.json"),
            Path("evals/comparisons/previous_labels.json"),
        )
    )
    current = new_review_state(
        build_review_from_paths(
            Path("evals/comparisons/current_pr.json"),
            Path("evals/comparisons/current_labels.json"),
        )
    )
    store.save(previous)
    store.save(current)
    return storage, previous.review.review_id, current.review.review_id


def test_compare_command_writes_validated_json_to_stdout_without_mutating_reviews(
    tmp_path: Path, capsys
) -> None:
    storage, previous_id, current_id = _save_comparison_reviews(tmp_path)
    previous_record = storage / f"{previous_id}.json"
    current_record = storage / f"{current_id}.json"
    before = (previous_record.read_bytes(), current_record.read_bytes())

    assert main(
        [
            "compare",
            previous_id,
            current_id,
            "--storage-dir",
            str(storage),
        ]
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["previous_head_sha"] == "constructed-previous-001"
    assert payload["current_head_sha"] == "constructed-current-001"
    assert payload["evidence_change_counts"] == {
        "added": 3,
        "modified": 1,
        "relocated": 1,
        "removed": 3,
        "unchanged": 0,
    }
    assert previous_record.read_bytes() == before[0]
    assert current_record.read_bytes() == before[1]


@pytest.mark.parametrize("compare_same_review", [False, True])
def test_compare_command_serializes_snapshot_with_concurrent_lifecycle_mutation(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
    compare_same_review: bool,
) -> None:
    storage, previous_id, current_id = _save_comparison_reviews(tmp_path)
    if compare_same_review:
        current_id = previous_id
    store = JsonReviewStore(storage)
    renderer_entered = Event()
    release_renderer = Event()
    mutation_started = Event()
    mutation_finished = Event()
    json_renderer = cli_module.COMPARISON_RENDERERS["json"]

    def blocking_renderer(comparison):
        renderer_entered.set()
        assert release_renderer.wait(timeout=2)
        return json_renderer(comparison)

    monkeypatch.setitem(cli_module.COMPARISON_RENDERERS, "json", blocking_renderer)

    def mutate_current_review():
        mutation_started.set()
        updated, _ = store.mutate(
            current_id,
            lambda state: append_resolution(
                state,
                ResolutionEvent(
                    event_id=f"concurrent-compare-resolution-{compare_same_review}",
                    criterion_id="AC-01",
                    decision=HumanDecision.ACCEPTED,
                    comment="Concurrent lifecycle mutation during CLI comparison",
                    reviewer="CLI comparison fixture",
                ),
            ),
        )
        mutation_finished.set()
        return updated

    with ThreadPoolExecutor(max_workers=2) as executor:
        compare_future = executor.submit(
            main,
            [
                "compare",
                previous_id,
                current_id,
                "--storage-dir",
                str(storage),
            ],
        )
        try:
            assert renderer_entered.wait(timeout=2)
            mutation_future = executor.submit(mutate_current_review)
            assert mutation_started.wait(timeout=2)
            assert not mutation_finished.wait(timeout=0.2)
        finally:
            release_renderer.set()
        assert compare_future.result(timeout=2) == 0
        updated = mutation_future.result(timeout=2)

    comparison = json.loads(capsys.readouterr().out)
    assert comparison["changed_human_resolutions"] == []
    assert updated.resolution_events[-1].decision is HumanDecision.ACCEPTED


def test_compare_command_writes_markdown_and_refuses_overwrite(
    tmp_path: Path, capsys
) -> None:
    storage, previous_id, current_id = _save_comparison_reviews(tmp_path)
    output = tmp_path / "comparison.md"

    assert main(
        [
            "compare",
            previous_id,
            current_id,
            "--format",
            "markdown",
            "--output",
            str(output),
            "--storage-dir",
            str(storage),
        ]
    ) == 0
    assert capsys.readouterr().out == ""
    report = output.read_text(encoding="utf-8")
    assert "# ScopeProof Re-review Comparison" in report
    assert "Candidate comparison does not prove criterion satisfaction" in report

    before = output.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(
            [
                "compare",
                previous_id,
                current_id,
                "--format",
                "markdown",
                "--output",
                str(output),
                "--storage-dir",
                str(storage),
            ]
        )
    assert error.value.code == 2
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == before


def test_compare_command_rejects_review_without_active_bundle(
    tmp_path: Path, capsys
) -> None:
    storage, previous_id, current_id = _save_comparison_reviews(tmp_path)
    store = JsonReviewStore(storage)
    current = store.load(current_id)
    pending = revise_criteria(
        current,
        [Criterion(criterion_id="AC-01", text="Revised criterion")],
        "Revised criterion",
    )
    store.save(pending)
    before = (storage / f"{current_id}.json").read_bytes()

    with pytest.raises(SystemExit) as error:
        main(
            [
                "compare",
                previous_id,
                current_id,
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "active analysis" in capsys.readouterr().err
    assert (storage / f"{current_id}.json").read_bytes() == before


@pytest.mark.parametrize(
    ("identity_update", "identity_value", "message"),
    [
        ("repository", "other/widget", "same repository"),
        ("pr_number", 999, "same pull request"),
    ],
)
def test_compare_command_rejects_reviews_from_different_pull_requests(
    tmp_path: Path,
    capsys,
    identity_update: str,
    identity_value: str | int,
    message: str,
) -> None:
    storage, previous_id, current_id = _save_comparison_reviews(tmp_path)
    store = JsonReviewStore(storage)
    current = store.load(current_id)
    assert current.bundle is not None
    current_review = current.review.model_copy(
        update={identity_update: identity_value}
    )
    current_bundle = current.bundle.model_copy(
        update={"review": current_review.model_copy(deep=True)}
    )
    mismatched = current.model_copy(
        update={"review": current_review, "bundle": current_bundle}
    )
    store.save(mismatched)
    before = {
        review_id: (storage / f"{review_id}.json").read_bytes()
        for review_id in (previous_id, current_id)
    }
    output = tmp_path / "unrelated-comparison.json"

    with pytest.raises(SystemExit) as error:
        main(
            [
                "compare",
                previous_id,
                current_id,
                "--output",
                str(output),
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert message in capsys.readouterr().err
    assert not output.exists()
    assert {
        review_id: (storage / f"{review_id}.json").read_bytes()
        for review_id in (previous_id, current_id)
    } == before


@pytest.mark.parametrize(
    ("criterion_update", "criterion_value"),
    [
        ("text", "Revised confirmed criterion"),
        ("required_evidence_level", EvidenceLevel.E3),
    ],
)
def test_compare_command_rejects_different_confirmed_criterion_definitions(
    tmp_path: Path,
    capsys,
    criterion_update: str,
    criterion_value: str | EvidenceLevel,
) -> None:
    storage, previous_id, current_id = _save_comparison_reviews(tmp_path)
    store = JsonReviewStore(storage)
    current = store.load(current_id)
    assert current.bundle is not None
    revised_criteria = [item.model_copy(deep=True) for item in current.bundle.criteria]
    revised_criteria[0] = revised_criteria[0].model_copy(
        update={criterion_update: criterion_value}
    )
    revised_source = "\n".join(item.text for item in revised_criteria)
    pending = revise_criteria(current, revised_criteria, revised_source)
    confirmed = confirm_criteria(
        pending,
        build_criteria_source_provenance(
            source_uri="https://example.test/revised-requirements",
            source_revision="revised-v2",
            source_text=revised_source,
            criteria=revised_criteria,
            confirmed_by="Comparison fixture owner",
            confirmed_at=pending.criteria_revision.created_at + timedelta(seconds=1),
        ),
    )
    incoming = current.bundle.model_copy(
        update={
            "review": confirmed.review.model_copy(deep=True),
            "source_text": revised_source,
            "criteria": [item.model_copy(deep=True) for item in revised_criteria],
            "gate": evaluate_gate(
                confirmed.review,
                revised_criteria,
                current.bundle.findings,
                [],
            ),
        },
        deep=True,
    )
    reanalyzed = attach_analysis(confirmed, incoming)
    store.save(reanalyzed)
    before = {
        review_id: (storage / f"{review_id}.json").read_bytes()
        for review_id in (previous_id, current_id)
    }
    output = tmp_path / "criterion-mismatch-comparison.json"

    with pytest.raises(SystemExit) as error:
        main(
            [
                "compare",
                previous_id,
                current_id,
                "--output",
                str(output),
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "identical ordered criterion definitions" in capsys.readouterr().err
    assert not output.exists()
    assert {
        review_id: (storage / f"{review_id}.json").read_bytes()
        for review_id in (previous_id, current_id)
    } == before


@pytest.mark.parametrize(
    ("invalid_relationship", "message"),
    [
        ("criterion_order", "identical ordered criterion definitions"),
        ("criteria_source", "compatible criteria-source provenance"),
        ("candidate_head", "evidence candidates must match the reviewed head"),
        ("live_head", "exact head SHAs"),
    ],
)
def test_compare_command_uses_core_relationship_validator_before_render_or_output(
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
    invalid_relationship: str,
    message: str,
) -> None:
    storage, previous_id, current_id = _save_comparison_reviews(tmp_path)
    store = JsonReviewStore(storage)
    current = store.load(current_id)
    assert current.bundle is not None
    review = current.review.model_copy(deep=True)
    bundle = current.bundle.model_copy(deep=True)
    criteria_revision = current.criteria_revision.model_copy(deep=True)

    if invalid_relationship == "criterion_order":
        criteria = list(reversed(bundle.criteria))
        provenance = review.criteria_source_provenance
        assert provenance is not None
        revised_provenance = build_criteria_source_provenance(
            source_uri=provenance.source_uri,
            source_revision=provenance.source_revision,
            source_text=bundle.source_text,
            criteria=criteria,
            confirmed_by=provenance.confirmed_by,
            confirmed_at=provenance.confirmed_at,
        )
        review = review.model_copy(
            update={"criteria_source_provenance": revised_provenance}
        )
        bundle = bundle.model_copy(
            update={
                "review": review.model_copy(deep=True),
                "criteria": criteria,
            }
        )
        criteria_revision = criteria_revision.model_copy(
            update={
                "criteria": criteria,
                "source_provenance": revised_provenance,
            }
        )
    elif invalid_relationship == "criteria_source":
        provenance = review.criteria_source_provenance
        assert provenance is not None
        revised_provenance = provenance.model_copy(
            update={"source_uri": "https://example.test/changed-requirements"}
        )
        review = review.model_copy(
            update={"criteria_source_provenance": revised_provenance}
        )
        bundle = bundle.model_copy(
            update={"review": review.model_copy(deep=True)}
        )
        criteria_revision = criteria_revision.model_copy(
            update={"source_provenance": revised_provenance}
        )
    elif invalid_relationship == "candidate_head":
        evidence = [item.model_copy(deep=True) for item in bundle.evidence]
        evidence[0] = evidence[0].model_copy(update={"commit_sha": "unrelated-head"})
        bundle = bundle.model_copy(update={"evidence": evidence})
    else:
        review = review.model_copy(
            update={
                "input_origin": ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
                "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            }
        )
        bundle = bundle.model_copy(
            update={"review": review.model_copy(deep=True)}
        )

    store.save(
        current.model_copy(
            update={
                "review": review,
                "criteria_revision": criteria_revision,
                "bundle": bundle,
            }
        )
    )
    before = {
        review_id: (storage / f"{review_id}.json").read_bytes()
        for review_id in (previous_id, current_id)
    }
    output = tmp_path / "ineligible-comparison.json"
    renderer_called = False

    def unexpected_renderer(_comparison):
        nonlocal renderer_called
        renderer_called = True
        return "unexpected"

    monkeypatch.setitem(cli_module.COMPARISON_RENDERERS, "json", unexpected_renderer)

    with pytest.raises(SystemExit) as error:
        main(
            [
                "compare",
                previous_id,
                current_id,
                "--output",
                str(output),
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert message in capsys.readouterr().err
    assert renderer_called is False
    assert not output.exists()
    assert {
        review_id: (storage / f"{review_id}.json").read_bytes()
        for review_id in (previous_id, current_id)
    } == before


def test_export_command_migrates_raw_v2_runtime_verification_fail_closed(
    tmp_path: Path, capsys
) -> None:
    storage = tmp_path / "reviews"
    store = JsonReviewStore(storage)
    state = new_review_state(build_demo_review())
    runtime_item = RuntimeEvidence(
        runtime_evidence_id="pre-migration-runtime",
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="https://example.test/runtime/v2",
        scenario="Exercise the export scenario",
        environment="staging",
        result="observed passing",
        reviewer="Migration QA",
        evidence_level=EvidenceLevel.E3,
    )
    state = append_external_verification(
        state,
        runtime_item,
        ResolutionEvent(
            event_id="pre-migration-manual-event",
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Observed the export scenario",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=runtime_item.runtime_evidence_id,
            reviewer=runtime_item.reviewer,
        ),
    )
    for criterion in state.bundle.criteria:
        if criterion.criterion_id == "AC-01":
            continue
        state = append_resolution(
            state,
            ResolutionEvent(
                event_id=f"accepted-{criterion.criterion_id}",
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment="Reviewed the candidate evidence",
            ),
        )
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="pre-migration-final-acceptance",
            final_acceptance=True,
            comment="Accepted before provenance migration",
        ),
    )
    path = store.save(state)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["record_version"] = 2
    for item in record["state"]["bundle"]["runtime_evidence"]:
        for field_name in (
            "runtime_evidence_id",
            "repository",
            "pr_number",
            "head_sha",
        ):
            item.pop(field_name)
    for resolution in record["state"]["bundle"]["resolutions"]:
        resolution.pop("runtime_evidence_id", None)
    for event in record["state"]["resolution_events"]:
        event.pop("runtime_evidence_id", None)
    path.write_text(json.dumps(record), encoding="utf-8")

    assert main(
        ["export", state.review.review_id, "--storage-dir", str(storage), "--format", "json"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    migrated_bundle = payload["bundle"]
    migrated_runtime = migrated_bundle["runtime_evidence"][0]
    assert migrated_bundle["gate"]["verdict"] == "needs_review"
    assert "runtime_verification_reconfirmation_required" in migrated_bundle["gate"][
        "reason_codes"
    ]
    assert migrated_runtime["runtime_evidence_id"]
    assert (
        migrated_runtime["repository"],
        migrated_runtime["pr_number"],
        migrated_runtime["head_sha"],
    ) == (
        migrated_bundle["review"]["repository"],
        migrated_bundle["review"]["pr_number"],
        migrated_bundle["review"]["head_sha"],
    )
    manual_resolution = next(
        item
        for item in migrated_bundle["resolutions"]
        if item["decision"] == "manually_verified"
    )
    manual_event = next(
        item
        for item in payload["resolution_events"]
        if item["decision"] == "manually_verified"
    )
    assert manual_resolution["runtime_evidence_id"] is None
    assert manual_event["runtime_evidence_id"] is None


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
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
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
            "--confirmation",
            str(write_requirements_confirmation(requirements)),
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
    confirmation = write_requirements_confirmation(requirements)

    assert main(
        [
            "validate-requirements-confirmation",
            "--requirements",
            str(requirements),
            "--confirmation",
            str(confirmation),
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["confirmed_by"] == "Demo owner"
    assert output["source_uri"] == "https://example.test/requirements"
    assert set(output) == {
        "source_uri",
        "source_revision",
        "source_text_sha256",
        "normalized_criteria_sha256",
        "confirmed_by",
        "confirmed_at",
    }


def test_requirements_confirmation_command_rejects_blank_confirmer(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Document the demo.\n", encoding="utf-8")
    confirmation = write_requirements_confirmation(requirements)
    payload = json.loads(confirmation.read_text(encoding="utf-8"))
    payload["confirmed_by"] = "   "
    confirmation.write_text(json.dumps(payload), encoding="utf-8")

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


def test_prepare_requirements_confirmation_hashes_exact_bytes(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    raw = b"Export CSV\r\nShow an error state\r\n"
    requirements.write_bytes(raw)
    output = tmp_path / "confirmation.json"

    assert main(
        [
            "prepare-requirements-confirmation",
            "--requirements",
            str(requirements),
            "--source-uri",
            "https://github.com/acme/repo/issues/6",
            "--source-revision",
            "issue-6@abc123",
            "--confirmed-by",
            "Repository owner",
            "--output",
            str(output),
        ]
    ) == 0

    printed = json.loads(capsys.readouterr().out)
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert printed["confirmation"] == str(output)
    assert printed["source_text_sha256"] == sha256(raw).hexdigest()
    assert stored["source_text_sha256"] == sha256(raw).hexdigest()
    assert stored["confirmed_by"] == "Repository owner"
    assert main(
        [
            "validate-requirements-confirmation",
            "--requirements",
            str(requirements),
            "--confirmation",
            str(output),
        ]
    ) == 0


def test_prepare_requirements_confirmation_refuses_overwrite(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    output = tmp_path / "confirmation.json"
    output.write_text("preserve me\n", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "prepare-requirements-confirmation",
                "--requirements",
                str(requirements),
                "--source-uri",
                "https://github.com/acme/repo/issues/6",
                "--confirmed-by",
                "Repository owner",
                "--output",
                str(output),
            ]
        )

    assert error.value.code == 2
    assert output.read_text(encoding="utf-8") == "preserve me\n"
    assert capsys.readouterr().out == ""


def test_prepare_requirements_confirmation_rejects_secret_bearing_uri(
    tmp_path: Path, capsys
) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "prepare-requirements-confirmation",
                "--requirements",
                str(requirements),
                "--source-uri",
                "https://example.com/requirements?token=secret",
                "--confirmed-by",
                "Repository owner",
                "--output",
                str(tmp_path / "confirmation.json"),
            ]
        )

    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "secret" not in captured.err
    assert captured.out == ""


def _initialize_alpha_case(tmp_path: Path, capsys) -> tuple[Path, str, Path, str]:
    requirements = tmp_path / "alpha-requirements.txt"
    requirements.write_text("Export CSV\nShow an error state\n", encoding="utf-8")
    confirmation = write_requirements_confirmation(
        requirements, source_uri="https://github.com/acme/repo/issues/6"
    )
    store = tmp_path / "alpha-cases"
    verified_snapshot = PullRequestSnapshot(
        repository="acme/repo",
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        pr_number=7,
        title="Export CSV",
        html_url="https://github.com/acme/repo/pull/7",
        base_sha="b" * 40,
        head_sha="a" * 40,
    )
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=verified_snapshot,
    ):
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
                "--confirmation",
                str(confirmation),
                "--source-owner-confirmed",
                "--confirmed-no-confidential-information",
                "--storage-dir",
                str(store),
            ]
        ) == 0
    case_id = json.loads(capsys.readouterr().out)["case_id"]
    criteria = [
        Criterion(criterion_id=draft.criterion_id, text=draft.text)
        for draft in parse_criteria(requirements.read_text(encoding="utf-8"))
    ]
    provenance = CriteriaSourceProvenance.model_validate_json(
        confirmation.read_text(encoding="utf-8")
    )
    snapshot = PullRequestSnapshot(
        repository="acme/repo",
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        pr_number=7,
        title="Export CSV",
        html_url="https://github.com/acme/repo/pull/7",
        base_sha="b" * 40,
        head_sha="a" * 40,
    )
    review_state = new_review_state(
        _build_bundle(
            snapshot,
            criteria,
            requirements.read_text(encoding="utf-8"),
            provenance,
            input_origin=ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
        )
    )
    review_store = tmp_path / "reviews"
    JsonReviewStore(review_store).save(review_state)
    return store, case_id, review_store, review_state.review.review_id


def test_alpha_init_rejects_unverified_repository_without_saving(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    requirements = tmp_path / "alpha-requirements.txt"
    requirements.write_text("Export CSV\n", encoding="utf-8")
    confirmation = write_requirements_confirmation(
        requirements, source_uri="https://github.com/acme/repo/issues/6"
    )
    monkeypatch.setattr(
        "scopeproof_core.cli.GitHubClient.fetch_pull_request",
        lambda _self, _pr: PullRequestSnapshot(
            repository="acme/repo",
            pr_number=7,
            title="Export CSV",
            html_url="https://github.com/acme/repo/pull/7",
            base_sha="b" * 40,
            head_sha="a" * 40,
        ),
    )
    storage = tmp_path / "alpha-cases"

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
                "--confirmation",
                str(confirmation),
                "--source-owner-confirmed",
                "--confirmed-no-confidential-information",
                "--storage-dir",
                str(storage),
            ]
        )

    assert error.value.code == 2
    assert "verified public" in capsys.readouterr().err
    assert not storage.exists()


def test_alpha_init_creates_validated_local_record(tmp_path: Path, capsys) -> None:
    store_dir, case_id, _, _ = _initialize_alpha_case(tmp_path, capsys)

    record = JsonAlphaCaseStore(store_dir).load(case_id)

    assert record.confirmed_criteria == ["Export CSV", "Show an error state"]
    assert record.source_owner_confirmed is True
    assert record.no_confidential_information is True
    assert record.repository_visibility is RepositoryVisibility.VERIFIED_PUBLIC
    assert record.criteria_source_provenance is not None
    assert record.criteria_source_provenance.source_uri == (
        "https://github.com/acme/repo/issues/6"
    )


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
    store_dir, case_id, review_store, review_id = _initialize_alpha_case(
        tmp_path, capsys
    )
    notes = tmp_path / "outcome.txt"
    notes.write_text("The report showed only information already known.\n", encoding="utf-8")

    assert main(
        [
            "alpha",
            "outcome",
            case_id,
            "--review-id",
            review_id,
            "--review-storage-dir",
            str(review_store),
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
    store_dir, case_id, review_store, review_id = _initialize_alpha_case(
        tmp_path, capsys
    )
    assert main(
        [
            "alpha",
            "outcome",
            case_id,
            "--review-id",
            review_id,
            "--review-storage-dir",
            str(review_store),
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
    store_dir, case_id, review_store, review_id = _initialize_alpha_case(
        tmp_path, capsys
    )

    with pytest.raises(SystemExit) as error:
        main(
            [
                "alpha",
                "outcome",
                case_id,
                "--review-id",
                review_id,
                "--review-storage-dir",
                str(review_store),
                "--result",
                "created_friction",
                "--storage-dir",
                str(store_dir),
            ]
        )

    assert error.value.code == 2
    assert "friction stage" in capsys.readouterr().err
