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


def test_criterion_text_is_rendered_inertly_outside_markdown_headings() -> None:
    app_source = Path("apps/web/app.py").read_text(encoding="utf-8")

    assert "st.text(criterion.text)" in app_source
    assert "st.text(selected_criterion.text)" in app_source
    assert 'st.markdown(f"### {selected_id} · {selected_criterion.text}")' not in app_source
    assert 'st.markdown(f"### {criterion.criterion_id} · {criterion.text}")' not in app_source
    unsafe_selected_criterion_interpolations = [
        'f"This record will be attached to {selected_id} — {selected_criterion.text}. "',
        'f"This decision will be recorded for {selected_id} — {selected_criterion.text}. "',
    ]
    assert [
        interpolation
        for interpolation in unsafe_selected_criterion_interpolations
        if interpolation in app_source
    ] == []


def test_candidate_evidence_links_use_the_safe_reference_renderer() -> None:
    app_source = Path("apps/web/app.py").read_text(encoding="utf-8")

    assert 'f"[Open immutable GitHub evidence]({item.permalink})"' not in app_source
    assert "render_artifact_reference_markdown(item.permalink)" in app_source
