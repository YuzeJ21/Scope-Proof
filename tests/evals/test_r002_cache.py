"""Adversarial persistence tests for the local-only R-002 research cache."""

from __future__ import annotations

import errno
import gc
import io
import json
import os
import stat
import threading
import weakref
from contextlib import suppress
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from scopeproof_core.evals.r002_cache import R002Cache, R002CacheError
from scopeproof_core.evals.r002_models import (
    R002AnnotationReview,
    R002AnnotationReviewItem,
    R002AnnotationUniverse,
    R002CachedCase,
    R002CachedHeadFile,
    R002CacheIndex,
    R002CandidateLabelProposal,
    R002CandidateLineKey,
    R002CriteriaProposal,
    R002CriteriaSourceCase,
    R002CriteriaSourceIndex,
    R002CriterionReviewCase,
    R002DiffStream,
    SWEbenchVerifiedRow,
    canonical_json_bytes,
    canonical_sha256,
)
from scopeproof_core.schemas.models import (
    Criterion,
    CriterionSource,
    CriterionType,
    EvidenceLevel,
    Finding,
    FindingStatus,
    GateDecision,
    GateVerdict,
    Priority,
    ResearchContext,
    Review,
    ReviewBundle,
)


def _sha(number: int) -> str:
    return f"{number:064x}"


def _criterion_case(number: int) -> R002CriterionReviewCase:
    problem = f"Fixture problem {number}."
    return R002CriterionReviewCase.model_validate(
        {
            "case_id": f"R002-{number:03d}",
            "problem_statement_sha256": sha256(problem.encode()).hexdigest(),
            "problem_statement": problem,
            "criteria": (
                {
                    "criterion_id": "AC-01",
                    "text": "Preserve the fixture behavior.",
                    "priority": Priority.MUST_HAVE,
                    "criterion_type": CriterionType.BEHAVIOR,
                    "criterion_source": CriterionSource.USER_CONFIRMED,
                    "source_span": "problem_statement:L1-L1",
                    "required_evidence_level": EvidenceLevel.E1,
                },
            ),
        }
    )


def _criteria_proposal() -> R002CriteriaProposal:
    return R002CriteriaProposal(
        source_manifest_sha256=_sha(900),
        cases=tuple(_criterion_case(number) for number in range(1, 21)),
    )


def _review_bundle() -> ReviewBundle:
    criterion = Criterion(criterion_id="AC-01", text="Preserve the fixture behavior.")
    return ReviewBundle(
        review=Review(
            review_id="r002-review-001",
            repository="fixture/repository",
            pr_number=1,
            base_sha="base-sha",
            head_sha="head-sha",
            criteria_confirmed=True,
            created_at=datetime(2026, 7, 22, 12, 30, tzinfo=UTC),
        ),
        criteria_revision_number=1,
        source_text="Preserve the fixture behavior.",
        criteria=[criterion],
        evidence=[],
        findings=[
            Finding(
                criterion_id="AC-01",
                status=FindingStatus.MISSING,
                reason="No implementation evidence was supplied.",
                missing_evidence=["Implementation evidence"],
                recommended_action="Collect explicit evidence.",
            )
        ],
        gate=GateDecision(
            verdict=GateVerdict.BLOCKED,
            blocking_criteria=["AC-01"],
            reason_codes=["missing_evidence"],
        ),
        research_context=ResearchContext(
            case_id="R002-001",
            boundary_note="Public engineering research only; no Stage 1 credit.",
        ),
    )


def _row(number: int) -> SWEbenchVerifiedRow:
    return SWEbenchVerifiedRow(
        repo=f"fixture/repo-{number}",
        instance_id=f"fixture__repo-{number}-{number}",
        base_commit=f"{number:040x}",
        patch=f"patch-{number}",
        test_patch=f"test-patch-{number}",
        problem_statement=f"problem-{number}",
        hints_text="",
        created_at="2026-01-01",
        version="1",
        FAIL_TO_PASS="[]",
        PASS_TO_PASS="[]",
        environment_setup_commit="",
        difficulty="fixture",
    )


def _prepared_cache(cache: R002Cache, *, head_bytes: bytes = b"head") -> R002CacheIndex:
    criteria_cases = []
    cached_cases = []
    for number in range(1, 21):
        problem = f"problem-{number}".encode()
        problem_hash = sha256(problem).hexdigest()
        cache.write_bytes(f"criteria-sources/{problem_hash}", problem)
        criteria_cases.append(
            R002CriteriaSourceCase(
                case_id=f"R002-{number:03d}",
                problem_statement_sha256=problem_hash,
                byte_length=len(problem),
            )
        )
        row = _row(number)
        row_hash = canonical_sha256(row)
        cache.write_content_addressed_model(f"rows/{row_hash}", row, SWEbenchVerifiedRow)
        head_files: tuple[R002CachedHeadFile, ...] = ()
        if number == 1:
            head_hash = sha256(head_bytes).hexdigest()
            cache.write_bytes(f"head-files/{head_hash}", head_bytes)
            head_files = (
                R002CachedHeadFile(
                    logical_path="src/fixture.py",
                    head_sha=f"{101:040x}",
                    byte_length=len(head_bytes),
                    content_sha256=head_hash,
                ),
            )
        cached_cases.append(
            R002CachedCase(
                case_id=f"R002-{number:03d}",
                row_sha256=row_hash,
                problem_statement_sha256=sha256(row.problem_statement.encode()).hexdigest(),
                patch_sha256=sha256(row.patch.encode()).hexdigest(),
                test_patch_sha256=sha256(row.test_patch.encode()).hexdigest(),
                parsed_case_sha256=_sha(number + 500),
                verified_lines=(),
                head_files=head_files,
            )
        )
    cache.publish_criteria_source_index(
        R002CriteriaSourceIndex(
            source_sha256=_sha(700),
            manifest_sha256=_sha(701),
            cases=tuple(criteria_cases),
        )
    )
    return R002CacheIndex(
        source_sha256=_sha(700),
        manifest_sha256=_sha(701),
        criteria_set_sha256=_sha(702),
        cases=tuple(cached_cases),
    )


def _key(number: int, content: str | None = None) -> R002CandidateLineKey:
    text = content or f"line {number}"
    return R002CandidateLineKey(
        case_id="R002-001",
        criterion_id="AC-01",
        stream=R002DiffStream.PATCH,
        path="src/fixture.py",
        new_line_number=number,
        normalized_line_sha256=sha256(text.encode()).hexdigest(),
    )


def _write_universe(cache: R002Cache) -> R002AnnotationUniverse:
    keys = (_key(1), _key(2))
    return cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=2,
        ordered_key_factory=lambda: iter(keys),
    )


def _assert_public_error_is_sanitized(
    error: BaseException, forbidden_values: tuple[str, ...]
) -> None:
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        traceback = current.__traceback__
        while traceback is not None:
            if Path(traceback.tb_frame.f_code.co_filename).name == "r002_cache.py":
                retained = repr(traceback.tb_frame.f_locals)
                for forbidden in forbidden_values:
                    assert forbidden not in retained
            traceback = traceback.tb_next
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    assert error.__cause__ is None
    assert error.__context__ is None


