"""Installed, source-free mapping corrections by constructed automated actors only."""

from __future__ import annotations

import csv
import html
import io
import json
import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from tests.browser.test_junit_withdrawal import IMPORT_ID, REVIEW_ID, _reopen
from tests.browser.test_packaged_workbench import (
    REPOSITORY_ROOT,
    VIEWPORTS,
    _capture_browser_failure,
    _choose_combobox_option,
    _choose_multiselect_option,
    _download_review_state,
    _download_with_retry,
    _installed_workbench_server,
    _route_loopback_only,
    _run,
    _run_and_wait_for_streamlit_rerun,
)
from tests.browser.test_packaged_workbench import installed_wheel as installed_wheel

pytestmark = pytest.mark.browser

ACTOR = "CONSTRUCTED browser mapping correction actor"
REASON = (
    'CONSTRUCTED organizational correction. <script>'
    'window.__scopeproofCorrectionExecuted=true</script> '
    '<img src="https://correction.invalid/image" '
    'onerror="window.__scopeproofCorrectionExecuted=true"> '
    '[recorded link](https://correction.invalid/reason) '
    + "ConstructedUnbrokenCorrection" * 10
)
CASE_IDS = [f"suite-0001-case-{number:04d}" for number in range(1, 4)]
EXPECTED_MAPPINGS = [
    {"criterion_id": "AC-02", "test_case_ids": CASE_IDS[1:]},
    {"criterion_id": "AC-03", "test_case_ids": CASE_IDS[:1]},
]


def _seed(installed: Path, runtime: Path, home: Path) -> tuple[Path, dict]:
    """Copy the trusted constructed recipe; execute with installed product imports only."""
    home.mkdir(parents=True)
    recipe_text = (REPOSITORY_ROOT / "tests" / "junit_audit_fixture.py").read_text()
    old = '        Criterion(criterion_id="AC-02", text="CONSTRUCTED failure behavior"),'
    assert recipe_text.count(old) == 1
    recipe_text = recipe_text.replace(
        old, old + '\n        Criterion(criterion_id="AC-03", text="CONSTRUCTED third behavior"),',
    )
    old_xml = "    b'</testsuite>'"
    assert recipe_text.count(old_xml) == 1
    recipe_text = recipe_text.replace(
        old_xml, "    b'<testcase name=\"CONSTRUCTED unassigned third case\"/>'\n" + old_xml,
    )
    recipe = runtime / "constructed-junit-correction.py"
    recipe.write_text(recipe_text, encoding="utf-8")
    store = home / ".scopeproof" / "reviews"
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
    assert envelope["record_version"] in (8, 9)
    state = envelope["state"]
    assert len(state["bundle"]["criteria"]) == 3
    imported = state["bundle"]["junit_evidence_imports"][0]
    assert [case["test_case_id"] for case in imported["test_cases"]] == CASE_IDS
    assert imported["criterion_mappings"] == [
        {"criterion_id": "AC-01", "test_case_ids": CASE_IDS[:1]},
        {"criterion_id": "AC-02", "test_case_ids": CASE_IDS[1:2]},
    ]
    assert state["bundle"]["junit_import_events"] == []
    return record, state


def _button(page: Page, name: str):
    return page.get_by_role("button", name=name, exact=True)


def _open_panel(page: Page) -> None:
    inspect = page.get_by_role("combobox", name="Inspect criterion", exact=True)
    selected_criterion = inspect.input_value()
    target = page.get_by_role("combobox", name="JUnit import to correct", exact=True)
    if not target.is_visible():
        page.get_by_text("Correct saved JUnit mappings", exact=True).click()
    _choose_combobox_option(page, target, option_name=IMPORT_ID)
    expect(inspect).to_have_value(selected_criterion)
    expect(_button(page, "Save corrected JUnit mappings")).to_be_disabled()


def _downloads(page: Page, *, pending: bool) -> None:
    for name in ("Download JSON", "Download Markdown", "Download CSV"):
        if pending:
            expect(_button(page, name)).to_be_disabled()
        else:
            expect(_button(page, name)).to_be_enabled()


