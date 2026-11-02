"""Independent historical-version and atomic-save checks for mapping corrections."""

import json
from datetime import UTC, datetime
from importlib import import_module

import pytest

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.junit_audit import withdraw_junit_evidence_import
from scopeproof_core.schemas.models import JUnitCriterionMapping, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore, StaleReviewState
from tests.junit_audit_fixture import junit_audit_state

IMPORT_ID = "constructed-junit-import"


def correction_api():
    try:
        return import_module("scopeproof_core.reviews.junit_correction")
    except ModuleNotFoundError as error:
        if error.name != "scopeproof_core.reviews.junit_correction":
            raise
        pytest.fail("saved JUnit mapping correction is not implemented", pytrace=False)


def correct(state):
    return correction_api().correct_junit_mappings(
        state,
        import_id=IMPORT_ID,
        criterion_mappings=[
            JUnitCriterionMapping(
                criterion_id="AC-02",
                test_case_ids=["suite-0001-case-0001", "suite-0001-case-0002"],
            )
        ],
        reviewer="CONSTRUCTED migration actor",
        reason="CONSTRUCTED grouping correction",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        confirm_whole_import=True,
        occurred_at=datetime(2026, 11, 1, 14, tzinfo=UTC),
    )


def with_history(state):
    payload = state.model_dump(mode="python")
    payload["analysis_history"] = [state.bundle.model_dump(mode="python")]
    payload["criteria_revision"]["number"] = 2
    payload["bundle"]["criteria_revision_number"] = 2
    for imported in payload["bundle"]["junit_evidence_imports"]:
        imported["criteria_revision_number"] = 2
    for event in payload["bundle"]["junit_import_events"]:
        event["criteria_revision_number"] = 2
    return validated_review_state(ReviewState.model_validate(payload))


def envelope(state, version):
    return {"record_version": version, "state": state.model_dump(mode="json")}


def write_payload(tmp_path, payload):
    path = tmp_path / f"{payload['state']['review']['review_id']}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def bundles(payload):
    return [payload["state"]["bundle"], *payload["state"]["analysis_history"]]


@pytest.mark.parametrize("location", ["active", "history"])
@pytest.mark.parametrize("missing_tags", [
    ("action",), ("schema_version",), ("action", "schema_version"),
])
def test_v8_rejects_correction_shape_even_when_type_tags_are_missing(
    tmp_path, location, missing_tags,
):
    state = with_history(correct(junit_audit_state()))
    payload = envelope(state, 8)
    active, history = bundles(payload)
    target, other = (active, history) if location == "active" else (history, active)
    other["junit_import_events"] = []
    for field in missing_tags:
        target["junit_import_events"][0].pop(field)
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        JsonReviewStore(tmp_path).load(state.review.review_id)
    assert path.read_bytes() == before


@pytest.mark.parametrize("action", ["withdrawal", "correction"])
@pytest.mark.parametrize("location", ["active", "history"])
def test_missing_tags_keep_withdrawal_v8_and_correction_v9_default_compatibility(
    tmp_path, action, location,
):
    state = junit_audit_state()
    if action == "withdrawal":
        state = withdraw_junit_evidence_import(
            state, import_id=IMPORT_ID, reviewer="CONSTRUCTED compatibility actor",
            reason="CONSTRUCTED terminal withdrawal",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        )
    else:
        state = correct(state)
    state = with_history(state)
    payload = envelope(state, 8 if action == "withdrawal" else 9)
    active, history = bundles(payload)
    target = active if location == "active" else history
    target["junit_import_events"][0].pop("action")
    target["junit_import_events"][0].pop("schema_version")
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    loaded = JsonReviewStore(tmp_path).load(state.review.review_id)
    assert loaded.model_dump(mode="json") == state.model_dump(mode="json")
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", range(1, 9))
@pytest.mark.parametrize("events", ["absent", "empty"])
def test_old_records_load_without_invented_corrections_or_load_time_write(
    tmp_path, version, events
):
    correction_api()
    state = with_history(junit_audit_state())
    payload = envelope(state, version)
    # v1 history has unknown revision identity and cannot own exact-revision imports.
    if version == 1:
        payload["state"]["analysis_history"][0]["junit_evidence_imports"] = []
    for bundle in bundles(payload):
        bundle.pop("effective_junit_mappings", None)
        if events == "absent":
            bundle.pop("junit_import_events", None)
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    store = JsonReviewStore(tmp_path)
    if version >= 8 and events == "absent":
        with pytest.raises(ValueError):
            store.load(state.review.review_id)
    else:
        loaded = store.load(state.review.review_id)
        assert loaded.bundle.junit_import_events == []
        assert loaded.analysis_history[0].junit_import_events == []
        assert loaded.bundle.junit_evidence_imports == state.bundle.junit_evidence_imports
        assert loaded.bundle.effective_junit_mappings[IMPORT_ID] == (
            state.bundle.junit_evidence_imports[0].criterion_mappings
        )
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", range(1, 9))
@pytest.mark.parametrize("location", ["active", "history"])
def test_corrections_cannot_be_smuggled_into_older_versions(tmp_path, version, location):
    state = with_history(correct(junit_audit_state()))
    payload = envelope(state, version)
    other = (
        payload["state"]["analysis_history"][0]
        if location == "active"
        else payload["state"]["bundle"]
    )
    other["junit_import_events"] = []
    # Keep an active-only smuggling attempt independent from v1 history identity.
    if version == 1 and location == "active":
        other["junit_evidence_imports"] = []
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        JsonReviewStore(tmp_path).load(state.review.review_id)
    assert path.read_bytes() == before


