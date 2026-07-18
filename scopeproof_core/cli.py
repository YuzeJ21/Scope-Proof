"""Local-first command-line interface over the ScopeProof core engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scopeproof_core.alpha.models import AlphaFrictionStage, AlphaOutcome, ParticipantRole
from scopeproof_core.alpha.rehearsal import initialize_alpha_rehearsal
from scopeproof_core.alpha.rehearsal_storage import JsonAlphaRehearsalStore
from scopeproof_core.alpha.service import (
    initialize_alpha_case,
    public_alpha_summary,
    record_alpha_outcome,
)
from scopeproof_core.alpha.storage import JsonAlphaCaseStore
from scopeproof_core.criteria.confirmation import validate_requirements_confirmation
from scopeproof_core.criteria.service import parse_criteria
from scopeproof_core.evals.comparison_runner import run_bundled_comparison_benchmark
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
    SavedReviewListing,
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
        ingestion_warnings=snapshot.warnings,
        skipped_files=snapshot.skipped_files,
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
        "ingestion_state": bundle.review.ingestion_state.value,
        "ingestion_warnings": bundle.review.ingestion_warnings,
        "skipped_files": bundle.review.skipped_files,
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


def _list(args: argparse.Namespace) -> int:
    storage_dir = Path(args.storage_dir)
    listing = SavedReviewListing(
        review_ids=JsonReviewStore(storage_dir).list_review_ids(),
        storage_dir=str(storage_dir),
    )
    print(listing.model_dump_json())
    return 0


def _delete(args: argparse.Namespace) -> int:
    storage_dir = Path(args.storage_dir)
    JsonReviewStore(storage_dir).delete(args.review_id)
    print(
        json.dumps(
            {"deleted_review_id": args.review_id, "storage_dir": str(storage_dir)},
            sort_keys=True,
        )
    )
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


def _alpha_init(args: argparse.Namespace) -> int:
    """Create a local, validated record for one genuine public-alpha case."""
    requirements_path = Path(args.requirements)
    criteria = _criteria_from_file(requirements_path)
    record = initialize_alpha_case(
        public_pr_url=args.pr,
        requirements_source_url=args.requirements_source,
        participant_role=ParticipantRole(args.participant_role),
        source_owner_confirmed=args.source_owner_confirmed,
        no_confidential_information=args.confirmed_no_confidential_information,
        confirmed_criteria=[criterion.text for criterion in criteria],
    )
    path = JsonAlphaCaseStore(Path(args.storage_dir)).save(record)
    payload = record.model_dump(mode="json")
    payload["record"] = str(path)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _alpha_outcome(args: argparse.Namespace) -> int:
    """Complete one local alpha case with a bounded, validated outcome."""
    store = JsonAlphaCaseStore(Path(args.storage_dir))
    record = store.load(args.case_id)
    notes = None
    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding="utf-8")
    updated = record_alpha_outcome(
        record,
        review_id=args.review_id,
        reviewed_head_sha=args.head_sha,
        outcome=AlphaOutcome(args.result),
        friction_stage=(
            AlphaFrictionStage(args.friction_stage) if args.friction_stage else None
        ),
        outcome_notes=notes,
        report_consent=args.report_consent,
        quote_consent=args.quote_consent,
    )
    store.update(updated)
    print(updated.model_dump_json(indent=2))
    return 0


def _alpha_show(args: argparse.Namespace) -> int:
    """Show a full local case or its reduced consent-gated public summary."""
    record = JsonAlphaCaseStore(Path(args.storage_dir)).load(args.case_id)
    output = public_alpha_summary(record) if args.public_summary else record
    print(json.dumps(output.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _owner_rehearsal_init(args: argparse.Namespace) -> int:
    """Create a deterministic local owner rehearsal excluded from genuine alpha."""
    requirements_path = Path(args.requirements)
    criteria = _criteria_from_file(requirements_path)
    record = initialize_alpha_rehearsal(
        public_pr_url=args.pr,
        requirements_source_url=args.requirements_source,
        criteria_authority=args.criteria_authority,
        source_owner_confirmed=args.source_owner_confirmed,
        no_confidential_information=args.confirmed_no_confidential_information,
        confirmed_criteria=[criterion.text for criterion in criteria],
    )
    path = JsonAlphaRehearsalStore(Path(args.storage_dir)).save(record)
    payload = record.model_dump(mode="json")
    payload["record"] = str(path)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _owner_rehearsal_show(args: argparse.Namespace) -> int:
    """Show one local owner rehearsal and its fixed exclusion boundary."""
    record = JsonAlphaRehearsalStore(Path(args.storage_dir)).load(args.rehearsal_id)
    print(json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True))
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
    list_reviews = commands.add_parser("list", help="List safe local saved review IDs")
    list_reviews.add_argument("--storage-dir", default=".scopeproof/reviews")
    list_reviews.set_defaults(handler=_list)
    delete = commands.add_parser("delete", help="Delete one saved local review")
    delete.add_argument("review_id")
    delete.add_argument("--storage-dir", default=".scopeproof/reviews")
    delete.set_defaults(handler=_delete)
    benchmark = commands.add_parser("benchmark", help="Run every labelled local benchmark case")
    benchmark.set_defaults(handler=lambda _: _benchmark())
    comparison_benchmark = commands.add_parser(
        "comparison-benchmark",
        help="Run the constructed re-review evidence-integrity benchmark",
    )
    comparison_benchmark.set_defaults(handler=lambda _: _comparison_benchmark())
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
    alpha = commands.add_parser(
        "alpha", help="Capture truthful local evidence from genuine public-alpha use"
    )
    alpha_commands = alpha.add_subparsers(dest="alpha_command", required=True)
    alpha_init = alpha_commands.add_parser(
        "init", help="Initialize a source-owner-confirmed public-alpha case"
    )
    alpha_init.add_argument("--pr", required=True, help="Public GitHub pull request URL")
    alpha_init.add_argument(
        "--requirements-source",
        required=True,
        help="Public HTTPS URL containing the owner-confirmed requirements",
    )
    alpha_init.add_argument(
        "--participant-role",
        required=True,
        choices=[role.value for role in ParticipantRole],
    )
    alpha_init.add_argument(
        "--requirements", required=True, help="One confirmed criterion per line"
    )
    alpha_init.add_argument(
        "--source-owner-confirmed",
        action="store_true",
        required=True,
        help="Confirm authority to approve the linked requirements",
    )
    alpha_init.add_argument(
        "--confirmed-no-confidential-information",
        action="store_true",
        required=True,
        help="Confirm the case contains no private or confidential information",
    )
    alpha_init.add_argument("--storage-dir", default=".scopeproof/alpha-cases")
    alpha_init.set_defaults(handler=_alpha_init)
    alpha_outcome = alpha_commands.add_parser(
        "outcome", help="Record one bounded alpha outcome"
    )
    alpha_outcome.add_argument("case_id")
    alpha_outcome.add_argument("--review-id", required=True)
    alpha_outcome.add_argument("--head-sha", required=True)
    alpha_outcome.add_argument(
        "--result", required=True, choices=[outcome.value for outcome in AlphaOutcome]
    )
    alpha_outcome.add_argument("--notes-file")
    alpha_outcome.add_argument(
        "--friction-stage", choices=[stage.value for stage in AlphaFrictionStage]
    )
    alpha_outcome.add_argument("--report-consent", action="store_true")
    alpha_outcome.add_argument("--quote-consent", action="store_true")
    alpha_outcome.add_argument("--storage-dir", default=".scopeproof/alpha-cases")
    alpha_outcome.set_defaults(handler=_alpha_outcome)
    alpha_show = alpha_commands.add_parser(
        "show", help="Show a local alpha record or consent-gated public summary"
    )
    alpha_show.add_argument("case_id")
    alpha_show.add_argument("--public-summary", action="store_true")
    alpha_show.add_argument("--storage-dir", default=".scopeproof/alpha-cases")
    alpha_show.set_defaults(handler=_alpha_show)
    owner_rehearsal = commands.add_parser(
        "owner-rehearsal",
        help="Exercise local owner intake without creating a genuine alpha case",
    )
    owner_rehearsal_commands = owner_rehearsal.add_subparsers(
        dest="owner_rehearsal_command", required=True
    )
    owner_rehearsal_init = owner_rehearsal_commands.add_parser(
        "init", help="Create a local owner rehearsal permanently excluded from Stage 1"
    )
    owner_rehearsal_init.add_argument(
        "--pr", required=True, help="Public GitHub pull request URL"
    )
    owner_rehearsal_init.add_argument(
        "--requirements-source",
        required=True,
        help="Public-shaped HTTPS URL containing the owner-approved requirements",
    )
    owner_rehearsal_init.add_argument(
        "--criteria-authority",
        required=True,
        help="Statement identifying authority for the confirmed criteria",
    )
    owner_rehearsal_init.add_argument(
        "--requirements", required=True, help="One confirmed criterion per line"
    )
    owner_rehearsal_init.add_argument(
        "--source-owner-confirmed",
        action="store_true",
        required=True,
        help="Confirm authority to approve the linked requirements",
    )
    owner_rehearsal_init.add_argument(
        "--confirmed-no-confidential-information",
        action="store_true",
        required=True,
        help="Confirm the rehearsal contains no private or confidential information",
    )
    owner_rehearsal_init.add_argument(
        "--storage-dir", default=".scopeproof/alpha-rehearsals"
    )
    owner_rehearsal_init.set_defaults(handler=_owner_rehearsal_init)
    owner_rehearsal_show = owner_rehearsal_commands.add_parser(
        "show", help="Show one local owner rehearsal"
    )
    owner_rehearsal_show.add_argument("rehearsal_id")
    owner_rehearsal_show.add_argument(
        "--storage-dir", default=".scopeproof/alpha-rehearsals"
    )
    owner_rehearsal_show.set_defaults(handler=_owner_rehearsal_show)
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


def _comparison_benchmark() -> int:
    result = run_bundled_comparison_benchmark()
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
    return int(bool(result.mismatches or result.executed_case_count == 0))


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
