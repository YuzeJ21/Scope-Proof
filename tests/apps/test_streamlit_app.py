from pathlib import Path

from streamlit.testing.v1 import AppTest

from scopeproof_core.schemas.models import HumanDecision

APP_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "app.py"


def new_app() -> AppTest:
    return AppTest.from_file(APP_PATH).run()


def load_demo(app: AppTest) -> AppTest:
    return app.button(key="load_demo").click().run()


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
        if markdown.value.startswith("| Criterion | Requirement | Priority |")
    ]
    assert len(table_blocks) == 1
    assert "|---|---|---|---|---|---|" in table_blocks[0]
    assert "| AC-04 | Successful export records research_exported |" in table_blocks[0]


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
