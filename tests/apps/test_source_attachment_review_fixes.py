"""Constructed review regressions preserve source observations and explicit reanalysis."""

from unittest.mock import patch

import httpx
import pytest

from apps.web.deferred_exports import DeferredExportUnavailable
from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.github.client import GitHubClient
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import CheckState, CIObservation, HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_source_attachment import load_matching, reopen, saved_reference
from tests.apps.test_source_attachment_safety import queued_export, simulated_live_saved_source
from tests.apps.test_streamlit_app import analyzed_demo, new_app, runtime_key


@pytest.mark.parametrize(
    "metadata",
    [
        {"private": True, "visibility": "public"},
        {"private": False, "visibility": "private"},
        {"private": False, "visibility": "internal"},
    ],
)
def test_observed_non_public_source_blocks_saved_authority_and_queued_export(metadata):
    app, state, _, _, store = simulated_live_saved_source()
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    export = queued_export(app, state, store)
    assert export()

    def fetch_non_public(_url):
        return GitHubClient._verified_repository_visibility(
            {"base": {"repo": {"full_name": state.review.repository, **metadata}}},
            expected_repository=state.review.repository,
        )

    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=fetch_non_public,
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=AssertionError("Observed non-public source must not load candidates"),
        ),
    ):
        app = app.button(key="load_reviewed_source").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == state
    assert path.read_bytes() == before
    assert app.session_state["review_source_attachment"] is None
    assert not app.session_state["source_authority_guard"].allows(state)
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    with pytest.raises(DeferredExportUnavailable):
        export()


def test_unavailable_403_source_does_not_invent_non_public_observation_or_block_authority():
    app, state, _, _, store = simulated_live_saved_source()
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()
    export = queued_export(app, state, store)

    def fetch_inaccessible(_url):
        response = httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "10"},
            request=httpx.Request(
                "GET", "https://api.github.com/repos/constructed/repository/pulls/1"
            ),
        )
        GitHubClient._raise_for_pr(response)

    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=fetch_inaccessible,
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=AssertionError("No source snapshot was obtained"),
        ),
    ):
        app = app.button(key="load_reviewed_source").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == state
    assert path.read_bytes() == before
    assert app.session_state["source_authority_guard"].allows(state)
    assert all(not b.disabled for b in app.download_button if b.key.startswith("download_"))
    assert export()


def _load_contradictory_ci(app):
    contradictory_snapshot = load_demo_snapshot()
    contradictory_snapshot.check_state = CheckState.FAILING
    contradictory_snapshot.ci_observation = CIObservation(
        state=CheckState.FAILING,
        total_check_runs=1,
        failing_check_runs=1,
        reason="Constructed fresh CI failure",
    )
    return load_matching(app, contradictory_snapshot)


def _stage_criterion_save(app, save_key):
    if save_key == "save_resolution":
        app.selectbox(key="resolution_decision").set_value(HumanDecision.CHANGE_REQUIRED)
        app.text_area(key="resolution_note").set_value("Constructed reviewer decision")
    else:
        app.text_input(key=runtime_key(app, "runtime_artifact_reference")).set_value(
            "constructed-run"
        )
        app.text_area(key=runtime_key(app, "runtime_scenario")).set_value(
            "Export configured columns"
        )
        app.text_input(key=runtime_key(app, "runtime_environment")).set_value(
            "Controlled environment"
        )
        app.text_input(key=runtime_key(app, "runtime_result")).set_value(
            "Observed exported columns"
        )
        app.text_input(key=runtime_key(app, "runtime_reviewer")).set_value("Constructed reviewer")
    return app.run()


def _criterion_save_button(app, save_key):
    key = runtime_key(app, save_key) if save_key == "save_runtime_evidence" else save_key
    return app.button(key=key)


def _submit_stale_save_click(app, save_key):
    button = _criterion_save_button(app, save_key)
    # Model a click queued by a client before it received the new disabled state.
    button.proto.disabled = False
    return button.click().run()


