"""CONSTRUCTED workbench record handoff, never qualifying independent use."""

import pytest

from apps.web.deferred_exports import DeferredExportUnavailable
from apps.web.review_transfer import deferred_record_download
from scopeproof_core.reviews.lifecycle import revise_criteria
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import analyzed_demo, new_app, select_saved_review
from tests.historical_analysis_fixture import historical_analysis_state
from tests.saved_comparison_fixture import saved_comparison_states


def portable_record(tmp_path):
    state = historical_analysis_state()
    source = JsonReviewStore(tmp_path / "sender")
    path = source.save(state)
    return state, path.read_bytes()


def upload(app, raw, name="review.json"):
    return app.file_uploader(key="transfer_upload").upload(name, raw, "application/json").run()


def prepare_download(app):
    return next(button for button in app.button if button.label == "Prepare saved review download")


def inspect(app):
    return app.button(key="inspect_transfer_upload").click().run()


def test_upload_requires_inspection_and_explicit_import_before_reopening(tmp_path):
    state, raw = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    app = upload(new_app(), raw)
    assert not app.exception
    assert not store.list_review_ids()
    assert not [b for b in app.button if b.key == "import_transfer_upload"]
    app = inspect(app)
    assert app.button(key="import_transfer_upload").disabled
    assert app.session_state["review_state"] is None
    assert state.review.repository in [x.value for x in app.text]
    app = app.checkbox(key="confirm_transfer_import").check().run()
    assert not store.list_review_ids()
    app = app.button(key="import_transfer_upload").click().run()
    assert not app.exception
    assert app.session_state["review_state"] is None
    assert (store.directory / f"{state.review.review_id}.json").read_bytes() == raw
    app = select_saved_review(app, state.review.review_id)
    app = app.button(key="reopen_review").click().run()
    assert app.session_state["review_state"] == state
    assert not app.session_state["review_state"].review.criteria_confirmed


def test_replacing_upload_revokes_preview_and_consent(tmp_path):
    _, raw = portable_record(tmp_path)
    app = inspect(upload(new_app(), raw))
    app = app.checkbox(key="confirm_transfer_import").check().run()
    app = upload(app, raw + b" ", "replacement.json")
    assert not app.exception
    assert not [b for b in app.button if b.key == "import_transfer_upload"]
    app = inspect(app)
    assert not app.checkbox(key="confirm_transfer_import").value
    assert app.button(key="import_transfer_upload").disabled


def test_collision_preserves_recipient_and_never_opens_upload(tmp_path):
    state, raw = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    before = path.read_bytes()
    app = inspect(upload(new_app(), raw))
    app = app.checkbox(key="confirm_transfer_import").check().run()
    app = app.button(key="import_transfer_upload").click().run()
    assert not app.exception
    assert path.read_bytes() == before
    assert app.session_state["review_state"] is None
    assert any("already exists" in item.value for item in app.error)
    assert not app.checkbox(key="confirm_transfer_import").value


def test_import_preserves_open_requirements_draft(tmp_path):
    state, raw = portable_record(tmp_path)
    app = analyzed_demo(new_app())
    app = app.text_area(key="requirements_input").set_value("CONSTRUCTED unsaved intent").run()
    before = app.session_state["review_state"].model_copy(deep=True)
    app = inspect(upload(app, raw))
    app = app.checkbox(key="confirm_transfer_import").check().run()
    app = app.button(key="import_transfer_upload").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == before
    assert app.text_area(key="requirements_input").value == "CONSTRUCTED unsaved intent"
    app = select_saved_review(app, state.review.review_id)
    assert app.button(key="reopen_review").disabled


@pytest.mark.parametrize("delete_before_render", [False, True])
def test_import_cannot_replace_open_identity_after_external_deletion(
    tmp_path, monkeypatch, delete_before_render,
):
    import apps.web.review_transfer as ui

    app = analyzed_demo(new_app())
    before = app.session_state["review_state"].model_copy(deep=True)
    incoming = before.model_copy(deep=True)
    incoming.review.tool_version = "CONSTRUCTED incoming producer"
    incoming.bundle.review.tool_version = incoming.review.tool_version
    sender = JsonReviewStore(tmp_path / "sender")
    raw = sender.save(incoming).read_bytes()
    app = inspect(upload(app, raw))
    app = app.checkbox(key="confirm_transfer_import").check().run()
    store = JsonReviewStore(default_local_review_directory())
    if delete_before_render:
        (store.directory / f"{before.review.review_id}.json").unlink()
    real_import = ui.import_review_bytes
    attempted = []

    def delete_then_import(destination, data, **kwargs):
        attempted.append(True)
        if not delete_before_render:
            (destination.directory / f"{before.review.review_id}.json").unlink()
        return real_import(destination, data, **kwargs)

    monkeypatch.setattr(ui, "import_review_bytes", delete_then_import)
    app = app.button(key="import_transfer_upload").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == before
    assert not attempted
    assert any("currently open review" in item.value for item in app.error)


