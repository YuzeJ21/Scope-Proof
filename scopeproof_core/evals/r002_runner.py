"""Offline, two-pass annotation and execution helpers for R-002."""

from __future__ import annotations

import json
import os
import re
import stat
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from scopeproof_core.evals.r002_cache import R002Cache, R002CacheError
from scopeproof_core.evals.r002_diff import parse_case_diffs, parsed_case_to_changed_files
from scopeproof_core.evals.r002_models import (
    R002_REDACTION_RAW_VALUE_MAX_BYTES,
    R002_REDACTION_TRACKED_FILE_MAX_BYTES,
    R002_RESULT_LIMITATIONS,
    R002_STATIC_EVIDENCE_TYPES,
    R002AnnotationError,
    R002AnnotationReviewItem,
    R002AnnotationUniverse,
    R002BenchmarkResult,
    R002CachedCase,
    R002CandidateLabel,
    R002CandidateLabelProposal,
    R002CandidateLabelSet,
    R002CandidateLineKey,
    R002CaseManifest,
    R002CaseResult,
    R002CriteriaProposal,
    R002CriteriaSet,
    R002CriterionCase,
    R002CriterionReviewCase,
    R002DeterminismProjection,
    R002ExpectedMissing,
    R002Metric,
    R002Metrics,
    R002MetricState,
    R002MissingExplanation,
    R002ParsedCase,
    R002RedactionAudit,
    R002RetrievedCandidate,
    R002SourceManifest,
    R002VerifiedCaseLines,
    R002VerifiedLine,
    SWEbenchVerifiedRow,
    canonical_json_bytes,
    canonical_sha256,
    load_confirmed_criteria,
    load_confirmed_labels,
    load_source_manifest,
    validate_r002_source_span,
)
from scopeproof_core.evals.r002_verify import (
    verify_case_head_files,
    verify_evidence_reference,
)
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.retrieval.engine import classify_changed_path_evidence_type, retrieve_evidence
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    CIReasonCode,
    Criterion,
    CriterionSource,
    EvidenceType,
    Finding,
    FindingStatus,
    GateVerdict,
    IngestionState,
    LineChangeType,
    Priority,
    PullRequestSnapshot,
    ResearchContext,
    Review,
    ReviewBundle,
)
from scopeproof_core.verification.service import build_findings


def _normalized_problem_lines(value: str) -> tuple[str, ...]:
    return tuple(value.replace("\r\n", "\n").replace("\r", "\n").split("\n"))


def _validate_criterion_spans(
    criteria: Sequence[Criterion],
    *,
    line_count: int,
) -> None:
    required_fields = {
        "criterion_id",
        "text",
        "priority",
        "criterion_type",
        "criterion_source",
        "source_span",
        "required_evidence_level",
    }
    if not 1 <= len(criteria) <= 16:
        raise R002AnnotationError("criteria_source_cache_manifest_mismatch")
    for criterion in criteria:
        if (
            type(criterion) is not Criterion
            or criterion.model_fields_set != required_fields
            or criterion.criterion_source is not CriterionSource.USER_CONFIRMED
            or not criterion.text.strip()
            or len(criterion.text) > 512
            or "\n" in criterion.text
            or "\r" in criterion.text
            or criterion.source_span is None
        ):
            raise R002AnnotationError("criteria_source_cache_manifest_mismatch")
        try:
            span = validate_r002_source_span(criterion.source_span)
            end = int(span.rsplit("-L", maxsplit=1)[1])
        except (TypeError, ValueError):
            raise R002AnnotationError("criteria_source_cache_manifest_mismatch") from None
        if end > line_count:
            raise R002AnnotationError("criteria_source_cache_manifest_mismatch")
    if not any(criterion.priority is Priority.MUST_HAVE for criterion in criteria):
        raise R002AnnotationError("criteria_source_cache_manifest_mismatch")


def build_criteria_proposal(
    manifest: R002SourceManifest,
    cache: R002Cache,
    criteria_by_case: Mapping[str, Sequence[Criterion]],
) -> R002CriteriaProposal:
    """Build an unconfirmed proposal using only pinned problem statements."""
    index = cache.load_criteria_source_index()
    manifest_hash = canonical_sha256(manifest)
    manifest_identity = tuple(
        (case.case_id, case.problem_statement_sha256) for case in manifest.cases
    )
    index_identity = tuple((case.case_id, case.problem_statement_sha256) for case in index.cases)
    if (
        index.source_sha256 != manifest.source.sha256
        or index.manifest_sha256 != manifest_hash
        or index_identity != manifest_identity
        or set(criteria_by_case) != {case.case_id for case in manifest.cases}
    ):
        raise R002AnnotationError("criteria_source_cache_manifest_mismatch")
    cases: list[R002CriterionReviewCase] = []
    for case in manifest.cases:
        try:
            body = cache.read_bytes(
                f"criteria-sources/{case.problem_statement_sha256}",
                expected_sha256=case.problem_statement_sha256,
            )
            problem_statement = body.decode("utf-8")
        except Exception:
            raise R002AnnotationError("problem_statement_hash_mismatch") from None
        if sha256(problem_statement.encode("utf-8")).hexdigest() != (case.problem_statement_sha256):
            raise R002AnnotationError("problem_statement_hash_mismatch")
        criteria = tuple(criteria_by_case[case.case_id])
        _validate_criterion_spans(
            criteria,
            line_count=len(_normalized_problem_lines(problem_statement)),
        )
        cases.append(
            R002CriterionReviewCase(
                case_id=case.case_id,
                problem_statement_sha256=case.problem_statement_sha256,
                problem_statement=problem_statement,
                criteria=criteria,
            )
        )
    return R002CriteriaProposal(
        source_manifest_sha256=manifest_hash,
        cases=tuple(cases),
    )


