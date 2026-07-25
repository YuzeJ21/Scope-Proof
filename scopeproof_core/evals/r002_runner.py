"""Offline, two-pass annotation and execution helpers for R-002."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from scopeproof_core.evals.r002_cache import R002Cache, R002CacheError
from scopeproof_core.evals.r002_diff import parse_case_diffs
from scopeproof_core.evals.r002_models import (
    R002_STATIC_EVIDENCE_TYPES,
    R002AnnotationError,
    R002AnnotationReviewItem,
    R002AnnotationUniverse,
    R002CachedCase,
    R002CandidateLabel,
    R002CandidateLabelProposal,
    R002CandidateLabelSet,
    R002CandidateLineKey,
    R002CaseManifest,
    R002CriteriaProposal,
    R002CriteriaSet,
    R002CriterionCase,
    R002CriterionReviewCase,
    R002ExpectedMissing,
    R002ParsedCase,
    R002SourceManifest,
    R002VerifiedLine,
    SWEbenchVerifiedRow,
    canonical_json_bytes,
    canonical_sha256,
    load_confirmed_criteria,
    load_source_manifest,
    validate_r002_source_span,
)
from scopeproof_core.evals.r002_verify import verify_case_head_files
from scopeproof_core.retrieval.engine import classify_changed_path_evidence_type
from scopeproof_core.schemas.models import (
    Criterion,
    CriterionSource,
    EvidenceType,
    LineChangeType,
    Priority,
)


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
            raise R002AnnotationError(
                "criteria_source_cache_manifest_mismatch"
            ) from None
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
    index_identity = tuple(
        (case.case_id, case.problem_statement_sha256) for case in index.cases
    )
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
        if sha256(problem_statement.encode("utf-8")).hexdigest() != (
            case.problem_statement_sha256
        ):
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
                line
                for line in hunk.lines
                if line.change_type is not LineChangeType.REMOVED
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
                    previous_line=(
                        new_side[position - 1].content if position > 0 else None
                    ),
                    next_line=(
                        new_side[position + 1].content
                        if position + 1 < len(new_side)
                        else None
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
            or sha256(row.problem_statement.encode()).hexdigest()
            != case.problem_statement_sha256
            or sha256(row.patch.encode()).hexdigest() != case.patch_sha256
            or sha256(row.test_patch.encode()).hexdigest()
            != case.test_patch_sha256
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
        expected = tuple(
            _verified_line_identity(line) for line in cached_case.verified_lines
        )
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
            yield key, R002AnnotationReviewItem(
                key=key,
                line_content=context.line_content,
                previous_line=context.previous_line,
                next_line=context.next_line,
                relevant=None,
                reason_code=None,
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
        len(material.cached_case.verified_lines)
        * len(material.criterion_case.criteria)
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
                key
                for material in materials
                for key, _item in _annotation_pairs(material)
            ),
            ordered_item_factory=lambda: (
                item
                for material in materials
                for _key, item in _annotation_pairs(material)
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
        if evidence_type
        not in relevant_types[(case.case_id, criterion.criterion_id)]
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
        universe = R002AnnotationUniverse.model_validate_json(
            canonical_json_bytes(universe)
        )
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
        (key.case_id, key.criterion_id) not in criterion_identity
        for key in universe.candidate_keys
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