@pytest.mark.parametrize("raw", [b"{}", b"\xff", b"{", b'{"record_version":999,"state":{}}'])
def test_invalid_upload_never_creates_review(tmp_path, raw):
    app = inspect(upload(new_app(), raw))
    assert not app.exception
    assert any("could not be inspected" in item.value for item in app.error)
    assert not JsonReviewStore(default_local_review_directory()).list_review_ids()
    assert not [b for b in app.button if b.key == "import_transfer_upload"]


def test_saved_download_requires_explicit_preparation(tmp_path):
    state, _ = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    before = path.read_bytes()
    app = select_saved_review(new_app(), state.review.review_id)
    assert not [b for b in app.get("download_button") if b.key == "download_saved_record"]
    app = prepare_download(app).click().run()
    assert not app.exception
    preview = app.session_state["transfer_download_lease"].preview
    assert preview.receipt.review_id == state.review.review_id
    assert app.get("download_button")[-1].key == "download_saved_record"
    assert store.load(state.review.review_id) == state
    assert path.read_bytes() == before


@pytest.mark.parametrize("direct_id", [False, True])
def test_prepare_matches_displayed_saved_details(direct_id):
    state, _ = saved_comparison_states()
    review_id = state.review.review_id
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    app = new_app().button(key="load_saved_review_details").click().run()
    if direct_id:
        app = app.checkbox(key="saved_discovery_direct_id").check().run()

    def select(app):
        if direct_id:
            return app.text_input(key="reopen_review_id").set_value(f" {review_id} ").run()
        return select_saved_review(app, review_id)

    app = select(app)
    assert any("Retained historical analyses: 1" in item.value for item in app.text)
    revised = revise_criteria(state, state.criteria_revision.criteria, "CONSTRUCTED new intent")
    store.save(revised, expected_fingerprint=store.state_fingerprint(state))
    replacement_bytes = path.read_bytes()

    app = prepare_download(app).click().run()
    assert not app.exception
    assert "transfer_download_lease" not in app.session_state
    assert not any(button.key == "download_saved_record" for button in app.download_button)
    assert any("Refresh saved details" in item.value for item in app.error)
    assert path.read_bytes() == replacement_bytes

    app = select(app.button(key="load_saved_review_details").click().run())
    app = prepare_download(app).click().run()
    preview = app.session_state["transfer_download_lease"].preview
    assert preview.criteria_revision_number == revised.criteria_revision.number
    assert preview.receipt.analysis_history_count == len(revised.analysis_history)
    download = deferred_record_download(store, app.session_state["transfer_download_lease"])
    assert download() == path.read_bytes() == replacement_bytes
    assert app.session_state["review_state"] is None


def test_prepared_download_revalidates_bytes_and_rejects_old_selection(tmp_path):
    from scopeproof_core.demo import build_demo_review
    from scopeproof_core.reviews.lifecycle import new_review_state
    state, _ = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    other = new_review_state(build_demo_review())
    store.save(other)
    app = select_saved_review(new_app(), state.review.review_id)
    app = prepare_download(app).click().run()
    download = deferred_record_download(store, app.session_state["transfer_download_lease"])
    assert download() == path.read_bytes()
    before = path.read_bytes()
    path.write_bytes(before + b" ")
    with pytest.raises(DeferredExportUnavailable):
        download()
    path.write_bytes(before)
    app = select_saved_review(app, other.review.review_id)
    with pytest.raises(DeferredExportUnavailable):
        download()
    assert "transfer_download_lease" not in app.session_state
    assert path.read_bytes() == before


def test_stale_prepare_click_cannot_follow_a_new_saved_selection():
    state, other = saved_comparison_states()
    store = JsonReviewStore(default_local_review_directory())
    store.save(state)
    store.save(other)
    app = select_saved_review(new_app(), state.review.review_id)
    old_prepare = prepare_download(app)
    app.selectbox(key="saved_reopen_review_id").set_value(other.review.review_id)
    app = old_prepare.click().run()
    assert "transfer_download_lease" not in app.session_state
    assert not any(button.key == "download_saved_record" for button in app.download_button)
    app = prepare_download(app).click().run()
    preview = app.session_state["transfer_download_lease"].preview
    assert preview.receipt.review_id == other.review.review_id


