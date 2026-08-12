import errno
import os
from hashlib import sha256
from pathlib import Path

import pytest

import scopeproof_core.storage.atomic_files as atomic_files_module
from scopeproof_core.storage.atomic_files import (
    UnsafeAtomicPath,
    atomic_create_text,
    atomic_create_text_with_receipt,
    atomic_replace_text,
    ensure_safe_directory,
    exclusive_path_claim,
    list_regular_files,
    read_text_no_follow,
    rollback_created_file,
)


def test_atomic_create_never_overwrites_existing_target(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("owner bytes\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        atomic_create_text(target, "new bytes\n")

    assert target.read_bytes() == b"owner bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["report.json"]


def test_atomic_create_builds_missing_safe_directories(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "records" / "record.json"

    assert atomic_create_text(target, "validated\n") == target
    assert target.read_text(encoding="utf-8") == "validated\n"


def test_safe_directory_rejects_non_directory_component(tmp_path: Path) -> None:
    component = tmp_path / "not-a-directory"
    component.write_text("file\n", encoding="utf-8")

    with pytest.raises(UnsafeAtomicPath, match="must be a directory"):
        ensure_safe_directory(component / "nested", create=True)


def test_regular_file_read_rejects_directory_target(tmp_path: Path) -> None:
    target = tmp_path / "record.json"
    target.mkdir()

    with pytest.raises(UnsafeAtomicPath, match="regular file"):
        read_text_no_follow(target)


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_descriptor_read_rejects_fifo_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    os.mkfifo(target)
    original_open = os.open

    def reject_fifo_open(path, flags, *args, **kwargs):
        if path == target.name and kwargs.get("dir_fd") is not None:
            raise AssertionError("FIFO must be rejected before a blocking open")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", reject_fifo_open)

    with pytest.raises(UnsafeAtomicPath, match="regular file"):
        read_text_no_follow(target)


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_descriptor_read_rejects_fifo_swapped_between_stat_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("validated\n", encoding="utf-8")
    original_open = os.open
    swapped = False

    def swap_to_fifo(path, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and path == target.name and kwargs.get("dir_fd") is not None:
            swapped = True
            target.unlink()
            os.mkfifo(target)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", swap_to_fifo)

    with pytest.raises(UnsafeAtomicPath, match="regular file"):
        read_text_no_follow(target)


def test_portable_read_rejects_fifo_swapped_between_stat_and_open_without_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable")
    target = tmp_path / "record.json"
    target.write_text("validated\n", encoding="utf-8")
    original_open = os.open
    swapped = False

    def swap_to_fifo(path, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and Path(path) == target and not flags & os.O_CREAT:
            swapped = True
            target.unlink()
            os.mkfifo(target)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "open", swap_to_fifo)

    with pytest.raises(UnsafeAtomicPath, match="regular file"):
        read_text_no_follow(target)


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_descriptor_read_rejects_regular_file_swap_between_stat_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("validated\n", encoding="utf-8")
    original_open = os.open
    swapped = False

    def swap_regular_file(path, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and path == target.name and kwargs.get("dir_fd") is not None:
            swapped = True
            target.unlink()
            target.write_text("different bytes\n", encoding="utf-8")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", swap_regular_file)

    with pytest.raises(UnsafeAtomicPath, match="changed while it was being opened"):
        read_text_no_follow(target)


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_descriptor_read_translates_no_follow_loop_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("validated\n", encoding="utf-8")
    original_open = os.open

    def reject_target(path, flags, *args, **kwargs):
        if path == target.name and kwargs.get("dir_fd") is not None:
            raise OSError(errno.ELOOP, "symbolic-link loop")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", reject_target)

    with pytest.raises(UnsafeAtomicPath, match="symbolic link or reparse"):
        read_text_no_follow(target)


def test_portable_read_rejects_regular_file_swap_between_stat_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("validated\n", encoding="utf-8")
    original_open = os.open
    swapped = False

    def swap_regular_file(path, flags, *args, **kwargs):
        nonlocal swapped
        if not swapped and Path(path) == target and not flags & os.O_CREAT:
            swapped = True
            target.unlink()
            target.write_text("different bytes\n", encoding="utf-8")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "open", swap_regular_file)

    with pytest.raises(UnsafeAtomicPath, match="changed while it was being opened"):
        read_text_no_follow(target)


def test_missing_directory_lists_no_records(tmp_path: Path) -> None:
    assert list_regular_files(tmp_path / "absent") == []


def test_portable_missing_directory_lists_no_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    assert list_regular_files(tmp_path / "absent") == []


def test_portable_read_and_listing_return_only_regular_direct_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    record = tmp_path / "record.json"
    record.write_text("validated\n", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "nested.json").write_text("not direct\n", encoding="utf-8")
    (tmp_path / "linked.json").symlink_to(record)

    assert read_text_no_follow(record) == "validated\n"
    assert list_regular_files(tmp_path) == [record]


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


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows prevents unlinking an open temporary file",
)
def test_atomic_create_rejects_private_temporary_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.json"
    original_link = os.link

    def swap_source_before_link(source, destination, **kwargs):
        directory_fd = kwargs.get("src_dir_fd")
        if directory_fd is None:
            Path(source).unlink()
            Path(source).write_text("attacker bytes\n", encoding="utf-8")
        else:
            os.unlink(source, dir_fd=directory_fd)
            descriptor = os.open(
                source,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=directory_fd,
            )
            try:
                os.write(descriptor, b"attacker bytes\n")
            finally:
                os.close(descriptor)
        return original_link(source, destination, **kwargs)

    monkeypatch.setattr(os, "link", swap_source_before_link)

    with pytest.raises(UnsafeAtomicPath, match="temporary file changed"):
        atomic_create_text(target, "validated bytes\n")

    assert target.read_bytes() == b"attacker bytes\n"
    assert any(path.suffix == ".tmp" for path in tmp_path.iterdir())


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_committed_create_never_deletes_foreign_temporary_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.json"
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
            os.write(descriptor, b"foreign temporary\n")
        finally:
            os.close(descriptor)
        foreign_name = source
        return result

    monkeypatch.setattr(os, "link", replace_temporary_after_publication)

    assert atomic_create_text(target, "validated report\n") == target
    assert target.read_bytes() == b"validated report\n"
    assert (tmp_path / foreign_name).read_bytes() == b"foreign temporary\n"


def test_atomic_create_retries_private_temporary_name_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bounded = sha256(b"record").hexdigest()[:16]
    (tmp_path / f".{bounded}-collision.tmp").write_text("occupied", encoding="utf-8")
    tokens = iter(("collision", "available", "cleanup"))
    monkeypatch.setattr(atomic_files_module.secrets, "token_hex", lambda _size: next(tokens))

    target = atomic_create_text(tmp_path / "record.json", "validated\n")

    assert target.read_text(encoding="utf-8") == "validated\n"


def test_atomic_create_bounds_temporary_name_for_long_valid_target(tmp_path: Path) -> None:
    target = tmp_path / ("a" * 220 + ".json")

    assert atomic_create_text(target, "validated\n") == target
    assert target.read_text(encoding="utf-8") == "validated\n"


def test_zero_byte_progress_fails_and_cleans_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(os, "write", lambda *_args, **_kwargs: 0)

    with pytest.raises(OSError, match="complete local record"):
        atomic_create_text(tmp_path / "record.json", "validated\n")

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("unsupported_error", [TypeError, NotImplementedError])
def test_atomic_create_uses_legacy_link_signature_when_needed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsupported_error: type[Exception],
) -> None:
    original_link = os.link
    calls = 0

    def legacy_link(source, target, **kwargs):
        nonlocal calls
        calls += 1
        if kwargs:
            raise unsupported_error("follow_symlinks unsupported")
        return original_link(source, target)

    monkeypatch.setattr(os, "link", legacy_link)
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    target = atomic_create_text(tmp_path / "record.json", "validated\n")

    assert target.read_text(encoding="utf-8") == "validated\n"
    assert calls == 2


def test_portable_create_receipt_supports_identity_bound_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.md"
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    receipt = atomic_create_text_with_receipt(target, "validated report\n")

    assert receipt.descriptor_backend is False
    assert target.read_bytes() == b"validated report\n"
    rollback_created_file(receipt)
    assert list(tmp_path.iterdir()) == []


def test_portable_create_refuses_existing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.md"
    target.write_text("owner bytes\n", encoding="utf-8")
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    with pytest.raises(FileExistsError, match="already exists"):
        atomic_create_text(target, "new bytes\n")

    assert target.read_bytes() == b"owner bytes\n"


def test_portable_receipt_rollback_preserves_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.md"
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    receipt = atomic_create_text_with_receipt(target, "validated report\n")
    target.unlink()
    target.write_text("owner replacement\n", encoding="utf-8")

    with pytest.raises(UnsafeAtomicPath, match="changed before rollback"):
        rollback_created_file(receipt)

    assert target.read_bytes() == b"owner replacement\n"


def test_receipt_rollback_rejects_relative_path(tmp_path: Path) -> None:
    receipt = atomic_files_module.CreatedFileReceipt(
        path=Path("relative.json"),
        identity=(0, 0),
        descriptor_backend=False,
    )

    with pytest.raises(UnsafeAtomicPath, match="path is not absolute"):
        rollback_created_file(receipt)


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


def test_committed_create_does_not_report_failure_when_temporary_cleanup_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    original_rename = os.rename

    def deny_temporary_cleanup(source, destination, *args, **kwargs):
        if str(source).endswith(".tmp"):
            raise PermissionError("simulated cleanup denial")
        return original_rename(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "rename", deny_temporary_cleanup)

    assert atomic_create_text(target, "committed bytes\n") == target
    assert target.read_bytes() == b"committed bytes\n"
    assert any(path.suffix == ".tmp" for path in tmp_path.iterdir())


def test_created_file_rollback_refuses_to_delete_replacement(
    tmp_path: Path,
) -> None:
    target = tmp_path / "report.md"
    receipt = atomic_create_text_with_receipt(target, "generated bytes\n")
    target.unlink()
    target.write_text("owner replacement\n", encoding="utf-8")

    with pytest.raises(UnsafeAtomicPath, match="changed before rollback"):
        rollback_created_file(receipt)

    assert target.read_text(encoding="utf-8") == "owner replacement\n"


def test_created_file_rollback_preserves_replacement_racing_the_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "report.md"
    receipt = atomic_create_text_with_receipt(target, "generated bytes\n")
    original_rename = os.rename
    swapped = False

    def swap_before_quarantine(source, destination, *args, **kwargs):
        nonlocal swapped
        source_fd = kwargs.get("src_dir_fd")
        if not swapped and Path(source).name == target.name:
            swapped = True
            if source_fd is None:
                Path(source).unlink()
                Path(source).write_text("owner replacement\n", encoding="utf-8")
            else:
                os.unlink(source, dir_fd=source_fd)
                descriptor = os.open(
                    source,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=source_fd,
                )
                try:
                    os.write(descriptor, b"owner replacement\n")
                finally:
                    os.close(descriptor)
        return original_rename(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "rename", swap_before_quarantine)

    with pytest.raises(UnsafeAtomicPath, match="changed before rollback"):
        rollback_created_file(receipt)

    assert target.read_text(encoding="utf-8") == "owner replacement\n"


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_descriptor_replace_never_overwrites_foreign_file_published_by_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_rename = os.rename

    def swap_temporary(source, destination, *args, **kwargs):
        source_fd = kwargs.get("src_dir_fd")
        if Path(source).suffix == ".tmp" and source_fd is not None:
            os.unlink(source, dir_fd=source_fd)
            descriptor = os.open(
                source,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=source_fd,
            )
            try:
                os.write(descriptor, b"attacker bytes\n")
            finally:
                os.close(descriptor)
        return original_rename(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "rename", swap_temporary)

    with (
        pytest.raises(UnsafeAtomicPath, match="replacement changed before rollback"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"attacker bytes\n"
    assert any(path.suffix == ".rollback" for path in tmp_path.iterdir())


def test_committed_replace_ignores_claim_cleanup_denial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_unlink = os.unlink

    def deny_claim_cleanup(path, *args, **kwargs):
        if str(path).endswith(".claim"):
            raise PermissionError("simulated claim cleanup denial")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", deny_claim_cleanup)

    with exclusive_path_claim(target) as claim:
        assert atomic_replace_text(target, "new valid bytes\n", claim=claim) == target

    assert target.read_bytes() == b"new valid bytes\n"


def test_portable_create_removes_published_target_after_parent_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "report.md"
    original_link = os.link

    def escape_link(source, destination, *args, **kwargs):
        safe.rename(moved)
        safe.symlink_to(outside, target_is_directory=True)
        original_link(moved / Path(source).name, outside / Path(source).name)
        return original_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "link", escape_link)

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"):
        atomic_create_text(target, "validated report\n")

    assert not (outside / target.name).exists()


def test_directory_sync_is_optional_when_flags_or_open_are_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delattr(os, "O_DIRECTORY", raising=False)
    atomic_files_module._fsync_directory(tmp_path)

    monkeypatch.undo()
    monkeypatch.setattr(os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    atomic_files_module._fsync_directory(tmp_path)


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_claimed_replace_preserves_old_bytes_and_cleans_artifacts_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")

    original_rename = os.rename

    def fail_replace(source, destination, *args, **kwargs):
        if str(source).endswith(".tmp") and Path(destination).name == target.name:
            raise OSError("simulated replacement interruption")
        return original_rename(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, "rename", fail_replace)

    with (
        pytest.raises(OSError, match="replacement interruption"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"old valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_portable_claimed_replace_preserves_old_bytes_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")

    def fail_replace(*_args, **_kwargs):
        raise OSError("simulated portable replacement interruption")

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "replace", fail_replace)

    with (
        pytest.raises(OSError, match="portable replacement interruption"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"old valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_portable_claimed_replace_commits_and_cleans_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    with exclusive_path_claim(target) as claim:
        assert atomic_replace_text(target, "new valid bytes\n", claim=claim) == target

    assert target.read_bytes() == b"new valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_claims_are_bound_to_their_exact_read_and_replace_target(tmp_path: Path) -> None:
    target = tmp_path / "record.json"
    neighbor = tmp_path / "neighbor.json"
    target.write_text("valid\n", encoding="utf-8")
    neighbor.write_text("neighbor\n", encoding="utf-8")

    with exclusive_path_claim(target) as claim:
        with pytest.raises(UnsafeAtomicPath, match="does not match read target"):
            read_text_no_follow(neighbor, claim=claim)
        with pytest.raises(UnsafeAtomicPath, match="does not match replacement target"):
            atomic_replace_text(neighbor, "changed\n", claim=claim)

    assert neighbor.read_bytes() == b"neighbor\n"


def test_claim_rejects_record_replaced_after_acquisition(tmp_path: Path) -> None:
    target = tmp_path / "record.json"
    replacement = tmp_path / "replacement.json"
    target.write_text("validated unresolved\n", encoding="utf-8")
    replacement.write_text("foreign completed\n", encoding="utf-8")

    with exclusive_path_claim(target) as claim:
        os.replace(replacement, target)
        with pytest.raises(UnsafeAtomicPath, match="changed after mutation claim"):
            read_text_no_follow(target, claim=claim)
        with pytest.raises(UnsafeAtomicPath, match="changed after mutation claim"):
            atomic_replace_text(target, "stale outcome\n", claim=claim)

    assert target.read_bytes() == b"foreign completed\n"


def test_portable_claim_rejects_record_replaced_after_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    replacement = tmp_path / "replacement.json"
    target.write_text("validated unresolved\n", encoding="utf-8")
    replacement.write_text("foreign completed\n", encoding="utf-8")
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    with exclusive_path_claim(target) as claim:
        os.replace(replacement, target)
        with pytest.raises(UnsafeAtomicPath, match="changed after mutation claim"):
            read_text_no_follow(target, claim=claim)
        with pytest.raises(UnsafeAtomicPath, match="changed after mutation claim"):
            atomic_replace_text(target, "stale outcome\n", claim=claim)

    assert target.read_bytes() == b"foreign completed\n"


@pytest.mark.parametrize("portable", [False, True])
def test_replace_preserves_backup_when_record_changes_after_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, portable: bool
) -> None:
    if not portable and not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED:
        pytest.skip("descriptor-relative storage backend is unavailable")
    target = tmp_path / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_write = atomic_files_module._write_all

    def swap_after_backup(descriptor: int, payload: bytes) -> None:
        original_write(descriptor, payload)
        if payload == b"new valid bytes\n":
            target.unlink()
            target.write_text("foreign replacement\n", encoding="utf-8")

    if portable:
        monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(atomic_files_module, "_write_all", swap_after_backup)

    with (
        pytest.raises(UnsafeAtomicPath, match="changed before replacement"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"foreign replacement\n"
    assert any(path.suffix == ".rollback" for path in tmp_path.iterdir())


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_claimed_replace_cleans_backup_when_temporary_allocation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")

    def fail_temporary(*_args, **_kwargs):
        raise OSError("simulated temporary allocation failure")

    monkeypatch.setattr(atomic_files_module, "_open_private_temporary_at", fail_temporary)

    with (
        pytest.raises(OSError, match="temporary allocation failure"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"old valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_portable_claimed_replace_cleans_backup_when_temporary_allocation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")

    def fail_temporary(*_args, **_kwargs):
        raise OSError("simulated temporary allocation failure")

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(atomic_files_module, "_open_private_temporary", fail_temporary)

    with (
        pytest.raises(OSError, match="temporary allocation failure"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"old valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_directory_sync_unavailability_after_replace_does_not_report_false_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
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

    with exclusive_path_claim(target) as claim:
        assert atomic_replace_text(target, "new valid bytes\n", claim=claim) == target

    assert target.read_bytes() == b"new valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["alpha-record.json"]


def test_competing_mutation_claim_fails_without_removing_owner_claim(tmp_path: Path) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("valid\n", encoding="utf-8")

    with (
        exclusive_path_claim(target),
        pytest.raises(FileExistsError, match="another process"),
        exclusive_path_claim(target),
    ):
        raise AssertionError("competing claim must never be entered")


def test_portable_competing_mutation_claim_fails_without_removing_owner_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "alpha-record.json"
    target.write_text("valid\n", encoding="utf-8")
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    with (
        exclusive_path_claim(target),
        pytest.raises(FileExistsError, match="another process"),
        exclusive_path_claim(target),
    ):
        raise AssertionError("competing claim must never be entered")


@pytest.mark.parametrize("portable", [False, True])
def test_missing_record_claim_failure_cleans_claim_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, portable: bool
) -> None:
    if not portable and not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED:
        pytest.skip("descriptor-relative storage backend is unavailable")
    target = tmp_path / "missing.json"
    if portable:
        monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    with pytest.raises(FileNotFoundError), exclusive_path_claim(target):
        raise AssertionError("missing target claim must never be entered")

    assert list(tmp_path.iterdir()) == []


def test_claim_cleanup_never_deletes_recreated_foreign_claim(tmp_path: Path) -> None:
    target = tmp_path / "record.json"
    target.write_text("valid\n", encoding="utf-8")
    claim_name = f".{sha256(os.fsencode(target.name)).hexdigest()}.claim"
    owner = exclusive_path_claim(target)
    owner.__enter__()
    (tmp_path / claim_name).unlink()
    competitor = exclusive_path_claim(target)
    competitor.__enter__()

    with pytest.raises(UnsafeAtomicPath, match="claim changed"):
        owner.__exit__(None, None, None)

    assert (tmp_path / claim_name).exists()
    competitor.__exit__(None, None, None)


def test_portable_replace_never_restores_through_swapped_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_replace = os.replace
    calls = 0

    def swap_after_publication(source, destination, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            original_replace(source, destination, *args, **kwargs)
            safe.rename(moved)
            safe.symlink_to(outside, target_is_directory=True)
            (outside / Path(destination).name).write_text("foreign target\n", encoding="utf-8")
            return None
        return original_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "replace", swap_after_publication)

    with (
        pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert (outside / target.name).read_bytes() == b"foreign target\n"
    assert any(path.suffix == ".rollback" for path in moved.iterdir())


def test_portable_claim_cleanup_never_deletes_foreign_swapped_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "record.json"
    target.write_text("valid\n", encoding="utf-8")
    claim_name = f".{sha256(os.fsencode(target.name)).hexdigest()}.claim"
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)

    with (
        pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"),
        exclusive_path_claim(target),
    ):
        safe.rename(moved)
        safe.symlink_to(outside, target_is_directory=True)
        (outside / claim_name).write_text("foreign claim\n", encoding="utf-8")

    assert (outside / claim_name).read_text(encoding="utf-8") == "foreign claim\n"
    assert (moved / claim_name).exists()


def test_portable_claim_cleanup_preserves_recreated_foreign_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("valid\n", encoding="utf-8")
    claim_name = f".{sha256(os.fsencode(target.name)).hexdigest()}.claim"
    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    owner = exclusive_path_claim(target)
    owner.__enter__()
    (tmp_path / claim_name).unlink()
    (tmp_path / claim_name).write_text("foreign claim\n", encoding="utf-8")

    with pytest.raises(UnsafeAtomicPath, match="claim changed"):
        owner.__exit__(None, None, None)

    assert (tmp_path / claim_name).read_bytes() == b"foreign claim\n"


@pytest.mark.skipif(
    not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED,
    reason="descriptor-relative storage backend is unavailable",
)
def test_descriptor_replace_restores_old_bytes_after_post_publication_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_require = atomic_files_module._require_regular_at
    target_checks = 0

    def fail_once_after_publication(directory_fd: int, name: str):
        nonlocal target_checks
        result = original_require(directory_fd, name)
        if name == target.name:
            target_checks += 1
            if target_checks == 4:
                raise OSError("simulated post-publication validation failure")
        return result

    monkeypatch.setattr(atomic_files_module, "_require_regular_at", fail_once_after_publication)

    with (
        pytest.raises(OSError, match="post-publication validation failure"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"old valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == [target.name]


def test_portable_replace_restores_old_bytes_after_post_publication_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_require = atomic_files_module._require_regular_file
    target_checks = 0

    def fail_once_after_publication(path: Path):
        nonlocal target_checks
        result = original_require(path)
        if path == target:
            target_checks += 1
            if target_checks == 4:
                raise UnsafeAtomicPath("simulated post-publication validation failure")
        return result

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(atomic_files_module, "_require_regular_file", fail_once_after_publication)

    with (
        pytest.raises(UnsafeAtomicPath, match="post-publication validation failure"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert target.read_bytes() == b"old valid bytes\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == [target.name]


@pytest.mark.parametrize("portable", [False, True])
def test_failed_rollback_preserves_old_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, portable: bool
) -> None:
    if not portable and not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED:
        pytest.skip("descriptor-relative storage backend is unavailable")
    target = tmp_path / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    if portable:
        monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
        original_require = atomic_files_module._require_regular_file
        target_checks = 0

        def fail_once_after_publication(path: Path):
            nonlocal target_checks
            result = original_require(path)
            if path == target:
                target_checks += 1
                if target_checks == 4:
                    raise OSError("post-publication failure")
            return result

        original_replace = os.replace

        def fail_backup_restore(source, destination, *args, **kwargs):
            if str(source).endswith(".rollback"):
                raise OSError("restore failed")
            return original_replace(source, destination, *args, **kwargs)

        monkeypatch.setattr(
            atomic_files_module,
            "_require_regular_file",
            fail_once_after_publication,
        )
        monkeypatch.setattr(os, "replace", fail_backup_restore)
    else:
        original_require_at = atomic_files_module._require_regular_at
        target_checks = 0

        def fail_once_after_publication_at(directory_fd: int, name: str):
            nonlocal target_checks
            result = original_require_at(directory_fd, name)
            if name == target.name:
                target_checks += 1
                if target_checks == 4:
                    raise OSError("post-publication failure")
            return result

        original_rename = os.rename

        def fail_backup_restore_at(source, destination, *args, **kwargs):
            if str(source).endswith(".rollback") and Path(destination).name == target.name:
                raise OSError("restore failed")
            return original_rename(source, destination, *args, **kwargs)

        monkeypatch.setattr(
            atomic_files_module,
            "_require_regular_at",
            fail_once_after_publication_at,
        )
        monkeypatch.setattr(os, "rename", fail_backup_restore_at)

    with (
        pytest.raises(OSError, match="restore failed"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert not target.exists()
    backups = list(tmp_path.glob("*.rollback"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"old valid bytes\n"


def test_portable_path_operations_reject_symlinked_ancestor(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    target = linked / "nested" / "record.json"

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|reparse"):
        atomic_create_text(target, "must not escape\n")

    assert list(outside.iterdir()) == []


def test_portable_create_rejects_ancestor_swapped_during_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    (safe / "nested").mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "nested").mkdir()
    target = safe / "nested" / "record.json"
    original_lstat = os.lstat
    swapped = False

    def swapping_lstat(path, *args, **kwargs):
        nonlocal swapped
        metadata = original_lstat(path, *args, **kwargs)
        if not swapped and Path(path) == safe:
            safe.rename(moved)
            safe.symlink_to(outside, target_is_directory=True)
            swapped = True
        return metadata

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "lstat", swapping_lstat)

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"):
        atomic_create_text(target, "must not escape\n")

    assert list((outside / "nested").iterdir()) == []


def test_portable_create_cleans_directory_redirected_during_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "nested" / "record.json"
    original_lstat = os.lstat
    swapped = False

    def swap_after_safe_stat(path, *args, **kwargs):
        nonlocal swapped
        metadata = original_lstat(path, *args, **kwargs)
        if not swapped and Path(path) == safe:
            safe.rename(moved)
            safe.symlink_to(outside, target_is_directory=True)
            swapped = True
        return metadata

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "lstat", swap_after_safe_stat)

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"):
        atomic_create_text(target, "must not escape\n")

    assert not (outside / "nested").exists()
    assert list(moved.iterdir()) == []


def test_portable_create_rechecks_ancestor_after_component_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    (safe / "nested").mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "nested").mkdir()
    target = safe / "nested" / "record.json"
    original_lstat = os.lstat
    safe_checks = 0

    def swapping_after_confirmation(path, *args, **kwargs):
        nonlocal safe_checks
        metadata = original_lstat(path, *args, **kwargs)
        if Path(path) == safe:
            safe_checks += 1
            if safe_checks == 2:
                safe.rename(moved)
                safe.symlink_to(outside, target_is_directory=True)
        return metadata

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "lstat", swapping_after_confirmation)

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"):
        atomic_create_text(target, "must not escape\n")

    assert list((outside / "nested").iterdir()) == []


def test_portable_create_cleanup_never_deletes_foreign_swapped_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "record.json"
    foreign_path: Path | None = None

    def swap_then_fail(source, destination, *args, **kwargs):
        nonlocal foreign_path
        safe.rename(moved)
        safe.symlink_to(outside, target_is_directory=True)
        foreign_path = outside / Path(source).name
        foreign_path.write_text("foreign bytes\n", encoding="utf-8")
        raise OSError("simulated publication interruption")

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "link", swap_then_fail)

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"):
        atomic_create_text(target, "validated bytes\n")

    assert foreign_path is not None
    assert foreign_path.read_text(encoding="utf-8") == "foreign bytes\n"
    assert any(path.suffix == ".tmp" for path in moved.iterdir())


def test_portable_create_rejects_ancestor_swap_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "record.json"
    original_open = atomic_files_module._open_private_temporary

    def swap_parent(parent: Path, stem: str):
        safe.rename(moved)
        safe.symlink_to(outside, target_is_directory=True)
        return original_open(parent, stem)

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(atomic_files_module, "_open_private_temporary", swap_parent)

    with pytest.raises(UnsafeAtomicPath, match=r"changed during storage operation|symbolic link"):
        atomic_create_text(target, "must not escape\n")

    assert len(list(outside.glob("*.tmp"))) == 1
    assert list(moved.iterdir()) == []


def test_portable_replace_rejects_ancestor_swap_after_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    original_open = atomic_files_module._open_private_temporary

    def swap_parent(parent: Path, stem: str):
        safe.rename(moved)
        safe.symlink_to(outside, target_is_directory=True)
        (outside / target.name).write_text("attacker bytes\n", encoding="utf-8")
        return original_open(parent, stem)

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(atomic_files_module, "_open_private_temporary", swap_parent)

    with (
        pytest.raises(UnsafeAtomicPath, match=r"changed during storage operation|symbolic link"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "must not escape\n", claim=claim)

    assert (moved / target.name).read_text(encoding="utf-8") == "old valid bytes\n"
    assert (outside / target.name).read_text(encoding="utf-8") == "attacker bytes\n"


def test_portable_replace_cleanup_never_deletes_foreign_swapped_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    safe.mkdir()
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = safe / "record.json"
    target.write_text("old valid bytes\n", encoding="utf-8")
    foreign_path: Path | None = None

    def swap_then_fail(source, destination, *args, **kwargs):
        nonlocal foreign_path
        safe.rename(moved)
        safe.symlink_to(outside, target_is_directory=True)
        foreign_path = outside / Path(source).name
        foreign_path.write_text("foreign bytes\n", encoding="utf-8")
        (outside / Path(destination).name).write_text("foreign record\n", encoding="utf-8")
        raise OSError("simulated replacement interruption")

    monkeypatch.setattr(atomic_files_module, "_DESCRIPTOR_BACKEND_SUPPORTED", False)
    monkeypatch.setattr(os, "replace", swap_then_fail)

    with (
        pytest.raises(UnsafeAtomicPath, match=r"symbolic link|changed"),
        exclusive_path_claim(target) as claim,
    ):
        atomic_replace_text(target, "new valid bytes\n", claim=claim)

    assert foreign_path is not None
    assert foreign_path.read_text(encoding="utf-8") == "foreign bytes\n"
    assert (moved / target.name).read_text(encoding="utf-8") == "old valid bytes\n"
    assert any(path.suffix == ".tmp" for path in moved.iterdir())


def test_read_rejects_symlink_target(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("outside\n", encoding="utf-8")
    linked = tmp_path / "record.json"
    linked.symlink_to(outside)

    with pytest.raises(UnsafeAtomicPath, match=r"symbolic link|reparse"):
        read_text_no_follow(linked)


def test_private_name_allocators_fail_after_the_bounded_collision_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_open = os.open

    def collide(*_args, **_kwargs):
        raise FileExistsError("occupied")

    monkeypatch.setattr(os, "open", collide)
    with pytest.raises(FileExistsError, match="allocate an exclusive temporary"):
        atomic_files_module._open_private_temporary(tmp_path, "record")

    monkeypatch.setattr(os, "open", original_open)
    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        monkeypatch.setattr(os, "open", collide)
        with pytest.raises(FileExistsError, match="allocate an exclusive temporary"):
            atomic_files_module._open_private_temporary_at(descriptor, "record")
    finally:
        os.close(descriptor)


def test_backup_allocators_fail_after_the_bounded_collision_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("valid\n", encoding="utf-8")
    metadata = target.stat()
    identity = (metadata.st_dev, metadata.st_ino)

    monkeypatch.setattr(
        os,
        "link",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError("occupied")),
    )
    with pytest.raises(FileExistsError, match="allocate replacement backup"):
        atomic_files_module._create_backup_path(target, identity)

    if atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED:
        descriptor = os.open(tmp_path, os.O_RDONLY | atomic_files_module._DIRECTORY)
        try:
            with pytest.raises(FileExistsError, match="allocate replacement backup"):
                atomic_files_module._create_backup_at(descriptor, target.name, identity)
        finally:
            os.close(descriptor)


@pytest.mark.parametrize("portable", [False, True])
def test_backup_identity_drift_preserves_foreign_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, portable: bool
) -> None:
    if not portable and not atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED:
        pytest.skip("descriptor-relative storage backend is unavailable")
    target = tmp_path / "record.json"
    target.write_text("valid\n", encoding="utf-8")
    metadata = target.stat()
    identity = (metadata.st_dev, metadata.st_ino)
    original_link = os.link
    foreign_path: Path | None = None

    def replace_backup(source, destination, *args, **kwargs):
        nonlocal foreign_path
        result = original_link(source, destination, *args, **kwargs)
        directory_fd = kwargs.get("dst_dir_fd")
        if directory_fd is None:
            foreign_path = Path(destination)
            foreign_path.unlink()
            foreign_path.write_text("foreign backup\n", encoding="utf-8")
        else:
            foreign_path = tmp_path / str(destination)
            os.unlink(destination, dir_fd=directory_fd)
            descriptor = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=directory_fd,
            )
            try:
                os.write(descriptor, b"foreign backup\n")
            finally:
                os.close(descriptor)
        return result

    monkeypatch.setattr(os, "link", replace_backup)
    if portable:
        with pytest.raises(UnsafeAtomicPath, match="changed while backup was created"):
            atomic_files_module._create_backup_path(target, identity)
    else:
        directory_fd = os.open(tmp_path, os.O_RDONLY | atomic_files_module._DIRECTORY)
        try:
            with pytest.raises(UnsafeAtomicPath, match="changed while backup was created"):
                atomic_files_module._create_backup_at(directory_fd, target.name, identity)
        finally:
            os.close(directory_fd)

    assert target.read_bytes() == b"valid\n"
    assert foreign_path is not None
    assert foreign_path.read_bytes() == b"foreign backup\n"


def test_quarantine_allocators_fail_after_the_bounded_collision_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "record.json"
    target.write_text("valid\n", encoding="utf-8")
    identity = (target.stat().st_dev, target.stat().st_ino)
    monkeypatch.setattr(
        os,
        "rename",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError("occupied")),
    )

    with pytest.raises(FileExistsError, match="allocate rollback quarantine"):
        atomic_files_module._quarantine_and_remove_path(
            target,
            identity,
            changed_message="changed",
        )

    if atomic_files_module._DESCRIPTOR_BACKEND_SUPPORTED:
        descriptor = os.open(tmp_path, os.O_RDONLY | atomic_files_module._DIRECTORY)
        try:
            with pytest.raises(FileExistsError, match="allocate rollback quarantine"):
                atomic_files_module._quarantine_and_remove_at(
                    descriptor,
                    target.name,
                    identity,
                    changed_message="changed",
                )
        finally:
            os.close(descriptor)
