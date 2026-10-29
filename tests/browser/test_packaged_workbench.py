from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from hashlib import sha256
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
from zipfile import ZipFile

import pytest
from playwright.sync_api import (
    Download,
    Locator,
    Page,
    Route,
    expect,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from scopeproof_core.schemas.models import JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION
from tests.candidate_selection_fixture import selection_criteria, selection_snapshot

pytestmark = pytest.mark.browser

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIEWPORTS = (
    {"width": 1280, "height": 720},
    {"width": 390, "height": 844},
)
FOCUS_STYLE_SCRIPT = """element => {
    const colorIsVisible = value => {
        const normalized = value.trim().toLowerCase();
        if (!normalized || normalized === "none" || normalized === "transparent") {
            return false;
        }
        if (/\\brgb\\(/.test(normalized)) {
            return true;
        }
        const alphaValues = [...normalized.matchAll(
            /rgba\\([^)]*,\\s*([0-9.]+)\\)/g
        )].map(match => Number(match[1]));
        if (alphaValues.length) {
            return alphaValues.some(alpha => alpha > 0);
        }
        return true;
    };
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return {
        boxShadow: style.boxShadow,
        boxShadowVisible:
            style.boxShadow !== "none" && colorIsVisible(style.boxShadow),
        inViewport:
            rect.bottom > 0 &&
            rect.top < window.innerHeight &&
            rect.right > 0 &&
            rect.left < window.innerWidth,
        outlineColor: style.outlineColor,
        outlineStyle: style.outlineStyle,
        outlineVisible:
            style.outlineStyle !== "none" &&
            parseFloat(style.outlineWidth) > 0 &&
            colorIsVisible(style.outlineColor),
        outlineWidth: parseFloat(style.outlineWidth),
    };
}"""
ARM_STREAMLIT_RERUN_OBSERVER_SCRIPT = """() => {
    if (window.__scopeproofRerunObserver) {
        window.__scopeproofRerunObserver.disconnect();
    }
    window.__scopeproofRerunObserved = false;
    const observer = new MutationObserver(mutations => {
        for (const mutation of mutations) {
            if (
                mutation.attributeName === "data-test-script-state" &&
                (
                    mutation.oldValue === "notRunning" ||
                    mutation.target.getAttribute("data-test-script-state") !==
                        "notRunning"
                )
            ) {
                window.__scopeproofRerunObserved = true;
            }
        }
    });
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-test-script-state"],
        attributeOldValue: true,
        subtree: true,
    });
    window.__scopeproofRerunObserver = observer;
}"""
STREAMLIT_RERUN_FINISHED_SCRIPT = """() => {
    const app = document.querySelector('[data-testid="stApp"]');
    return (
        window.__scopeproofRerunObserved === true &&
        app?.getAttribute("data-test-script-state") === "notRunning"
    );
}"""


def _run(*command: str, cwd: Path | None = None) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"command failed ({result.returncode}): {' '.join(command)}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _is_loopback_request(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme in {"http", "https", "ws", "wss"} and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _route_loopback_only(route: Route, external_requests: list[str]) -> None:
    if _is_loopback_request(route.request.url):
        route.continue_()
        return
    external_requests.append(route.request.url)
    route.abort()


def _wait_until_healthy(url: str, process: subprocess.Popen[str], log_path: Path) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(
                "installed workbench exited before becoming healthy:\n"
                + log_path.read_text(encoding="utf-8")
            )
        try:
            with urlopen(f"{url}/_stcore/health", timeout=1) as response:
                if response.read().decode("utf-8") == "ok":
                    return
        except OSError:
            time.sleep(0.25)
    pytest.fail(
        "installed workbench did not become healthy:\n"
        + log_path.read_text(encoding="utf-8")
    )


def test_focus_specific_treatment_rejects_unchanged_visible_decoration() -> None:
    always_on_shadow = {
        "boxShadow": "rgb(0, 0, 0) 0px 0px 0px 2px",
        "boxShadowVisible": True,
        "outlineColor": "rgb(0, 0, 0)",
        "outlineStyle": "none",
        "outlineVisible": False,
        "outlineWidth": 0,
    }

    assert not _has_focus_specific_treatment(always_on_shadow, always_on_shadow)


def test_focus_specific_treatment_accepts_changed_visible_outline() -> None:
    unfocused = {
        "boxShadow": "none",
        "boxShadowVisible": False,
        "outlineColor": "rgb(0, 0, 0)",
        "outlineStyle": "none",
        "outlineVisible": False,
        "outlineWidth": 0,
    }
    focused = {
        **unfocused,
        "outlineColor": "rgb(255, 191, 71)",
        "outlineStyle": "solid",
        "outlineVisible": True,
        "outlineWidth": 3,
    }

    assert _has_focus_specific_treatment(unfocused, focused)


def _has_focus_specific_treatment(
    unfocused: dict[str, bool | float | str],
    focused: dict[str, bool | float | str],
) -> bool:
    outline_changed = any(
        focused[key] != unfocused[key]
        for key in ("outlineColor", "outlineStyle", "outlineWidth")
    )
    shadow_changed = focused["boxShadow"] != unfocused["boxShadow"]
    return (
        bool(focused["outlineVisible"]) and outline_changed
    ) or bool(focused["boxShadowVisible"] and shadow_changed)


def _focus_with_keyboard(
    page: Page,
    control: Locator,
    *,
    label: str,
    max_presses: int = 80,
) -> None:
    expect(control).to_be_visible()
    unfocused_state = control.evaluate(FOCUS_STYLE_SCRIPT)
    assert not control.evaluate("element => element === document.activeElement"), (
        f"{label} must start unfocused so the regression can compare focus styles"
    )
    focus_trace: list[str] = []

    for _ in range(max_presses):
        page.keyboard.press("Tab")
        active = page.evaluate(
            """() => {
                const element = document.activeElement;
                if (!element) return "<none>";
                const name =
                    element.getAttribute("aria-label") ||
                    element.getAttribute("placeholder") ||
                    element.innerText ||
                    element.tagName;
                return `${element.tagName}: ${name.trim().replace(/\\s+/g, " ").slice(0, 120)}`;
            }"""
        )
        focus_trace.append(active)
        if not control.evaluate("element => element === document.activeElement"):
            continue

        expect(control).to_be_enabled()
        focus_state = control.evaluate(FOCUS_STYLE_SCRIPT)
        assert focus_state["inViewport"], f"{label} received focus outside the viewport"
        assert _has_focus_specific_treatment(unfocused_state, focus_state), (
            f"{label} has no changed, nontransparent focus-specific treatment; "
            f"unfocused={unfocused_state}, focused={focus_state}"
        )
        return

    pytest.fail(
        f"keyboard focus did not reach {label} after {max_presses} Tab presses; "
        f"trace={focus_trace}"
    )


def _activate_with_keyboard(
    page: Page,
    control: Locator,
    *,
    label: str,
    key: str,
) -> None:
    _focus_with_keyboard(page, control, label=label)
    page.keyboard.press(key)


def _run_and_wait_for_streamlit_rerun(
    page: Page, action: Callable[[], None]
) -> None:
    page.evaluate(ARM_STREAMLIT_RERUN_OBSERVER_SCRIPT)
    action()
    page.wait_for_function(STREAMLIT_RERUN_FINISHED_SCRIPT, timeout=10_000)


def _choose_combobox_option(
    page: Page,
    combobox: Locator,
    *,
    option_name: str,
    settled_control: Locator | None = None,
) -> None:
    for attempt in range(3):
        try:
            combobox.click()
            combobox.fill(option_name)
            option = page.get_by_role("option", name=option_name, exact=True)
            option.wait_for(state="visible", timeout=5_000)
            if option.get_attribute("aria-selected") == "true":
                combobox.press("Tab")
                expect(combobox).to_have_value(option_name, timeout=5_000)
                if settled_control is not None:
                    expect(settled_control).to_be_enabled(timeout=5_000)
                return
            _run_and_wait_for_streamlit_rerun(
                page,
                lambda selected_option=option: selected_option.click(timeout=5_000),
            )
            expect(combobox).to_have_value(option_name, timeout=5_000)
            if settled_control is not None:
                expect(settled_control).to_be_enabled(timeout=5_000)
            return
        except PlaywrightTimeoutError:
            if attempt == 2:
                raise


def _choose_multiselect_option(
    page: Page,
    combobox: Locator,
    *,
    query: str,
    option_name: str,
) -> None:
    selected_values = combobox.locator("xpath=../..")
    for attempt in range(3):
        if option_name in selected_values.inner_text():
            return
        try:
            combobox.click()
            combobox.fill(query)
            option = page.get_by_role("option", name=option_name, exact=True)
            expect(option).to_be_visible(timeout=5_000)
            _run_and_wait_for_streamlit_rerun(
                page, lambda selected_option=option: selected_option.click(timeout=5_000)
            )
            expect(selected_values).to_contain_text(option_name, timeout=5_000)
            return
        except PlaywrightTimeoutError:
            if attempt == 2:
                raise


def _download_with_retry(page: Page, *, button_name: str) -> Download:
    for attempt in range(3):
        download_button = page.get_by_role(
            "button", name=button_name, exact=True
        )
        expect(download_button).to_be_visible(timeout=5_000)
        expect(download_button).to_be_enabled(timeout=5_000)
        try:
            with page.expect_download(timeout=5_000) as download_info:
                download_button.click()
            return download_info.value
        except PlaywrightTimeoutError:
            if attempt == 2:
                raise
    raise AssertionError("download retry loop exhausted without a terminal result")


def _click_until_text_visible(
    page: Page, *, button_name: str, outcome_text: str
) -> None:
    outcome = page.get_by_text(outcome_text, exact=True)
    for attempt in range(3):
        if outcome.is_visible():
            return
        button = page.get_by_role("button", name=button_name, exact=True)
        try:
            expect(button).to_be_visible(timeout=5_000)
            expect(button).to_be_enabled(timeout=5_000)
            button.click(timeout=5_000)
            expect(outcome).to_be_visible(timeout=5_000)
            return
        except (AssertionError, PlaywrightTimeoutError):
            if outcome.is_visible():
                return
            if attempt == 2:
                raise


@contextmanager
def _capture_browser_failure(
    page: Page, destination: Path, server_log: Path,
) -> Iterator[None]:
    """Keep constructed-journey evidence without replacing its original failure."""
    page.context.tracing.start(screenshots=True, snapshots=True, sources=False)
    try:
        yield
    except Exception as failure:
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except Exception as capture_error:
            failure.add_note(f"Could not create browser diagnostics: {capture_error}")
        captures: tuple[tuple[str, Callable[[], object]], ...] = (
            ("failure.png", lambda: page.screenshot(path=str(destination / "failure.png"))),
            (
                "failure.aria.txt",
                lambda: (destination / "failure.aria.txt").write_text(
                    page.locator("body").aria_snapshot(), encoding="utf-8"
                ),
            ),
            ("server.log", lambda: shutil.copy2(server_log, destination / "server.log")),
            ("trace.zip", lambda: page.context.tracing.stop(path=str(destination / "trace.zip"))),
        )
        for name, capture in captures:
            try:
                capture()
            except Exception as capture_error:
                failure.add_note(f"Could not capture {name}: {capture_error}")
        failure.add_note(f"Constructed browser failure diagnostics: {destination}")
        raise
    else:
        page.context.tracing.stop()


def test_choose_combobox_option_retries_after_detached_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCombobox:
        def __init__(self) -> None:
            self.value = ""
            self.clicks = 0
            self.fills: list[str] = []

        def input_value(self) -> str:
            return self.value

        def click(self) -> None:
            self.clicks += 1

        def fill(self, value: str) -> None:
            self.fills.append(value)

        def press(self, key: str) -> None:
            assert key == "Tab"

    class FakeControl:
        def __init__(self) -> None:
            self.enabled = False

        def is_enabled(self) -> bool:
            return self.enabled

    class FakeOption:
        def __init__(self, combobox: FakeCombobox, control: FakeControl) -> None:
            self.combobox = combobox
            self.control = control
            self.clicks = 0

        def wait_for(self, *, state: str, timeout: int) -> None:
            assert state == "visible"

        def get_attribute(self, name: str) -> str:
            assert name == "aria-selected"
            return "false"

        def click(self, *, timeout: int | None = None) -> None:
            self.clicks += 1
            self.combobox.value = "junit-browser-review"
            if self.clicks == 1:
                raise PlaywrightTimeoutError("element was detached from the DOM")
            self.control.enabled = True

    class FakePage:
        def __init__(self, option: FakeOption) -> None:
            self.option = option

        def evaluate(self, script: str) -> None:
            return None

        def get_by_role(self, *args: object, **kwargs: object) -> FakeOption:
            return self.option

        def wait_for_function(self, script: str, *, timeout: int) -> None:
            return None

    class FakeExpectation:
        def __init__(self, target: object) -> None:
            self.target = target

        def to_be_visible(self, *, timeout: int | None = None) -> None:
            return None

        def to_have_value(self, expected: str, *, timeout: int | None = None) -> None:
            assert isinstance(self.target, FakeCombobox)
            assert self.target.value == expected

        def to_be_enabled(self, *, timeout: int | None = None) -> None:
            assert isinstance(self.target, FakeControl)
            if not self.target.enabled:
                raise PlaywrightTimeoutError("dependent control did not settle")

    combobox = FakeCombobox()
    control = FakeControl()
    option = FakeOption(combobox, control)
    monkeypatch.setattr(
        sys.modules[__name__], "expect", lambda target: FakeExpectation(target)
    )

    _choose_combobox_option(
        FakePage(option),  # type: ignore[arg-type]
        combobox,  # type: ignore[arg-type]
        option_name="junit-browser-review",
        settled_control=control,  # type: ignore[arg-type]
    )

    assert option.clicks == 2
    assert combobox.clicks == 2
    assert combobox.fills == [
        "junit-browser-review",
        "junit-browser-review",
    ]
    assert control.enabled is True


@pytest.fixture
def selectbox_page(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[Page]:
    if "browser" not in request.config.option.markexpr:
        pytest.skip("run explicitly with -m browser after installing Playwright Chromium")
    if os.name != "posix":
        pytest.skip("fixture server cleanup requires POSIX process groups")
    application = tmp_path / "selectbox_fixture.py"
    application.write_text(
        "import time\nimport streamlit as st\n"
        "st.session_state['runs'] = st.session_state.get('runs', 0) + 1\n"
        # Keep the constructed server run observable, like the larger workbench.
        "time.sleep(0.15)\n"
        "selected = st.selectbox('File scope decision', "
        "['outside_confirmed_criteria', 'within_confirmed_criteria'], index=None, "
        "format_func=lambda value: value.replace('_', ' ').title(), key='scope')\n"
        "st.text(f'SERVER_SELECTION={selected}')\n"
        "st.text(f'SERVER_RUN={st.session_state[\"runs\"]}')\n",
        encoding="utf-8",
    )
    port = _available_port()
    base_url = f"http://127.0.0.1:{port}"
    log_path = tmp_path / "server.log"
    environment = os.environ.copy()
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    fixture_home = tmp_path / "home"
    fixture_home.mkdir()
    environment["HOME"] = str(fixture_home)
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", str(application),
                "--server.address=127.0.0.1", f"--server.port={port}",
                "--server.headless=true", "--server.fileWatcherType=none",
            ],
            cwd=tmp_path, env=environment, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, text=True,
        )
    try:
        _wait_until_healthy(base_url, process, log_path)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                external_requests: list[str] = []
                context.route(
                    "**/*", lambda route: _route_loopback_only(route, external_requests)
                )
                page = context.new_page()
                page.goto(base_url, wait_until="domcontentloaded")
                expect(page.get_by_text("SERVER_SELECTION=None", exact=True)).to_be_visible()
                yield page
                assert external_requests == []
            finally:
                browser.close()
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)


