import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from pydantic import ValidationError

from scopeproof_core.alpha.rehearsal import initialize_alpha_rehearsal
from scopeproof_core.alpha.rehearsal_storage import (
    JsonAlphaRehearsalStore,
    UnsafeAlphaRehearsalStore,
    default_alpha_rehearsal_directory,
)
from scopeproof_core.alpha.storage import JsonAlphaCaseStore


def alpha_rehearsal(*, pull_number: int = 7):
    return initialize_alpha_rehearsal(
        public_pr_url=f"https://github.com/acme/repo/pull/{pull_number}",
        requirements_source_url="https://github.com/acme/repo/issues/6",
        criteria_authority="Repository owner confirmation for this rehearsal",
        source_owner_confirmed=True,
        no_confidential_information=True,
        confirmed_criteria=["Export CSV"],
    )


def test_default_rehearsal_directory_is_separate_from_genuine_cases() -> None:
    assert default_alpha_rehearsal_directory() == (
        Path.home() / ".scopeproof" / "alpha-rehearsals"
    )


def test_rehearsal_round_trips_as_validated_json(tmp_path: Path) -> None:
    record = alpha_rehearsal()
    store = JsonAlphaRehearsalStore(tmp_path)

    path = store.save(record)

    assert store.load(record.rehearsal_id) == record
    assert path.name == f"{record.rehearsal_id}.json"
    assert store.list_rehearsal_ids() == [record.rehearsal_id]
    assert not hasattr(store, "update")


def test_rehearsal_listing_is_deterministically_sorted(tmp_path: Path) -> None:
    records = [alpha_rehearsal(pull_number=number) for number in (9, 7, 8)]
    store = JsonAlphaRehearsalStore(tmp_path)
    for record in records:
        store.save(record)

    assert store.list_rehearsal_ids() == sorted(
        record.rehearsal_id for record in records
    )


def test_rehearsal_save_refuses_silent_overwrite(tmp_path: Path) -> None:
    record = alpha_rehearsal()
    store = JsonAlphaRehearsalStore(tmp_path)
    store.save(record)

    with pytest.raises(FileExistsError):
        store.save(record)


@pytest.mark.parametrize(
    "rehearsal_id",
    [
        "../escape",
        "rehearsal-not-a-digest",
        "/tmp/rehearsal",
        "alpha-" + "a" * 32,
        "rehearsal-" + "A" * 32,
    ],
)
def test_rehearsal_store_rejects_unsafe_and_genuine_case_ids(
    tmp_path: Path, rehearsal_id: str
) -> None:
    with pytest.raises(ValueError):
        JsonAlphaRehearsalStore(tmp_path).load(rehearsal_id)


def test_rehearsal_store_rejects_symlink_root(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "rehearsals"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(UnsafeAlphaRehearsalStore):
        JsonAlphaRehearsalStore(link).list_rehearsal_ids()


def test_rehearsal_store_rejects_symlinked_existing_ancestor(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked-parent"
    link.symlink_to(target, target_is_directory=True)
    store = JsonAlphaRehearsalStore(link / "nested" / "rehearsals")

    with pytest.raises(UnsafeAlphaRehearsalStore, match="ancestor"):
        store.list_rehearsal_ids()
    with pytest.raises(UnsafeAlphaRehearsalStore, match="ancestor"):
        store.save(alpha_rehearsal())


def test_rehearsal_store_rejects_symlink_file(tmp_path: Path) -> None:
    record = alpha_rehearsal()
    target = tmp_path / "outside.json"
    target.write_text(record.model_dump_json(), encoding="utf-8")
    directory = tmp_path / "rehearsals"
    directory.mkdir()
    link = directory / f"{record.rehearsal_id}.json"
    link.symlink_to(target)
    store = JsonAlphaRehearsalStore(directory)

    with pytest.raises(FileNotFoundError):
        store.load(record.rehearsal_id)
    assert store.list_rehearsal_ids() == []


def test_rehearsal_store_revalidates_loaded_payload(tmp_path: Path) -> None:
    record = alpha_rehearsal()
    store = JsonAlphaRehearsalStore(tmp_path)
    path = store.save(record)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["eligible_for_stage_1"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        store.load(record.rehearsal_id)


def test_concurrent_rehearsal_saves_create_exactly_once(tmp_path: Path) -> None:
    start_barrier = Barrier(2)
    write_barrier = Barrier(2)

    class SynchronizedStore(JsonAlphaRehearsalStore):
        def _write(self, target, record):
            write_barrier.wait()
            return super()._write(target, record)

    record = alpha_rehearsal()
    store = SynchronizedStore(tmp_path)

    def save_once() -> str:
        start_barrier.wait()
        try:
            store.save(record)
        except FileExistsError:
            return "already_exists"
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: save_once(), range(2)))

    assert sorted(results) == ["already_exists", "created"]
    assert store.load(record.rehearsal_id) == record


def test_rehearsal_store_rejects_valid_record_under_different_id(
    tmp_path: Path,
) -> None:
    requested = alpha_rehearsal(pull_number=7)
    replacement = alpha_rehearsal(pull_number=8)
    store = JsonAlphaRehearsalStore(tmp_path)
    path = store.save(requested)
    path.write_text(replacement.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match requested ID"):
        store.load(requested.rehearsal_id)


def test_rehearsal_listing_never_enumerates_genuine_alpha_case_files(
    tmp_path: Path,
) -> None:
    genuine_id = "alpha-" + "a" * 32
    (tmp_path / f"{genuine_id}.json").write_text("{}", encoding="utf-8")

    assert JsonAlphaRehearsalStore(tmp_path).list_rehearsal_ids() == []


def test_genuine_alpha_store_rejects_rehearsal_ids(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        JsonAlphaCaseStore(tmp_path).load(alpha_rehearsal().rehearsal_id)
