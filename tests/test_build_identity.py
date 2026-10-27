import json
import os
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.validation import validated_review_bundle
from scopeproof_core.reviews.lifecycle import (
    attach_analysis,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import Review, ReviewBundle
from scopeproof_core.storage.json_store import JsonReviewStore


def test_new_analysis_records_core_source_and_parsing_absent_identity_stays_unknown() -> None:
    bundle = build_demo_review()
    assert bundle.review.analysis_source_identity is not None
    payload = bundle.model_dump(mode="json")
    payload["review"].pop("analysis_source_identity")
    historical = ReviewBundle.model_validate(payload)
    assert historical.review.analysis_source_identity is None
    assert validated_review_bundle(historical).review.analysis_source_identity is None
    assert historical.gate == bundle.gate


def test_source_identity_is_root_order_and_newline_independent(tmp_path: Path) -> None:
    from scopeproof_core.build_identity import core_source_identity

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "a.py").write_bytes(b"x=1\n")
    (second / "a.py").write_bytes(b"x=1\r\n")
    identity = core_source_identity(first)
    assert identity.sha256 == "96a8c9d0211c05940c997d340b5743f2dafa3cd1f2378e17a95d4ce776f59d18"
    assert identity == core_source_identity(second)
    assert identity.scheme == "core-python-source-v1"
    (second / "ignored.pyc").write_bytes(b"bytecode")
    assert identity == core_source_identity(second)
    (second / "a.py").write_bytes(b"x=2\n")
    assert identity != core_source_identity(second)
    (second / "a.py").rename(second / "b.py")
    assert identity != core_source_identity(second)


@pytest.mark.parametrize("digest", ["", "a" * 63, "A" * 64, "g" * 64, 7, True])
def test_source_identity_rejects_malformed_digest(digest: object) -> None:
    from scopeproof_core.build_identity import CoreSourceIdentity

    with pytest.raises(ValidationError):
        CoreSourceIdentity(sha256=digest)


def test_source_identity_rejects_unknown_fields_and_scheme() -> None:
    from scopeproof_core.build_identity import CoreSourceIdentity

    with pytest.raises(ValidationError):
        CoreSourceIdentity(sha256="a" * 64, commit="invented")
    with pytest.raises(ValidationError):
        CoreSourceIdentity(sha256="a" * 64, scheme="unknown")


def test_source_identity_refuses_empty_missing_and_symlinked_source(tmp_path: Path) -> None:
    from scopeproof_core.build_identity import core_source_identity

    with pytest.raises(ValueError, match="source"):
        core_source_identity(tmp_path)
    with pytest.raises(ValueError, match="source"):
        core_source_identity(tmp_path / "absent")
    source = tmp_path / "outside.py"
    source.write_text("x=1\n")
    package = tmp_path / "package"
    package.mkdir()
    try:
        (package / "linked.py").symlink_to(source)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="symlink"):
        core_source_identity(package)


def test_saved_identity_round_trip_and_unknown_historical_record(tmp_path: Path) -> None:
    state = new_review_state(build_demo_review())
    store = JsonReviewStore(tmp_path / "reviews")
    path = store.save(state)
    assert store.load(state.review.review_id).review.analysis_source_identity == (
        state.review.analysis_source_identity
    )
    raw = json.loads(path.read_text())
    raw["state"]["review"].pop("analysis_source_identity")
    raw["state"]["bundle"]["review"].pop("analysis_source_identity")
    path.write_text(json.dumps(raw))
    assert store.load(state.review.review_id).review.analysis_source_identity is None


@pytest.mark.parametrize("old_identity", [None, {"sha256": "a" * 64}])
def test_reanalysis_adopts_current_source_preserving_archived_identity(old_identity) -> None:
    from scopeproof_core.build_identity import current_core_source_identity

    payload = build_demo_review().model_dump(mode="python")
    payload["review"]["analysis_source_identity"] = old_identity
    payload["review"]["tool_version"] = "0.1.0"
    payload["review"]["ruleset_version"] = "1.0.0"
    state = new_review_state(ReviewBundle.model_validate(payload))
    revised = revise_criteria(state, state.criteria_revision.criteria, state.bundle.source_text)
    provenance = build_criteria_source_provenance(
        source_uri="https://example.test/requirements",
        source_revision="2",
        source_text=revised.criteria_revision.source_text,
        criteria=revised.criteria_revision.criteria,
        confirmed_by="Constructed test actor",
        confirmed_at=revised.criteria_revision.created_at + timedelta(seconds=1),
    )
    revised = confirm_criteria(revised, provenance)
    incoming = build_demo_review()
    incoming.review.criteria_source_provenance = provenance
    updated = attach_analysis(revised, incoming)
    assert updated.review.analysis_source_identity == current_core_source_identity()
    assert updated.review.tool_version == incoming.review.tool_version
    assert updated.review.ruleset_version == incoming.review.ruleset_version
    assert updated.bundle.review == updated.review
    assert updated.analysis_history == revised.analysis_history
    assert updated.analysis_history[0].review == state.review


def test_bare_review_does_not_manufacture_source_identity() -> None:
    review = Review(repository="acme/repo", pr_number=1, base_sha="base", head_sha="head")
    assert review.analysis_source_identity is None


def test_unreadable_core_source_fails_explicitly(tmp_path: Path, monkeypatch) -> None:
    from scopeproof_core.build_identity import core_source_identity

    (tmp_path / "a.py").write_text("x=1\n")

    def unreadable(_path):
        raise PermissionError("constructed read failure")

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    with pytest.raises(ValueError, match="cannot read core source"):
        core_source_identity(tmp_path)


def test_unreadable_nested_source_directory_cannot_produce_partial_identity(tmp_path: Path) -> None:
    from scopeproof_core.build_identity import core_source_identity

    (tmp_path / "a.py").write_text("x=1\n")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.py").write_text("x=2\n")
    nested.chmod(0)
    try:
        if os.access(nested, os.R_OK):
            pytest.skip("directory permission enforcement unavailable")
        with pytest.raises(ValueError, match="cannot read core source"):
            core_source_identity(tmp_path)
    finally:
        nested.chmod(0o700)
