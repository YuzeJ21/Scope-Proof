"""Saved discovery never retargets an ID or applies a changed preview."""

from datetime import timedelta
from importlib import import_module

import pytest

from scopeproof_core.reviews.saved_comparison import prepare_saved_comparison
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.saved_comparison_fixture import saved_comparison_states
from tests.storage.test_review_discovery import saved


def api():
    return import_module("scopeproof_core.storage.discovery")


def test_discovered_reopen_rejects_changed_record_and_retains_saved_bytes(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store)
    entry = api().discover_saved_review_page(store).entries[0]
    original = store.load(state.review.review_id)
    assert (
        api().load_discovered_review(
            store,
            entry.review_id,
            expected_fingerprint=entry.metadata.state_fingerprint,
        )
        == original
    )
    changed = original.model_copy(deep=True)
    changed.criteria_revision.created_at += timedelta(seconds=1)
    store.save(changed)
    path = tmp_path / f"{entry.review_id}.json"
    before = path.read_bytes()
    with pytest.raises(ValueError, match="changed"):
        api().load_discovered_review(
            store,
            entry.review_id,
            expected_fingerprint=entry.metadata.state_fingerprint,
        )
    assert path.read_bytes() == before


def test_discovered_reopen_rejects_removed_record_without_fallback(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store)
    entry = api().discover_saved_review_page(store).entries[0]
    (tmp_path / f"{state.review.review_id}.json").unlink()
    with pytest.raises(FileNotFoundError):
        api().load_discovered_review(
            store, entry.review_id, expected_fingerprint=entry.metadata.state_fingerprint
        )


def test_raw_id_fallback_cannot_reopen_a_different_owner(tmp_path):
    store = JsonReviewStore(tmp_path)
    saved(store, "real-owner")
    (tmp_path / "wrong-id.json").write_bytes((tmp_path / "real-owner.json").read_bytes())
    with pytest.raises(ValueError, match="owning"):
        api().load_discovered_review(store, "wrong-id")


@pytest.mark.parametrize("side", ["current", "baseline"])
def test_core_comparison_never_retargets_mismatching_saved_file_owner(tmp_path, side):
    store = JsonReviewStore(tmp_path)
    current, previous = saved_comparison_states()
    store.save(current)
    store.save(previous)
    selected = current if side == "current" else previous
    path = tmp_path / f"{selected.review.review_id}.json"

    def replace_owner(value):
        if isinstance(value, dict):
            return {
                key: "different-owner" if key == "review_id" else replace_owner(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [replace_owner(item) for item in value]
        return value

    impostor = type(selected).model_validate(replace_owner(selected.model_dump(mode="python")))
    other_path = store.save(impostor)
    path.write_bytes(other_path.read_bytes())
    with pytest.raises(ValueError, match=r"owning|identity"):
        prepare_saved_comparison(store, current, previous.review.review_id)
