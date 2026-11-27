"""Exact-build CI directory lookup stays bounded and independent of review state."""

from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from pathlib import Path

import pytest

from scopeproof_core.reviews.ci_handoff import (
    ci_manifest_filename,
    load_exact_ci_manifest,
    load_exact_ci_manifest_with_sha256,
)
from scopeproof_core.reviews.ci_status import MAX_CI_STATUS_BYTES
from scopeproof_core.schemas.models import ReviewBundle, normalized_criteria_sha256
from tests.junit_audit_fixture import junit_audit_state


@pytest.fixture
def bundle() -> ReviewBundle:
    analysis = junit_audit_state().bundle
    assert analysis is not None
    return analysis


@pytest.fixture
def manifest(bundle: ReviewBundle) -> dict:
    review = bundle.review
    return {
        "schema_version": "criterion-ci-status-v1",
        "repository": review.repository,
        "pr_number": review.pr_number,
        "criteria_sha256": normalized_criteria_sha256(bundle.criteria),
        "expected_tests": {"AC-01": ["export-rows"]},
        "runs": [{
            "run_id": "constructed-ci-01",
            "head_sha": review.head_sha,
            "source_url": "https://ci.example.invalid/runs/01",
            "outcomes": {"export-rows": "passed"},
        }],
    }


def _manifest_path(root: Path, bundle: ReviewBundle) -> Path:
    review = bundle.review
    return root / ci_manifest_filename(
        review.repository, review.pr_number, review.head_sha,
        normalized_criteria_sha256(bundle.criteria),
    )


def _payload(manifest: dict) -> bytes:
    return json.dumps(manifest).encode("utf-8")


def test_exact_lookup_key_is_canonical_and_changes_with_review_context() -> None:
    key = ("owner/project", 17, "a" * 40, "b" * 64)
    filename = ci_manifest_filename(*key)
    assert re.fullmatch(r"[a-z0-9-]+\.json", filename)
    assert ci_manifest_filename("Owner/ProjecT", *key[1:]) == filename
    for replacement in (
        ("owner/other", *key[1:]),
        (key[0], 18, *key[2:]),
        (*key[:2], "c" * 40, key[3]),
        (*key[:3], "d" * 64),
    ):
        assert ci_manifest_filename(*replacement) != filename


def test_loads_matching_manifest_without_altering_review_or_files(
    tmp_path: Path, bundle: ReviewBundle, manifest: dict,
) -> None:
    root = tmp_path.resolve()
    path = _manifest_path(root, bundle)
    manifest["repository"] = manifest["repository"].upper()
    payload = _payload(manifest)
    path.write_bytes(payload)
    (root / "unrelated.json").write_bytes(b"malformed unrelated file")
    prior = bundle.model_dump_json()
    loaded = load_exact_ci_manifest(root, bundle)
    assert loaded.model_dump(mode="json") == manifest
    assert bundle.model_dump_json() == prior
    assert path.read_bytes() == payload


def test_handoff_digest_binds_exact_bytes_even_for_identical_parsed_content(
    tmp_path: Path, bundle: ReviewBundle, manifest: dict,
) -> None:
    root = tmp_path.resolve()
    path = _manifest_path(root, bundle)
    first = b"\r\n" + _payload(manifest) + b"\r\n"
    second = first.replace(b"\r\n", b"\n")
    path.write_bytes(first)
    manifest_first, digest_first = load_exact_ci_manifest_with_sha256(root, bundle)
    path.write_bytes(second)
    manifest_second, digest_second = load_exact_ci_manifest_with_sha256(root, bundle)

    assert manifest_first == manifest_second == load_exact_ci_manifest(root, bundle)
    assert digest_first == sha256(first).hexdigest()
    assert digest_second == sha256(second).hexdigest()
    assert digest_first != digest_second


