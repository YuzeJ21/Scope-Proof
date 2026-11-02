"""Disposable installed-workbench JUnit audit journeys with constructed actors only."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import Locator, Page, expect, sync_playwright

from tests.browser.test_packaged_workbench import (
    REPOSITORY_ROOT,
    VIEWPORTS,
    _capture_browser_failure,
    _choose_combobox_option,
    _download_review_state,
    _download_with_retry,
    _installed_workbench_server,
    _is_loopback_request,
    _route_loopback_only,
    _run,
    _run_and_wait_for_streamlit_rerun,
)
from tests.browser.test_packaged_workbench import (
    installed_wheel as installed_wheel,
)

pytestmark = pytest.mark.browser

REVIEW_ID = "constructed-junit-audit-review"
IMPORT_ID = "constructed-junit-import"
ACTOR = "CONSTRUCTED browser withdrawal actor"
HOSTILE_REASON = (
    'CONSTRUCTED mistaken whole-import context. <script>'
    'window.__scopeproofJUnitExecuted=true</script> '
    '<img src="https://junit-audit.invalid/image" '
    'onerror="window.__scopeproofJUnitExecuted=true"> '
    '[recorded link](https://junit-audit.invalid/reason) '
    + "ConstructedUnbrokenReason" * 10
)


def _seed_installed_review(installed: Path, runtime: Path, home: Path) -> tuple[Path, dict]:
    """Run only a copied product-import recipe outside the checkout with explicit storage."""
    home.mkdir(parents=True)
    store = home / ".scopeproof" / "reviews"
    recipe = runtime / "constructed-junit-audit.py"
    shutil.copy2(REPOSITORY_ROOT / "tests" / "junit_audit_fixture.py", recipe)
    _run(
        str(installed / "bin" / "python"), "-I", "-c",
        "from pathlib import Path; import runpy, sys; import apps, scopeproof_core; "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        "assert all(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()) "
        "for module in (apps, scopeproof_core)); "
        "recipe=runpy.run_path(sys.argv[1]); "
        "JsonReviewStore(Path(sys.argv[2])).save(recipe['junit_audit_state']())",
        str(recipe), str(store), cwd=runtime,
    )
    record = store / f"{REVIEW_ID}.json"
    envelope = json.loads(record.read_text(encoding="utf-8"))
    assert envelope["record_version"] == 9
    state = envelope["state"]
    assert state["bundle"]["junit_import_events"] == []
    assert state["bundle"]["active_junit_import_ids"] == [IMPORT_ID]
    assert len(state["bundle"]["junit_evidence_imports"][0]["criterion_mappings"]) == 2
    return record, state


def _reopen(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page, page.get_by_role("combobox", name="Saved review ID", exact=True),
        option_name=REVIEW_ID, settled_control=reopen,
    )
    reopen.click()
    expect(page.get_by_text(
        "Review reopened from local storage after validation.", exact=True,
    )).to_be_visible()
    expect(page.get_by_role(
        "button", name="Load matching reviewed source", exact=True,
    )).to_be_visible()


def _open_withdrawal_form(page: Page) -> None:
    control = page.get_by_role("combobox", name="Active JUnit import", exact=True)
    if not control.is_visible():
        page.get_by_text("Withdraw a saved JUnit import", exact=True).click()
    expect(control).to_have_value("")
    expect(page.get_by_role(
        "button", name="Withdraw selected JUnit import", exact=True,
    )).to_be_disabled()


def _stage_withdrawal(page: Page) -> None:
    _open_withdrawal_form(page)
    target = page.get_by_role("combobox", name="Active JUnit import", exact=True)
    _choose_combobox_option(page, target, option_name=IMPORT_ID)
    expect(target).to_be_visible()
    for label, value in (("Withdrawal reviewer", ACTOR), ("Withdrawal reason", HOSTILE_REASON)):
        control = page.get_by_label(label, exact=True)
        control.fill(value)
        _run_and_wait_for_streamlit_rerun(page, lambda field=control: field.press("Tab"))
    expect(page.get_by_role(
        "button", name="Withdraw selected JUnit import", exact=True,
    )).to_be_enabled()
    for name in ("Download JSON", "Download Markdown", "Download CSV"):
        expect(page.get_by_role("button", name=name, exact=True)).to_be_disabled()


def _recorded_import(page: Page, state: dict, criterion: str, status: str) -> Locator:
    _choose_combobox_option(
        page, page.get_by_role("combobox", name="Inspect criterion", exact=True),
        option_name=criterion,
    )
    title = page.get_by_text("Recorded imported JUnit results (1)", exact=True)
    block = title.locator("xpath=ancestor::details[1]")
    if block.get_attribute("open") is None:
        title.click()
    expect(block.get_by_text("Import status", exact=True)).to_be_visible()
    expect(block.get_by_text(status, exact=True).first).to_be_visible()
    expect(block.get_by_text(IMPORT_ID, exact=True).first).to_be_visible()
    imported = state["bundle"]["junit_evidence_imports"][0]
    expect(block.get_by_text(imported["artifact_sha256"], exact=True).first).to_be_visible()
    mapping = next(item for item in imported["criterion_mappings"]
                   if item["criterion_id"] == criterion)
    for case in imported["test_cases"]:
        if case["test_case_id"] in mapping["test_case_ids"]:
            expect(block.get_by_text(
                f"{case['test_case_id']} · {case['status']} · {case['test_name']}", exact=True,
            )).to_be_visible()
    expect(block.locator("script, img, a")).to_have_count(0)
    assert page.evaluate("window.__scopeproofJUnitExecuted === undefined")
    return block


def _assert_audit_only_change(before: dict, after: dict) -> None:
    for key in before.keys() - {"bundle"}:
        assert before[key] == after[key]
    previous, current = dict(before["bundle"]), dict(after["bundle"])
    for payload in (previous, current):
        payload.pop("junit_import_events")
        payload.pop("active_junit_import_ids")
    assert previous == current
    assert after["bundle"]["active_junit_import_ids"] == []
    events = after["bundle"]["junit_import_events"]
    assert len(events) == 1
    event = events[0]
    assert event["import_id"] == IMPORT_ID
    assert event["reviewer"] == ACTOR
    assert event["reason"] == HOSTILE_REASON
    assert event["artifact_sha256"] == before["bundle"]["junit_evidence_imports"][0][
        "artifact_sha256"
    ]
    assert event["occurred_at"].endswith(("Z", "+00:00"))


def _capture_automated_audit(page: Page, captures: Path, state: dict) -> None:
    manifest = {
        "actor": "constructed automated browser", "personal_testing": False,
        "qualifying_review": False, "accessibility_conformance": False, "captures": [],
    }
    for viewport, zoom, layout in (
        (VIEWPORTS[0], "", "desktop"), (VIEWPORTS[1], "", "phone-390"),
        (VIEWPORTS[1], "2", "phone-390-css-zoom-200"),
    ):
        page.set_viewport_size(viewport)
        page.evaluate("value => { document.documentElement.style.zoom = value; }", zoom)
        block = _recorded_import(page, state, "AC-01", "Withdrawn")
        anchor = block.get_by_text(HOSTILE_REASON, exact=True)
        expect(anchor).to_be_visible()
        anchor.evaluate("element => element.scrollIntoView({block: 'center'})")
        expect(anchor).to_be_in_viewport()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        geometry = block.evaluate("""element => {
            const bounds = element.getBoundingClientRect();
            return {left: bounds.left, right: bounds.right,
                    clientWidth: element.clientWidth, scrollWidth: element.scrollWidth};
        }""")
        assert geometry["left"] >= -1
        assert geometry["right"] <= viewport["width"] + 1
        assert geometry["scrollWidth"] <= geometry["clientWidth"] + 1
        name = f"automated-junit-withdrawal-{layout}.png"
        page.screenshot(path=str(captures / name))
        manifest["captures"].append({
            "file": name, "viewport": viewport, "css_zoom": zoom or "1",
            "visible_anchor": "recorded withdrawal reason", "geometry": geometry,
        })
    page.evaluate("document.documentElement.style.zoom = ''")
    page.set_viewport_size(VIEWPORTS[0])
    (captures / "automated-junit-withdrawal-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8",
    )


def test_installed_wheel_whole_junit_import_withdrawal_survives_source_free_restart(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    """Real downloads retain both original mappings and one attributed terminal event."""
    runtime = tmp_path / "runtime"
    home = runtime / "home"
    record, original = _seed_installed_review(installed_wheel, runtime, home)
    original_bytes = record.read_bytes()
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / "junit-withdrawal"
    captures = diagnostics / "captures"
    captures.mkdir(parents=True)
    external_requests: list[str] = []
    browser_errors: list[str] = []
    saved = None
    saved_bytes = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for generation in range(2):
                with _installed_workbench_server(
                    installed_wheel, runtime, home, log_name=f"junit-audit-{generation}.log",
                ) as (base_url, log_path):
                    context = browser.new_context(viewport=VIEWPORTS[0])
                    try:
                        context.route(
                            "**/*", lambda route: _route_loopback_only(route, external_requests),
                        )
                        page = context.new_page()
                        page.on("pageerror", lambda error: browser_errors.append(str(error)))
                        page.on("websocket", lambda websocket: (
                            external_requests.append(websocket.url)
                            if not _is_loopback_request(websocket.url) else None
                        ))
                        with _capture_browser_failure(
                            page, diagnostics / f"generation-{generation}", log_path,
                        ):
                            _reopen(page, base_url)
                            if generation == 0:
                                assert _download_review_state(page) == original
                                _recorded_import(page, original, "AC-01", "Active")
                                _stage_withdrawal(page)
                                assert record.read_bytes() == original_bytes
                                save = page.get_by_role(
                                    "button", name="Withdraw selected JUnit import", exact=True,
                                )
                                _run_and_wait_for_streamlit_rerun(page, save.click)
                                saved = _download_review_state(page)
                                _assert_audit_only_change(original, saved)
                                saved_bytes = record.read_bytes()
                                assert json.loads(saved_bytes)["state"] == saved
                            assert saved is not None
                            assert saved_bytes is not None
                            for criterion in ("AC-01", "AC-02"):
                                block = _recorded_import(page, saved, criterion, "Withdrawn")
                                expect(block.get_by_text(ACTOR, exact=True)).to_be_visible()
                                expect(block.get_by_text(
                                    HOSTILE_REASON, exact=True,
                                )).to_be_visible()
                                recorded_at = block.get_by_text("Withdrawn at (UTC)", exact=True)
                                timestamp_value = recorded_at.locator(
                                    'xpath=ancestor::div[@data-testid="stElementContainer"][1]'
                                    '/following-sibling::*[1]',
                                )
                                expect(timestamp_value).to_have_text(
                                    saved["bundle"]["junit_import_events"][0][
                                        "occurred_at"
                                    ].replace("Z", "+00:00"),
                                )
                            assert _download_review_state(page) == saved
                            markdown = _download_with_retry(page, button_name="Download Markdown")
                            report = markdown.path().read_text(encoding="utf-8")
                            imported_section = report.split(
                                "## Imported External Test Results", 1,
                            )[1].split("\n## ", 1)[0]
                            assert "Withdrawn" in imported_section
                            assert "<script>" not in imported_section
                            assert "<img " not in imported_section
                            assert "<a " not in imported_section
                            reason_lines = [
                                line.removeprefix("- Withdrawal reason: ")
                                for line in imported_section.splitlines()
                                if line.startswith("- Withdrawal reason: ")
                            ]
                            assert len(reason_lines) == 1
                            assert r"\[recorded link\]\(" in reason_lines[0]
                            assert "](" not in reason_lines[0]
                            assert html.unescape(re.sub(
                                r"\\(.)", r"\1", reason_lines[0],
                            )) == HOSTILE_REASON
                            decoded = html.unescape(re.sub(r"\\(.)", r"\1", imported_section))
                            for value in (IMPORT_ID, ACTOR, HOSTILE_REASON, "AC-01", "AC-02"):
                                assert value in decoded
                            assert record.read_bytes() == saved_bytes
                            withdrawal = page.get_by_role(
                                "button", name="Withdraw selected JUnit import", exact=True,
                            )
                            if not withdrawal.is_visible():
                                page.get_by_text(
                                    "Withdraw a saved JUnit import", exact=True,
                                ).click()
                            expect(withdrawal).to_be_disabled()
                            if generation == 0:
                                _capture_automated_audit(page, captures, saved)
                                assert record.read_bytes() == saved_bytes
                    finally:
                        context.close()
                assert record.read_bytes() == saved_bytes
        finally:
            browser.close()
    assert browser_errors == []
    assert external_requests == []
    assert len(list(captures.glob("automated-junit-withdrawal-*.png"))) == 3


@pytest.mark.parametrize("external_action", ["changed", "deleted"])
def test_installed_wheel_queued_junit_withdrawal_rejects_changed_or_deleted_record(
    tmp_path: Path, installed_wheel: Path, external_action: str,
) -> None:
    """A queued click cannot overwrite an external update or recreate a deleted record."""
    runtime = tmp_path / "runtime"
    home = runtime / "home"
    record, _original = _seed_installed_review(installed_wheel, runtime, home)
    store = record.parent
    external_requests: list[str] = []
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / f"junit-withdrawal-{external_action}"
    with _installed_workbench_server(
        installed_wheel, runtime, home, log_name=f"junit-{external_action}.log",
    ) as (url, log_path), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport=VIEWPORTS[0])
            context.route("**/*", lambda route: _route_loopback_only(route, external_requests))
            page = context.new_page()
            with _capture_browser_failure(page, diagnostics, log_path):
                _reopen(page, url)
                _stage_withdrawal(page)
                action = (
                    "store.delete(sys.argv[2])"
                    if external_action == "deleted" else
                    "store.mutate(sys.argv[2], lambda state: append_resolution(state, "
                    "ResolutionEvent(criterion_id='AC-02', decision=HumanDecision.CHANGE_REQUIRED, "
                    "reviewer='CONSTRUCTED external updater', "
                    "comment='CONSTRUCTED external decision update')))"
                )
                _run(
                    str(installed_wheel / "bin" / "python"), "-I", "-c",
                    "from pathlib import Path; import sys; "
                    "from scopeproof_core.storage.json_store import JsonReviewStore; "
                    "from scopeproof_core.reviews.lifecycle import append_resolution; "
                    "from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent; "
                    "store=JsonReviewStore(Path(sys.argv[1])); " + action,
                    str(store), REVIEW_ID, cwd=runtime,
                )
                external_bytes = record.read_bytes() if record.exists() else None
                save = page.get_by_role(
                    "button", name="Withdraw selected JUnit import", exact=True,
                )
                _run_and_wait_for_streamlit_rerun(page, save.click)
                expect(save).to_be_disabled()
                for name in ("Download JSON", "Download Markdown", "Download CSV"):
                    expect(page.get_by_role("button", name=name, exact=True)).to_be_disabled()
                if external_action == "deleted":
                    assert not record.exists()
                else:
                    assert record.read_bytes() == external_bytes
                    assert json.loads(record.read_text(encoding="utf-8"))["state"]["bundle"][
                        "junit_import_events"
                    ] == []
        finally:
            browser.close()
    assert external_requests == []
