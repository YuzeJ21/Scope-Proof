"""Constructed local discovery is bounded, validated and never a readiness claim."""

import json
from importlib import import_module
from unittest.mock import patch

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.storage.json_store import JsonReviewStore


def api():
    return import_module("scopeproof_core.storage.discovery")


def saved(store, review_id="review-001"):
    state = new_review_state(build_demo_review())
    state.review.review_id = review_id
    state.bundle.review.review_id = review_id
    store.save(state)
    return state


def test_discovery_validates_metadata_without_rewriting_or_adding_gate_claims(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    page = api().discover_saved_review_page(store)
    assert page.page_index == 0 and page.total_review_count == 1
    entry = page.entries[0]
    assert entry.review_id == state.review.review_id
    assert entry.metadata.repository == state.review.repository
    assert entry.metadata.pr_number == state.review.pr_number
    assert entry.metadata.head_sha == state.review.head_sha
    assert entry.metadata.criteria_revision_number == 1
    assert entry.metadata.state_fingerprint == store.state_fingerprint(state)
    assert entry.metadata.has_active_analysis is True
    assert "gate" not in entry.model_dump_json() and "ready" not in entry.model_dump_json()
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*.json")} == before


def test_page_reads_only_ten_candidates_under_the_one_mib_budget(tmp_path):
    store = JsonReviewStore(tmp_path)
    for i in range(12):
        saved(store, f"record-{i:02}")
    with patch.object(store, "load", wraps=store.load) as load:
        page = api().discover_saved_review_page(store, page_index=1)
    assert [e.review_id for e in page.entries] == ["record-10", "record-11"]
    assert load.call_count == 2
    assert all(c.kwargs["max_bytes"] == 1024 * 1024 for c in load.call_args_list)


@pytest.mark.parametrize("index", [-1, True, 1.0, "0", 1])
def test_invalid_or_out_of_range_pages_reject_before_record_reads(tmp_path, index):
    store = JsonReviewStore(tmp_path)
    saved(store)
    with (
        patch.object(store, "load", side_effect=AssertionError("must not read")),
        pytest.raises(ValueError),
    ):
        api().discover_saved_review_page(store, page_index=index)


@pytest.mark.parametrize("bad", ["json", "version", "nested", "encoding", "oversized", "owner"])
def test_bad_neighbor_keeps_id_but_supplies_no_partial_metadata(tmp_path, bad):
    store = JsonReviewStore(tmp_path)
    saved(store, "a-good")
    state = saved(store, "z-bad")
    path = tmp_path / "z-bad.json"
    payload = json.loads(path.read_text())
    if bad == "json":
        path.write_text('{"repository":"invented/repo",')
    elif bad == "encoding":
        path.write_bytes(b"\xff")
    elif bad == "oversized":
        path.write_bytes(b" " * (1024 * 1024 + 1))
    else:
        if bad == "version":
            payload["record_version"] = 99
        elif bad == "nested":
            payload["state"]["bundle"]["gate"]["verdict"] = "invented"
        else:
            payload = {**payload, "state": state.model_dump(mode="json")}
            payload["state"]["review"]["review_id"] = "different-owner"
            payload["state"]["bundle"]["review"]["review_id"] = "different-owner"
        path.write_text(json.dumps(payload))
    before = path.read_bytes()
    page = api().discover_saved_review_page(store)
    assert page.entries[0].metadata is not None
    assert page.entries[1].review_id == "z-bad" and page.entries[1].metadata is None
    assert path.read_bytes() == before


def test_search_labels_and_duplicate_metadata_keep_explicit_record_identity(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store, "a-first")
    saved(store, "b-second")
    page = api().discover_saved_review_page(store)
    labels = [api().format_saved_review_label(e) for e in page.entries]
    assert state.review.repository in labels[0]
    assert f"#{state.review.pr_number}" in labels[0]
    assert "revision 1" in labels[0]
    assert labels[0] != labels[1]
    assert api().matching_saved_review_ids(page, state.review.repository.upper()) == [
        "a-first",
        "b-second",
    ]
    assert api().matching_saved_review_ids(page, "first") == ["a-first"]
    assert api().matching_saved_review_ids(page, "not-present") == []


def test_loader_preview_cap_preserves_normal_large_record_loading(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store)
    path = tmp_path / f"{state.review.review_id}.json"
    path.write_text(path.read_text() + " " * (1024 * 1024))
    with pytest.raises(ValueError, match="byte limit"):
        store.load(state.review.review_id, max_bytes=1024 * 1024)
    assert store.load(state.review.review_id) == state
