"""Two-pass isolation and completeness tests for R-002 annotation."""

from __future__ import annotations

import json
import threading
from hashlib import sha256
from pathlib import Path

import pytest

from scopeproof_core.evals import r002_runner
from scopeproof_core.evals.r002_cache import R002Cache, R002CacheError
from scopeproof_core.evals.r002_diff import parse_case_diffs
from scopeproof_core.evals.r002_models import (
    R002AnnotationError,
    R002AnnotationReview,
    R002AnnotationReviewItem,
    R002AnnotationUniverse,
    R002CachedCase,
    R002CachedHeadFile,
    R002CacheIndex,
    R002CandidateLabel,
    R002CandidateLabelProposal,
    R002CandidateLabelSet,
    R002CandidateLineKey,
    R002CriteriaSet,
    R002CriteriaSourceCase,
    R002CriteriaSourceIndex,
    R002DiffStream,
    R002SourceManifest,
    SWEbenchVerifiedRow,
    canonical_sha256,
)
from scopeproof_core.evals.r002_runner import (
    _validate_criterion_spans,
    build_annotation_universe,
    build_criteria_proposal,
    confirmed_criteria_from_proposal,
    derive_expected_missing,
    validate_complete_label_proposal,
    validate_complete_labels,
)
from scopeproof_core.evals.r002_verify import verify_case_head_files
from scopeproof_core.schemas.models import (
    Criterion,
    CriterionSource,
    CriterionType,
    EvidenceLevel,
    Priority,
)


def _criterion() -> Criterion:
    return Criterion(
        criterion_id="AC-01",
        text="The changed behavior is present.",
        priority=Priority.MUST_HAVE,
        criterion_type=CriterionType.BEHAVIOR,
        criterion_source=CriterionSource.USER_CONFIRMED,
        source_span="problem_statement:L1-L1",
        required_evidence_level=EvidenceLevel.E1,
    )


def _manifest_with_problem_sources(
    payload: dict[str, object],
) -> tuple[R002SourceManifest, dict[str, bytes]]:
    sources: dict[str, bytes] = {}
    cases = []
    for number, case in enumerate(payload["cases"], start=1):  # type: ignore[index]
        body = f"Problem statement {number}.".encode()
        digest = sha256(body).hexdigest()
        cases.append({**case, "problem_statement_sha256": digest})
        sources[digest] = body
    prepared = {**payload, "cases": cases}
    return R002SourceManifest.model_validate_json(json.dumps(prepared)), sources


class _RecordingCriteriaCache:
    def __init__(
        self,
        manifest: R002SourceManifest,
        sources: dict[str, bytes],
    ) -> None:
        self.sources = dict(sources)
        self.criteria_source_reads: set[str] = set()
        self.row_reads = 0
        self.index = R002CriteriaSourceIndex(
            source_sha256=manifest.source.sha256,
            manifest_sha256=canonical_sha256(manifest),
            cases=tuple(
                R002CriteriaSourceCase(
                    case_id=case.case_id,
                    problem_statement_sha256=case.problem_statement_sha256,
                    byte_length=len(sources[case.problem_statement_sha256]),
                )
                for case in manifest.cases
            ),
        )

    def load_criteria_source_index(self) -> R002CriteriaSourceIndex:
        return self.index

    def read_bytes(self, relative_name: str, *, expected_sha256: str) -> bytes:
        digest = relative_name.removeprefix("criteria-sources/")
        assert digest == expected_sha256
        self.criteria_source_reads.add(digest)
        return self.sources[digest]

    def read_model(self, *args: object, **kwargs: object) -> object:
        del args, kwargs
        self.row_reads += 1
        raise AssertionError("criteria proposal must not read full rows")


def _criteria_by_case(
    manifest: R002SourceManifest,
) -> dict[str, tuple[Criterion, ...]]:
    return {case.case_id: (_criterion(),) for case in manifest.cases}


