"""Adversarial constructed records exercise discovery's storage and trust boundaries."""

import json
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import scopeproof_core.storage.atomic_files as atomic_files
import scopeproof_core.storage.discovery as discovery
import scopeproof_core.storage.json_store as json_store
from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.storage.json_store import JsonReviewStore, UnsafeReviewStore
from tests.storage.test_review_discovery import saved

PREVIEW_BYTES = 1024 * 1024


def padded_record(path, size):
    content = path.read_bytes()
    assert len(content) < size
    path.write_bytes(content + b" " * (size - len(content)))


class ObservedRead:
    """Keep actual descriptor reads, exposing only the requested and returned bytes."""

    def __init__(self, handle, observations, grow=None):
        self.handle = handle
        self.observations = observations
        self.grow = grow

    def fileno(self):
        return self.handle.fileno()

    def read(self, size=-1):
        if self.grow is not None:
            with self.grow.open("ab") as handle:
                handle.write(b" ")
        value = self.handle.read(size)
        self.observations.append((size, len(value)))
        return value


@pytest.mark.parametrize("grow", [False, True], ids=["exact-cap", "overflow-after-stat"])
def test_actual_descriptor_read_accepts_exact_cap_and_probes_only_one_extra_byte(
    tmp_path, monkeypatch, grow
):
    store = JsonReviewStore(tmp_path)
    state = saved(store, "bounded-record")
    path = tmp_path / "bounded-record.json"
    padded_record(path, PREVIEW_BYTES)
    original = atomic_files.read_bounded_utf8
    observations = []

    def observe(handle, *, max_bytes):
        return original(
            ObservedRead(handle, observations, path if grow else None), max_bytes=max_bytes
        )

    monkeypatch.setattr(atomic_files, "read_bounded_utf8", observe)
    page = discovery.discover_saved_review_page(store)
    assert observations == [(PREVIEW_BYTES + 1, PREVIEW_BYTES + int(grow))]
    if grow:
        assert page.entries[0].metadata is None
    else:
        assert page.entries[0].metadata.review_id == state.review.review_id
    assert path.stat().st_size == PREVIEW_BYTES + int(grow)


def test_ten_real_reads_bound_the_aggregate_and_never_parse_other_pages(tmp_path, monkeypatch):
    store = JsonReviewStore(tmp_path)
    for index in range(23):
        path = tmp_path / f"record-{index:02}.json"
        if 10 <= index < 20:
            saved(store, f"record-{index:02}")
        else:
            path.write_text('{"out-of-page-sentinel":true}', encoding="utf-8")
    before = {path.name: path.read_bytes() for path in tmp_path.glob("*.json")}
    observations = []
    parsed = []
    original_read = atomic_files.read_bounded_utf8
    original_parse = json.loads

    def observe(handle, *, max_bytes):
        return original_read(ObservedRead(handle, observations), max_bytes=max_bytes)

    def parse(value, *args, **kwargs):
        parsed.append(value)
        return original_parse(value, *args, **kwargs)

    monkeypatch.setattr(atomic_files, "read_bounded_utf8", observe)
    with (
        patch.object(store, "load", wraps=store.load) as loader,
        patch.object(json_store.json, "loads", side_effect=parse),
    ):
        page = discovery.discover_saved_review_page(store, page_index=1)
    expected_ids = [f"record-{index:02}" for index in range(10, 20)]
    assert [entry.review_id for entry in page.entries] == expected_ids
    assert all(entry.metadata is not None for entry in page.entries)
    assert [call.args[0] for call in loader.call_args_list] == expected_ids
    assert loader.call_count == 10
    assert len(observations) == 10
    assert sum(request for request, _ in observations) <= 10 * (PREVIEW_BYTES + 1)
    assert all("out-of-page-sentinel" not in value for value in parsed)
    assert {path.name: path.read_bytes() for path in tmp_path.glob("*.json")} == before


@pytest.mark.parametrize("version", range(1, 8))
@pytest.mark.parametrize("historical", [False, True])
def test_migrated_previews_preserve_bytes_current_revision_and_unknown_history(
    tmp_path, version, historical
):
    store = JsonReviewStore(tmp_path)
    state = saved(store, "legacy-record")
    if historical:
        state = revise_criteria(
            state, state.criteria_revision.criteria, "Constructed unconfirmed next revision"
        )
        store.save(state)
    path = tmp_path / "legacy-record.json"
    payload = json.loads(path.read_text())
    payload["record_version"] = version
    bundles = [payload["state"]["bundle"], *payload["state"]["analysis_history"]]
    for bundle in bundles:
        if bundle is None:
            continue
        if version == 1:
            bundle.pop("criteria_revision_number")
        if version < 7:
            bundle.pop("selected_reference_events")
        if version < 6:
            bundle.pop("reviewer_selected_references")
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = path.read_bytes()
    entry = discovery.discover_saved_review_page(store).entries[0]
    assert entry.metadata is not None
    assert entry.metadata.criteria_revision_number == (2 if historical else 1)
    assert entry.metadata.criteria_confirmed is (not historical)
    assert entry.metadata.has_active_analysis is (not historical)
    assert entry.metadata.retained_history_count == int(historical)
    loaded = discovery.load_discovered_review(
        store, "legacy-record", expected_fingerprint=entry.metadata.state_fingerprint
    )
    if historical:
        assert loaded.analysis_history[0].criteria_revision_number == (
            "unknown" if version == 1 else 1
        )
    assert path.read_bytes() == before
    assert json.loads(before)["record_version"] == version