@pytest.mark.parametrize("location", ["active", "history"])
@pytest.mark.parametrize("invalid", [None, False, {}, "", ["not-an-event"]])
def test_version_eight_malformed_event_arrays_remain_rejected(tmp_path, location, invalid):
    state = with_history(junit_audit_state())
    payload = envelope(state, 8)
    target = (
        payload["state"]["bundle"]
        if location == "active"
        else payload["state"]["analysis_history"][0]
    )
    target["junit_import_events"] = invalid
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        JsonReviewStore(tmp_path).load(state.review.review_id)
    assert path.read_bytes() == before


@pytest.mark.parametrize("location", ["active", "history"])
def test_v8_invalid_gate_is_rejected_instead_of_repaired_by_v9_upgrade(tmp_path, location):
    correction_api()
    state = with_history(junit_audit_state())
    payload = envelope(state, 8)
    target = (
        payload["state"]["bundle"]
        if location == "active"
        else payload["state"]["analysis_history"][0]
    )
    target["gate"]["reason_codes"] = ["FORGED_DETERMINISTIC_GATE"]
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    with pytest.raises(ValueError, match=r"gate|deterministic"):
        JsonReviewStore(tmp_path).load(state.review.review_id)
    assert path.read_bytes() == before


def test_v8_withdrawal_defaults_remain_supported_without_fabricating_correction(tmp_path):
    correction_api()
    original = junit_audit_state()
    withdrawn = withdraw_junit_evidence_import(
        original,
        import_id=IMPORT_ID,
        reviewer="CONSTRUCTED actor",
        reason="CONSTRUCTED withdrawal",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(original),
    )
    state = with_history(withdrawn)
    payload = envelope(state, 8)
    for bundle in bundles(payload):
        bundle["junit_import_events"][0].pop("schema_version")
        bundle["junit_import_events"][0].pop("action")
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    loaded = JsonReviewStore(tmp_path).load(state.review.review_id)
    assert loaded.model_dump(mode="python") == state.model_dump(mode="python")
    assert loaded.bundle.active_junit_import_ids == []
    assert path.read_bytes() == before


def test_v9_roundtrip_preserves_originals_active_history_and_chain(tmp_path):
    state = with_history(correct(junit_audit_state()))
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["record_version"] == 9
    before = path.read_bytes()
    loaded = store.load(state.review.review_id)
    assert loaded.model_dump(mode="python") == state.model_dump(mode="python")
    assert loaded.bundle.junit_evidence_imports == state.bundle.junit_evidence_imports
    assert loaded.analysis_history == state.analysis_history
    assert len(loaded.bundle.junit_import_events) == 1
    assert loaded.bundle.effective_junit_mappings[IMPORT_ID][0].criterion_id == "AC-02"
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", [8, 9])
@pytest.mark.parametrize("location", ["active", "history"])
def test_new_formats_require_explicit_audit_stream_in_every_bundle(tmp_path, version, location):
    correction_api()
    state = with_history(junit_audit_state())
    payload = envelope(state, version)
    target = (
        payload["state"]["bundle"]
        if location == "active"
        else payload["state"]["analysis_history"][0]
    )
    target.pop("junit_import_events")
    path = write_payload(tmp_path, payload)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        JsonReviewStore(tmp_path).load(state.review.review_id)
    assert path.read_bytes() == before


def test_stale_guarded_save_cannot_overwrite_external_saved_changes(tmp_path):
    state = junit_audit_state()
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    fingerprint = store.state_fingerprint(state)
    candidate = correct(state)
    external = state.model_copy(deep=True)
    external.bundle.junit_evidence_imports[0].limitations.append("CONSTRUCTED external update")
    store.save(external)
    external_bytes = path.read_bytes()
    with pytest.raises(StaleReviewState):
        store.save(candidate, expected_fingerprint=fingerprint)
    assert path.read_bytes() == external_bytes
    assert store.load(state.review.review_id) == external


def test_failed_locked_correction_preserves_record_and_candidate_input(tmp_path, monkeypatch):
    state = junit_audit_state()
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    before = path.read_bytes()
    original = state.model_dump_json()

    def fail_save(_updated):
        raise OSError("CONSTRUCTED disk failure")

    monkeypatch.setattr(store, "_save_unlocked", fail_save)
    with pytest.raises(OSError, match="CONSTRUCTED disk failure"):
        store.mutate(state.review.review_id, correct)
    assert path.read_bytes() == before
    assert state.model_dump_json() == original
    assert store.load(state.review.review_id).bundle.junit_import_events == []