def test_cache_creates_owned_0700_directories_and_0600_files(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "r002")
    proposal = _criteria_proposal()
    path = cache.replace_model("criteria-proposal.json", proposal)

    assert stat.S_IMODE((tmp_path / "r002").stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.stat().st_uid == os.geteuid()
    assert cache.read_model("criteria-proposal.json", R002CriteriaProposal) == proposal


@pytest.mark.parametrize(
    "relative",
    ["../escape", "/tmp/escape", "rows\\escape", "rows/\x00", "rows/not-a-hash"],
)
def test_cache_rejects_nonlocal_or_nonallowlisted_names(tmp_path: Path, relative: str) -> None:
    with pytest.raises(R002CacheError, match="unsafe_relative_name"):
        R002Cache(tmp_path / "cache").write_bytes(relative, b"value")
    assert not (tmp_path / "cache").exists()


def test_cache_rejects_symlink_root_and_existing_ancestor(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    root_link = tmp_path / "root-link"
    root_link.symlink_to(real, target_is_directory=True)
    ancestor_link = tmp_path / "ancestor-link"
    ancestor_link.symlink_to(real, target_is_directory=True)

    for root in (root_link, ancestor_link / "cache"):
        with pytest.raises(R002CacheError, match="symlink_or_nondirectory"):
            R002Cache(root).replace_model("criteria-proposal.json", _criteria_proposal())


def test_cache_rejects_symlink_destination_without_following_it(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache = R002Cache(cache_root)
    expected = b"expected"
    digest = sha256(expected).hexdigest()
    cache.write_bytes(f"head-files/{digest}", expected)
    target = tmp_path / "outside"
    target.write_bytes(b"outside")
    (cache_root / "head-files" / digest).unlink()
    (cache_root / "head-files" / digest).symlink_to(target)

    with pytest.raises(R002CacheError, match="cache_file_security"):
        cache.read_bytes(f"head-files/{digest}")
    assert target.read_bytes() == b"outside"


def test_cache_rejects_symlinked_namespace_and_wrong_mode_directory(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache = R002Cache(cache_root)
    cache.replace_model("criteria-proposal.json", _criteria_proposal())
    outside = tmp_path / "outside-directory"
    outside.mkdir()
    (cache_root / "head-files").symlink_to(outside, target_is_directory=True)
    data = b"value"
    with pytest.raises(R002CacheError, match="symlink_or_nondirectory"):
        cache.write_bytes(f"head-files/{sha256(data).hexdigest()}", data)
    assert list(outside.iterdir()) == []

    (cache_root / "head-files").unlink()
    path = cache.write_bytes(f"head-files/{sha256(data).hexdigest()}", data)
    path.parent.chmod(0o755)
    with pytest.raises(R002CacheError, match="cache_directory_security"):
        cache.read_bytes(f"head-files/{sha256(data).hexdigest()}")


def test_cache_rejects_hardlinks_fifos_and_wrong_modes(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache = R002Cache(cache_root)
    data = b"content"
    digest = sha256(data).hexdigest()
    path = cache.write_bytes(f"head-files/{digest}", data)
    hardlink = tmp_path / "hardlink"
    os.link(path, hardlink)
    with pytest.raises(R002CacheError, match="cache_file_security"):
        cache.read_bytes(f"head-files/{digest}")
    hardlink.unlink()

    path.chmod(0o644)
    with pytest.raises(R002CacheError, match="cache_file_security"):
        cache.read_bytes(f"head-files/{digest}")
    path.unlink()
    fifo_digest = sha256(b"fifo").hexdigest()
    os.mkfifo(cache_root / "head-files" / fifo_digest, 0o600)
    with pytest.raises(R002CacheError, match="cache_file_security"):
        cache.read_bytes(f"head-files/{fifo_digest}")


def test_existing_content_addressed_object_is_reused_but_never_changed(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    expected = b"expected"
    digest = sha256(expected).hexdigest()
    first = cache.write_bytes(f"head-files/{digest}", expected)

    assert cache.write_bytes(f"head-files/{digest}", expected) == first
    with pytest.raises(R002CacheError, match="content_address_collision"):
        cache.write_bytes(f"head-files/{digest}", b"changed")
    assert first.read_bytes() == expected


def test_direct_content_readers_always_enforce_the_basename_digest(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    raw = b"expected"
    raw_digest = sha256(raw).hexdigest()
    raw_path = cache.write_bytes(f"head-files/{raw_digest}", raw)
    raw_path.write_bytes(b"tampered")
    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.read_bytes(f"head-files/{raw_digest}")

    row = _row(1)
    row_digest = canonical_sha256(row)
    row_path = cache.write_content_addressed_model(f"rows/{row_digest}", row, SWEbenchVerifiedRow)
    row_path.write_bytes(b"{}")
    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.read_model(f"rows/{row_digest}", SWEbenchVerifiedRow)


def test_new_content_address_name_must_equal_data_digest(tmp_path: Path) -> None:
    with pytest.raises(R002CacheError, match="content_address_digest_mismatch"):
        R002Cache(tmp_path / "cache").write_bytes(f"head-files/{'0' * 64}", b"different digest")


def test_rows_require_the_exact_typed_canonical_model_api(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    row = _row(1)
    digest = canonical_sha256(row)

    with pytest.raises(R002CacheError, match="raw_write_requires_content_namespace"):
        cache.write_bytes(f"rows/{digest}", canonical_json_bytes(row))
    with pytest.raises(R002CacheError, match="model_type_mismatch"):
        cache.write_content_addressed_model(
            f"rows/{digest}", _criteria_proposal(), R002CriteriaProposal
        )
    path = cache.write_content_addressed_model(f"rows/{digest}", row, SWEbenchVerifiedRow)
    assert cache.read_model(
        f"rows/{digest}",
        SWEbenchVerifiedRow,
    ) == cache.read_model(
        str(path.relative_to(tmp_path / "cache")),
        SWEbenchVerifiedRow,
    )


def test_namespace_limit_fails_before_cache_creation(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    data = b"x" * (128 * 1024 + 1)
    with pytest.raises(R002CacheError, match="cache_file_security"):
        R002Cache(cache_root).write_bytes(f"criteria-sources/{sha256(data).hexdigest()}", data)
    assert not cache_root.exists()


@pytest.mark.parametrize("reserved", ["criteria-source-index.json", "cache-index.json"])
def test_completion_markers_reject_all_generic_writes(tmp_path: Path, reserved: str) -> None:
    cache = R002Cache(tmp_path / "cache")
    with pytest.raises(R002CacheError, match="completion_marker_requires_publish"):
        cache.write_bytes(reserved, b"{}")
    with pytest.raises(R002CacheError, match="completion_marker_requires_publish"):
        cache.write_model(reserved, _criteria_proposal())
    with pytest.raises(R002CacheError, match="completion_marker_requires_publish"):
        cache.replace_model(reserved, _criteria_proposal())
    marker_type = (
        R002CriteriaSourceIndex if reserved == "criteria-source-index.json" else R002CacheIndex
    )
    with pytest.raises(R002CacheError, match="completion_marker_requires_publish"):
        cache.read_model(reserved, marker_type)
    with pytest.raises(R002CacheError, match="completion_marker_requires_publish"):
        cache.read_bytes(reserved)


@pytest.mark.parametrize(
    "control",
    [
        "criteria-proposal.json",
        "criteria-review.json",
        "annotation-universe.json",
        "annotation-review.json",
        "candidate-label-proposal.json",
        "result.json",
        "reviews/R002-001.json",
    ],
)
def test_raw_bytes_cannot_bypass_control_model_validation(tmp_path: Path, control: str) -> None:
    with pytest.raises(R002CacheError, match="raw_write_requires_content_namespace"):
        R002Cache(tmp_path / "cache").write_bytes(control, b"{}")


def test_generic_model_api_rejects_wrong_type_and_streamed_artifacts(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    proposal = _criteria_proposal()
    with pytest.raises(R002CacheError, match="model_type_mismatch"):
        cache.replace_model("candidate-label-proposal.json", proposal)
    for relative in ("annotation-universe.json", "annotation-review.json"):
        with pytest.raises(R002CacheError, match="streamed_annotation_requires_writer"):
            cache.replace_model(relative, proposal)


def test_write_model_is_create_only_and_preserves_the_first_control(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    proposal = _criteria_proposal()
    cache.write_model("criteria-proposal.json", proposal)
    with pytest.raises(R002CacheError, match="control_already_exists"):
        cache.write_model("criteria-proposal.json", proposal)
    assert cache.read_model("criteria-proposal.json", R002CriteriaProposal) == proposal


def test_model_construct_cannot_bypass_revalidation(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    bypass = R002CriteriaProposal.model_construct(source_manifest_sha256="not-a-sha", cases=())
    with pytest.raises(R002CacheError, match="model_validation_failed"):
        cache.replace_model("criteria-proposal.json", bypass)
    assert not (tmp_path / "cache" / "criteria-proposal.json").exists()


@pytest.mark.parametrize("writer_name", ["write_model", "replace_model"])
def test_generic_control_writer_compares_reopened_validated_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer_name: str
) -> None:
    cache = R002Cache(tmp_path / "cache")
    proposal = _criteria_proposal()
    unequal_reopened = proposal.model_copy()
    object.__setattr__(unequal_reopened, "__pydantic_private__", {"fault": "injected"})
    assert unequal_reopened != proposal
    assert canonical_json_bytes(unequal_reopened) == canonical_json_bytes(proposal)
    real_read_model = R002Cache._read_model_internal

    def unequal_reopen(self, relative_name, model_type, **kwargs):
        observed = real_read_model(self, relative_name, model_type, **kwargs)
        assert observed == proposal
        return unequal_reopened

    monkeypatch.setattr(R002Cache, "_read_model_internal", unequal_reopen)
    with pytest.raises(R002CacheError, match="cache_state_unknown"):
        getattr(cache, writer_name)("criteria-proposal.json", proposal)


@pytest.mark.parametrize(
    "writer_name", ["write_content_addressed_model", "write_model", "replace_model"]
)
def test_public_postpublication_model_error_discards_sensitive_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer_name: str,
) -> None:
    native_detail = f"native-{writer_name}-detail"
    cache_root = tmp_path / f"cache-{writer_name}"
    cache = R002Cache(cache_root)
    if writer_name == "write_content_addressed_model":
        secret = "UNIQUE_PATCH_SECRET_CONTENT_ADDRESSED"
        value = _row(1).model_copy(update={"patch": secret})
        canonical = canonical_json_bytes(value).decode()
        relative = f"rows/{canonical_sha256(value)}"
        arguments = (relative, value, SWEbenchVerifiedRow)
    else:
        secret = f"UNIQUE_SOURCE_SECRET_{writer_name.upper()}"
        secret_case = _criterion_case(1).model_copy(
            update={
                "problem_statement": secret,
                "problem_statement_sha256": sha256(secret.encode()).hexdigest(),
            }
        )
        proposal = _criteria_proposal().model_copy(
            update={"cases": (secret_case, *_criteria_proposal().cases[1:])}
        )
        canonical = canonical_json_bytes(proposal).decode()
        arguments = ("criteria-proposal.json", proposal)

    def fail_reopen(*args, **kwargs):
        raise OSError(native_detail)

    monkeypatch.setattr(R002Cache, "_read_model_internal", fail_reopen)
    with pytest.raises(R002CacheError, match="cache_write_failed") as caught:
        getattr(cache, writer_name)(*arguments)
    _assert_public_error_is_sanitized(
        caught.value,
        (secret, canonical, str(cache_root.resolve()), native_detail),
    )


def test_review_bundle_roundtrips_canonical_datetime_json(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    bundle = _review_bundle()

    path = cache.replace_model("reviews/R002-001.json", bundle)

    assert cache.read_model("reviews/R002-001.json", ReviewBundle) == bundle
    assert json.loads(path.read_bytes())["review"]["created_at"] == "2026-07-22T12:30:00Z"


def test_review_bundle_reader_rejects_malformed_datetime_json(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    reviews = cache_root / "reviews"
    reviews.mkdir(parents=True, mode=0o700)
    cache_root.chmod(0o700)
    reviews.chmod(0o700)
    payload = _review_bundle().model_dump(mode="json")
    payload["review"]["created_at"] = "not-a-datetime"
    review_path = reviews / "R002-001.json"
    review_path.write_bytes(canonical_json_bytes(payload))
    review_path.chmod(0o600)

    with pytest.raises(R002CacheError, match="model_validation_failed"):
        R002Cache(cache_root).read_model("reviews/R002-001.json", ReviewBundle)


def test_review_bundle_reader_rejects_coercible_nonexact_primitive_json(
    tmp_path: Path,
) -> None:
    cache_root = tmp_path / "cache"
    reviews = cache_root / "reviews"
    reviews.mkdir(parents=True, mode=0o700)
    cache_root.chmod(0o700)
    reviews.chmod(0o700)
    payload = _review_bundle().model_dump(mode="json")
    payload["review"]["pr_number"] = "1"
    review_path = reviews / "R002-001.json"
    review_path.write_bytes(canonical_json_bytes(payload))
    review_path.chmod(0o600)

    with pytest.raises(R002CacheError, match="model_validation_failed"):
        R002Cache(cache_root).read_model("reviews/R002-001.json", ReviewBundle)


def test_replace_fsyncs_temp_before_replace_and_directory_after(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    events: list[str] = []
    real_fsync = os.fsync
    real_replace = os.replace

    def recording_fsync(fd: int) -> None:
        events.append("dir-fsync" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file-fsync")
        real_fsync(fd)

    def recording_replace(*args, **kwargs) -> None:
        events.append("replace")
        real_replace(*args, **kwargs)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    monkeypatch.setattr(os, "replace", recording_replace)
    cache.replace_model("criteria-proposal.json", _criteria_proposal())

    replace_at = events.index("replace")
    assert "file-fsync" in events[:replace_at]
    assert "dir-fsync" in events[replace_at + 1 :]


def test_failed_pre_replace_preserves_control_and_sanitizes_native_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    first = _criteria_proposal()
    cache.replace_model("criteria-proposal.json", first)

    def failing_replace(*args, **kwargs) -> None:
        raise OSError("secret-native-path")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(R002CacheError, match="cache_replace_failed") as caught:
        cache.replace_model("criteria-proposal.json", first.model_copy())
    assert caught.value.args == ("cache_replace_failed",)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert cache.read_model("criteria-proposal.json", R002CriteriaProposal) == first
    assert not any(path.name.startswith(".r002-tmp-") for path in (tmp_path / "cache").iterdir())


def test_failed_replace_after_in_place_marker_mutation_is_unknown_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    marker = cache.publish_index(index)

    def mutate_marker_then_raise(*args, **kwargs) -> None:
        fd = os.open(
            args[1],
            os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW,
            dir_fd=kwargs["dst_dir_fd"],
        )
        try:
            os.write(fd, b"X")
            os.fsync(fd)
        finally:
            os.close(fd)
        raise OSError("native marker mutation detail")

    monkeypatch.setattr(os, "replace", mutate_marker_then_raise)
    with pytest.raises(R002CacheError, match="cache_state_unknown") as caught:
        cache.publish_index(index)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert marker.read_bytes() == b"X"
    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.load_index()


@pytest.mark.parametrize("attack", ["symlink", "fifo", "hardlink", "mode"])
def test_replace_rejects_unsafe_existing_control_before_publication(
    tmp_path: Path, attack: str
) -> None:
    cache = R002Cache(tmp_path / "cache")
    proposal = _criteria_proposal()
    path = cache.replace_model("criteria-proposal.json", proposal)
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    if attack == "symlink":
        path.unlink()
        path.symlink_to(outside)
    elif attack == "fifo":
        path.unlink()
        os.mkfifo(path, 0o600)
    elif attack == "hardlink":
        os.link(path, tmp_path / "control-hardlink")
    else:
        path.chmod(0o644)

    with pytest.raises(R002CacheError, match="cache_file_security"):
        cache.replace_model("criteria-proposal.json", proposal)
    assert outside.read_bytes() == b"outside"


def test_fixed_class_serializer_ignores_top_and_nested_instance_shadows(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    proposal = _criteria_proposal()

    def explode(*args, **kwargs):
        raise AssertionError("input-controlled serializer reached")

    object.__setattr__(proposal, "model_dump", explode)
    object.__setattr__(proposal, "__pydantic_serializer__", object())
    object.__setattr__(proposal.cases[0], "__pydantic_serializer__", object())
    path = cache.replace_model("criteria-proposal.json", proposal)

    assert path.stat().st_size > 0
    assert cache.read_model("criteria-proposal.json", R002CriteriaProposal).cases[0].case_id == (
        "R002-001"
    )


def test_primitive_subclasses_are_rejected_before_filesystem_use(tmp_path: Path) -> None:
    class StringSubclass(str):
        pass

    class BytesSubclass(bytes):
        pass

    cache = R002Cache(tmp_path / "cache")
    with pytest.raises(R002CacheError, match="unsafe_relative_name"):
        cache.write_bytes(StringSubclass(f"head-files/{'0' * 64}"), b"value")
    with pytest.raises(R002CacheError, match="cache_write_failed"):
        cache.write_bytes(f"head-files/{sha256(b'value').hexdigest()}", BytesSubclass(b"value"))


def test_public_reason_is_rebuilt_from_a_canonical_builtin_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StringSubclass(str):
        pass

    cache = R002Cache(tmp_path / "cache")

    def hostile_internal(*args, **kwargs):
        raise R002CacheError(StringSubclass("cache_file_security"))

    monkeypatch.setattr(cache, "_immutable_bytes", hostile_internal)
    data = b"value"
    with pytest.raises(R002CacheError, match="cache_write_failed") as caught:
        cache.write_bytes(f"head-files/{sha256(data).hexdigest()}", data)
    assert caught.value.args == ("cache_write_failed",)
    assert type(caught.value.args[0]) is str
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_post_replace_failure_reports_unknown_state_not_old_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    first = _criteria_proposal()
    cache.replace_model("criteria-proposal.json", first)
    real_fsync = os.fsync
    replaced = False

    def recording_replace(*args, **kwargs) -> None:
        nonlocal replaced
        os.rename(
            args[0],
            args[1],
            src_dir_fd=kwargs["src_dir_fd"],
            dst_dir_fd=kwargs["dst_dir_fd"],
        )
        replaced = True

    def failing_directory_fsync(fd: int) -> None:
        if replaced and stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("post-replace secret")
        real_fsync(fd)

    monkeypatch.setattr(os, "replace", recording_replace)
    monkeypatch.setattr(os, "fsync", failing_directory_fsync)
    with pytest.raises(R002CacheError, match="cache_state_unknown"):
        cache.replace_model("criteria-proposal.json", first)


def test_replace_then_raise_is_ambiguous_not_a_pre_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    first = _criteria_proposal()
    second = first.model_copy(update={"source_manifest_sha256": _sha(901)})
    cache.replace_model("criteria-proposal.json", first)
    real_replace = os.replace

    def replacing_then_raising(*args, **kwargs) -> None:
        real_replace(*args, **kwargs)
        raise OSError("ambiguous replace")

    monkeypatch.setattr(os, "replace", replacing_then_raising)
    with pytest.raises(R002CacheError, match="cache_state_unknown"):
        cache.replace_model("criteria-proposal.json", second)
    assert cache.read_model("criteria-proposal.json", R002CriteriaProposal) == second


def test_immutable_publication_uses_link_not_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")

    def forbidden_replace(*args, **kwargs) -> None:
        raise AssertionError("immutable objects must not use replace")

    monkeypatch.setattr(os, "replace", forbidden_replace)
    data = b"immutable"
    digest = sha256(data).hexdigest()
    path = cache.write_bytes(f"head-files/{digest}", data)
    assert path.read_bytes() == data
    assert path.stat().st_nlink == 1


@pytest.mark.parametrize("public_writer", ["write_bytes", "write_model"])
@pytest.mark.parametrize("outcome", ["exact", "corrupt", "directory_fsync_failure"])
def test_ambiguous_link_publication_reconciles_only_exact_durable_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    public_writer: str,
    outcome: str,
) -> None:
    cache_root = tmp_path / "cache"
    cache = R002Cache(cache_root)
    if public_writer == "write_bytes":
        expected = b"ambiguous-link-immutable"
        relative = f"head-files/{sha256(expected).hexdigest()}"

        def write() -> Path:
            return cache.write_bytes(relative, expected)

    else:
        proposal = _criteria_proposal()
        expected = canonical_json_bytes(proposal)
        relative = "criteria-proposal.json"

        def write() -> Path:
            return cache.write_model(relative, proposal)

    real_link = os.link
    real_fsync = os.fsync
    link_completed = False
    directory_fsync_attempts = 0
    native_detail = "ambiguous-link-native-detail"

    def linking_then_raising(src, dst, *, src_dir_fd, dst_dir_fd, follow_symlinks):
        nonlocal link_completed
        real_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        link_completed = True
        if outcome == "corrupt":
            fd = os.open(dst, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, dir_fd=dst_dir_fd)
            try:
                os.write(fd, b"X")
                real_fsync(fd)
            finally:
                os.close(fd)
        raise OSError(errno.EIO, native_detail)

    def recording_fsync(fd: int) -> None:
        nonlocal directory_fsync_attempts
        if link_completed and stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_fsync_attempts += 1
            if outcome == "directory_fsync_failure":
                raise OSError(errno.EIO, "ambiguous-link-directory-fsync-detail")
        real_fsync(fd)

    monkeypatch.setattr(os, "link", linking_then_raising)
    monkeypatch.setattr(os, "fsync", recording_fsync)

    if outcome == "exact":
        path = write()
        assert path.read_bytes() == expected
        if public_writer == "write_model":
            assert cache.read_model(relative, R002CriteriaProposal) == proposal
    else:
        with pytest.raises(R002CacheError, match="cache_state_unknown") as caught:
            write()
        assert caught.value.args == ("cache_state_unknown",)
        _assert_public_error_is_sanitized(
            caught.value,
            (native_detail, "ambiguous-link-directory-fsync-detail", relative),
        )
        if outcome == "corrupt":
            assert (cache_root / relative).read_bytes() == b"X"

    assert directory_fsync_attempts == 1
    assert not tuple(cache_root.rglob(".r002-tmp-*"))


@pytest.mark.parametrize("fail_directory", [False, True])
def test_immutable_fsync_failures_leave_no_temp_and_never_claim_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_directory: bool
) -> None:
    cache_root = tmp_path / "cache"
    cache = R002Cache(cache_root)
    real_fsync = os.fsync

    def failing_fsync(fd: int) -> None:
        is_directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        if is_directory == fail_directory:
            raise OSError("simulated fsync failure")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", failing_fsync)
    data = b"immutable-fsync"
    expected = "cache_state_unknown" if fail_directory else "cache_fsync_failed"
    with pytest.raises(R002CacheError, match=expected):
        cache.write_bytes(f"head-files/{sha256(data).hexdigest()}", data)
    assert not any(
        path.name.startswith(".r002-tmp-") for path in (cache_root / "head-files").iterdir()
    )


def test_identical_immutable_retry_requires_containing_directory_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    data = b"immutable-retry-fsync"
    relative = f"head-files/{sha256(data).hexdigest()}"
    real_fsync = os.fsync
    directory_attempts = 0

    def failing_directory_fsync(fd: int) -> None:
        nonlocal directory_attempts
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_attempts += 1
            raise OSError("simulated containing-directory fsync failure")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", failing_directory_fsync)
    with pytest.raises(R002CacheError, match="cache_state_unknown"):
        cache.write_bytes(relative, data)
    assert (tmp_path / "cache" / relative).read_bytes() == data

    with pytest.raises(R002CacheError, match="cache_state_unknown"):
        cache.write_bytes(relative, data)
    assert directory_attempts == 2


def test_prepare_temp_close_failure_never_retries_a_reused_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close_fd = cache_module._close_fd
    replacement_fd = -1

    def close_temp_reuse_number_and_fail(fd: int) -> bool:
        nonlocal replacement_fd
        if replacement_fd < 0 and stat.S_ISREG(os.fstat(fd).st_mode):
            assert real_close_fd(fd)
            replacement_fd = os.open("/dev/null", os.O_RDONLY)
            assert replacement_fd == fd
            return False
        return real_close_fd(fd)

    monkeypatch.setattr(cache_module, "_close_fd", close_temp_reuse_number_and_fail)
    data = b"prepare-temp-close-fault"
    try:
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            R002Cache(tmp_path / "cache").write_bytes(
                f"head-files/{sha256(data).hexdigest()}", data
            )
        assert replacement_fd >= 0
        assert stat.S_ISCHR(os.fstat(replacement_fd).st_mode)
    finally:
        if replacement_fd >= 0:
            with suppress(OSError):
                os.close(replacement_fd)


@pytest.mark.parametrize("winner", [b"race-data", b"different"])
def test_no_overwrite_race_rechecks_identical_or_different_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winner: bytes
) -> None:
    cache = R002Cache(tmp_path / "cache")
    data = b"race-data"
    digest = sha256(data).hexdigest()
    real_link = os.link
    called = False

    def racing_link(src, dst, *, src_dir_fd, dst_dir_fd, follow_symlinks):
        nonlocal called
        if not called:
            called = True
            fd = os.open(
                dst,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=dst_dir_fd,
            )
            try:
                os.write(fd, winner)
                os.fsync(fd)
            finally:
                os.close(fd)
            raise FileExistsError
        return real_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(os, "link", racing_link)
    if winner == data:
        assert cache.write_bytes(f"head-files/{digest}", data).read_bytes() == data
    else:
        with pytest.raises(R002CacheError, match="content_address_collision"):
            cache.write_bytes(f"head-files/{digest}", data)


def test_temp_candidate_collision_is_rejected_without_following_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    cache = R002Cache(tmp_path / "cache")
    initial = b"initial"
    initial_hash = sha256(initial).hexdigest()
    cache.write_bytes(f"head-files/{initial_hash}", initial)
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    temp = tmp_path / "cache" / "head-files" / ".r002-tmp-fixed"
    temp.symlink_to(outside)
    monkeypatch.setattr(cache_module.secrets, "token_hex", lambda _: "fixed")
    data = b"new"
    with pytest.raises(R002CacheError, match="temp_collision"):
        cache.write_bytes(f"head-files/{sha256(data).hexdigest()}", data)
    assert outside.read_bytes() == b"outside"


def test_criteria_source_marker_is_reserved_and_load_rechecks_all_objects(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    loaded = cache.load_criteria_source_index()
    missing = loaded.cases[7].problem_statement_sha256
    (tmp_path / "cache" / "criteria-sources" / missing).unlink()

    with pytest.raises(R002CacheError, match="referenced_object_missing"):
        cache.load_criteria_source_index()
    with pytest.raises(R002CacheError, match="referenced_object_missing"):
        cache.publish_index(index)


def test_cache_index_publication_and_load_verify_rows_heads_and_criteria(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    cache.publish_index(index)
    assert cache.load_index() == index

    row_path = tmp_path / "cache" / "rows" / index.cases[3].row_sha256
    row_path.chmod(0o600)
    row_path.write_bytes(b"{}")
    row_path.chmod(0o600)
    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.load_index()


def test_marker_replace_rejects_unsafe_existing_marker(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    cache.publish_index(index)
    marker = tmp_path / "cache" / "cache-index.json"
    outside = tmp_path / "outside-marker"
    outside.write_bytes(b"outside")
    marker.unlink()
    marker.symlink_to(outside)

    with pytest.raises(R002CacheError, match="cache_file_security"):
        cache.publish_index(index)
    assert outside.read_bytes() == b"outside"


def test_failed_marker_replace_preserves_previous_complete_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    first = _prepared_cache(cache)
    cache.publish_index(first)

    def failing_replace(*args, **kwargs) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(R002CacheError, match="cache_replace_failed"):
        cache.publish_index(first.model_copy(update={"criteria_set_sha256": _sha(999)}))
    assert cache.load_index() == first


def test_marker_replace_then_raise_reports_unknown_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    first = _prepared_cache(cache)
    cache.publish_index(first)
    second = first.model_copy(update={"criteria_set_sha256": _sha(999)})
    real_replace = os.replace

    def replacing_then_raising(*args, **kwargs) -> None:
        real_replace(*args, **kwargs)
        raise OSError("ambiguous marker replace")

    monkeypatch.setattr(os, "replace", replacing_then_raising)
    with pytest.raises(R002CacheError, match="cache_state_unknown"):
        cache.publish_index(second)
    assert cache.load_index() == second


def test_publish_index_revalidates_constructed_input_and_cross_binds_marker(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    bypass = R002CacheIndex.model_construct(
        source_sha256=index.source_sha256,
        manifest_sha256=index.manifest_sha256,
        criteria_set_sha256="invalid",
        complete=True,
        cases=index.cases,
    )
    with pytest.raises(R002CacheError, match="model_validation_failed"):
        cache.publish_index(bypass)

    drifted = index.model_copy(update={"manifest_sha256": _sha(999)})
    with pytest.raises(R002CacheError, match="criteria_source_index_mismatch"):
        cache.publish_index(drifted)


def test_annotation_universe_streams_exact_canonical_typed_model(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    yielded: list[int] = []

    def factory():
        for number in (1, 2):
            yielded.append(number)
            yield _key(number)

    universe = cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=2,
        ordered_key_factory=factory,
    )

    assert yielded == [1, 2]
    assert cache.read_model("annotation-universe.json", R002AnnotationUniverse) == universe
    assert (tmp_path / "cache" / "annotation-universe.json").read_bytes() == canonical_json_bytes(
        universe
    )


@pytest.mark.parametrize("keys", [(_key(2), _key(1)), (_key(1), _key(1)), (_key(1),)])
def test_annotation_universe_rejects_order_duplicates_and_count_without_replacement(
    tmp_path: Path, keys: tuple[R002CandidateLineKey, ...]
) -> None:
    cache = R002Cache(tmp_path / "cache")
    first = _write_universe(cache)
    before = canonical_json_bytes(first)
    with pytest.raises(R002CacheError, match="annotation_stream_invalid"):
        cache.write_annotation_universe(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            candidate_count=2,
            ordered_key_factory=lambda: iter(keys),
        )
    assert (tmp_path / "cache" / "annotation-universe.json").read_bytes() == before


def test_annotation_stream_stops_at_count_plus_one(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    yielded: list[int] = []

    def factory():
        for number in (1, 2, 3, 4):
            yielded.append(number)
            yield _key(number)

    with pytest.raises(R002CacheError, match="annotation_stream_invalid"):
        cache.write_annotation_universe(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            candidate_count=2,
            ordered_key_factory=factory,
        )
    assert yielded == [1, 2, 3]


def test_annotation_factory_cache_error_is_normalized(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")

    def hostile_factory():
        raise R002CacheError("cache_file_security")
        yield _key(1)

    with pytest.raises(R002CacheError, match="annotation_stream_invalid") as caught:
        cache.write_annotation_universe(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            candidate_count=1,
            ordered_key_factory=hostile_factory,
        )
    assert caught.value.args == ("annotation_stream_invalid",)


def test_annotation_review_requires_current_hash_count_keys_and_incomplete_judgements(
    tmp_path: Path,
) -> None:
    cache = R002Cache(tmp_path / "cache")
    universe = _write_universe(cache)
    items = tuple(
        R002AnnotationReviewItem(key=_key(number), line_content=f"line {number}")
        for number in (1, 2)
    )
    review = cache.write_annotation_review(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        annotation_universe_sha256=canonical_sha256(universe),
        candidate_count=2,
        ordered_item_factory=lambda: iter(items),
    )
    assert cache.read_model("annotation-review.json", R002AnnotationReview) == review

    judged = items[0].model_copy(update={"relevant": True, "reason_code": "manual"})
    for kwargs in (
        {"annotation_universe_sha256": _sha(99), "items": items},
        {
            "annotation_universe_sha256": canonical_sha256(universe),
            "items": (items[1], items[0]),
        },
        {
            "annotation_universe_sha256": canonical_sha256(universe),
            "items": (judged, items[1]),
        },
    ):
        with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
            cache.write_annotation_review(
                source_manifest_sha256=_sha(1),
                criteria_set_sha256=_sha(2),
                annotation_universe_sha256=kwargs["annotation_universe_sha256"],
                candidate_count=2,
                ordered_item_factory=lambda values=kwargs["items"]: iter(values),
            )
    assert cache.read_model("annotation-review.json", R002AnnotationReview) == review


def test_annotation_review_reader_rejects_stale_universe_pair(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    first_key = _key(1)
    first = cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=1,
        ordered_key_factory=lambda: iter((first_key,)),
    )
    cache.write_annotation_review(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        annotation_universe_sha256=canonical_sha256(first),
        candidate_count=1,
        ordered_item_factory=lambda: iter(
            (R002AnnotationReviewItem(key=first_key, line_content="line 1"),)
        ),
    )
    second_key = _key(2)
    cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=1,
        ordered_key_factory=lambda: iter((second_key,)),
    )
    with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
        cache.read_model("annotation-review.json", R002AnnotationReview)


def test_public_stale_annotation_read_discards_sensitive_state(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache-sensitive-annotation"
    cache = R002Cache(cache_root)
    secret = "UNIQUE_ANNOTATION_SOURCE_SECRET"
    first_key = _key(1, secret)
    first = cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=1,
        ordered_key_factory=lambda: iter((first_key,)),
    )
    review = cache.write_annotation_review(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        annotation_universe_sha256=canonical_sha256(first),
        candidate_count=1,
        ordered_item_factory=lambda: iter(
            (R002AnnotationReviewItem(key=first_key, line_content=secret),)
        ),
    )
    cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=1,
        ordered_key_factory=lambda: iter((_key(2),)),
    )

    with pytest.raises(R002CacheError, match="annotation_pair_mismatch") as caught:
        cache.read_model("annotation-review.json", R002AnnotationReview)
    _assert_public_error_is_sanitized(
        caught.value,
        (secret, canonical_json_bytes(review).decode(), str(cache_root.resolve())),
    )


def test_streamed_replace_then_raise_reports_unknown_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    _write_universe(cache)
    real_replace = os.replace

    def replacing_then_raising(*args, **kwargs) -> None:
        real_replace(*args, **kwargs)
        raise OSError("ambiguous stream replace")

    monkeypatch.setattr(os, "replace", replacing_then_raising)
    with pytest.raises(R002CacheError, match="cache_state_unknown"):
        cache.write_annotation_universe(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            candidate_count=1,
            ordered_key_factory=lambda: iter((_key(3),)),
        )


def test_stream_temp_close_failure_never_retries_a_reused_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close_fd = cache_module._close_fd
    replacement_fd = -1

    def close_temp_reuse_number_and_fail(fd: int) -> bool:
        nonlocal replacement_fd
        if replacement_fd < 0 and stat.S_ISREG(os.fstat(fd).st_mode):
            assert real_close_fd(fd)
            replacement_fd = os.open("/dev/null", os.O_RDONLY)
            assert replacement_fd == fd
            return False
        return real_close_fd(fd)

    monkeypatch.setattr(cache_module, "_close_fd", close_temp_reuse_number_and_fail)
    try:
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            R002Cache(tmp_path / "cache").write_annotation_universe(
                source_manifest_sha256=_sha(1),
                criteria_set_sha256=_sha(2),
                candidate_count=1,
                ordered_key_factory=lambda: iter((_key(1),)),
            )
        assert replacement_fd >= 0
        assert stat.S_ISCHR(os.fstat(replacement_fd).st_mode)
    finally:
        if replacement_fd >= 0:
            with suppress(OSError):
                os.close(replacement_fd)


def test_annotation_writers_use_a_single_writer_lock(tmp_path: Path) -> None:
    first_cache = R002Cache(tmp_path / "cache")
    second_cache = R002Cache(tmp_path / "cache")
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()
    errors: list[BaseException] = []

    def first_factory():
        first_entered.set()
        assert release_first.wait(2)
        yield _key(1)

    def second_factory():
        second_entered.set()
        yield _key(1)

    def run(cache: R002Cache, factory) -> None:
        try:
            cache.write_annotation_universe(
                source_manifest_sha256=_sha(1),
                criteria_set_sha256=_sha(2),
                candidate_count=1,
                ordered_key_factory=factory,
            )
        except BaseException as error:  # pragma: no cover - asserted below
            errors.append(error)

    first = threading.Thread(target=run, args=(first_cache, first_factory))
    second = threading.Thread(target=run, args=(second_cache, second_factory))
    first.start()
    assert first_entered.wait(2)
    second.start()
    assert not second_entered.wait(0.2)
    release_first.set()
    first.join(2)
    second.join(2)
    assert not errors
    assert second_entered.is_set()


def test_annotation_writer_rejects_nonregular_lock_without_blocking(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=1,
        ordered_key_factory=lambda: iter((_key(1),)),
    )
    lock_path = tmp_path / "cache" / ".r002-annotation.lock"
    lock_path.unlink()
    os.mkfifo(lock_path, 0o600)

    with pytest.raises(R002CacheError, match="writer_lock_failed"):
        cache.write_annotation_universe(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            candidate_count=1,
            ordered_key_factory=lambda: iter((_key(1),)),
        )


def test_scratch_is_0600_seekable_immediately_unlinked_and_closed(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    with cache.open_unlinked_scratch() as scratch:
        fd = scratch.fileno()
        assert not scratch.closed
        assert scratch.readable()
        assert scratch.writable()
        assert scratch.seekable()
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o600
        assert os.fstat(fd).st_nlink == 0
        scratch.write(b"dataset")
        scratch.flush()
        assert scratch.tell() == len(b"dataset")
        scratch.seek(0)
        assert scratch.read() == b"dataset"
        assert not any(
            path.name.startswith(".r002-scratch-") for path in (tmp_path / "cache").iterdir()
        )
    assert scratch.closed
    with pytest.raises(ValueError):
        scratch.fileno()
    with pytest.raises(OSError):
        os.fstat(fd)


def test_scratch_supports_pyarrow_file_protocol(tmp_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    expected = pa.table({"value": ["fixture"]})
    with R002Cache(tmp_path / "cache").open_unlinked_scratch() as scratch:
        pq.write_table(expected, scratch)
        scratch.seek(0)
        assert pq.read_table(scratch).equals(expected)


def test_scratch_close_failure_is_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_fileio = io.FileIO

    class FailingClose:
        def __init__(self, wrapped) -> None:
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def close(self) -> None:
            self.wrapped.close()
            raise OSError("secret close detail")

    class FaultingIO:
        def __getattr__(self, name):
            return getattr(io, name)

        def FileIO(self, *args, **kwargs):
            return FailingClose(real_fileio(*args, **kwargs))

    monkeypatch.setattr(cache_module, "io", FaultingIO(), raising=False)
    with (
        pytest.raises(R002CacheError, match="scratch_failed") as caught,
        R002Cache(tmp_path / "cache").open_unlinked_scratch(),
    ):
        pass
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


@pytest.mark.parametrize("exit_path", ["normal", "caller_error"])
def test_scratch_preclose_failure_drops_all_public_handle_references(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_path: str
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_fileio = io.FileIO
    state: dict[str, object] = {}
    native_detail = "scratch-preclose-native-detail"
    secret = f"scratch-preclose-secret-{exit_path}".encode()

    class FailingBeforeClose:
        def __init__(self, wrapped) -> None:
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def close(self) -> None:
            raise OSError(errno.EIO, native_detail)

    def wrapping_fileio(*args, **kwargs):
        wrapped = FailingBeforeClose(real_fileio(*args, **kwargs))
        state["fd"] = wrapped.fileno()
        state["reference"] = weakref.ref(wrapped)
        return wrapped

    class FaultingIO:
        def __getattr__(self, name):
            return getattr(io, name)

        def FileIO(self, *args, **kwargs):
            return wrapping_fileio(*args, **kwargs)

    monkeypatch.setattr(cache_module, "io", FaultingIO(), raising=False)
    caller_error = R002CacheError("cache_read_failed")
    with (
        pytest.raises(R002CacheError) as caught,
        R002Cache(tmp_path / "cache").open_unlinked_scratch() as scratch,
    ):
        scratch.write(secret)
        scratch.seek(0)
        if exit_path == "caller_error":
            raise caller_error
    del scratch
    gc.collect()

    if exit_path == "normal":
        assert caught.value.args == ("scratch_failed",)
        assert type(caught.value.args[0]) is str
    else:
        assert caught.value is caller_error
        assert caught.value.args == ("cache_read_failed",)
    _assert_public_error_is_sanitized(
        caught.value,
        (native_detail, secret.decode()),
    )

    retained_handle_names: list[str] = []
    traceback = caught.value.__traceback__
    while traceback is not None:
        if Path(traceback.tb_frame.f_code.co_filename).name == "r002_cache.py":
            retained_handle_names.extend(
                name for name in traceback.tb_frame.f_locals if name == "handle"
            )
        traceback = traceback.tb_next

    reference = state["reference"]
    assert isinstance(reference, weakref.ReferenceType)
    leaked = reference()
    recovered_secret = False
    descriptor_was_open = True
    try:
        if leaked is not None:
            leaked.seek(0)
            recovered_secret = leaked.read() == secret
        try:
            os.fstat(state["fd"])  # type: ignore[arg-type]
        except OSError:
            descriptor_was_open = False
    finally:
        if leaked is not None:
            with suppress(OSError):
                leaked.wrapped.close()

    assert not retained_handle_names
    assert leaked is None
    assert not recovered_secret
    assert not descriptor_was_open


def test_scratch_nonowning_constructor_failure_closes_owned_descriptor_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close_fd = cache_module._close_fd
    constructed_fd = -1
    owned_close_attempts = 0
    native_detail = "scratch-nonowning-constructor-native-detail"

    class FaultingIO:
        def __getattr__(self, name):
            return getattr(io, name)

        def FileIO(self, fd: int, mode: str, *, closefd: bool):
            nonlocal constructed_fd
            constructed_fd = fd
            assert mode == "r+"
            assert closefd is False
            raise OSError(errno.EIO, native_detail)

    def recording_close_fd(fd: int) -> bool:
        nonlocal owned_close_attempts
        if fd == constructed_fd:
            owned_close_attempts += 1
        return real_close_fd(fd)

    monkeypatch.setattr(cache_module, "io", FaultingIO(), raising=False)
    monkeypatch.setattr(cache_module, "_close_fd", recording_close_fd)
    with (
        pytest.raises(R002CacheError, match="scratch_failed") as caught,
        R002Cache(tmp_path / "cache").open_unlinked_scratch(),
    ):
        pass
    assert caught.value.args == ("scratch_failed",)
    assert type(caught.value.args[0]) is str
    _assert_public_error_is_sanitized(caught.value, (native_detail,))
    assert constructed_fd >= 0
    assert owned_close_attempts == 1
    with pytest.raises(OSError):
        os.fstat(constructed_fd)


def test_scratch_constructor_cleanup_never_retries_reused_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close = os.close
    real_close_fd = cache_module._close_fd
    constructed_fd = -1
    replacement_fd = -1
    owned_close_attempts = 0
    filler_fds: list[int] = []
    native_detail = "scratch-constructor-cleanup-native-detail"

    class FaultingIO:
        def __getattr__(self, name):
            return getattr(io, name)

        def FileIO(self, fd: int, mode: str, *, closefd: bool):
            nonlocal constructed_fd
            constructed_fd = fd
            assert mode == "r+"
            assert closefd is False
            while not filler_fds or filler_fds[-1] <= fd:
                filler_fds.append(os.open("/dev/null", os.O_RDONLY))
            raise OSError(errno.EIO, native_detail)

    def ambiguous_owned_close(fd: int) -> bool:
        nonlocal owned_close_attempts, replacement_fd
        if fd != constructed_fd:
            return real_close_fd(fd)
        owned_close_attempts += 1
        if owned_close_attempts == 1:
            real_close(fd)
            replacement_fd = os.open("/dev/null", os.O_RDONLY)
            assert replacement_fd == fd
            return False
        return real_close_fd(fd)

    monkeypatch.setattr(cache_module, "io", FaultingIO(), raising=False)
    monkeypatch.setattr(cache_module, "_close_fd", ambiguous_owned_close)
    try:
        with (
            pytest.raises(R002CacheError, match="scratch_failed") as caught,
            R002Cache(tmp_path / "cache").open_unlinked_scratch(),
        ):
            pass
        assert caught.value.args == ("scratch_failed",)
        assert type(caught.value.args[0]) is str
        _assert_public_error_is_sanitized(caught.value, (native_detail,))
        assert owned_close_attempts == 1
        assert replacement_fd == constructed_fd
        assert stat.S_ISCHR(os.fstat(replacement_fd).st_mode)
    finally:
        if replacement_fd >= 0:
            with suppress(OSError):
                real_close(replacement_fd)
        for filler_fd in filler_fds:
            with suppress(OSError):
                real_close(filler_fd)


def test_scratch_wrapper_constructor_failure_closes_local_descriptor_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close_fd = cache_module._close_fd
    constructed_fd = -1
    owned_close_attempts = 0
    raw_reference: weakref.ReferenceType[io.FileIO] | None = None
    native_detail = "scratch-wrapper-constructor-native-detail"
    secret = "scratch-wrapper-constructor-secret"

    def failing_owner_constructor(*constructor_args: object) -> None:
        nonlocal constructed_fd, raw_reference
        raw = constructor_args[-1]
        assert isinstance(raw, io.FileIO)
        constructed_fd = raw.fileno()
        assert raw.closefd is False
        raw_reference = weakref.ref(raw)
        raise OSError(errno.EIO, f"{native_detail}:{secret}")

    def recording_close_fd(fd: int) -> bool:
        nonlocal owned_close_attempts
        if fd == constructed_fd:
            owned_close_attempts += 1
        return real_close_fd(fd)

    monkeypatch.setattr(cache_module, "_OwnedScratch", failing_owner_constructor)
    monkeypatch.setattr(cache_module, "_close_fd", recording_close_fd)
    with (
        pytest.raises(R002CacheError, match="scratch_failed") as caught,
        R002Cache(tmp_path / "cache").open_unlinked_scratch(),
    ):
        pass
    gc.collect()

    assert caught.value.args == ("scratch_failed",)
    assert type(caught.value.args[0]) is str
    _assert_public_error_is_sanitized(caught.value, (native_detail, secret))
    assert constructed_fd >= 0
    assert raw_reference is not None
    assert raw_reference() is None

    descriptor_open = True
    try:
        os.fstat(constructed_fd)
    except OSError:
        descriptor_open = False
    if descriptor_open:
        os.close(constructed_fd)

    assert owned_close_attempts == 1
    assert not descriptor_open


def test_scratch_transfer_interruption_closes_transferred_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_transfer = cache_module._transfer_scratch_fd
    transferred_fd = -1

    def transfer_then_interrupt(scratch, fd: int) -> None:
        nonlocal transferred_fd
        real_transfer(scratch, fd)
        transferred_fd = fd
        raise KeyboardInterrupt()

    monkeypatch.setattr(cache_module, "_transfer_scratch_fd", transfer_then_interrupt)
    with (
        pytest.raises(KeyboardInterrupt),
        R002Cache(tmp_path / "cache").open_unlinked_scratch(),
    ):
        pass

    assert transferred_fd >= 0
    with pytest.raises(OSError):
        os.fstat(transferred_fd)


def test_scratch_post_transfer_interruption_closes_descriptor_while_trace_is_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    transferred_fd = -1
    retained: KeyboardInterrupt | None = None
    real_transfer = cache_module._transfer_scratch_fd

    def recording_transfer(scratch, fd: int) -> None:
        nonlocal transferred_fd
        real_transfer(scratch, fd)
        transferred_fd = fd

    def interrupt_after_transfer(scratch):
        del scratch
        raise KeyboardInterrupt()

    monkeypatch.setattr(cache_module, "_transfer_scratch_fd", recording_transfer)
    monkeypatch.setattr(cache_module, "_finish_scratch_transfer", interrupt_after_transfer)
    try:
        with (
            pytest.raises(KeyboardInterrupt) as caught,
            R002Cache(tmp_path / "cache").open_unlinked_scratch(),
        ):
            pass
        retained = caught.value
        assert transferred_fd >= 0
        with pytest.raises(OSError):
            os.fstat(transferred_fd)
    finally:
        del retained


def test_scratch_closes_duplicate_when_root_close_reports_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close_fd = cache_module._close_fd
    real_dup = os.dup
    source_fd = -1
    duplicate_fd = -1

    def recording_dup(fd: int) -> int:
        nonlocal source_fd, duplicate_fd
        source_fd = fd
        duplicate_fd = real_dup(fd)
        return duplicate_fd

    def close_root_then_report_failure(fd: int) -> bool:
        if duplicate_fd >= 0 and stat.S_ISDIR(os.fstat(fd).st_mode):
            assert real_close_fd(fd)
            return False
        return real_close_fd(fd)

    monkeypatch.setattr(cache_module.os, "dup", recording_dup)
    monkeypatch.setattr(cache_module, "_close_fd", close_root_then_report_failure)
    try:
        with (
            pytest.raises(R002CacheError, match="cache_state_unknown") as caught,
            R002Cache(tmp_path / "cache").open_unlinked_scratch(),
        ):
            pass
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is None
        assert source_fd >= 0
        assert duplicate_fd >= 0
        for fd in (source_fd, duplicate_fd):
            with pytest.raises(OSError):
                os.fstat(fd)
    finally:
        if duplicate_fd >= 0:
            with suppress(OSError):
                os.close(duplicate_fd)


def test_ambiguous_close_does_not_close_a_reused_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close = os.close
    replacement_fd = -1

    def close_then_reuse_and_raise(fd: int) -> None:
        nonlocal replacement_fd
        if replacement_fd < 0:
            real_close(fd)
            replacement_fd = os.open("/dev/null", os.O_RDONLY)
            assert replacement_fd == fd
            raise OSError("ambiguous close failure")
        real_close(fd)

    monkeypatch.setattr(cache_module.os, "close", close_then_reuse_and_raise)
    with pytest.raises(R002CacheError):
        R002Cache(tmp_path / "cache").replace_model("criteria-proposal.json", _criteria_proposal())
    monkeypatch.setattr(cache_module.os, "close", real_close)

    assert replacement_fd >= 0
    assert stat.S_ISCHR(os.fstat(replacement_fd).st_mode)
    real_close(replacement_fd)


def test_root_walk_closes_each_owned_descriptor_number_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_close_fd = cache_module._close_fd
    replacement_fds: list[int] = []

    def close_reuse_number_and_fail(fd: int) -> bool:
        if len(replacement_fds) < 2:
            assert stat.S_ISDIR(os.fstat(fd).st_mode)
            assert real_close_fd(fd)
            replacement = os.open("/dev/null", os.O_RDONLY)
            assert replacement == fd
            replacement_fds.append(replacement)
            return False
        return real_close_fd(fd)

    monkeypatch.setattr(cache_module, "_close_fd", close_reuse_number_and_fail)
    try:
        with pytest.raises(R002CacheError):
            R002Cache(tmp_path / "cache").replace_model(
                "criteria-proposal.json", _criteria_proposal()
            )
        assert len(replacement_fds) == 2
        for fd in replacement_fds:
            assert stat.S_ISCHR(os.fstat(fd).st_mode)
    finally:
        for fd in replacement_fds:
            with suppress(OSError):
                os.close(fd)


def test_unsupported_required_primitive_fails_closed_before_root_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    monkeypatch.setattr(cache_module.os, "O_NOFOLLOW", 0)
    with pytest.raises(R002CacheError, match="unsupported_filesystem_primitives"):
        R002Cache(tmp_path / "cache").replace_model("criteria-proposal.json", _criteria_proposal())
    assert not (tmp_path / "cache").exists()


def test_public_error_traceback_does_not_retain_hostile_relative_name(tmp_path: Path) -> None:
    hostile = "../secret-hostile-name"
    with pytest.raises(R002CacheError) as caught:
        R002Cache(tmp_path / "cache").write_bytes(hostile, b"secret-body")

    cache_frames = []
    traceback = caught.value.__traceback__
    while traceback is not None:
        if Path(traceback.tb_frame.f_code.co_filename).name == "r002_cache.py":
            cache_frames.append(traceback.tb_frame)
        traceback = traceback.tb_next
    retained = " ".join(repr(frame.f_locals) for frame in cache_frames)
    assert "secret-hostile-name" not in retained
    assert "secret-body" not in retained
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.args == ("unsafe_relative_name",)


def test_module_has_no_pyarrow_or_network_dependency() -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    source = Path(cache_module.__file__).read_text(encoding="utf-8")
    assert "pyarrow" not in source
    assert "httpx" not in source
    assert "requests" not in source
    assert "subprocess" not in source
    assert "exec(" not in source
    assert "os.fdopen" not in source


def test_candidate_label_control_mapping_is_typed(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    proposal = R002CandidateLabelProposal.model_construct()
    with pytest.raises(R002CacheError, match="model_validation_failed"):
        cache.replace_model("candidate-label-proposal.json", proposal)
    with pytest.raises(R002CacheError, match="model_type_mismatch"):
        cache.read_model("criteria-proposal.json", R002CandidateLabelProposal)


def test_persisted_control_is_canonical_json_without_terminal_newline(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    proposal = _criteria_proposal()
    path = cache.write_model("criteria-proposal.json", proposal)
    assert path.read_bytes() == canonical_json_bytes(proposal)
    assert not path.read_bytes().endswith(b"\n")
    assert json.loads(path.read_bytes()) == proposal.model_dump(mode="json")


def test_scratch_wrapper_exercises_binary_protocol_and_closed_guards(
    tmp_path: Path,
) -> None:
    with R002Cache(tmp_path / "cache").open_unlinked_scratch() as scratch:
        assert scratch.write(b"abcdef") == 6
        assert scratch.tell() == 6
        assert scratch.seek(0) == 0
        target = bytearray(3)
        assert scratch.readinto(target) == 3
        assert bytes(target) == b"abc"
        assert scratch.truncate(4) == 4
        scratch.flush()
        scratch.close()
        scratch.close()
        assert scratch.closed is True
        with pytest.raises(ValueError, match="closed file"):
            scratch.fileno()
        with pytest.raises(ValueError, match="closed file"):
            scratch.read(1)


def test_public_cache_wrappers_sanitize_unexpected_internal_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    cache = R002Cache(tmp_path / "cache")
    secret = "unexpected-internal-secret"

    def unexpected(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError(secret)

    cases = (
        (
            "_write_bytes_public_internal",
            lambda: cache.write_bytes(f"head-files/{_sha(1)}", b"value"),
            "cache_write_failed",
        ),
        (
            "_write_content_addressed_model_public_internal",
            lambda: cache.write_content_addressed_model(
                f"rows/{_sha(2)}", _row(1), SWEbenchVerifiedRow
            ),
            "cache_write_failed",
        ),
        (
            "_write_model_public_internal",
            lambda: cache.write_model("criteria-proposal.json", _criteria_proposal()),
            "cache_write_failed",
        ),
        (
            "_replace_model_public_internal",
            lambda: cache.replace_model("criteria-proposal.json", _criteria_proposal()),
            "cache_write_failed",
        ),
        (
            "_read_bytes_public_internal",
            lambda: cache.read_bytes(f"head-files/{_sha(3)}"),
            "cache_read_failed",
        ),
        (
            "_read_model_public_internal",
            lambda: cache.read_model("criteria-proposal.json", R002CriteriaProposal),
            "cache_read_failed",
        ),
        (
            "_publish_criteria_source_index_internal",
            lambda: cache.publish_criteria_source_index(
                R002CriteriaSourceIndex.model_construct()
            ),
            "cache_write_failed",
        ),
        (
            "_load_criteria_source_index_internal",
            cache.load_criteria_source_index,
            "cache_read_failed",
        ),
        (
            "_publish_index_internal",
            lambda: cache.publish_index(R002CacheIndex.model_construct()),
            "cache_write_failed",
        ),
        (
            "_load_index_internal",
            cache.load_index,
            "cache_read_failed",
        ),
        (
            "_write_annotation_universe_internal",
            lambda: cache.write_annotation_universe(
                source_manifest_sha256=_sha(4),
                criteria_set_sha256=_sha(5),
                candidate_count=1,
                ordered_key_factory=lambda: iter(()),
            ),
            "annotation_stream_invalid",
        ),
        (
            "_write_annotation_review_internal",
            lambda: cache.write_annotation_review(
                source_manifest_sha256=_sha(4),
                criteria_set_sha256=_sha(5),
                annotation_universe_sha256=_sha(6),
                candidate_count=1,
                ordered_item_factory=lambda: iter(()),
            ),
            "annotation_pair_mismatch",
        ),
        (
            "_open_scratch_internal",
            lambda: cache.open_unlinked_scratch().__enter__(),
            "scratch_failed",
        ),
    )

    for method_name, operation, reason in cases:
        with monkeypatch.context() as scoped:
            scoped.setattr(cache_module.R002Cache, method_name, unexpected)
            with pytest.raises(R002CacheError, match=reason) as caught:
                operation()
        _assert_public_error_is_sanitized(caught.value, (secret,))


def test_low_level_cache_failures_are_closed_and_classified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    file_path = tmp_path / "plain"
    file_path.write_bytes(b"value")
    file_fd = os.open(file_path, os.O_RDONLY)
    directory_fd = os.open(tmp_path, os.O_RDONLY)
    try:
        with pytest.raises(R002CacheError, match="symlink_or_nondirectory"):
            cache_module.R002Cache._verify_directory(file_fd, owned=False)

        with monkeypatch.context() as scoped:
            scoped.setattr(cache_module.os, "fstat", lambda fd: (_ for _ in ()).throw(OSError()))
            with pytest.raises(R002CacheError, match="cache_directory_security"):
                cache_module.R002Cache._verify_directory(directory_fd, owned=False)
            with pytest.raises(R002CacheError, match="cache_file_security"):
                cache_module.R002Cache._verify_file(file_fd)

        with monkeypatch.context() as scoped:
            scoped.setattr(cache_module, "_close_fd", lambda fd: False)
            assert cache_module._close_all([file_fd]) is False

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "open",
                lambda *args, **kwargs: (_ for _ in ()).throw(FileExistsError()),
            )
            with pytest.raises(R002CacheError, match="temp_collision"):
                cache_module.R002Cache._new_temp(directory_fd)

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "open",
                lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
            )
            with pytest.raises(R002CacheError, match="cache_write_failed"):
                cache_module.R002Cache._new_temp(directory_fd)

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "unlink",
                lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
            )
            with pytest.raises(R002CacheError, match="cache_state_unknown"):
                cache_module.R002Cache._unlink_created(directory_fd, "temp")

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "write",
                lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
            )
            with pytest.raises(R002CacheError, match="cache_write_failed"):
                cache_module.R002Cache._write_all(file_fd, b"value")

        with monkeypatch.context() as scoped:
            scoped.setattr(cache_module.os, "write", lambda *args, **kwargs: 0)
            with pytest.raises(R002CacheError, match="cache_write_failed"):
                cache_module.R002Cache._write_all(file_fd, b"value")
    finally:
        os.close(file_fd)
        os.close(directory_fd)

    with (
        pytest.raises(R002CacheError, match="cache_directory_security"),
        R002Cache(Path("/"))._open_root(),
    ):
        pass


def test_public_read_and_annotation_validation_failure_paths(tmp_path: Path) -> None:
    cache = R002Cache(tmp_path / "cache")
    body = b"head"
    digest = sha256(body).hexdigest()
    cache.write_bytes(f"head-files/{digest}", body)

    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.read_bytes(f"head-files/{digest}", expected_sha256=_sha(99))
    with pytest.raises(R002CacheError, match="model_type_mismatch"):
        cache.read_bytes("annotation-universe.json")
    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.read_bytes(f"head-files/{digest}", expected_sha256="not-a-hash")

    invalid_universe_calls = (
        {
            "source_manifest_sha256": "bad",
            "criteria_set_sha256": _sha(2),
            "candidate_count": 1,
            "ordered_key_factory": lambda: iter((_key(1),)),
        },
        {
            "source_manifest_sha256": _sha(1),
            "criteria_set_sha256": _sha(2),
            "candidate_count": 0,
            "ordered_key_factory": lambda: iter(()),
        },
    )
    for arguments in invalid_universe_calls:
        with pytest.raises(
            R002CacheError,
            match=r"annotation_stream_invalid|annotation_pair_limit",
        ):
            cache.write_annotation_universe(**arguments)

    invalid_review_calls = (
        {
            "source_manifest_sha256": "bad",
            "criteria_set_sha256": _sha(2),
            "annotation_universe_sha256": _sha(3),
            "candidate_count": 1,
            "ordered_item_factory": lambda: iter(()),
        },
        {
            "source_manifest_sha256": _sha(1),
            "criteria_set_sha256": _sha(2),
            "annotation_universe_sha256": _sha(3),
            "candidate_count": 0,
            "ordered_item_factory": lambda: iter(()),
        },
    )
    for arguments in invalid_review_calls:
        with pytest.raises(
            R002CacheError,
            match=r"annotation_pair_mismatch|annotation_pair_limit",
        ):
            cache.write_annotation_review(**arguments)


class _IteratorFailure:
    def __init__(self, *, fail_during_iter: bool) -> None:
        self.fail_during_iter = fail_during_iter

    def __iter__(self):
        if self.fail_during_iter:
            raise KeyboardInterrupt()
        return self

    def __next__(self):
        raise KeyboardInterrupt()


@pytest.mark.parametrize("fail_during_iter", [True, False])
def test_annotation_universe_normalizes_iterator_base_exceptions(
    tmp_path: Path, fail_during_iter: bool
) -> None:
    cache = R002Cache(tmp_path / "cache")
    with pytest.raises(R002CacheError, match="annotation_stream_invalid"):
        cache.write_annotation_universe(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            candidate_count=1,
            ordered_key_factory=lambda: _IteratorFailure(
                fail_during_iter=fail_during_iter
            ),
        )


@pytest.mark.parametrize("fail_during_iter", [True, False])
def test_annotation_review_normalizes_iterator_base_exceptions(
    tmp_path: Path, fail_during_iter: bool
) -> None:
    cache = R002Cache(tmp_path / "cache")
    key = _key(1)
    universe = cache.write_annotation_universe(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        candidate_count=1,
        ordered_key_factory=lambda: iter((key,)),
    )
    with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
        cache.write_annotation_review(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            annotation_universe_sha256=canonical_sha256(universe),
            candidate_count=1,
            ordered_item_factory=lambda: _IteratorFailure(
                fail_during_iter=fail_during_iter
            ),
        )


def test_criteria_source_index_maps_corruption_and_reopen_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    criteria_index = cache.load_criteria_source_index()

    first = criteria_index.cases[0]
    source_path = tmp_path / "cache" / "criteria-sources" / first.problem_statement_sha256
    source_path.write_bytes(b"same-length-wrong")
    source_path.chmod(0o600)
    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.load_criteria_source_index()

    cache = R002Cache(tmp_path / "second-cache")
    _prepared_cache(cache)
    current = cache.load_criteria_source_index()
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_load_criteria_source_index_internal",
            lambda: current.model_copy(update={"manifest_sha256": _sha(777)}),
        )
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            cache._publish_criteria_source_index_internal(current)

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_load_criteria_source_index_internal",
            lambda: (_ for _ in ()).throw(R002CacheError("completion_marker_missing")),
        )
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            cache._publish_criteria_source_index_internal(current)

    assert index.complete is True


def test_cache_index_maps_missing_corrupt_objects_and_reopen_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    cache.publish_index(index)

    first = index.cases[0]
    row_path = tmp_path / "cache" / "rows" / first.row_sha256
    row_path.unlink()
    with pytest.raises(R002CacheError, match="referenced_object_missing"):
        cache.load_index()

    cache = R002Cache(tmp_path / "second-cache")
    index = _prepared_cache(cache)
    head = index.cases[0].head_files[0]
    head_path = tmp_path / "second-cache" / "head-files" / head.content_sha256
    head_path.write_bytes(b"wrong")
    head_path.chmod(0o600)
    with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
        cache.publish_index(index)

    cache = R002Cache(tmp_path / "third-cache")
    index = _prepared_cache(cache)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_load_index_internal",
            lambda: index.model_copy(update={"criteria_set_sha256": _sha(778)}),
        )
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            cache._publish_index_internal(index)

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_load_index_internal",
            lambda: (_ for _ in ()).throw(R002CacheError("completion_marker_missing")),
        )
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            cache._publish_index_internal(index)


def test_annotation_lock_release_and_stream_limits_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    cache = R002Cache(tmp_path / "cache")
    real_flock = cache_module.fcntl.flock

    def unlock_failure(fd: int, operation: int) -> None:
        if operation == cache_module.fcntl.LOCK_UN:
            raise OSError("simulated unlock failure")
        real_flock(fd, operation)

    with monkeypatch.context() as scoped:
        scoped.setattr(cache_module.fcntl, "flock", unlock_failure)
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            cache.write_annotation_universe(
                source_manifest_sha256=_sha(1),
                criteria_set_sha256=_sha(2),
                candidate_count=1,
                ordered_key_factory=lambda: iter((_key(1),)),
            )

    read_fd = os.open("/dev/null", os.O_RDONLY)
    try:
        with pytest.raises(R002CacheError, match="annotation_pair_limit"):
            cache._stream_piece(read_fd, b"ab", size=1, limit=2)
    finally:
        os.close(read_fd)


def test_stream_replace_detects_destination_drift_and_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    calls = 0
    real_preflight = cache._preflight_replace_destination

    def drifting_preflight(*args, **kwargs):
        nonlocal calls
        calls += 1
        result = real_preflight(*args, **kwargs)
        if calls == 2:
            return ("drifted",)
        return result

    with monkeypatch.context() as scoped:
        scoped.setattr(cache, "_preflight_replace_destination", drifting_preflight)
        with pytest.raises(R002CacheError, match="cache_replace_failed"):
            _write_universe(cache)

    cache = R002Cache(tmp_path / "cleanup-cache")
    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_unlink_created",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                R002CacheError("cache_state_unknown")
            ),
        )
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            cache.write_annotation_universe(
                source_manifest_sha256=_sha(1),
                criteria_set_sha256=_sha(2),
                candidate_count=1,
                ordered_key_factory=lambda: (_ for _ in ()).throw(RuntimeError("writer")),
            )


def test_annotation_reopen_drift_and_invalid_items_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    universe = _write_universe(cache)
    real_read = cache._read_model_internal

    def drifting_universe(relative_name, model_type, **kwargs):
        value = real_read(relative_name, model_type, **kwargs)
        if relative_name == "annotation-universe.json":
            return value.model_copy(update={"criteria_set_sha256": _sha(999)})
        return value

    with monkeypatch.context() as scoped:
        scoped.setattr(cache, "_read_model_internal", drifting_universe)
        with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
            cache._write_annotation_universe_internal(
                source_manifest_sha256=_sha(1),
                criteria_set_sha256=_sha(2),
                candidate_count=2,
                ordered_key_factory=lambda: iter((_key(1), _key(2))),
            )

    invalid = R002AnnotationReviewItem.model_construct(key=_key(1), line_content=object())
    with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
        cache.write_annotation_review(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            annotation_universe_sha256=canonical_sha256(universe),
            candidate_count=2,
            ordered_item_factory=lambda: iter((invalid,)),
        )


def test_cache_destination_usability_rejects_unbound_or_invalid_objects(
    tmp_path: Path,
) -> None:
    cache = R002Cache(tmp_path / "cache")
    row = _row(1)
    row_bytes = canonical_json_bytes(row)

    assert not cache._replace_destination_usable(f"rows/{_sha(1)}", row_bytes)
    assert not cache._replace_destination_usable(
        f"rows/{sha256(b'not-json').hexdigest()}", b"not-json"
    )
    assert not cache._replace_destination_usable("unknown.json", b"{}")

    review = _review_bundle()
    review_bytes = canonical_json_bytes(review)
    assert not cache._replace_destination_usable("reviews/R002-999.json", review_bytes)

    universe = _write_universe(cache)
    mismatched_review = R002AnnotationReview(
        source_manifest_sha256=_sha(1),
        criteria_set_sha256=_sha(2),
        annotation_universe_sha256=_sha(999),
        items=tuple(
            R002AnnotationReviewItem(key=_key(number), line_content=f"line {number}")
            for number in (1, 2)
        ),
    )
    assert not cache._replace_destination_usable(
        "annotation-review.json", canonical_json_bytes(mismatched_review)
    )
    assert canonical_sha256(universe) != mismatched_review.annotation_universe_sha256


def test_low_level_snapshot_and_temp_failures_are_conservative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    cache = R002Cache(tmp_path / "cache")
    with cache._open_root() as root_fd:
        with pytest.raises(R002CacheError, match="cache_file_security"):
            cache._prepare_temp(root_fd, b"too-large", 1)

        with monkeypatch.context() as scoped:
            scoped.setattr(cache, "_read_checked", lambda *args, **kwargs: b"different")
            with pytest.raises(R002CacheError, match="cache_write_failed"):
                cache._prepare_temp(root_fd, b"expected", 100)

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "fsync",
                lambda fd: (_ for _ in ()).throw(OSError("fsync")),
            )
            with pytest.raises(R002CacheError, match="cache_fsync_failed"):
                cache._fsync(root_fd)

        assert cache._ambiguous_link_snapshot(
            root_fd, "missing", "criteria-proposal.json"
        ) is None

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "unlink",
                lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
            )
            with pytest.raises(R002CacheError, match="cache_state_unknown"):
                cache._remove_ambiguous_temp_and_sync(
                    root_fd, "missing", require_present=True
                )

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "unlink",
                lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
            )
            with pytest.raises(R002CacheError, match="cache_state_unknown"):
                cache._remove_ambiguous_temp_and_sync(
                    root_fd, "missing", require_present=False
                )


def test_read_snapshot_rejects_oversize_read_failure_and_close_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    path = tmp_path / "value"
    path.write_bytes(b"content")
    path.chmod(0o600)
    parent_fd = os.open(tmp_path, os.O_RDONLY)
    try:
        with pytest.raises(R002CacheError, match="cache_file_security"):
            R002Cache._read_checked_snapshot(parent_fd, "value", max_bytes=1)

        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module.os,
                "read",
                lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
            )
            with pytest.raises(R002CacheError, match="cache_read_failed"):
                R002Cache._read_checked_snapshot(parent_fd, "value", max_bytes=100)

        leaked_fds: list[int] = []
        with monkeypatch.context() as scoped:
            scoped.setattr(
                cache_module,
                "_close_fd",
                lambda fd: leaked_fds.append(fd) and False,
            )
            with pytest.raises(R002CacheError, match="cache_state_unknown"):
                R002Cache._read_checked_snapshot(parent_fd, "value", max_bytes=100)
        for leaked_fd in leaked_fds:
            os.close(leaked_fd)
    finally:
        os.close(parent_fd)


def test_index_internal_corruption_mappings_cover_length_rows_and_heads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    index = _prepared_cache(cache)
    criteria_index = cache.load_criteria_source_index()

    first_source = criteria_index.cases[0]
    with monkeypatch.context() as scoped:
        scoped.setattr(cache, "_read_bytes_internal", lambda *args, **kwargs: b"x")
        with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
            cache._verify_criteria_source_index(
                criteria_index.model_copy(
                    update={
                        "cases": (
                            first_source.model_copy(update={"byte_length": 2}),
                            *criteria_index.cases[1:],
                        )
                    }
                )
            )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            cache,
            "_read_model_internal",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                R002CacheError("model_validation_failed")
            ),
        )
        with pytest.raises(R002CacheError, match="criteria_source_index_mismatch"):
            cache._load_criteria_source_index_internal()
        with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
            cache._load_index_internal()

    first_case = index.cases[0]
    with monkeypatch.context() as scoped:
        real_read_model = cache._read_model_internal

        def wrong_row(relative_name, model_type, **kwargs):
            if relative_name.startswith("rows/"):
                return _row(999)
            return real_read_model(relative_name, model_type, **kwargs)

        scoped.setattr(
            cache,
            "_read_model_internal",
            wrong_row,
        )
        with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
            cache._verify_cache_index(index)

    with monkeypatch.context() as scoped:
        real_read_model = cache._read_model_internal

        def row_then_real(relative_name, model_type, **kwargs):
            if relative_name.startswith("rows/"):
                return real_read_model(relative_name, model_type, **kwargs)
            return real_read_model(relative_name, model_type, **kwargs)

        scoped.setattr(cache, "_read_model_internal", row_then_real)
        real_read_bytes = cache._read_bytes_internal

        def fail_head(relative_name, **kwargs):
            if relative_name.startswith("head-files/"):
                raise R002CacheError("cache_file_security")
            return real_read_bytes(relative_name, **kwargs)

        scoped.setattr(
            cache,
            "_read_bytes_internal",
            fail_head,
        )
        with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
            cache._verify_cache_index(index)

    with monkeypatch.context() as scoped:
        scoped.setattr(cache, "_read_model_internal", cache._read_model_internal)
        real_read_bytes = cache._read_bytes_internal

        def short_head(relative_name, **kwargs):
            if relative_name.startswith("head-files/"):
                return b"x"
            return real_read_bytes(relative_name, **kwargs)

        scoped.setattr(cache, "_read_bytes_internal", short_head)
        with pytest.raises(R002CacheError, match="referenced_object_mismatch"):
            cache._verify_cache_index(
                index.model_copy(
                    update={
                        "cases": (
                            first_case.model_copy(
                                update={
                                    "head_files": (
                                        first_case.head_files[0].model_copy(
                                            update={"byte_length": 2}
                                        ),
                                    )
                                }
                            ),
                            *index.cases[1:],
                        )
                    }
                )
            )


def test_annotation_invalid_constructed_values_and_reopen_failures_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    invalid_key = R002CandidateLineKey.model_construct(path="../unsafe")
    with pytest.raises(R002CacheError, match="annotation_stream_invalid"):
        cache.write_annotation_universe(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            candidate_count=1,
            ordered_key_factory=lambda: iter((invalid_key,)),
        )

    universe = _write_universe(cache)
    item = R002AnnotationReviewItem(key=_key(1), line_content="line 1")
    item_two = R002AnnotationReviewItem(key=_key(2), line_content="line 2")
    with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
        cache.write_annotation_review(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            annotation_universe_sha256=canonical_sha256(universe),
            candidate_count=2,
            ordered_item_factory=lambda: iter((item, item_two, item)),
        )
    with pytest.raises(R002CacheError, match="annotation_pair_mismatch"):
        cache.write_annotation_review(
            source_manifest_sha256=_sha(1),
            criteria_set_sha256=_sha(2),
            annotation_universe_sha256=canonical_sha256(universe),
            candidate_count=2,
            ordered_item_factory=lambda: iter((item,)),
        )

    cache = R002Cache(tmp_path / "reopen-cache")
    real_read_checked = cache._read_checked
    calls = 0

    def fail_reopen(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise R002CacheError("cache_read_failed")
        return real_read_checked(*args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(cache, "_read_checked", fail_reopen)
        with pytest.raises(R002CacheError, match="cache_state_unknown"):
            _write_universe(cache)


def test_public_criteria_index_publish_preserves_closed_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = R002Cache(tmp_path / "cache")
    monkeypatch.setattr(
        cache,
        "_publish_criteria_source_index_internal",
        lambda index: (_ for _ in ()).throw(
            R002CacheError("criteria_source_index_mismatch")
        ),
    )
    with pytest.raises(R002CacheError, match="criteria_source_index_mismatch"):
        cache.publish_criteria_source_index(R002CriteriaSourceIndex.model_construct())
