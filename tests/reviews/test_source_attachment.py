"""Saved source continuation preserves review truth and rejects stale authority."""

from __future__ import annotations

from importlib import import_module

import pytest

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.lifecycle import append_resolution, revise_criteria
from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    EvidenceSourceScope,
    HumanDecision,
    IngestionState,
    RepositoryVisibility,
    ResolutionEvent,
    RetrievedFile,
    ReviewInputOrigin,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_selected_references import append, source_state


def api():
    return import_module("scopeproof_core.reviews.source_attachment")


def saved_source(tmp_path):
    state, snapshot = source_state()
    store = JsonReviewStore(tmp_path / "reviews")
    store.save(state)
    return store, state, snapshot


def prepare(store, state, snapshot, candidates=None, **kwargs):
    return api().prepare_saved_source_attachment(
        store,
        state,
        snapshot=snapshot,
        candidate_files=candidates or [],
        source_origin=kwargs.pop("source_origin", ReviewInputOrigin.CONSTRUCTED_DEMO),
        expected_state_fingerprint=kwargs.pop(
            "expected_state_fingerprint", JsonReviewStore.state_fingerprint(state)
        ),
        **kwargs,
    )


def unchanged_reference_state(state, snapshot, paths):
    candidates = [
        RetrievedFile(
            path=path,
            content="explicit_context()",
            commit_sha=snapshot.head_sha,
            retrieval_reason="Constructed already-ingested source",
        )
        for path in paths
    ]
    module = import_module("scopeproof_core.reviews.selected_references")
    for candidate in candidates:
        selected = next(
            line
            for line in module.selectable_reference_lines(state, snapshot, candidates)
            if line.file_path == candidate.path
        )
        state = append(state, snapshot, selected, unchanged_files=candidates)
    return state, candidates


