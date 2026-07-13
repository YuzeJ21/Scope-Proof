"""Regression checks for the local Streamlit workbench."""

from pathlib import Path


def test_requirements_widget_uses_session_state_without_a_second_default() -> None:
    app_source = Path("apps/web/app.py").read_text(encoding="utf-8")

    assert 'key="requirements_input"' in app_source
    assert '"requirements_input": ""' in app_source
    assert 'value=st.session_state["source_text"]' not in app_source


def test_repeated_criterion_controls_name_their_target() -> None:
    app_source = Path("apps/web/app.py").read_text(encoding="utf-8")

    assert 'f"Priority for {criterion.criterion_id}"' in app_source
    assert 'f"Required evidence for {criterion.criterion_id}"' in app_source
    assert 'f"Remove {criterion.criterion_id}"' in app_source
    assert 'f"Move {criterion.criterion_id} up"' in app_source
    assert 'st.button("Remove",' not in app_source
    assert 'st.button("Move up",' not in app_source
