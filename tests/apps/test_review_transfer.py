"""CONSTRUCTED workbench record handoff, never qualifying independent use."""

import pytest

from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import analyzed_demo, new_app, select_saved_review
from tests.historical_analysis_fixture import historical_analysis_state


def portable_record(tmp_path):
    state = historical_analysis_state()
    source = JsonReviewStore(tmp_path / "sender")
    path = source.save(state)
    return state, path.read_bytes()


def upload(app, raw, name="review.json"):
    return app.file_uploader(key="transfer_upload").upload(name, raw, "application/json").run()


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
    app = app.button(key="prepare_transfer_download").click().run()
    assert not app.exception
    preview = app.session_state["transfer_download_preview"]
    assert preview.receipt.review_id == state.review.review_id
    assert app.get("download_button")[-1].key == "download_saved_record"
    assert store.load(state.review.review_id) == state
    assert path.read_bytes() == before


def test_prepared_download_revalidates_bytes_and_rejects_old_selection(tmp_path):
    from apps.web.deferred_exports import DeferredExportUnavailable
    from apps.web.review_transfer import deferred_record_download
    from scopeproof_core.demo import build_demo_review
    from scopeproof_core.reviews.lifecycle import new_review_state
    state, _ = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    path = store.save(state)
    other = new_review_state(build_demo_review())
    store.save(other)
    app = select_saved_review(new_app(), state.review.review_id)
    app = app.button(key="prepare_transfer_download").click().run()
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
    assert app.session_state["transfer_download_preview"] is None
    assert path.read_bytes() == before


def test_pending_draft_revokes_prepared_saved_download(tmp_path):
    from apps.web.deferred_exports import DeferredExportUnavailable
    from apps.web.review_transfer import deferred_record_download
    state, _ = portable_record(tmp_path)
    store = JsonReviewStore(default_local_review_directory())
    store.save(state)
    app = select_saved_review(new_app(), state.review.review_id)
    app = app.button(key="reopen_review").click().run()
    app = app.button(key="prepare_transfer_download").click().run()
    download = deferred_record_download(store, app.session_state["transfer_download_lease"])
    app = app.text_area(key="requirements_input").set_value("CONSTRUCTED unsaved edit").run()
    assert not app.exception
    assert app.button(key="prepare_transfer_download").disabled
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
    app = app.button(key="prepare_transfer_download").click().run()
    assert not app.exception
    assert any("could not be prepared" in x.value for x in app.error)
    assert "private malformed content" not in " ".join(x.value for x in app.error)
    assert app.session_state["transfer_download_preview"] is None
