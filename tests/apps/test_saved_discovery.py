"""Constructed saved-record discovery keeps explicit targets and fresh validation."""

import pytest

from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_saved_comparison_ui import apply_other_baseline, rendered
from tests.apps.test_streamlit_app import new_app
from tests.saved_comparison_fixture import (
    CURRENT_HEAD,
    CURRENT_REVIEW_ID,
    PREVIOUS_REVIEW_ID,
    saved_comparison_states,
)


def discovery_app():
    store = JsonReviewStore(default_local_review_directory())
    current, previous = saved_comparison_states()
    store.save(current)
    store.save(previous)
    return new_app(), store


def load_details(app):
    return app.button(key="load_saved_review_details").click().run()


def test_details_are_explicit_and_search_uses_validated_labels_without_writing():
    app, store = discovery_app()
    before = {path.name: path.read_bytes() for path in store.directory.glob("*.json")}
    assert app.selectbox(key="saved_reopen_review_id").options == [
        CURRENT_REVIEW_ID,
        PREVIOUS_REVIEW_ID,
    ]
    app = load_details(app)
    assert not app.exception
    labels = app.selectbox(key="saved_reopen_review_id").options
    assert all("acme/widget" in label and "PR #7" in label for label in labels)
    assert CURRENT_REVIEW_ID in labels[0] and PREVIOUS_REVIEW_ID in labels[1]
    app = app.text_input(key="saved_discovery_query").set_value(CURRENT_HEAD).run()
    assert len(app.selectbox(key="saved_reopen_review_id").options) == 1
    assert app.selectbox(key="saved_reopen_review_id").value is None
    assert {path.name: path.read_bytes() for path in store.directory.glob("*.json")} == before


def test_query_change_clears_reopen_and_delete_confirmation():
    app, _ = discovery_app()
    app = load_details(app)
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.text_input(key="saved_discovery_query").set_value("no-match").run()
    assert not app.exception
    assert app.selectbox(key="saved_reopen_review_id").value is None
    assert not app.session_state["delete_saved_review_confirmed"]
    assert "loaded page" in rendered(app).lower()
    assert app.button(key="reopen_review").disabled


