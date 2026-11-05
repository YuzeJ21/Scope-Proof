"""Installed workbench verification using a constructed acceptance history."""

import json
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.browser.test_packaged_workbench import (
    _capture_browser_failure,
    _choose_combobox_option,
    _download_with_retry,
    _installed_workbench_server,
    _route_loopback_only,
    _run,
    _run_and_wait_for_streamlit_rerun,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel
from tests.saved_comparison_fixture import CURRENT_REVIEW_ID

pytestmark = pytest.mark.browser


def test_installed_workbench_saves_rationale_on_explicit_acceptance_events(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    store = home / ".scopeproof" / "reviews"
    recipe = tmp_path / "constructed.py"
    shutil.copyfile(Path(__file__).parents[1] / "saved_comparison_fixture.py", recipe)
    _run(
        str(installed_wheel / "bin" / "python"), "-I", "-c",
        "from pathlib import Path; import runpy, sys; "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        "recipe=runpy.run_path(sys.argv[1]); "
        "current, _=recipe['saved_comparison_states'](final_acceptance_context=True); "
        "JsonReviewStore(Path(sys.argv[2])).save(current)",
        str(recipe), str(store), cwd=tmp_path,
    )
    review_id = CURRENT_REVIEW_ID + "-acceptance"
    record = store / f"{review_id}.json"
    external_requests: list[str] = []
    with _installed_workbench_server(
        installed_wheel, tmp_path, home, log_name="acceptance-rationale.log",
    ) as (url, log), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            context.route("**/*", lambda route: _route_loopback_only(route, external_requests))
            page = context.new_page()
            with _capture_browser_failure(page, tmp_path / "diagnostics", log):
                page.goto(url, wait_until="domcontentloaded")
                page.get_by_text("Resume a saved review", exact=True).click()
                reopen = page.get_by_role("button", name="Reopen local review", exact=True)
                _choose_combobox_option(
                    page, page.get_by_role("combobox", name="Saved review ID", exact=True),
                    option_name=review_id, settled_control=reopen,
                )
                _run_and_wait_for_streamlit_rerun(page, reopen.click)
                note = page.get_by_role("textbox", name="Final acceptance note (optional)")
                export = page.get_by_role("button", name="Download HTML", exact=True)
                for label, accept, rationale in (
                    ("Revoke final acceptance", False, "Constructed <withdrawal> reason"),
                    ("Record final acceptance", True, "Constructed <acceptance> reason"),
                ):
                    before = record.read_bytes()
                    action = page.get_by_role("button", name=label, exact=True)
                    expect(action).to_be_enabled()
                    note.fill(rationale)
                    _run_and_wait_for_streamlit_rerun(page, lambda: note.press("Tab"))
                    expect(export).to_be_disabled()
                    assert record.read_bytes() == before
                    _run_and_wait_for_streamlit_rerun(page, action.click)
                    expect(note).to_have_value("")
                    saved = json.loads(record.read_bytes())["state"]
                    event = saved["resolution_events"][-1]
                    assert event["final_acceptance"] is accept
                    assert event["comment"] == rationale
                    assert saved["resolution_events"][:-1] == json.loads(before)["state"][
                        "resolution_events"
                    ]
                downloaded = _download_with_retry(page, button_name="Download HTML")
                html = downloaded.path().read_text(encoding="utf-8")
                assert "Constructed &lt;withdrawal&gt; reason" in html
                assert "Constructed &lt;acceptance&gt; reason" in html
            context.close()
        finally:
            browser.close()
    assert not external_requests