def confirmed_criteria_from_proposal(
    proposal: R002CriteriaProposal,
) -> R002CriteriaSet:
    """Create the owner-confirmed structural set; raw problem text is discarded."""
    return R002CriteriaSet(
        source_manifest_sha256=proposal.source_manifest_sha256,
        source_owner_confirmed=False,
        benchmark_owner_confirmed=True,
        cases=tuple(
            R002CriterionCase(
                case_id=case.case_id,
                problem_statement_sha256=case.problem_statement_sha256,
                criteria=case.criteria,
            )
            for case in proposal.cases
        ),
    )


@dataclass(frozen=True)
class _VerifiedLineIdentity:
    stream: str
    path: str
    hunk_id: str
    new_line_number: int
    normalized_line_sha256: str


@dataclass(frozen=True)
class _RawLineContext:
    line_content: str
    previous_line: str | None
    next_line: str | None


@dataclass(frozen=True)
class _R002AnnotationMaterial:
    case: R002CaseManifest
    criterion_case: R002CriterionCase
    cached_case: R002CachedCase
    contexts: Mapping[_VerifiedLineIdentity, _RawLineContext]


def _verified_line_identity(line: R002VerifiedLine) -> _VerifiedLineIdentity:
    return _VerifiedLineIdentity(
        stream=line.stream.value,
        path=line.path,
        hunk_id=line.hunk_id,
        new_line_number=line.new_line_number,
        normalized_line_sha256=line.normalized_line_sha256,
    )


def _raw_line_contexts(
    parsed: R002ParsedCase,
) -> dict[_VerifiedLineIdentity, _RawLineContext]:
    contexts: dict[_VerifiedLineIdentity, _RawLineContext] = {}
    for parsed_file in parsed.files:
        for hunk in parsed_file.hunks:
            new_side = tuple(
                line for line in hunk.lines if line.change_type is not LineChangeType.REMOVED
            )
            for position, line in enumerate(new_side):
                if line.new_line_number is None:
                    raise R002AnnotationError("prepared_cache_evidence_drift")
                identity = _VerifiedLineIdentity(
                    stream=parsed_file.stream.value,
                    path=parsed_file.path,
                    hunk_id=hunk.hunk_id,
                    new_line_number=line.new_line_number,
                    normalized_line_sha256=line.normalized_line_sha256,
                )
                if identity in contexts:
                    raise R002AnnotationError("prepared_cache_evidence_drift")
                contexts[identity] = _RawLineContext(
                    line_content=line.content,
                    previous_line=(new_side[position - 1].content if position > 0 else None),
                    next_line=(
                        new_side[position + 1].content if position + 1 < len(new_side) else None
                    ),
                )
    return contexts


def _load_annotation_material(
    case: R002CaseManifest,
    criterion_case: R002CriterionCase,
    cached_case: R002CachedCase,
    cache: R002Cache,
) -> _R002AnnotationMaterial:
    try:
        row = cache.read_model(
            f"rows/{case.row_sha256}",
            SWEbenchVerifiedRow,
        )
        if (
            canonical_sha256(row) != case.row_sha256
            or sha256(row.problem_statement.encode()).hexdigest() != case.problem_statement_sha256
            or sha256(row.patch.encode()).hexdigest() != case.patch_sha256
            or sha256(row.test_patch.encode()).hexdigest() != case.test_patch_sha256
        ):
            raise R002AnnotationError("prepared_cache_evidence_drift")
        parsed = parse_case_diffs(
            case_id=case.case_id,
            patch=row.patch,
            test_patch=row.test_patch,
        )
        if canonical_sha256(parsed) != cached_case.parsed_case_sha256:
            raise R002AnnotationError("prepared_cache_evidence_drift")
        head_file_bytes: dict[str, bytes] = {}
        for head_file in cached_case.head_files:
            if head_file.head_sha != case.verified_pr_head_sha:
                raise R002AnnotationError("prepared_cache_evidence_drift")
            content = cache.read_bytes(
                f"head-files/{head_file.content_sha256}",
                expected_sha256=head_file.content_sha256,
            )
            if len(content) != head_file.byte_length:
                raise R002AnnotationError("prepared_cache_evidence_drift")
            head_file_bytes[head_file.logical_path] = content
        rebound = verify_case_head_files(
            case=case,
            parsed=parsed,
            head_file_bytes=head_file_bytes,
        )
        if rebound.lines != cached_case.verified_lines:
            raise R002AnnotationError("prepared_cache_evidence_drift")
        contexts = _raw_line_contexts(parsed)
        expected = tuple(_verified_line_identity(line) for line in cached_case.verified_lines)
        if tuple(contexts) != expected:
            raise R002AnnotationError("prepared_cache_evidence_drift")
    except R002AnnotationError:
        raise
    except Exception:
        raise R002AnnotationError("prepared_cache_evidence_drift") from None
    return _R002AnnotationMaterial(
        case=case,
        criterion_case=criterion_case,
        cached_case=cached_case,
        contexts=contexts,
    )


def _annotation_pairs(
    material: _R002AnnotationMaterial,
) -> Iterator[tuple[R002CandidateLineKey, R002AnnotationReviewItem]]:
    for criterion in material.criterion_case.criteria:
        for verified_line in material.cached_case.verified_lines:
            context = material.contexts[_verified_line_identity(verified_line)]
            key = R002CandidateLineKey(
                case_id=material.case.case_id,
                criterion_id=criterion.criterion_id,
                stream=verified_line.stream,
                path=verified_line.path,
                new_line_number=verified_line.new_line_number,
                normalized_line_sha256=verified_line.normalized_line_sha256,
            )
            yield (
                key,
                R002AnnotationReviewItem(
                    key=key,
                    line_content=context.line_content,
                    previous_line=context.previous_line,
                    next_line=context.next_line,
                    relevant=None,
                    reason_code=None,
                ),
            )


