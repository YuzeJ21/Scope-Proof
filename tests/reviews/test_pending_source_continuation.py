"""Confirmed revisions resume with exact source, full-state leases and no inherited context."""

from datetime import UTC, datetime

import pytest

from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
from scopeproof_core.reviews.lifecycle import append_resolution, confirm_criteria, revise_criteria
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent, ReviewBundle
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.verification.service import build_findings
from tests.reviews.test_source_attachment import (
    api,
    prepare,
    saved_source,
    unchanged_reference_state,
)


def pending_source(tmp_path, *, paths=()):
    store, original, snapshot = saved_source(tmp_path)
    original, candidates = unchanged_reference_state(original, snapshot, list(paths))
    original = append_resolution(
        original,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            reviewer="CONSTRUCTED prior actor",
            comment="Retain this prior-revision decision",
        ),
    )
    criteria = [item.model_copy(deep=True) for item in original.criteria_revision.criteria]
    criteria[0].text += " with newly confirmed scope"
    pending = revise_criteria(original, criteria, "CONSTRUCTED changed requirements")
    pending = confirm_criteria(
        pending,
        build_criteria_source_provenance(
            source_uri=original.review.criteria_source_provenance.source_uri,
            source_revision="constructed-revision-2",
            source_text=pending.criteria_revision.source_text,
            criteria=criteria,
            confirmed_by="CONSTRUCTED confirmer",
            confirmed_at=datetime.now(UTC),
        ),
    )
    store.save(pending)
    return store, original, pending, snapshot, candidates


def fresh_bundle(pending, snapshot, candidates=()):
    result = retrieve_evidence_with_diagnostics(
        snapshot,
        pending.criteria_revision.criteria,
        unchanged_files=list(candidates),
    )
    findings = build_findings(
        pending.criteria_revision.criteria, result.evidence, snapshot.ingestion_state
    )
    return ReviewBundle(
        review=pending.review.model_copy(deep=True),
        source_text=pending.criteria_revision.source_text,
        criteria=pending.criteria_revision.criteria,
        evidence=result.evidence,
        retrieval_diagnostics=result.diagnostics,
        findings=findings,
        gate=evaluate_gate(
            pending.review, pending.criteria_revision.criteria, findings, [], result.evidence
        ),
    )


def complete(store, pending, snapshot, candidates, receipt, bundle=None):
    return api().attach_saved_pending_analysis(
        store,
        pending,
        bundle or fresh_bundle(pending, snapshot, candidates),
        attachment=receipt,
        snapshot=snapshot,
        candidate_files=list(candidates),
    )


def test_confirmed_pending_load_preserves_bytes_and_restores_only_recorded_paths(tmp_path):
    store, original, pending, snapshot, candidates = pending_source(
        tmp_path, paths=["src/helper.py"]
    )
    path = store.directory / f"{pending.review.review_id}.json"
    before = path.read_bytes()
    receipt = prepare(store, pending, snapshot, candidates)
    assert api().required_source_candidate_paths(pending) == ["src/helper.py"]
    assert receipt.saved_state_fingerprint == JsonReviewStore.state_fingerprint(pending)
    assert pending.bundle is None and pending.analysis_history == [original.bundle]
    assert api().validate_source_attachment(pending, receipt, snapshot, candidates) is None
    assert path.read_bytes() == before


def test_atomic_fresh_analysis_preserves_identity_and_history_without_prior_context(tmp_path):
    store, original, pending, snapshot, candidates = pending_source(
        tmp_path, paths=["src/helper.py"]
    )
    receipt = prepare(store, pending, snapshot, candidates)
    after = complete(store, pending, snapshot, candidates, receipt)
    assert after.review.review_id == original.review.review_id
    assert after.review.created_at == original.review.created_at
    assert after.criteria_revision == pending.criteria_revision
    assert after.bundle.criteria_revision_number == 2
    assert after.analysis_history == [original.bundle]
    assert after.resolution_events == original.resolution_events
    assert not after.review.final_acceptance
    for field in [
        "resolutions",
        "runtime_evidence",
        "file_scope_decisions",
        "reviewer_selected_references",
        "selected_reference_events",
        "junit_evidence_imports",
        "junit_import_events",
    ]:
        assert getattr(after.bundle, field) == []
    assert store.load(original.review.review_id) == after
    assert pending.bundle is None


