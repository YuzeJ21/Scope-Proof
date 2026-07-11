from pathlib import Path

from streamlit.testing.v1 import AppTest

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


def test_demo_summary_has_three_exports_and_resolution_control() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    assert len(app.download_button) == 3
    assert app.button(key="save_resolution").disabled is False


def test_optional_token_uses_password_input() -> None:
    app = new_app()
    token = app.text_input(key="github_token")
    assert token.proto.type == token.proto.PASSWORD
