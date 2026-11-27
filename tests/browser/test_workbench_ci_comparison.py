"""Compare explicit CI inputs and read the installed workbench's exported report."""

import json
import os
from hashlib import sha256
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.browser.test_ci_status import _open_ci_panel
from tests.browser.test_junit_withdrawal import _reopen, _seed_installed_review
from tests.browser.test_packaged_workbench import (
    _capture_browser_failure,
    _download_review_state,
    _download_with_retry,
    _installed_workbench_server,
    _route_loopback_only,
    _run_and_wait_for_streamlit_rerun,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel

pytestmark = pytest.mark.browser


def test_installed_workbench_exports_explicit_ci_comparison_without_saving_review(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    runtime = tmp_path / "runtime"
    home = runtime / "home"
    record, original = _seed_installed_review(installed_wheel, runtime, home)
    saved_bytes = record.read_bytes()
    review = original["review"]
    previous = {
        "schema_version": "criterion-ci-status-v1",
        "repository": review["repository"], "pr_number": review["pr_number"],
        "criteria_sha256": review["criteria_source_provenance"]["normalized_criteria_sha256"],
        "expected_tests": {"AC-01": ["suite/_smoke_", "suite/smoke"], "AC-02": ["row_access"]},
        "runs": [{
            "run_id": "run/_initial_", "head_sha": review["head_sha"],
            "source_url": "https://ci.example.invalid/runs/initial",
            "outcomes": {
                "suite/_smoke_": "failed", "suite/smoke": "passed", "row_access": "skipped",
            },
        }],
    }
    current = {**previous, "runs": [*previous["runs"], {
        "run_id": "targeted", "head_sha": review["head_sha"],
        "source_url": "https://ci.example.invalid/runs/targeted",
        "outcomes": {"suite/_smoke_": "skipped", "row_access": "failed"},
    }]}
    prior = runtime / "previous.json"
    latest = runtime / "current.json"
    wrong = runtime / "wrong.json"
    prior.write_text(json.dumps(previous), encoding="utf-8")
    latest.write_text(json.dumps(current), encoding="utf-8")
    wrong.write_text(json.dumps({**previous, "criteria_sha256": "f" * 64}), encoding="utf-8")
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / "workbench-ci-comparison"
    external_requests = []
    report_requests = []

    with _installed_workbench_server(
        installed_wheel, runtime, home, log_name="ci-comparison.log",
    ) as (url, log_path), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.route("**/*", lambda route: _route_loopback_only(route, external_requests))
            page = context.new_page()
            with _capture_browser_failure(page, diagnostics, log_path):
                _reopen(page, url)
                panel = _open_ci_panel(page)
                _run_and_wait_for_streamlit_rerun(
                    page, lambda: panel.locator("input[type=file]").set_input_files(latest),
                )
                download = panel.get_by_role("button", name="Download CI comparison", exact=True)
                expect(download).to_have_count(0)
                _run_and_wait_for_streamlit_rerun(
                    page, lambda: panel.get_by_role(
                        "checkbox", name="Compare with a previous CI manifest", exact=True,
                    ).check(),
                )
                prior_upload = panel.get_by_test_id("stFileUploader").filter(
                    has=page.get_by_text("Previous CI status manifest", exact=True),
                ).locator("input[type=file]")
                expect(download).to_have_count(0)
                _run_and_wait_for_streamlit_rerun(page, lambda: prior_upload.set_input_files(prior))
                expect(download).to_be_enabled()
                table = panel.get_by_role("table").filter(
                    has=page.get_by_role("columnheader", name="Previous result", exact=True),
                )
                expect(table.get_by_role("cell", name="suite/_smoke_", exact=True)).to_have_count(1)
                expect(table.get_by_role("cell", name="suite/smoke", exact=True)).to_have_count(1)
                expect(table.get_by_role("cell", name="run/_initial_", exact=True)).to_have_count(5)
                access = table.get_by_role("row").filter(
                    has=page.get_by_role("cell", name="row_access", exact=True),
                )
                expect(access.get_by_role("cell", name="Explicitly skipped", exact=True))\
                    .to_be_visible()
                expect(access.get_by_role("cell", name="Failed", exact=True)).to_be_visible()
                for width in (1280, 390):
                    page.set_viewport_size({"width": width, "height": 900})
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.set_viewport_size({"width": 1280, "height": 900})
                result = _download_with_retry(page, button_name="Download CI comparison")
                previous_digest = sha256(prior.read_bytes()).hexdigest()
                current_digest = sha256(latest.read_bytes()).hexdigest()
                assert result.suggested_filename == (
                    f'scopeproof-ci-comparison-pr-{review["pr_number"]}-'
                    f'{review["head_sha"][:12]}-{previous_digest[:12]}-{current_digest[:12]}.html'
                )
                destination = runtime / "comparison.html"
                result.save_as(destination)
                recipient = browser.new_context(offline=True)
                report = recipient.new_page()
                report.on("request", lambda request: report_requests.append(request.url)
                          if request.url.startswith(("http:", "https:")) else None)
                report.goto(destination.as_uri(), wait_until="load")
                expect(report.get_by_role("heading", name="ScopeProof CI Context Comparison"))\
                    .to_be_visible()
                for digest in (previous_digest, current_digest):
                    expect(report.get_by_text(digest, exact=True)).to_be_visible()
                row = report.locator('tr[data-test-id="row_access"]')
                expect(row.get_by_role("cell", name="Explicitly skipped", exact=False))\
                    .to_have_count(1)
                expect(row.get_by_role("cell", name="Failed", exact=False)).to_have_count(1)
                for width in (1280, 390):
                    report.set_viewport_size({"width": width, "height": 844})
                    assert report.evaluate("document.documentElement.scrollWidth === innerWidth")
                recipient.close()
                assert _download_review_state(page) == original
                _run_and_wait_for_streamlit_rerun(page, lambda: prior_upload.set_input_files(wrong))
                expect(download).to_have_count(0)
                expect(panel.get_by_text(
                    "The comparison inputs must be valid CI manifests for this review, "
                    "its confirmed criteria and exact reviewed commit.", exact=True,
                )).to_be_visible()
                assert _download_review_state(page) == original
        finally:
            browser.close()
    assert record.read_bytes() == saved_bytes
    assert prior.read_text() == json.dumps(previous)
    assert latest.read_text() == json.dumps(current)
    assert external_requests == report_requests == []
