"""Version-six records retain only attributable non-gating selected references."""

from __future__ import annotations

import json
from importlib import import_module

import pytest

from scopeproof_core.demo import build_demo_review, load_demo_snapshot
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import Criterion
from scopeproof_core.storage.json_store import JsonReviewStore


def state_with_reference():
    module = import_module("scopeproof_core.reviews.selected_references")
    state = new_review_state(build_demo_review())
    snapshot = load_demo_snapshot()
    return module.append_reviewer_selected_reference(
        state,
        snapshot=snapshot,
        selected=module.selectable_reference_lines(state, snapshot)[0],
        criterion_id=state.criteria_revision.criteria[0].criterion_id,
        reviewer="Constructed fixture reviewer",
        rationale="Explicit fixture mapping",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
    )


def test_selected_reference_round_trips_without_source_snapshot_or_truth_upgrade(tmp_path):
    state = state_with_reference()
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    payload = json.loads(path.read_text())
    assert payload["record_version"] == 7
    assert store.load(state.review.review_id) == state
    assert "snapshot" not in payload["state"]
    reference = payload["state"]["bundle"]["reviewer_selected_references"][0]
    assert reference["reviewer"] == "Constructed fixture reviewer"
    assert reference["rationale"] == "Explicit fixture mapping"


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("value", [None, {}, "forged", [{"reviewer": "invented"}]])
@pytest.mark.parametrize("historical", [False, True])
def test_pre_v6_rejects_nonempty_or_malformed_attribution(version, value, historical, tmp_path):
    state = new_review_state(build_demo_review())
    if historical:
        state = revise_criteria(state, [Criterion(criterion_id="AC-01", text="Changed")], "Changed")
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    payload = json.loads(path.read_text())
    payload["record_version"] = version
    bundle = payload["state"]["analysis_history"][0] if historical else payload["state"]["bundle"]
    bundle["reviewer_selected_references"] = value
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    with pytest.raises(ValueError, match=r"selected.reference|version 6"):
        store.load(state.review.review_id)
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("empty_field", [False, True])
def test_pre_v6_empty_records_migrate_without_inventing_attribution(version, empty_field, tmp_path):
    state = new_review_state(build_demo_review())
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    payload = json.loads(path.read_text())
    payload["record_version"] = version
    if not empty_field:
        payload["state"]["bundle"].pop("reviewer_selected_references", None)
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    loaded = store.load(state.review.review_id)
    assert loaded.bundle.reviewer_selected_references == []
    if version < 5:
        assert loaded.review.changed_file_inventory is None
    else:
        assert loaded.review.changed_file_inventory == state.review.changed_file_inventory
    assert path.read_bytes() == before


def test_selected_reference_history_survives_saved_revision_without_rebinding(tmp_path):
    state = state_with_reference()
    reference = state.bundle.reviewer_selected_references[0]
    revised = revise_criteria(state, [Criterion(criterion_id="AC-01", text="Changed")], "Changed")
    store = JsonReviewStore(tmp_path)
    path = store.save(revised)
    loaded = store.load(state.review.review_id)
    assert loaded.bundle is None
    assert loaded.analysis_history[0].reviewer_selected_references == [reference]
    assert loaded.analysis_history[0].reviewer_selected_references[0].criteria_revision_number == 1
    assert json.loads(path.read_text())["record_version"] == 7


def test_downgraded_selected_reference_records_fail_closed_instead_of_losing_attribution(tmp_path):
    state = state_with_reference()
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    payload = json.loads(path.read_text())
    payload["record_version"] = 5
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match=r"selected.reference|version 6"):
        store.load(state.review.review_id)
