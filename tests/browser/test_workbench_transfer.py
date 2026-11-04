"""CONSTRUCTED installed-workbench handoff and real 64 MiB upload transport checks."""

import json
import os
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.browser.test_packaged_workbench import (
    HISTORICAL_REVIEW_ID,
    _capture_browser_failure,
    _choose_combobox_option,
    _download_with_retry,
    _exercise_historical_inspection,
    _installed_workbench_server,
    _route_loopback_only,
    _run,
    _run_and_wait_for_streamlit_rerun,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel

pytestmark = pytest.mark.browser
RECORD_LIMIT = 64 * 1024 * 1024


def _seed_record(
    runtime: Path, installation: Path, *, storage_directory: Path | None = None,
) -> tuple[Path, bytes]:
    home = runtime / "sender-home"
    home.mkdir(parents=True)
    store = storage_directory if storage_directory is not None else home / ".scopeproof" / "reviews"
    recipe = runtime / "constructed_history.py"
    shutil.copyfile(Path(__file__).parents[1] / "historical_analysis_fixture.py", recipe)
    _run(str(installation / "bin" / "python"), "-I", "-c",
         "from pathlib import Path; import sys, runpy, scopeproof_core; "
         "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix)); "
         "from scopeproof_core.storage.json_store import JsonReviewStore; "
         f"recipe=runpy.run_path({str(recipe)!r}); "
         f"JsonReviewStore(Path({str(store)!r})).save(recipe['criteria_change_browser_state']())",
         cwd=runtime)
    path = store / f"{HISTORICAL_REVIEW_ID}.json"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    return home, path.read_bytes()


def _diagnostics(tmp_path: Path, name: str) -> Path:
    destination = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / name
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def test_installed_ui_download_import_and_reopen_preserves_complete_record(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    runtime = tmp_path / "ui-handoff"
    sender = runtime / "sender reviews"
    recipient = runtime / "recipient reviews"
    home, raw = _seed_record(runtime, installed_wheel, storage_directory=sender)
    target = recipient / f"{HISTORICAL_REVIEW_ID}.json"
    portable = runtime / "downloaded-review.json"
    diagnostics = _diagnostics(tmp_path, "workbench-handoff")
    external: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for name, storage in (("sender", sender), ("recipient", recipient)):
                with _installed_workbench_server(
                    installed_wheel, runtime, home, log_name=f"handoff-{name}.log",
                    storage_directory=storage,
                ) as (url, log):
                    context = browser.new_context(
                        accept_downloads=True, viewport={"width": 1440, "height": 1000},
                    )
                    context.route("**/*", lambda route: _route_loopback_only(route, external))
                    page = context.new_page()
                    try:
                        with _capture_browser_failure(page, diagnostics / name, log):
                            page.goto(url, wait_until="domcontentloaded")
                            page.get_by_text("Resume a saved review", exact=True).click()
                            expect(page.get_by_text(str(storage), exact=True)).to_be_visible()
                            if name == "sender":
                                prepare = page.get_by_role(
                                    "button", name="Prepare saved review download", exact=True,
                                )
                                _choose_combobox_option(
                                    page, page.get_by_role("combobox", name="Saved review ID"),
                                    option_name=HISTORICAL_REVIEW_ID, settled_control=prepare,
                                )
                                _run_and_wait_for_streamlit_rerun(page, prepare.click)
                                download = _download_with_retry(
                                    page, button_name="Download saved review record",
                                )
                                download.save_as(portable)
                                assert portable.read_bytes() == raw
                            else:
                                page.locator('input[type="file"]').set_input_files(portable)
                                inspect = page.get_by_role("button", name="Inspect uploaded review")
                                expect(inspect).to_be_enabled()
                                _run_and_wait_for_streamlit_rerun(page, inspect.click)
                                preview = page.locator(".st-key-transfer_import_preview_panel")
                                expect(preview.get_by_text(
                                    "Unconfirmed", exact=True,
                                )).to_be_visible()
                                expect(preview.get_by_text(HISTORICAL_REVIEW_ID,
                                                         exact=True)).to_be_visible()
                                assert not target.exists()
                                consent = page.get_by_role("checkbox", name=(
                                    "Import this inspected saved record "
                                    "under its original review ID"
                                ))
                                consent_label = page.get_by_text(
                                    "Import this inspected saved record "
                                    "under its original review ID", exact=True,
                                )
                                action = page.get_by_role("button", name="Import inspected review")
                                expect(action).to_be_disabled()
                                _run_and_wait_for_streamlit_rerun(page, consent_label.click)
                                expect(consent).to_be_checked()
                                _run_and_wait_for_streamlit_rerun(page, action.click)
                                expect(page.get_by_text(
                                    "Open work remains unchanged.", exact=False,
                                )).to_be_visible()
                                assert target.read_bytes() == raw
                                expect(page.get_by_role("button", name="Download JSON",
                                                        exact=True)).to_have_count(0)
                                expect(consent).not_to_be_checked()
                                _run_and_wait_for_streamlit_rerun(page, consent_label.click)
                                expect(consent).to_be_checked()
                                _run_and_wait_for_streamlit_rerun(page, action.click)
                                expect(page.get_by_text(
                                    "Nothing was overwritten.", exact=False,
                                )).to_be_visible()
                                assert target.read_bytes() == raw
                                _exercise_historical_inspection(
                                    page, url, json.loads(raw)["state"], diagnostics,
                                )
                                assert target.read_bytes() == raw
                    finally:
                        context.close()
        finally:
            browser.close()
    assert not external
    assert (sender / target.name).read_bytes() == raw
    assert not (home / ".scopeproof" / "reviews").exists()


def test_installed_ui_full_record_limit_reaches_parser_and_overflow_stays_unsaved(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    runtime = tmp_path / "upload-boundary"
    _, raw = _seed_record(runtime, installed_wheel)
    recipient = runtime / "recipient-home"
    recipient.mkdir()
    exact = runtime / "exact-limit.json"
    overflow = runtime / "one-byte-over.json"
    exact.write_bytes(raw.ljust(RECORD_LIMIT, b" "))
    overflow.write_bytes(raw.ljust(RECORD_LIMIT + 1, b" "))
    diagnostics = _diagnostics(tmp_path, "workbench-transfer-limit")
    external: list[str] = []
    with _installed_workbench_server(
        installed_wheel, runtime, recipient, log_name="upload-limit.log",
    ) as (url, log), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.route("**/*", lambda route: _route_loopback_only(route, external))
            page = context.new_page()
            try:
                with _capture_browser_failure(page, diagnostics, log):
                    page.goto(url, wait_until="domcontentloaded")
                    page.get_by_text("Resume a saved review", exact=True).click()
                    page.locator('input[type="file"]').set_input_files(exact)
                    inspect = page.get_by_role("button", name="Inspect uploaded review")
                    expect(inspect).to_be_enabled(timeout=60_000)
                    _run_and_wait_for_streamlit_rerun(page, inspect.click)
                    preview = page.locator(".st-key-transfer_import_preview_panel")
                    preview.get_by_text("Recorded provenance and file details", exact=True).click()
                    expect(preview.get_by_text(str(RECORD_LIMIT), exact=True)).to_be_visible()
                    assert not list(recipient.rglob("*.json"))
                    page.locator('input[type="file"]').set_input_files(overflow)
                    expect(preview).to_have_count(0)
                    expect(inspect).to_be_enabled(timeout=60_000)
                    _run_and_wait_for_streamlit_rerun(page, inspect.click)
                    expect(page.get_by_text(
                        "Uploaded review could not be inspected.", exact=False,
                    )).to_be_visible()
                    expect(preview).to_have_count(0)
                    assert not list(recipient.rglob("*.json"))
            finally:
                context.close()
        finally:
            browser.close()
    assert not external