@pytest.mark.parametrize("initial_state", ["query_only", "already_selected"])
def test_choose_combobox_option_requires_committed_selection(
    selectbox_page: Page, initial_state: str,
) -> None:
    page = selectbox_page
    combobox = page.get_by_role("combobox", name="File scope decision", exact=True)
    option_name = "Outside Confirmed Criteria"
    combobox.click()
    combobox.fill(option_name)
    option = page.get_by_role("option", name=option_name, exact=True)
    expect(option).to_have_attribute("aria-selected", "false")
    if initial_state == "already_selected":
        _run_and_wait_for_streamlit_rerun(page, option.click)
        expect(
            page.get_by_text("SERVER_SELECTION=outside_confirmed_criteria", exact=True)
        ).to_be_visible()
    else:
        expect(page.get_by_text("SERVER_SELECTION=None", exact=True)).to_be_visible()

    _choose_combobox_option(page, combobox, option_name=option_name)

    expect(combobox).to_have_value(option_name, timeout=1_000)
    expect(
        page.get_by_text("SERVER_SELECTION=outside_confirmed_criteria", exact=True)
    ).to_be_visible(timeout=1_000)
    expect(page.get_by_text("SERVER_RUN=2", exact=True)).to_be_visible()


def test_choose_combobox_option_recovers_after_constructed_dropdown_dismissal(
    selectbox_page: Page, monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = selectbox_page
    combobox = page.get_by_role("combobox", name="File scope decision", exact=True)
    original_fill = combobox.fill
    dismissed = False

    def fill_and_dismiss_once(value: str) -> None:
        nonlocal dismissed
        original_fill(value)
        if not dismissed:
            # A constructed loss of the popup, not the original CI race's cause.
            combobox.press("Escape")
            dismissed = True

    monkeypatch.setattr(combobox, "fill", fill_and_dismiss_once)

    _choose_combobox_option(page, combobox, option_name="Outside Confirmed Criteria")

    expect(
        page.get_by_text("SERVER_SELECTION=outside_confirmed_criteria", exact=True)
    ).to_be_visible()
    assert dismissed


def test_choose_combobox_option_rejects_an_unavailable_matching_query(
    selectbox_page: Page,
) -> None:
    page = selectbox_page
    combobox = page.get_by_role("combobox", name="File scope decision", exact=True)
    combobox.click()
    combobox.fill("Unavailable decision")

    with pytest.raises((AssertionError, PlaywrightTimeoutError)):
        _choose_combobox_option(page, combobox, option_name="Unavailable decision")

    expect(page.get_by_text("SERVER_SELECTION=None", exact=True)).to_be_visible()


def test_download_with_retry_reissues_click_after_missed_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeButton:
        def __init__(self) -> None:
            self.clicks = 0

        def click(self) -> None:
            self.clicks += 1

    class FakeDownload:
        suggested_filename = "review.md"

    class FakeDownloadEvent:
        def __init__(self, attempt: int) -> None:
            self.attempt = attempt
            self.value = FakeDownload()

        def __enter__(self) -> FakeDownloadEvent:
            return self

        def __exit__(self, *args: object) -> None:
            if self.attempt == 1:
                raise PlaywrightTimeoutError("download event was not observed")

    class FakePage:
        def __init__(self, button: FakeButton) -> None:
            self.button = button
            self.download_attempts = 0

        def get_by_role(self, *args: object, **kwargs: object) -> FakeButton:
            return self.button

        def expect_download(self, *, timeout: int) -> FakeDownloadEvent:
            self.download_attempts += 1
            return FakeDownloadEvent(self.download_attempts)

    class FakeExpectation:
        def to_be_visible(self, *, timeout: int | None = None) -> None:
            return None

        def to_be_enabled(self, *, timeout: int | None = None) -> None:
            return None

    button = FakeButton()
    page = FakePage(button)
    monkeypatch.setattr(
        sys.modules[__name__], "expect", lambda target: FakeExpectation()
    )

    download = _download_with_retry(
        page,  # type: ignore[arg-type]
        button_name="Download Markdown",
    )

    assert download.suggested_filename == "review.md"
    assert page.download_attempts == 2
    assert button.clicks == 2


@pytest.mark.parametrize("server_log_exists", [True, False])
def test_browser_failure_capture_preserves_original_error_and_collects_evidence(
    tmp_path: Path, request: pytest.FixtureRequest, server_log_exists: bool,
) -> None:
    if "browser" not in request.config.option.markexpr:
        pytest.skip("run explicitly with -m browser after installing Playwright Chromium")
    server_log = tmp_path / "server.log"
    if server_log_exists:
        server_log.write_text("constructed server diagnostic\n", encoding="utf-8")
    destination = tmp_path / "diagnostics"
    original = RuntimeError("constructed journey failure")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            with (
                pytest.raises(RuntimeError, match="constructed journey failure") as caught,
                _capture_browser_failure(page, destination, server_log),
            ):
                page.set_content('<h1>Constructed failure state</h1>')
                raise original
            assert caught.value is original
        finally:
            browser.close()

    assert (destination / "failure.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Constructed failure state" in (destination / "failure.aria.txt").read_text(
        encoding="utf-8"
    )
    with ZipFile(destination / "trace.zip") as trace:
        assert any(name.endswith(".trace") for name in trace.namelist())
    if server_log_exists:
        assert (destination / "server.log").read_text(encoding="utf-8") == (
            "constructed server diagnostic\n"
        )
    else:
        assert any("server.log" in note for note in original.__notes__)


def _exercise_primary_path(
    page: Page,
    base_url: str,
    *,
    verify_persistence_and_downloads: bool,
    capture_directory: Path | None = None,
) -> None:
    def capture(name: str) -> None:
        if capture_directory is not None:
            capture_directory.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(capture_directory / f"{name}.png"))

    page.goto(base_url, wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="ScopeProof", exact=True)).to_be_visible()

    load_demo = page.get_by_role(
        "button", name="Load deliberately constructed demo", exact=True
    )
    _activate_with_keyboard(
        page,
        load_demo,
        label="Load deliberately constructed demo",
        key="Space",
    )
    confirmer = page.get_by_label("Confirmed by", exact=True)
    _focus_with_keyboard(page, confirmer, label="Confirmed by")
    page.keyboard.type("Packaged browser reviewer")
    expect(confirmer).to_have_value("Packaged browser reviewer")
    capture("01-confirm-criteria")

    confirm = page.get_by_role(
        "button", name="Apply edits and confirm criteria", exact=True
    )
    _activate_with_keyboard(
        page,
        confirm,
        label="Apply edits and confirm criteria",
        key="Space",
    )
    expect(page.get_by_text("Criteria confirmed by the reviewer.", exact=True)).to_be_visible()
    capture("02-criteria-confirmed")

    run_analysis = page.get_by_role(
        "button", name="Run deterministic analysis", exact=True
    )
    _activate_with_keyboard(
        page,
        run_analysis,
        label="Run deterministic analysis",
        key="Space",
    )
    expect(page.get_by_role("heading", name="3 · Decision Progress", exact=True)).to_be_visible()
    expect(page.get_by_text("Missing evidence", exact=True).first).to_be_visible()
    expect(page.get_by_text("Review status: Action required", exact=True)).to_be_visible()
    expect(page.get_by_text("Evidence status:", exact=False).first).to_be_visible()
    expect(
        page.get_by_text("Import external JUnit results", exact=True)
    ).to_be_visible()
    export_controls = (
        ("Download Markdown", ".md"),
        ("Download JSON", ".json"),
        ("Download CSV", ".csv"),
    )
    for label, _suffix in export_controls:
        export = page.get_by_role("button", name=label, exact=True)
        expect(export).to_be_visible()
        expect(export).to_be_enabled()
    capture("03-decision-progress")

    page.get_by_text("Missing evidence", exact=True).first.scroll_into_view_if_needed()
    capture("04-partial-support")

    page.get_by_role("button", name="Download Markdown", exact=True).scroll_into_view_if_needed()
    capture("05-export-controls")

    if verify_persistence_and_downloads:
        save_notice = page.get_by_text("Review saved automatically. ID:", exact=False)
        expect(save_notice).to_be_visible()
        saved_id_match = re.search(
            r"Review saved automatically\. ID: ([A-Za-z0-9_-]+)\.",
            save_notice.inner_text(),
        )
        assert saved_id_match is not None
        saved_review_id = saved_id_match.group(1)

        download = _download_with_retry(page, button_name="Download Markdown")
        assert download.suggested_filename.endswith(".md")
        assert b"head-demo-002" in download.path().read_bytes()

        csv_download = _download_with_retry(page, button_name="Download CSV")
        assert csv_download.suggested_filename.endswith(".csv")
        csv_rows = list(csv.DictReader(io.StringIO(
            csv_download.path().read_text(encoding="utf-8")
        )))
        assert len(csv_rows) == 4
        for row in csv_rows:
            assert row["head_sha"] == "head-demo-002"
            assert row["review_status"] == "Action required"
            assert "blocking_criteria" in json.loads(row["gate_reason_codes"])
            assert json.loads(row["gate_blocking_criteria"]) == ["AC-02", "AC-03"]
            assert json.loads(row["gate_guidance"])

        page.get_by_text("Resume a saved review", exact=True).click()
        expect(page.get_by_text(re.compile(r"saved local reviews? found"))).to_be_visible()
        saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
        reopen = page.get_by_role("button", name="Reopen local review", exact=True)
        _choose_combobox_option(
            page,
            saved_review,
            option_name=saved_review_id,
            settled_control=reopen,
        )
        reopen.click()
        expect(
            page.get_by_text(
                "Review reopened from local storage after validation.", exact=True
            )
        ).to_be_visible()
        expect(
            page.get_by_role("button", name="Check current head", exact=True)
        ).to_be_visible()

    open_ac_02 = page.get_by_role(
        "button", name="Open AC-02 decision controls", exact=True
    )
    expect(open_ac_02).to_be_visible()
    open_ac_02.scroll_into_view_if_needed()
    capture("06-criterion-review-card")
    _activate_with_keyboard(
        page,
        open_ac_02,
        label="Open AC-02 decision controls",
        key="Enter",
    )
    criterion_selector = page.get_by_role(
        "combobox", name="Inspect criterion", exact=True
    )
    expect(criterion_selector).to_have_value("AC-02")
    decision_selector = page.get_by_role(
        "combobox", name="Human decision", exact=True
    )
    expect(decision_selector).to_be_visible()
    decision_before_matrix = decision_selector.locator(
        "xpath=following::h2[@id='5-evidence-matrix']"
    )
    expect(decision_before_matrix).to_have_count(1)

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.evaluate("document.body.scrollWidth <= window.innerWidth")


