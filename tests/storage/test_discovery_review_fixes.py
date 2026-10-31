"""Independent-review regressions for bounded nesting and preview-bound deletion."""

import pytest

from scopeproof_core.storage.discovery import discover_saved_review_page, load_discovered_review
from scopeproof_core.storage.json_store import (
    _SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED,
    JsonReviewStore,
    StaleReviewState,
)
from tests.storage.test_review_discovery import saved


@pytest.mark.parametrize(
    "payload",
    [
        "[" * 2000 + "0" + "]" * 2000,
        '{"record_version":7,"state":{"extra":' + "[" * 600 + "0" + "]" * 600 + "}}",
    ],
    ids=["json-parser-depth", "state-copy-depth"],
)
def test_deep_record_is_unavailable_without_aborting_valid_neighbor(tmp_path, payload):
    store = JsonReviewStore(tmp_path)
    saved(store, "a-good")
    path = tmp_path / "z-deep.json"
    path.write_text(payload)
    before = path.read_bytes()
    page = discover_saved_review_page(store)
    assert page.entries[0].metadata is not None
    assert page.entries[1].review_id == "z-deep" and page.entries[1].metadata is None
    with pytest.raises(ValueError):
        load_discovered_review(store, "z-deep")
    assert path.read_bytes() == before


@pytest.mark.skipif(
    not _SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED,
    reason="safe descriptor deletion is unavailable on this platform",
)
def test_preview_guarded_delete_rejects_changed_record_without_unlink(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store)
    expected = store.state_fingerprint(state)
    state.review.tool_version = "0.0.changed"
    state.bundle.review.tool_version = state.review.tool_version
    path = store.save(state)
    before = path.read_bytes()
    with pytest.raises(StaleReviewState):
        store.delete(state.review.review_id, expected_fingerprint=expected)
    assert path.read_bytes() == before


@pytest.mark.skipif(
    not _SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED,
    reason="safe descriptor deletion is unavailable on this platform",
)
def test_preview_guarded_delete_accepts_matching_record(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store)
    store.delete(state.review.review_id, expected_fingerprint=store.state_fingerprint(state))
    assert not (tmp_path / f"{state.review.review_id}.json").exists()


@pytest.mark.skipif(
    not _SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED,
    reason="safe descriptor deletion is unavailable on this platform",
)
def test_id_only_corrupt_record_deletion_remains_available_without_preview(tmp_path):
    store = JsonReviewStore(tmp_path)
    path = tmp_path / "broken.json"
    path.write_text("{broken")
    store.delete("broken")
    assert not path.exists()