def _previews(page: Page, original: list[dict], current: list[dict], staged: list[dict]) -> None:
    panel = page.locator(".st-key-junit_correction_panel")
    for label in (
        "Original mappings (retained)", "Current effective mappings", "Staged corrected mappings",
    ):
        expect(panel.get_by_text(label, exact=True)).to_be_visible()
    blocks = panel.locator('[data-testid="stCode"] code')
    expect(blocks).to_have_count(3)
    assert [json.loads(block.inner_text()) for block in blocks.all()] == [original, current, staged]


def _replace_group(page: Page, state: dict, criterion: str, case_ids: list[str]) -> None:
    _choose_combobox_option(
        page, page.get_by_role("combobox", name="Correction criterion", exact=True),
        option_name=criterion,
    )
    control = page.get_by_role("combobox", name="Correction test cases", exact=True)
    cases = state["bundle"]["junit_evidence_imports"][0]["test_cases"]
    for case_id in case_ids:
        case = next(case for case in cases if case["test_case_id"] == case_id)
        _choose_multiselect_option(
            page, control, query=case_id, option_name=f"{case_id} · {case['test_name']}",
        )
    control.press("Escape")
    expect(control).to_have_attribute("aria-expanded", "false")
    page.get_by_text("Staged corrected mappings", exact=True).click()
    expect(page.get_by_role("listbox", name="Correction test cases Open")).to_have_count(0)
    page.wait_for_function(
        "document.querySelector('[data-testid=stApp]')?.getAttribute("
        "'data-test-script-state') === 'notRunning'",
    )
    expect(_button(page, "Stage criterion mapping")).to_be_enabled()
    _run_and_wait_for_streamlit_rerun(page, _button(page, "Stage criterion mapping").click)


def _stage(page: Page, state: dict, *, exercise_guards: bool = False) -> None:
    _open_panel(page)
    _downloads(page, pending=False)  # A pristine initialized preview is not an edit.
    if exercise_guards:
        _choose_combobox_option(
            page, page.get_by_role("combobox", name="Correction criterion", exact=True),
            option_name="AC-01",
        )
        _downloads(page, pending=True)  # Unstaged controls must block handoffs.
        _replace_group(page, state, "AC-01", CASE_IDS[:1])
        expect(_button(page, "Save corrected JUnit mappings")).to_be_disabled()
        _downloads(page, pending=False)  # Staging an identical group leaves no actual change.
        inspect = page.get_by_role("combobox", name="Inspect criterion", exact=True)
        _choose_combobox_option(
            page, inspect, option_name="AC-03" if inspect.input_value() == "AC-02" else "AC-02",
        )
        expect(page.get_by_role(
            "combobox", name="JUnit import to correct", exact=True,
        )).to_have_value("")
        _open_panel(page)
    _choose_combobox_option(
        page, page.get_by_role("combobox", name="Remove mapped criterion", exact=True),
        option_name="AC-01",
    )
    _run_and_wait_for_streamlit_rerun(page, _button(page, "Remove criterion mapping").click)
    _replace_group(page, state, "AC-02", CASE_IDS[1:])
    _replace_group(page, state, "AC-03", CASE_IDS[:1])
    original = state["bundle"]["junit_evidence_imports"][0]["criterion_mappings"]
    _previews(page, original, original, EXPECTED_MAPPINGS)
    for label, value in (("Correction reviewer", ACTOR), ("Correction reason", REASON)):
        control = page.get_by_label(label, exact=True)
        control.fill(value)
        _run_and_wait_for_streamlit_rerun(page, lambda field=control: field.press("Tab"))
    confirm = page.get_by_role(
        "checkbox", name="I confirm these mappings for the whole import", exact=True,
    )
    expect(confirm).not_to_be_checked()
    expect(_button(page, "Save corrected JUnit mappings")).to_be_disabled()
    confirm_label = page.get_by_text("I confirm these mappings for the whole import", exact=True)
    _run_and_wait_for_streamlit_rerun(page, confirm_label.click)
    expect(confirm).to_be_checked()
    expect(_button(page, "Save corrected JUnit mappings")).to_be_enabled()
    if exercise_guards:
        _choose_combobox_option(
            page, page.get_by_role("combobox", name="Correction criterion", exact=True),
            option_name="AC-02",
        )
        expect(confirm).not_to_be_checked()
        expect(_button(page, "Save corrected JUnit mappings")).to_be_disabled()
        _replace_group(page, state, "AC-02", CASE_IDS[1:])
        _run_and_wait_for_streamlit_rerun(page, confirm_label.click)
        expect(confirm).to_be_checked()
        expect(_button(page, "Save corrected JUnit mappings")).to_be_enabled()
    _downloads(page, pending=True)


