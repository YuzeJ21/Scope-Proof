"""Real workbench inputs and deferred CI comparison downloads stay bound together."""

import json
from hashlib import sha256
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from apps.web.deferred_exports import DeferredExportUnavailable
from apps.web.launcher import CI_MANIFEST_DIR_ENV, WORKBENCH_STORAGE_ENV
from scopeproof_core.reviews.ci_handoff import ci_manifest_filename
from scopeproof_core.reviews.ci_status import MAX_CI_STATUS_BYTES
from scopeproof_core.reviews.lifecycle import append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.apps.test_simulated_ci_manifest_workbench import _panel, _reopen
from tests.apps.test_streamlit_app import APP_PATH
from tests.ci_comparison_fixture import ci_comparison_inputs

_MODE = "Compare with a previous CI manifest"
_DOWNLOAD = "Download CI comparison"


@pytest.fixture
def downloads(monkeypatch):
    captured = []
    original = st.download_button

    def capture(label, data, *args, **kwargs):
        if label == _DOWNLOAD and not kwargs.get("disabled"):
            assert callable(data)
            captured.append(data)
        return original(label, data, *args, **kwargs)

    monkeypatch.setattr(st, "download_button", capture)
    return captured


@pytest.fixture
def live_uploads(monkeypatch):
    """Capture the real objects held by callbacks; AppTest.value deserializes a copy."""
    values = {}
    original = st.file_uploader

    def capture(label, *args, **kwargs):
        uploaded = original(label, *args, **kwargs)
        if uploaded is not None:
            values[label] = uploaded
        return uploaded

    monkeypatch.setattr(st, "file_uploader", capture)
    return values


@pytest.fixture
def workbench(tmp_path, monkeypatch):
    state, _, _, previous, current = ci_comparison_inputs()
    storage = tmp_path / "reviews"
    JsonReviewStore(storage).save(state)
    monkeypatch.setenv(WORKBENCH_STORAGE_ENV, str(storage))
    monkeypatch.delenv(CI_MANIFEST_DIR_ENV, raising=False)
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    app = _reopen(app, state.review.review_id)
    return app, storage, state, previous, current


def _upload(app, payload, *, previous=False):
    label = "Previous CI status manifest" if previous else "CI status manifest"
    uploader, = (u for u in _panel(app).get("file_uploader") if u.label == label)
    app = uploader.set_value(("ci.json", payload, "application/json") if payload else None).run()
    assert not app.exception
    return app


def _enable(app):
    mode, = (c for c in _panel(app).get("checkbox") if c.label == _MODE)
    app = mode.check().run()
    assert not app.exception
    return app


def _ready(workbench):
    app, storage, state, previous, current = workbench
    app = _enable(_upload(app, current))
    return _upload(app, previous, previous=True), storage, state, previous, current


def _has_download(app):
    return any(b.label == _DOWNLOAD and not b.disabled for b in app.get("download_button"))


def _expired(callback):
    with pytest.raises(DeferredExportUnavailable):
        callback()


def test_comparison_is_explicit_and_needs_both_inputs(workbench, downloads):
    app, _, _, previous, current = workbench
    assert not any(c.label == _MODE for c in _panel(app).get("checkbox"))
    app = _upload(app, current)
    assert len(_panel(app).get("file_uploader")) == 1
    assert not downloads
    app = _enable(app)
    assert len(_panel(app).get("file_uploader")) == 2
    assert not _has_download(app)
    app = _upload(app, previous, previous=True)
    assert _has_download(app)
    assert "ScopeProof CI Context Comparison" in downloads[-1]()


def test_comparison_displays_effective_changes_with_original_run_citations(workbench, downloads):
    app, storage, state, previous, current = _ready(workbench)
    table, = (t for t in _panel(app).get("table") if "Previous result" in t.value.columns)
    rows = table.value.to_dict(orient="records")
    assert [(r["Expected test"], r["Previous result"], r["Current result"],
             r["Previous runs"], r["Current runs"]) for r in rows] == [
        ("`category_filter`", "Failed", "Failed", "`B`", "`B`"),
        ("`csv_header`", "Passed", "Passed", "`B`", "`B`"),
        ("`row_entitlement`", "Explicitly skipped", "Failed", "`B`", "`B-targeted`"),
    ]
    assert rows[-1]["Previous criteria"] == rows[-1]["Current criteria"] == "AC-02"
    record = storage / f"{state.review.review_id}.json"
    before = record.read_bytes()
    html = downloads[-1]()
    assert sha256(previous).hexdigest() in html
    assert sha256(current).hexdigest() in html
    assert "https://ci.example.invalid/builds/B-targeted" in html
    assert "not verified chronology" in html
    assert record.read_bytes() == before
    assert JsonReviewStore(storage).load(state.review.review_id) == state
    assert app.session_state["review_state"] == state


