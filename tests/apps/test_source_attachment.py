"""Saved source continuation is explicit, read-only and guarded on new contradictions."""

from unittest.mock import patch

import pytest

from apps.web.deferred_exports import DeferredExportUnavailable, deferred_review_export
from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.github.client import GitHubNetworkError, PrivateOrInaccessibleRepository
from scopeproof_core.reporting.exporters import export_json
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    CIObservation,
    LineChangeType,
)
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_deferred_exports import accepted_review_state
from tests.apps.test_selected_references import complete_reference
from tests.apps.test_streamlit_app import (
    analyzed_exact_head_standard_demo,
    load_demo,
    new_app,
    resolve_all_criteria,
)


def reopen(review_id):
    app = new_app().selectbox(key="saved_reopen_review_id").set_value(review_id).run()
    return app.button(key="reopen_review").click().run()


def saved_reference():
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(
        ChangedFile(
            path="src/reference_only.py",
            status="modified",
            lines=[
                ChangedLine(change_type=LineChangeType.ADDED, line_number=i, content=f"return {i}")
                for i in (7, 8, 9)
            ],
        )
    )
    app = app.run().button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    snapshot = app.session_state["snapshot"].model_copy(deep=True)
    app = complete_reference(app).button(key="save_selected_reference").click().run()
    state = app.session_state["review_state"]
    return reopen(state.review.review_id), state, snapshot


def load_matching(app, snapshot):
    # Reproduction must fail on the missing control before patching the new module.
    button = app.button(key="load_reviewed_source")
    with (
        patch("apps.web.source_attachment.load_demo_snapshot", return_value=snapshot),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=AssertionError("Constructed source must stay offline"),
        ),
    ):
        return button.click().run()


def test_reopen_load_and_repeated_reference_saves_preserve_analysis_and_saved_confirmation():
    app, before, snapshot = saved_reference()
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{before.review.review_id}.json"
    original_bytes = path.read_bytes()
    assert app.session_state["snapshot"] is None
    app = load_matching(app, snapshot)
    assert not app.exception
    assert app.session_state["review_state"] == before
    assert app.session_state["criteria_confirmed"]
    assert app.session_state["snapshot"] == snapshot
    assert path.read_bytes() == original_bytes
    assert app.button(key="run_analysis").disabled
    for number in (8, 9):
        app = (
            app.selectbox(key="selected_reference_source")
            .set_value("changed_file:src/reference_only.py")
            .run()
        )
        app = app.selectbox(key="selected_reference_line").set_value(number).run()
        app = (
            app.text_input(key="selected_reference_reviewer")
            .set_value("Constructed resumed actor")
            .run()
        )
        app = (
            app.text_area(key="selected_reference_rationale")
            .set_value("Constructed continued inspection")
            .run()
        )
        app = app.button(key="save_selected_reference").click().run()
        assert not app.exception
    after = app.session_state["review_state"].model_dump(mode="json")
    refs = after["bundle"].pop("reviewer_selected_references")
    assert [r["line_number"] for r in refs] == [7, 8, 9]
    original = before.model_dump(mode="json")
    assert refs[0] == original["bundle"].pop("reviewer_selected_references")[0]
    assert after["bundle"].pop("active_reviewer_selected_reference_ids") == [
        r["reference_id"] for r in refs
    ]
    original["bundle"].pop("active_reviewer_selected_reference_ids")
    assert after == original
    assert store.load(before.review.review_id) == app.session_state["review_state"]


def test_source_contradiction_blocks_old_ready_exports_and_survives_reopen():
    state = accepted_review_state()
    store = JsonReviewStore(default_local_review_directory())
    store.save(state)
    path = store.directory / f"{state.review.review_id}.json"
    saved = path.read_bytes()
    app = reopen(state.review.review_id)
    assert app.button(key="load_reviewed_source")
    guard = app.session_state["source_authority_guard"]
    deferred = deferred_review_export(
        state,
        export_json,
        store=store,
        expected_fingerprint=store.state_fingerprint(state),
        authority_check=lambda: guard.allows(state),
    )
    assert deferred()
    snapshot = load_demo_snapshot()
    snapshot.ci_observation = CIObservation(
        state=CheckState.FAILING,
        total_check_runs=1,
        failing_check_runs=1,
        reason="Constructed fresh CI failure",
    )
    snapshot.check_state = snapshot.ci_observation.state
    app = load_matching(app, snapshot)
    assert not app.exception
    assert app.session_state["review_state"] == state
    assert path.read_bytes() == saved
    assert not guard.allows(state)
    assert not any("**Review status: Ready**" in m.value for m in app.markdown)
    assert any("Refresh required" in m.value for m in app.markdown)
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    with pytest.raises(DeferredExportUnavailable):
        deferred()
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert not app.session_state["source_authority_guard"].allows(state)
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    app = load_matching(app, load_demo_snapshot())
    assert not app.exception
    assert app.session_state["source_authority_guard"].allows(state)
    assert path.read_bytes() == saved


def test_pending_requirements_draft_disables_attachment_without_discarding_it():
    app, _, _ = saved_reference()
    app = (
        app.text_area(key="requirements_input").set_value("Constructed unsaved requirements").run()
    )
    assert app.button(key="load_reviewed_source").disabled
    assert app.text_area(key="requirements_input").value == "Constructed unsaved requirements"


def test_new_current_head_path_still_requires_explicit_reanalysis():
    app, _, snapshot = saved_reference()
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request", return_value=snapshot
        ),
        patch("scopeproof_core.github.client.GitHubClient.fetch_candidate_files", return_value=[]),
    ):
        app = app.button(key="fetch_pr").click().run()
    assert not app.exception
    assert app.session_state["review_state"] is None
    assert not app.session_state["criteria_confirmed"]