def test_matching_attachment_preserves_saved_bytes_review_and_criteria(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    before = state.model_dump_json()
    path = store.directory / f"{state.review.review_id}.json"
    saved_bytes = path.read_bytes()
    receipt = prepare(store, state, snapshot)
    assert isinstance(receipt, api().ReviewSourceAttachment)
    assert receipt.review_id == state.review.review_id
    assert receipt.saved_state_fingerprint == JsonReviewStore.state_fingerprint(state)
    assert receipt.source_origin == ReviewInputOrigin.CONSTRUCTED_DEMO
    assert receipt.snapshot == snapshot
    assert not receipt.candidate_files
    assert api().validate_source_attachment(state, receipt, snapshot, []) is None
    assert state.model_dump_json() == before
    assert path.read_bytes() == saved_bytes


def test_same_head_selected_reference_excerpt_contradiction_blocks_attachment(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    state = append(state, snapshot)
    store.save(state)
    saved_reference = state.bundle.reviewer_selected_references[0]
    fresh = snapshot.model_copy(deep=True)
    line = next(
        line for line in fresh.files[0].lines if line.line_number == saved_reference.line_number
    )
    line.content = "different_raw_context = 99"
    assert fresh.scope_inventory() == state.review.changed_file_inventory
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    with pytest.raises(api().SourceAttachmentUnavailable) as caught:
        prepare(store, state, fresh)
    assert caught.value.observed_conflict is True
    assert path.read_bytes() == before
    assert state.bundle.reviewer_selected_references == [saved_reference]


def test_matching_metadata_cannot_restore_selected_reference_from_ambiguous_patch(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    state = append(state, snapshot)
    store.save(state)
    fresh = snapshot.model_copy(deep=True)
    fresh.files[0].patch = "@@ -1 +1 @@\n+ambiguous\u2028line\n"
    assert fresh.scope_inventory() == state.review.changed_file_inventory
    with pytest.raises(api().SourceAttachmentUnavailable) as caught:
        prepare(store, state, fresh)
    assert caught.value.observed_conflict is True
    assert store.load(state.review.review_id) == state


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository", "another/repository"),
        ("pr_number", 111),
        ("base_sha", "another-base"),
        ("head_sha", "another-head"),
        ("repository_visibility", RepositoryVisibility.VERIFIED_PUBLIC),
        ("ingestion_state", IngestionState.PARTIAL),
        ("warnings", ["Fresh ingestion limitation"]),
        ("skipped_files", ["src/missing.py"]),
    ],
)
def test_observed_source_fact_mismatch_refuses_without_touching_review(tmp_path, field, value):
    store, state, snapshot = saved_source(tmp_path)
    changed = snapshot.model_copy(update={field: value}, deep=True)
    before = state.model_dump_json()
    path = store.directory / f"{state.review.review_id}.json"
    saved_bytes = path.read_bytes()
    with pytest.raises(api().SourceAttachmentUnavailable) as caught:
        prepare(store, state, changed)
    assert caught.value.observed_conflict is True
    assert state.model_dump_json() == before
    assert path.read_bytes() == saved_bytes


@pytest.mark.parametrize("change", ["rename", "extra_file", "truncated"])
def test_inventory_and_truncation_cannot_be_hidden_by_matching_head(tmp_path, change):
    store, state, snapshot = saved_source(tmp_path)
    changed = snapshot.model_copy(deep=True)
    if change == "rename":
        changed.files[0].previous_path = "src/previous.py"
    elif change == "extra_file":
        extra = changed.files[0].model_copy(update={"path": "src/extra.py"}, deep=True)
        changed.files.append(extra)
    else:
        changed.files[0].truncated = True
    with pytest.raises(api().SourceAttachmentUnavailable) as caught:
        prepare(store, state, changed)
    assert caught.value.observed_conflict is True


@pytest.mark.parametrize("change", ["failing", "pending", "passing_counts", "collection_notes"])
def test_full_fresh_ci_observation_must_match_not_just_head_or_passing(tmp_path, change):
    store, state, snapshot = saved_source(tmp_path)
    changed = snapshot.model_copy(deep=True)
    observation = snapshot.ci_observation.model_dump(mode="python")
    if change in {"failing", "pending"}:
        observation.update(successful_check_runs=0)
        observation[f"{change}_check_runs"] = 1
        observation["state"] = CheckState.FAILING if change == "failing" else CheckState.PENDING
        changed.check_state = observation["state"]
    elif change == "passing_counts":
        observation.update(total_check_runs=2, successful_check_runs=2)
    else:
        observation["collection_notes"] = ["Additional observed limitation"]
        observation["collection_complete"] = False
        observation["state"] = CheckState.UNAVAILABLE
    changed.ci_observation = CIObservation.model_validate(observation)
    changed.check_state = changed.ci_observation.state
    with pytest.raises(api().SourceAttachmentUnavailable) as caught:
        prepare(store, state, changed)
    assert caught.value.observed_conflict is True


def test_mutable_pr_description_and_fetch_time_do_not_replace_saved_review(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    changed = snapshot.model_copy(update={"title": "New title", "description": "New description"})
    receipt = prepare(store, state, changed)
    assert api().validate_source_attachment(state, receipt, changed, []) is None
    assert store.load(state.review.review_id) == state


@pytest.mark.parametrize(
    "origin",
    [
        ReviewInputOrigin.LIVE_PUBLIC_GITHUB,
        ReviewInputOrigin.LOCAL_FIXTURE,
        ReviewInputOrigin.LEGACY_UNKNOWN,
    ],
)
def test_source_origin_never_relabels_constructed_saved_analysis(tmp_path, origin):
    store, state, snapshot = saved_source(tmp_path)
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, state, snapshot, source_origin=origin)


def test_explicit_verified_public_live_source_is_supported(tmp_path):
    from scopeproof_core.demo import build_review, load_demo_labels
    from scopeproof_core.reviews.lifecycle import new_review_state

    _, snapshot = source_state()
    snapshot = snapshot.model_copy(
        update={
            "repository_visibility": RepositoryVisibility.VERIFIED_PUBLIC,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
        },
        deep=True,
    )
    bundle = build_review(snapshot, load_demo_labels())
    bundle.review.input_origin = ReviewInputOrigin.LIVE_PUBLIC_GITHUB
    bundle.review.repository_visibility = RepositoryVisibility.VERIFIED_PUBLIC
    state = new_review_state(bundle)
    store = JsonReviewStore(tmp_path / "reviews")
    store.save(state)
    receipt = prepare(store, state, snapshot, source_origin=ReviewInputOrigin.LIVE_PUBLIC_GITHUB)
    assert api().validate_source_attachment(state, receipt, snapshot, []) is None


def test_selected_reference_only_unchanged_paths_are_required_and_restored(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    state, candidates = unchanged_reference_state(state, snapshot, ["src/z.py", "src/a.py"])
    assert state.bundle.evidence == []
    store.save(state)
    assert api().required_source_candidate_paths(state) == ["src/a.py", "src/z.py"]
    receipt = prepare(store, state, snapshot, candidates)
    assert {f.path for f in receipt.candidate_files} == {"src/a.py", "src/z.py"}
    assert api().validate_source_attachment(state, receipt, snapshot, candidates) is None


def test_candidate_paths_union_automatic_and_selected_sources_without_duplicates(tmp_path):
    from scopeproof_core.gates.evaluator import evaluate_gate
    from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
    from scopeproof_core.verification.service import build_findings

    store, state, snapshot = saved_source(tmp_path)
    automatic = RetrievedFile(
        path="src/automatic.py",
        content=state.criteria_revision.criteria[0].text,
        commit_sha=snapshot.head_sha,
        retrieval_reason="Constructed automatic source",
    )
    result = retrieve_evidence_with_diagnostics(
        snapshot, state.bundle.criteria, unchanged_files=[automatic]
    )
    assert {e.file_path for e in result.evidence} == {"src/automatic.py"}
    state.bundle.evidence = result.evidence
    state.bundle.retrieval_diagnostics = result.diagnostics
    state.bundle.findings = build_findings(
        state.bundle.criteria, result.evidence, snapshot.ingestion_state
    )
    state.bundle.gate = evaluate_gate(
        state.review, state.bundle.criteria, state.bundle.findings, [], result.evidence
    )
    state = validated_review_state(state)
    state, selected_candidates = unchanged_reference_state(state, snapshot, ["src/selected.py"])
    candidates = [automatic, selected_candidates[0]]
    selected = next(
        line
        for line in import_module(
            "scopeproof_core.reviews.selected_references"
        ).selectable_reference_lines(state, snapshot, candidates)
        if line.file_path == "src/automatic.py"
    )
    state = append(state, snapshot, selected, unchanged_files=candidates)
    store.save(state)
    assert api().required_source_candidate_paths(state) == ["src/automatic.py", "src/selected.py"]
    assert prepare(store, state, snapshot, candidates).review_id == state.review.review_id


def test_candidate_byte_limit_applies_to_total_utf8_bytes_across_files(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    state, candidates = unchanged_reference_state(state, snapshot, ["src/a.py", "src/b.py"])
    store.save(state)
    for candidate in candidates:
        candidate.content += "\n" + "é" * 50001
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, state, snapshot, candidates)


def test_source_attachment_requires_known_saved_inventory(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    state.review.changed_file_inventory = None
    state.bundle.review.changed_file_inventory = None
    store.save(state)
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, state, snapshot)


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate",
        "unexpected",
        "wrong_head",
        "wrong_scope",
        "noncanonical",
        "oversize_utf8",
    ],
)
def test_unchanged_response_is_exact_bounded_and_canonical(tmp_path, change):
    store, state, snapshot = saved_source(tmp_path)
    state, candidates = unchanged_reference_state(state, snapshot, ["src/helper.py"])
    store.save(state)
    changed = [f.model_copy(deep=True) for f in candidates]
    if change == "missing":
        changed = []
    elif change == "duplicate":
        changed.append(changed[0].model_copy(deep=True))
    elif change == "unexpected":
        changed.append(changed[0].model_copy(update={"path": "src/other.py"}))
    elif change == "wrong_head":
        changed[0].commit_sha = "wrong-head"
    elif change == "wrong_scope":
        changed[0].source_scope = EvidenceSourceScope.CHANGED_FILE
    elif change == "noncanonical":
        changed[0].path = "src/../helper.py"
    else:
        changed[0].content += "\n" + "é" * 100001
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, state, snapshot, changed)