def _exercise_selection_completeness(page: Page, base_url: str) -> None:
    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page, saved_review, option_name="selection-browser-review", settled_control=reopen
    )
    reopen.click()
    expect(page.get_by_text(
        "8 of 12 candidates passing search filters shown; "
        "4 omitted during selection (limit: 8).", exact=True,
    )).to_be_visible()
    for label, report_format in (("Download CSV", "csv"), ("Download JSON", "json")):
        download = _download_with_retry(page, button_name=label)
        contents = download.path().read_text(encoding="utf-8")
        if report_format == "csv":
            row = next(csv.DictReader(io.StringIO(contents)))
            diagnostic = json.loads(row["retrieval_diagnostic"])
            assert row["head_sha"] == "a" * 40
            assert row["verdict"] == "needs_review"
        else:
            report = json.loads(contents)
            bundle = report.get("bundle", report)
            diagnostic = bundle["retrieval_diagnostics"][0]
            assert bundle["review"]["head_sha"] == "a" * 40
            assert len(bundle["evidence"]) == 8
        assert diagnostic["eligible_candidate_count"] == 12
        assert diagnostic["accepted_candidate_count"] == 8
        assert diagnostic["candidate_limit"] == 8
        assert diagnostic["omitted_candidate_count"] == 4


def _exercise_junit_import_round_trip(
    page: Page,
    base_url: str,
    *,
    artifact_path: Path,
    artifact_digest: str,
    capture_directory: Path | None = None,
) -> None:
    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page,
        saved_review,
        option_name="junit-browser-review",
        settled_control=reopen,
    )
    reopen.click()
    expect(
        page.get_by_text(
            "Review reopened from local storage after validation.", exact=True
        )
    ).to_be_visible()

    scope_path = page.get_by_role("combobox", name="Uncited changed file", exact=True)
    scope_save = page.get_by_role("button", name="Save file scope decision", exact=True)
    _choose_combobox_option(
        page, scope_path, option_name="src/unrelated.py",
    )
    disposition = page.get_by_role("combobox", name="File scope decision", exact=True)
    _choose_combobox_option(
        page, disposition, option_name="Outside Confirmed Criteria",
    )
    scope_note = page.get_by_label("File scope explanation (required)", exact=True)
    scope_note.fill(
        "Reviewed this constructed file against the confirmed criterion."
    )
    _run_and_wait_for_streamlit_rerun(page, lambda: scope_note.press("Tab"))
    expect(scope_path).to_have_value("src/unrelated.py")
    expect(disposition).to_have_value("Outside Confirmed Criteria")
    scope_reviewer = page.get_by_label("Decision reviewer (required)", exact=True)
    scope_reviewer.fill("Automated browser reviewer (constructed)")
    _run_and_wait_for_streamlit_rerun(page, lambda: scope_reviewer.press("Tab"))
    expect(scope_save).to_be_enabled()
    scope_save.click()
    expect(page.get_by_text("File scope decision history", exact=True)).to_be_visible()
    if capture_directory is not None:
        capture_directory.mkdir(parents=True, exist_ok=True)
        page.get_by_role("heading", name="Changed-file scope", exact=True).evaluate(
            "element => element.scrollIntoView({block: 'start'})"
        )
        page.screenshot(path=str(capture_directory / "07-file-scope-decision.png"))

    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page, saved_review, option_name="junit-browser-review", settled_control=reopen,
    )
    reopen.click()
    expect(page.get_by_text("File scope decision history", exact=True)).to_be_visible()

    junit_expander = page.get_by_text("Import external JUnit results", exact=True)
    junit_expander.click()
    artifact_input = page.get_by_label(
        "Local JUnit XML artifact", exact=True
    ).locator("input[type=file]")
    _run_and_wait_for_streamlit_rerun(
        page, lambda: artifact_input.set_input_files(artifact_path)
    )
    preview = page.get_by_text(
        "Computed results: 1 total · 1 passed · 0 failed · 0 errors · 0 skipped",
        exact=True,
    )
    expect(preview).to_have_count(1)
    if not preview.is_visible():
        junit_expander.click()
    expect(preview).to_be_visible()
    importer = page.get_by_label("Asserted JUnit importer (required)", exact=True)
    importer.fill("Packaged browser reviewer")
    _run_and_wait_for_streamlit_rerun(page, lambda: importer.press("Tab"))
    if not preview.is_visible():
        junit_expander.click()
    expect(preview).to_be_visible()
    mapping = page.get_by_role(
        "combobox", name="Map JUnit scopes to the selected criterion", exact=True
    )
    expect(mapping).to_be_enabled()
    _choose_multiselect_option(
        page,
        mapping,
        query="suite-0001",
        option_name="suite-0001 · suite · unit",
    )
    page.keyboard.press("Escape")
    expect(mapping.locator("xpath=../..")).to_contain_text(
        "suite-0001 · suite · unit"
    )
    expect(preview).to_have_count(1)
    if not preview.is_visible():
        junit_expander.click()
    expect(
        page.get_by_label("Asserted JUnit importer (required)", exact=True)
    ).to_have_value("Packaged browser reviewer")
    save = page.get_by_role(
        "button", name="Save imported JUnit results", exact=True
    )
    expect(save).to_be_enabled()
    expect(save).to_be_visible()
    _click_until_text_visible(
        page,
        button_name="Save imported JUnit results",
        outcome_text=(
            "Imported JUnit results appended as external non-gating context."
        ),
    )
    boundary = page.get_by_text(JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION, exact=True)
    if not boundary.is_visible():
        junit_expander.click()
    expect(boundary).to_be_visible()
    expect(page.get_by_text("Review saved automatically. ID:", exact=False)).to_be_visible()

    page.get_by_text("Resume a saved review", exact=True).click()
    saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page,
        saved_review,
        option_name="junit-browser-review",
        settled_control=reopen,
    )
    reopen.click()
    expect(
        page.get_by_text(
            "Review reopened from local storage after validation.", exact=True
        )
    ).to_be_visible()
    expect(
        page.get_by_text("Recorded imported JUnit results (1)", exact=True)
    ).to_be_visible()

    for label, suffix in (("Download Markdown", ".md"), ("Download JSON", ".json")):
        download = _download_with_retry(page, button_name=label)
        assert download.suggested_filename.endswith(suffix)
        downloaded_bytes = download.path().read_bytes()
        assert artifact_digest.encode() in downloaded_bytes
        assert b"RAW-JUNIT-OUTPUT-SENTINEL" not in downloaded_bytes
        assert b"FAILURE-BODY-SENTINEL" not in downloaded_bytes


