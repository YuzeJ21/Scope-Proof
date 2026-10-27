"""Observed source identity, independent of Git, target code, and UI layers."""

from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CoreSourceIdentity(BaseModel):
    """A source fingerprint, not a signature or an execution attestation."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    scheme: Literal["core-python-source-v1"] = "core-python-source-v1"
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def core_source_identity(root: Path) -> CoreSourceIdentity:
    """Hash sorted relative Python paths and LF-normalized source digests."""
    if root.is_symlink():
        raise ValueError("core source root must not be a symlink")
    if not root.is_dir():
        raise ValueError("core source directory is unavailable")
    manifest: list[list[str]] = []

    def fail_scan(error: OSError) -> None:
        raise ValueError("cannot read core source for identity") from error

    for directory, subdirectories, files in os.walk(root, onerror=fail_scan, followlinks=False):
        for name in [*subdirectories, *files]:
            if (Path(directory) / name).is_symlink():
                raise ValueError("core source tree must not contain symlinks")
        for name in files:
            path = Path(directory) / name
            if path.suffix != ".py":
                continue
            try:
                contents = path.read_bytes().replace(b"\r\n", b"\n")
            except OSError as error:
                raise ValueError("cannot read core source for identity") from error
            manifest.append([path.relative_to(root).as_posix(), sha256(contents).hexdigest()])
    if not manifest:
        raise ValueError("core source directory contains no Python source")
    manifest.sort(key=lambda entry: entry[0])
    canonical = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return CoreSourceIdentity(sha256=sha256(canonical).hexdigest())


def current_core_source_identity() -> CoreSourceIdentity:
    """Observe this installed core's source without executing repository code."""
    return core_source_identity(Path(__file__).resolve().parent)
