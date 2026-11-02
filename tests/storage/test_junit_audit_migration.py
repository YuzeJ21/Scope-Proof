"""Independent version-boundary and atomic-store regressions for JUnit audit facts."""

import json
from datetime import UTC, datetime
from importlib import import_module

import pytest

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore, StaleReviewState
from tests.junit_audit_fixture import junit_audit_state


def audit_api():
    try:
        return import_module("scopeproof_core.reviews.junit_audit")
    except ModuleNotFoundError as error:
        if error.name != "scopeproof_core.reviews.junit_audit":
            raise
        pytest.fail("JUnit import withdrawal is not implemented yet", pytrace=False)


def withdrawn_state():
    state = junit_audit_state()
    return audit_api().withdraw_junit_evidence_import(
        state,
        import_id="constructed-junit-import",
        reviewer="CONSTRUCTED migration actor",
        reason="CONSTRUCTED wrong mapping",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        occurred_at=datetime(2026, 11, 1, 13, tzinfo=UTC),
    )


def with_history(state):
    """Construct two valid revisions without file, application or target-code IO."""
    payload = state.model_dump(mode="python")
    payload["analysis_history"] = [state.bundle.model_dump(mode="python")]
    payload["criteria_revision"]["number"] = 2
    payload["bundle"]["criteria_revision_number"] = 2
    for imported in payload["bundle"]["junit_evidence_imports"]:
        imported["criteria_revision_number"] = 2
    for event in payload["bundle"].get("junit_import_events", []):
        event["criteria_revision_number"] = 2
    return validated_review_state(ReviewState.model_validate(payload))


def write_envelope(tmp_path, state, version):
    path = tmp_path / f"{state.review.review_id}.json"
    payload = {"record_version": version, "state": state.model_dump(mode="json")}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


@pytest.mark.parametrize("version", range(1, 8))
@pytest.mark.parametrize("audit_field", ["absent", "empty"])
def test_legacy_absent_or_empty_audit_loads_without_inventing_events_or_rewriting_disk(
    tmp_path, version, audit_field,
) -> None:
    audit_api()
    state = with_history(junit_audit_state())
    path, payload = write_envelope(tmp_path, state, version)
    # Version one archives have unknown revision identity. They cannot assert a
    # revision-bound JUnit import in that archived bundle.
    payload["state"]["analysis_history"][0]["junit_evidence_imports"] = []
    bundles = [payload["state"]["bundle"], *payload["state"]["analysis_history"]]
    for bundle in bundles:
        if audit_field == "absent":
            bundle.pop("junit_import_events", None)
        else:
            bundle["junit_import_events"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = path.read_bytes()

    loaded = JsonReviewStore(tmp_path).load(state.review.review_id)

    assert loaded.bundle.junit_import_events == []
    assert loaded.analysis_history[0].junit_import_events == []
    assert loaded.bundle.active_junit_import_ids == ["constructed-junit-import"]
    assert len(loaded.bundle.junit_evidence_imports) == 1
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", [1, 6, 7])
@pytest.mark.parametrize("location", ["active", "history"])
@pytest.mark.parametrize("invalid", [None, {}, "", ["invalid"], False])
def test_pre_v8_malformed_audit_fields_reject_without_rewriting(
    tmp_path, version, location, invalid,
) -> None:
    audit_api()
    state = with_history(junit_audit_state())
    path, payload = write_envelope(tmp_path, state, version)
    target = payload["state"]["bundle"] if location == "active" else (
        payload["state"]["analysis_history"][0]
    )
    target["junit_import_events"] = invalid
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(ValueError):
        JsonReviewStore(tmp_path).load(state.review.review_id)

    assert path.read_bytes() == before


@pytest.mark.parametrize("version", range(1, 8))
@pytest.mark.parametrize("location", ["active", "history"])
def test_downgraded_nonempty_withdrawal_audit_is_rejected(tmp_path, version, location) -> None:
    state = with_history(withdrawn_state())
    path, payload = write_envelope(tmp_path, state, version)
    if location == "active":
        payload["state"]["analysis_history"][0]["junit_import_events"] = []
    else:
        payload["state"]["bundle"]["junit_import_events"] = []
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(ValueError):
        JsonReviewStore(tmp_path).load(state.review.review_id)

    assert path.read_bytes() == before


@pytest.mark.parametrize("location", ["active", "history"])
def test_version_eight_requires_explicit_junit_audit_in_each_bundle(tmp_path, location) -> None:
    audit_api()
    state = with_history(junit_audit_state())
    path, payload = write_envelope(tmp_path, state, 8)
    target = payload["state"]["bundle"] if location == "active" else (
        payload["state"]["analysis_history"][0]
    )
    target.pop("junit_import_events", None)
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=r"audit|JUnit|junit|version 8"):
        JsonReviewStore(tmp_path).load(state.review.review_id)


@pytest.mark.parametrize("version", [7, 8])
@pytest.mark.parametrize("location", ["active", "history"])
def test_v8_does_not_weaken_v7_selected_reference_audit_requirements(
    tmp_path, version, location,
) -> None:
    audit_api()
    state = with_history(junit_audit_state())
    path, payload = write_envelope(tmp_path, state, version)
    target = payload["state"]["bundle"] if location == "active" else (
        payload["state"]["analysis_history"][0]
    )
    target.pop("selected_reference_events")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=r"reference audit|reference.*history|version [78]"):
        JsonReviewStore(tmp_path).load(state.review.review_id)


def test_new_save_uses_v8_and_round_trips_originals_and_history(tmp_path) -> None:
    state = with_history(withdrawn_state())
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["record_version"] == 8
    for bundle in [payload["state"]["bundle"], *payload["state"]["analysis_history"]]:
        assert len(bundle["junit_import_events"]) == 1
        assert bundle["selected_reference_events"] == []
    loaded = store.load(state.review.review_id)
    assert loaded.model_dump(mode="python") == state.model_dump(mode="python")
    assert loaded.bundle.active_junit_import_ids == []
    assert loaded.analysis_history[0].active_junit_import_ids == []


def test_stale_guarded_save_does_not_persist_in_memory_withdrawal(tmp_path) -> None:
    api = audit_api()
    store = JsonReviewStore(tmp_path)
    original = junit_audit_state()
    path = store.save(original)
    fingerprint = store.state_fingerprint(original)
    candidate = api.withdraw_junit_evidence_import(
        original, import_id="constructed-junit-import", reviewer="CONSTRUCTED actor",
        reason="CONSTRUCTED correction", expected_state_fingerprint=fingerprint,
    )
    external = original.model_copy(deep=True)
    external.bundle.junit_evidence_imports[0].limitations.append("CONSTRUCTED concurrent edit")
    store.save(external)
    before = path.read_bytes()
    with pytest.raises(StaleReviewState):
        store.save(candidate, expected_fingerprint=fingerprint)
    assert path.read_bytes() == before
    assert store.load(original.review.review_id).bundle.junit_import_events == []


def test_failed_locked_withdrawal_preserves_saved_bytes(tmp_path) -> None:
    api = audit_api()
    state = junit_audit_state()
    store = JsonReviewStore(tmp_path)
    path = store.save(state)
    before = path.read_bytes()

    def transition(current):
        return api.withdraw_junit_evidence_import(
            current, import_id="missing-import", reviewer="CONSTRUCTED actor",
            reason="CONSTRUCTED correction",
            expected_state_fingerprint=store.state_fingerprint(current),
        )

    with pytest.raises(ValueError):
        store.mutate(state.review.review_id, transition)
    assert path.read_bytes() == before