def _assert_only_correction(before: dict, after: dict) -> dict:
    assert before.keys() == after.keys()
    for key in before.keys() - {"bundle"}:
        assert before[key] == after[key]
    previous, current = dict(before["bundle"]), dict(after["bundle"])
    for payload in (previous, current):
        payload.pop("junit_import_events")
        payload.pop("effective_junit_mappings", None)
    assert previous == current
    assert after["bundle"]["active_junit_import_ids"] == [IMPORT_ID]
    assert after["bundle"]["effective_junit_mappings"][IMPORT_ID] == EXPECTED_MAPPINGS
    events = after["bundle"]["junit_import_events"]
    assert len(events) == 1
    event = events[0]
    assert event["action"] == "mapping_corrected"
    assert event["schema_version"] == "junit-mapping-correction-v1"
    assert event["reviewer"] == ACTOR
    assert event["reason"] == REASON
    assert event["criterion_mappings"] == EXPECTED_MAPPINGS
    assert event["previous_correction_event_id"] is None
    assert re.fullmatch(r"[0-9a-f]{64}", event["previous_mapping_sha256"])
    return event


def _associations(page: Page, state: dict) -> None:
    cases = state["bundle"]["junit_evidence_imports"][0]["test_cases"]
    for criterion, ids in (("AC-01", []), ("AC-02", CASE_IDS[1:]), ("AC-03", CASE_IDS[:1])):
        _choose_combobox_option(
            page, page.get_by_role("combobox", name="Inspect criterion", exact=True),
            option_name=criterion,
        )
        title = page.get_by_text(f"Recorded imported JUnit results ({int(bool(ids))})", exact=True)
        block = title.locator("xpath=ancestor::details[1]")
        if block.get_attribute("open") is None:
            title.click()
        for case in cases:
            case_text = f"{case['test_case_id']} · {case['status']} · {case['test_name']}"
            if case["test_case_id"] in ids:
                expect(block.get_by_text(case_text, exact=True)).to_be_visible()
            else:
                expect(block.get_by_text(case_text, exact=True)).to_have_count(0)
        if not ids:
            expect(block.get_by_text(
                "No external JUnit results are mapped to this criterion.", exact=True,
            )).to_be_visible()


def _audit_downloads(page: Page, state: dict, output: Path) -> None:
    event = state["bundle"]["junit_import_events"][0]
    assert _download_review_state(page) == state
    for kind in ("Markdown", "CSV"):
        download = _download_with_retry(page, button_name=f"Download {kind}")
        text = download.path().read_text(encoding="utf-8")
        (output / f"corrected.{kind.lower()}").write_text(text, encoding="utf-8")
        if kind == "Markdown":
            decoded = html.unescape(re.sub(r"\\(.)", r"\1", text))
            for value in _audit_strings(event):
                assert value.replace("Z", "+00:00") in decoded.replace("Z", "+00:00")
            assert "<script>" not in text and "<img " not in text
            assert "[recorded link](" not in text
        else:
            rows = {row["criterion_id"]: row for row in csv.DictReader(io.StringIO(text))}
            assert json.loads(rows["AC-01"]["junit_artifact_digests"]) == []
            assert json.loads(rows["AC-01"]["junit_mapped_cases"]) == []
            for criterion in ("AC-01", "AC-02", "AC-03"):
                audit = json.loads(rows[criterion]["junit_import_audit"])
                assert event in _audit_objects(audit)
            for mapping in EXPECTED_MAPPINGS:
                row = rows[mapping["criterion_id"]]
                cases = json.loads(row["junit_mapped_cases"])
                assert [case["test_case_id"] for case in cases] == mapping["test_case_ids"]
                assert all(case["import_id"] == IMPORT_ID for case in cases)


