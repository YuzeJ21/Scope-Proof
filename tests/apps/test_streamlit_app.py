from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.schemas.models import HumanDecision

APP_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "app.py"


def new_app() -> AppTest:
    return AppTest.from_file(APP_PATH).run()


def load_demo(app: AppTest) -> AppTest:
    return app.button(key="load_demo").click().run()


def analyzed_demo(app: AppTest) -> AppTest:
    app = load_demo(app)
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()


def saved_demo_review(app: AppTest) -> tuple[AppTest, str]:
    app = analyzed_demo(app)
    review_id = app.session_state["review_state"].review.review_id
    app = app.button(key="save_review").click().run()
    return app, review_id


def test_analysis_is_disabled_before_criteria_confirmation() -> None:
    app = new_app()
    assert app.button(key="run_analysis").disabled is True


def test_product_disclaimer_is_visible() -> None:
    app = new_app()
    markdown_text = [markdown.value for markdown in app.markdown]
    caption_text = [caption.value for caption in app.caption]
    visible_text = "\n".join(
        [*markdown_text, *caption_text]
    )
    assert "does not replace QA" in visible_text
    assert "No paid LLM API" in visible_text


def test_demo_loads_confirmable_criteria() -> None:
    app = load_demo(new_app())
    assert app.session_state["snapshot"] is not None
    assert app.session_state["criteria_confirmed"] is False
    assert len(app.text_input) >= 4
    assert app.button(key="confirm_criteria").disabled is False


def test_sidebar_reports_confirmation_and_next_action_in_same_run() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()

    sidebar_text = "\n".join(markdown.value for markdown in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text
    assert "active_step" not in app.session_state.filtered_state


def test_sidebar_reports_analysis_and_review_availability() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    sidebar_text = "\n".join(markdown.value for markdown in app.sidebar.markdown)
    assert "Complete — Analysis generated" in sidebar_text
    assert "Complete — Review and export available" in sidebar_text


def test_demo_flow_reaches_blocked_summary() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    assert app.session_state["criteria_confirmed"] is True
    app = app.button(key="run_analysis").click().run()
    visible_text = "\n".join(markdown.value for markdown in app.markdown)
    assert "Blocked" in visible_text
    assert "Partial" in visible_text
    assert "Missing" in visible_text
    assert app.session_state["bundle"] is not None


def test_demo_summary_explains_non_prescriptive_next_actions() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    visible_text = "\n".join(markdown.value for markdown in app.markdown)
    assert "What to do next" in visible_text
    assert "unresolved criteria: AC-01" in visible_text
    assert "ScopeProof does not decide them" in visible_text
    assert "blocking_criteria" in visible_text


def test_demo_summary_requires_explicit_resolution_decision() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    assert len(app.download_button) == 3
    assert app.selectbox(key="resolution_decision").value is None
    assert app.button(key="save_resolution").disabled is True


def test_optional_token_uses_password_input() -> None:
    app = new_app()
    token = app.text_input(key="github_token")
    assert token.proto.type == token.proto.PASSWORD


def test_demo_can_save_and_reopen_durable_review_state() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    review_id = app.session_state["review_state"].review.review_id

    app = app.button(key="save_review").click().run()
    assert "Review saved locally" in "\n".join(message.value for message in app.success)
    app = app.text_input(key="reopen_review_id").set_value(review_id).run()
    app = app.button(key="reopen_review").click().run()

    assert app.session_state["review_state"].review.review_id == review_id
    success_text = "\n".join(message.value for message in app.success)
    assert "Review reopened from local storage" in success_text


def test_current_review_id_is_copyable_and_used_in_save_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    review_id = app.session_state["review_state"].review.review_id

    assert review_id in [item.value for item in app.code]
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Current review ID" in caption_text
    assert "save this review before using the ID in a future session" in caption_text

    app = app.button(key="save_review").click().run()
    assert f"Review saved locally. ID: {review_id}." in [item.value for item in app.success]


def test_saved_review_can_be_reopened_from_a_fresh_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_state = saved.session_state["review_state"]

    fresh = new_app()
    assert fresh.text_input(key="reopen_review_id").value == ""
    fresh = fresh.text_input(key="reopen_review_id").set_value(review_id).run()
    fresh = fresh.button(key="reopen_review").click().run()

    reopened = fresh.session_state["review_state"]
    assert reopened == saved_state
    assert fresh.session_state["bundle"] == saved_state.bundle
    assert fresh.session_state["criteria"] == saved_state.criteria_revision.criteria
    assert fresh.session_state["criteria_confirmed"] is True
    assert fresh.session_state["source_text"] == saved_state.criteria_revision.source_text
    assert (
        fresh.text_area(key="requirements_input").value
        == saved_state.criteria_revision.source_text
    )
    assert fresh.session_state["snapshot"] is None
    assert fresh.button(key="run_analysis").disabled is True
    assert len(fresh.download_button) == 3
    assert review_id in [item.value for item in fresh.code]


def test_reopening_clears_an_unrelated_loaded_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())

    app = load_demo(new_app())
    assert app.session_state["snapshot"] is not None
    app = app.text_input(key="reopen_review_id").set_value(review_id).run()
    app = app.button(key="reopen_review").click().run()

    assert app.session_state["snapshot"] is None
    assert app.button(key="run_analysis").disabled is True
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Next — Reload source to rerun analysis" in sidebar_text


