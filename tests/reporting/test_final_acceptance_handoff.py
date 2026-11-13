from pathlib import Path

import pytest

from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reporting.historical_analysis import export_historical_markdown
from scopeproof_core.reviews.historical_analysis import (
    locked_historical_analysis,
    prepare_historical_analysis,
)
from scopeproof_core.reviews.lifecycle import (
    append_file_scope_decision,
    append_resolution,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    Criterion,
    GateVerdict,
    HumanDecision,
    ResolutionEvent,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_file_scope_lifecycle import scope_decision, scope_state
from tests.reviews.test_final_acceptance_blockers import _recompute_gate, _set_review_facts
from tests.reviews.test_runtime_evidence_level import _previous_policy_record


def _handoff_section(report: str, heading: str) -> str:
    if report.startswith("<!doctype html>"):
        marker = f"<h2>{heading}</h2>"
        assert marker in report
        return report.split(marker, 1)[1].split("<h2", 1)[0]
    marker = f"## {heading}\n"
    assert marker in report
    return report.split(marker, 1)[1].split("\n## ", 1)[0].replace("\\", "")


def test_full_state_handoff_explains_scope_even_when_required_checks_fail(tmp_path: Path) -> None:
    state = append_resolution(
        scope_state(),
        ResolutionEvent(
            criterion_id="AC-01", decision=HumanDecision.ACCEPTED,
            reviewer="Fixture reviewer", comment="Reviewed the CSV candidate.",
        ),
    )
    _set_review_facts(
        state, check_state=CheckState.FAILING,
        ci_observation=CIObservation(
            state=CheckState.FAILING, reason="Constructed check failure.",
            total_check_runs=1, failing_check_runs=1,
        ),
    )
    assert state.bundle is not None
    assert state.bundle.gate.reason_codes == ["required_checks_failing"]
    store = JsonReviewStore(tmp_path / "reviews")
    record = store.save(state)
    original = record.read_bytes()
    saved = store.load(state.review.review_id)
    structured_exports = (export_json(saved), export_csv(saved))

    markdown = export_markdown(saved)
    html = export_html(saved)
    for report in (markdown, html):
        section = _handoff_section(report, "Final Acceptance Prerequisites")
        assert "Observed GitHub checks are failing" in section
        assert "Changed-file scope is unresolved" in section
        assert "Record final acceptance after reviewing" not in report
        assert "What To Do Next" in report

    assert (export_json(saved), export_csv(saved)) == structured_exports
    assert store.load(state.review.review_id) == saved == state
    assert record.read_bytes() == original


@pytest.mark.parametrize("accepted", [False, True], ids=["pending", "recorded"])
def test_full_state_handoff_explains_legacy_e3_below_e4(tmp_path: Path, accepted: bool) -> None:
    state = _previous_policy_record(accepted=accepted)
    assert state.bundle is not None
    expected_verdict = GateVerdict.READY if accepted else GateVerdict.NEEDS_REVIEW
    assert state.bundle.gate.verdict is expected_verdict
    store = JsonReviewStore(tmp_path / "reviews")
    record = store.save(state)
    original = record.read_bytes()
    saved = store.load(state.review.review_id)
    structured_exports = (export_json(saved), export_csv(saved))

    markdown = export_markdown(saved)
    html = export_html(saved)
    recorded_status = "Review complete" if accepted else "Review incomplete"
    assert f"**Recorded review status:** {recorded_status}" in markdown
    assert f"<strong>Recorded review status:</strong> {recorded_status}" in html
    assert f"**Recorded final acceptance:** {'Yes' if accepted else 'No'}" in markdown
    heading = "Final Acceptance Guidance" if accepted else "Final Acceptance Prerequisites"
    for report in (markdown, html):
        assert "Record final acceptance only after a reviewer" not in report
        assert "Record final acceptance after reviewing" not in report
        section = _handoff_section(report, heading)
        assert "AC-01 records E3 verification and requires E4" in section
        assert (
            "Before new final acceptance, record verification at the required level "
            "or record an explicit reviewer decision with the applicable rationale"
        ) in section
        assert ("Revoke recorded final acceptance" in section) == accepted

    assert (export_json(saved), export_csv(saved)) == structured_exports
    assert store.load(state.review.review_id) == saved == state
    assert record.read_bytes() == original


def test_full_state_handoff_explains_revocation_before_replacing_unlinked_verification() -> None:
    state = _previous_policy_record(accepted=True)
    assert state.bundle is not None
    state.bundle.resolutions[0].runtime_evidence_id = None
    state.resolution_events[0].runtime_evidence_id = None
    _recompute_gate(state)

    for render in (export_markdown, export_html):
        report = render(state)
        guidance = _handoff_section(report, "Final Acceptance Guidance")
        assert "Revoke recorded final acceptance before replacing manual verification." in guidance
        assert "criteria with unlinked manual verification" in guidance
        assert "Record final acceptance after reviewing" not in report


@pytest.mark.parametrize(
    ("decision", "recorded_reason"),
    [
        (HumanDecision.ACCEPTED, "final_acceptance_required"),
        (HumanDecision.ACCEPTED_EXCEPTION, "conditional_criteria"),
    ],
)
def test_full_state_handoff_invites_final_acceptance_when_prerequisites_are_met(
    decision: HumanDecision, recorded_reason: str,
) -> None:
    state = append_resolution(
        scope_state(),
        ResolutionEvent(
            criterion_id="AC-01", decision=decision,
            reviewer="Fixture reviewer", comment="Reviewed the CSV candidate.",
        ),
    )
    state = append_file_scope_decision(state, scope_decision(state))
    assert state.bundle is not None
    assert state.bundle.gate.reason_codes == [recorded_reason]
    accepted = append_resolution(state, ResolutionEvent(final_acceptance=True))

    expected = "Record final acceptance after reviewing every criterion and its evidence."
    for render in (export_markdown, export_html):
        report = render(state)
        section = _handoff_section(report, "Final Acceptance Guidance")
        assert expected in section
        assert "Final Acceptance Prerequisites" not in report
        assert "Record final acceptance only after a reviewer" not in report
        assert "Final Acceptance Guidance" not in render(accepted)


def test_bare_bundle_and_historical_handoff_exclude_current_prerequisites(tmp_path: Path) -> None:
    active = _previous_policy_record(accepted=True)
    assert active.bundle is not None
    state = revise_criteria(
        active, [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
        "Export filtered CSV",
    )
    store = JsonReviewStore(tmp_path / "reviews")
    record = store.save(state)
    original = record.read_bytes()
    with locked_historical_analysis(store, prepare_historical_analysis(store, state, 0)) as report:
        assert report.analysis == state.analysis_history[0]
        historical = export_historical_markdown(report)

    assert "Historical review status (installed policy):** Review complete" in historical
    for export in (export_markdown(active.bundle), export_html(active.bundle), historical):
        assert "Final Acceptance Prerequisites" not in export
        assert "Final Acceptance Guidance" not in export
        assert "Revoke recorded final acceptance" not in export
    assert record.read_bytes() == original
