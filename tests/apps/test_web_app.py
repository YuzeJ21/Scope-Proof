"""Regression checks for the local Streamlit workbench."""

from pathlib import Path


def test_requirements_widget_uses_session_state_without_a_second_default() -> None:
    app_source = Path("apps/web/app.py").read_text(encoding="utf-8")

    assert 'key="requirements_input"' in app_source
    assert '"requirements_input": ""' in app_source
    assert 'value=st.session_state["source_text"]' not in app_source
