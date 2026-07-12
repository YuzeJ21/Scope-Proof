from __future__ import annotations

import json
from pathlib import Path

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import PullRequestSnapshot
from scopeproof_core.storage.json_store import (
    JsonReviewStore,
    UnsupportedRecordVersion,
    default_local_review_directory,
)


def review_state():
    state = new_review_state(build_demo_review())
    state.review.review_id = "review-1"
    return state


def test_saved_review_round_trips_without_token(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()

    path = store.save(state)
    loaded = store.load("review-1")

    assert path.name == "review-1.json"
    assert loaded.model_dump(mode="json") == state.model_dump(mode="json")
    assert "ghp_" not in path.read_text(encoding="utf-8")
    assert "authorization" not in path.read_text(encoding="utf-8").lower()


def test_head_change_is_reported_without_mutating_old_evidence(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    snapshot = PullRequestSnapshot.model_validate(
        {
            **build_demo_review().review.model_dump(mode="json"),
            "title": "Updated demo",
            "html_url": "https://github.com/scopeproof/demo-stock-research/pull/17",
            "head_sha": "new-head",
            "files": [],
        }
    )

    change = store.detect_head_change(state, snapshot)

    assert change.changed is True
    assert change.saved_head_sha == "head-demo-002"
    assert change.current_head_sha == "new-head"
    assert state.bundle is not None
    assert state.bundle.review.head_sha == "head-demo-002"


def test_unknown_record_version_is_rejected(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["record_version"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(UnsupportedRecordVersion):
        store.load("review-1")


def test_review_id_cannot_escape_store_directory(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)

    with pytest.raises(ValueError):
        store.load("../outside")


def test_default_local_review_directory_is_confined_to_the_user_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert default_local_review_directory() == tmp_path / ".scopeproof" / "reviews"
