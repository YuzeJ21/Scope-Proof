from pathlib import Path
from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.proto.WidgetStates_pb2 import WidgetStates
from streamlit.runtime.state.session_state_proxy import SessionStateProxy
from streamlit.testing.v1 import AppTest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.resolution_events import current_resolutions
from scopeproof_core.reviews.lifecycle import append_resolution, can_record_final_acceptance
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    GateVerdict,
    HumanDecision,
    IngestionState,
    ResolutionEvent,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_cli_evidence_level_reopen import _save_cli_review
from tests.apps.test_source_attachment import reopen
from tests.apps.test_streamlit_app import _criterion_card, _criterion_detail_evidence, runtime_key
from tests.reviews.test_runtime_evidence_level import _previous_policy_record, _review_requiring


def _e4_actions(app: AppTest) -> list[str]:
    evidence = list(_criterion_detail_evidence(app))
    heading = next(
        index for index, item in enumerate(evidence)
        if item.type == "markdown" and item.value == "**Recommended next action**"
    )
    actions = [
        evidence[heading + 1].value,
        _criterion_card(app, "inspect_matrix_AC-01").code[0].value,
    ]
    if any(button.key == "inspect_queue_AC-01" for button in app.button):
        actions.append(_criterion_card(app, "inspect_queue_AC-01").text[-1].value)
    return actions


def _fill_external_verification(app: AppTest) -> AppTest:
    app.text_input(key=runtime_key(app, "runtime_artifact_reference")).set_value("fixture-run")
    app.text_area(key=runtime_key(app, "runtime_scenario")).set_value("Export CSV")
    app.text_input(key=runtime_key(app, "runtime_environment")).set_value(
        "Controlled fixture environment"
    )
    app.text_input(key=runtime_key(app, "runtime_result")).set_value(
        "Exported data matched expectations"
    )
    app.text_input(key=runtime_key(app, "runtime_reviewer")).set_value("Fixture reviewer")
    return app.run()


def _verification_payload(app: AppTest) -> WidgetStates:
    save = app.button(key=runtime_key(app, "save_runtime_evidence")).click()
    runtime_ids = {
        widget.id for widget in [*app.text_input, *app.text_area, *app.selectbox]
        if widget.key and widget.key.startswith("runtime_")
    }
    runtime_ids.add(save.id)
    payload = WidgetStates()
    payload.widgets.extend(
        widget for widget in app._tree.get_widget_states().widgets if widget.id in runtime_ids
    )
    return payload


def _empty_verification_fields(app: AppTest) -> None:
    form_id = app.session_state["runtime_verification_form_id"]
    for widget in [*app.text_input, *app.text_area]:
        if widget.key and widget.key.endswith(form_id):
            widget.set_value("")
    app.selectbox(key=runtime_key(app, "runtime_evidence_level")).set_value(EvidenceLevel.E3)


def test_delayed_verification_cannot_save_against_another_criterion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    review_id, record = _save_cli_review(tmp_path / "delayed", storage, EvidenceLevel.E4)
    store = JsonReviewStore(storage)
    state = store.load(review_id)
    original = record.read_bytes()
    app = reopen(review_id).selectbox(key="selected_criterion").set_value("AC-01").run()
    app = _fill_external_verification(app)
    app = app.selectbox(key=runtime_key(app, "runtime_evidence_level")).set_value(
        EvidenceLevel.E4
    ).run()
    payload = _verification_payload(app)
    app.button(key=runtime_key(app, "save_runtime_evidence")).set_value(False)
    _empty_verification_fields(app)
    app = app.selectbox(key="selected_criterion").set_value("AC-02").run()
    app = app._run(payload)

    assert not app.exception
    assert app.selectbox(key="selected_criterion").value == "AC-02"
    assert app.session_state["review_state"] == state
    assert store.load(review_id) == state
    assert record.read_bytes() == original
    assert app.text_input(key=runtime_key(app, "runtime_artifact_reference")).value == ""
    assert app.button(key=runtime_key(app, "save_runtime_evidence")).disabled
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    app = app._run(payload)
    assert app.selectbox(key="selected_criterion").value == "AC-01"
    assert app.session_state["review_state"] == state
    assert record.read_bytes() == original


