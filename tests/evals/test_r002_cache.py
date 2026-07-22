"""Adversarial persistence tests for the local-only R-002 research cache."""

from __future__ import annotations

import json
import os
import stat
import threading
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
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o600
        assert os.fstat(fd).st_nlink == 0
        scratch.write(b"dataset")
        scratch.seek(0)
        assert scratch.read() == b"dataset"
        assert not any(
            path.name.startswith(".r002-scratch-") for path in (tmp_path / "cache").iterdir()
        )
    with pytest.raises(OSError):
        os.fstat(fd)


def test_scratch_close_failure_is_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scopeproof_core.evals.r002_cache as cache_module

    real_fdopen = os.fdopen

    class FailingClose:
        def __init__(self, wrapped) -> None:
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def close(self) -> None:
            self.wrapped.close()
            raise OSError("secret close detail")

    monkeypatch.setattr(
        cache_module.os,
        "fdopen",
        lambda *args, **kwargs: FailingClose(real_fdopen(*args, **kwargs)),
    )
    with (
        pytest.raises(R002CacheError, match="scratch_failed") as caught,
        R002Cache(tmp_path / "cache").open_unlinked_scratch(),
    ):
        pass
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


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
