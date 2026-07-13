"""Local-first command-line interface over the ScopeProof core engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scopeproof_core.criteria.confirmation import validate_requirements_confirmation
from scopeproof_core.criteria.service import parse_criteria
from scopeproof_core.evals.metrics import EvidenceQualityMetrics
from scopeproof_core.evals.runner import run_bundled_benchmark
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.github.client import GitHubClient, GitHubIngestionError
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import (
    ActionValidationRecord,
    Criterion,
    PullRequestSnapshot,
    Review,
    ReviewBundle,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.verification.service import build_findings
from scopeproof_core.version import __version__

EXPORT_RENDERERS = {
    "json": export_json,
    "markdown": export_markdown,
    "csv": export_csv,
    "html": export_html,
}

REPORT_SUFFIX_FORMATS = {
    ".md": "markdown",
    ".json": "json",
    ".csv": "csv",
    ".html": "html",
}


def _report_target(value: str | None):
    if value is None:
        return None
    path = Path(value)
    report_format = REPORT_SUFFIX_FORMATS.get(path.suffix.lower())
    if report_format is None:
        raise ValueError("report path must end in .md, .json, .csv, or .html")
    if path.exists():
        raise FileExistsError(f"report path already exists: {path}")
    return path, EXPORT_RENDERERS[report_format]


def _criteria_from_file(path: Path) -> list[Criterion]:
    drafts = parse_criteria(path.read_text(encoding="utf-8"))
    if not drafts:
        raise ValueError("requirements file must contain at least one non-empty criterion")
    return [Criterion(criterion_id=draft.criterion_id, text=draft.text) for draft in drafts]


def _build_bundle(
    snapshot: PullRequestSnapshot, criteria: list[Criterion], source_text: str
) -> ReviewBundle:
    review = Review(
        repository=snapshot.repository,
        pr_number=snapshot.pr_number,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
        check_state=snapshot.check_state,
        criteria_confirmed=True,
        ingestion_state=snapshot.ingestion_state,
    )
    evidence = retrieve_evidence(snapshot, criteria)
    findings = build_findings(criteria, evidence, snapshot.ingestion_state)
    gate = evaluate_gate(review, criteria, findings, [])
    return ReviewBundle(
        review=review,
        source_text=source_text,
        criteria=criteria,
        evidence=evidence,
        findings=findings,
        gate=gate,
    )


def _review(args: argparse.Namespace) -> int:
    report_target = _report_target(args.report)
    requirements_path = Path(args.requirements)
    criteria = _criteria_from_file(requirements_path)
    if args.fixture:
        fixture_text = Path(args.fixture).read_text(encoding="utf-8")
        snapshot = PullRequestSnapshot.model_validate_json(fixture_text)
    else:
        snapshot = GitHubClient(token=args.token or None).fetch_pull_request(args.pr)
    bundle = _build_bundle(snapshot, criteria, requirements_path.read_text(encoding="utf-8"))
    state = new_review_state(bundle)
    path = JsonReviewStore(Path(args.storage_dir)).save(state)
    metadata = {
        "review_id": state.review.review_id,
        "record": str(path),
        "verdict": bundle.gate.verdict.value,
        "head_sha": bundle.review.head_sha,
    }
    if report_target is not None:
        report_path, renderer = report_target
        report_path.write_text(renderer(state), encoding="utf-8")
        metadata["report"] = str(report_path)
    print(json.dumps(metadata, sort_keys=True))
    return 0


def _export(args: argparse.Namespace) -> int:
    state = JsonReviewStore(Path(args.storage_dir)).load(args.review_id)
    print(EXPORT_RENDERERS[args.format](state), end="")
    return 0


def _validate_action_evidence(args: argparse.Namespace) -> int:
    """Validate owner-supplied external Action evidence without contacting GitHub."""

    record = ActionValidationRecord.model_validate_json(
        Path(args.record).read_text(encoding="utf-8")
    )
    print(json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _validate_requirements_confirmation(args: argparse.Namespace) -> int:
    """Validate a hash-bound Action requirements confirmation without networking."""

    confirmation = validate_requirements_confirmation(
        Path(args.requirements), Path(args.confirmation)
    )
    print(json.dumps(confirmation.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scopeproof", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review", help="Review a public PR or local fixture")
    source = review.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", help="Path to a PR-shaped local fixture JSON")
    source.add_argument("--pr", help="Public GitHub pull request URL")
    review.add_argument(
        "--requirements", required=True, help="One user-confirmed criterion per line"
    )
    review.add_argument("--storage-dir", default=".scopeproof/reviews")
    review.add_argument("--token", help="Optional GitHub token; never persisted or printed")
    review.add_argument(
        "--report", help="Write .md, .json, .csv, or .html without overwriting an existing file"
    )
    review.set_defaults(handler=_review)
    export = commands.add_parser("export", help="Render a saved local review")
    export.add_argument("review_id")
    export.add_argument("--storage-dir", default=".scopeproof/reviews")
    export.add_argument("--format", choices=["json", "markdown", "csv", "html"], default="json")
    export.set_defaults(handler=_export)
    benchmark = commands.add_parser("benchmark", help="Run every labelled local benchmark case")
    benchmark.set_defaults(handler=lambda _: _benchmark())
    action_evidence = commands.add_parser(
        "validate-action-evidence",
        help="Validate an owner-supplied external Action evidence record without networking",
    )
    action_evidence.add_argument("record", help="Path to action-validation JSON")
    action_evidence.set_defaults(handler=_validate_action_evidence)
    requirements_confirmation = commands.add_parser(
        "validate-requirements-confirmation",
        help="Validate a hash-bound Action requirements confirmation without networking",
    )
    requirements_confirmation.add_argument("--requirements", required=True)
    requirements_confirmation.add_argument("--confirmation", required=True)
    requirements_confirmation.set_defaults(handler=_validate_requirements_confirmation)
    return parser


def _benchmark() -> int:
    result = run_bundled_benchmark()
    payload = result.model_dump(mode="json")
    payload["evidence_quality_metrics"] = EvidenceQualityMetrics.from_benchmark(result).model_dump(
        mode="json"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return int(
        bool(
            result.must_have_false_ready
            or result.false_blocker
            or result.mismatches
            or result.unexecuted_declared_categories
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Run a ScopeProof command and return a shell-safe status code."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (GitHubIngestionError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
