from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

import scopeproof_core.storage.json_store as json_store_module
from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import export_html, export_markdown
from scopeproof_core.reviews.lifecycle import (
    attach_analysis,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
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

_MISSING_RECORD_VERSION = object()


def review_state(review_id: str = "review-1"):
    bundle = build_demo_review()
    bundle.review.review_id = review_id
    return new_review_state(bundle)


def attached_review_state():
    state = new_review_state(build_demo_review())
    updated_criteria = [
        item.model_copy(deep=True) for item in state.criteria_revision.criteria
    ]
    updated_criteria[0] = updated_criteria[0].model_copy(
        update={"text": "Updated AC-01 requirement"}
    )
    revised = confirm_criteria(
        revise_criteria(
            state,
            updated_criteria,
            "Updated requirements",
        )
    )
    incoming = build_demo_review()
    incoming.review = incoming.review.model_copy(
        update={
            "repository": revised.review.repository,
            "pr_number": revised.review.pr_number,
            "base_sha": revised.review.base_sha,
            "head_sha": revised.review.head_sha,
            "check_state": revised.review.check_state,
            "criteria_confirmed": True,
            "ingestion_state": revised.review.ingestion_state,
            "ingestion_warnings": revised.review.ingestion_warnings,
            "skipped_files": revised.review.skipped_files,
            "tool_version": revised.review.tool_version,
            "ruleset_version": revised.review.ruleset_version,
        }
    )
    incoming.source_text = revised.criteria_revision.source_text
    incoming.criteria = [
        item.model_copy(deep=True) for item in revised.criteria_revision.criteria
    ]
    return attach_analysis(revised, incoming)


def downgrade_to_version_one(payload: dict) -> dict:
    payload["record_version"] = 1
    if payload["state"]["bundle"] is not None:
        payload["state"]["bundle"].pop("criteria_revision_number")
    for historical_bundle in payload["state"]["analysis_history"]:
        historical_bundle.pop("criteria_revision_number")
    return payload


def test_saved_review_round_trips_without_token(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    state = review_state()

    path = store.save(state)
    loaded = store.load("review-1")

    assert path.name == "review-1.json"
    assert loaded.model_dump(mode="json") == state.model_dump(mode="json")
    assert "ghp_" not in path.read_text(encoding="utf-8")
    assert "authorization" not in path.read_text(encoding="utf-8").lower()


def test_attached_analysis_round_trip_preserves_reanalysis_lineage(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    attached = attached_review_state()
    original = build_demo_review()
    stable_review_id = attached.review.review_id

    store.save(attached)
    loaded = store.load(stable_review_id)

    assert loaded == attached
    assert loaded.criteria_revision.number == 2
    assert len(loaded.analysis_history) == 1
    assert loaded.review.review_id == stable_review_id
    assert loaded.bundle is not None
    assert loaded.bundle.review.review_id == stable_review_id
    assert loaded.bundle.source_text == "Updated requirements"
    assert loaded.bundle.criteria == loaded.criteria_revision.criteria
    historical = loaded.analysis_history[0]
    assert historical.source_text == original.source_text
    assert historical.criteria == original.criteria
    assert historical.source_text != loaded.bundle.source_text
    assert historical.criteria != loaded.bundle.criteria


def test_new_save_writes_version_two_with_exact_analysis_lineage(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()

    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["record_version"] == 2
    assert payload["state"]["bundle"]["criteria_revision_number"] == 2
    assert [
        bundle["criteria_revision_number"]
        for bundle in payload["state"]["analysis_history"]
    ] == [1]


def test_version_one_record_migrates_active_revision_and_unknown_history(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    payload["state"]["analysis_history"].append(
        json.loads(json.dumps(payload["state"]["analysis_history"][0]))
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(state.review.review_id)

    assert loaded.bundle is not None
    assert loaded.bundle.criteria_revision_number == 2
    assert [
        bundle.criteria_revision_number for bundle in loaded.analysis_history
    ] == ["unknown", "unknown"]


def test_saving_migrated_version_one_state_preserves_unknown_history(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    migrated = store.load(state.review.review_id)
    migrated_path = store.save(migrated)
    migrated_payload = json.loads(migrated_path.read_text(encoding="utf-8"))

    assert migrated_payload["record_version"] == 2
    assert migrated_payload["state"]["bundle"]["criteria_revision_number"] == 2
    assert [
        bundle["criteria_revision_number"]
        for bundle in migrated_payload["state"]["analysis_history"]
    ] == ["unknown"]


def test_bundleless_version_one_record_preserves_unknown_history(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    pending = revise_criteria(
        review_state(),
        review_state().criteria_revision.criteria,
        "Updated requirements",
    )
    path = store.save(pending)
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.load(pending.review.review_id)

    assert loaded.bundle is None
    assert [
        bundle.criteria_revision_number for bundle in loaded.analysis_history
    ] == ["unknown"]


def test_version_one_migration_does_not_mutate_parsed_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    legacy_payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    original_payload = json.loads(json.dumps(legacy_payload))
    monkeypatch.setattr(
        "scopeproof_core.storage.json_store.json.loads",
        lambda _: legacy_payload,
    )

    store.load(state.review.review_id)

    assert legacy_payload == original_payload


def test_malformed_version_one_nested_content_is_rejected_by_pydantic(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    payload["state"]["bundle"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        store.load("review-1")


def test_version_one_migration_rejects_non_deterministic_gate(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = downgrade_to_version_one(
        json.loads(path.read_text(encoding="utf-8"))
    )
    payload["state"]["bundle"]["gate"]["verdict"] = GateVerdict.READY.value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        store.load("review-1")


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


def test_save_rejects_foreign_historical_review_lineage(tmp_path: Path) -> None:
    state = review_state()
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.analysis_history[0].review.repository = "other/repository"

    with pytest.raises(
        ValueError,
        match="historical bundle review lineage must match lifecycle review",
    ):
        JsonReviewStore(tmp_path).save(revised)

    assert list(tmp_path.iterdir()) == []


def test_version_one_record_with_legacy_permalink_loads_and_exports_inertly(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    legacy_permalink = "javascript:alert(1)"
    payload["state"]["bundle"]["evidence"][0]["permalink"] = legacy_permalink
    downgrade_to_version_one(payload)
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


def test_delete_removes_only_the_exact_review_and_preserves_its_neighbor(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    first_state = review_state("review-1")
    second_state = review_state("review-2")
    store.save(first_state)
    store.save(second_state)

    store.delete("review-1")

    assert not (tmp_path / "review-1.json").exists()
    assert store.load("review-2") == second_state


def test_delete_removes_a_corrupt_regular_record_without_parsing_it(
    tmp_path: Path,
) -> None:
    corrupt_record = tmp_path / "corrupt.json"
    corrupt_record.write_text("not valid JSON", encoding="utf-8")

    JsonReviewStore(tmp_path).delete("corrupt")

    assert not corrupt_record.exists()


def test_delete_pins_store_directory_when_root_is_replaced_at_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_root = tmp_path / "reviews"
    store = JsonReviewStore(store_root)
    target = store.save(review_state("review-1"))
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()
    opened_store_root = tmp_path / "opened-reviews"
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_target = outside / target.name
    outside_target.write_text("keep external", encoding="utf-8")
    real_unlink = os.unlink
    root_replaced = False

    def replace_root_then_unlink(path, *args, **kwargs):
        nonlocal root_replaced
        if not root_replaced:
            store_root.rename(opened_store_root)
            store_root.symlink_to(outside, target_is_directory=True)
            root_replaced = True
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", replace_root_then_unlink)

    store.delete("review-1")

    assert root_replaced is True
    assert outside_target.read_text(encoding="utf-8") == "keep external"
    assert not (opened_store_root / target.name).exists()
    assert (opened_store_root / neighbor.name).read_bytes() == neighbor_contents


def test_delete_fails_closed_when_safe_directory_descriptor_operations_are_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = JsonReviewStore(tmp_path)
    target = store.save(review_state("review-1"))
    monkeypatch.setattr(
        json_store_module, "_SAFE_DIRECTORY_DESCRIPTOR_DELETE_SUPPORTED", False
    )

    with pytest.raises(OSError, match="safe local review deletion is unsupported"):
        store.delete("review-1")

    assert target.exists()


@pytest.mark.parametrize("review_id", ["../review-1", "review-1.json", "/tmp/review-1"])
def test_delete_rejects_invalid_review_ids_without_changing_any_files(
    review_id: str,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    first_path = store.save(review_state("review-1"))
    second_path = store.save(review_state("review-2"))
    before = {path.name: path.read_bytes() for path in (first_path, second_path)}

    with pytest.raises(ValueError):
        store.delete(review_id)

    assert {path.name: path.read_bytes() for path in (first_path, second_path)} == before


def test_delete_missing_record_raises_without_changing_its_neighbor(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()

    with pytest.raises(FileNotFoundError):
        store.delete("missing")

    assert neighbor.read_bytes() == neighbor_contents


def test_delete_rejects_a_symlinked_store_root_without_changing_external_files(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_store = JsonReviewStore(outside)
    target = outside_store.save(review_state("review-1"))
    neighbor = outside_store.save(review_state("review-2"))
    external = outside / "external.txt"
    external.write_text("keep external", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in (target, neighbor, external)}
    store_root = tmp_path / "reviews"
    store_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeReviewStore, match="store directory must not be a symbolic link"):
        JsonReviewStore(store_root).delete("review-1")

    assert store_root.is_symlink()
    assert {path.name: path.read_bytes() for path in (target, neighbor, external)} == before


def test_delete_rejects_a_record_symlink_without_changing_any_files(
    tmp_path: Path,
) -> None:
    store_root = tmp_path / "reviews"
    store_root.mkdir()
    store = JsonReviewStore(store_root)
    external = tmp_path / "external-review.json"
    external.write_text("keep external", encoding="utf-8")
    target = store_root / "review-1.json"
    target.symlink_to(external)
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()

    with pytest.raises(FileNotFoundError):
        store.delete("review-1")

    assert target.is_symlink()
    assert neighbor.read_bytes() == neighbor_contents
    assert external.read_text(encoding="utf-8") == "keep external"


def test_delete_rejects_a_directory_named_like_a_record_without_changing_files(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    target = tmp_path / "review-1.json"
    target.mkdir()
    external = target / "external.txt"
    external.write_text("keep external", encoding="utf-8")
    neighbor = store.save(review_state("review-2"))
    neighbor_contents = neighbor.read_bytes()

    with pytest.raises(FileNotFoundError):
        store.delete("review-1")

    assert target.is_dir()
    assert neighbor.read_bytes() == neighbor_contents
    assert external.read_text(encoding="utf-8") == "keep external"


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


@pytest.mark.parametrize(
    "record_version",
    [
        pytest.param(999, id="unknown-integer"),
        pytest.param(True, id="true"),
        pytest.param(False, id="false"),
        pytest.param(1.0, id="float-one"),
        pytest.param(2.0, id="float-two"),
        pytest.param("1", id="string-one"),
        pytest.param("2", id="string-two"),
        pytest.param(None, id="null"),
        pytest.param(_MISSING_RECORD_VERSION, id="missing"),
    ],
)
def test_unsupported_or_coercive_record_version_is_rejected(
    record_version: object,
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    if record_version is _MISSING_RECORD_VERSION:
        payload.pop("record_version")
    else:
        payload["record_version"] = record_version
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
