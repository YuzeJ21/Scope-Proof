"""CONSTRUCTED installed CLI transfer followed by genuine automated browser reopening."""

import json
import os
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tests.browser.test_packaged_workbench import (
    HISTORICAL_REVIEW_ID,
    _capture_browser_failure,
    _exercise_historical_inspection,
    _installed_workbench_server,
    _route_loopback_only,
    _run,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel

pytestmark = pytest.mark.browser


def test_installed_transferred_review_reopens_history_without_current_authority(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    runtime = tmp_path / "transfer-runtime"
    home = runtime / "home"
    home.mkdir(parents=True)
    source = runtime / "sender"
    recipient = home / ".scopeproof" / "reviews"
    recipe = runtime / "constructed_history.py"
    shutil.copyfile(Path(__file__).parents[1] / "historical_analysis_fixture.py", recipe)
    python = str(installed_wheel / "bin" / "python")
    _run(python, "-I", "-c",
         "from pathlib import Path; import runpy, sys, scopeproof_core; "
         "assert Path(scopeproof_core.__file__).resolve().is_relative_to(Path(sys.prefix)); "
         "from scopeproof_core.storage.json_store import JsonReviewStore; "
         f"recipe=runpy.run_path({str(recipe)!r}); "
         f"JsonReviewStore(Path({str(source)!r})).save(recipe['criteria_change_browser_state']())",
         cwd=runtime)
    original = source / f"{HISTORICAL_REVIEW_ID}.json"
    before = original.read_bytes()
    portable = runtime / "portable-review.json"
    _run(python, "-I", "-m", "scopeproof_core.cli", "export-review", HISTORICAL_REVIEW_ID,
         "--storage-dir", str(source), "--output", str(portable), cwd=runtime)
    _run(python, "-I", "-m", "scopeproof_core.cli", "import-review", "--input", str(portable),
         "--storage-dir", str(recipient), cwd=runtime)
    assert original.read_bytes() == portable.read_bytes() == (
        recipient / original.name
    ).read_bytes()
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / "review-transfer"
    diagnostics.mkdir(parents=True, exist_ok=True)
    external_requests: list[str] = []
    with _installed_workbench_server(
        installed_wheel, runtime, home, log_name="transfer-workbench.log",
    ) as (base_url, log_path), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                accept_downloads=True, viewport={"width": 1440, "height": 1000},
            )
            context.route("**/*", lambda route: _route_loopback_only(route, external_requests))
            page = context.new_page()
            try:
                with _capture_browser_failure(page, diagnostics, log_path):
                    _exercise_historical_inspection(
                        page, base_url, json.loads(before)["state"], diagnostics,
                    )
                    assert not external_requests
            finally:
                context.close()
        finally:
            browser.close()
    assert original.read_bytes() == portable.read_bytes() == (
        recipient / original.name
    ).read_bytes()
