from __future__ import annotations

import json
from pathlib import Path

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import export_html, export_markdown
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import (
    GateVerdict,
    HumanDecision,
    HumanResolution,
    PullRequestSnapshot,
)
from scopeproof_core.storage.json_store import (
    JsonReviewStore,
    UnsafeReviewStore,
    UnsupportedRecordVersion,
    default_local_review_directory,
)


def review_state():
    bundle = build_demo_review()
    bundle.review.review_id = "review-1"
    return new_review_state(bundle)


def test_saved_review_round_trips_without_token(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()

    path = store.save(state)
    loaded = store.load("review-1")

    assert path.name == "review-1.json"
    assert loaded.model_dump(mode="json") == state.model_dump(mode="json")
    assert "ghp_" not in path.read_text(encoding="utf-8")
    assert "authorization" not in path.read_text(encoding="utf-8").lower()


def test_historical_review_state_loads_without_ingestion_limitation_fields(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    for review in (
        payload["state"]["review"],
        payload["state"]["bundle"]["review"],
    ):
        review.pop("ingestion_warnings", None)
        review.pop("skipped_files", None)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load("review-1")

    assert loaded.review.ingestion_warnings == []
    assert loaded.review.skipped_files == []
    assert loaded.bundle is not None
    assert loaded.bundle.review.ingestion_warnings == []
    assert loaded.bundle.review.skipped_files == []


def test_load_rejects_mismatched_active_bundle_review(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["review"]["head_sha"] = "different-head"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match="active bundle review must match lifecycle review"
    ):
        store.load("review-1")


def test_save_revalidates_mismatched_active_bundle_review(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    divergent = state.model_copy(
        update={
            "review": state.review.model_copy(update={"head_sha": "different-head"})
        }
    )

    with pytest.raises(
        ValueError, match="active bundle review must match lifecycle review"
    ):
        store.save(divergent)

    assert list(tmp_path.iterdir()) == []


def test_save_rejects_a_non_deterministic_active_gate(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    assert state.bundle is not None
    state.bundle.gate = state.bundle.gate.model_copy(update={"verdict": GateVerdict.READY})

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        store.save(state)

    assert list(tmp_path.iterdir()) == []


def test_load_rejects_a_non_deterministic_active_gate(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["bundle"]["gate"]["verdict"] = GateVerdict.READY.value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        store.load("review-1")


def test_save_rejects_forged_ready_state_without_resolution_events(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()
    assert state.bundle is not None
    state.review.final_acceptance = True
    state.bundle.review.final_acceptance = True
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Forged acceptance",
        )
        for criterion in state.bundle.criteria
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )
    assert state.bundle.gate.verdict is GateVerdict.READY
    assert state.resolution_events == []

    with pytest.raises(
        ValueError, match="active bundle resolutions must match active resolution events"
    ):
        store.save(state)

    assert list(tmp_path.iterdir()) == []


def test_version_one_record_with_legacy_permalink_loads_and_exports_inertly(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    legacy_permalink = "javascript:alert(1)"
    payload["state"]["bundle"]["evidence"][0]["permalink"] = legacy_permalink
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load("review-1")

    assert loaded.bundle is not None
    assert loaded.bundle.evidence[0].permalink == legacy_permalink
    assert f"]({legacy_permalink})" not in export_markdown(loaded)
    assert f'href="{legacy_permalink}"' not in export_html(loaded)


def test_list_review_ids_returns_empty_when_store_does_not_exist(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path / "reviews")

    assert store.list_review_ids() == []


def test_list_review_ids_is_sorted_bounded_and_does_not_parse_records(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    (tmp_path / "z-review.json").write_text("not parsed during discovery", encoding="utf-8")
    (tmp_path / "a-review.json").write_text("{}", encoding="utf-8")
    (tmp_path / "bad id.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("{}", encoding="utf-8")
    (tmp_path / "directory.json").mkdir()
    (tmp_path / "linked-review.json").symlink_to(tmp_path / "a-review.json")

    assert store.list_review_ids() == ["a-review", "z-review"]


def test_list_review_ids_rejects_a_symlinked_store_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "outside-review.json").write_text("{}", encoding="utf-8")
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).list_review_ids()


def test_load_rejects_a_symlinked_store_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_store = JsonReviewStore(outside)
    outside_store.save(review_state())
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).load("review-1")


def test_save_rejects_a_symlinked_store_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).save(review_state())

    assert list(outside.iterdir()) == []


def test_list_review_ids_rejects_a_regular_file_store_root(tmp_path: Path) -> None:
    store_root = tmp_path / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(UnsafeReviewStore, match="review store path must be a directory"):
        JsonReviewStore(store_root).list_review_ids()


def test_load_rejects_a_regular_file_store_root(tmp_path: Path) -> None:
    store_root = tmp_path / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(UnsafeReviewStore, match="review store path must be a directory"):
        JsonReviewStore(store_root).load("review-1")


def test_save_rejects_a_regular_file_store_root(tmp_path: Path) -> None:
    store_root = tmp_path / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(UnsafeReviewStore, match="review store path must be a directory"):
        JsonReviewStore(store_root).save(review_state())

    assert store_root.read_text(encoding="utf-8") == "not a directory"


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


def test_load_rejects_a_review_record_symlink_that_escapes_the_store(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    saved_path = store.save(review_state())
    outside_record = tmp_path.parent / "outside-review.json"
    outside_record.write_text(saved_path.read_text(encoding="utf-8"), encoding="utf-8")
    saved_path.unlink()
    saved_path.symlink_to(outside_record)

    with pytest.raises(FileNotFoundError):
        store.load("review-1")
