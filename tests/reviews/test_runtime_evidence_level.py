import json
from pathlib import Path

import pytest

from scopeproof_core.cli import main
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import export_json
from scopeproof_core.resolution_events import current_resolutions
from scopeproof_core.reviews.historical_analysis import (
    locked_historical_analysis,
    prepare_historical_analysis,
)
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    append_resolution,
    can_record_final_acceptance,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    Criterion,
    EvidenceLevel,
    GateDecision,
    GateVerdict,
    HumanDecision,
    ResolutionEvent,
    ReviewState,
    normalized_criteria_sha256,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.storage.transfer import export_review, import_review
from scopeproof_core.verification.service import build_findings
from tests.reviews.test_lifecycle import (
    exact_head_state,
    linked_manual_event,
    scoped_runtime_evidence,
)


def _review_requiring(level: EvidenceLevel) -> ReviewState:
    bundle = exact_head_state().bundle
    assert bundle is not None
    provenance = bundle.review.criteria_source_provenance
    assert provenance is not None
    bundle.criteria[0].required_evidence_level = level
    bundle.review.criteria_source_provenance = provenance.model_copy(
        update={"normalized_criteria_sha256": normalized_criteria_sha256(bundle.criteria)},
    )
    bundle.findings = build_findings(
        bundle.criteria, bundle.evidence, bundle.review.ingestion_state,
    )
    bundle.gate = evaluate_gate(
        bundle.review, bundle.criteria, bundle.findings, [], bundle.evidence,
    )
    return new_review_state(bundle)


def _previous_policy_record(*, accepted: bool) -> ReviewState:
    """Reconstruct recorded facts allowed by the previous write path."""
    state = _review_requiring(EvidenceLevel.E4)
    bundle = state.bundle
    assert bundle is not None
    evidence = scoped_runtime_evidence(head_sha=state.review.head_sha)
    event = linked_manual_event(criteria_revision_number=state.criteria_revision.number)
    state.resolution_events = [event]
    if accepted:
        state.resolution_events.append(
            ResolutionEvent(
                event_id="accepted", final_acceptance=True,
                criteria_revision_number=state.criteria_revision.number,
            )
        )
    state.review.final_acceptance = accepted
    bundle.review.final_acceptance = accepted
    bundle.runtime_evidence = [evidence]
    bundle.resolutions = current_resolutions(
        state.resolution_events, state.criteria_revision.number,
    )
    bundle.gate = (
        GateDecision(verdict=GateVerdict.READY)
        if accepted
        else GateDecision(
            verdict=GateVerdict.NEEDS_REVIEW,
            reason_codes=["final_acceptance_required"],
        )
    )
    return state


def test_linked_e3_cannot_resolve_e4_and_does_not_mutate_state() -> None:
    state = _review_requiring(EvidenceLevel.E4)
    original = state.model_dump_json()
    evidence = scoped_runtime_evidence(head_sha=state.review.head_sha)

    with pytest.raises(ValueError, match="requires E4 evidence"):
        append_external_verification(state, evidence, linked_manual_event())

    assert state.model_dump_json() == original


@pytest.mark.parametrize("level", [EvidenceLevel.E3, EvidenceLevel.E4])
def test_matching_runtime_level_resolves_criterion_and_enables_acceptance(
    level: EvidenceLevel,
) -> None:
    state = _review_requiring(level)
    assert state.bundle is not None
    evidence = scoped_runtime_evidence(head_sha=state.review.head_sha, evidence_level=level)
    event = linked_manual_event(claimed_evidence_level=level)

    verified = append_external_verification(state, evidence, event)

    assert verified.bundle is not None
    assert verified.bundle.runtime_evidence == [evidence]
    assert verified.bundle.resolutions[0].runtime_evidence_id == evidence.runtime_evidence_id
    assert verified.bundle.findings == state.bundle.findings
    assert not verified.review.final_acceptance
    assert can_record_final_acceptance(verified)
    accepted = append_resolution(verified, ResolutionEvent(final_acceptance=True))
    assert accepted.bundle is not None
    assert accepted.bundle.gate.verdict is GateVerdict.READY