def test_more_than_eight_explicit_unchanged_sources_fails_instead_of_truncating(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    state, candidates = unchanged_reference_state(
        state, snapshot, [f"src/helper_{n}.py" for n in range(9)]
    )
    store.save(state)
    with pytest.raises(api().SourceAttachmentUnavailable):
        api().required_source_candidate_paths(state)
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, state, snapshot, candidates)


@pytest.mark.parametrize("stale", ["current", "persisted", "expected"])
def test_fetch_time_compare_and_swap_rejects_staleness_without_source_conflict(tmp_path, stale):
    store, state, snapshot = saved_source(tmp_path)
    expected = JsonReviewStore.state_fingerprint(state)
    updated = append_resolution(
        state,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            reviewer="Concurrent constructed reviewer",
            comment="Keep this newer decision.",
        ),
    )
    if stale == "persisted":
        store.save(updated)
    elif stale == "current":
        state = updated
    else:
        expected = "0" * 64
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    with pytest.raises(api().SourceAttachmentUnavailable) as caught:
        prepare(store, state, snapshot, expected_state_fingerprint=expected)
    assert caught.value.observed_conflict is False
    assert path.read_bytes() == before


def test_source_neutral_reference_and_decision_appends_keep_receipt_valid(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    receipt = prepare(store, state, snapshot)
    context = api().review_source_context_fingerprint(state)
    updated = append(state, snapshot)
    updated = append_resolution(
        updated,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            reviewer="Constructed reviewer",
            comment="Explicit decision after inspecting source.",
        ),
    )
    updated = append(
        state=updated,
        snapshot=snapshot,
        selected=import_module(
            "scopeproof_core.reviews.selected_references"
        ).selectable_reference_lines(updated, snapshot)[1],
    )
    assert JsonReviewStore.state_fingerprint(updated) != receipt.saved_state_fingerprint
    assert api().review_source_context_fingerprint(updated) == context
    assert api().validate_source_attachment(updated, receipt, snapshot, []) is None