@pytest.mark.parametrize("bad", ["malformed", "oversize", "criteria", "head", "repository"])
def test_invalid_previous_input_removes_output_and_expires_earlier_download(
    workbench, downloads, bad,
):
    app, _, _, previous, _ = _ready(workbench)
    old = downloads[-1]
    value = json.loads(previous)
    if bad == "malformed":
        payload = b"{"
    elif bad == "oversize":
        payload = b" " * (MAX_CI_STATUS_BYTES + 1)
    else:
        if bad == "head":
            for run in value["runs"]:
                run["head_sha"] = "f" * 40
        else:
            value["criteria_sha256" if bad == "criteria" else "repository"] = (
                "f" * 64 if bad == "criteria" else "other/repository"
            )
        payload = json.dumps(value).encode()
    app = _upload(app, payload, previous=True)
    assert app.error
    assert not _has_download(app)
    _expired(old)


@pytest.mark.parametrize("change", ["previous", "current", "remove", "mode", "rerun"])
def test_input_or_mode_changes_revoke_existing_callbacks(workbench, downloads, change):
    app, _, _, previous, current = _ready(workbench)
    old = downloads[-1]
    if change == "mode":
        mode, = (c for c in _panel(app).get("checkbox") if c.label == _MODE)
        app = mode.uncheck().run()
    elif change == "rerun":
        app = app.run()
    else:
        app = _upload(
            app, None if change == "remove" else
            (previous if change == "previous" else current) + b"\n",
            previous=change != "current",
        )
    _expired(old)
    assert _has_download(app) is (change not in {"remove", "mode"})


@pytest.mark.parametrize("which", ["previous", "current"])
@pytest.mark.parametrize("during", [False, True])
def test_upload_byte_drift_is_checked_before_and_after_rendering(
    workbench, downloads, live_uploads, monkeypatch, which, during,
):
    from apps.web import ci_comparison

    _ready(workbench)
    label = "Previous CI status manifest" if which == "previous" else "CI status manifest"
    uploaded = live_uploads[label]

    def drift():
        uploaded.seek(0, 2)
        uploaded.write(b"\n")

    if during:
        export = ci_comparison.export_ci_comparison_html

        def change_after_render(comparison):
            html = export(comparison)
            drift()
            return html

        monkeypatch.setattr(ci_comparison, "export_ci_comparison_html", change_after_render)
    else:
        drift()
    _expired(downloads[-1])


@pytest.mark.parametrize("during", [False, True])
def test_configured_current_input_is_rechecked_without_changing_saved_review(
    workbench, downloads, tmp_path, monkeypatch, during,
):
    from apps.web import ci_comparison

    app, storage, state, previous, current = workbench
    handoff = (tmp_path / "manifests").resolve()
    handoff.mkdir()
    manifest = json.loads(current)
    path = handoff / ci_manifest_filename(
        state.review.repository, state.review.pr_number, state.review.head_sha,
        manifest["criteria_sha256"],
    )
    path.write_bytes(current)
    monkeypatch.setenv(CI_MANIFEST_DIR_ENV, str(handoff))
    get_option = st.get_option
    monkeypatch.setattr(
        st, "get_option", lambda key: "127.0.0.1" if key == "server.address" else get_option(key),
    )
    app = _upload(_enable(app.run()), previous, previous=True)
    record = storage / f"{state.review.review_id}.json"
    before = record.read_bytes()
    old = downloads[-1]
    assert "ScopeProof CI Context Comparison" in old()
    if during:
        export = ci_comparison.export_ci_comparison_html

        def change_after_render(comparison):
            html = export(comparison)
            path.write_bytes(current + b"\n")
            return html

        monkeypatch.setattr(ci_comparison, "export_ci_comparison_html", change_after_render)
    else:
        path.write_bytes(current + b"\n")
    _expired(old)
    assert record.read_bytes() == before


def test_saved_record_change_blocks_captured_comparison(workbench, downloads):
    _, storage, state, _, _ = _ready(workbench)
    JsonReviewStore(storage).mutate(
        state.review.review_id,
        lambda saved: append_resolution(saved, ResolutionEvent(
            event_id="comparison-record-change", criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED, comment="Constructed later decision",
            reviewer="Constructed reviewer",
        )),
    )
    _expired(downloads[-1])