def test_direct_id_is_reachable_after_empty_search_without_delete_path():
    app, _ = discovery_app()
    app = load_details(app)
    app = app.text_input(key="saved_discovery_query").set_value("no-match").run()
    app = app.checkbox(key="saved_discovery_direct_id").check().run()
    app = app.text_input(key="reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    assert not [item for item in app.button if item.key == "delete_saved_review"]
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.session_state["review_state"].review.review_id == CURRENT_REVIEW_ID


@pytest.mark.parametrize("change", ["changed", "deleted"])
def test_preview_receipt_blocks_stale_reopen(change):
    app, store = discovery_app()
    app = load_details(app)
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    if change == "deleted":
        store.delete(CURRENT_REVIEW_ID)
    else:
        state = store.load(CURRENT_REVIEW_ID)
        state.review.tool_version = "0.0.changed"
        state.bundle.review.tool_version = "0.0.changed"
        store.save(state)
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.session_state["review_state"] is None
    if change == "deleted":
        assert app.selectbox(key="saved_reopen_review_id").value is None
    assert any(item.value for item in [*app.error, *app.warning, *app.info])


def test_inventory_change_discards_metadata_and_target():
    app, store = discovery_app()
    app = load_details(app)
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    store.delete(PREVIOUS_REVIEW_ID)
    app = app.run()
    assert not app.exception
    assert app.selectbox(key="saved_reopen_review_id").value is None
    assert app.selectbox(key="saved_reopen_review_id").options == [CURRENT_REVIEW_ID]


def test_foreign_baseline_uses_labels_and_changed_preview_blocks_analysis_choice():
    app, store = discovery_app()
    app = load_details(app)
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.button(key="reopen_review").click().run()
    options = app.selectbox(key="saved_comparison_baseline").options
    assert any("acme/widget" in label and PREVIOUS_REVIEW_ID in label for label in options)
    state = store.load(PREVIOUS_REVIEW_ID)
    state.review.tool_version = "0.0.changed"
    state.bundle.review.tool_version = "0.0.changed"
    store.save(state)
    app = (
        app.selectbox(key="saved_comparison_baseline")
        .set_value(f"saved:{PREVIOUS_REVIEW_ID}")
        .run()
    )
    assert not app.exception
    assert app.selectbox(key="saved_comparison_analysis").disabled
    assert app.button(key="compare_saved_analysis").disabled
    assert "refresh" in rendered(app).lower()


def test_query_change_invalidates_applied_comparison_and_download_lease():
    app, _ = discovery_app()
    app = load_details(app)
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.button(key="reopen_review").click().run()
    app = apply_other_baseline(app)
    assert app.session_state["saved_comparison_selection"] is not None
    lease = app.session_state["saved_comparison_export_lease"]
    app = app.text_input(key="saved_discovery_query").set_value("acme").run()
    assert not app.exception
    assert app.session_state["saved_comparison_selection"] is None
    assert lease.selection is None


def test_unavailable_preview_stays_id_only_and_allows_full_validation():
    app, store = discovery_app()
    path = store.directory / "broken.json"
    path.write_text("{invalid", encoding="utf-8")
    app = load_details(app.run())
    assert not app.exception
    assert any("broken" in label for label in app.selectbox(key="saved_reopen_review_id").options)
    app = app.selectbox(key="saved_reopen_review_id").set_value("broken").run()
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.session_state["review_state"] is None
    assert app.error


def test_changing_reopen_target_clears_delete_confirmation():
    app, _ = discovery_app()
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.selectbox(key="saved_reopen_review_id").set_value(PREVIOUS_REVIEW_ID).run()
    assert not app.exception
    assert not app.checkbox(key="delete_saved_review_confirmed").value
    assert app.button(key="delete_saved_review").disabled


def test_page_change_clears_targets_and_requires_explicit_page_reload():
    app, store = discovery_app()
    for index in range(11):
        (store.directory / f"z-{index:02d}.json").write_text("{}", encoding="utf-8")
    app = load_details(app.run())
    assert len(app.selectbox(key="saved_reopen_review_id").options) == 10
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.number_input(key="saved_discovery_page").set_value(2).run()
    assert not app.exception
    assert app.selectbox(key="saved_reopen_review_id").value is None
    assert not app.session_state["delete_saved_review_confirmed"]
    assert app.text_input(key="saved_discovery_query").disabled
    app = load_details(app)
    assert len(app.selectbox(key="saved_reopen_review_id").options) == 3
    assert all("z-" in option for option in app.selectbox(key="saved_reopen_review_id").options)
    assert "3 of 13 candidate records" in rendered(app)


def test_selected_details_show_complete_local_identity_and_history_presence():
    app, _ = discovery_app()
    app = load_details(app)
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    text = rendered(app)
    assert "Local saved repository: acme/widget" in text
    assert f"Head: {CURRENT_HEAD}" in text
    assert "Criteria revision: 2" in text
    assert "Active analysis recorded: yes" in text
    assert "Retained historical analyses: 1" in text


def test_default_id_mode_keeps_baseline_when_unrelated_record_is_added(monkeypatch):
    app, store = discovery_app()
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.button(key="reopen_review").click().run()
    app = (
        app.selectbox(key="saved_comparison_baseline")
        .set_value(f"saved:{PREVIOUS_REVIEW_ID}")
        .run()
    )
    (store.directory / "unrelated.json").write_text("not parsed", encoding="utf-8")
    original = JsonReviewStore.load

    def reject_unrelated(self, review_id, **kwargs):
        if review_id == "unrelated":
            raise AssertionError("ID-only discovery must not load an unrelated new record")
        return original(self, review_id, **kwargs)

    monkeypatch.setattr(JsonReviewStore, "load", reject_unrelated)
    app = app.run()
    assert not app.exception
    assert app.selectbox(key="saved_comparison_baseline").value == (f"saved:{PREVIOUS_REVIEW_ID}")
    assert app.selectbox(key="saved_comparison_analysis").value == "active"
    app = app.button(key="compare_saved_analysis").click().run()
    assert not app.exception
    assert app.session_state["saved_comparison_selection"] is not None
