import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from pydantic import ValidationError

import scopeproof_core.alpha.rehearsal_storage as rehearsal_storage_module
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


def test_portable_rehearsal_backend_round_trips_without_posix_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rehearsal_storage_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    record = alpha_rehearsal()
    store = JsonAlphaRehearsalStore(tmp_path / "portable" / "rehearsals")

    path = store.save(record)

    assert path.read_text(encoding="utf-8").endswith("\n")
    assert store.load(record.rehearsal_id) == record
    assert store.list_rehearsal_ids() == [record.rehearsal_id]
    with pytest.raises(FileExistsError):
        store.save(record)


def test_rehearsal_backend_requires_descriptor_relative_rename() -> None:
    script = """
import os
os.supports_dir_fd.discard(os.rename)
import scopeproof_core.alpha.rehearsal_storage as storage
assert storage._DESCRIPTOR_BACKEND_SUPPORTED is False
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(
    not rehearsal_storage_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative rehearsal backend is unavailable",
)
def test_descriptor_rehearsal_create_cleans_publication_when_link_fails_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = alpha_rehearsal()
    original_link = os.link

    def publish_then_fail(source, destination, *args, **kwargs):
        original_link(source, destination, *args, **kwargs)
        raise OSError("simulated post-publication interruption")

    monkeypatch.setattr(os, "link", publish_then_fail)

    with pytest.raises(OSError, match="post-publication interruption"):
        JsonAlphaRehearsalStore(tmp_path).save(record)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(
    not rehearsal_storage_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative rehearsal backend is unavailable",
)
def test_descriptor_rehearsal_metadata_failure_cleans_owned_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_fstat = os.fstat

    def fail_regular_descriptor_metadata(descriptor: int):
        metadata = original_fstat(descriptor)
        if rehearsal_storage_module.stat.S_ISREG(metadata.st_mode):
            raise OSError("simulated rehearsal metadata failure")
        return metadata

    monkeypatch.setattr(os, "fstat", fail_regular_descriptor_metadata)

    with pytest.raises(OSError, match="rehearsal metadata failure"):
        JsonAlphaRehearsalStore(tmp_path).save(alpha_rehearsal())

    assert list(tmp_path.iterdir()) == []


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


def test_committed_rehearsal_does_not_report_failure_when_cleanup_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = alpha_rehearsal()
    original_rename = os.rename

    def deny_temporary_cleanup(source, destination, *args, **kwargs):
        if str(source).endswith(".tmp"):
            raise PermissionError("simulated cleanup denial")
        return original_rename(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "rename", deny_temporary_cleanup)

    path = JsonAlphaRehearsalStore(tmp_path).save(record)

    assert JsonAlphaRehearsalStore(tmp_path).load(record.rehearsal_id) == record
    assert path.exists()
    assert any(item.suffix == ".tmp" for item in tmp_path.iterdir())


@pytest.mark.skipif(
    not rehearsal_storage_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative rehearsal backend is unavailable",
)
def test_committed_rehearsal_never_deletes_foreign_temporary_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = alpha_rehearsal()
    original_link = os.link
    foreign_name = ""

    def replace_temporary_after_publication(source, destination, *args, **kwargs):
        nonlocal foreign_name
        if not str(source).endswith(".tmp"):
            return original_link(source, destination, *args, **kwargs)
        result = original_link(source, destination, *args, **kwargs)
        directory_fd = kwargs["src_dir_fd"]
        os.unlink(source, dir_fd=directory_fd)
        descriptor = os.open(
            source,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=directory_fd,
        )
        try:
            os.write(descriptor, b"foreign rehearsal temporary\n")
        finally:
            os.close(descriptor)
        foreign_name = source
        return result

    monkeypatch.setattr(os, "link", replace_temporary_after_publication)

    path = JsonAlphaRehearsalStore(tmp_path).save(record)

    assert JsonAlphaRehearsalStore(tmp_path).load(record.rehearsal_id) == record
    assert path.exists()
    assert (tmp_path / foreign_name).read_bytes() == b"foreign rehearsal temporary\n"


@pytest.mark.skipif(
    not rehearsal_storage_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative rehearsal backend is unavailable",
)
def test_rehearsal_failure_after_publication_removes_owned_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = alpha_rehearsal()
    target_name = f"{record.rehearsal_id}.json"
    original_stat = os.stat

    def fail_target_validation(path, *args, **kwargs):
        if path == target_name and kwargs.get("dir_fd") is not None:
            raise OSError("simulated rehearsal publication validation failure")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", fail_target_validation)

    with pytest.raises(OSError, match="publication validation failure"):
        JsonAlphaRehearsalStore(tmp_path).save(record)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(
    not rehearsal_storage_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative rehearsal backend is unavailable",
)
def test_rehearsal_failure_tolerates_publication_removed_before_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = alpha_rehearsal()
    target_name = f"{record.rehearsal_id}.json"
    original_stat = os.stat
    original_cleanup = rehearsal_storage_module._quarantine_and_remove_at

    def fail_target_validation(path, *args, **kwargs):
        if path == target_name and kwargs.get("dir_fd") is not None:
            raise OSError("simulated rehearsal publication validation failure")
        return original_stat(path, *args, **kwargs)

    def remove_publication_before_cleanup(directory_fd, name, *args, **kwargs):
        if name == target_name:
            os.unlink(name, dir_fd=directory_fd)
            raise FileNotFoundError(name)
        return original_cleanup(directory_fd, name, *args, **kwargs)

    monkeypatch.setattr(os, "stat", fail_target_validation)
    monkeypatch.setattr(
        rehearsal_storage_module,
        "_quarantine_and_remove_at",
        remove_publication_before_cleanup,
    )

    with pytest.raises(OSError, match="publication validation failure"):
        JsonAlphaRehearsalStore(tmp_path).save(record)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(
    not rehearsal_storage_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative rehearsal backend is unavailable",
)
def test_rehearsal_failure_surfaces_publication_cleanup_denial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = alpha_rehearsal()
    target_name = f"{record.rehearsal_id}.json"
    original_stat = os.stat
    original_cleanup = rehearsal_storage_module._quarantine_and_remove_at

    def fail_target_validation(path, *args, **kwargs):
        if path == target_name and kwargs.get("dir_fd") is not None:
            raise OSError("simulated rehearsal publication validation failure")
        return original_stat(path, *args, **kwargs)

    def deny_publication_cleanup(directory_fd, name, *args, **kwargs):
        if name == target_name:
            raise PermissionError("simulated rehearsal cleanup denial")
        return original_cleanup(directory_fd, name, *args, **kwargs)

    monkeypatch.setattr(os, "stat", fail_target_validation)
    monkeypatch.setattr(
        rehearsal_storage_module,
        "_quarantine_and_remove_at",
        deny_publication_cleanup,
    )

    with pytest.raises(PermissionError, match="cleanup denial"):
        JsonAlphaRehearsalStore(tmp_path).save(record)

    assert sorted(path.name for path in tmp_path.iterdir()) == [target_name]


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
        def _write(self, directory_fd, target_name, record):
            write_barrier.wait()
            return super()._write(directory_fd, target_name, record)

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


def test_rehearsal_save_stays_anchored_when_ancestor_is_swapped(
    tmp_path: Path,
) -> None:
    root = tmp_path / "save-root"
    directory = root / "rehearsals"
    directory.mkdir(parents=True)
    moved_root = tmp_path / "save-root-original"
    outside = tmp_path / "save-outside"
    outside.mkdir()

    class SwappingWriteStore(JsonAlphaRehearsalStore):
        def _write(self, directory_fd, target_name, record):
            root.rename(moved_root)
            root.symlink_to(outside, target_is_directory=True)
            return super()._write(directory_fd, target_name, record)

    record = alpha_rehearsal()
    store = SwappingWriteStore(directory)

    returned_path = store.save(record)

    anchored_directory = moved_root / "rehearsals"
    assert returned_path == directory / f"{record.rehearsal_id}.json"
    assert JsonAlphaRehearsalStore(anchored_directory).load(record.rehearsal_id) == record
    assert list(outside.rglob("*.json")) == []


def test_rehearsal_load_stays_anchored_when_ancestor_is_swapped(
    tmp_path: Path,
) -> None:
    root = tmp_path / "load-root"
    directory = root / "rehearsals"
    directory.mkdir(parents=True)
    moved_root = tmp_path / "load-root-original"
    outside = tmp_path / "load-outside"
    outside_directory = outside / "rehearsals"
    outside_directory.mkdir(parents=True)
    record = alpha_rehearsal()
    JsonAlphaRehearsalStore(directory).save(record)
    outside_path = outside_directory / f"{record.rehearsal_id}.json"
    outside_path.write_text("outside target must not be read", encoding="utf-8")

    class SwappingReadStore(JsonAlphaRehearsalStore):
        def _read(self, directory_fd, target_name):
            root.rename(moved_root)
            root.symlink_to(outside, target_is_directory=True)
            return super()._read(directory_fd, target_name)

    loaded = SwappingReadStore(directory).load(record.rehearsal_id)

    assert loaded == record
    assert root.is_symlink()
    assert (moved_root / "rehearsals").is_dir()
    assert outside_path.read_text(encoding="utf-8") == "outside target must not be read"


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
