"""Stale preview metadata cannot authorize a different reopen or deletion."""

from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.schemas.models import Criterion
from tests.apps.test_saved_comparison_ui import rendered
from tests.apps.test_saved_discovery import discovery_app, load_details
from tests.saved_comparison_fixture import CURRENT_REVIEW_ID
from tests.storage.test_review_discovery import saved


def change_revision(store):
    state = store.load(CURRENT_REVIEW_ID)
    state = revise_criteria(
        state,
        [Criterion(criterion_id="AC-01", text="Changed constructed revision")],
        "Changed constructed revision",
    )
    store.save(state)
    return state


def test_loaded_inventory_refresh_clears_direct_id_before_reopen_can_retarget():
    app, store = discovery_app()
    app = load_details(app)
    app = app.checkbox(key="saved_discovery_direct_id").check().run()
    app = app.text_input(key="reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    change_revision(store)
    saved(store, "unrelated-added-record")
    app = app.run()
    assert not app.exception
    assert app.text_input(key="reopen_review_id").value == ""
    assert app.button(key="reopen_review").disabled
    assert app.session_state["review_state"] is None


def test_changed_preview_cannot_delete_a_new_revision_under_old_consent():
    app, store = discovery_app()
    app = load_details(app)
    app = app.selectbox(key="saved_reopen_review_id").set_value(CURRENT_REVIEW_ID).run()
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    changed = change_revision(store)
    path = store.directory / f"{CURRENT_REVIEW_ID}.json"
    before = path.read_bytes()
    app = app.run().button(key="delete_saved_review").click().run()
    assert not app.exception
    assert path.exists() and path.read_bytes() == before
    assert store.load(CURRENT_REVIEW_ID) == changed
    assert not app.session_state["delete_saved_review_confirmed"]


def test_deep_malformed_neighbor_does_not_crash_loaded_details():
    app, store = discovery_app()
    (store.directory / "z-deep.json").write_text("[" * 2000 + "0" + "]" * 2000)
    app = load_details(app.run())
    assert not app.exception
    assert "details unavailable" in " ".join(app.selectbox(key="saved_reopen_review_id").options)
    assert "Search covers this page only" in rendered(app)
