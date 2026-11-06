"""Requirements-only inspection preserves the saved evidence-comparison boundary."""

import pytest

from scopeproof_core.reviews import saved_comparison as api
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.saved_comparison_fixture import (
    CURRENT_HEAD,
    FOREIGN_HISTORY_HEAD,
    PREVIOUS_HEAD,
    saved_requirements_states,
)


@pytest.mark.parametrize("index, head", [(None, PREVIOUS_HEAD), (0, FOREIGN_HISTORY_HEAD)])
def test_explicit_requirements_comparison_handles_incompatible_analyses(tmp_path, index, head):
    current, baseline = saved_requirements_states()
    store = JsonReviewStore(tmp_path)
    paths = [store.save(state) for state in (current, baseline)]
    before = [path.read_bytes() for path in paths]

    with pytest.raises(ValueError, match="identical ordered criterion definitions"):
        api.prepare_saved_comparison(store, current, baseline.review.review_id, history_index=index)
    selection = api.prepare_saved_requirements_comparison(
        store, current, baseline.review.review_id, history_index=index,
    )
    with api.locked_saved_requirements_comparison(store, selection) as diff:
        assert diff.previous.review_id == baseline.review.review_id
        assert diff.previous.head_sha == head
        assert diff.current.review_id == current.review.review_id
        assert diff.current.head_sha == CURRENT_HEAD
        assert diff.source_text_changed
        assert diff.source_provenance_changed
        assert diff.criterion_changes[0].changed_fields == ["text"]
    assert [path.read_bytes() for path in paths] == before


@pytest.mark.parametrize("side", ["current", "baseline", "removed"])
def test_requirements_comparison_expires_when_either_saved_record_changes(tmp_path, side):
    current, baseline = saved_requirements_states()
    store = JsonReviewStore(tmp_path)
    store.save(current)
    store.save(baseline)
    selection = api.prepare_saved_requirements_comparison(store, current, baseline.review.review_id)
    if side == "removed":
        store.delete(baseline.review.review_id)
    else:
        affected = current if side == "current" else baseline
        store.mutate(
            affected.review.review_id,
            lambda state: append_resolution(
                state, ResolutionEvent(
                    criterion_id="AC-01", decision=HumanDecision.CHANGE_REQUIRED,
                    comment="Constructed external update",
                ),
            ),
        )
    with pytest.raises((ValueError, FileNotFoundError)), api.locked_saved_requirements_comparison(
        store, selection,
    ):
        pytest.fail("changed saved records must not render")


def test_requirements_comparison_rejects_another_pull_request(tmp_path):
    current, baseline = saved_requirements_states()
    baseline.analysis_history = []
    baseline.review.pr_number = baseline.bundle.review.pr_number = 999
    store = JsonReviewStore(tmp_path)
    store.save(current)
    store.save(baseline)
    with pytest.raises(ValueError, match="same pull request"):
        api.prepare_saved_requirements_comparison(store, current, baseline.review.review_id)
