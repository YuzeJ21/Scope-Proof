"""Saved comparison is explicit, read-only and bound to both complete records."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib import import_module
from pathlib import Path
from threading import Event

import pytest
from pydantic import ValidationError

from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.schemas.models import HumanDecision, Priority, ResolutionEvent, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_scope_comparison import NEW, OLD, scoped_bundle


def api():
    return import_module("scopeproof_core.reviews.saved_comparison")


def saved_pair(tmp_path: Path) -> tuple[JsonReviewStore, ReviewState, ReviewState]:
    store = JsonReviewStore(tmp_path)
    previous = new_review_state(scoped_bundle(OLD))
    current = new_review_state(scoped_bundle(NEW, "src/unrelated.py"))
    historical = previous.bundle.model_copy(deep=True)
    historical.review.review_id = current.review.review_id
    current.criteria_revision.number = 2
    current.bundle.criteria_revision_number = 2
    current.analysis_history = [historical]
    current = ReviewState.model_validate(current.model_dump(mode="python"))
    store.save(previous)
    store.save(current)
    return store, previous, current


def record_bytes(store: JsonReviewStore) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in store.directory.glob("*.json")}


@pytest.mark.parametrize("use_history", [False, True])
def test_prepare_and_load_saved_baseline_preserve_bytes_and_current_decisions(
    tmp_path: Path,
    use_history: bool,
) -> None:
    store, previous, current = saved_pair(tmp_path)
    before = record_bytes(store)
    selection = api().prepare_saved_comparison(
        store,
        current,
        current.review.review_id if use_history else previous.review.review_id,
        history_index=0 if use_history else None,
    )
    with api().locked_saved_comparison(store, selection) as comparison:
        assert comparison.previous_head_sha == OLD
        assert comparison.current_head_sha == NEW
        assert comparison.file_scope.current.unresolved_paths == ["src/unrelated.py"]
    assert record_bytes(store) == before
    assert current.bundle.resolutions == []
    assert not current.review.final_acceptance


@pytest.mark.parametrize("side", ["baseline", "current"])
def test_changed_record_expires_saved_comparison(tmp_path: Path, side: str) -> None:
    store, previous, current = saved_pair(tmp_path)
    selection = api().prepare_saved_comparison(store, current, previous.review.review_id)
    target = previous if side == "baseline" else current
    store.mutate(
        target.review.review_id,
        lambda state: append_resolution(
            state,
            ResolutionEvent(
                criterion_id="AC-01",
                decision=HumanDecision.REJECTED_FINDING,
                reviewer="Constructed reviewer",
                comment="Changed saved decision",
            ),
        ),
    )
    before = record_bytes(store)
    with (
        pytest.raises(api().SavedComparisonUnavailable),
        api().locked_saved_comparison(store, selection),
    ):
        pytest.fail("stale comparison yielded a result")
    assert record_bytes(store) == before


@pytest.mark.parametrize("damage", ["delete", "corrupt", "unsupported"])
def test_unavailable_baseline_rejects_without_changing_current(tmp_path: Path, damage: str) -> None:
    store, previous, current = saved_pair(tmp_path)
    selection = api().prepare_saved_comparison(store, current, previous.review.review_id)
    path = store.directory / f"{previous.review.review_id}.json"
    if damage == "delete":
        path.unlink()  # Simulate external removal; app deletion is platform-dependent.
    elif damage == "corrupt":
        path.write_text("broken", encoding="utf-8")
    else:
        path.write_text('{"record_version":999,"state":{}}', encoding="utf-8")
    before = record_bytes(store)
    with pytest.raises((OSError, ValueError)), api().locked_saved_comparison(store, selection):
        pytest.fail("unavailable comparison yielded a result")
    assert record_bytes(store) == before


def test_unsaved_current_cannot_be_used_as_saved_comparison(tmp_path: Path) -> None:
    store, previous, current = saved_pair(tmp_path)
    current = append_resolution(
        current,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.REJECTED_FINDING,
            comment="Unsaved decision",
            reviewer="Constructed reviewer",
        ),
    )
    before = record_bytes(store)
    with pytest.raises(api().SavedComparisonUnavailable):
        api().prepare_saved_comparison(store, current, previous.review.review_id)
    assert record_bytes(store) == before


def test_replaced_history_cannot_silently_retarget_selected_index(tmp_path: Path) -> None:
    store, _, current = saved_pair(tmp_path)
    selection = api().prepare_saved_comparison(
        store,
        current,
        current.review.review_id,
        history_index=0,
    )
    original_created_at = current.analysis_history[0].review.created_at
    current.analysis_history[0].review.created_at = original_created_at + timedelta(seconds=1)
    assert current.analysis_history[0].review.created_at != original_created_at
    store.save(current)
    with (
        pytest.raises(api().SavedComparisonUnavailable),
        api().locked_saved_comparison(store, selection),
    ):
        pytest.fail("replaced history was accepted")


@pytest.mark.parametrize("history_index", [-1, 2, True])
def test_invalid_history_selection_rejects(tmp_path: Path, history_index: int) -> None:
    store, _, current = saved_pair(tmp_path)
    with pytest.raises((ValueError, ValidationError)):
        api().prepare_saved_comparison(
            store,
            current,
            current.review.review_id,
            history_index=history_index,
        )


def test_unknown_history_revision_and_inventory_remain_unknown(tmp_path: Path) -> None:
    store, _, current = saved_pair(tmp_path)
    old = current.analysis_history[0]
    old.criteria_revision_number = "unknown"
    old.review.changed_file_inventory = None
    from tests.reviews.test_scope_comparison import revalidated

    current.analysis_history = [revalidated(old)]
    store.save(current)
    selection = api().prepare_saved_comparison(
        store,
        current,
        current.review.review_id,
        history_index=0,
    )
    with api().locked_saved_comparison(store, selection) as comparison:
        assert comparison.file_scope.previous.criteria_revision_number == "unknown"
        assert comparison.file_scope.inventory_changes is None


@pytest.mark.parametrize("side", ["baseline", "current"])
def test_missing_active_analysis_rejects(tmp_path: Path, side: str) -> None:
    store, previous, current = saved_pair(tmp_path)
    target = current if side == "current" else previous
    target.bundle = None
    store.save(target)
    with pytest.raises(ValueError, match="active analysis"):
        api().prepare_saved_comparison(store, current, previous.review.review_id)


@pytest.mark.parametrize("difference", ["pr", "criteria", "source"])
def test_incompatible_saved_baseline_rejects(tmp_path: Path, difference: str) -> None:
    store, previous, current = saved_pair(tmp_path)
    if difference == "pr":
        previous.review.pr_number = 2
        previous.bundle.review.pr_number = 2
    elif difference == "criteria":
        previous.criteria_revision.criteria[0].priority = Priority.SHOULD_HAVE
        previous.bundle.criteria[0].priority = Priority.SHOULD_HAVE
        # Use another valid analysis rather than forging contradictory provenance.
        from scopeproof_core.criteria.confirmation import build_criteria_source_provenance

        provenance = build_criteria_source_provenance(
            source_uri="https://example.test/requirements",
            source_text=previous.bundle.source_text,
            criteria=previous.bundle.criteria,
            confirmed_by="Constructed confirmer",
            confirmed_at=previous.review.created_at,
        )
        previous.review.criteria_source_provenance = provenance
        previous.bundle.review.criteria_source_provenance = provenance
        previous.criteria_revision.source_provenance = provenance
    else:
        provenance = previous.review.criteria_source_provenance.model_copy(
            update={"source_uri": "https://example.test/other-requirements"},
        )
        previous.review.criteria_source_provenance = provenance
        previous.bundle.review.criteria_source_provenance = provenance
        previous.criteria_revision.source_provenance = provenance
    from tests.reviews.test_scope_comparison import revalidated

    previous.bundle = revalidated(previous.bundle)
    store.save(previous)
    before = record_bytes(store)
    with pytest.raises(ValueError):
        api().prepare_saved_comparison(store, current, previous.review.review_id)
    assert record_bytes(store) == before


@pytest.mark.parametrize("side", ["baseline", "current"])
def test_saved_comparison_holds_both_records_through_rendering(tmp_path: Path, side: str) -> None:
    store, previous, current = saved_pair(tmp_path)
    selection = api().prepare_saved_comparison(store, current, previous.review.review_id)
    entered, release, mutation_started, mutation_done = Event(), Event(), Event(), Event()

    def render() -> str:
        with api().locked_saved_comparison(store, selection) as comparison:
            entered.set()
            assert release.wait(3)
            return comparison.current_head_sha

    def mutate() -> None:
        mutation_started.set()
        store.mutate(
            current.review.review_id if side == "current" else previous.review.review_id,
            lambda state: append_resolution(
                state,
                ResolutionEvent(
                    criterion_id="AC-01",
                    decision=HumanDecision.REJECTED_FINDING,
                    reviewer="Constructed reviewer",
                    comment="Concurrent change",
                ),
            ),
        )
        mutation_done.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        rendered = pool.submit(render)
        assert entered.wait(3)
        changed = pool.submit(mutate)
        try:
            assert mutation_started.wait(3)
            assert not mutation_done.wait(0.1)
        finally:
            release.set()
        assert rendered.result(3) == NEW
        changed.result(3)