def test_installed_wheel_primary_path_in_chromium(
    tmp_path: Path, request: pytest.FixtureRequest
) -> None:
    if "browser" not in request.config.option.markexpr:
        pytest.skip("run explicitly with -m browser after installing Playwright Chromium")
    if os.name != "posix":
        pytest.skip("process-group cleanup is verified only on POSIX in this regression")

    distribution_dir = tmp_path / "dist"
    environment_dir = tmp_path / "venv"
    runtime_dir = tmp_path / "runtime"
    home_dir = runtime_dir / "home"
    distribution_dir.mkdir()
    home_dir.mkdir(parents=True)

    if find_spec("pip") is not None:
        _run(
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--wheel-dir",
            str(distribution_dir),
            cwd=REPOSITORY_ROOT,
        )
    else:
        _run(
            "uv",
            "build",
            "--wheel",
            "--out-dir",
            str(distribution_dir),
            cwd=REPOSITORY_ROOT,
        )
    wheel = next(distribution_dir.glob("scopeproof-*.whl"))
    _run(sys.executable, "-m", "venv", str(environment_dir))
    environment_python = environment_dir / "bin" / "python"
    _run(
        str(environment_python),
        "-m",
        "pip",
        "install",
        str(wheel),
        f"playwright=={version('playwright')}",
    )
    _run(str(environment_python), "-c", "import playwright, scopeproof_core, streamlit")

    review_store_dir = home_dir / ".scopeproof" / "reviews"
    selection_snapshot_path = runtime_dir / "constructed-selection-snapshot.json"
    selection_snapshot_path.write_text(selection_snapshot().model_dump_json(), encoding="utf-8")
    selection_labels_path = runtime_dir / "constructed-selection-labels.json"
    selection_labels_path.write_text(json.dumps({
        "fixture": "constructed-candidate-selection",
        "deliberately_constructed_demo": True,
        "source_text": "Export CSV",
        "criteria": [item.model_dump(mode="json") for item in selection_criteria()],
        "criteria_confirmed": True,
        "resolutions": [],
    }), encoding="utf-8")
    _run(
        str(environment_python), "-c",
        (
            "from pathlib import Path; import sys; "
            "from scopeproof_core.demo import build_review_from_paths; "
            "from scopeproof_core.reviews.lifecycle import new_review_state; "
            "from scopeproof_core.storage.json_store import JsonReviewStore; "
            "import scopeproof_core; "
            "assert Path(scopeproof_core.__file__).resolve().is_relative_to("
            "Path(sys.prefix).resolve()); "
            "bundle=build_review_from_paths(Path(sys.argv[2]),Path(sys.argv[3])); "
            "bundle.review.review_id='selection-browser-review'; "
            "JsonReviewStore(Path(sys.argv[1])).save(new_review_state(bundle))"
        ),
        str(review_store_dir), str(selection_snapshot_path), str(selection_labels_path),
        cwd=runtime_dir,
    )
    _run(
        str(environment_python),
        "-c",
        (
            "from pathlib import Path; import sys; "
            "from scopeproof_core.demo import build_demo_review; "
            "from scopeproof_core.reviews.lifecycle import new_review_state; "
            "from scopeproof_core.schemas.models import ChangedFileScope, ReviewBundle; "
            "from scopeproof_core.gates.evaluator import evaluate_gate; "
            "from scopeproof_core.storage.json_store import JsonReviewStore; "
            "bundle=build_demo_review().model_copy(deep=True); "
            "bundle.review.review_id='junit-browser-review'; "
            "bundle.review.head_sha='a'*40; "
            "bundle.review.changed_file_inventory.head_sha=bundle.review.head_sha; "
            "bundle.review.changed_file_inventory.files.append("
            "ChangedFileScope(path='src/unrelated.py', status='modified')); "
            "bundle.criteria_revision_number=1; "
            "[(setattr(item, 'commit_sha', bundle.review.head_sha), "
            "setattr(item, 'permalink', item.permalink.replace('head-demo-002', "
            "bundle.review.head_sha))) for item in bundle.evidence]; "
            "bundle.gate=evaluate_gate(bundle.review,bundle.criteria,bundle.findings,"
            "bundle.resolutions,bundle.evidence); "
            "bundle=ReviewBundle.model_validate(bundle.model_dump(mode='python')); "
            "JsonReviewStore(Path(sys.argv[1])).save(new_review_state(bundle))"
        ),
        str(review_store_dir),
    )
    junit_artifact = runtime_dir / "junit-results.xml"
    junit_artifact_bytes = (
        b'<testsuite name="unit"><testcase name="test_browser_round_trip"/>'
        b"<system-out>RAW-JUNIT-OUTPUT-SENTINEL</system-out></testsuite>"
    )
    junit_artifact.write_bytes(junit_artifact_bytes)
    junit_artifact_digest = sha256(junit_artifact_bytes).hexdigest()

    port = _available_port()
    base_url = f"http://127.0.0.1:{port}"
    log_path = runtime_dir / "scopeproof-web.log"
    environment = os.environ.copy()
    environment["HOME"] = str(home_dir)
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                str(environment_dir / "bin" / "scopeproof-web"),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=runtime_dir,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )

    try:
        _wait_until_healthy(base_url, process, log_path)
        browser_errors: list[str] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                external_requests: list[str] = []
                for viewport_index, viewport in enumerate(VIEWPORTS):
                    context = browser.new_context(viewport=viewport)
                    context.route(
                        "**/*",
                        lambda route: _route_loopback_only(route, external_requests),
                    )
                    page = context.new_page()
                    page.on(
                        "console",
                        lambda message: (
                            browser_errors.append(f"console: {message.text}")
                            if message.type == "error"
                            else None
                        ),
                    )
                    page.on("pageerror", lambda error: browser_errors.append(f"page: {error}"))
                    page.on(
                        "websocket",
                        lambda websocket: (
                            external_requests.append(websocket.url)
                            if not _is_loopback_request(websocket.url)
                            else None
                        ),
                    )
                    diagnostics = Path(os.environ.get(
                        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics")
                    )) / f"viewport-{viewport_index}"
                    with _capture_browser_failure(page, diagnostics, log_path):
                        _exercise_primary_path(
                            page,
                            base_url,
                            verify_persistence_and_downloads=viewport_index == 1,
                            capture_directory=(
                                tmp_path / "captures"
                                if viewport_index == 0
                                and "SCOPEPROOF_PORTFOLIO_CAPTURE_DIR" in os.environ
                                else None
                            ),
                        )
                        if viewport_index == 0:
                            _exercise_selection_completeness(page, base_url)
                            _exercise_junit_import_round_trip(
                                page,
                                base_url,
                                artifact_path=junit_artifact,
                                artifact_digest=junit_artifact_digest,
                                capture_directory=(
                                    tmp_path / "captures"
                                    if "SCOPEPROOF_PORTFOLIO_CAPTURE_DIR" in os.environ
                                    else None
                                ),
                            )
                    context.close()
            finally:
                browser.close()
        assert browser_errors == []
        assert external_requests == []
        if "SCOPEPROOF_PORTFOLIO_CAPTURE_DIR" in os.environ:
            expected_captures = (
                "01-confirm-criteria.png",
                "02-criteria-confirmed.png",
                "03-decision-progress.png",
                "04-partial-support.png",
                "05-export-controls.png",
                "06-criterion-review-card.png",
                "07-file-scope-decision.png",
            )
            destination = Path(os.environ["SCOPEPROOF_PORTFOLIO_CAPTURE_DIR"])
            captures = tmp_path / "captures"
            assert all((captures / name).is_file() for name in expected_captures)
            destination.mkdir(parents=True, exist_ok=True)
            for name in expected_captures:
                shutil.copy2(captures / name, destination / name)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        assert process.poll() is not None