def build_annotation_universe(
    *,
    manifest: R002SourceManifest,
    criteria: R002CriteriaSet,
    cache: R002Cache,
) -> R002AnnotationUniverse:
    """Freeze the exact post-confirmation criterion/candidate cross-product."""
    manifest_hash = canonical_sha256(manifest)
    criteria_hash = canonical_sha256(criteria)
    manifest_identity = tuple(
        (case.case_id, case.problem_statement_sha256) for case in manifest.cases
    )
    criteria_identity = tuple(
        (case.case_id, case.problem_statement_sha256) for case in criteria.cases
    )
    if (
        not criteria.benchmark_owner_confirmed
        or criteria.source_manifest_sha256 != manifest_hash
        or criteria_identity != manifest_identity
    ):
        raise R002AnnotationError("criteria_manifest_drift")
    try:
        index = cache.load_index()
    except Exception:
        raise R002AnnotationError("prepared_cache_criteria_drift") from None
    index_identity = tuple(
        (
            case.case_id,
            case.row_sha256,
            case.problem_statement_sha256,
            case.patch_sha256,
            case.test_patch_sha256,
        )
        for case in index.cases
    )
    manifest_cache_identity = tuple(
        (
            case.case_id,
            case.row_sha256,
            case.problem_statement_sha256,
            case.patch_sha256,
            case.test_patch_sha256,
        )
        for case in manifest.cases
    )
    if (
        index.source_sha256 != manifest.source.sha256
        or index.manifest_sha256 != manifest_hash
        or index.criteria_set_sha256 != criteria_hash
        or index_identity != manifest_cache_identity
    ):
        raise R002AnnotationError("prepared_cache_criteria_drift")
    materials = tuple(
        _load_annotation_material(case, criterion_case, cached_case, cache)
        for case, criterion_case, cached_case in zip(
            manifest.cases,
            criteria.cases,
            index.cases,
            strict=True,
        )
    )
    candidate_count = sum(
        len(material.cached_case.verified_lines) * len(material.criterion_case.criteria)
        for material in materials
    )
    if not 1 <= candidate_count <= 250_000:
        raise R002AnnotationError("annotation_pair_limit")
    try:
        universe, review = cache.write_annotation_pair(
            source_manifest_sha256=manifest_hash,
            criteria_set_sha256=criteria_hash,
            candidate_count=candidate_count,
            ordered_key_factory=lambda: (
                key for material in materials for key, _item in _annotation_pairs(material)
            ),
            ordered_item_factory=lambda: (
                item for material in materials for _key, item in _annotation_pairs(material)
            ),
        )
    except R002CacheError as error:
        if error.reason_code == "annotation_pair_limit":
            raise R002AnnotationError("annotation_pair_limit") from None
        raise
    except Exception:
        raise R002AnnotationError("prepared_cache_evidence_drift") from None
    if tuple(item.key for item in review.items) != universe.candidate_keys:
        raise R002AnnotationError("prepared_cache_evidence_drift")
    return universe


def annotate_r002(
    *,
    manifest_path: Path,
    criteria_path: Path,
    cache_root: Path,
) -> R002AnnotationUniverse:
    """Validate confirmation before opening the full evidence cache."""
    manifest = load_source_manifest(manifest_path)
    criteria = load_confirmed_criteria(
        criteria_path,
        canonical_sha256(manifest),
    )
    return build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=R002Cache(cache_root),
    )


def derive_expected_missing(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: Sequence[R002CandidateLabel],
) -> tuple[R002ExpectedMissing, ...]:
    del universe
    relevant_types: dict[tuple[str, str], set[EvidenceType]] = defaultdict(set)
    for label in labels:
        if label.relevant:
            relevant_types[(label.key.case_id, label.key.criterion_id)].add(
                classify_changed_path_evidence_type(label.key.path)
            )
    return tuple(
        R002ExpectedMissing(
            case_id=case.case_id,
            criterion_id=criterion.criterion_id,
            evidence_type=evidence_type,
            reason_code="no_owner_labelled_relevant_candidate",
        )
        for case in criteria.cases
        for criterion in case.criteria
        for evidence_type in R002_STATIC_EVIDENCE_TYPES
        if evidence_type not in relevant_types[(case.case_id, criterion.criterion_id)]
    )


def _validate_label_content(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: R002CandidateLabelProposal | R002CandidateLabelSet,
) -> None:
    label_type = (
        R002CandidateLabelProposal
        if type(labels) is R002CandidateLabelProposal
        else R002CandidateLabelSet
    )
    try:
        criteria = R002CriteriaSet.model_validate_json(canonical_json_bytes(criteria))
        universe = R002AnnotationUniverse.model_validate_json(canonical_json_bytes(universe))
        labels = label_type.model_validate_json(canonical_json_bytes(labels))
    except Exception:
        raise R002AnnotationError("reannotation_required") from None
    criteria_hash = canonical_sha256(criteria)
    if (
        universe.criteria_set_sha256 != criteria_hash
        or labels.criteria_set_sha256 != criteria_hash
        or labels.source_manifest_sha256 != criteria.source_manifest_sha256
        or universe.source_manifest_sha256 != criteria.source_manifest_sha256
    ):
        raise R002AnnotationError("label_upstream_hash_drift")
    criterion_identity = {
        (case.case_id, criterion.criterion_id)
        for case in criteria.cases
        for criterion in case.criteria
    }
    if any(
        (key.case_id, key.criterion_id) not in criterion_identity for key in universe.candidate_keys
    ):
        raise R002AnnotationError("annotation_criterion_drift")
    if (
        tuple(label.key for label in labels.labels) != universe.candidate_keys
        or labels.annotation_count != universe.candidate_count
        or labels.annotation_universe_sha256 != canonical_sha256(universe)
    ):
        raise R002AnnotationError("reannotation_required")
    if labels.expected_missing != derive_expected_missing(
        criteria,
        universe,
        labels.labels,
    ):
        raise R002AnnotationError("expected_missing_drift")


