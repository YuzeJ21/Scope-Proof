from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.web.deferred_exports import (
    DeferredExportUnavailable,
    deferred_review_export,
)
from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import export_json
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    new_review_state,
)
from scopeproof_core.schemas.models import (
    GateVerdict,
    HumanDecision,
    ResolutionEvent,
    ReviewState,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def accepted_review_state() -> ReviewState:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    for criterion in state.bundle.criteria:
        state = append_resolution(
            state,
            ResolutionEvent(
                event_id=f"accepted-{criterion.criterion_id}",
                criterion_id=criterion.criterion_id,
                decision=HumanDecision.ACCEPTED,
                comment="Deferred export fixture acceptance",
                reviewer="Fixture reviewer",
            ),
        )
    state = append_resolution(
        state,
        ResolutionEvent(
            event_id="final-acceptance",
            final_acceptance=True,
            comment="Deferred export fixture final acceptance",
            reviewer="Fixture reviewer",
        ),
    )
    assert state.bundle is not None
    assert state.bundle.gate.verdict is GateVerdict.READY
    return state


def test_deferred_export_renders_the_click_time_validated_saved_review(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = accepted_review_state()
    store.save(state)
    deferred = deferred_review_export(
        state,
        export_json,
        store=store,
        expected_fingerprint=store.state_fingerprint(state),
    )

    exported = ReviewState.model_validate(json.loads(deferred()))

    assert exported == state


def test_deferred_export_blocks_external_final_acceptance_revocation(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    accepted = accepted_review_state()
    store.save(accepted)
    deferred = deferred_review_export(
        accepted,
        export_json,
        store=store,
        expected_fingerprint=store.state_fingerprint(accepted),
    )
    revoked, _ = store.mutate(
        accepted.review.review_id,
        lambda state: append_resolution(
            state,
            ResolutionEvent(
                event_id="external-click-time-revocation",
                final_acceptance=False,
                comment="External revocation after page render",
                reviewer="CLI reviewer",
            ),
        ),
    )
    assert revoked.bundle is not None
    assert revoked.bundle.gate.verdict is not GateVerdict.READY

    with pytest.raises(
        DeferredExportUnavailable,
        match="saved review could not be revalidated",
    ):
        deferred()
