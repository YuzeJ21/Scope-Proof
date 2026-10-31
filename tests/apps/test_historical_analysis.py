"""Historical UI remains read-only and separate from active review authority."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.schemas.models import GateVerdict, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.historical_analysis_fixture import historical_analysis_state
from tests.reviews.test_historical_analysis import history_only_state


def _panel(directory, review_id):
    from pathlib import Path

    import streamlit as st

    from apps.web.historical_analysis import (
        clear_historical_analysis_selection,
        render_historical_analysis_selector,
    )
    from scopeproof_core.storage.json_store import JsonReviewStore

    store = JsonReviewStore(Path(directory))
    if "opened" not in st.session_state:
        st.session_state["opened"] = store.load(review_id)
    st.text_input("Current unconfirmed draft", key="current_draft")
    st.button("Reopen same record", on_click=clear_historical_analysis_selection)
    render_historical_analysis_selector(
        st.session_state["opened"], store=store,
        current_is_saved=st.session_state.get("current_is_saved", True),
    )


def seeded(tmp_path, state=None):
    store = JsonReviewStore(Path(tmp_path).resolve() / "records")
    state = state or historical_analysis_state()
    path = store.save(state)
    return store, state, path


def inspect(app, index=0):
    app.selectbox(key="historical_analysis_index").set_value(index).run()
    return app.button(key="inspect_historical_analysis").click().run()


def values(elements):
    return "\n".join(item.value for item in elements)


def test_history_only_has_no_default_or_current_authority_and_inspects_read_only(tmp_path):
    store, state, path = seeded(tmp_path)
    before = state.model_dump_json(), path.read_bytes()
    app = AppTest.from_function(_panel, args=(str(store.directory), state.review.review_id)).run()
    assert not app.exception
    assert app.selectbox(key="historical_analysis_index").value is None
    assert app.button(key="inspect_historical_analysis").disabled
    assert not app.get("download_button")
    app = inspect(app)
    assert not app.exception
    markdown = values(app.markdown)
    assert "Historical recorded analysis" in markdown
    assert "Historical review status (installed policy)" in markdown
    assert "Criteria revision: 1" in markdown
    assert "CONSTRUCTED export CSV" in markdown
    assert "CONSTRUCTED historical automatic decision actor" in markdown
    assert "not current-head verification" in values(app.warning)
    assert len(app.get("download_button")) == 2
    assert app.session_state["opened"].bundle is None
    assert not app.session_state["opened"].criteria_revision.confirmed
    assert before == (app.session_state["opened"].model_dump_json(), path.read_bytes())


def test_current_unconfirmed_draft_is_not_historical_output_or_an_export_blocker(tmp_path):
    store, state, _ = seeded(tmp_path)
    app = AppTest.from_function(_panel, args=(str(store.directory), state.review.review_id)).run()
    app.text_input(key="current_draft").set_value("DRAFT-MUST-NOT-BECOME-HISTORY").run()
    app = inspect(app)
    assert not app.exception
    assert "DRAFT-MUST-NOT-BECOME-HISTORY" not in values(app.markdown)
    assert len(app.get("download_button")) == 2
    assert app.session_state["opened"].criteria_revision.number == 3


def test_same_record_reopen_clears_applied_choice_and_old_download_lease(tmp_path):
    store, state, _ = seeded(tmp_path)
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run())
    lease = app.session_state["historical_analysis_export_lease"]
    generation = lease.generation
    app.button[0].click().run()
    assert not app.exception
    assert app.selectbox(key="historical_analysis_index").value is None
    assert not app.get("download_button")
    assert lease.generation > generation and lease.selection is None


def test_saved_runtime_change_blocks_applied_view_and_requires_reselection(tmp_path):
    store, state, path = seeded(tmp_path)
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run())
    changed = store.load(state.review.review_id)
    changed.analysis_history[0].runtime_evidence[0].limitations.append(
        "Constructed later limitation"
    )
    store.save(changed)
    after = path.read_bytes()
    app.run()
    assert not app.exception
    assert not app.get("download_button")
    assert "reopen" in values(app.warning).lower()
    assert path.read_bytes() == after


def test_unsaved_model_and_missing_history_disable_inspection(tmp_path):
    store, state, _ = seeded(tmp_path)
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run())
    app.session_state["current_is_saved"] = False
    app.run()
    assert not app.exception and not app.get("download_button")
    assert app.button(key="inspect_historical_analysis").disabled
    fresh = history_only_state()
    fresh.analysis_history = []
    store2, state2, _ = seeded(tmp_path / "empty", fresh)
    empty = AppTest.from_function(
        _panel, args=(str(store2.directory), state2.review.review_id),
    ).run()
    assert not empty.exception
    assert empty.button(key="inspect_historical_analysis").disabled


def test_legacy_missing_provenance_shows_identity_and_blocks_downloads(tmp_path):
    legacy = history_only_state()
    legacy.analysis_history[1].review.criteria_source_provenance = None
    store, state, _ = seeded(tmp_path, legacy)
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run(), index=1)
    assert not app.exception
    assert "Historical recorded analysis" in values(app.markdown)
    assert "provenance" in values(app.warning).lower()
    assert not app.get("download_button")


def test_historical_ready_does_not_create_current_acceptance_or_edit_controls(tmp_path):
    state = historical_analysis_state()
    past = state.analysis_history[0]
    past.review.final_acceptance = True
    past.gate = evaluate_gate(
        past.review, past.criteria, past.findings, past.resolutions, past.evidence,
        past.file_scope_decisions,
    )
    assert past.gate.verdict is GateVerdict.READY
    state.resolution_events.append(ResolutionEvent(
        event_id="constructed-historical-final", final_acceptance=True,
        reviewer="CONSTRUCTED automatic final-acceptance actor",
        comment="Constructed fixture only; not a genuine review.", criteria_revision_number=1,
    ))
    store, state, _ = seeded(tmp_path, state)
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run())
    assert not app.exception
    assert "**Historical review status (installed policy):** Review complete" in (
        values(app.markdown)
    )
    assert "not current-head verification" in values(app.warning)
    assert app.session_state["opened"].bundle is None
    assert not app.session_state["opened"].review.final_acceptance
    assert not any("Accept" in button.label or "Save" in button.label for button in app.button)


def test_historical_preview_does_not_show_literal_html_code_tags(tmp_path):
    store, state, _ = seeded(tmp_path)
    app = inspect(AppTest.from_function(
        _panel, args=(str(store.directory), state.review.review_id),
    ).run())
    assert not app.exception
    assert "<code>" not in values(app.markdown)


def test_preview_code_is_readable_without_activating_backticks_or_html():
    from apps.web.historical_analysis import _readable_markdown

    assert _readable_markdown(
        '<code>note `](javascript:bad) &lt;img src=x&gt;</code>'
    ) == '`` note `](javascript:bad) <img src=x> ``'
    assert _readable_markdown('<code>a|b</code>') == '` a|b `'
    assert _readable_markdown('| Field | <code>a|b</code> |') == '| Field | ` a\\|b ` |'
