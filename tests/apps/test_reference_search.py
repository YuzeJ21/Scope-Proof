"""Find static source text before explicitly choosing a physical line."""

from streamlit.testing.v1 import AppTest

from tests.reviews.test_reference_search import search_fixture


def panel(state_json, snapshot_json):
    import streamlit as st

    from apps.web.selected_references import (
        _render_source_selection,
        clear_selected_reference_draft,
    )
    from scopeproof_core.schemas.models import PullRequestSnapshot, ReviewState

    state = ReviewState.model_validate_json(state_json)
    snapshot = PullRequestSnapshot.model_validate_json(snapshot_json)
    st.button("Clear reference draft", on_click=clear_selected_reference_draft)
    selected = _render_source_selection(
        state, snapshot, state.criteria_revision.criteria[0].criterion_id, None,
    )
    if selected:
        st.text(f"Explicitly chosen physical line {selected.line_number}")


def app_for(state=None, snapshot=None):
    if state is None:
        state, snapshot = search_fixture()
    return AppTest.from_function(panel, args=(state.model_dump_json(), snapshot.model_dump_json()))


def choose_source(app):
    return app.selectbox(key="selected_reference_source").set_value(
        "changed_file:src/search.py",
    ).run()


def query(app, value):
    return app.text_input(key="selected_reference_query").set_value(value).run()


def test_page_preview_shows_source_before_explicit_line_choice():
    app = app_for().run()
    assert not app.exception
    assert app.text_input(key="selected_reference_query").disabled
    app = choose_source(app)
    assert not app.exception
    assert app.selectbox(key="selected_reference_line").value is None
    preview = "\n".join(item.value for item in app.code)
    assert "10:   Match.*[x]  " in preview
    assert "1002: Straße = 'Kept'\t" in preview
    assert "1005: <img src=x onerror=bad> **Match**" in preview
    assert not any("Explicitly chosen" in item.value for item in app.text)


def test_literal_search_and_no_match_never_select_first_line():
    app = query(choose_source(app_for().run()), ".*[x]")
    assert not app.exception
    assert app.selectbox(key="selected_reference_line").options == ["10"]
    assert app.selectbox(key="selected_reference_line").value is None
    assert any("1 matching" in item.value for item in app.caption)
    app.selectbox(key="selected_reference_line").set_value(10).run()
    app = query(app, "CONSTRUCTED-NO-MATCH")
    assert not app.exception
    assert app.selectbox(key="selected_reference_line").value is None
    assert app.selectbox(key="selected_reference_line").disabled
    assert app.selectbox(key="selected_reference_page").disabled
    assert any("No eligible source lines match" in item.value for item in app.info)
    assert not any("10: " in item.value for item in app.code)
    app = query(app, "STRASSE")
    assert app.selectbox(key="selected_reference_line").options == ["1002"]
    assert app.selectbox(key="selected_reference_line").value is None


def test_query_change_resets_later_page_and_clear_draft_resets_query():
    from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType
    from tests.reviews.test_selected_references import source_state

    state, snapshot = source_state([ChangedFile(
        path="src/search.py", status="modified", lines=[ChangedLine(
            change_type=LineChangeType.ADDED, line_number=index,
            content=f"Constructed source line {index}",
        ) for index in range(1, 203)],
    )])
    app = choose_source(app_for(state, snapshot).run())
    app.selectbox(key="selected_reference_page").set_value(2).run()
    app.selectbox(key="selected_reference_line").set_value(202).run()
    app = query(app, "line 202")
    assert not app.exception
    assert app.selectbox(key="selected_reference_page").value == 0
    assert app.selectbox(key="selected_reference_line").value is None
    app.button[0].click().run()
    assert not app.exception
    assert app.text_input(key="selected_reference_query").value == ""
    assert app.selectbox(key="selected_reference_source").value is None


def test_file_change_clears_query_and_previous_line():
    from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType
    from tests.reviews.test_selected_references import source_state

    state, snapshot = source_state([ChangedFile(
        path=path, status="modified", lines=[ChangedLine(
            change_type=LineChangeType.ADDED, line_number=7, content="Constructed file source",
        )],
    ) for path in ("src/search.py", "src/other.py")])
    app = query(choose_source(app_for(state, snapshot).run()), "source")
    app.selectbox(key="selected_reference_line").set_value(7).run()
    app.selectbox(key="selected_reference_source").set_value("changed_file:src/other.py").run()
    assert not app.exception
    assert app.text_input(key="selected_reference_query").value == ""
    assert app.selectbox(key="selected_reference_line").value is None


def test_actual_source_context_change_clears_query_without_recording_reference():
    from tests.apps.test_selected_references import reference_app

    app = reference_app()
    app.selectbox(key="selected_reference_source").set_value(
        "changed_file:src/reference_only.py",
    ).run()
    app = query(app, "return")
    app.selectbox(key="selected_reference_line").set_value(7).run()
    before = app.session_state["review_state"].model_dump_json()
    app.session_state["snapshot"].files[-1].lines[0].content = "Constructed changed source"
    app.run()
    assert not app.exception
    assert app.text_input(key="selected_reference_query").value == ""
    assert app.selectbox(key="selected_reference_source").value is None
    assert app.session_state["review_state"].model_dump_json() == before
