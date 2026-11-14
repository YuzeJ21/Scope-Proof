"""Installed workbench smoke for a read-only, externally supplied CI manifest."""

import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from tests.browser.test_junit_withdrawal import _reopen, _seed_installed_review
from tests.browser.test_packaged_workbench import (
    VIEWPORTS,
    _capture_browser_failure,
    _download_review_state,
    _installed_workbench_server,
    _route_loopback_only,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel

pytestmark = pytest.mark.browser


def _ci_panel(page: Page):
    panel = page.get_by_test_id("stExpander").filter(
        has=page.get_by_text("CI status by criterion", exact=True),
    )
    if not panel.get_by_text("CI status manifest", exact=True).is_visible():
        panel.get_by_text("CI status by criterion", exact=True).click()
    return panel


def test_installed_ci_manifest_changes_display_without_saving_review(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    runtime = tmp_path / "runtime"
    home = runtime / "home"
    record, original = _seed_installed_review(installed_wheel, runtime, home)
    original_bytes = record.read_bytes()
    review = original["review"]
    run_url = "https://ci.example.invalid/runs/constructed-browser"
    manifest = {
        "schema_version": "criterion-ci-status-v1",
        "repository": review["repository"],
        "pr_number": review["pr_number"],
        "criteria_sha256": review["criteria_source_provenance"]["normalized_criteria_sha256"],
        "expected_tests": {"AC-01": ["export_rows"], "AC-02": ["row_access"]},
        "runs": [{
            "run_id": "constructed-browser",
            "head_sha": review["head_sha"],
            "source_url": run_url,
            "outcomes": {"export_rows": "failed", "row_access": "skipped"},
        }],
    }
    matching = runtime / "ci-status.json"
    matching.write_text(json.dumps(manifest), encoding="utf-8")
    wrong = runtime / "different-criteria-ci-status.json"
    wrong.write_text(json.dumps({**manifest, "criteria_sha256": "f" * 64}), encoding="utf-8")
    diagnostics = Path(
        os.environ.get("SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"))
    ) / "ci-status"
    external_requests: list[str] = []
    with _installed_workbench_server(
        installed_wheel, runtime, home, log_name="ci-status.log",
    ) as (url, log_path), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport=VIEWPORTS[0])
            context.route("**/*", lambda route: _route_loopback_only(route, external_requests))
            page = context.new_page()
            with _capture_browser_failure(page, diagnostics, log_path):
                _reopen(page, url)
                panel = _ci_panel(page)
                export_row = panel.get_by_role("row").filter(
                    has=page.get_by_role("cell", name="AC-01", exact=True),
                )
                access_row = panel.get_by_role("row").filter(
                    has=page.get_by_role("cell", name="AC-02", exact=True),
                )
                expect(export_row.get_by_role("cell", name="Unknown", exact=True)).to_be_visible()
                uploader = panel.locator("input[type=file]")
                uploader.set_input_files(matching)
                expect(export_row.get_by_role("cell", name="Failed", exact=True)).to_be_visible()
                expect(
                    access_row.get_by_role("cell", name="Explicitly skipped", exact=True),
                ).to_be_visible()
                expect(panel.get_by_role("link", name=run_url)).to_have_attribute("href", run_url)
                assert _download_review_state(page) == original
                assert record.read_bytes() == original_bytes

                uploader.set_input_files(wrong)
                expect(panel.get_by_text(
                    "The CI status manifest does not match this review or its confirmed criteria.",
                    exact=True,
                )).to_be_visible()
                expect(export_row.get_by_role("cell", name="Unknown", exact=True)).to_be_visible()
                expect(access_row.get_by_role("cell", name="Unknown", exact=True)).to_be_visible()
                expect(panel.get_by_role("link", name=run_url)).to_have_count(0)
                assert _download_review_state(page) == original
        finally:
            browser.close()
    assert record.read_bytes() == original_bytes
    assert external_requests == []