def test_saved_record_replaced_during_rendering_blocks_the_comparison(
    workbench, downloads, monkeypatch, tmp_path,
):
    from apps.web import ci_comparison

    _, storage, state, _, _ = _ready(workbench)
    changed = append_resolution(state, ResolutionEvent(
        event_id="external-replacement", criterion_id="AC-01",
        decision=HumanDecision.ACCEPTED, comment="Constructed later acceptance",
        reviewer="Constructed reviewer",
    ))
    replacement = JsonReviewStore(tmp_path / "other-writer").save(changed)
    record = storage / f"{state.review.review_id}.json"
    export = ci_comparison.export_ci_comparison_html

    def replace_after_render(comparison):
        html = export(comparison)
        replacement.replace(record)
        return html

    monkeypatch.setattr(ci_comparison, "export_ci_comparison_html", replace_after_render)
    _expired(downloads[-1])
    assert JsonReviewStore(storage).load(state.review.review_id) == changed


def test_markdown_identifier_cells_are_supplied_as_literal_code(workbench, downloads):
    app, _, state, previous, _ = workbench
    value = json.loads(previous)
    value["expected_tests"] = {"AC-01": ["suite/_smoke_", "suite/smoke"]}
    value["runs"] = [{
        "run_id": "run/_one_", "head_sha": state.review.head_sha,
        "source_url": "https://ci.example.invalid/run/one",
        "outcomes": {"suite/_smoke_": "passed", "suite/smoke": "passed"},
    }]
    payload = json.dumps(value).encode()
    app = _upload(_enable(_upload(app, payload)), payload, previous=True)
    table, = (t for t in _panel(app).get("table") if "Previous result" in t.value.columns)
    rows = table.value.to_dict(orient="records")
    assert [row["Expected test"] for row in rows] == ["`suite/_smoke_`", "`suite/smoke`"]
    assert [row["Previous runs"] for row in rows] == ["`run/_one_`", "`run/_one_`"]
    assert [row["Current runs"] for row in rows] == ["`run/_one_`", "`run/_one_`"]


def test_review_draft_pauses_output_and_discard_does_not_revive_old_download(workbench, downloads):
    app, storage, state, _, _ = _ready(workbench)
    record = storage / f"{state.review.review_id}.json"
    before = record.read_bytes()
    old = downloads[-1]
    app = app.text_input(key="criterion_text_AC-01").set_value("Unsubmitted edit").run()
    assert not app.exception
    assert not _has_download(app)
    _expired(old)
    app = app.button(key="discard_criteria_draft").click().run()
    assert _has_download(app)
    _expired(old)
    assert "ScopeProof CI Context Comparison" in downloads[-1]()
    assert record.read_bytes() == before


def test_source_conflict_blocks_existing_download_before_rerun(workbench, downloads):
    app, _, state, _, _ = _ready(workbench)
    app.session_state["source_authority_guard"].block(state)
    _expired(downloads[-1])
    app = app.run()
    assert not app.exception
    assert not _has_download(app)


def test_switching_review_requires_new_explicit_comparison_inputs(workbench, downloads):
    app, storage, _, _, _ = _ready(workbench)
    old = downloads[-1]
    path = (
        Path(__file__).resolve().parents[2]
        / "docs/examples/ci-handoff/source/inputs/A-review.json"
    )
    other = JsonReviewStore.decode_record(path.read_text(), require_recorded_facts=True)
    JsonReviewStore(storage).save(other)
    app = _reopen(app.run(), other.review.review_id)
    assert not _has_download(app)
    assert not any(c.label == _MODE for c in _panel(app).get("checkbox"))
    _expired(old)


def test_invalid_current_input_retires_the_comparison(workbench, downloads):
    app, _, _, _, _ = _ready(workbench)
    old = downloads[-1]
    app = _upload(app, b"{")
    assert not _has_download(app)
    _expired(old)


def test_manual_current_selection_does_not_keep_following_configured_input(
    workbench, downloads, tmp_path, monkeypatch,
):
    app, _, state, previous, current = workbench
    handoff = (tmp_path / "manifests").resolve()
    handoff.mkdir()
    path = handoff / ci_manifest_filename(
        state.review.repository, state.review.pr_number, state.review.head_sha,
        json.loads(current)["criteria_sha256"],
    )
    path.write_bytes(current)
    monkeypatch.setenv(CI_MANIFEST_DIR_ENV, str(handoff))
    get_option = st.get_option
    monkeypatch.setattr(
        st, "get_option", lambda key: "127.0.0.1" if key == "server.address" else get_option(key),
    )
    app = _upload(_enable(app.run()), previous, previous=True)
    configured = downloads[-1]
    app = _upload(app, current + b"\n")
    _expired(configured)
    path.unlink()
    assert sha256(current + b"\n").hexdigest() in downloads[-1]()