@pytest.mark.parametrize("newline", [b"\n", b"\r\n", b"\r"])
def test_comparison_reader_preserves_the_exact_bounded_input_bytes(
    tmp_path: Path, bundle: ReviewBundle, manifest: dict, newline: bytes,
) -> None:
    from scopeproof_core.reviews.ci_handoff import load_exact_ci_manifest_with_payload

    path = _manifest_path(tmp_path.resolve(), bundle)
    payload = newline + _payload(manifest) + newline
    path.write_bytes(payload)
    before = bundle.model_dump_json()

    loaded, raw = load_exact_ci_manifest_with_payload(tmp_path.resolve(), bundle)

    assert raw == payload
    assert loaded.model_dump(mode="json") == manifest
    assert path.read_bytes() == payload
    assert bundle.model_dump_json() == before


def test_missing_exact_filename_does_not_scan_other_manifests(
    tmp_path: Path, bundle: ReviewBundle, manifest: dict,
) -> None:
    root = tmp_path.resolve()
    (root / "different-name.json").write_bytes(_payload(manifest))
    with pytest.raises(FileNotFoundError):
        load_exact_ci_manifest(root, bundle)


@pytest.mark.parametrize("context", [{"criteria_confirmed": False}, {"head_sha": "short"}])
def test_invalid_review_context_is_rejected_before_lookup(
    tmp_path: Path, bundle: ReviewBundle, context: dict,
) -> None:
    invalid = bundle.model_copy(update={"review": bundle.review.model_copy(update=context)})
    with pytest.raises(ValueError):
        load_exact_ci_manifest(tmp_path.resolve(), invalid)


@pytest.mark.parametrize(("field", "value"), [
    ("repository", "owner/other"),
    ("pr_number", 42),
    ("criteria_sha256", "0" * 64),
    ("expected_tests", {"AC-99": ["export-rows"]}),
])
def test_filename_cannot_override_embedded_context(
    tmp_path: Path, bundle: ReviewBundle, manifest: dict, field: str, value: object,
) -> None:
    root = tmp_path.resolve()
    manifest[field] = value
    _manifest_path(root, bundle).write_bytes(_payload(manifest))
    with pytest.raises(ValueError):
        load_exact_ci_manifest(root, bundle)


def test_automatic_manifest_requires_at_least_one_exact_head_run(
    tmp_path: Path, bundle: ReviewBundle, manifest: dict,
) -> None:
    root = tmp_path.resolve()
    target = _manifest_path(root, bundle)
    manifest["runs"][0]["head_sha"] = "c" * 40
    target.write_bytes(_payload(manifest))
    with pytest.raises(ValueError):
        load_exact_ci_manifest(root, bundle)

    manifest["runs"].append({
        **manifest["runs"][0],
        "run_id": "constructed-ci-02",
        "head_sha": bundle.review.head_sha,
    })
    target.write_bytes(_payload(manifest))
    assert len(load_exact_ci_manifest(root, bundle).runs) == 2


@pytest.mark.parametrize("condition", ["malformed", "oversize", "directory", "fifo"])
def test_rejects_unsafe_or_invalid_exact_candidate(
    tmp_path: Path, bundle: ReviewBundle, condition: str,
) -> None:
    root = tmp_path.resolve()
    target = _manifest_path(root, bundle)
    if condition == "directory":
        target.mkdir()
    elif condition == "fifo":
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO creation is unavailable")
        os.mkfifo(target)
    else:
        target.write_bytes(b" " * (MAX_CI_STATUS_BYTES + 1) if condition == "oversize" else b"[")
    with pytest.raises(ValueError):
        load_exact_ci_manifest(root, bundle)


@pytest.mark.parametrize("link", ["manifest", "root"])
def test_refuses_symbolic_links_even_when_the_referent_would_validate(
    tmp_path: Path, bundle: ReviewBundle, manifest: dict, link: str,
) -> None:
    root = tmp_path.resolve()
    actual_root = root / "actual"
    actual_root.mkdir()
    actual = _manifest_path(actual_root, bundle)
    actual.write_bytes(_payload(manifest))
    target = _manifest_path(root, bundle)
    try:
        if link == "root":
            root = root / "linked-root"
            root.symlink_to(actual_root, target_is_directory=True)
        else:
            target.symlink_to(actual)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic link creation is unavailable")
    with pytest.raises(ValueError):
        load_exact_ci_manifest(root, bundle)
