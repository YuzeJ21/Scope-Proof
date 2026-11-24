"""Installed workbench smoke for a read-only, externally supplied CI manifest."""

import json
import os
import shutil
from hashlib import sha256
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, Locator, Page, expect, sync_playwright

from tests.browser.test_junit_withdrawal import _reopen, _seed_installed_review
from tests.browser.test_packaged_workbench import (
    REPOSITORY_ROOT,
    VIEWPORTS,
    _capture_browser_failure,
    _choose_combobox_option,
    _download_review_state,
    _download_with_retry,
    _installed_workbench_server,
    _route_loopback_only,
    _run,
    _run_and_wait_for_streamlit_rerun,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel

pytestmark = pytest.mark.browser


def _open_ci_panel(page: Page) -> Locator:
    title = page.get_by_text("CI status by criterion", exact=True)
    panel = page.get_by_test_id("stExpander").filter(has=title)
    details = panel.locator("details")
    if details.get_attribute("open") is None:
        details.locator("summary").press("Enter")
    expect(panel.locator("details[open]")).to_have_count(1)
    return panel


def _criterion_status_table(page: Page, panel: Locator) -> Locator:
    return panel.get_by_role("table").filter(
        has=page.get_by_role("columnheader", name="Criterion", exact=True),
    )


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
                panel = _open_ci_panel(page)
                criterion_table = _criterion_status_table(page, panel)
                export_row = criterion_table.get_by_role("row").filter(
                    has=page.get_by_role("cell", name="AC-01", exact=True),
                )
                access_row = criterion_table.get_by_role("row").filter(
                    has=page.get_by_role("cell", name="AC-02", exact=True),
                )
                expect(
                    export_row.get_by_role("cell", name="Unknown", exact=True),
                ).to_be_visible(timeout=20_000)
                uploader = panel.locator("input[type=file]")
                _run_and_wait_for_streamlit_rerun(
                    page, lambda: uploader.set_input_files(matching),
                )
                expect(export_row.get_by_role("cell", name="Failed", exact=True)).to_be_visible()
                expect(
                    access_row.get_by_role("cell", name="Explicitly skipped", exact=True),
                ).to_be_visible()
                follow_up = panel.get_by_role("table").filter(
                    has=page.get_by_role("columnheader", name="Mapped criteria", exact=True),
                )
                expect(follow_up.get_by_role("cell", name="row_access")).to_be_visible()
                expect(follow_up.get_by_role("cell", name="export_rows")).to_be_visible()
                expect(panel.get_by_role("link", name=run_url)).to_have_attribute("href", run_url)
                expect(panel.get_by_role("button", name="Download CI snapshot")).to_be_enabled()
                assert _download_review_state(page) == original
                assert record.read_bytes() == original_bytes

                _run_and_wait_for_streamlit_rerun(page, lambda: uploader.set_input_files(wrong))
                expect(panel.get_by_text(
                    "The CI status manifest does not match this review or its confirmed criteria.",
                    exact=True,
                )).to_be_visible()
                expect(export_row.get_by_role("cell", name="Unknown", exact=True)).to_be_visible()
                expect(access_row.get_by_role("cell", name="Unknown", exact=True)).to_be_visible()
                expect(panel.get_by_role("link", name=run_url)).to_have_count(0)
                expect(panel.get_by_role("button", name="Download CI snapshot")).to_have_count(0)
                assert _download_review_state(page) == original
        finally:
            browser.close()
    assert record.read_bytes() == original_bytes
    assert external_requests == []


def _open_build(page: Page, record: Path, head: str) -> Locator:
    saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
    if not saved_review.is_visible():
        page.get_by_text("Resume a saved review", exact=True).click()
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(page, saved_review, option_name=record.stem, settled_control=reopen)
    reopen.click()
    panel = _open_ci_panel(page)
    expect(panel.get_by_text(f"Reviewed commit · {head}", exact=True)).to_be_visible()
    return panel


def _assert_narrow_report_tables(report: Page) -> None:
    # Stress only the rendered layout with the longest legal test ID.
    long_test_id = "x" * 160
    report.evaluate("""(testId) => {
        document.querySelectorAll('.table-scroll td code').forEach(id => id.textContent = testId);
    }""", long_test_id)
    for width in (390, 673):
        report.set_viewport_size({"width": width, "height": 844})
        assert report.evaluate("document.documentElement.scrollWidth === window.innerWidth")
        for name in ("CI follow-up table", "CI tests for AC-01"):
            scroller = report.get_by_role("region", name=name, exact=True)
            expect(scroller).to_have_attribute("tabindex", "0")
            header = scroller.get_by_role("columnheader", name="CI status", exact=True)
            assert header.evaluate("cell => getComputedStyle(cell).overflowWrap") == "normal"
            identifier = scroller.get_by_text(long_test_id, exact=True).first
            assert identifier.evaluate("code => getComputedStyle(code).overflowWrap") == "anywhere"
            status = scroller.get_by_role("cell", name="Failed", exact=True).first
            assert status.evaluate("""cell => {
                const text = document.createRange();
                text.selectNodeContents(cell);
                return text.getClientRects().length;
            }""") == 1
            if width == 390:
                assert scroller.evaluate("node => node.scrollWidth > node.clientWidth")
                scroller.focus()
                scroller.press("ArrowRight")
                report.wait_for_function(
                    "node => node.scrollLeft > 0", arg=scroller.element_handle(),
                )


def _assert_offline_snapshot(
    page: Page, recipient: BrowserContext, destination: Path, *, state: dict, manifest: bytes,
    statuses: tuple[str, str, str], access_run: str,
) -> None:
    download = _download_with_retry(page, button_name="Download CI snapshot")
    review = state["review"]
    head = review["head_sha"]
    manifest_sha = sha256(manifest).hexdigest()
    assert download.suggested_filename == (
        f'scopeproof-ci-pr-{review["pr_number"]}-{head[:12]}-{manifest_sha[:12]}.html'
    )
    download.save_as(destination)
    report = recipient.new_page()
    requests: list[str] = []
    report.on("request", lambda request: requests.append(request.url)
              if request.url.startswith(("http://", "https://")) else None)
    try:
        report.goto(destination.as_uri(), wait_until="load")
        expect(report.get_by_role("heading", name="ScopeProof CI Status Snapshot")).to_be_visible()
        expect(report.get_by_text("Externally supplied CI results.", exact=False)).to_be_visible()
        expect(report.get_by_text(head, exact=True).first).to_be_visible()
        expect(report.get_by_text(review["review_id"], exact=True)).to_be_visible()
        expect(report.get_by_text(review["repository"], exact=True)).to_be_visible()
        expect(report.get_by_text(f'#{review["pr_number"]}', exact=True)).to_be_visible()
        criteria_sha = review["criteria_source_provenance"]["normalized_criteria_sha256"]
        expect(report.get_by_text(criteria_sha, exact=True)).to_be_visible()
        expect(report.get_by_text(manifest_sha, exact=True)).to_be_visible()
        expect(report.get_by_text("Configured local folder", exact=True)).to_be_visible()
        criteria = state["bundle"]["criteria"]
        expected_tests = ("category_filter", "row_entitlement", "csv_header")
        follow_up = report.get_by_role("region", name="CI follow-up")
        if all(status == "Passed" for status in statuses):
            expect(follow_up.get_by_text(
                "All mapped CI tests reported a pass for this commit.", exact=True,
            )).to_be_visible()
        for criterion, test_id, status in zip(criteria, expected_tests, statuses, strict=True):
            follow_up_row = follow_up.get_by_role("row").filter(
                has=report.get_by_role("cell", name=test_id, exact=True),
            )
            if status == "Passed":
                expect(follow_up_row).to_have_count(0)
            else:
                expect(follow_up_row.get_by_role("cell", name=status, exact=True)).to_be_visible()
            section = report.get_by_role("region", name=criterion["criterion_id"], exact=True)
            expect(section.get_by_text(criterion["text"], exact=True)).to_be_visible()
            row = section.get_by_role("row").filter(
                has=report.get_by_role("cell", name=test_id, exact=True),
            )
            expect(row.get_by_role("cell", name=status, exact=True)).to_be_visible()
            expect(row.get_by_role("cell").nth(2)).not_to_be_empty()
            if test_id == "row_entitlement":
                fragment = row.get_by_role("link").get_attribute("href")
                assert fragment is not None and fragment.startswith("#ci-run-")
                run = report.locator(fragment)
                run_url = f"https://ci.example.invalid/builds/{access_run}"
                expect(run.get_by_text(access_run, exact=True)).to_be_visible()
                expect(run.get_by_text(head, exact=True)).to_be_visible()
                expect(run.get_by_role("link", name=run_url)).to_have_attribute("href", run_url)
        if access_run == "B-targeted":
            _assert_narrow_report_tables(report)
        assert requests == []
    finally:
        report.close()


def test_installed_offline_ci_snapshots_follow_the_two_build_handoff(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    runtime = tmp_path / "snapshot-runtime"
    home = runtime / "home"
    home.mkdir(parents=True)
    scenario = runtime / "scenario"
    recipe = runtime / "simulate_ci_manifest.py"
    shutil.copy2(REPOSITORY_ROOT / "scripts" / recipe.name, recipe)
    python = str(installed_wheel / "bin" / "python")
    _run(python, "-I", str(recipe), "--prepare-workbench", str(scenario), cwd=runtime)
    storage = scenario / "reviews"
    original_bytes = {path: path.read_bytes() for path in storage.glob("*.json")}
    assert len(original_bytes) == 2
    reviews = {}
    for path, payload in original_bytes.items():
        state = json.loads(payload)["state"]
        reviews[state["review"]["head_sha"]] = (path, state)
    diagnostics = Path(
        os.environ.get("SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"))
    ) / "offline-ci-snapshot"
    external_requests: list[str] = []
    with _installed_workbench_server(
        installed_wheel, runtime, home, log_name="ci-snapshot.log", storage_directory=storage,
        ci_manifest_directory=scenario / "manifests",
    ) as (url, log_path), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport=VIEWPORTS[0])
            context.route("**/*", lambda route: _route_loopback_only(route, external_requests))
            recipient = browser.new_context(offline=True)
            page = context.new_page()
            with _capture_browser_failure(page, diagnostics, log_path):
                page.goto(url, wait_until="domcontentloaded")
                for build, statuses in (
                    ("A", ("Passed", "Passed", "Passed")),
                    ("B", ("Failed", "Explicitly skipped", "Passed")),
                ):
                    head = json.loads((scenario / f"{build}-fixture.json").read_bytes())["head_sha"]
                    record, state = reviews[head]
                    panel = _open_build(page, record, head)
                    _assert_offline_snapshot(
                        page, recipient, runtime / f"{build}.html", state=state,
                        manifest=(scenario / f"{build}-scopeproof-manifest.json").read_bytes(),
                        statuses=statuses, access_run=build,
                    )
                ordinary_html = _download_with_retry(page, button_name="Download HTML")
                before = ordinary_html.path().read_bytes()
                _run(python, "-I", str(recipe), "--publish-targeted", str(scenario), cwd=runtime)
                panel.get_by_role("button", name="Refresh CI status", exact=True).click()
                access_row = _criterion_status_table(page, panel).get_by_role("row").filter(
                    has=page.get_by_role("cell", name="AC-02", exact=True),
                )
                expect(access_row.get_by_role("cell", name="Failed", exact=True)).to_be_visible()
                _assert_offline_snapshot(
                    page, recipient, runtime / "B-targeted.html", state=state,
                    manifest=(scenario / "B-targeted-scopeproof-manifest.json").read_bytes(),
                    statuses=("Failed", "Failed", "Passed"), access_run="B-targeted",
                )
                ordinary_html = _download_with_retry(page, button_name="Download HTML")
                assert ordinary_html.path().read_bytes() == before
                assert _download_review_state(page) == state
        finally:
            browser.close()
    assert {path: path.read_bytes() for path in storage.glob("*.json")} == original_bytes
    assert external_requests == []
