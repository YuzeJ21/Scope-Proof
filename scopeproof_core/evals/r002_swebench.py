"""Opt-in command surface for the local R-002 engineering benchmark."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx
from pydantic import ValidationError

from scopeproof_core.evals.r002_cache import R002CacheError
from scopeproof_core.evals.r002_models import (
    GitSha,
    R002AnnotationError,
    R002AnnotationUniverse,
    R002CommandFailure,
    R002CriteriaSourcePreparationResult,
    R002Error,
    R002PreparationResult,
    R002SourceError,
    canonical_json_bytes,
)
from scopeproof_core.evals.r002_prepare import (
    R002NetworkPolicyError,
    R002PreparationError,
    prepare_criteria_sources,
    prepare_r002,
)
from scopeproof_core.evals.r002_runner import R002RunError, annotate_r002, run_r002

R002_EXPECTED_ERRORS = (
    R002Error,
    ValidationError,
    OSError,
)


class _R002CommandBoundaryError(Exception):
    allowed = frozenset(
        {
            "source_manifest_missing",
            "criteria_missing",
            "labels_missing",
        }
    )

    def __init__(self, reason_code: str) -> None:
        if reason_code not in self.allowed:
            raise RuntimeError("unregistered command-boundary reason code")
        self.reason_code = reason_code
        super().__init__(reason_code)


R002_EXPECTED_ERRORS += (_R002CommandBoundaryError,)


def bundled_r002_root() -> Path:
    return Path(__file__).resolve().parents[2] / "evals" / "r002"


def default_cache_root() -> Path:
    return Path(".scopeproof/research/r002")


def _git_sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise argparse.ArgumentTypeError("expected a 40-character lowercase Git SHA")
    return value


def resolve_scopeproof_commit(
    explicit: str | None,
    *,
    checkout_root: Path | None = None,
) -> GitSha:
    root = checkout_root or Path(__file__).resolve().parents[2]
    if not (root / ".git").exists():
        if explicit is None:
            raise R002RunError("scopeproof_commit_required_outside_checkout")
        if not re.fullmatch(r"[0-9a-f]{40}", explicit):
            raise R002RunError("scopeproof_head_invalid")
        return explicit
    try:
        status = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise R002RunError("scopeproof_git_probe_failed") from None
    if status.stdout:
        raise R002RunError("scopeproof_checkout_dirty")
    try:
        head = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--verify",
                "HEAD^{commit}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise R002RunError("scopeproof_git_probe_failed") from None
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise R002RunError("scopeproof_head_invalid")
    if explicit is not None and explicit != head:
        raise R002RunError("scopeproof_commit_mismatch")
    return head


def _command_failure(command: str, reason_code: str) -> R002CommandFailure:
    return R002CommandFailure(
        command=command,
        reason_code=reason_code,
        errors=(reason_code,),
    )


def _map_failure(
    *,
    command: str,
    phase: str | None,
    error: BaseException,
) -> R002CommandFailure:
    if isinstance(error, _R002CommandBoundaryError):
        reason = error.reason_code
    elif isinstance(error, R002RunError):
        if error.reason_code == "reannotation_required":
            reason = "reannotation_required"
        elif error.reason_code in {
            "benchmark_gate_failed",
            "expected_missing_label_conflict",
            "redaction_boundary_failed",
            "normalized_rerun_mismatch",
        }:
            reason = "benchmark_gate_failed"
        else:
            reason = "input_validation_failed"
    elif isinstance(error, R002PreparationError):
        reason = (
            "criteria_not_confirmed"
            if error.reason_code == "criteria_not_confirmed"
            else "preparation_integrity_failed"
        )
    elif isinstance(error, R002NetworkPolicyError):
        if error.reason_code == "network_failure":
            reason = "network_unavailable"
        elif error.reason_code in {
            "unsafe_request_target",
            "redirect_location_invalid",
            "redirect_limit",
            "request_limit",
            "content_encoding",
            "content_length_invalid",
        }:
            reason = "network_policy_failed"
        else:
            reason = "source_integrity_failed"
    elif isinstance(error, R002SourceError):
        reason = "source_integrity_failed"
    elif isinstance(error, R002AnnotationError):
        if error.reason_code == "candidate_labels_not_confirmed":
            reason = "labels_not_confirmed"
        elif error.reason_code == "reannotation_required":
            reason = "reannotation_required"
        elif "criteria" in error.reason_code:
            reason = "criteria_not_confirmed"
        else:
            reason = "annotation_required"
    elif isinstance(error, R002CacheError):
        reason = (
            "prepared_cache_missing"
            if command in {"annotate", "run"} or phase == "evidence"
            else "filesystem_failed"
        )
    elif isinstance(error, FileNotFoundError):
        reason = "prepared_cache_missing"
    elif isinstance(error, (ValidationError, OSError)):
        reason = "input_validation_failed"
    else:
        reason = "internal_error"
    return _command_failure(command, reason)


def _write_result(value: object) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(value))  # type: ignore[arg-type]
    sys.stdout.buffer.flush()


def _preflight_paths(command: str, phase: str | None, root: Path) -> None:
    if not (root / "source_manifest.json").is_file():
        raise _R002CommandBoundaryError("source_manifest_missing")
    if (command in {"annotate", "run"} or phase == "evidence") and not (
        root / "criteria.json"
    ).is_file():
        raise _R002CommandBoundaryError("criteria_missing")
    if command == "run" and not (root / "candidate_labels.json").is_file():
        raise _R002CommandBoundaryError("labels_missing")


def main(
    argv: Sequence[str] | None = None,
    *,
    transport: httpx.BaseTransport | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m scopeproof_core.evals.r002_swebench")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "annotate", "run"):
        command = commands.add_parser(name)
        command.add_argument(
            "--cache-dir",
            type=Path,
            default=default_cache_root(),
        )
        if name == "prepare":
            command.add_argument(
                "--phase",
                choices=("criteria-sources", "evidence"),
                required=True,
            )
        if name == "run":
            command.add_argument("--scopeproof-commit", type=_git_sha)
    args = parser.parse_args(argv)
    root = bundled_r002_root()
    phase = getattr(args, "phase", None)
    try:
        _preflight_paths(args.command, phase, root)
        if args.command == "prepare" and phase == "criteria-sources":
            result = prepare_criteria_sources(
                manifest_path=root / "source_manifest.json",
                cache_root=args.cache_dir,
                transport=transport,
            )
        elif args.command == "prepare":
            result = prepare_r002(
                manifest_path=root / "source_manifest.json",
                criteria_path=root / "criteria.json",
                cache_root=args.cache_dir,
                transport=transport,
            )
        elif args.command == "annotate":
            result = annotate_r002(
                manifest_path=root / "source_manifest.json",
                criteria_path=root / "criteria.json",
                cache_root=args.cache_dir,
            )
        else:
            result = run_r002(
                manifest_path=root / "source_manifest.json",
                criteria_path=root / "criteria.json",
                labels_path=root / "candidate_labels.json",
                cache_root=args.cache_dir,
                scopeproof_commit=resolve_scopeproof_commit(args.scopeproof_commit),
            )
    except R002_EXPECTED_ERRORS as error:
        _write_result(
            _map_failure(
                command=args.command,
                phase=phase,
                error=error,
            )
        )
        return 2
    except Exception as error:
        _write_result(
            _map_failure(
                command=args.command,
                phase=phase,
                error=error,
            )
        )
        return 3
    _write_result(result)
    if isinstance(
        result,
        (R002CriteriaSourcePreparationResult, R002PreparationResult),
    ):
        return int(bool(result.hard_gate_errors or not result.complete))
    if isinstance(result, R002AnnotationUniverse):
        return 0
    return int(bool(result.hard_gate_errors))


if __name__ == "__main__":
    raise SystemExit(main())
