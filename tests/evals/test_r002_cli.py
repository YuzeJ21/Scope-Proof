"""Command-boundary tests for the opt-in R-002 module."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from scopeproof_core.evals import r002_swebench
from scopeproof_core.evals.r002_cache import R002CacheError
from scopeproof_core.evals.r002_models import (
    R002AnnotationError,
    R002CommandFailure,
    R002SourceError,
    canonical_json_bytes,
)
from scopeproof_core.evals.r002_prepare import (
    R002NetworkPolicyError,
    R002PreparationError,
)
from scopeproof_core.evals.r002_runner import R002RunError


class _DummyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    executed_case_count: int = 20
    unexpected_ready_count: int = 0
    hard_gate_errors: tuple[str, ...] = ()


def _pack_root(tmp_path: Path, *, criteria: bool = True, labels: bool = True) -> Path:
    root = tmp_path / "r002"
    root.mkdir()
    (root / "source_manifest.json").write_text("{}", encoding="utf-8")
    if criteria:
        (root / "criteria.json").write_text("{}", encoding="utf-8")
    if labels:
        (root / "candidate_labels.json").write_text("{}", encoding="utf-8")
    return root


def test_run_is_offline_canonical_and_does_not_import_pyarrow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root = _pack_root(tmp_path)
    expected = _DummyResult()
    monkeypatch.setattr(r002_swebench, "bundled_r002_root", lambda: root)
    monkeypatch.setattr(
        r002_swebench,
        "resolve_scopeproof_commit",
        lambda *_args, **_kwargs: "a" * 40,
    )
    monkeypatch.setattr(r002_swebench, "run_r002", lambda **_kwargs: expected)
    monkeypatch.setattr(
        httpx.Client,
        "send",
        lambda *_args, **_kwargs: pytest.fail("network used"),
    )
    monkeypatch.setitem(sys.modules, "pyarrow", None)

    assert (
        r002_swebench.main(
            [
                "run",
                "--cache-dir",
                str(tmp_path / "cache"),
                "--scopeproof-commit",
                "a" * 40,
            ]
        )
        == 0
    )
    output = capsysbinary.readouterr().out
    assert output == canonical_json_bytes(expected)
    assert not output.endswith(b"\n")
    assert json.loads(output)["executed_case_count"] == 20


@pytest.mark.parametrize(
    ("argv", "missing", "reason"),
    (
        (["run"], "source", "source_manifest_missing"),
        (["run"], "criteria", "criteria_missing"),
        (["run"], "labels", "labels_missing"),
    ),
)
def test_missing_pack_inputs_are_bounded_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    missing: str,
    reason: str,
) -> None:
    if missing == "source":
        root = tmp_path / "absent"
    else:
        root = _pack_root(
            tmp_path,
            criteria=missing != "criteria",
            labels=missing != "labels",
        )
    monkeypatch.setattr(r002_swebench, "bundled_r002_root", lambda: root)

    assert r002_swebench.main(argv) == 2
    failure = R002CommandFailure.model_validate_json(capsys.readouterr().out)
    assert failure.reason_code == reason
    assert failure.errors == (reason,)
    assert str(root) not in failure.model_dump_json()


def test_prepare_phases_are_the_only_transport_routed_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root = _pack_root(tmp_path)
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))
    calls: list[tuple[str, object]] = []
    expected = _DummyResult()
    monkeypatch.setattr(r002_swebench, "bundled_r002_root", lambda: root)
    monkeypatch.setattr(
        r002_swebench,
        "prepare_criteria_sources",
        lambda **kwargs: calls.append(("criteria", kwargs["transport"])) or expected,
    )
    monkeypatch.setattr(
        r002_swebench,
        "prepare_r002",
        lambda **kwargs: calls.append(("evidence", kwargs["transport"])) or expected,
    )
    monkeypatch.setattr(
        r002_swebench,
        "annotate_r002",
        lambda **_kwargs: expected,
    )

    assert (
        r002_swebench.main(
            ["prepare", "--phase", "criteria-sources"],
            transport=transport,
        )
        == 0
    )
    capsysbinary.readouterr()
    assert (
        r002_swebench.main(
            ["prepare", "--phase", "evidence"],
            transport=transport,
        )
        == 0
    )
    capsysbinary.readouterr()
    assert calls == [("criteria", transport), ("evidence", transport)]


@pytest.mark.parametrize(
    "argv",
    (
        [],
        ["prepare"],
        ["run", "--scopeproof-commit", "BAD"],
    ),
)
def test_argparse_errors_remain_pre_dispatch_stderr(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit, match="2"):
        r002_swebench.main(argv)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err


def test_argparse_help_is_standard_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit, match="0"):
        r002_swebench.main(["--help"])
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert captured.err == ""


def test_resolve_scopeproof_commit_requires_clean_exact_head(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(
        ["git", "-C", str(checkout), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(checkout), "config", "user.name", "Test"],
        check=True,
    )
    tracked = checkout / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(checkout), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(checkout), "commit", "-qm", "init"], check=True)
    head = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert (
        r002_swebench.resolve_scopeproof_commit(
            head,
            checkout_root=checkout,
        )
        == head
    )
    with pytest.raises(R002RunError, match="scopeproof_commit_mismatch"):
        r002_swebench.resolve_scopeproof_commit(
            "b" * 40,
            checkout_root=checkout,
        )
    (checkout / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(R002RunError, match="scopeproof_checkout_dirty"):
        r002_swebench.resolve_scopeproof_commit(
            head,
            checkout_root=checkout,
        )


def test_internal_failure_is_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _pack_root(tmp_path)
    monkeypatch.setattr(r002_swebench, "bundled_r002_root", lambda: root)
    monkeypatch.setattr(
        r002_swebench,
        "resolve_scopeproof_commit",
        lambda *_args, **_kwargs: "a" * 40,
    )
    monkeypatch.setattr(
        r002_swebench,
        "run_r002",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("secret body and local path")),
    )

    assert r002_swebench.main(["run"]) == 3
    output = capsys.readouterr().out
    failure = R002CommandFailure.model_validate_json(output)
    assert failure.reason_code == "internal_error"
    assert "secret" not in output
    assert str(tmp_path) not in output


@pytest.mark.parametrize(
    ("command", "phase", "error", "reason"),
    (
        (
            "run",
            None,
            R002RunError("reannotation_required"),
            "reannotation_required",
        ),
        (
            "run",
            None,
            R002RunError("redaction_boundary_failed"),
            "benchmark_gate_failed",
        ),
        (
            "run",
            None,
            R002RunError("scopeproof_commit_mismatch"),
            "input_validation_failed",
        ),
        (
            "prepare",
            "evidence",
            R002PreparationError("criteria_not_confirmed"),
            "criteria_not_confirmed",
        ),
        (
            "prepare",
            "evidence",
            R002PreparationError("preparation_integrity_failed"),
            "preparation_integrity_failed",
        ),
        (
            "prepare",
            "evidence",
            R002NetworkPolicyError("network_failure"),
            "network_unavailable",
        ),
        (
            "prepare",
            "evidence",
            R002NetworkPolicyError("unsafe_request_target"),
            "network_policy_failed",
        ),
        (
            "prepare",
            "evidence",
            R002NetworkPolicyError("http_status"),
            "source_integrity_failed",
        ),
        (
            "prepare",
            "criteria-sources",
            R002SourceError("source_pin_mismatch"),
            "source_integrity_failed",
        ),
        (
            "run",
            None,
            R002AnnotationError("candidate_labels_not_confirmed"),
            "labels_not_confirmed",
        ),
        (
            "run",
            None,
            R002AnnotationError("reannotation_required"),
            "reannotation_required",
        ),
        (
            "annotate",
            None,
            R002AnnotationError("criteria_manifest_drift"),
            "criteria_not_confirmed",
        ),
        (
            "annotate",
            None,
            R002AnnotationError("annotation_universe_drift"),
            "annotation_required",
        ),
        (
            "run",
            None,
            R002CacheError("cache_read_failed"),
            "prepared_cache_missing",
        ),
        (
            "prepare",
            "criteria-sources",
            R002CacheError("cache_read_failed"),
            "filesystem_failed",
        ),
        (
            "run",
            None,
            FileNotFoundError(),
            "prepared_cache_missing",
        ),
        (
            "run",
            None,
            OSError(),
            "input_validation_failed",
        ),
    ),
)
def test_domain_failures_map_to_closed_public_codes(
    command: str,
    phase: str | None,
    error: BaseException,
    reason: str,
) -> None:
    failure = r002_swebench._map_failure(
        command=command,
        phase=phase,
        error=error,
    )
    assert failure.reason_code == reason
    assert failure.errors == (reason,)


def test_resolve_scopeproof_commit_outside_checkout_is_explicit(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        R002RunError,
        match="scopeproof_commit_required_outside_checkout",
    ):
        r002_swebench.resolve_scopeproof_commit(
            None,
            checkout_root=tmp_path,
        )
    with pytest.raises(R002RunError, match="scopeproof_head_invalid"):
        r002_swebench.resolve_scopeproof_commit(
            "BAD",
            checkout_root=tmp_path,
        )
    assert (
        r002_swebench.resolve_scopeproof_commit(
            "a" * 40,
            checkout_root=tmp_path,
        )
        == "a" * 40
    )


def test_git_probe_failures_and_invalid_head_are_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").mkdir()

    monkeypatch.setattr(
        r002_swebench.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
    )
    with pytest.raises(R002RunError, match="scopeproof_git_probe_failed"):
        r002_swebench.resolve_scopeproof_commit(
            None,
            checkout_root=checkout,
        )

    calls = iter((SimpleNamespace(stdout=""), OSError()))

    def fail_second(*_args, **_kwargs):
        value = next(calls)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(r002_swebench.subprocess, "run", fail_second)
    with pytest.raises(R002RunError, match="scopeproof_git_probe_failed"):
        r002_swebench.resolve_scopeproof_commit(
            None,
            checkout_root=checkout,
        )

    calls = iter(
        (
            SimpleNamespace(stdout=""),
            SimpleNamespace(stdout="not-a-sha"),
        )
    )
    monkeypatch.setattr(
        r002_swebench.subprocess,
        "run",
        lambda *_args, **_kwargs: next(calls),
    )
    with pytest.raises(R002RunError, match="scopeproof_head_invalid"):
        r002_swebench.resolve_scopeproof_commit(
            None,
            checkout_root=checkout,
        )


def test_annotate_dispatch_and_bundled_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    assert r002_swebench.bundled_r002_root().as_posix().endswith("/evals/r002")
    root = _pack_root(tmp_path)
    expected = _DummyResult()
    monkeypatch.setattr(r002_swebench, "bundled_r002_root", lambda: root)
    monkeypatch.setattr(
        r002_swebench,
        "annotate_r002",
        lambda **_kwargs: expected,
    )

    assert r002_swebench.main(["annotate"]) == 0
    assert capsysbinary.readouterr().out == canonical_json_bytes(expected)