def test_criteria_proposal_reads_problem_statements_only(
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, sources = _manifest_with_problem_sources(r002_manifest_payload)
    cache = _RecordingCriteriaCache(manifest, sources)

    proposal = build_criteria_proposal(
        manifest,
        cache,  # type: ignore[arg-type]
        _criteria_by_case(manifest),
    )

    assert proposal.benchmark_owner_confirmed is False
    assert proposal.source_owner_confirmed is False
    assert cache.criteria_source_reads == set(sources)
    assert cache.row_reads == 0
    assert all(case.problem_statement.startswith("Problem statement") for case in proposal.cases)
    confirmed = confirmed_criteria_from_proposal(proposal)
    assert confirmed.benchmark_owner_confirmed is True
    assert confirmed.source_owner_confirmed is False
    assert all(
        "problem_statement" not in type(case).model_fields for case in confirmed.cases
    )


def _prepared_annotation_inputs(
    tmp_path: Path,
    payload: dict[str, object],
) -> tuple[R002SourceManifest, R002CriteriaSet, R002Cache]:
    manifest, sources = _manifest_with_problem_sources(payload)
    cache = R002Cache(tmp_path / "cache")
    manifest_cases = []
    cached_cases = []
    for number, case in enumerate(manifest.cases, start=1):
        path = f"src/file_{number}.py"
        content = f"new-{number}"
        patch = (
            f"diff --git a/{path} b/{path}\n"
            f"--- a/{path}\n"
            f"+++ b/{path}\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            f"+{content}\n"
        )
        row = SWEbenchVerifiedRow(
            repo=case.repository,
            instance_id=case.instance_id,
            base_commit=case.dataset_base_commit,
            patch=patch,
            test_patch="",
            problem_statement=sources[case.problem_statement_sha256].decode(),
            hints_text="",
            created_at="2026-01-01",
            version="1",
            FAIL_TO_PASS="[]",
            PASS_TO_PASS="[]",
            environment_setup_commit="",
            difficulty=case.difficulty,
        )
        prepared_case = case.model_copy(
            update={
                "row_sha256": canonical_sha256(row),
                "patch_sha256": sha256(patch.encode()).hexdigest(),
                "test_patch_sha256": sha256(b"").hexdigest(),
            }
        )
        parsed = parse_case_diffs(
            case_id=case.case_id,
            patch=patch,
            test_patch="",
        )
        head = f"{content}\n".encode()
        verified = verify_case_head_files(
            case=prepared_case,
            parsed=parsed,
            head_file_bytes={path: head},
        )
        cache.write_content_addressed_model(
            f"rows/{prepared_case.row_sha256}",
            row,
            SWEbenchVerifiedRow,
        )
        head_digest = sha256(head).hexdigest()
        cache.write_bytes(f"head-files/{head_digest}", head)
        manifest_cases.append(prepared_case)
        cached_cases.append(
            R002CachedCase(
                case_id=case.case_id,
                row_sha256=prepared_case.row_sha256,
                problem_statement_sha256=prepared_case.problem_statement_sha256,
                patch_sha256=prepared_case.patch_sha256,
                test_patch_sha256=prepared_case.test_patch_sha256,
                parsed_case_sha256=canonical_sha256(parsed),
                verified_lines=verified.lines,
                head_files=(
                    R002CachedHeadFile(
                        logical_path=path,
                        head_sha=prepared_case.verified_pr_head_sha,
                        byte_length=len(head),
                        content_sha256=head_digest,
                    ),
                ),
            )
        )
    manifest = manifest.model_copy(update={"cases": tuple(manifest_cases)})
    for digest, body in sources.items():
        cache.write_bytes(f"criteria-sources/{digest}", body)
    cache.publish_criteria_source_index(
        R002CriteriaSourceIndex(
            source_sha256=manifest.source.sha256,
            manifest_sha256=canonical_sha256(manifest),
            cases=tuple(
                R002CriteriaSourceCase(
                    case_id=case.case_id,
                    problem_statement_sha256=case.problem_statement_sha256,
                    byte_length=len(sources[case.problem_statement_sha256]),
                )
                for case in manifest.cases
            ),
        )
    )
    proposal = build_criteria_proposal(manifest, cache, _criteria_by_case(manifest))
    criteria = confirmed_criteria_from_proposal(proposal)
    cache.publish_index(
        R002CacheIndex(
            source_sha256=manifest.source.sha256,
            manifest_sha256=canonical_sha256(manifest),
            criteria_set_sha256=canonical_sha256(criteria),
            cases=tuple(cached_cases),
        )
    )
    return manifest, criteria, cache


def _labels_for_universe(
    criteria: R002CriteriaSet,
    universe,
    *,
    confirmed: bool,
):
    labels = tuple(
        R002CandidateLabel(
            key=key,
            relevant=True,
            reason_code="direct_static_candidate",
        )
        for key in universe.candidate_keys
    )
    model = R002CandidateLabelSet if confirmed else R002CandidateLabelProposal
    return model(
        source_manifest_sha256=criteria.source_manifest_sha256,
        criteria_set_sha256=canonical_sha256(criteria),
        annotation_universe_sha256=canonical_sha256(universe),
        annotation_count=len(labels),
        labels=labels,
        expected_missing=derive_expected_missing(criteria, universe, labels),
        benchmark_owner_confirmed=confirmed,
    )


def test_annotation_universe_is_complete_and_labels_are_exact(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, criteria, cache = _prepared_annotation_inputs(
        tmp_path, r002_manifest_payload
    )
    universe = build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    review = cache.read_model("annotation-review.json", R002AnnotationReview)

    assert universe.candidate_count == 20
    assert tuple(item.key for item in review.items) == universe.candidate_keys
    assert all(item.relevant is None and item.reason_code is None for item in review.items)
    assert all(item.line_content.startswith("new-") for item in review.items)

    proposal = _labels_for_universe(criteria, universe, confirmed=False)
    validate_complete_label_proposal(criteria, universe, proposal)
    confirmed = _labels_for_universe(criteria, universe, confirmed=True)
    validate_complete_labels(criteria, universe, confirmed)

    with pytest.raises(R002AnnotationError, match="reannotation_required"):
        validate_complete_labels(
            criteria,
            universe,
            confirmed.model_copy(
                update={
                    "labels": confirmed.labels[:-1],
                    "annotation_count": len(confirmed.labels) - 1,
                }
            ),
        )


def test_annotation_fails_before_publication_on_upstream_drift(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, criteria, cache = _prepared_annotation_inputs(
        tmp_path, r002_manifest_payload
    )
    drifted = criteria.model_copy(update={"source_manifest_sha256": "f" * 64})
    with pytest.raises(R002AnnotationError, match="criteria_manifest_drift"):
        build_annotation_universe(
            manifest=manifest,
            criteria=drifted,
            cache=cache,
        )
    assert not (tmp_path / "cache" / "annotation-universe.json").exists()


@pytest.mark.parametrize(
    "criteria",
    [
        (),
        (
            Criterion(
                criterion_id="AC-01",
                text="Defaults are not explicit.",
            ),
        ),
        (
            _criterion().model_copy(
                update={"source_span": "problem_statement:L1-L2"}
            ),
        ),
        (
            _criterion().model_copy(
                update={"source_span": "not-a-source-span"}
            ),
        ),
        (
            _criterion().model_copy(
                update={"priority": Priority.SHOULD_HAVE}
            ),
        ),
    ],
)
def test_criteria_proposal_rejects_incomplete_or_unbounded_criteria(
    criteria: tuple[Criterion, ...],
) -> None:
    with pytest.raises(
        R002AnnotationError,
        match="criteria_source_cache_manifest_mismatch",
    ):
        _validate_criterion_spans(criteria, line_count=1)


def test_criteria_proposal_fails_closed_on_cache_identity_and_body_errors(
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, sources = _manifest_with_problem_sources(r002_manifest_payload)
    cache = _RecordingCriteriaCache(manifest, sources)
    cache.index = cache.index.model_copy(update={"manifest_sha256": "f" * 64})
    with pytest.raises(
        R002AnnotationError,
        match="criteria_source_cache_manifest_mismatch",
    ):
        build_criteria_proposal(manifest, cache, _criteria_by_case(manifest))  # type: ignore[arg-type]

    cache = _RecordingCriteriaCache(manifest, sources)
    cache.sources.clear()
    with pytest.raises(
        R002AnnotationError,
        match="problem_statement_hash_mismatch",
    ):
        build_criteria_proposal(manifest, cache, _criteria_by_case(manifest))  # type: ignore[arg-type]

    cache = _RecordingCriteriaCache(manifest, sources)
    first = manifest.cases[0].problem_statement_sha256
    cache.sources[first] = b"different valid utf8"
    with pytest.raises(
        R002AnnotationError,
        match="problem_statement_hash_mismatch",
    ):
        build_criteria_proposal(manifest, cache, _criteria_by_case(manifest))  # type: ignore[arg-type]


def test_annotation_detects_cache_and_material_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, criteria, cache = _prepared_annotation_inputs(
        tmp_path, r002_manifest_payload
    )
    real_index = cache.load_index()
    first = real_index.cases[0]
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "load_index",
            lambda: (_ for _ in ()).throw(RuntimeError("cache detail")),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_criteria_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    tampered_head_cases = (
        first.model_copy(
            update={
                "head_files": (
                    first.head_files[0].model_copy(
                        update={"head_sha": "f" * 40}
                    ),
                )
            }
        ),
        *real_index.cases[1:],
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "load_index",
            lambda: real_index.model_copy(update={"cases": tampered_head_cases}),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_evidence_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    first_row = cache.read_model(
        f"rows/{manifest.cases[0].row_sha256}",
        SWEbenchVerifiedRow,
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "read_model",
            lambda relative, model: first_row.model_copy(
                update={"problem_statement": "drifted"}
            ),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_evidence_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_write_annotation_review_internal",
            lambda **kwargs: (_ for _ in ()).throw(
                R002CacheError("annotation_pair_mismatch")
            ),
        )
        with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )
    assert not (tmp_path / "cache" / "annotation-universe.json").exists()
    assert not (tmp_path / "cache" / "annotation-review.json").exists()

    build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    before_universe = (tmp_path / "cache" / "annotation-universe.json").read_bytes()
    before_review = (tmp_path / "cache" / "annotation-review.json").read_bytes()
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_write_annotation_review_internal",
            lambda **kwargs: (_ for _ in ()).throw(
                R002CacheError("annotation_pair_mismatch")
            ),
        )
        with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )
    assert (tmp_path / "cache" / "annotation-universe.json").read_bytes() == (
        before_universe
    )
    assert (tmp_path / "cache" / "annotation-review.json").read_bytes() == (
        before_review
    )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "write_annotation_pair",
            lambda **kwargs: (_ for _ in ()).throw(
                R002CacheError("cache_write_failed")
            ),
        )
        with pytest.raises(R002CacheError, match="cache_write_failed"):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "read_model",
            lambda relative, model: (_ for _ in ()).throw(
                RuntimeError("read detail")
            ),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_evidence_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    missing_line_cases = (
        first.model_copy(update={"verified_lines": ()}),
        *real_index.cases[1:],
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "load_index",
            lambda: real_index.model_copy(update={"cases": missing_line_cases}),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_evidence_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "load_index",
            lambda: real_index.model_copy(update={"source_sha256": "f" * 64}),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_criteria_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    universe = build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    review = cache.read_model("annotation-review.json", R002AnnotationReview)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_write_annotation_universe_internal",
            lambda **kwargs: universe,
        )
        scoped.setattr(
            cache,
            "_write_annotation_review_internal",
            lambda **kwargs: review.model_copy(update={"items": ()}),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_evidence_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    drifted_cases = (
        first.model_copy(update={"parsed_case_sha256": "f" * 64}),
        *real_index.cases[1:],
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "load_index",
            lambda: real_index.model_copy(update={"cases": drifted_cases}),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_evidence_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    empty_cases = tuple(
        case.model_copy(update={"verified_lines": ()})
        for case in real_index.cases
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "load_index",
            lambda: real_index.model_copy(update={"cases": empty_cases}),
        )
        scoped.setattr(
            r002_runner,
            "_load_annotation_material",
            lambda case, criterion_case, cached_case, supplied_cache: (
                r002_runner._R002AnnotationMaterial(
                    case=case,
                    criterion_case=criterion_case,
                    cached_case=cached_case,
                    contexts={},
                )
            ),
        )
        with pytest.raises(R002AnnotationError, match="annotation_pair_limit"):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_write_annotation_universe_internal",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("write detail")),
        )
        with pytest.raises(
            R002AnnotationError,
            match="prepared_cache_evidence_drift",
        ):
            build_annotation_universe(
                manifest=manifest,
                criteria=criteria,
                cache=cache,
            )


def test_label_validation_covers_hash_identity_expected_missing_and_confirmation(
    tmp_path: Path,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, criteria, cache = _prepared_annotation_inputs(
        tmp_path, r002_manifest_payload
    )
    universe = build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    confirmed = _labels_for_universe(criteria, universe, confirmed=True)

    with pytest.raises(R002AnnotationError, match="label_upstream_hash_drift"):
        validate_complete_labels(
            criteria,
            universe,
            confirmed.model_copy(update={"criteria_set_sha256": "f" * 64}),
        )

    bad_key = universe.candidate_keys[0].model_copy(
        update={"criterion_id": "AC-02"}
    )
    bad_universe = universe.model_copy(
        update={"candidate_keys": (bad_key, *universe.candidate_keys[1:])}
    )
    with pytest.raises(R002AnnotationError, match="annotation_criterion_drift"):
        validate_complete_labels(criteria, bad_universe, confirmed)

    with pytest.raises(R002AnnotationError, match="expected_missing_drift"):
        validate_complete_labels(
            criteria,
            universe,
            confirmed.model_copy(update={"expected_missing": ()}),
        )

    contradictory = confirmed.labels[0].model_copy(
        update={
            "relevant": False,
            "reason_code": "direct_static_candidate",
        }
    )
    invalid_labels = (contradictory, *confirmed.labels[1:])
    with pytest.raises(R002AnnotationError, match="reannotation_required"):
        validate_complete_labels(
            criteria,
            universe,
            confirmed.model_copy(
                update={
                    "labels": invalid_labels,
                    "expected_missing": derive_expected_missing(
                        criteria,
                        universe,
                        invalid_labels,
                    ),
                }
            ),
        )

    proposal = _labels_for_universe(criteria, universe, confirmed=False)
    with pytest.raises(
        R002AnnotationError,
        match="label_proposal_must_be_unconfirmed",
    ):
        validate_complete_label_proposal(
            criteria,
            universe,
            proposal.model_copy(update={"benchmark_owner_confirmed": True}),
        )
    with pytest.raises(
        R002AnnotationError,
        match="candidate_labels_not_confirmed",
    ):
        validate_complete_labels(
            criteria,
            universe,
            confirmed.model_copy(update={"benchmark_owner_confirmed": False}),
        )

    irrelevant = tuple(
        label.model_copy(
            update={
                "relevant": False,
                "reason_code": "unrelated_candidate",
            }
        )
        for label in confirmed.labels
    )
    assert len(derive_expected_missing(criteria, universe, irrelevant)) == 80


def test_annotate_wrapper_validates_confirmation_before_opening_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r002_manifest_payload: dict[str, object],
) -> None:
    manifest, criteria, cache = _prepared_annotation_inputs(
        tmp_path, r002_manifest_payload
    )
    manifest_path = tmp_path / "source_manifest.json"
    criteria_path = tmp_path / "criteria.json"
    expected = build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    opened: list[Path] = []
    monkeypatch.setattr(r002_runner, "load_source_manifest", lambda path: manifest)
    monkeypatch.setattr(
        r002_runner,
        "load_confirmed_criteria",
        lambda path, digest: criteria,
    )
    monkeypatch.setattr(
        r002_runner,
        "R002Cache",
        lambda root: opened.append(root) or cache,
    )
    assert (
        r002_runner.annotate_r002(
            manifest_path=manifest_path,
            criteria_path=criteria_path,
            cache_root=tmp_path / "cache",
        )
        == expected
    )
    assert opened == [tmp_path / "cache"]

    opened.clear()
    monkeypatch.setattr(
        r002_runner,
        "load_confirmed_criteria",
        lambda path, digest: (_ for _ in ()).throw(
            R002AnnotationError("criteria_manifest_drift")
        ),
    )
    with pytest.raises(R002AnnotationError, match="criteria_manifest_drift"):
        r002_runner.annotate_r002(
            manifest_path=manifest_path,
            criteria_path=criteria_path,
            cache_root=tmp_path / "cache",
        )
    assert opened == []


def test_annotation_pair_lock_serializes_failure_rollback_and_next_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_a = R002Cache(tmp_path / "cache")
    cache_b = R002Cache(tmp_path / "cache")
    line = "x"
    key = R002CandidateLineKey(
        case_id="R002-001",
        criterion_id="AC-01",
        stream=R002DiffStream.PATCH,
        path="src/a.py",
        new_line_number=1,
        normalized_line_sha256=sha256(line.encode()).hexdigest(),
    )
    item = R002AnnotationReviewItem(
        key=key,
        line_content=line,
        relevant=None,
        reason_code=None,
    )
    entered_review = threading.Event()
    release_failure = threading.Event()
    writer_b_started = threading.Event()
    writer_b_done = threading.Event()
    errors: list[BaseException] = []

    def fail_review(**kwargs: object) -> object:
        del kwargs
        entered_review.set()
        assert release_failure.wait(timeout=5)
        raise R002CacheError("annotation_pair_mismatch")

    monkeypatch.setattr(
        cache_a,
        "_write_annotation_review_internal",
        fail_review,
    )

    def write_a() -> None:
        try:
            cache_a.write_annotation_pair(
                source_manifest_sha256="a" * 64,
                criteria_set_sha256="b" * 64,
                candidate_count=1,
                ordered_key_factory=lambda: iter((key,)),
                ordered_item_factory=lambda: iter((item,)),
            )
        except BaseException as error:
            errors.append(error)

    def write_b() -> None:
        writer_b_started.set()
        try:
            cache_b.write_annotation_pair(
                source_manifest_sha256="c" * 64,
                criteria_set_sha256="d" * 64,
                candidate_count=1,
                ordered_key_factory=lambda: iter((key,)),
                ordered_item_factory=lambda: iter((item,)),
            )
        except BaseException as error:
            errors.append(error)
        finally:
            writer_b_done.set()

    thread_a = threading.Thread(target=write_a)
    thread_b = threading.Thread(target=write_b)
    thread_a.start()
    assert entered_review.wait(timeout=5)
    thread_b.start()
    assert writer_b_started.wait(timeout=5)
    assert not writer_b_done.wait(timeout=0.1)
    release_failure.set()
    thread_a.join(timeout=5)
    thread_b.join(timeout=5)

    assert not thread_a.is_alive()
    assert not thread_b.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], R002CacheError)
    universe = cache_b.read_model(
        "annotation-universe.json",
        R002AnnotationUniverse,
    )
    review = cache_b.read_model("annotation-review.json", R002AnnotationReview)
    assert universe.source_manifest_sha256 == "c" * 64
    assert universe.criteria_set_sha256 == "d" * 64
    assert review.source_manifest_sha256 == "c" * 64
    assert review.criteria_set_sha256 == "d" * 64