@pytest.mark.parametrize("transition", ["clear", "reopen", "save", "interrupted_save"])
def test_retired_verification_submission_cannot_write_on_same_criterion(
    transition: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    review_id, record = _save_cli_review(tmp_path / "replay", storage, EvidenceLevel.E3)
    store = JsonReviewStore(storage)
    original = store.load(review_id)
    app = reopen(review_id).selectbox(key="selected_criterion").set_value("AC-01").run()
    app = _fill_external_verification(app)
    payload = _verification_payload(app)
    save = app.button(key=runtime_key(app, "save_runtime_evidence"))
    if transition in {"clear", "reopen"}:
        save.set_value(False)
        if transition == "clear":
            app = app.button(key="clear_criterion_detail_drafts").click().run()
        else:
            # Return to a clean form first so the ordinary reopen action is available.
            _empty_verification_fields(app)
            app = app.run().button(key="reopen_review").click().run()
            app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    elif transition == "interrupted_save":
        set_state = SessionStateProxy.__setitem__
        interrupted = False

        def interrupt_after_append(proxy, key, value):
            nonlocal interrupted
            set_state(proxy, key, value)
            if key == "review_state" and value.bundle.runtime_evidence and not interrupted:
                interrupted = True
                st.rerun()

        with patch.object(SessionStateProxy, "__setitem__", interrupt_after_append):
            app = save.run()
        assert interrupted
    else:
        app = save.run()

    expected = store.load(review_id)
    if transition in {"clear", "reopen"}:
        assert expected == original
    else:
        evidence, = expected.bundle.runtime_evidence
        event, = expected.resolution_events
        assert evidence.criterion_id == event.criterion_id == "AC-01"
        assert event.runtime_evidence_id == evidence.runtime_evidence_id
    saved_bytes = record.read_bytes()
    app = app._run(payload)
    assert not app.exception
    assert app.selectbox(key="selected_criterion").value == "AC-01"
    assert app.session_state["review_state"] == expected
    assert record.read_bytes() == saved_bytes
    assert app.text_input(key=runtime_key(app, "runtime_artifact_reference")).value == ""
    assert app.button(key=runtime_key(app, "save_runtime_evidence")).disabled


def test_e4_guidance_preserves_partial_ingestion_recovery() -> None:
    from apps.web.view_models import criterion_next_actions

    state = _review_requiring(EvidenceLevel.E4)
    assert state.bundle is not None
    bundle = state.bundle
    bundle.review.ingestion_state = IngestionState.PARTIAL
    bundle.review.skipped_files = ["constructed/skipped.py"]
    bundle.findings[0].recommended_action = "Review skipped content before deciding."
    assert criterion_next_actions(bundle, suggest_external_verification=True) == {
        "AC-01": "Review skipped content before deciding.",
    }


def test_e4_guidance_prioritizes_source_recovery_over_recording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    state = _previous_policy_record(accepted=True)
    record = JsonReviewStore(storage).save(state)
    before = record.read_bytes()
    app = reopen(state.review.review_id)
    app.session_state["source_authority_guard"].block(state)
    app = app.run()

    assert not app.exception
    actions = _e4_actions(app)
    assert len(actions) == 2
    assert all("workbench recovery guidance" in action for action in actions)
    assert all("Revoke final acceptance" not in action for action in actions)
    assert all("Record optional external verification" not in action for action in actions)
    assert "**Decision status: Refresh required**" in [item.value for item in app.markdown]
    assert record.read_bytes() == before


def test_reopened_e4_criterion_rejects_e3_but_accepts_explicit_e4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    review_id, record = _save_cli_review(tmp_path / "e4", storage, EvidenceLevel.E4)
    store = JsonReviewStore(storage)
    app = reopen(review_id).selectbox(key="selected_criterion").set_value("AC-02").run()
    app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED)
    app.text_area(key="resolution_note").set_value("Reviewed the CSV header evidence")
    app = app.run().button(key="save_resolution").click().run()
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    before = store.load(review_id)
    before_bytes = record.read_bytes()
    assert before.bundle is not None
    assert before.bundle.criteria[0].required_evidence_level is EvidenceLevel.E4
    assert [resolution.criterion_id for resolution in before.bundle.resolutions] == ["AC-02"]
    assert not can_record_final_acceptance(before)
    actions = _e4_actions(app)
    assert len(actions) == 3
    assert all("explicit human acceptance for the reviewed PR head" in action for action in actions)
    assert all("Record optional external verification (E3/E4)" in action for action in actions)

    app = _fill_external_verification(app)
    assert app.selectbox(key=runtime_key(app, "runtime_evidence_level")).value is EvidenceLevel.E3
    button = app.button(key=runtime_key(app, "save_runtime_evidence"))
    # Send a click that was queued before the disabled state reached the client.
    button.proto.disabled = False
    app = button.click().run()

    assert not app.exception
    assert app.session_state["review_state"] == before
    assert store.load(review_id) == before
    assert record.read_bytes() == before_bytes
    assert app.button(key=runtime_key(app, "save_runtime_evidence")).disabled
    assert app.button(key="record_final_acceptance").disabled
    assert any(
        "This criterion requires E4. Select E4 only when you have explicit human acceptance "
        "for the reviewed commit." in item.value
        for item in [*app.caption, *app.warning, *app.info]
    )

    app = app.selectbox(key=runtime_key(app, "runtime_evidence_level")).set_value(
        EvidenceLevel.E4
    ).run()
    assert not app.button(key=runtime_key(app, "save_runtime_evidence")).disabled
    app = app.button(key=runtime_key(app, "save_runtime_evidence")).click().run()

    assert not app.exception
    after = store.load(review_id)
    assert after == app.session_state["review_state"]
    assert after.bundle is not None
    runtime_item, = after.bundle.runtime_evidence
    assert runtime_item.criterion_id == "AC-01"
    assert runtime_item.evidence_level is EvidenceLevel.E4
    event = after.resolution_events[-1]
    assert event.decision is HumanDecision.MANUALLY_VERIFIED
    assert event.claimed_evidence_level is EvidenceLevel.E4
    assert event.runtime_evidence_id == runtime_item.runtime_evidence_id
    assert can_record_final_acceptance(after)
    assert not app.button(key="record_final_acceptance").disabled
    assert after.review.final_acceptance is False
    assert all("Review the recorded E4 verification" in action for action in _e4_actions(app))