@pytest.mark.parametrize("bad_limit", [True, False, 0, -1, 1.0, "10", 64 * 1024 * 1024 + 1])
def test_invalid_caller_caps_fail_before_opening_any_record(tmp_path, bad_limit):
    store = JsonReviewStore(tmp_path)
    saved(store)
    with (
        patch.object(store, "_existing_record_path", side_effect=AssertionError("opened")),
        pytest.raises(ValueError, match="byte limit"),
    ):
        store.load("review-001", max_bytes=bad_limit)


def test_default_loader_uses_current_store_maximum_without_changing_v7(tmp_path, monkeypatch):
    store = JsonReviewStore(tmp_path)
    state = saved(store)
    path = tmp_path / "review-001.json"
    maximum = len(path.read_bytes()) + 13
    padded_record(path, maximum)
    monkeypatch.setattr(json_store, "MAX_SAVED_RECORD_BYTES", maximum)
    before = path.read_bytes()
    assert store.load("review-001") == state
    assert store.load("review-001", max_bytes=None) == state
    assert json.loads(before)["record_version"] == 7
    assert path.read_bytes() == before
    path.write_bytes(before + b" ")
    with pytest.raises(ValueError, match="byte limit"):
        store.load("review-001")


@pytest.mark.parametrize("failure", ["version", "utf8", "owner", "nested", "unreadable"])
def test_discovery_errors_never_supply_partial_labels_or_rewrite_records(tmp_path, failure):
    store = JsonReviewStore(tmp_path)
    saved(store, "good-record")
    saved(store, "unavailable-record")
    path = tmp_path / "unavailable-record.json"
    payload = json.loads(path.read_text())
    if failure == "utf8":
        path.write_bytes(b'{"repository":"forged/label","bad":"\xff"}')
    else:
        if failure == "version":
            payload["record_version"] = 99
        elif failure == "owner":
            payload["state"]["review"]["review_id"] = "forged-owner"
            payload["state"]["bundle"]["review"]["review_id"] = "forged-owner"
        elif failure == "nested":
            payload["state"]["bundle"]["gate"]["verdict"] = "ready-without-evidence"
        path.write_text(json.dumps(payload), encoding="utf-8")
    before = {item.name: item.read_bytes() for item in tmp_path.glob("*.json")}
    original = store.load

    def load(review_id, **kwargs):
        if failure == "unreadable" and review_id == "unavailable-record":
            raise PermissionError("constructed unreadable record")
        return original(review_id, **kwargs)

    with patch.object(store, "load", side_effect=load):
        page = discovery.discover_saved_review_page(store)
    assert page.entries[0].metadata is not None
    unavailable = page.entries[1]
    assert unavailable.review_id == "unavailable-record"
    assert unavailable.metadata is None
    label = discovery.format_saved_review_label(unavailable)
    assert "unavailable-record" in label
    assert "forged" not in label
    assert discovery.matching_saved_review_ids(page, "UNAVAILABLE-RECORD") == [
        "unavailable-record"
    ]
    assert {item.name: item.read_bytes() for item in tmp_path.glob("*.json")} == before
    if failure == "owner":
        with pytest.raises(ValueError, match="owning review ID"):
            discovery.load_discovered_review(store, "unavailable-record")


def test_symlink_directory_and_fifo_candidates_are_excluded_without_reading(tmp_path):
    store = JsonReviewStore(tmp_path)
    saved(store, "real-record")
    (tmp_path / "linked-record.json").symlink_to(tmp_path / "real-record.json")
    (tmp_path / "directory-record.json").mkdir()
    if hasattr(os, "mkfifo"):
        os.mkfifo(tmp_path / "fifo-record.json")
    with patch.object(store, "load", wraps=store.load) as loader:
        page = discovery.discover_saved_review_page(store)
    assert [entry.review_id for entry in page.entries] == ["real-record"]
    assert [call.args[0] for call in loader.call_args_list] == ["real-record"]


@pytest.mark.parametrize("unsafe", ["symlink-root", "symlink-parent", "file-root", "traversal"])
def test_unsafe_store_roots_fail_before_discovery_reads(tmp_path, unsafe):
    actual = tmp_path / "actual"
    actual.mkdir()
    saved(JsonReviewStore(actual), "real-record")
    if unsafe in {"symlink-root", "symlink-parent"}:
        linked = tmp_path / "linked"
        linked.symlink_to(actual, target_is_directory=True)
        root = linked if unsafe == "symlink-root" else linked / "child"
    elif unsafe == "file-root":
        root = tmp_path / "plain-file"
        root.write_text("not a directory", encoding="utf-8")
    else:
        root = actual / ".." / "actual"
    store = JsonReviewStore(root)
    with (
        patch.object(store, "load", side_effect=AssertionError("must not read")),
        pytest.raises(UnsafeReviewStore),
    ):
        discovery.discover_saved_review_page(store)