def validate_complete_label_proposal(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: R002CandidateLabelProposal,
) -> None:
    if labels.benchmark_owner_confirmed is not False:
        raise R002AnnotationError("label_proposal_must_be_unconfirmed")
    _validate_label_content(criteria, universe, labels)


def validate_complete_labels(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: R002CandidateLabelSet,
) -> None:
    if labels.benchmark_owner_confirmed is not True:
        raise R002AnnotationError("candidate_labels_not_confirmed")
    _validate_label_content(criteria, universe, labels)


class R002RunError(Exception):
    allowed_reason_codes = frozenset(
        {
            "run_input_drift",
            "reannotation_required",
            "expected_missing_label_conflict",
            "redaction_boundary_failed",
            "normalized_rerun_mismatch",
            "benchmark_gate_failed",
            "scopeproof_commit_required_outside_checkout",
            "scopeproof_git_probe_failed",
            "scopeproof_checkout_dirty",
            "scopeproof_head_invalid",
            "scopeproof_commit_mismatch",
        }
    )

    def __init__(self, reason_code: str) -> None:
        if reason_code not in self.allowed_reason_codes:
            raise RuntimeError("unregistered R-002 run reason code")
        self.reason_code = reason_code
        super().__init__(reason_code)


def build_r002_review(
    *,
    case: R002CaseManifest,
    row: SWEbenchVerifiedRow,
    criterion_case: R002CriterionCase,
    parsed: R002ParsedCase,
) -> ReviewBundle:
    """Run one historical case through the unchanged static product path."""
    observation = CIObservation(
        state=CheckState.UNAVAILABLE,
        reason="No check runs or concrete legacy statuses were observed.",
        reason_code=CIReasonCode.NO_OBSERVATIONS,
        collection_complete=True,
    )
    snapshot = PullRequestSnapshot(
        repository=case.repository,
        pr_number=case.pr_number,
        title=f"R-002 {case.case_id}",
        description="",
        html_url=case.pr_url,
        base_sha=case.dataset_base_commit,
        head_sha=case.verified_pr_head_sha,
        check_state=CheckState.UNAVAILABLE,
        ci_observation=observation,
        ingestion_state=IngestionState.COMPLETE,
        files=parsed_case_to_changed_files(parsed),
    )
    review = Review(
        repository=case.repository,
        pr_number=case.pr_number,
        base_sha=case.dataset_base_commit,
        head_sha=case.verified_pr_head_sha,
        check_state=CheckState.UNAVAILABLE,
        ci_observation=observation,
        criteria_confirmed=True,
        ingestion_state=IngestionState.COMPLETE,
        final_acceptance=False,
    )
    criteria = [item.model_copy(deep=True) for item in criterion_case.criteria]
    evidence = retrieve_evidence(snapshot, criteria)
    findings = build_findings(criteria, evidence, IngestionState.COMPLETE)
    gate = evaluate_gate(review, criteria, findings, [])
    return ReviewBundle(
        review=review,
        source_text=row.problem_statement,
        criteria=criteria,
        evidence=evidence,
        runtime_evidence=[],
        findings=findings,
        resolutions=[],
        gate=gate,
        research_context=ResearchContext(
            case_id=case.case_id,
            boundary_note=(
                "Public engineering research only; this case is not customer or Alpha "
                "validation and does not advance Stage 1."
            ),
        ),
    )


def _build_missing_explanations(
    *,
    case: R002CaseManifest,
    findings: Sequence[Finding],
    retrieved: Sequence[R002RetrievedCandidate],
    expected_missing: Sequence[R002ExpectedMissing],
) -> tuple[R002MissingExplanation, ...]:
    finding_by_id: dict[str, Finding] = {}
    for finding in findings:
        if finding.criterion_id in finding_by_id:
            raise R002RunError("benchmark_gate_failed")
        finding_by_id[finding.criterion_id] = finding
    explanations: list[R002MissingExplanation] = []
    for expected in expected_missing:
        if expected.case_id != case.case_id:
            continue
        finding = finding_by_id.get(expected.criterion_id)
        if finding is None:
            continue
        matching = tuple(
            item
            for item in retrieved
            if item.key.criterion_id == expected.criterion_id
            and item.evidence_type is expected.evidence_type
        )
        if any(item.owner_label_relevant for item in matching):
            raise R002RunError("expected_missing_label_conflict")
        if any(value.strip() for value in finding.missing_evidence):
            source = "scopeproof_finding"
            reason = "scopeproof_finding_explicit_gap"
            status = finding.status
        elif not matching:
            source = "r002_retrieval_comparison"
            reason = "no_candidate_retrieved_for_type"
            status = FindingStatus.EVIDENCE_FOUND
        else:
            source = "r002_retrieval_comparison"
            reason = "retrieved_only_owner_labelled_irrelevant"
            status = FindingStatus.EVIDENCE_FOUND
        explanations.append(
            R002MissingExplanation(
                case_id=case.case_id,
                criterion_id=expected.criterion_id,
                evidence_type=expected.evidence_type,
                source=source,
                finding_status=status,
                reason_code=reason,
            )
        )
    return tuple(
        sorted(
            explanations,
            key=lambda item: (
                item.case_id,
                item.criterion_id,
                item.evidence_type.value,
            ),
        )
    )


