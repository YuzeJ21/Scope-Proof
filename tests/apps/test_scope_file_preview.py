"""Read-only loaded diff inspection and target-bound scope decision drafts."""

from streamlit.testing.v1 import AppTest


def _render(mode="available"):
    import streamlit as st

    from apps.web.scope_file_preview import (
        prepare_scope_draft_context,
        render_scope_file_preview,
        scope_file_changed,
    )
    from tests.scope_preview_fixture import scope_preview_context

    if "fixture" not in st.session_state:
        if mode == "escaped":
            from scopeproof_core.schemas.models import ChangedLine, LineChangeType

            st.session_state.fixture = scope_preview_context(lines=[
                ChangedLine(change_type=LineChangeType.REMOVED, line_number=None,
                            content="CONSTRUCTED\r\u2028record"),
                ChangedLine(change_type=LineChangeType.ADDED, line_number=2, content="x" * 4097),
            ])
        elif mode == "paged":
            from scopeproof_core.schemas.models import ChangedLine, LineChangeType

            st.session_state.fixture = scope_preview_context(lines=[
                ChangedLine(change_type=LineChangeType.ADDED, line_number=index + 1,
                            content=f"CONSTRUCTED record {index}") for index in range(101)
            ])
        elif mode == "renamed-missing":
            st.session_state.fixture = scope_preview_context(
                status="renamed", previous_path="old/notes.md",
            )
        else:
            st.session_state.fixture = scope_preview_context()
    state, snapshot = st.session_state.fixture
    prepare_scope_draft_context(state, snapshot)
    st.selectbox("Uncited changed file", ["notes.md", "src/export.py"], index=None,
                 key="scope_file_path", on_change=scope_file_changed)
    render_scope_file_preview(state, None if mode.endswith("missing") else snapshot,
                             st.session_state.scope_file_path, source_allowed=mode != "blocked")
    st.selectbox("File scope decision", ["outside_confirmed_criteria", "within_confirmed_criteria"],
                 index=None, key="scope_disposition")
    st.text_area("File scope explanation (required)", key="scope_note")


def _values(elements):
    return "\n".join(element.value for element in elements)


def test_selected_file_renders_inert_base_head_records_before_decision_without_mutation():
    app = AppTest.from_function(_render).run()
    state, snapshot = app.session_state.fixture
    before = state.model_dump_json(), snapshot.model_dump_json()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    assert not app.exception
    assert "Loaded changed-file diff" in _values(app.caption)
    assert "- old diff line 20 | CONSTRUCTED old note" in _values(app.code)
    assert "+ head line 21 | CONSTRUCTED new note <img src=x> **Ready**" in _values(app.code)
    assert "  head line 50 | CONSTRUCTED retained context" in _values(app.code)
    assert "<img" not in _values(app.markdown)
    assert "not a full file, runtime verification or a scope decision" in _values(app.caption)
    assert (state.model_dump_json(), snapshot.model_dump_json()) == before
    assert not app.button


def test_switching_file_clears_disposition_criterion_note_and_preview_page():
    app = AppTest.from_function(_render, args=("paged",)).run()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    app.selectbox(key="scope_disposition").select("outside_confirmed_criteria").run()
    app.text_area(key="scope_note").input("CONSTRUCTED prior-file note").run()
    app.session_state.scope_criterion_id = "AC-01"
    app.selectbox(key="scope_preview_page").select(1).run()
    app.selectbox(key="scope_file_path").select("src/export.py").run()
    assert not app.exception
    assert app.selectbox(key="scope_disposition").value is None
    assert app.text_area(key="scope_note").value == ""
    assert app.session_state.scope_criterion_id is None
    assert app.session_state.scope_preview_page == 0
    assert "CONSTRUCTED old note" not in _values(app.code)


def test_changed_source_context_clears_whole_target_draft():
    app = AppTest.from_function(_render).run()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    app.text_area(key="scope_note").input("CONSTRUCTED prior source").run()
    _, snapshot = app.session_state.fixture
    snapshot.files[-1].lines[1].content = "CONSTRUCTED new observed text"
    app.run()
    assert not app.exception
    assert app.selectbox(key="scope_file_path").value is None
    assert app.text_area(key="scope_note").value == ""


def test_missing_or_conflicted_source_never_invents_content():
    for mode in ("missing", "blocked"):
        app = AppTest.from_function(_render, args=(mode,)).run()
        app.selectbox(key="scope_file_path").select("notes.md").run()
        assert not app.exception
        assert "unavailable" in _values(app.info)
        assert "CONSTRUCTED old note" not in _values(app.code)


def test_unknown_coordinates_control_escapes_and_oversized_omission_are_explicit():
    app = AppTest.from_function(_render, args=("escaped",)).run()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    assert not app.exception
    assert "- old diff line unknown | CONSTRUCTED\\u000d\\u2028record" in _values(app.code)
    assert "+ head line 2 | [Content omitted: exceeds 4,096 UTF-8 bytes]" in _values(app.code)
    assert "x" * 4097 not in _values(app.code)


def test_changed_source_identity_is_unavailable_after_explicit_reselection():
    app = AppTest.from_function(_render).run()
    _, snapshot = app.session_state.fixture
    snapshot.head_sha = "different-observed-head"
    app.run()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    assert not app.exception
    assert "unavailable for this active analysis" in _values(app.info)
    assert "CONSTRUCTED old note" not in _values(app.code)


def test_truncated_loaded_content_remains_hidden_with_explicit_reason():
    app = AppTest.from_function(_render).run()
    _, snapshot = app.session_state.fixture
    snapshot.files[-1].truncated = True
    app.run()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    assert not app.exception
    assert "truncated; no content is shown" in _values(app.info)
    assert "CONSTRUCTED old note" not in _values(app.code)


def test_removed_lines_do_not_claim_coordinates_at_the_recorded_pr_base_commit():
    app = AppTest.from_function(_render).run()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    assert not app.exception
    assert "- old diff line 20 | CONSTRUCTED old note" in _values(app.code)
    assert "old-side commit was not retained" in _values(app.caption)
    assert "Base (removed-line coordinates)" not in _values(app.caption)


def test_saved_rename_metadata_remains_visible_when_loaded_source_is_missing():
    app = AppTest.from_function(_render, args=("renamed-missing",)).run()
    app.selectbox(key="scope_file_path").select("notes.md").run()
    assert not app.exception
    assert "Recorded change status: renamed" in _values(app.text)
    assert "old/notes.md" in _values(app.code)
    assert "unavailable" in _values(app.info)
    assert "CONSTRUCTED old note" not in _values(app.code)


def test_unicode_display_controls_are_escaped_without_normalizing_unicode_source():
    from apps.web.scope_file_preview import _visible_content

    assert _visible_content("é漢字\t\x80\u202e\u2066\U000e0001") == (
        "é漢字\t\\u0080\\u202e\\u2066\\U000e0001"
    )
