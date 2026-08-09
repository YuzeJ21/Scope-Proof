"""Local-first command-line interface over the ScopeProof core engine."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from scopeproof_core.alpha.models import AlphaFrictionStage, AlphaOutcome, ParticipantRole
from scopeproof_core.alpha.rehearsal import initialize_alpha_rehearsal
from scopeproof_core.alpha.rehearsal_storage import JsonAlphaRehearsalStore
from scopeproof_core.alpha.service import (
    initialize_alpha_case,
    public_alpha_summary,
    record_alpha_outcome,
)
from scopeproof_core.alpha.storage import JsonAlphaCaseStore
from scopeproof_core.criteria.confirmation import (
    build_criteria_source_provenance,
    read_exact_utf8_text,
    validate_criteria_source_confirmation,
    validate_requirements_confirmation,
)
from scopeproof_core.criteria.service import parse_criteria
from scopeproof_core.evals.comparison_runner import run_bundled_comparison_benchmark
from scopeproof_core.evals.metrics import EvidenceQualityMetrics
from scopeproof_core.evals.runner import run_bundled_benchmark
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.github.client import GitHubClient, GitHubIngestionError
from scopeproof_core.reporting.exporters import (
    export_comparison_json,
    export_comparison_markdown,
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
from scopeproof_core.reviews.comparison import compare_reviews
from scopeproof_core.reviews.lifecycle import (
    acceptance_requires_comment,
    append_external_verification,
    append_resolution,
    new_review_state,
)
from scopeproof_core.schemas.models import (
    ActionValidationRecord,
    CriteriaSourceProvenance,
    Criterion,
    EvidenceLevel,
    HumanDecision,
    LifecycleMutationMetadata,
    PullRequestSnapshot,
    ResearchContext,
    ResolutionEvent,
    Review,
    ReviewBundle,
    ReviewInputOrigin,
    ReviewState,
    RuntimeEvidence,
    SavedReviewListing,
    normalize_public_https_source_uri,
    require_verified_public_origin,
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

COMPARISON_RENDERERS = {
    "json": export_comparison_json,
    "markdown": export_comparison_markdown,
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
    return _criteria_from_text(path.read_text(encoding="utf-8"))


def _criteria_from_text(source_text: str) -> list[Criterion]:
    drafts = parse_criteria(source_text)
    if not drafts:
        raise ValueError("requirements file must contain at least one non-empty criterion")
    return [Criterion(criterion_id=draft.criterion_id, text=draft.text) for draft in drafts]


def _build_bundle(
    snapshot: PullRequestSnapshot,
    criteria: list[Criterion],
    source_text: str,
    criteria_source_provenance: CriteriaSourceProvenance,
    research_case_id: str | None = None,
    input_origin: ReviewInputOrigin = ReviewInputOrigin.LEGACY_UNKNOWN,
) -> ReviewBundle:
    require_verified_public_origin(snapshot.repository_visibility, input_origin)
    review = Review(
        repository=snapshot.repository,
        repository_visibility=snapshot.repository_visibility,
        pr_number=snapshot.pr_number,
        base_sha=snapshot.base_sha,
        head_sha=snapshot.head_sha,
        check_state=snapshot.check_state,
        ci_observation=snapshot.ci_observation,
        criteria_confirmed=True,
        criteria_source_provenance=criteria_source_provenance,
        ingestion_state=snapshot.ingestion_state,
        ingestion_warnings=snapshot.warnings,
        skipped_files=snapshot.skipped_files,
        input_origin=input_origin,
    )
    retrieval_result = retrieve_evidence_with_diagnostics(snapshot, criteria)
    evidence = retrieval_result.evidence
    findings = build_findings(criteria, evidence, snapshot.ingestion_state)
    gate = evaluate_gate(review, criteria, findings, [])
    return ReviewBundle(
        review=review,
        source_text=source_text,
        criteria=criteria,
        evidence=evidence,
        retrieval_diagnostics=retrieval_result.diagnostics,
        findings=findings,
        gate=gate,
        research_context=(
            ResearchContext(
                case_id=research_case_id,
                boundary_note=(
                    "This public engineering research case does not advance Stage 1 "
                    "and is not customer or Alpha validation."
                ),
            )
            if research_case_id is not None
            else None
        ),
    )


def _review(args: argparse.Namespace) -> int:
    report_target = _report_target(args.report)
    requirements_path = Path(args.requirements)
    source_text = read_exact_utf8_text(requirements_path)
    criteria = _criteria_from_text(source_text)
    provenance = validate_criteria_source_confirmation(
        Path(args.confirmation),
        source_text=source_text,
        criteria=criteria,
    )
    if args.fixture:
        fixture_text = Path(args.fixture).read_text(encoding="utf-8")
        snapshot = PullRequestSnapshot.model_validate_json(fixture_text)
    else:
        snapshot = GitHubClient(token=args.token or None).fetch_pull_request(args.pr)
    bundle = _build_bundle(
        snapshot,
        criteria,
        source_text,
        provenance,
        args.research_case_id,
        (
            ReviewInputOrigin.LOCAL_FIXTURE
            if args.fixture
            else ReviewInputOrigin.LIVE_PUBLIC_GITHUB
        ),
    )
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
        "ci_state": bundle.review.ci_observation.state.value,
        "ci_reason": bundle.review.ci_observation.reason,
        "ci_total_check_runs": bundle.review.ci_observation.total_check_runs,
        "ci_successful_check_runs": bundle.review.ci_observation.successful_check_runs,
        "ci_pending_check_runs": bundle.review.ci_observation.pending_check_runs,
        "ci_failing_check_runs": bundle.review.ci_observation.failing_check_runs,
        "ci_neutral_check_runs": bundle.review.ci_observation.neutral_check_runs,
        "ci_skipped_check_runs": bundle.review.ci_observation.skipped_check_runs,
        "ci_concrete_legacy_status_count": (
            bundle.review.ci_observation.concrete_legacy_status_count
        ),
        "skipped_check_names": bundle.review.ci_observation.skipped_check_names,
        "ci_collection_complete": bundle.review.ci_observation.collection_complete,
        "ci_collection_notes": bundle.review.ci_observation.collection_notes,
        "candidate_evidence": [
            {
                "criterion_id": item.criterion_id,
                "evidence_type": item.evidence_type.value,
                "evidence_level": item.evidence_level.value,
            }
            for item in sorted(
                bundle.evidence,
                key=lambda item: (
                    item.criterion_id,
                    item.evidence_type.value,
                    item.evidence_level.value,
                    item.evidence_id,
                ),
            )
        ],
        "candidate_evidence_proves_correctness": bundle.candidate_evidence_proves_correctness,
        "candidate_evidence_boundary": "Candidate evidence does not prove correctness.",
        "runtime_verification_state": bundle.runtime_verification_state.value,
        "reviewer_decision_state": bundle.reviewer_decision_state.value,
        "gate_reason_codes": bundle.gate.reason_codes,
        "blocking_criteria": bundle.gate.blocking_criteria,
        "criteria_source_provenance": provenance.model_dump(mode="json"),
    }
    if bundle.research_context is not None:
        metadata.update(
            {
                "research_case_id": bundle.research_context.case_id,
                "research_classification": bundle.research_context.classification,
                "stage1_credit": bundle.research_context.stage1_credit,
                "research_boundary_note": bundle.research_context.boundary_note,
            }
        )
    if report_target is not None:
        report_path, renderer = report_target
        report_path.write_text(renderer(state), encoding="utf-8")
        metadata["report"] = str(report_path)
    print(json.dumps(metadata, sort_keys=True))
    return 0


def _export(args: argparse.Namespace) -> int:
    store = JsonReviewStore(Path(args.storage_dir))
    with store.locked_load(args.review_id) as state:
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


def _read_optional_comment(path: str | None) -> str:
    """Read a human-authored note without interpreting its contents."""

    return "" if path is None else Path(path).read_text(encoding="utf-8")


def _mutation_metadata(
    state: ReviewState, path: Path, event_id: str
) -> LifecycleMutationMetadata:
    """Return deterministic metadata for one persisted lifecycle mutation."""

    if state.bundle is None:
        raise ValueError("Run a confirmed analysis before recording a lifecycle event")
    return LifecycleMutationMetadata(
        review_id=state.review.review_id,
        record=str(path),
        head_sha=state.review.head_sha,
        event_id=event_id,
        verdict=state.bundle.gate.verdict,
        gate_reason_codes=state.bundle.gate.reason_codes,
    )


def _resolve(args: argparse.Namespace) -> int:
    """Append one validated human criterion resolution to a saved review."""

    store = JsonReviewStore(Path(args.storage_dir))
    decision = HumanDecision(args.decision)
    comment = _read_optional_comment(args.comment_file)
    event = ResolutionEvent(
        criterion_id=args.criterion_id,
        decision=decision,
        comment=comment,
        evidence_url=args.evidence_url,
        reviewer=args.reviewer.strip(),
    )

    def transition(state: ReviewState) -> ReviewState:
        if state.bundle is None:
            raise ValueError("Run a confirmed analysis before recording a resolution")
        criterion_by_id = {
            criterion.criterion_id: criterion for criterion in state.bundle.criteria
        }
        finding_by_id = {
            finding.criterion_id: finding for finding in state.bundle.findings
        }
        criterion = criterion_by_id.get(args.criterion_id)
        finding = finding_by_id.get(args.criterion_id)
        if criterion is None or finding is None:
            raise ValueError("resolution must reference a criterion in the active review")
        if acceptance_requires_comment(
            decision,
            finding.evidence_level,
            criterion.required_evidence_level,
        ) and not comment.strip():
            raise ValueError(
                "a reviewer comment is required when accepting below the required evidence level"
            )
        return append_resolution(state, event)

    updated, path = store.mutate(args.review_id, transition)
    print(_mutation_metadata(updated, path, event.event_id).model_dump_json())
    return 0


def _verify_runtime(args: argparse.Namespace) -> int:
    """Atomically record human-supplied runtime evidence and its decision."""

    store = JsonReviewStore(Path(args.storage_dir))
    runtime_id = str(uuid4())
    reviewer = args.reviewer.strip()
    level = EvidenceLevel(args.level)
    event = ResolutionEvent(
        criterion_id=args.criterion_id,
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment=Path(args.comment_file).read_text(encoding="utf-8"),
        claimed_evidence_level=level,
        runtime_evidence_id=runtime_id,
        reviewer=reviewer,
    )

    def transition(state: ReviewState) -> ReviewState:
        evidence = RuntimeEvidence(
            runtime_evidence_id=runtime_id,
            repository=state.review.repository,
            pr_number=state.review.pr_number,
            head_sha=state.review.head_sha,
            criterion_id=args.criterion_id,
            artifact_reference=args.artifact_reference,
            scenario=args.scenario,
            environment=args.environment,
            result=args.result,
            reviewer=reviewer,
            evidence_level=level,
            limitations=args.limitation,
        )
        return append_external_verification(state, evidence, event)

    updated, path = store.mutate(args.review_id, transition)
    print(_mutation_metadata(updated, path, event.event_id).model_dump_json())
    return 0


def _final_acceptance(args: argparse.Namespace) -> int:
    """Append a validated final-acceptance or revocation event."""

    store = JsonReviewStore(Path(args.storage_dir))
    event = ResolutionEvent(
        final_acceptance=args.accept,
        comment=_read_optional_comment(args.comment_file),
        reviewer=args.reviewer.strip(),
    )
    updated, path = store.mutate(
        args.review_id,
        lambda state: append_resolution(state, event),
    )
    print(_mutation_metadata(updated, path, event.event_id).model_dump_json())
    return 0


def _compare(args: argparse.Namespace) -> int:
    """Compare two validated saved review bundles without carrying decisions forward."""

    store = JsonReviewStore(Path(args.storage_dir))
    with store.locked_load_many(
        (args.previous_review_id, args.current_review_id)
    ) as (previous, current):
        if previous.bundle is None or current.bundle is None:
            raise ValueError("comparison requires an active analysis in both saved reviews")
        if (
            previous.bundle.review.repository,
            previous.bundle.review.pr_number,
        ) != (
            current.bundle.review.repository,
            current.bundle.review.pr_number,
        ):
            raise ValueError(
                "comparison requires reviews from the same repository and pull request"
            )
        previous_criteria = {
            item.criterion_id: item.model_dump(mode="json")
            for item in previous.bundle.criteria
        }
        current_criteria = {
            item.criterion_id: item.model_dump(mode="json")
            for item in current.bundle.criteria
        }
        if previous_criteria != current_criteria:
            raise ValueError(
                "comparison requires identical confirmed criterion definitions"
            )
        comparison = compare_reviews(previous.bundle, current.bundle)
        rendered = COMPARISON_RENDERERS[args.format](comparison)
        if args.output is None:
            print(rendered, end="")
        else:
            output_path = Path(args.output)
            if output_path.exists():
                raise FileExistsError(f"comparison output already exists: {output_path}")
            with output_path.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
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


def _prepare_requirements_confirmation(args: argparse.Namespace) -> int:
    """Write one owner-attested, hash-bound confirmation without networking."""

    requirements_path = Path(args.requirements)
    source_text = read_exact_utf8_text(requirements_path)
    criteria = _criteria_from_text(source_text)
    source_uri = normalize_public_https_source_uri(args.source_uri)
    confirmation = build_criteria_source_provenance(
        source_uri=source_uri,
        source_revision=args.source_revision,
        source_text=source_text,
        criteria=criteria,
        confirmed_by=args.confirmed_by,
        confirmed_at=datetime.now(UTC),
    )
    output_path = Path(args.output)
    with output_path.open("x", encoding="utf-8") as handle:
        handle.write(confirmation.model_dump_json(indent=2) + "\n")
    print(
        json.dumps(
            {
                "confirmation": str(output_path),
                "source_text_sha256": confirmation.source_text_sha256,
                "normalized_criteria_sha256": (
                    confirmation.normalized_criteria_sha256
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _alpha_init(args: argparse.Namespace) -> int:
    """Create a local, validated record for one genuine public-alpha case."""
    requirements_path = Path(args.requirements)
    source_text = read_exact_utf8_text(requirements_path)
    criteria = _criteria_from_text(source_text)
    provenance = validate_criteria_source_confirmation(
        Path(args.confirmation),
        source_text=source_text,
        criteria=criteria,
    )
    record = initialize_alpha_case(
        public_pr_url=args.pr,
        requirements_source_url=args.requirements_source,
        participant_role=ParticipantRole(args.participant_role),
        source_owner_confirmed=args.source_owner_confirmed,
        no_confidential_information=args.confirmed_no_confidential_information,
        confirmed_criteria=[criterion.text for criterion in criteria],
        confirmed_criterion_snapshot=criteria,
        criteria_source_provenance=provenance,
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
    review_state = JsonReviewStore(Path(args.review_storage_dir)).load(args.review_id)
    notes = None
    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding="utf-8")
    updated = record_alpha_outcome(
        record,
        review_state=review_state,
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
    review.add_argument(
        "--confirmation",
        required=True,
        help="Typed criteria-source confirmation JSON for the exact requirements snapshot",
    )
    review.add_argument("--storage-dir", default=".scopeproof/reviews")
    review.add_argument("--token", help="Optional GitHub token; never persisted or printed")
    review.add_argument(
        "--research-case-id",
        help="Fixed public engineering research case ID; never grants Stage 1 credit",
    )
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
    resolve = commands.add_parser("resolve", help="Record one human criterion decision")
    resolve.add_argument("review_id")
    resolve.add_argument("--criterion-id", required=True)
    resolve.add_argument(
        "--decision",
        required=True,
        choices=[
            decision.value
            for decision in HumanDecision
            if decision is not HumanDecision.MANUALLY_VERIFIED
        ],
    )
    resolve.add_argument("--reviewer", required=True)
    resolve.add_argument("--comment-file")
    resolve.add_argument("--evidence-url")
    resolve.add_argument("--storage-dir", default=".scopeproof/reviews")
    resolve.set_defaults(handler=_resolve)
    verify_runtime = commands.add_parser(
        "verify-runtime",
        help="Atomically record external runtime evidence and manual verification",
    )
    verify_runtime.add_argument("review_id")
    verify_runtime.add_argument("--criterion-id", required=True)
    verify_runtime.add_argument(
        "--level",
        required=True,
        choices=[EvidenceLevel.E3.value, EvidenceLevel.E4.value],
    )
    verify_runtime.add_argument("--reviewer", required=True)
    verify_runtime.add_argument("--artifact-reference", required=True)
    verify_runtime.add_argument("--scenario", required=True)
    verify_runtime.add_argument("--environment", required=True)
    verify_runtime.add_argument("--result", required=True)
    verify_runtime.add_argument("--comment-file", required=True)
    verify_runtime.add_argument("--limitation", action="append", default=[])
    verify_runtime.add_argument("--storage-dir", default=".scopeproof/reviews")
    verify_runtime.set_defaults(handler=_verify_runtime)
    final_acceptance = commands.add_parser(
        "final-acceptance",
        help="Record or revoke final human acceptance",
    )
    final_acceptance.add_argument("review_id")
    final_action = final_acceptance.add_mutually_exclusive_group(required=True)
    final_action.add_argument("--accept", action="store_true", dest="accept")
    final_action.add_argument("--revoke", action="store_false", dest="accept")
    final_acceptance.add_argument("--reviewer", required=True)
    final_acceptance.add_argument("--comment-file")
    final_acceptance.add_argument("--storage-dir", default=".scopeproof/reviews")
    final_acceptance.set_defaults(handler=_final_acceptance)
    compare = commands.add_parser("compare", help="Compare two saved review heads")
    compare.add_argument("previous_review_id")
    compare.add_argument("current_review_id")
    compare.add_argument("--format", choices=sorted(COMPARISON_RENDERERS), default="json")
    compare.add_argument("--output")
    compare.add_argument("--storage-dir", default=".scopeproof/reviews")
    compare.set_defaults(handler=_compare)
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
    prepare_confirmation = commands.add_parser(
        "prepare-requirements-confirmation",
        help=(
            "Create a no-network hash-bound confirmation after human criteria review"
        ),
    )
    prepare_confirmation.add_argument("--requirements", required=True)
    prepare_confirmation.add_argument("--source-uri", required=True)
    prepare_confirmation.add_argument("--source-revision")
    prepare_confirmation.add_argument(
        "--confirmed-by",
        required=True,
        help="Human owner or authorized role explicitly attesting the criteria",
    )
    prepare_confirmation.add_argument("--output", required=True)
    prepare_confirmation.set_defaults(handler=_prepare_requirements_confirmation)
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
        "--confirmation",
        required=True,
        help="Typed criteria-source confirmation JSON for the exact requirements snapshot",
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
    alpha_outcome.add_argument("--review-storage-dir", default=".scopeproof/reviews")
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
