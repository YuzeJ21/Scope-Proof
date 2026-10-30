"""Historical records acquire no invented audit events and load without rewriting."""

import json

import pytest

from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import Criterion
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_reference_audit import withdraw
from tests.reviews.test_selected_references import append, source_state


def saved(tmp_path, *, historical=False):
    state, snapshot = source_state()
    state = withdraw(append(state, snapshot))
    if historical:
        state = revise_criteria(state, [Criterion(criterion_id="AC-01", text="Revised")], "Revised")
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    payload = json.loads(path.read_text())
    bundle = payload["state"]["analysis_history"][0] if historical else payload["state"]["bundle"]
    return state, store, path, payload, bundle


@pytest.mark.parametrize("historical", [False, True])
def test_v7_roundtrip_retains_audit_without_rewriting(tmp_path, historical):
    state, store, path, payload, _ = saved(tmp_path, historical=historical)
    assert payload["record_version"] == 7
    before = path.read_bytes()
    assert store.load(state.review.review_id) == state
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5, 6])
@pytest.mark.parametrize("historical", [False, True])
@pytest.mark.parametrize("value", [None, {}, "forged", [{"reason": "invented"}]])
def test_pre_v7_rejects_malformed_or_nonempty_events(tmp_path, version, historical, value):
    state, store, path, payload, bundle = saved(tmp_path, historical=historical)
    payload["record_version"] = version
    bundle["reviewer_selected_references"] = []
    bundle["selected_reference_events"] = value
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    with pytest.raises(ValueError, match=r"version 7|reference audit"):
        store.load(state.review.review_id)
    assert path.read_bytes() == before


@pytest.mark.parametrize("historical", [False, True])
def test_v6_keeps_references_but_invents_no_events(tmp_path, historical):
    state, store, path, payload, bundle = saved(tmp_path, historical=historical)
    payload["record_version"] = 6
    bundle.pop("selected_reference_events")
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    loaded = store.load(state.review.review_id)
    restored = loaded.analysis_history[0] if historical else loaded.bundle
    assert restored.selected_reference_events == []
    assert restored.active_reviewer_selected_reference_ids == [
        r.reference_id for r in restored.reviewer_selected_references
    ]
    assert path.read_bytes() == before


@pytest.mark.parametrize("historical", [False, True])
def test_v7_missing_eventlist_cannot_reactivate_a_reference(tmp_path, historical):
    state, store, path, payload, bundle = saved(tmp_path, historical=historical)
    payload["record_version"] = 7
    bundle.pop("selected_reference_events")
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="reference audit"):
        store.load(state.review.review_id)
