"""Inactive source references remain history without demanding restoration reads."""

from scopeproof_core.reviews.source_attachment import (
    prepare_saved_source_attachment,
    required_source_candidate_paths,
)
from scopeproof_core.schemas.models import ReviewInputOrigin
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.reviews.test_reference_audit import withdraw
from tests.reviews.test_selected_references import source_state
from tests.reviews.test_source_attachment import unchanged_reference_state


def test_withdrawn_unchanged_reference_does_not_require_candidate_fetch():
    state, snapshot = source_state()
    selected, _ = unchanged_reference_state(state, snapshot, ["src/history_only.py"])
    assert required_source_candidate_paths(selected) == ["src/history_only.py"]
    withdrawn = withdraw(selected)
    assert required_source_candidate_paths(withdrawn) == []
    assert (
        withdrawn.bundle.reviewer_selected_references
        == selected.bundle.reviewer_selected_references
    )


def test_inactive_unchanged_history_does_not_require_source_to_reattach(tmp_path):
    state, snapshot = source_state()
    selected, _ = unchanged_reference_state(state, snapshot, ["src/history_only.py"])
    withdrawn = withdraw(selected)
    store = JsonReviewStore(tmp_path)
    store.save(withdrawn)
    before = withdrawn.model_dump_json()
    receipt = prepare_saved_source_attachment(
        store,
        withdrawn,
        snapshot=snapshot,
        candidate_files=[],
        source_origin=ReviewInputOrigin.CONSTRUCTED_DEMO,
        expected_state_fingerprint=store.state_fingerprint(withdrawn),
    )
    assert receipt.candidate_files == ()
    assert withdrawn.model_dump_json() == before


def test_withdrawal_does_not_remove_automatic_candidate_path_requirement():
    from scopeproof_core.demo import build_demo_review, load_demo_snapshot
    from scopeproof_core.reviews.lifecycle import new_review_state

    state, snapshot = new_review_state(build_demo_review()), load_demo_snapshot()
    selected, _ = unchanged_reference_state(state, snapshot, ["src/history_only.py"])
    # Existing engine candidate paths remain independently required even after
    # a manual reference to the same file is withdrawn.
    evidence = selected.bundle.evidence[0].model_copy(deep=True)
    from scopeproof_core.schemas.models import EvidenceSourceScope

    evidence.file_path = "src/automatic_context.py"
    evidence.source_scope = EvidenceSourceScope.UNCHANGED_CANDIDATE
    evidence.permalink = (
        f"https://github.com/{state.review.repository}/blob/{state.review.head_sha}/"
        f"src/automatic_context.py#L{evidence.line_start}-L{evidence.line_end}"
    )
    selected.bundle.evidence[0] = evidence
    withdrawn = withdraw(selected)
    assert required_source_candidate_paths(withdrawn) == ["src/automatic_context.py"]
