"""File/page navigation never implicitly chooses or retargets static evidence."""

from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType
from tests.apps.test_streamlit_app import load_demo, new_app


def paged_app():
    app = load_demo(new_app())
    app.session_state["snapshot"].files.extend(
        [
            ChangedFile(
                path="aaa/large.py",
                status="modified",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=i, content=f"value_{i} = {i}"
                    )
                    for i in range(1, 1003)
                ],
            ),
            ChangedFile(
                path="zzz/later.py",
                status="modified",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED, line_number=41, content="later = 41"
                    )
                ],
            ),
        ]
    )
    app = app.run().button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()


def choose_last_page(app):
    app = (
        app.selectbox(key="selected_reference_source").set_value("changed_file:aaa/large.py").run()
    )
    return app.selectbox(key="selected_reference_page").set_value(10).run()


def test_later_file_and_last_page_are_selectable_without_automatic_choice():
    app = paged_app()
    assert not app.exception
    assert "Changed file · zzz/later.py" in app.selectbox(key="selected_reference_source").options
    app = choose_last_page(app)
    assert not app.exception
    assert app.selectbox(key="selected_reference_line").options == ["1001", "1002"]
    assert app.selectbox(key="selected_reference_line").value is None
    assert app.button(key="save_selected_reference").disabled
    assert any("1,001 to 1,002 of 1,002 eligible lines" in c.value for c in app.caption)
    app = app.selectbox(key="selected_reference_line").set_value(1002).run()
    app = (
        app.text_input(key="selected_reference_reviewer")
        .set_value("Constructed paging actor")
        .run()
    )
    app = (
        app.text_area(key="selected_reference_rationale")
        .set_value("Constructed late-line inspection")
        .run()
    )
    before = app.session_state["review_state"].model_dump(mode="json")
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    after = app.session_state["review_state"].model_dump(mode="json")
    refs = after["bundle"].pop("reviewer_selected_references")
    assert refs[0]["line_number"] == 1002
    assert refs[0]["excerpt"] == "value_1002 = 1002"
    before["bundle"].pop("reviewer_selected_references")
    assert after == before
    assert app.selectbox(key="selected_reference_source").value is None


def test_page_source_and_criterion_changes_clear_line_including_queued_save():
    app = choose_last_page(paged_app())
    app = app.selectbox(key="selected_reference_line").set_value(1001).run()
    app = (
        app.text_input(key="selected_reference_reviewer")
        .set_value("Constructed paging actor")
        .run()
    )
    app = app.text_area(key="selected_reference_rationale").set_value("Constructed draft").run()
    app.selectbox(key="selected_reference_page").set_value(0)
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert app.selectbox(key="selected_reference_line").value is None
    assert app.button(key="save_selected_reference").disabled
    assert app.session_state["review_state"].bundle.reviewer_selected_references == []
    app = app.selectbox(key="selected_reference_line").set_value(1).run()
    app = (
        app.selectbox(key="selected_reference_source").set_value("changed_file:zzz/later.py").run()
    )
    assert app.selectbox(key="selected_reference_page").value == 0
    assert app.selectbox(key="selected_reference_line").value is None
    assert app.selectbox(key="selected_reference_line").options == ["41"]
    other = next(
        v
        for v in app.selectbox(key="selected_criterion").options
        if v != app.selectbox(key="selected_criterion").value
    )
    app = app.selectbox(key="selected_criterion").set_value(other).run()
    assert not app.exception
    assert app.selectbox(key="selected_reference_source").value is None
    assert app.selectbox(key="selected_reference_line").value is None
    assert app.text_area(key="selected_reference_rationale").value == ""


def test_default_navigation_does_not_create_a_draft_and_clear_resets_page():
    app = paged_app()
    assert all(not b.disabled for b in app.download_button if b.key == "download_json")
    app = choose_last_page(app)
    assert all(b.disabled for b in app.download_button if b.key == "download_json")
    app = app.button(key="clear_criterion_detail_drafts").click().run()
    assert not app.exception
    assert app.selectbox(key="selected_reference_source").value is None
    assert all(not b.disabled for b in app.download_button if b.key == "download_json")
