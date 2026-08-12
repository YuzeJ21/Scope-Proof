import os
from pathlib import Path

import pytest

from scopeproof_core.storage.atomic_files import (
    UnsafeAtomicPath,
    atomic_create_text,
    atomic_replace_text,
    exclusive_path_claim,
    read_text_no_follow,
)


def test_atomic_create_never_overwrites_existing_target(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("owner bytes\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        atomic_create_text(target, "new bytes\n")

    assert target.read_bytes() == b"owner bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["report.json"]


def test_failed_exclusive_publish_cleans_private_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.json"

    def fail_link(*_args, **_kwargs):
        raise OSError("simulated publication interruption")

    monkeypatch.setattr(os, "link", fail_link)

    with pytest.raises(OSError, match="publication interruption"):
        atomic_create_text(target, "validated bytes\n")

    assert list(tmp_path.iterdir()) == []


def test_directory_sync_unavailability_after_create_does_not_report_false_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    original_fsync = os.fsync
    calls = 0

    def fail_directory_sync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("directory sync unsupported")
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_directory_sync)

    assert atomic_create_text(target, "committed bytes\n") == target
    assert target.read_bytes() == b"committed bytes\n"


def test_claimed_replace_preserves_old_bytes_and_cleans_artifacts_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")

    def fail_replace(*_args, **_kwargs):
        raise OSError("simulated replacement interruption")

    monkeypatch.setattr(os, "replace", fail_replace)

    with (
        pytest.raises(OSError, match="replacement interruption"),
        exclusive_path_claim(target),
    ):
        atomic_replace_text(target, "new valid bytes\n")

    assert target.read_bytes() == b"old valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_directory_sync_unavailability_after_replace_does_not_report_false_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_fsync = os.fsync
    calls = 0

    def fail_directory_sync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("directory sync unsupported")
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_directory_sync)

    with exclusive_path_claim(target):
        assert atomic_replace_text(target, "new valid bytes\n") == target

    assert target.read_bytes() == b"new valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_portable_path_operations_reject_symlinked_ancestor(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    target = linked / "nested" / "record.json"

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|reparse"):
        atomic_create_text(target, "must not escape\n")

    assert list(outside.iterdir()) == []


def test_read_rejects_symlink_target(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("outside\n", encoding="utf-8")
    linked = tmp_path / "record.json"
    linked.symlink_to(outside)

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|reparse"):
        read_text_no_follow(linked)
