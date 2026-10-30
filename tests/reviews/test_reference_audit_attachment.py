"""Neutral audit actions must not contradict an already validated source receipt."""

import pytest

from scopeproof_core.reviews.selected_references import selectable_reference_lines
from scopeproof_core.reviews.source_attachment import (
    SourceAttachmentUnavailable,
    prepare_saved_source_attachment,
    validate_source_attachment,
)
from scopeproof_core.schemas.models import RetrievedFile, ReviewInputOrigin
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_reference_audit import correct, withdraw
from tests.reviews.test_selected_references import source_state
from tests.reviews.test_source_attachment import unchanged_reference_state


def attached(tmp_path):
    state, snapshot = source_state()
    state, candidates = unchanged_reference_state(state, snapshot, ["src/context.py"])
    store = JsonReviewStore(tmp_path)
    store.save(state)
    receipt = prepare_saved_source_attachment(
        store,
        state,
        snapshot=snapshot,
        candidate_files=candidates,
        source_origin=ReviewInputOrigin.CONSTRUCTED_DEMO,
        expected_state_fingerprint=store.state_fingerprint(state),
    )
    return state, snapshot, candidates, receipt


@pytest.mark.parametrize("operation", ["withdraw", "correct_to_changed", "correct_same_file"])
def test_retiring_candidate_reference_keeps_existing_bound_attachment_valid(tmp_path, operation):
    state, snapshot, candidates, receipt = attached(tmp_path)
    if operation == "withdraw":
        updated = withdraw(state)
    else:
        offered = selectable_reference_lines(state, snapshot, candidates)
        selected = next(
            line
            for line in offered
            if (line.file_path == "src/context.py") == (operation == "correct_same_file")
        )
        updated = correct(state, snapshot, selected=selected, unchanged_files=candidates)
    validate_source_attachment(updated, receipt, snapshot, candidates)
    assert (
        state.bundle.reviewer_selected_references[0]
        == updated.bundle.reviewer_selected_references[0]
    )


def test_new_attachment_still_requires_exact_candidate_path_set_after_withdrawal(tmp_path):
    state, snapshot, candidates, _ = attached(tmp_path)
    state = withdraw(state)
    store = JsonReviewStore(tmp_path)
    store.save(state)
    with pytest.raises(SourceAttachmentUnavailable):
        prepare_saved_source_attachment(
            store,
            state,
            snapshot=snapshot,
            candidate_files=candidates,
            source_origin=ReviewInputOrigin.CONSTRUCTED_DEMO,
            expected_state_fingerprint=store.state_fingerprint(state),
        )


@pytest.mark.parametrize("mutation", ["new_file", "wrong_head", "changed_bytes", "duplicate"])
def test_retired_reference_does_not_allow_unbound_candidate_mutation(tmp_path, mutation):
    state, snapshot, candidates, receipt = attached(tmp_path)
    state = withdraw(state)
    if mutation == "new_file":
        candidates = [
            *candidates,
            RetrievedFile(
                path="src/unrequested.py",
                content="different()",
                commit_sha=snapshot.head_sha,
                retrieval_reason="Constructed unrequested source",
            ),
        ]
    elif mutation == "duplicate":
        candidates = candidates * 2
    else:
        candidates = [
            candidates[0].model_copy(
                update={
                    "commit_sha" if mutation == "wrong_head" else "content": "different",
                }
            )
        ]
    with pytest.raises(SourceAttachmentUnavailable):
        validate_source_attachment(state, receipt, snapshot, candidates)