def evaluate_r002_case(
    *,
    case: R002CaseManifest,
    bundle: ReviewBundle,
    verified: R002VerifiedCaseLines,
    label_by_key: Mapping[R002CandidateLineKey, R002CandidateLabel],
    expected_missing: Sequence[R002ExpectedMissing],
) -> R002CaseResult:
    retrieved: list[R002RetrievedCandidate] = []
    for evidence in bundle.evidence:
        try:
            key = verify_evidence_reference(
                case=case,
                evidence=evidence,
                verified_lines=verified,
            )
        except Exception:
            raise R002RunError("run_input_drift") from None
        label = label_by_key.get(key)
        if label is None:
            raise R002RunError("reannotation_required")
        line = verified.by_path_and_line(evidence.file_path, evidence.line_start)
        retrieved.append(
            R002RetrievedCandidate(
                key=key,
                evidence_type=evidence.evidence_type,
                evidence_level=evidence.evidence_level,
                hunk_id=line.hunk_id,
                head_file_sha256=line.head_file_sha256,
                matching_rule=evidence.matching_rule,
                relevance_score=evidence.relevance_score,
                owner_label_relevant=label.relevant,
            )
        )
    explanations = _build_missing_explanations(
        case=case,
        findings=bundle.findings,
        retrieved=retrieved,
        expected_missing=expected_missing,
    )
    if len(bundle.gate.reason_codes) != len(set(bundle.gate.reason_codes)):
        raise R002RunError("benchmark_gate_failed")
    return R002CaseResult(
        case_id=case.case_id,
        repository=case.repository,
        pr_number=case.pr_number,
        head_sha=case.verified_pr_head_sha,
        criterion_count=len(bundle.criteria),
        annotation_candidate_count=sum(key.case_id == case.case_id for key in label_by_key),
        retrieved_candidates=tuple(retrieved),
        missing_explanations=explanations,
        gate_verdict=bundle.gate.verdict,
        gate_reason_codes=tuple(sorted(bundle.gate.reason_codes)),
        blocking_criteria=tuple(bundle.gate.blocking_criteria),
        conditional_criteria=tuple(bundle.gate.conditional_criteria),
        unresolved_criteria=tuple(bundle.gate.unresolved_criteria),
        check_state=bundle.review.check_state,
        ci_reason_code=bundle.review.ci_observation.reason_code,
        runtime_evidence_count=len(bundle.runtime_evidence),
        resolution_count=len(bundle.resolutions),
        final_acceptance=bundle.review.final_acceptance,
        separation_errors=0,
        reference_errors=0,
        limitations=R002_RESULT_LIMITATIONS,
    )


def metric(numerator: int, denominator: int) -> R002Metric:
    if denominator == 0:
        return R002Metric(
            state=R002MetricState.NOT_APPLICABLE,
            numerator=numerator,
            denominator=0,
            value=None,
        )
    return R002Metric(
        state=R002MetricState.VALUE,
        numerator=numerator,
        denominator=denominator,
        value=numerator / denominator,
    )


def calculate_metrics(
    cases: Sequence[R002CaseResult],
    universe: R002AnnotationUniverse,
    labels: R002CandidateLabelSet,
    parsed_cases: Mapping[str, R002ParsedCase],
) -> R002Metrics:
    del universe
    retrieved = {item.key: item for case in cases for item in case.retrieved_candidates}
    relevant_keys = {label.key for label in labels.labels if label.relevant}
    criteria_with_gold = {(key.case_id, key.criterion_id) for key in relevant_keys}
    criteria_with_retrieved_gold = {
        (key.case_id, key.criterion_id) for key in retrieved if key in relevant_keys
    }
    all_paths = {
        (case_id, file.stream, file.path)
        for case_id, parsed in parsed_cases.items()
        for file in parsed.files
    }
    hit_paths = {(key.case_id, key.stream, key.path) for key in retrieved}
    all_hunks = {
        (case_id, hunk.hunk_id)
        for case_id, parsed in parsed_cases.items()
        for file in parsed.files
        for hunk in file.hunks
    }
    hit_hunks = {(item.key.case_id, item.hunk_id) for item in retrieved.values()}
    explanations = {
        (item.case_id, item.criterion_id, item.evidence_type)
        for case in cases
        for item in case.missing_explanations
    }
    expected = {
        (item.case_id, item.criterion_id, item.evidence_type) for item in labels.expected_missing
    }
    return R002Metrics(
        owner_confirmed_label_candidate_precision=metric(
            len(set(retrieved) & relevant_keys),
            len(retrieved),
        ),
        criterion_candidate_coverage=metric(
            len(criteria_with_retrieved_gold),
            len(criteria_with_gold),
        ),
        candidate_to_gold_file_coverage=metric(
            len(hit_paths),
            len(all_paths),
        ),
        candidate_to_gold_hunk_coverage=metric(
            len(hit_hunks),
            len(all_hunks),
        ),
        missing_evidence_explanation_completeness=metric(
            len(explanations & expected),
            len(expected),
        ),
        implementation_test_separation_errors=sum(case.separation_errors for case in cases),
        immutable_reference_integrity_errors=sum(case.reference_errors for case in cases),
        parse_errors=0,
        schema_errors=0,
        source_hash_errors=0,
        source_sha_errors=0,
        unexpected_ready_count=sum(case.gate_verdict is GateVerdict.READY for case in cases),
        normalized_rerun_mismatches=0,
    )