def test_reopened_review_reports_changed_head_before_invalidating_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_head = saved.session_state["review_state"].review.head_sha
    changed_head = "changed-head-for-regression"
    changed_snapshot = load_demo_snapshot().model_copy(update={"head_sha": changed_head})

    fresh = new_app()
    fresh = fresh.text_input(key="reopen_review_id").set_value(review_id).run()
    fresh = fresh.button(key="reopen_review").click().run()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=changed_snapshot):
        fresh = fresh.button(key="load_demo").click().run()

    warning_text = "\n".join(item.value for item in fresh.warning)
    assert saved_head in warning_text
    assert changed_head in warning_text
    assert "saved evidence remains anchored" in warning_text
    assert fresh.session_state["review_state"] is None
    assert fresh.session_state["bundle"] is None
    assert fresh.session_state["criteria_confirmed"] is False
    assert fresh.button(key="run_analysis").disabled is True


def test_reopened_review_reports_same_head_before_reanalysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_head = saved.session_state["review_state"].review.head_sha

    fresh = new_app()
    fresh = fresh.text_input(key="reopen_review_id").set_value(review_id).run()
    fresh = fresh.button(key="reopen_review").click().run()
    fresh = fresh.button(key="load_demo").click().run()

    info_text = "\n".join(item.value for item in fresh.info)
    assert f"same head SHA: {saved_head}" in info_text
    assert fresh.session_state["review_state"] is None
    assert fresh.session_state["criteria_confirmed"] is False
    assert fresh.button(key="run_analysis").disabled is True


def test_reopened_review_does_not_compare_a_different_pull_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    unrelated_snapshot = load_demo_snapshot().model_copy(update={"pr_number": 999})

    fresh = new_app()
    fresh = fresh.text_input(key="reopen_review_id").set_value(review_id).run()
    fresh = fresh.button(key="reopen_review").click().run()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=unrelated_snapshot):
        fresh = fresh.button(key="load_demo").click().run()

    assert fresh.session_state.filtered_state.get("source_reload_notice", "missing") is None
    assert not any("PR head changed" in item.value for item in fresh.warning)


def test_missing_saved_review_has_safe_recovery_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()
    app = app.text_input(key="reopen_review_id").set_value("missing-review").run()
    app = app.button(key="reopen_review").click().run()

    assert [item.value for item in app.error] == [
        "No saved review was found for that review ID."
    ]
    assert app.session_state["review_state"] is None
    assert app.session_state["bundle"] is None


def test_final_acceptance_control_is_visible_only_after_analysis() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert app.button(key="record_final_acceptance").disabled is False


def test_criteria_can_be_added_and_removed_before_reconfirmation() -> None:
    app = load_demo(new_app())
    app = app.text_input(key="new_criterion_text").set_value("Document export format").run()
    app = app.button(key="add_criterion_ui").click().run()

    assert len(app.session_state["criteria"]) == 5
    assert app.session_state["criteria"][-1].criterion_id == "AC-05"
    assert app.session_state["criteria_confirmed"] is False

    app = app.button(key="remove_AC-05").click().run()
    assert len(app.session_state["criteria"]) == 4


def test_evidence_matrix_exposes_status_and_priority_filters() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert app.multiselect(key="status_filter").value == []
    assert app.multiselect(key="priority_filter").value == []


def test_evidence_matrix_renders_as_one_markdown_table() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    table_blocks = [
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith(
            "| Criterion | Requirement | Priority | Status | Evidence | Confidence | Count |"
        )
    ]
    assert len(table_blocks) == 1
    assert "|---|---|---|---|---|---|---|---|---|" in table_blocks[0]
    assert "| AC-01 | User can export the research list as CSV |" in table_blocks[0]
    assert "| High | 4 | Strong candidate evidence was found;" in table_blocks[0]
    assert "| Unresolved |" in table_blocks[0]
    assert "| AC-04 | Successful export records research_exported |" in table_blocks[0]


def test_evidence_matrix_shows_current_human_resolution() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()
    app = app.run()

    table = next(
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith("| Criterion | Requirement | Priority |")
    )
    ac_01_row = next(line for line in table.splitlines() if line.startswith("| AC-01 |"))
    assert ac_01_row.endswith("| Accepted |")


def test_compound_criterion_can_be_split_in_workbench() -> None:
    app = new_app()
    app = app.text_area(key="requirements_input").set_value("Export CSV and record analytics").run()
    app = app.button(key="prepare_criteria").click().run()
    app = app.text_area(key="split_criterion_text").set_value("Export CSV\nRecord analytics").run()
    app = app.button(key="split_criterion_ui").click().run()

    assert [(item.criterion_id, item.text) for item in app.session_state["criteria"]] == [
        ("AC-01", "Export CSV"),
        ("AC-02", "Record analytics"),
    ]


def test_human_decision_and_final_acceptance_append_history() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()
    app = app.button(key="record_final_acceptance").click().run()

    state = app.session_state["review_state"]
    assert len(state.resolution_events) == 2
    assert state.review.final_acceptance is True
    assert "Resolution history" in "\n".join(markdown.value for markdown in app.markdown)


def test_runtime_evidence_save_requires_all_required_fields() -> None:
    app = analyzed_demo(new_app())
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value("   ").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()
    assert app.button(key="save_runtime_evidence").disabled is False


def test_runtime_evidence_prerequisite_guidance_is_visible() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(caption.value for caption in app.caption)
    assert (
        "Artifact, scenario, environment, observed result, and reviewer are required"
        in caption_text
    )
    assert "Limitations are optional" in caption_text


def test_manual_runtime_evidence_can_be_recorded_without_changing_static_findings() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    finding_status = app.session_state["review_state"].bundle.findings[0].status
    app = app.text_input(key="runtime_artifact_reference").set_value("https://example.test/run/1").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    app = app.button(key="save_runtime_evidence").click().run()

    bundle = app.session_state["review_state"].bundle
    assert bundle.findings[0].status is finding_status
    assert bundle.runtime_evidence[0].artifact_reference.endswith("/1")
