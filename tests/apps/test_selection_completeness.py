"""Reopened workbench reviews disclose recorded and historical selection limits."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import (
    JsonReviewStore,
    default_local_review_directory,
)
from tests.candidate_selection_fixture import selection_bundle

APP_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "app.py"


@pytest.mark.parametrize("legacy", [False, True], ids=["recorded-limit", "legacy-unknown"])
def test_reopened_selection_disclosure_preserves_gate_and_decisions(legacy: bool) -> None:
    state = append_resolution(
        new_review_state(selection_bundle()),
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            reviewer="Constructed fixture reviewer",
            comment="Constructed review decision; no execution claim.",
        ),
    )
    store = JsonReviewStore(default_local_review_directory())
    record_path = store.save(state)
    if legacy:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        for diagnostic in record["state"]["bundle"]["retrieval_diagnostics"]:
            for key in (
                "eligible_candidate_count", "candidate_limit", "omitted_candidate_count"
            ):
                diagnostic.pop(key, None)
        record_path.write_text(json.dumps(record), encoding="utf-8")
    before = store.load(state.review.review_id)

    app = AppTest.from_file(str(APP_PATH)).run()
    app = app.selectbox(key="saved_reopen_review_id").set_value(
        state.review.review_id
    ).run()
    app = app.button(key="reopen_review").click().run()

    assert not app.exception
    rendered = "\n".join(
        item.value for kind in (app.caption, app.text, app.markdown) for item in kind
    )
    selection = (
        "8 of 12 candidates passing search filters shown; "
        "4 omitted during selection (limit: 8)."
    )
    unknown = "Candidate selection completeness was not recorded for this review."
    assert (unknown if legacy else selection) in rendered
    assert (selection if legacy else unknown) not in rendered
    assert (
        "Search diagnostics explain retrieval; they are not evidence that the criterion "
        "is satisfied or missing from the repository."
    ) in rendered
    reopened = app.session_state["review_state"]
    assert reopened == before
    assert reopened.bundle.gate == state.bundle.gate
    assert reopened.bundle.resolutions == state.bundle.resolutions
    assert reopened.resolution_events == state.resolution_events
    assert store.load(state.review.review_id) == before