def reopened_live_review_with_export():
    prepared = resolve_all_criteria(analyzed_exact_head_standard_demo(new_app()))
    prepared = prepared.button(key="record_final_acceptance").click().run()
    state = prepared.session_state["review_state"]
    snapshot = prepared.session_state["snapshot"].model_copy(deep=True)
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{state.review.review_id}.json"
    app = reopen(state.review.review_id)
    guard = app.session_state["source_authority_guard"]
    deferred = deferred_review_export(
        state,
        export_json,
        store=store,
        expected_fingerprint=store.state_fingerprint(state),
        authority_check=lambda: guard.allows(state),
    )
    assert deferred()
    assert app.button(key="fetch_pr").label == "Check current head"
    return app, state, snapshot, path, deferred


@pytest.mark.parametrize(
    "change",
    ["head", "same-head-checks", "same-head-counts", "invalid-head", "unrelated", "matching"],
)
def test_current_head_observation_precedes_a_failed_candidate_fetch(change):
    app, state, snapshot, path, deferred = reopened_live_review_with_export()
    before = path.read_bytes()
    app = app.text_area(key="candidate_paths").set_value("src/helper.py").run()
    if change == "head":
        snapshot.head_sha = "b" * 40
    elif change == "same-head-checks":
        snapshot.ci_observation = CIObservation(
            state=CheckState.FAILING,
            total_check_runs=1,
            failing_check_runs=1,
            reason="Constructed fresh CI failure",
        )
        snapshot.check_state = snapshot.ci_observation.state
    elif change == "same-head-counts":
        snapshot.ci_observation.total_check_runs += 1
        snapshot.ci_observation.successful_check_runs += 1
    elif change == "invalid-head":
        snapshot.head_sha = "invalid-head"
    elif change == "unrelated":
        app = app.text_input(key="pr_url").set_value(
            "https://github.com/elsewhere/example/pull/23"
        ).run()
        snapshot.repository = "elsewhere/example"
        snapshot.pr_number = 23
    elif change == "matching":
        snapshot.repository = snapshot.repository.upper()
    explanation = {
        "head": f"Observed different head: {snapshot.head_sha}",
        "same-head-checks": (
            "GitHub check details differ at the reviewed head. "
            "Saved status Passing, observed status Failing."
        ),
        "same-head-counts": (
            "GitHub check details differ at the reviewed head. Both observations report Passing."
        ),
    }.get(change)
    contradictory = explanation is not None or change == "invalid-head"

    availability = []

    def fail_candidate(*args):
        try:
            availability.append(bool(deferred()))
        except DeferredExportUnavailable:
            availability.append(False)
        raise GitHubNetworkError("Constructed candidate request failed.")

    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request", return_value=snapshot
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=fail_candidate,
        ) as fetch_candidates,
    ):
        app = app.button(key="fetch_pr").click().run()

    assert not app.exception
    fetch_candidates.assert_called_once_with(
        snapshot.repository, snapshot.head_sha, ["src/helper.py"],
    )
    assert availability == [not contradictory]
    assert app.session_state["review_state"] == state
    assert path.read_bytes() == before
    assert app.text_area(key="candidate_paths").value == "src/helper.py"
    assert any("Constructed candidate request failed." in error.value for error in app.error)
    overview = [item.value for item in app.markdown]
    if contradictory:
        assert "**Decision status: Refresh required**" in overview
        assert "**Recorded verdict: Review complete**" not in overview
        if explanation is not None:
            assert explanation in [item.value for item in app.text]
        else:
            assert not any("invalid-head" in item.value for item in app.text)
        assert all(button.disabled for button in app.download_button)
        app = app.button(key="reopen_review").click().run()
        assert "**Decision status: Refresh required**" in [item.value for item in app.markdown]
        if explanation is not None:
            assert explanation in [item.value for item in app.text]
        with pytest.raises(DeferredExportUnavailable):
            deferred()
    else:
        assert "**Recorded verdict: Review complete**" in overview
        assert all(not button.disabled for button in app.download_button)
        assert not any(
            item.value.startswith(("Observed different head:", "GitHub check details differ"))
            for item in app.text
        )


def test_successful_changed_head_reload_revokes_prior_authoritative_export():
    app, _, snapshot, path, deferred = reopened_live_review_with_export()
    before = path.read_bytes()
    snapshot.head_sha = "b" * 40
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request", return_value=snapshot
    ):
        app = app.button(key="fetch_pr").click().run()
    assert not app.exception
    assert app.session_state["snapshot"] == snapshot
    assert app.session_state["review_state"] is None
    assert not app.session_state["criteria_confirmed"]
    assert path.read_bytes() == before
    with pytest.raises(DeferredExportUnavailable):
        deferred()


@pytest.mark.parametrize("observed_non_public", [True, False])
def test_current_head_distinguishes_explicit_visibility_from_access_failure(observed_non_public):
    app, state, _, path, deferred = reopened_live_review_with_export()
    before = path.read_bytes()
    # A URL with different GitHub owner casing still identifies the same PR.
    app = app.text_input(key="pr_url").set_value(
        f"https://github.com/{state.review.repository.upper()}/pull/{state.review.pr_number}"
    ).run()
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        side_effect=PrivateOrInaccessibleRepository(
            "Constructed inaccessible repository.", observed_non_public=observed_non_public,
        ),
    ):
        app = app.button(key="fetch_pr").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == state
    assert path.read_bytes() == before
    assert ("**Decision status: Refresh required**" in [m.value for m in app.markdown]) == (
        observed_non_public
    )
    assert (
        "GitHub reported non-public repository visibility." in [item.value for item in app.text]
    ) == observed_non_public
    if observed_non_public:
        with pytest.raises(DeferredExportUnavailable):
            deferred()
    else:
        assert deferred()