def _audit_strings(value):
    if isinstance(value, dict):
        return [item for child in value.values() for item in _audit_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _audit_strings(child)]
    return [value] if isinstance(value, str) else []


def _audit_objects(value):
    if isinstance(value, dict):
        return [value, *[item for child in value.values() for item in _audit_objects(child)]]
    if isinstance(value, list):
        return [item for child in value for item in _audit_objects(child)]
    return []


def _html_handoff(installed: Path, runtime: Path, record: Path, page: Page, output: Path) -> None:
    report = output / "corrected.html"
    _run(
        str(installed / "bin" / "python"), "-I", "-c",
        "from contextlib import redirect_stdout\n"
        "from pathlib import Path\n"
        "import sys\n"
        "from scopeproof_core.cli import main\n"
        "with Path(sys.argv[3]).open('w', encoding='utf-8') as output, redirect_stdout(output):\n"
        "    result=main(['export', sys.argv[1], '--storage-dir', sys.argv[2],\n"
        "                 '--format', 'html'])\n"
        "assert result == 0\n",
        REVIEW_ID, str(record.parent), str(report), cwd=runtime,
    )
    text = report.read_text(encoding="utf-8")
    assert html.escape(REASON) in text
    assert "<script>" not in text and "<img " not in text
    parsed = page.evaluate("""source => {
        const doc = new DOMParser().parseFromString(source, 'text/html');
        return {text: doc.body.textContent, unsafe: doc.querySelectorAll('script,img').length,
                hostileLinks: doc.querySelectorAll('a[href*="correction.invalid"]').length};
    }""", text)
    assert parsed["unsafe"] == 0 and parsed["hostileLinks"] == 0
    assert REASON in parsed["text"]


