"""Read one bounded CI manifest published for the confirmed review context."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from scopeproof_core.reviews.ci_status import (
    EXACT_HEAD_PATTERN,
    MAX_CI_STATUS_BYTES,
    CIStatusManifest,
    load_ci_status_manifest,
    validate_ci_manifest_context,
)
from scopeproof_core.schemas.models import ReviewBundle, normalized_criteria_sha256
from scopeproof_core.storage.atomic_files import read_text_no_follow


def ci_manifest_filename(
    repository: str, pr_number: int, head_sha: str, criteria_sha256: str,
) -> str:
    """Key one direct child by portable, case-insensitive repository identity."""
    identity = (repository.casefold(), pr_number, head_sha, criteria_sha256)
    digest = sha256(json.dumps(identity, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"ci-manifest-{digest}.json"


def load_exact_ci_manifest(directory: Path, bundle: ReviewBundle) -> CIStatusManifest:
    """Reject mismatched files even if they have the exact expected filename."""
    manifest, _ = load_exact_ci_manifest_with_sha256(directory, bundle)
    return manifest


def load_exact_ci_manifest_with_sha256(
    directory: Path, bundle: ReviewBundle,
) -> tuple[CIStatusManifest, str]:
    """Read and validate one matching manifest and hash the same bytes."""
    manifest, payload = load_exact_ci_manifest_with_payload(directory, bundle)
    return manifest, sha256(payload).hexdigest()


def load_exact_ci_manifest_with_payload(
    directory: Path, bundle: ReviewBundle,
) -> tuple[CIStatusManifest, bytes]:
    """Retain the exact bounded bytes used to validate the current CI context."""
    review = bundle.review
    if not review.criteria_confirmed or not re.fullmatch(EXACT_HEAD_PATTERN, review.head_sha):
        raise ValueError("automatic CI handoff requires confirmed criteria and an exact head")
    criteria_digest = normalized_criteria_sha256(bundle.criteria)
    name = ci_manifest_filename(
        review.repository, review.pr_number, review.head_sha, criteria_digest,
    )
    text = read_text_no_follow(
        directory / name, max_bytes=MAX_CI_STATUS_BYTES, preserve_newlines=True,
    )
    payload = text.encode("utf-8")
    manifest = load_ci_status_manifest(payload)
    if not any(run.head_sha == review.head_sha for run in manifest.runs):
        raise ValueError("automatic CI handoff requires an exact-head run")
    validate_ci_manifest_context(bundle, manifest, criteria_digest)
    return manifest, payload