def build_determinism_projection(
    result: R002BenchmarkResult,
) -> R002DeterminismProjection:
    return R002DeterminismProjection(
        source_manifest_sha256=result.source_manifest_sha256,
        criteria_set_sha256=result.criteria_set_sha256,
        candidate_label_set_sha256=result.candidate_label_set_sha256,
        scopeproof_commit=result.scopeproof_commit,
        case_results=result.case_results,
        metrics=result.metrics,
        limitations=result.limitations,
    )


def _hard_gate_codes(
    cases: Sequence[R002CaseResult],
    metrics: R002Metrics,
    labels: R002CandidateLabelSet,
) -> tuple[str, ...]:
    codes: set[str] = set()
    if len(cases) != 20:
        codes.add("case_count_invalid")
    if any(
        (
            case.check_state is not CheckState.UNAVAILABLE
            or case.ci_reason_code is not CIReasonCode.NO_OBSERVATIONS
            or case.runtime_evidence_count
            or case.resolution_count
            or case.final_acceptance
        )
        for case in cases
    ):
        codes.add("static_research_boundary_invalid")
    if any(case.separation_errors or case.reference_errors for case in cases) or any(
        (
            metrics.implementation_test_separation_errors,
            metrics.immutable_reference_integrity_errors,
            metrics.parse_errors,
            metrics.schema_errors,
            metrics.source_hash_errors,
            metrics.source_sha_errors,
        )
    ):
        codes.add("integrity_error")
    expected_missing = {
        (item.case_id, item.criterion_id, item.evidence_type) for item in labels.expected_missing
    }
    observed_missing = {
        (item.case_id, item.criterion_id, item.evidence_type)
        for case in cases
        for item in case.missing_explanations
    }
    if observed_missing != expected_missing:
        codes.add("missing_explanation_incomplete")
    if metrics.unexpected_ready_count or any(
        case.gate_verdict is GateVerdict.READY for case in cases
    ):
        codes.add("unexpected_ready")
    if metrics.normalized_rerun_mismatches:
        codes.add("rerun_mismatch")
    return tuple(sorted(codes))


_R002_FORBIDDEN_EXPORT_KEYS = frozenset(
    {
        "problem_statement",
        "patch",
        "test_patch",
        "hints_text",
        "source_text",
        "excerpt",
        "context_excerpt",
        "etag",
        "last_modified",
        "response_headers",
        "request_headers",
        "http_headers",
    }
)
_R002_HTTP_METADATA_LABEL = re.compile(
    r"(?i)(?:^|[\s|`\"'])(?:etag|last[-_ ]modified|"
    r"response[-_ ]headers?|request[-_ ]headers?|http[-_ ]headers?)\s*[:=]"
)
_R002_UUID_PATTERN = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"
)
_R002_TIMESTAMP_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})\b"
)


def _decoded_json_list(value: str) -> tuple[str, ...]:
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        raise R002RunError("redaction_boundary_failed") from None
    if not isinstance(decoded, list) or any(not isinstance(item, str) for item in decoded):
        raise R002RunError("redaction_boundary_failed")
    return tuple(item for item in decoded if item)


def _walk_json_strings(
    value: Any,
    *,
    key: str | None = None,
) -> Iterator[tuple[str | None, str]]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            if not isinstance(child_key, str):
                raise R002RunError("redaction_boundary_failed")
            yield from _walk_json_strings(child, key=child_key)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json_strings(child, key=key)
    elif isinstance(value, str):
        yield key, value


def _add_redaction_value(
    values: set[str],
    value: str,
    *,
    byte_count: list[int],
) -> None:
    if not value.strip() or value in values:
        return
    encoded_length = len(value.encode("utf-8"))
    if byte_count[0] + encoded_length > R002_REDACTION_RAW_VALUE_MAX_BYTES:
        raise R002RunError("redaction_boundary_failed")
    values.add(value)
    byte_count[0] += encoded_length


def _redaction_reference_values(
    cache: R002Cache,
    *,
    cache_path: str,
) -> tuple[set[str], set[str]]:
    bodies: set[str] = set()
    scalars: set[str] = set()
    byte_count = [0]
    index = cache.load_index()
    for cached_case in index.cases:
        row = cache.read_model(f"rows/{cached_case.row_sha256}", SWEbenchVerifiedRow)
        for body in (
            row.problem_statement,
            row.patch,
            row.test_patch,
            row.hints_text,
        ):
            _add_redaction_value(bodies, body, byte_count=byte_count)
        for scalar in (
            *_decoded_json_list(row.FAIL_TO_PASS),
            *_decoded_json_list(row.PASS_TO_PASS),
            row.created_at,
        ):
            _add_redaction_value(scalars, scalar, byte_count=byte_count)
        bundle = cache.read_model(
            f"reviews/{cached_case.case_id}.json",
            ReviewBundle,
        )
        payload = bundle.model_dump(mode="json")
        for key, value in _walk_json_strings(payload):
            if key in {"source_text", "excerpt", "context_excerpt"}:
                _add_redaction_value(bodies, value, byte_count=byte_count)
            if key and (
                _R002_UUID_PATTERN.fullmatch(value) or _R002_TIMESTAMP_PATTERN.fullmatch(value)
            ):
                _add_redaction_value(scalars, value, byte_count=byte_count)
    _add_redaction_value(scalars, cache_path, byte_count=byte_count)
    return bodies, scalars