@pytest.mark.parametrize("save_key", ["save_resolution", "save_runtime_evidence"])
def test_observed_source_conflict_rejects_criterion_save_without_mutation(save_key):
    analyzed = analyzed_demo(new_app())
    state = analyzed.session_state["review_state"].model_copy(deep=True)
    review_id = state.review.review_id
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{review_id}.json"
    before = path.read_bytes()
    app = _load_contradictory_ci(reopen(review_id))
    assert not app.exception
    assert not app.session_state["source_authority_guard"].allows(state)

    app = _stage_criterion_save(app, save_key)
    assert _criterion_save_button(app, save_key).disabled
    app = _submit_stale_save_click(app, save_key)

    assert not app.exception
    assert app.session_state["review_state"] == state
    assert app.session_state["bundle"] == state.bundle
    assert path.read_bytes() == before
    assert store.load(review_id) == state
    assert _criterion_save_button(app, save_key).disabled

    app = app.button(key="clear_criterion_detail_drafts").click().run()
    assert not app.session_state["source_authority_guard"].allows(state)
    app = load_matching(app, load_demo_snapshot())
    assert not app.exception
    assert app.session_state["source_authority_guard"].allows(state)
    assert path.read_bytes() == before

    app = _stage_criterion_save(app, save_key)
    assert not _criterion_save_button(app, save_key).disabled
    app = _criterion_save_button(app, save_key).click().run()
    assert not app.exception
    after = app.session_state["review_state"]
    assert len(after.resolution_events) == 1
    assert store.load(review_id) == after


def test_observed_source_conflict_prevents_autosave_of_unsaved_review_state():
    analyzed = analyzed_demo(new_app())
    state = analyzed.session_state["review_state"].model_copy(deep=True)
    review_id = state.review.review_id
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{review_id}.json"
    before = path.read_bytes()
    app = _load_contradictory_ci(reopen(review_id))

    unsaved = append_resolution(
        state,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            reviewer="Constructed reviewer",
            comment="Earlier in-memory update that must not autosave after the conflict",
        ),
    )
    assert not app.session_state["source_authority_guard"].allows(unsaved)
    app.session_state["review_state"] = unsaved
    app.session_state["bundle"] = unsaved.bundle
    app = app.run()

    assert not app.exception
    assert path.read_bytes() == before
    assert store.load(review_id) == state
    assert app.session_state["review_state"] == unsaved
    assert app.session_state["bundle"] == unsaved.bundle
    assert app.button(key="save_review").disabled

    app = _submit_stale_save_click(app, "save_review")
    assert not app.exception
    assert path.read_bytes() == before
    assert store.load(review_id) == state
    assert app.session_state["review_state"] == unsaved


@pytest.mark.parametrize("edited_key", ["criterion_text_AC-01", "criteria_source_revision"])
def test_explicit_criteria_reconfirmation_clears_receipt_preserves_source_and_allows_reanalysis(
    edited_key,
):
    _, original, snapshot = saved_reference()
    original = append_resolution(
        original,
        ResolutionEvent(
            criterion_id="AC-01",
            decision=HumanDecision.CHANGE_REQUIRED,
            reviewer="Constructed prior-revision decision reviewer",
            comment="Keep this historical decision when the criteria are explicitly revised.",
        ),
    )
    store = JsonReviewStore(default_local_review_directory())
    store.save(original)
    app = load_matching(reopen(original.review.review_id), snapshot)
    assert not app.exception
    assert app.session_state["review_source_attachment"] is not None
    assert app.session_state["snapshot"] == snapshot
    edited_value = (
        "The constructed CSV export retains the selected columns."
        if edited_key == "criterion_text_AC-01"
        else "constructed-source-revision@second"
    )
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=AssertionError("Criteria reanalysis must use already loaded source"),
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=AssertionError("Criteria reanalysis must not refetch candidate source"),
        ),
    ):
        app = app.text_input(key=edited_key).set_value(edited_value).run()
        app = app.button(key="confirm_criteria").click().run()
        assert not app.exception
        pending = app.session_state["review_state"]
        assert pending.criteria_revision.confirmed
        assert pending.bundle is None
        assert app.session_state["review_source_attachment"] is None
        assert app.session_state["snapshot"] == snapshot
        assert app.session_state["criteria_confirmed"]
        assert app.session_state["source_authority_guard"].allows(pending)
        assert not app.button(key="run_analysis").disabled
        assert pending.analysis_history[-1] == original.bundle
        assert pending.resolution_events == original.resolution_events
        assert not pending.review.final_acceptance
        app = app.button(key="run_analysis").click().run()
    assert not app.exception
    after = app.session_state["review_state"]
    assert after.review.review_id == original.review.review_id
    assert after.criteria_revision.number == original.criteria_revision.number + 1
    assert after.analysis_history[-1] == original.bundle
    assert after.resolution_events == original.resolution_events
    assert after.bundle.reviewer_selected_references == []
    assert after.bundle.resolutions == []
    assert not after.review.final_acceptance
    assert store.load(original.review.review_id) == after