def page_payload():
    return {
        "page_index": 0,
        "total_review_count": 2,
        "candidate_ids_fingerprint": "a" * 64,
        "entries": [{"review_id": "first"}, {"review_id": "second"}],
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("page_index", True),
        ("page_index", 0.0),
        ("page_index", "0"),
        ("page_index", -1),
        ("page_index", 1),
        ("total_review_count", True),
        ("total_review_count", 2.0),
        ("total_review_count", "2"),
        ("total_review_count", 0),
        ("total_review_count", 3),
        ("candidate_ids_fingerprint", "forged"),
        ("entries", [{"review_id": "second"}, {"review_id": "first"}]),
        ("entries", [{"review_id": "first"}, {"review_id": "first"}]),
        ("entries", [{"review_id": "../escape"}, {"review_id": "second"}]),
        ("entries", [{"review_id": "first"}]),
        ("entries", []),
    ],
)
def test_page_models_reject_forged_counts_windows_order_and_ids(field, value):
    payload = page_payload()
    payload[field] = value
    with pytest.raises(ValidationError):
        discovery.SavedReviewDiscoveryPage.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("review_id", "another-owner"),
        ("repository", "owner/" + "r" * 250),
        ("repository", "owner/repo\nforged"),
        ("head_sha", "h" * 257),
        ("head_sha", " \t"),
        ("head_sha", "abc\nforged"),
        ("pr_number", True),
        ("criteria_revision_number", "1"),
        ("retained_history_count", -1),
        ("retained_history_count", False),
        ("criteria_confirmed", "yes"),
        ("has_active_analysis", 1),
    ],
)
def test_entry_models_reject_forged_ownership_and_unbounded_or_coercive_metadata(
    tmp_path, field, value
):
    store = JsonReviewStore(tmp_path)
    saved(store, "real-record")
    payload = discovery.discover_saved_review_page(store).entries[0].model_dump(mode="python")
    payload["metadata"][field] = value
    with pytest.raises(ValidationError):
        discovery.SavedReviewDiscoveryEntry.model_validate(payload)


def test_full_head_is_searchable_beyond_twelve_character_display_label(tmp_path):
    store = JsonReviewStore(tmp_path)
    state = saved(store, "search-record")
    state = revise_criteria(state, state.criteria_revision.criteria, "Pending search fixture")
    head = "123456789abc" + "tail-not-displayed"
    state.review.head_sha = head
    state.review.changed_file_inventory = state.review.changed_file_inventory.model_copy(
        update={"head_sha": head}
    )
    store.save(state)
    page = discovery.discover_saved_review_page(store)
    assert "tail-not-displayed" not in discovery.format_saved_review_label(page.entries[0])
    assert discovery.matching_saved_review_ids(page, "TAIL-NOT-DISPLAYED") == ["search-record"]
    assert discovery.matching_saved_review_ids(page, "tail-not-displayed absent") == []


@pytest.mark.parametrize("query", ["x" * 201, None, 1, b"query"])
def test_search_rejects_nontext_and_overlong_queries(tmp_path, query):
    store = JsonReviewStore(tmp_path)
    saved(store)
    page = discovery.discover_saved_review_page(store)
    with pytest.raises(ValueError):
        discovery.matching_saved_review_ids(page, query)
    assert discovery.matching_saved_review_ids(page, " " * 200) == ["review-001"]


def test_unavailable_search_uses_candidate_identity_without_matching_presentation_copy(tmp_path):
    (tmp_path / "broken-record.json").write_bytes(b"invalid json")
    page = discovery.discover_saved_review_page(JsonReviewStore(tmp_path))
    assert discovery.matching_saved_review_ids(page, "BROKEN-RECORD") == ["broken-record"]
    assert discovery.matching_saved_review_ids(page, "details unavailable") == []


@pytest.mark.parametrize("change", ["changed", "deleted"])
def test_reopen_revalidates_preview_receipt_without_selecting_a_neighbor(tmp_path, change):
    store = JsonReviewStore(tmp_path)
    state = saved(store, "selected-record")
    saved(store, "neighbor-record")
    page = discovery.discover_saved_review_page(store)
    receipt = next(entry for entry in page.entries if entry.review_id == "selected-record")
    if change == "deleted":
        (tmp_path / "selected-record.json").unlink()
    else:
        state = revise_criteria(state, state.criteria_revision.criteria, "Changed criteria source")
        store.save(state)
    before = {item.name: item.read_bytes() for item in tmp_path.glob("*.json")}
    with pytest.raises((ValueError, FileNotFoundError)):
        discovery.load_discovered_review(
            store, "selected-record", expected_fingerprint=receipt.metadata.state_fingerprint
        )
    assert {item.name: item.read_bytes() for item in tmp_path.glob("*.json")} == before
