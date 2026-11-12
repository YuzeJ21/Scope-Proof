from unittest.mock import patch

from scopeproof_core.github.client import GitHubNetworkError
from scopeproof_core.schemas.models import ChangedFile, CheckState, CIObservation
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_source_attachment import load_matching, reopen
from tests.apps.test_streamlit_app import analyzed_exact_head_standard_demo, load_demo, new_app


def _contradicting_checks(snapshot):
    observation = CIObservation(
        state=CheckState.FAILING,
        total_check_runs=1,
        failing_check_runs=1,
        reason="Constructed fresh CI failure",
    )
    return snapshot.model_copy(
        update={"check_state": observation.state, "ci_observation": observation},
    )


def test_source_conflict_blocks_file_scope_save_and_allows_matching_source_recovery():
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(
        ChangedFile(path="src/unrelated.py", status="modified")
    )
    app = app.run().button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    state = app.session_state["review_state"]
    snapshot = app.session_state["snapshot"]
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()

    app = load_matching(reopen(state.review.review_id), _contradicting_checks(snapshot))
    assert "**Decision status: Refresh required**" in [item.value for item in app.markdown]
    app = app.selectbox(key="scope_file_path").set_value("src/unrelated.py").run()
    app = app.selectbox(key="scope_disposition").set_value("outside_confirmed_criteria").run()
    app = app.text_area(key="scope_note").set_value("Constructed scope decision").run()

    assert app.button(key="save_scope_decision").disabled
    assert not app.exception
    assert app.text_area(key="scope_note").value == "Constructed scope decision"
    assert app.session_state["review_state"] == store.load(state.review.review_id) == state
    assert path.read_bytes() == before

    app = app.button(key="discard_scope_decision_draft").click().run()
    app = load_matching(app, snapshot)
    assert not app.exception
    assert app.session_state["source_authority_guard"].allows(state)
    assert path.read_bytes() == before


def test_source_conflict_blocks_initial_junit_import_and_allows_current_head_re_review():
    app = analyzed_exact_head_standard_demo(new_app())
    state = app.session_state["review_state"]
    snapshot = app.session_state["snapshot"]
    store = JsonReviewStore(default_local_review_directory())
    path = store.directory / f"{state.review.review_id}.json"
    before = path.read_bytes()

    app = reopen(state.review.review_id)
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            return_value=_contradicting_checks(snapshot),
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            side_effect=GitHubNetworkError("Constructed candidate request failed."),
        ),
    ):
        app = app.button(key="fetch_pr").click().run()
    assert "**Decision status: Refresh required**" in [item.value for item in app.markdown]
    app = app.file_uploader(key="junit_artifact_upload").upload(
        "results.xml",
        b'<testsuite name="unit"><testcase name="test_export"/></testsuite>',
        "application/xml",
    ).run()
    app = app.text_input(key="junit_importer").set_value("Constructed QA").run()
    app = app.multiselect(key="junit_mapping_scopes").set_value(["suite-0001"]).run()
    app = app.selectbox(key="junit_mapping_target").set_value("AC-02").run()
    app = app.button(key="stage_junit_mapping").click().run()

    assert app.button(key="save_junit_import").disabled
    assert not app.exception
    assert app.session_state["review_state"] == store.load(state.review.review_id) == state
    assert path.read_bytes() == before

    app = app.button(key="clear_criterion_detail_drafts").click().run()
    new_head = "b" * 40
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            return_value=snapshot.model_copy(update={"head_sha": new_head}),
        ),
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_candidate_files",
            return_value=[],
        ),
    ):
        app = app.button(key="fetch_pr").click().run()
    assert not app.exception
    assert app.session_state["snapshot"].head_sha == new_head
    assert app.session_state["review_state"] is None
    assert not app.session_state["criteria_confirmed"]
    assert path.read_bytes() == before