@pytest.mark.parametrize("recorded_acceptance", [False, True], ids=["pending", "recorded"])
def test_reopened_linked_e3_record_is_retained_and_requires_e4_for_acceptance(
    recorded_acceptance: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    review_id, record = _save_cli_review(tmp_path / "legacy", storage, EvidenceLevel.E4)
    store = JsonReviewStore(storage)
    legacy = append_resolution(
        store.load(review_id),
        ResolutionEvent(
            criterion_id="AC-02",
            decision=HumanDecision.ACCEPTED,
            reviewer="Fixture reviewer",
            comment="Reviewed the CSV header evidence",
        ),
    )
    assert legacy.bundle is not None
    # Represent a linked observation and decision admitted by the prior write policy.
    item = RuntimeEvidence(
        runtime_evidence_id="legacy-runtime-record",
        repository=legacy.review.repository,
        pr_number=legacy.review.pr_number,
        head_sha=legacy.review.head_sha,
        criterion_id="AC-01",
        artifact_reference="legacy-fixture-run",
        scenario="Export CSV",
        environment="Controlled fixture environment",
        result="Observed CSV export",
        reviewer="Legacy fixture reviewer",
        evidence_level=EvidenceLevel.E3,
    )
    event = ResolutionEvent(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment="Observed CSV export in the earlier review",
        claimed_evidence_level=EvidenceLevel.E3,
        runtime_evidence_id=item.runtime_evidence_id,
        reviewer=item.reviewer,
        criteria_revision_number=legacy.criteria_revision.number,
    )
    legacy.bundle.runtime_evidence.append(item)
    legacy.resolution_events.append(event)
    legacy.bundle.resolutions = current_resolutions(
        legacy.resolution_events, legacy.criteria_revision.number,
    )
    if recorded_acceptance:
        legacy.resolution_events.append(ResolutionEvent(
            final_acceptance=True,
            reviewer="Legacy fixture reviewer",
            comment="Final acceptance recorded under the earlier policy",
            criteria_revision_number=legacy.criteria_revision.number,
        ))
        legacy.review.final_acceptance = True
        legacy.bundle.review.final_acceptance = True
    legacy.bundle.gate = evaluate_gate(
        legacy.bundle.review, legacy.bundle.criteria, legacy.bundle.findings,
        legacy.bundle.resolutions, legacy.bundle.evidence, legacy.bundle.file_scope_decisions,
    )
    store.save(legacy)
    original_bytes = record.read_bytes()

    app = reopen(review_id).selectbox(key="selected_criterion").set_value("AC-01").run()

    assert not app.exception
    assert app.session_state["review_state"] == legacy
    assert record.read_bytes() == original_bytes
    actions = _e4_actions(app)
    assert all(
        "Recorded E3 verification is below the E4 requirement" in action for action in actions
    ), actions
    if recorded_acceptance:
        assert all("Revoke final acceptance" in action for action in actions)
        assert legacy.bundle.gate.verdict is GateVerdict.READY
        assert "**Recorded verdict: Review complete**" in [item.value for item in app.markdown]
        assert "**Recorded review status: Review complete**" in [
            item.value for item in app.markdown
        ]
        assert not app.button(key="revoke_final_acceptance").disabled
    else:
        assert all("Record optional external verification (E3/E4)" in action for action in actions)
        assert app.button(key="record_final_acceptance").disabled
        assert not can_record_final_acceptance(legacy)
        assert not any(
            "Record final acceptance after reviewing every criterion" in item.value
            for item in app.markdown
        )
    assert any(
        "record E4 verification for AC-01" in item.value
        and "explicit reviewer decision" in item.value
        for item in app.caption
    )
    assert any(
        item.value.startswith(
            "Previously recorded manual verification is below the required evidence level "
            "for AC-01."
        )
        for item in app.warning
    )

    if recorded_acceptance:
        app = app.button(key="revoke_final_acceptance").click().run()
        assert not app.exception
        assert not store.load(review_id).review.final_acceptance
        assert app.button(key="record_final_acceptance").disabled
        assert all(
            "Record optional external verification (E3/E4)" in action
            for action in _e4_actions(app)
        )

    app = _fill_external_verification(app)
    app = app.selectbox(key=runtime_key(app, "runtime_evidence_level")).set_value(
        EvidenceLevel.E4
    ).run()
    app = app.button(key=runtime_key(app, "save_runtime_evidence")).click().run()

    assert not app.exception
    after = store.load(review_id)
    assert after.bundle is not None
    assert after.bundle.runtime_evidence[0] == item
    assert after.resolution_events[:len(legacy.resolution_events)] == legacy.resolution_events
    if recorded_acceptance:
        assert after.resolution_events[-2].final_acceptance is False
    assert can_record_final_acceptance(after)
    assert not app.button(key="record_final_acceptance").disabled