def _open_redaction_candidate(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise R002RunError("redaction_boundary_failed") from None
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size > R002_REDACTION_TRACKED_FILE_MAX_BYTES
        ):
            raise R002RunError("redaction_boundary_failed")
        chunks: list[bytes] = []
        remaining = R002_REDACTION_TRACKED_FILE_MAX_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > R002_REDACTION_TRACKED_FILE_MAX_BYTES:
            raise R002RunError("redaction_boundary_failed")
        return data
    finally:
        os.close(descriptor)


def _assert_safe_scalar(
    value: str,
    *,
    bodies: set[str],
    scalars: set[str],
    cache_path: str,
) -> None:
    if (
        value in bodies
        or value in scalars
        or cache_path in value
        or _R002_UUID_PATTERN.search(value)
        or _R002_TIMESTAMP_PATTERN.search(value)
        or _R002_HTTP_METADATA_LABEL.search(value)
        or any(len(body.encode("utf-8")) >= 32 and body in value for body in bodies)
    ):
        raise R002RunError("redaction_boundary_failed")


def _text_logical_scalars(text: str) -> Iterator[str]:
    for raw_line in text.splitlines():
        line = re.sub(r"^\s*(?:#{1,6}\s+|>\s*|[-+*]\s+|\d+[.)]\s+)", "", raw_line)
        for cell in line.split("|"):
            scalar = cell.strip().strip("`\"'")
            if scalar:
                yield scalar
            for inline in re.findall(r"`([^`\n]+)`", cell):
                if inline:
                    yield inline


def audit_r002_redaction(
    *,
    cache_root: Path,
    candidate_paths: Sequence[Path],
) -> R002RedactionAudit:
    """Fail closed when a proposed tracked artifact leaks local-only R-002 data."""
    if not candidate_paths:
        raise R002RunError("redaction_boundary_failed")
    try:
        cache = R002Cache(cache_root)
        cache_path = str(cache_root.resolve())
        bodies, scalars = _redaction_reference_values(
            cache,
            cache_path=cache_path,
        )
        checked_files: set[Path] = set()
        for candidate in candidate_paths:
            absolute = candidate.resolve(strict=False)
            if absolute in checked_files:
                continue
            checked_files.add(absolute)
            data = _open_redaction_candidate(candidate)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                raise R002RunError("redaction_boundary_failed") from None
            if candidate.suffix.lower() == ".json":
                try:
                    decoded = json.loads(text)
                except ValueError:
                    raise R002RunError("redaction_boundary_failed") from None
                for key, value in _walk_json_strings(decoded):
                    if key in _R002_FORBIDDEN_EXPORT_KEYS:
                        raise R002RunError("redaction_boundary_failed")
                    _assert_safe_scalar(
                        value,
                        bodies=bodies,
                        scalars=scalars,
                        cache_path=cache_path,
                    )
            else:
                for scalar in _text_logical_scalars(text):
                    _assert_safe_scalar(
                        scalar,
                        bodies=bodies,
                        scalars=scalars,
                        cache_path=cache_path,
                    )
        value_hashes = tuple(
            sorted(sha256(value.encode("utf-8")).hexdigest() for value in bodies | scalars)
        )
        return R002RedactionAudit(
            tracked_file_count=len(checked_files),
            raw_value_count=len(value_hashes),
            checked_value_sha256=value_hashes,
        )
    except R002RunError:
        raise
    except Exception:
        raise R002RunError("redaction_boundary_failed") from None


@dataclass(frozen=True)
class _R002PreparedRunCase:
    case: R002CaseManifest
    criterion_case: R002CriterionCase
    row: SWEbenchVerifiedRow
    parsed: R002ParsedCase
    verified: R002VerifiedCaseLines


def _prepare_run_cases(
    *,
    manifest: R002SourceManifest,
    criteria: R002CriteriaSet,
    cache: R002Cache,
) -> tuple[_R002PreparedRunCase, ...]:
    try:
        index = cache.load_index()
        manifest_hash = canonical_sha256(manifest)
        criteria_hash = canonical_sha256(criteria)
        if (
            index.source_sha256 != manifest.source.sha256
            or index.manifest_sha256 != manifest_hash
            or index.criteria_set_sha256 != criteria_hash
        ):
            raise R002RunError("run_input_drift")
        prepared: list[_R002PreparedRunCase] = []
        for case, criterion_case, cached_case in zip(
            manifest.cases,
            criteria.cases,
            index.cases,
            strict=True,
        ):
            if (
                case.case_id != criterion_case.case_id
                or case.case_id != cached_case.case_id
                or case.problem_statement_sha256 != criterion_case.problem_statement_sha256
                or (
                    case.row_sha256,
                    case.problem_statement_sha256,
                    case.patch_sha256,
                    case.test_patch_sha256,
                )
                != (
                    cached_case.row_sha256,
                    cached_case.problem_statement_sha256,
                    cached_case.patch_sha256,
                    cached_case.test_patch_sha256,
                )
            ):
                raise R002RunError("run_input_drift")
            row = cache.read_model(
                f"rows/{case.row_sha256}",
                SWEbenchVerifiedRow,
            )
            if (
                canonical_sha256(row) != case.row_sha256
                or sha256(row.problem_statement.encode()).hexdigest()
                != case.problem_statement_sha256
                or sha256(row.patch.encode()).hexdigest() != case.patch_sha256
                or sha256(row.test_patch.encode()).hexdigest() != case.test_patch_sha256
            ):
                raise R002RunError("run_input_drift")
            parsed = parse_case_diffs(
                case_id=case.case_id,
                patch=row.patch,
                test_patch=row.test_patch,
            )
            if canonical_sha256(parsed) != cached_case.parsed_case_sha256:
                raise R002RunError("run_input_drift")
            head_bytes: dict[str, bytes] = {}
            for head_file in cached_case.head_files:
                if head_file.head_sha != case.verified_pr_head_sha:
                    raise R002RunError("run_input_drift")
                content = cache.read_bytes(
                    f"head-files/{head_file.content_sha256}",
                    expected_sha256=head_file.content_sha256,
                )
                if len(content) != head_file.byte_length:
                    raise R002RunError("run_input_drift")
                head_bytes[head_file.logical_path] = content
            verified = verify_case_head_files(
                case=case,
                parsed=parsed,
                head_file_bytes=head_bytes,
            )
            if verified.lines != cached_case.verified_lines:
                raise R002RunError("run_input_drift")
            prepared.append(
                _R002PreparedRunCase(
                    case=case,
                    criterion_case=criterion_case,
                    row=row,
                    parsed=parsed,
                    verified=verified,
                )
            )
    except R002RunError:
        raise
    except Exception:
        raise R002RunError("run_input_drift") from None
    return tuple(prepared)