def test_id_only_download_survives_unrelated_inventory_change():
    state, other = saved_comparison_states()
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    app = new_app().checkbox(key="saved_discovery_direct_id").check().run()
    app = app.text_input(key="reopen_review_id").set_value(state.review.review_id).run()
    app = prepare_download(app).click().run()
    lease = app.session_state["transfer_download_lease"]
    download = deferred_record_download(store, lease)
    store.save(other)
    app = app.run()
    assert app.session_state["transfer_download_lease"] is lease
    assert download() == path.read_bytes()


def test_refresh_revokes_download_before_loading_saved_details(monkeypatch):
    from apps.web import saved_discovery

    state, _ = saved_comparison_states()
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    app = select_saved_review(new_app(), state.review.review_id)
    app = prepare_download(app).click().run()
    download = deferred_record_download(store, app.session_state["transfer_download_lease"])
    assert download() == path.read_bytes()
    discover = saved_discovery.discover_saved_review_page
    attempted = []

    def refresh(*args, **kwargs):
        with pytest.raises(DeferredExportUnavailable):
            download()
        attempted.append(True)
        return discover(*args, **kwargs)

    monkeypatch.setattr(saved_discovery, "discover_saved_review_page", refresh)
    app = app.button(key="load_saved_review_details").click().run()
    assert not app.exception
    assert attempted == [True]
    assert "transfer_download_lease" not in app.session_state
    app = select_saved_review(app, state.review.review_id)
    app = prepare_download(app).click().run()
    preview = app.session_state["transfer_download_lease"].preview
    assert preview.receipt.review_id == state.review.review_id
    with pytest.raises(DeferredExportUnavailable):
        download()


def test_preparation_cannot_publish_after_selection_is_retired(monkeypatch):
    from apps.web import review_transfer

    state, _ = saved_comparison_states()
    store = JsonReviewStore(default_local_review_directory())
    store.save(state)
    app = select_saved_review(new_app(), state.review.review_id)
    read_transfer = review_transfer.read_review_transfer

    def retire_selection(*args, **kwargs):
        result = read_transfer(*args, **kwargs)
        review_transfer.clear_review_transfer_selection()
        return result

    with monkeypatch.context() as patch:
        patch.setattr(review_transfer, "read_review_transfer", retire_selection)
        app = prepare_download(app).click().run()
    assert not app.exception
    assert "transfer_download_lease" not in app.session_state
    assert not any(button.key == "download_saved_record" for button in app.download_button)


def test_pending_draft_revokes_prepared_saved_download(tmp_path):
    state, _ = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    store.save(state)
    app = select_saved_review(new_app(), state.review.review_id)
    app = app.button(key="reopen_review").click().run()
    app = prepare_download(app).click().run()
    download = deferred_record_download(store, app.session_state["transfer_download_lease"])
    app = app.text_area(key="requirements_input").set_value("CONSTRUCTED unsaved edit").run()
    assert not app.exception
    assert prepare_download(app).disabled
    with pytest.raises(DeferredExportUnavailable):
        download()


def test_changed_upload_at_import_is_rejected_without_writing(tmp_path, monkeypatch):
    import apps.web.review_transfer as ui
    _, raw = portable_record(tmp_path)
    app = inspect(upload(new_app(), raw))
    app = app.checkbox(key="confirm_transfer_import").check().run()
    monkeypatch.setattr(ui, "_uploaded_bytes", lambda uploaded: raw + b" ")
    app = app.button(key="import_transfer_upload").click().run()
    assert not app.exception
    assert not JsonReviewStore(default_local_review_directory()).list_review_ids()
    assert any("Import could not be completed" in x.value for x in app.error)
    assert not app.checkbox(key="confirm_transfer_import").value


def test_oversized_upload_is_rejected_before_reading(tmp_path, monkeypatch):
    import apps.web.review_transfer as ui
    _, raw = portable_record(tmp_path)
    app = upload(new_app(), raw)
    monkeypatch.setattr(ui, "MAX_SAVED_RECORD_BYTES", len(raw) - 1)
    class OversizedUpload:
        size = len(raw)

        def getvalue(self):
            raise AssertionError("oversized upload was read")

    with pytest.raises(ValueError, match="byte limit"):
        ui._uploaded_bytes(OversizedUpload())
    app = inspect(app)
    assert not app.exception
    assert any("could not be inspected" in x.value for x in app.error)
    assert not JsonReviewStore(default_local_review_directory()).list_review_ids()


def test_invalid_saved_download_keeps_fixed_recovery_text(tmp_path):
    state, _ = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    path.write_text("CONSTRUCTED private malformed content", encoding="utf-8")
    app = select_saved_review(new_app(), state.review.review_id)
    app = prepare_download(app).click().run()
    assert not app.exception
    assert any("could not be prepared" in x.value for x in app.error)
    assert "private malformed content" not in " ".join(x.value for x in app.error)
    assert "transfer_download_lease" not in app.session_state