def changed_audit(pending):
    event = ResolutionEvent(
        criterion_id="AC-01",
        decision=HumanDecision.CHANGE_REQUIRED,
        reviewer="CONSTRUCTED concurrent actor",
        criteria_revision_number=1,
    )
    return validated_review_state(
        pending.model_copy(
            update={
                # Keep the original latest resolution: only historical audit changes.
                "resolution_events": [event, *pending.resolution_events],
            },
            deep=True,
        )
    )


def test_pending_receipt_expires_on_prior_revision_audit_change(tmp_path):
    store, _, pending, snapshot, candidates = pending_source(tmp_path)
    receipt = prepare(store, pending, snapshot)
    changed = changed_audit(pending)
    assert api().review_source_context_fingerprint(changed) == receipt.context_fingerprint
    with pytest.raises(api().SourceAttachmentUnavailable):
        api().validate_source_attachment(changed, receipt, snapshot, candidates)


def test_external_save_race_cannot_overwrite_newer_pending_history(tmp_path):
    store, _, pending, snapshot, candidates = pending_source(tmp_path)
    receipt = prepare(store, pending, snapshot)
    changed = changed_audit(pending)
    store.save(changed)
    path = store.directory / f"{pending.review.review_id}.json"
    before = path.read_bytes()
    with pytest.raises(ValueError):
        complete(store, pending, snapshot, candidates, receipt)
    assert path.read_bytes() == before and store.load(pending.review.review_id) == changed


def test_failed_commit_does_not_install_an_analysis(tmp_path, monkeypatch):
    store, _, pending, snapshot, candidates = pending_source(tmp_path)
    receipt = prepare(store, pending, snapshot)
    path = store.directory / f"{pending.review.review_id}.json"
    before = path.read_bytes()

    def fail(_state):
        raise OSError("CONSTRUCTED write failure")

    monkeypatch.setattr(store, "_save_unlocked", fail)
    with pytest.raises(OSError):
        complete(store, pending, snapshot, candidates, receipt)
    assert path.read_bytes() == before and pending.bundle is None


@pytest.mark.parametrize(
    "field,value",
    [("head_sha", "different-head"), ("base_sha", "different-base"), ("pr_number", 123)],
)
def test_fresh_source_mismatch_keeps_pending_state_unchanged(tmp_path, field, value):
    store, _, pending, snapshot, _ = pending_source(tmp_path)
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, pending, snapshot.model_copy(update={field: value}, deep=True))
    assert store.load(pending.review.review_id) == pending


def test_latest_history_source_anchor_must_match_owner_without_fallback(tmp_path):
    store, _, pending, snapshot, _ = pending_source(tmp_path)
    pending.review.head_sha = "another-source"
    pending.review.changed_file_inventory.head_sha = pending.review.head_sha
    pending = validated_review_state(pending)
    store.save(pending)
    snapshot.head_sha = pending.review.head_sha
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, pending, snapshot)


def test_unconfirmed_revision_stays_blocked(tmp_path):
    store, _, pending, snapshot, _ = pending_source(tmp_path)
    pending = revise_criteria(
        pending, pending.criteria_revision.criteria, "CONSTRUCTED unconfirmed"
    )
    store.save(pending)
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, pending, snapshot)


def test_fresh_analysis_cannot_carry_a_recorded_decision(tmp_path):
    store, original, pending, snapshot, candidates = pending_source(tmp_path)
    receipt = prepare(store, pending, snapshot)
    bundle = fresh_bundle(pending, snapshot)
    bundle.resolutions = original.bundle.resolutions
    bundle.gate = evaluate_gate(
        bundle.review,
        bundle.criteria,
        bundle.findings,
        bundle.resolutions,
        bundle.evidence,
    )
    with pytest.raises(api().SourceAttachmentUnavailable):
        complete(store, pending, snapshot, candidates, receipt, bundle)
    assert store.load(pending.review.review_id) == pending


def test_pending_completion_cannot_replace_an_active_analysis(tmp_path):
    store, original, pending, snapshot, candidates = pending_source(tmp_path)
    receipt = prepare(store, pending, snapshot)
    with pytest.raises(api().SourceAttachmentUnavailable):
        complete(store, original, snapshot, candidates, receipt)
    assert store.load(pending.review.review_id) == pending


def test_pending_source_without_a_retained_anchor_is_unavailable(tmp_path):
    store, _, pending, snapshot, _ = pending_source(tmp_path)
    pending = validated_review_state(
        pending.model_copy(
            update={
                "analysis_history": [],
                "resolution_events": [],
            },
            deep=True,
        )
    )
    store.save(pending)
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, pending, snapshot)