def _execute_r002_pass(
    *,
    prepared: Sequence[_R002PreparedRunCase],
    labels: R002CandidateLabelSet,
    universe: R002AnnotationUniverse,
    scopeproof_commit: str,
    manifest_hash: str,
    criteria_hash: str,
    labels_hash: str,
    cache: R002Cache,
    save_reviews: bool,
) -> R002BenchmarkResult:
    label_by_key = {label.key: label for label in labels.labels}
    case_results: list[R002CaseResult] = []
    parsed_by_case: dict[str, R002ParsedCase] = {}
    for item in prepared:
        bundle = build_r002_review(
            case=item.case,
            row=item.row,
            criterion_case=item.criterion_case,
            parsed=item.parsed,
        )
        if save_reviews:
            cache.replace_model(
                f"reviews/{item.case.case_id}.json",
                bundle,
            )
        case_results.append(
            evaluate_r002_case(
                case=item.case,
                bundle=bundle,
                verified=item.verified,
                label_by_key=label_by_key,
                expected_missing=labels.expected_missing,
            )
        )
        parsed_by_case[item.case.case_id] = item.parsed
    metrics = calculate_metrics(
        case_results,
        universe,
        labels,
        parsed_by_case,
    )
    hard_gate_errors = _hard_gate_codes(case_results, metrics, labels)
    if hard_gate_errors:
        raise R002RunError("benchmark_gate_failed")
    return R002BenchmarkResult(
        source_manifest_sha256=manifest_hash,
        criteria_set_sha256=criteria_hash,
        candidate_label_set_sha256=labels_hash,
        scopeproof_commit=scopeproof_commit,
        executed_case_count=20,
        failed_case_count=0,
        skipped_case_count=0,
        confirmed_criterion_count=sum(len(item.criterion_case.criteria) for item in prepared),
        annotation_candidate_count=universe.candidate_count,
        case_results=tuple(case_results),
        metrics=metrics,
        unexpected_ready_count=metrics.unexpected_ready_count,
        normalized_rerun_mismatches=0,
        hard_gate_errors=hard_gate_errors,
        limitations=R002_RESULT_LIMITATIONS,
    )


def run_r002(
    *,
    manifest_path: Path,
    criteria_path: Path,
    labels_path: Path,
    cache_root: Path,
    scopeproof_commit: str,
) -> R002BenchmarkResult:
    """Execute all 20 cases twice and return only a deterministic redacted result."""
    try:
        manifest = load_source_manifest(manifest_path)
        manifest_hash = canonical_sha256(manifest)
        criteria = load_confirmed_criteria(criteria_path, manifest_hash)
        criteria_hash = canonical_sha256(criteria)
        labels = load_confirmed_labels(
            labels_path,
            manifest_hash,
            criteria_hash,
        )
        labels_hash = canonical_sha256(labels)
        cache = R002Cache(cache_root)
        universe = cache.read_model(
            "annotation-universe.json",
            R002AnnotationUniverse,
        )
        if (
            universe.source_manifest_sha256 != manifest_hash
            or universe.criteria_set_sha256 != criteria_hash
            or labels.annotation_universe_sha256 != canonical_sha256(universe)
        ):
            raise R002RunError("run_input_drift")
        validate_complete_labels(criteria, universe, labels)
        prepared = _prepare_run_cases(
            manifest=manifest,
            criteria=criteria,
            cache=cache,
        )
        first = _execute_r002_pass(
            prepared=prepared,
            labels=labels,
            universe=universe,
            scopeproof_commit=scopeproof_commit,
            manifest_hash=manifest_hash,
            criteria_hash=criteria_hash,
            labels_hash=labels_hash,
            cache=cache,
            save_reviews=True,
        )
        for item in prepared:
            cache.read_model(
                f"reviews/{item.case.case_id}.json",
                ReviewBundle,
            )
        second = _execute_r002_pass(
            prepared=prepared,
            labels=labels,
            universe=universe,
            scopeproof_commit=scopeproof_commit,
            manifest_hash=manifest_hash,
            criteria_hash=criteria_hash,
            labels_hash=labels_hash,
            cache=cache,
            save_reviews=False,
        )
        first_projection = build_determinism_projection(first)
        second_projection = build_determinism_projection(second)
        case_mismatches = sum(
            canonical_sha256(left) != canonical_sha256(right)
            for left, right in zip(
                first.case_results,
                second.case_results,
                strict=True,
            )
        )
        if (
            case_mismatches
            or first.metrics != second.metrics
            or canonical_sha256(first_projection) != canonical_sha256(second_projection)
        ):
            raise R002RunError("normalized_rerun_mismatch")
        return first
    except R002RunError:
        raise
    except Exception:
        raise R002RunError("run_input_drift") from None
