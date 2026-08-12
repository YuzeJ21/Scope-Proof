import json
import multiprocessing
import subprocess
import sys
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path
from threading import BrokenBarrierError

import pytest
from pydantic import ValidationError

import scopeproof_core.alpha.storage as alpha_storage_module
from scopeproof_core.alpha.models import ParticipantRole
from scopeproof_core.alpha.service import initialize_alpha_case
from scopeproof_core.alpha.storage import JsonAlphaCaseStore, UnsafeAlphaCaseStore
from scopeproof_core.cli import _build_bundle
from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import (
    Criterion,
    PullRequestSnapshot,
    RepositoryVisibility,
    ReviewInputOrigin,
)


def criteria_source_provenance(*, source_revision: str = "issue-6@abc123"):
    return build_criteria_source_provenance(
        source_uri="https://github.com/acme/repo/issues/6",
        source_revision=source_revision,
        source_text="Export CSV\n",
        criteria=[Criterion(criterion_id="AC-01", text="Export CSV")],
        confirmed_by="Repository owner",
        confirmed_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


def alpha_case():
    return initialize_alpha_case(
        public_pr_url="https://github.com/acme/repo/pull/7",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.ENGINEERING,
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
        confirmed_criterion_snapshot=[
            Criterion(criterion_id="AC-01", text="Export CSV")
        ],
        criteria_source_provenance=criteria_source_provenance(),
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
    )


class SynchronizedAlphaCaseStore(JsonAlphaCaseStore):
    def __init__(self, directory: Path, barrier) -> None:
        super().__init__(directory)
        self.barrier = barrier

    def _write(self, target, record):
        with suppress(BrokenBarrierError):
            self.barrier.wait(timeout=3)
        return super()._write(target, record)


def _run_alpha_mutation(
    directory: str,
    record_payload: dict,
    operation: str,
    barrier,
    outcomes,
) -> None:
    from scopeproof_core.alpha.models import AlphaCaseRecord

    record = AlphaCaseRecord.model_validate(record_payload)
    store = SynchronizedAlphaCaseStore(Path(directory), barrier)
    try:
        getattr(store, operation)(record)
    except (FileExistsError, ValueError) as error:
        outcomes.put(type(error).__name__)
    else:
        outcomes.put("success")


def matching_review_state():
    criteria = [Criterion(criterion_id="AC-01", text="Export CSV")]
    snapshot = PullRequestSnapshot(
        repository="acme/repo",
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        pr_number=7,
        title="Export CSV",
        html_url="https://github.com/acme/repo/pull/7",
        base_sha="b" * 40,
        head_sha="a" * 40,
    )
    return new_review_state(
        _build_bundle(
            snapshot,
            criteria,
            "Export CSV\n",
            criteria_source_provenance(),
            input_origin=ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
        )
    )


def test_alpha_case_round_trips_as_validated_json(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)

    path = store.save(record)

    assert store.load(record.case_id) == record
    assert path.name == f"{record.case_id}.json"
    assert store.list_case_ids() == [record.case_id]


def test_alpha_case_save_refuses_silent_overwrite(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    store.save(record)

    with pytest.raises(FileExistsError):
        store.save(record)


def test_cli_and_alpha_storage_import_without_posix_only_constants() -> None:
    script = """
import importlib
import os
for name in ('O_DIRECTORY', 'O_NOFOLLOW'):
    if hasattr(os, name):
        delattr(os, name)
importlib.import_module('scopeproof_core.cli')
importlib.import_module('scopeproof_core.alpha.storage')
importlib.import_module('scopeproof_core.alpha.rehearsal_storage')
importlib.import_module('apps.web.app')
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_concurrent_process_alpha_creates_publish_exactly_once(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    outcomes = context.Queue()
    record = alpha_case()
    processes = [
        context.Process(
            target=_run_alpha_mutation,
            args=(
                str(tmp_path),
                record.model_dump(mode="json"),
                "save",
                barrier,
                outcomes,
            ),
        )
        for _ in range(2)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0

    assert sorted(outcomes.get(timeout=2) for _ in range(2)) == [
        "FileExistsError",
        "success",
    ]
    assert JsonAlphaCaseStore(tmp_path).load(record.case_id) == record
    assert sorted(path.name for path in tmp_path.iterdir()) == [f"{record.case_id}.json"]


def test_alpha_case_update_requires_existing_same_case(tmp_path: Path) -> None:
    record = alpha_case()
    directory = tmp_path / "missing" / "alpha-cases"
    store = JsonAlphaCaseStore(directory)

    with pytest.raises(FileNotFoundError):
        store.update(record)

    assert not directory.exists()

    existing_store = JsonAlphaCaseStore(tmp_path)
    existing_store.save(record)
    with pytest.raises(ValueError, match="alpha-case update must record one outcome"):
        existing_store.update(record)


def test_alpha_case_update_rejects_criteria_source_provenance_drift(
    tmp_path: Path,
) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    store.save(record)
    replacement = record.model_copy(
        update={
            "criteria_source_provenance": criteria_source_provenance(
                source_revision="issue-6@changed"
            )
        }
    )

    with pytest.raises(
        ValueError,
        match="alpha-case update must preserve criteria source provenance",
    ):
        store.update(replacement)


def test_alpha_case_update_rejects_completed_outcome_overwrite(tmp_path: Path) -> None:
    from scopeproof_core.alpha.models import AlphaOutcome
    from scopeproof_core.alpha.service import record_alpha_outcome

    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    store.save(record)
    completed = record_alpha_outcome(
        record,
        review_state=matching_review_state(),
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
    )
    store.update(completed)
    overwritten = completed.model_copy(
        update={
            "review_id": "review-8",
            "reviewed_head_sha": "b" * 40,
            "outcome": AlphaOutcome.SHOWED_ONLY_KNOWN_INFORMATION,
        }
    )

    with pytest.raises(ValueError, match="alpha-case outcome is immutable once recorded"):
        store.update(overwritten)


def test_alpha_case_update_validates_through_claimed_directory_after_root_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scopeproof_core.alpha.models import AlphaOutcome
    from scopeproof_core.alpha.service import record_alpha_outcome

    root = tmp_path / "cases"
    moved = tmp_path / "moved"
    record = alpha_case()
    first = record_alpha_outcome(
        record,
        review_state=matching_review_state(),
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
    )
    second = first.model_copy(update={"outcome": AlphaOutcome.SHOWED_ONLY_KNOWN_INFORMATION})
    store = JsonAlphaCaseStore(root)
    store.save(first)
    real_claim = alpha_storage_module.exclusive_path_claim

    @contextmanager
    def swapping_claim(target: Path):
        with real_claim(target) as claim:
            root.rename(moved)
            root.mkdir()
            (root / target.name).write_text(
                record.model_dump_json(indent=2) + "\n", encoding="utf-8"
            )
            yield claim

    monkeypatch.setattr(alpha_storage_module, "exclusive_path_claim", swapping_claim)

    with pytest.raises(ValueError, match="outcome is immutable"):
        store.update(second)

    assert JsonAlphaCaseStore(moved).load(record.case_id).outcome is AlphaOutcome.FOUND_USEFUL_GAP
    assert JsonAlphaCaseStore(root).load(record.case_id).outcome is None


def test_concurrent_process_outcome_updates_commit_exactly_once(tmp_path: Path) -> None:
    from scopeproof_core.alpha.models import AlphaOutcome
    from scopeproof_core.alpha.service import record_alpha_outcome

    record = alpha_case()
    JsonAlphaCaseStore(tmp_path).save(record)
    first = record_alpha_outcome(
        record,
        review_state=matching_review_state(),
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
    )
    second = first.model_copy(
        update={"outcome": AlphaOutcome.SHOWED_ONLY_KNOWN_INFORMATION}
    )
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    outcomes = context.Queue()
    processes = [
        context.Process(
            target=_run_alpha_mutation,
            args=(str(tmp_path), item.model_dump(mode="json"), "update", barrier, outcomes),
        )
        for item in (first, second)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0

    assert sorted(outcomes.get(timeout=2) for _ in range(2)) == ["ValueError", "success"]
    stored = JsonAlphaCaseStore(tmp_path).load(record.case_id)
    assert stored in (first, second)
    assert sorted(path.name for path in tmp_path.iterdir()) == [f"{record.case_id}.json"]


def test_interrupted_outcome_update_preserves_prior_record_and_cleans_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scopeproof_core.alpha.models import AlphaOutcome
    from scopeproof_core.alpha.service import record_alpha_outcome

    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    path = store.save(record)
    before = path.read_bytes()
    completed = record_alpha_outcome(
        record,
        review_state=matching_review_state(),
        outcome=AlphaOutcome.FOUND_USEFUL_GAP,
    )

    def interrupt_replace(*_args, **_kwargs):
        raise OSError("simulated alpha update interruption")

    monkeypatch.setattr(
        "scopeproof_core.alpha.storage.atomic_replace_text",
        interrupt_replace,
    )

    with pytest.raises(OSError, match="alpha update interruption"):
        store.update(completed)

    assert path.read_bytes() == before
    assert sorted(item.name for item in tmp_path.iterdir()) == [path.name]


def test_alpha_store_reads_legacy_record_without_inventing_provenance(
    tmp_path: Path,
) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    path = store.save(record)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("criteria_source_provenance")
    payload.pop("repository_visibility")
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(record.case_id)

    assert loaded.criteria_source_provenance is None
    assert loaded.repository_visibility is RepositoryVisibility.UNVERIFIED


@pytest.mark.parametrize("case_id", ["../escape", "alpha-not-a-uuid", "/tmp/case"])
def test_alpha_store_rejects_unsafe_case_ids(tmp_path: Path, case_id: str) -> None:
    with pytest.raises(ValueError):
        JsonAlphaCaseStore(tmp_path).load(case_id)


def test_alpha_store_rejects_symlink_root(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "cases"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(UnsafeAlphaCaseStore):
        JsonAlphaCaseStore(link).list_case_ids()


def test_alpha_store_rejects_symlinked_existing_ancestor(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    store = JsonAlphaCaseStore(linked / "cases")

    with pytest.raises(UnsafeAlphaCaseStore, match="ancestor"):
        store.save(alpha_case())

    assert list(outside.iterdir()) == []


def test_alpha_store_revalidates_loaded_payload(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    path = store.save(record)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["no_confidential_information"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        store.load(record.case_id)


def test_alpha_store_rejects_malformed_json(tmp_path: Path) -> None:
    record = alpha_case()
    store = JsonAlphaCaseStore(tmp_path)
    path = store.save(record)
    path.write_text("{", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        store.load(record.case_id)


def test_alpha_store_rejects_symlink_record_target(tmp_path: Path) -> None:
    record = alpha_case()
    outside = tmp_path / "outside.json"
    outside.write_text(record.model_dump_json(), encoding="utf-8")
    directory = tmp_path / "cases"
    directory.mkdir()
    (directory / f"{record.case_id}.json").symlink_to(outside)

    with pytest.raises(UnsafeAlphaCaseStore, match="regular local file"):
        JsonAlphaCaseStore(directory).load(record.case_id)


def test_alpha_store_rejects_valid_record_under_different_id(tmp_path: Path) -> None:
    requested = alpha_case()
    replacement = initialize_alpha_case(
        public_pr_url="https://github.com/acme/repo/pull/8",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        participant_role=ParticipantRole.ENGINEERING,
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
        confirmed_criterion_snapshot=[Criterion(criterion_id="AC-01", text="Export CSV")],
        criteria_source_provenance=criteria_source_provenance(),
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
    )
    store = JsonAlphaCaseStore(tmp_path)
    path = store.save(requested)
    path.write_text(replacement.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match requested ID"):
        store.load(requested.case_id)