@pytest.mark.parametrize("change", ["source_text", "producer", "review_head"])
def test_source_context_change_expires_receipt(tmp_path, change):
    store, state, snapshot = saved_source(tmp_path)
    receipt = prepare(store, state, snapshot)
    changed = state.model_copy(deep=True)
    if change == "source_text":
        changed = revise_criteria(state, state.criteria_revision.criteria, "Revised requirements")
    else:
        field = "tool_version" if change == "producer" else "head_sha"
        value = "0.0.0-other" if change == "producer" else "other-head"
        setattr(changed.review, field, value)
        setattr(changed.bundle.review, field, value)
    with pytest.raises(api().SourceAttachmentUnavailable):
        api().validate_source_attachment(changed, receipt, snapshot, [])


@pytest.mark.parametrize("change", ["snapshot", "candidate", "receipt"])
def test_source_and_receipt_model_tampering_is_revalidated(tmp_path, change):
    store, state, snapshot = saved_source(tmp_path)
    state, candidates = unchanged_reference_state(state, snapshot, ["src/helper.py"])
    store.save(state)
    receipt = prepare(store, state, snapshot, candidates)
    if change == "snapshot":
        snapshot.files[0].lines[0].content = "tampered after attachment"
    elif change == "candidate":
        candidates[0].content = "tampered after attachment"
    else:
        receipt = receipt.model_copy(update={"source_fingerprint": "0" * 64})
    with pytest.raises(api().SourceAttachmentUnavailable):
        api().validate_source_attachment(state, receipt, snapshot, candidates)


def test_invalid_mutated_source_model_cannot_bypass_boundary_validation(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    snapshot.pr_number = 0
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, state, snapshot)


def test_pending_criteria_revision_has_no_attachable_analysis(tmp_path):
    store, state, snapshot = saved_source(tmp_path)
    state = revise_criteria(state, state.criteria_revision.criteria, "Pending requirements")
    assert validated_review_state(state).bundle is None
    store.save(state)
    with pytest.raises(api().SourceAttachmentUnavailable):
        prepare(store, state, snapshot)