def test_installed_wheel_junit_mapping_correction_survives_source_free_restart(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    """A whole snapshot moves, removes and newly assigns retained cases without gate changes."""
    runtime, home = tmp_path / "runtime", tmp_path / "runtime" / "home"
    record, original = _seed(installed_wheel, runtime, home)
    original_bytes = record.read_bytes()
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / "junit-correction"
    diagnostics.mkdir(parents=True)
    external: list[str] = []
    errors: list[str] = []
    saved = None
    saved_bytes = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for generation in range(2):
                with _installed_workbench_server(
                    installed_wheel, runtime, home, log_name=f"correction-{generation}.log",
                ) as (url, log):
                    context = browser.new_context(viewport=VIEWPORTS[0])
                    context.route("**/*", lambda route: _route_loopback_only(route, external))
                    try:
                        page = context.new_page()
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        with _capture_browser_failure(page, diagnostics / str(generation), log):
                            _reopen(page, url)
                            if generation == 0:
                                assert _download_review_state(page) == original
                                _stage(page, original, exercise_guards=True)
                                assert record.read_bytes() == original_bytes
                                _run_and_wait_for_streamlit_rerun(
                                    page, _button(page, "Save corrected JUnit mappings").click,
                                )
                                expect(page.get_by_text(
                                    "JUnit mapping correction saved.", exact=True,
                                )).to_be_visible()
                                saved = _download_review_state(page)
                                _assert_only_correction(original, saved)
                                saved_bytes = record.read_bytes()
                                assert json.loads(saved_bytes)["state"] == saved
                            assert saved is not None and saved_bytes is not None
                            _associations(page, saved)
                            _audit_downloads(page, saved, diagnostics)
                            _html_handoff(installed_wheel, runtime, record, page, diagnostics)
                            if generation == 0:
                                _open_panel(page)
                                original_groups = original["bundle"]["junit_evidence_imports"][0][
                                    "criterion_mappings"
                                ]
                                _previews(
                                    page, original_groups, EXPECTED_MAPPINGS, EXPECTED_MAPPINGS,
                                )
                                title = page.get_by_text(
                                    "Recorded imported JUnit results (1)", exact=True,
                                )
                                audit = title.locator("xpath=ancestor::details[1]")
                                expect(audit.get_by_text(REASON, exact=True)).to_be_visible()
                                audit_text = audit.inner_text()
                                event = saved["bundle"]["junit_import_events"][0]
                                for value in _audit_strings(event):
                                    assert value.replace("Z", "+00:00") in audit_text.replace(
                                        "Z", "+00:00",
                                    )
                                expect(audit.locator("script, img, a")).to_have_count(0)
                                assert page.evaluate(
                                    "window.__scopeproofCorrectionExecuted === undefined",
                                )
                                for viewport, zoom, name in (
                                    (VIEWPORTS[0], "", "desktop"),
                                    (VIEWPORTS[1], "", "phone"),
                                    (VIEWPORTS[1], "2", "phone-zoom-200"),
                                ):
                                    page.set_viewport_size(viewport)
                                    page.evaluate(
                                        "value => document.documentElement.style.zoom = value",
                                        zoom,
                                    )
                                    reason = audit.get_by_text(REASON, exact=True)
                                    reason.scroll_into_view_if_needed()
                                    assert page.evaluate(
                                        "document.documentElement.scrollWidth <= window.innerWidth",
                                    )
                                    assert audit.evaluate(
                                        "e => e.scrollWidth <= e.clientWidth + 1",
                                    )
                                    page.screenshot(path=str(diagnostics / f"{name}.png"))
                                (diagnostics / "automated-correction-manifest.json").write_text(
                                    json.dumps({
                                        "actor": "constructed automated browser",
                                        "personal_testing": False,
                                        "qualifying_review": False,
                                        "accessibility_conformance": False,
                                        "captures": [
                                            "desktop.png", "phone.png", "phone-zoom-200.png",
                                        ],
                                    }, indent=2), encoding="utf-8",
                                )
                            assert record.read_bytes() == saved_bytes
                    finally:
                        context.close()
                assert record.read_bytes() == saved_bytes
        finally:
            browser.close()
    assert errors == [] and external == []
    assert len(list(diagnostics.glob("*.png"))) == 3


@pytest.mark.parametrize("external_action", ["changed", "deleted"])
def test_installed_wheel_queued_junit_mapping_correction_rejects_external_change(
    tmp_path: Path, installed_wheel: Path, external_action: str,
) -> None:
    """A prepared request retains its draft and never overwrites or recreates a record."""
    runtime, home = tmp_path / "runtime", tmp_path / "runtime" / "home"
    record, original = _seed(installed_wheel, runtime, home)
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / f"junit-correction-{external_action}"
    external: list[str] = []
    with _installed_workbench_server(
        installed_wheel, runtime, home, log_name=f"correction-{external_action}.log",
    ) as (url, log), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport=VIEWPORTS[0])
            context.route("**/*", lambda route: _route_loopback_only(route, external))
            page = context.new_page()
            with _capture_browser_failure(page, diagnostics, log):
                _reopen(page, url)
                _stage(page, original)
                action = (
                    "store.delete(sys.argv[2])" if external_action == "deleted" else
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
                    str(record.parent), REVIEW_ID, cwd=runtime,
                )
                external_bytes = record.read_bytes() if record.exists() else None
                _run_and_wait_for_streamlit_rerun(
                    page, _button(page, "Save corrected JUnit mappings").click,
                )
                expect(_button(page, "Save corrected JUnit mappings")).to_be_disabled()
                _downloads(page, pending=True)
                expect(page.get_by_label("Correction reviewer", exact=True)).to_have_value(ACTOR)
                expect(page.get_by_label("Correction reason", exact=True)).to_have_value(REASON)
                expect(page.get_by_text(
                    "JUnit mapping correction saved.", exact=True,
                )).to_have_count(0)
                if external_action == "deleted":
                    assert not record.exists()
                else:
                    assert record.read_bytes() == external_bytes
                    state = json.loads(external_bytes)["state"]
                    assert state["bundle"]["junit_import_events"] == []
        finally:
            browser.close()
    assert external == []
