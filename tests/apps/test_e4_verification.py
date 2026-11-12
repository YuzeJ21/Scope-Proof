from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.resolution_events import current_resolutions
from scopeproof_core.reviews.lifecycle import append_resolution, can_record_final_acceptance
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    GateVerdict,
    HumanDecision,
    ResolutionEvent,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_cli_evidence_level_reopen import _save_cli_review
from tests.apps.test_source_attachment import reopen


def _fill_external_verification(app: AppTest) -> AppTest:
    app.text_input(key="runtime_artifact_reference").set_value("fixture-run")
    app.text_area(key="runtime_scenario").set_value("Export CSV")
    app.text_input(key="runtime_environment").set_value("Controlled fixture environment")
    app.text_input(key="runtime_result").set_value("Exported data matched expectations")
    app.text_input(key="runtime_reviewer").set_value("Fixture reviewer")
    return app.run()


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

    app = _fill_external_verification(app)
    assert app.selectbox(key="runtime_evidence_level").value is EvidenceLevel.E3
    button = app.button(key="save_runtime_evidence")
    # Send a click that was queued before the disabled state reached the client.
    button.proto.disabled = False
    app = button.click().run()

    assert not app.exception
    assert app.session_state["review_state"] == before
    assert store.load(review_id) == before
    assert record.read_bytes() == before_bytes
    assert app.button(key="save_runtime_evidence").disabled
    assert app.button(key="record_final_acceptance").disabled
    assert any(
        "This criterion requires E4. Select E4 only when you have explicit human acceptance "
        "for the reviewed commit." in item.value
        for item in [*app.caption, *app.warning, *app.info]
    )

    app = app.selectbox(key="runtime_evidence_level").set_value(EvidenceLevel.E4).run()
    assert not app.button(key="save_runtime_evidence").disabled
    app = app.button(key="save_runtime_evidence").click().run()

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
    if recorded_acceptance:
        assert legacy.bundle.gate.verdict is GateVerdict.READY
        assert "**Recorded verdict: Review complete**" in [item.value for item in app.markdown]
        assert "**Recorded review status: Review complete**" in [
            item.value for item in app.markdown
        ]
        assert not app.button(key="revoke_final_acceptance").disabled
    else:
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

    app = _fill_external_verification(app)
    app = app.selectbox(key="runtime_evidence_level").set_value(EvidenceLevel.E4).run()
    app = app.button(key="save_runtime_evidence").click().run()

    assert not app.exception
    after = store.load(review_id)
    assert after.bundle is not None
    assert after.bundle.runtime_evidence[0] == item
    assert after.resolution_events[:len(legacy.resolution_events)] == legacy.resolution_events
    if recorded_acceptance:
        assert after.resolution_events[-2].final_acceptance is False
    assert can_record_final_acceptance(after)
    assert not app.button(key="record_final_acceptance").disabled
