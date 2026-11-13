from pathlib import Path

import pytest

from scopeproof_core.resolution_events import current_resolutions
from scopeproof_core.reviews.lifecycle import append_external_verification, append_resolution
from scopeproof_core.schemas.models import EvidenceLevel, HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_source_attachment import reopen
from tests.apps.test_streamlit_app import (
    _criterion_card,
    analyzed_demo,
    evidence_matrix_criterion_ids,
    new_app,
)
from tests.reviews.test_final_acceptance_blockers import _recompute_gate
from tests.reviews.test_lifecycle import linked_manual_event, scoped_runtime_evidence
from tests.reviews.test_runtime_evidence_level import _previous_policy_record, _review_requiring


@pytest.mark.parametrize("recorded_level", [EvidenceLevel.E3, EvidenceLevel.E4])
def test_reopened_matrix_filters_by_current_linked_verification_level(
    recorded_level: EvidenceLevel, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    state = _review_requiring(recorded_level)
    state = append_external_verification(
        state,
        scoped_runtime_evidence(head_sha=state.review.head_sha, evidence_level=recorded_level),
        linked_manual_event(claimed_evidence_level=recorded_level),
    )
    assert state.bundle is not None
    assert state.bundle.findings[0].evidence_level is EvidenceLevel.E1
    record = JsonReviewStore(storage).save(state)
    original = record.read_bytes()
    app = reopen(state.review.review_id)

    app = app.multiselect(key="evidence_level_filter").select(recorded_level).run()

    assert not app.exception
    assert evidence_matrix_criterion_ids(app) == ["AC-01"]
    card = _criterion_card(app, "inspect_matrix_AC-01")
    captions = [item.value for item in card.caption]
    assert "Candidate evidence level: E1" in captions
    assert f"Recorded verification level: {recorded_level.value}" in captions

    app = app.multiselect(key="evidence_level_filter").set_value([EvidenceLevel.E1]).run()
    assert evidence_matrix_criterion_ids(app) == ["AC-01"]
    other_level = EvidenceLevel.E4 if recorded_level is EvidenceLevel.E3 else EvidenceLevel.E3
    app = app.multiselect(key="evidence_level_filter").set_value([other_level]).run()
    assert evidence_matrix_criterion_ids(app) == []
    app = app.multiselect(key="evidence_level_filter").set_value(
        [other_level, recorded_level],
    ).run()
    assert evidence_matrix_criterion_ids(app) == ["AC-01"]
    assert app.session_state["review_state"] == state
    assert record.read_bytes() == original


def test_matrix_preserves_static_e0_and_e2_filtering() -> None:
    app = analyzed_demo(new_app())
    app = app.multiselect(key="evidence_level_filter").set_value([EvidenceLevel.E0]).run()
    assert evidence_matrix_criterion_ids(app) == ["AC-03", "AC-04"]
    for criterion_id in evidence_matrix_criterion_ids(app):
        card = _criterion_card(app, f"inspect_matrix_{criterion_id}")
        assert "Candidate evidence level: E0" in [item.value for item in card.caption]
    app = app.multiselect(key="evidence_level_filter").set_value([EvidenceLevel.E2]).run()
    assert evidence_matrix_criterion_ids(app) == ["AC-01", "AC-02"]
    for criterion_id in evidence_matrix_criterion_ids(app):
        card = _criterion_card(app, f"inspect_matrix_{criterion_id}")
        assert "Candidate evidence level: E2" in [item.value for item in card.caption]


@pytest.mark.parametrize("unlinked", [True, False], ids=["unlinked", "superseded"])
def test_matrix_does_not_find_historical_runtime_evidence_as_current(
    unlinked: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    state = _previous_policy_record(accepted=False)
    assert state.bundle is not None
    if unlinked:
        state.resolution_events[0].runtime_evidence_id = None
        state.bundle.resolutions = current_resolutions(
            state.resolution_events, state.criteria_revision.number,
        )
        _recompute_gate(state)
    else:
        state = append_resolution(
            state,
            ResolutionEvent(
                criterion_id="AC-01", decision=HumanDecision.CHANGE_REQUIRED,
                comment="Verification does not cover this criterion.", reviewer="Fixture reviewer",
            ),
        )
    JsonReviewStore(storage).save(state)
    app = reopen(state.review.review_id)
    app = app.multiselect(key="evidence_level_filter").set_value([EvidenceLevel.E3]).run()
    assert not app.exception
    assert evidence_matrix_criterion_ids(app) == []
    app = app.multiselect(key="evidence_level_filter").set_value([EvidenceLevel.E1]).run()
    assert evidence_matrix_criterion_ids(app) == ["AC-01"]
    card = _criterion_card(app, "inspect_matrix_AC-01")
    assert not any(item.value.startswith("Recorded verification level:") for item in card.caption)


def test_matrix_finds_legacy_linked_e3_without_satisfying_e4_requirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    state = _previous_policy_record(accepted=False)
    JsonReviewStore(storage).save(state)
    app = reopen(state.review.review_id)
    app = app.multiselect(key="evidence_level_filter").set_value([EvidenceLevel.E4]).run()
    assert evidence_matrix_criterion_ids(app) == []
    app = app.multiselect(key="evidence_level_filter").set_value([EvidenceLevel.E3]).run()
    assert evidence_matrix_criterion_ids(app) == ["AC-01"]
    card = _criterion_card(app, "inspect_matrix_AC-01")
    assert any(
        item.value.startswith("Recorded verification level: E3")
        and "below" in item.value.lower()
        for item in card.caption
    )
    assert app.button(key="record_final_acceptance").disabled