def test_previously_recorded_e3_link_cannot_support_new_final_acceptance(tmp_path: Path) -> None:
    old = _previous_policy_record(accepted=False)
    store = JsonReviewStore(tmp_path / "reviews")
    path = store.save(old)
    original = path.read_bytes()
    loaded = store.load(old.review.review_id)
    assert loaded == old

    with pytest.raises(ValueError):
        store.mutate(
            loaded.review.review_id,
            lambda state: append_resolution(state, ResolutionEvent(final_acceptance=True)),
        )

    assert not can_record_final_acceptance(loaded)
    assert path.read_bytes() == original
    assert store.load(old.review.review_id) == old


def test_legacy_below_level_link_can_be_superseded_by_documented_reviewer_acceptance() -> None:
    old = _previous_policy_record(accepted=False)
    assert old.bundle is not None
    decision = ResolutionEvent(criterion_id="AC-01", decision=HumanDecision.ACCEPTED)
    with pytest.raises(ValueError, match="reviewer comment is required"):
        append_resolution(old, decision)

    resolved = append_resolution(
        old,
        decision.model_copy(update={"comment": "Accepted after inspecting the recorded evidence."}),
    )
    assert resolved.bundle is not None
    assert resolved.bundle.runtime_evidence == old.bundle.runtime_evidence
    assert resolved.resolution_events[:-1] == old.resolution_events
    assert resolved.bundle.resolutions[0].decision is HumanDecision.ACCEPTED
    assert resolved.bundle.resolutions[0].claimed_evidence_level is None
    assert can_record_final_acceptance(resolved)


def _report_json(store: JsonReviewStore, state: ReviewState, *, retained: bool) -> str:
    if not retained:
        return export_json(state)
    selection = prepare_historical_analysis(store, state, 0)
    with locked_historical_analysis(store, selection) as report:
        return report.model_dump_json()


@pytest.mark.parametrize("retained", [False, True], ids=["active", "retained"])
def test_prior_ready_record_preserves_review_transfer_and_report(
    tmp_path: Path, retained: bool,
) -> None:
    old = _previous_policy_record(accepted=True)
    if retained:
        old = revise_criteria(
            old, [Criterion(criterion_id="AC-01", text="Export filtered CSV")],
            "Export filtered CSV",
        )
    sender = JsonReviewStore(tmp_path / "sender")
    original_record = sender.save(old)
    saved_bytes = original_record.read_bytes()
    review_id = old.review.review_id
    assert sender.load(review_id) == old
    original_report = _report_json(sender, old, retained=retained)

    portable = tmp_path / "portable.json"
    export_review(sender, review_id, portable)
    recipient = JsonReviewStore(tmp_path / "recipient")
    import_review(recipient, portable)
    reopened = recipient.load(review_id)
    assert reopened == old

    transferred_report = _report_json(recipient, reopened, retained=retained)
    assert transferred_report == original_report
    report_bundle = json.loads(transferred_report)["analysis" if retained else "bundle"]
    assert report_bundle["gate"]["verdict"] == "ready"
    assert report_bundle["review"]["final_acceptance"] is True
    assert report_bundle["criteria"][0]["required_evidence_level"] == "E4"
    assert report_bundle["runtime_evidence"][0]["evidence_level"] == "E3"
    assert report_bundle["resolutions"][0]["runtime_evidence_id"] == "runtime-001"
    assert original_record.read_bytes() == portable.read_bytes() == saved_bytes
    assert (recipient.directory / original_record.name).read_bytes() == saved_bytes


def test_verify_runtime_cli_reports_level_mismatch_without_rewriting_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    state = _review_requiring(EvidenceLevel.E4)
    store = JsonReviewStore(tmp_path / "reviews")
    path = store.save(state)
    original = path.read_bytes()
    comment = tmp_path / "comment.txt"
    comment.write_text("Observed the constructed export scenario.", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main([
            "verify-runtime", state.review.review_id,
            "--criterion-id", "AC-01", "--level", "E3", "--reviewer", "QA",
            "--artifact-reference", "https://example.test/run/1",
            "--scenario", "Export CSV", "--environment", "staging", "--result", "passed",
            "--comment-file", str(comment), "--storage-dir", str(store.directory),
        ])

    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "Criterion AC-01 requires E4 evidence. E3 is below the required level." in output.err
    assert path.read_bytes() == original
