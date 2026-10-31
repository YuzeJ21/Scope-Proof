from __future__ import annotations

import csv
import html
import io
import json
import os
import re
import shutil
import signal
import socket
import string
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

from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.importers.junit import MAX_JUNIT_BYTES
from scopeproof_core.reviews.comparison import ReviewComparison
from scopeproof_core.schemas.models import (
    JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION,
    ChangedFile,
    ChangedLine,
    LineChangeType,
)
from tests.candidate_selection_fixture import selection_criteria, selection_snapshot
from tests.historical_analysis_fixture import (
    HISTORICAL_HEAD,
    HISTORICAL_PRODUCER_VERSION,
    HISTORICAL_REVIEW_ID,
    HISTORICAL_UNTRUSTED_TEXT,
    PENDING_CRITERIA_TEXT,
)
from tests.saved_comparison_fixture import (
    CURRENT_HEAD,
    CURRENT_REVIEW_ID,
    FOREIGN_HISTORY_HEAD,
    HISTORY_HEAD,
    PREVIOUS_HEAD,
    PREVIOUS_REVIEW_ID,
)

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
    selected_chip = selected_values.get_by_text(option_name, exact=True)
    for attempt in range(3):
        if selected_chip.count():
            return
        try:
            if combobox.get_attribute("aria-expanded") != "true":
                combobox.press("ArrowDown")
            combobox.fill(query)
            if combobox.get_attribute("aria-expanded") != "true":
                combobox.press("ArrowDown")
                combobox.fill(query)
            option = page.get_by_role("option", name=option_name, exact=True)
            option.wait_for(state="visible", timeout=5_000)
        except PlaywrightTimeoutError:
            if attempt == 2 or (
                combobox.get_attribute("aria-expanded") == "true"
                and combobox.input_value() == query
            ):
                raise
            continue
        if option.get_attribute("aria-selected") == "true":
            expect(selected_chip).to_be_visible(timeout=5_000)
            return
        _run_and_wait_for_streamlit_rerun(
            page, lambda selected_option=option: selected_option.click(timeout=5_000)
        )
        expect(selected_chip).to_be_visible(timeout=5_000)
        return


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
        "st.text(f'SERVER_RUN={st.session_state[\"runs\"]}')\n"
        "st.text_input('Constructed focus target', key='focus_target')\n"
        "mapping = st.multiselect('Map JUnit scopes to the selected criterion', "
        "['suite-0001 · suite · unit', 'suite-0001 · suite · unit extra'], "
        "key='mapping')\n"
        "st.text(f'SERVER_MAPPING={mapping}')\n",
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


def test_choose_multiselect_option_recovers_from_constructed_popup_loss(
    selectbox_page: Page, monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = selectbox_page
    page.set_default_timeout(2_000)
    combobox = page.get_by_role(
        "combobox", name="Map JUnit scopes to the selected criterion", exact=True,
    )
    original_fill = combobox.fill
    lost_popup = False

    def fill_and_lose_popup_once(value: str) -> None:
        nonlocal lost_popup
        original_fill(value)
        if not lost_popup:
            combobox.press("Escape")
            if combobox.get_attribute("aria-expanded") == "true":
                combobox.press("Escape")
            page.get_by_role("textbox", name="Constructed focus target", exact=True).click()
            expect(combobox).to_have_attribute("aria-expanded", "false")
            expect(page.get_by_text("SERVER_MAPPING=[]", exact=True)).to_be_visible()
            expect(page.get_by_text("SERVER_RUN=2", exact=True)).to_be_visible()
            lost_popup = True

    monkeypatch.setattr(combobox, "fill", fill_and_lose_popup_once)
    option_name = "suite-0001 · suite · unit"

    _choose_multiselect_option(page, combobox, query="suite-0001", option_name=option_name)
    _choose_multiselect_option(page, combobox, query="suite-0001", option_name=option_name)

    assert lost_popup
    expect(page.get_by_text(f"SERVER_MAPPING={[option_name]}", exact=True)).to_be_visible()
    expect(page.get_by_text("SERVER_RUN=3", exact=True)).to_be_visible()


def test_choose_multiselect_option_preserves_an_open_popup_and_commits_once(
    selectbox_page: Page,
) -> None:
    page = selectbox_page
    page.set_default_timeout(2_000)
    combobox = page.get_by_role(
        "combobox", name="Map JUnit scopes to the selected criterion", exact=True,
    )
    option_name = "suite-0001 · suite · unit"
    combobox.press("ArrowDown")
    combobox.fill("suite-0001")
    expect(combobox).to_have_attribute("aria-expanded", "true")

    _choose_multiselect_option(page, combobox, query="suite-0001", option_name=option_name)
    _choose_multiselect_option(page, combobox, query="suite-0001", option_name=option_name)

    expect(page.get_by_text(f"SERVER_MAPPING={[option_name]}", exact=True)).to_be_visible()
    expect(page.get_by_text("SERVER_RUN=2", exact=True)).to_be_visible()


def test_choose_multiselect_option_distinguishes_selected_prefix_and_preserves_exact_choice(
    selectbox_page: Page,
) -> None:
    page = selectbox_page
    page.set_default_timeout(2_000)
    combobox = page.get_by_role(
        "combobox", name="Map JUnit scopes to the selected criterion", exact=True,
    )
    option_name = "suite-0001 · suite · unit"
    distractor = f"{option_name} extra"
    combobox.press("ArrowDown")
    combobox.fill("unit extra")
    _run_and_wait_for_streamlit_rerun(
        page, page.get_by_role("option", name=distractor, exact=True).click,
    )
    expect(page.get_by_text(f"SERVER_MAPPING={[distractor]}", exact=True)).to_be_visible()

    _choose_multiselect_option(page, combobox, query="suite-0001", option_name=option_name)
    _choose_multiselect_option(page, combobox, query="suite-0001", option_name=option_name)

    expect(page.get_by_text(
        f"SERVER_MAPPING={[distractor, option_name]}", exact=True,
    )).to_be_visible()
    expect(page.get_by_text("SERVER_RUN=3", exact=True)).to_be_visible()


def test_choose_multiselect_option_rejects_an_unavailable_option_without_selection(
    selectbox_page: Page,
) -> None:
    page = selectbox_page
    page.set_default_timeout(2_000)
    combobox = page.get_by_role(
        "combobox", name="Map JUnit scopes to the selected criterion", exact=True,
    )

    with pytest.raises((AssertionError, PlaywrightTimeoutError)):
        _choose_multiselect_option(
            page, combobox, query="unavailable", option_name="unavailable",
        )

    expect(page.get_by_text("SERVER_MAPPING=[]", exact=True)).to_be_visible()
    expect(page.get_by_text("SERVER_RUN=1", exact=True)).to_be_visible()


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


def _exercise_junit_upload_byte_boundary(page: Page, artifact_directory: Path) -> None:
    """The frontend allowance must let the exact core limit reach bounded inspection."""
    page.get_by_text("Import external JUnit results", exact=True).click()
    uploader = page.get_by_label("Local JUnit XML artifact", exact=True).locator("input[type=file]")
    xml = b'<testsuite name="boundary"><testcase name="exact-one-mib"/></testsuite>'
    payload = xml + b" " * (MAX_JUNIT_BYTES - len(xml))
    exact = artifact_directory / "exact-one-mib.xml"
    exact.write_bytes(payload)
    _run_and_wait_for_streamlit_rerun(page, lambda: uploader.set_input_files(exact))
    preview = page.get_by_text("Sanitized JUnit preview", exact=True)
    if not preview.is_visible():
        page.get_by_text("Import external JUnit results", exact=True).click()
    expect(preview).to_be_visible()
    expect(page.get_by_text(
        "Computed results: 1 total · 1 passed · 0 failed · 0 errors · 0 skipped", exact=True
    )).to_be_visible()

    oversized = artifact_directory / "one-byte-over.xml"
    oversized.write_bytes(payload + b" ")
    _run_and_wait_for_streamlit_rerun(page, lambda: uploader.set_input_files(oversized))
    rejection = page.get_by_text(
        "JUnit artifact could not be inspected. It exceeds the local "
        "import byte limit and remains unsaved.", exact=True
    )
    if not rejection.is_visible():
        page.get_by_text("Import external JUnit results", exact=True).click()
    expect(rejection).to_be_visible()
    expect(page.get_by_text("Sanitized JUnit preview", exact=True)).to_have_count(0)
    expect(page.get_by_role(
        "button", name="Save imported JUnit results", exact=True
    )).to_be_disabled()
    expect(page.get_by_text("Recorded imported JUnit results (1)", exact=True)).to_be_visible()


@pytest.fixture(scope="module")
def installed_wheel(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest,
) -> Path:
    """Build and install once while keeping each browser journey's records isolated."""
    if "browser" not in request.config.option.markexpr:
        pytest.skip("run explicitly with -m browser after installing Playwright Chromium")
    if os.name != "posix":
        pytest.skip("process-group cleanup is verified only on POSIX in this regression")

    installation_dir = tmp_path_factory.mktemp("installed-workbench")
    distribution_dir = installation_dir / "dist"
    environment_dir = installation_dir / "venv"
    distribution_dir.mkdir()

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
    _run(
        str(environment_python), "-I", "-c",
        "from pathlib import Path; import sys; "
        "import apps, playwright, scopeproof_core, streamlit; "
        "assert all(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()) "
        "for module in (apps, scopeproof_core))",
        cwd=installation_dir,
    )
    return environment_dir


@contextmanager
def _installed_workbench_server(
    environment_dir: Path, runtime_dir: Path, home_dir: Path, *, log_name: str,
    constructed_snapshot: Path | None = None,
) -> Iterator[tuple[str, Path]]:
    port = _available_port()
    base_url = f"http://127.0.0.1:{port}"
    log_path = runtime_dir / log_name
    environment = os.environ.copy()
    environment["HOME"] = str(home_dir)
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    environment.pop("PYTHONPATH", None)
    command = [
        str(environment_dir / "bin" / "scopeproof-web"),
        "--host", "127.0.0.1", "--port", str(port),
    ]
    if constructed_snapshot is not None:
        # Inject validated constructed data without editing installed modules or
        # executing any source text carried by that data. Other journeys exercise
        # the ordinary installed CLI launcher.
        bootstrap = runtime_dir / "constructed-reference-bootstrap.py"
        bootstrap.write_text(
            "from pathlib import Path\nimport runpy\nimport sys\n"
            "import apps\nimport scopeproof_core\nimport scopeproof_core.demo as demo\n"
            "from scopeproof_core.schemas.models import PullRequestSnapshot\n"
            "assert all(Path(module.__file__).resolve().is_relative_to("
            "Path(sys.prefix).resolve()) for module in (apps, scopeproof_core))\n"
            f"fixture = Path({str(constructed_snapshot)!r})\n"
            "def constructed_snapshot():\n"
            "    return PullRequestSnapshot.model_validate_json(fixture.read_text())\n"
            "demo.load_demo_snapshot = constructed_snapshot\n"
            "runpy.run_module('apps.web.app', run_name='__main__')\n",
            encoding="utf-8",
        )
        command = [
            str(environment_dir / "bin" / "python"), "-I", "-m", "streamlit", "run",
            str(bootstrap), "--server.headless=true", "--server.address=127.0.0.1",
            f"--server.port={port}",
        ]
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=runtime_dir, env=environment, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, text=True,
        )
    try:
        _wait_until_healthy(base_url, process, log_path)
        yield base_url, log_path
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        assert process.poll() is not None


def test_installed_wheel_primary_path_in_chromium(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    environment_dir = installed_wheel
    environment_python = environment_dir / "bin" / "python"
    runtime_dir = tmp_path / "runtime"
    home_dir = runtime_dir / "home"
    home_dir.mkdir(parents=True)

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
        cwd=runtime_dir,
    )
    junit_artifact = runtime_dir / "junit-results.xml"
    junit_artifact_bytes = (
        b'<testsuite name="unit"><testcase name="test_browser_round_trip"/>'
        b"<system-out>RAW-JUNIT-OUTPUT-SENTINEL</system-out></testsuite>"
    )
    junit_artifact.write_bytes(junit_artifact_bytes)
    junit_artifact_digest = sha256(junit_artifact_bytes).hexdigest()

    with _installed_workbench_server(
        environment_dir, runtime_dir, home_dir, log_name="scopeproof-web.log",
    ) as (base_url, log_path):
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
                            _exercise_junit_upload_byte_boundary(page, runtime_dir)
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


def _download_review_state(page: Page) -> dict:
    download = _download_with_retry(page, button_name="Download JSON")
    return json.loads(download.path().read_text(encoding="utf-8"))


def _assert_selected_reference_is_nongating(
    before: dict,
    after: dict,
    *,
    expected_count: int = 1,
) -> dict:
    before_bundle = dict(before["bundle"])
    after_bundle = dict(after["bundle"])
    assert before_bundle.pop("reviewer_selected_references", []) == []
    references = after_bundle.pop("reviewer_selected_references")
    assert len(references) == expected_count
    assert after_bundle.pop("active_reviewer_selected_reference_ids") == [
        r["reference_id"] for r in references
    ]
    assert before_bundle.pop("active_reviewer_selected_reference_ids") == []
    assert after_bundle == before_bundle
    assert {key: value for key, value in after.items() if key != "bundle"} == {
        key: value for key, value in before.items() if key != "bundle"
    }
    assert after["resolution_events"] == []
    assert after_bundle["resolutions"] == []
    assert after_bundle["runtime_evidence"] == []
    assert after_bundle["review"]["final_acceptance"] is False
    return references[0]


def test_installed_wheel_selected_reference_survives_restart_without_gate_change(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    """Constructed late-page references can resume after restart without new analysis."""
    runtime_dir = tmp_path / "selected-reference-runtime"
    home_dir = runtime_dir / "home"
    home_dir.mkdir(parents=True)
    captures = runtime_dir / "captures"
    captures.mkdir()
    snapshot = load_demo_snapshot().model_copy(deep=True)
    target_path = "tests/test_late_reference.py"
    target_excerpt = "def test_constructed_late_reference():"
    for path in ("aaa/prefix.py", target_path):
        snapshot.files.append(ChangedFile(
            path=path, status="added",
            lines=[
                ChangedLine(
                    change_type=LineChangeType.ADDED, line_number=number,
                    content=(
                        target_excerpt if path == target_path and number == 1002
                        else f"constructed_value_{number} = {number}"
                    ),
                )
                for number in range(1, 1003)
            ],
        ))
    fixture = runtime_dir / "constructed-reference-snapshot.json"
    fixture.write_text(snapshot.model_dump_json(), encoding="utf-8")
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / "selected-reference"
    reviewer = "Constructed automated reference reviewer"
    rationale = "Constructed static definition selected for inspection; no execution observed."
    resumed_reviewer = "Constructed resumed reference reviewer"
    resumed_rationale = "Constructed resumed static context; no new analysis or execution."
    external_requests: list[str] = []
    browser_errors: list[str] = []
    before: dict | None = None
    selected_state: dict | None = None

    with sync_playwright() as playwright:
        for generation in range(2):
            with _installed_workbench_server(
                installed_wheel, runtime_dir, home_dir,
                log_name=f"selected-reference-{generation}.log",
                constructed_snapshot=fixture,
            ) as (base_url, log_path):
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(viewport=VIEWPORTS[generation])
                    context.route(
                        "**/*", lambda route: _route_loopback_only(route, external_requests),
                    )
                    page = context.new_page()
                    page.on("console", lambda message: (
                        browser_errors.append(f"console: {message.text}")
                        if message.type == "error" else None
                    ))
                    page.on("pageerror", lambda error: browser_errors.append(f"page: {error}"))
                    page.on("websocket", lambda websocket: (
                        external_requests.append(websocket.url)
                        if not _is_loopback_request(websocket.url) else None
                    ))
                    with _capture_browser_failure(
                        page, diagnostics / f"generation-{generation}", log_path,
                    ):
                        page.goto(base_url, wait_until="domcontentloaded")
                        if generation == 0:
                            page.get_by_role(
                                "button", name="Load deliberately constructed demo", exact=True,
                            ).click()
                            confirmer = page.get_by_label("Confirmed by", exact=True)
                            confirmer.fill("Constructed automated criteria confirmer")
                            _run_and_wait_for_streamlit_rerun(
                                page, lambda control=confirmer: control.press("Tab"),
                            )
                            page.get_by_role(
                                "button", name="Apply edits and confirm criteria", exact=True,
                            ).click()
                            expect(page.get_by_text(
                                "Criteria confirmed by the reviewer.", exact=True,
                            )).to_be_visible()
                            page.get_by_role(
                                "button", name="Run deterministic analysis", exact=True,
                            ).click()
                            expect(page.get_by_role(
                                "heading", name="4 · Criterion Review", exact=True,
                            )).to_be_visible()
                            before = _download_review_state(page)
                            assert before["bundle"]["review"]["head_sha"] == "head-demo-002"
                            finding = next(
                                item for item in before["bundle"]["findings"]
                                if item["criterion_id"] == "AC-03"
                            )
                            assert finding["evidence_ids"] == []
                            assert not any(
                                item["criterion_id"] == "AC-03"
                                and item["file_path"] == target_path
                                and item["line_start"] <= 1002 <= item["line_end"]
                                for item in before["bundle"]["evidence"]
                            )
                            criterion = page.get_by_role(
                                "combobox", name="Inspect criterion", exact=True,
                            )
                            _choose_combobox_option(page, criterion, option_name="AC-03")
                            selector = page.get_by_text("Select a source reference", exact=True)
                            expect(selector).to_be_visible()
                            selector.click()
                            source = page.get_by_role(
                                "combobox", name="Reference source", exact=True,
                            )
                            _choose_combobox_option(
                                page, source, option_name=f"Changed file · {target_path}",
                            )
                            reference_page = page.get_by_role(
                                "combobox", name="Reference page", exact=True,
                            )
                            expect(reference_page).to_have_value("Page 1 of 11")
                            _choose_combobox_option(
                                page, reference_page, option_name="Page 11 of 11",
                            )
                            line = page.get_by_role(
                                "combobox", name="Reference line", exact=True,
                            )
                            expect(line).to_have_value("")
                            _choose_combobox_option(page, line, option_name="1002")
                            save = page.get_by_role(
                                "button", name="Save selected reference", exact=True,
                            )
                            expect(save).to_be_disabled()
                            note = page.get_by_label("Why this reference matters", exact=True)
                            note.fill(rationale)
                            _run_and_wait_for_streamlit_rerun(
                                page, lambda control=note: control.press("Tab"),
                            )
                            expect(save).to_be_disabled()
                            author = page.get_by_label("Reference reviewer (required)", exact=True)
                            author.fill(reviewer)
                            _run_and_wait_for_streamlit_rerun(
                                page, lambda control=author: control.press("Tab"),
                            )
                            for label in ("Download JSON", "Download Markdown", "Download CSV"):
                                expect(page.get_by_role(
                                    "button", name=label, exact=True,
                                )).to_be_disabled()
                            expect(save).to_be_enabled()
                            source.scroll_into_view_if_needed()
                            page.screenshot(path=str(captures / "01-explicit-source-selection.png"))
                            _run_and_wait_for_streamlit_rerun(page, save.click)
                            expect(page.get_by_text(
                                f"Selected reference · {target_path}:1002 · Active", exact=True,
                            )).to_be_visible()
                            page.wait_for_function(STREAMLIT_RERUN_FINISHED_SCRIPT, timeout=10_000)
                            authoritative_json = page.get_by_role(
                                "button", name="Download JSON", exact=True,
                            )
                            expect(authoritative_json).to_have_count(1)
                            expect(authoritative_json).to_be_enabled()
                            selected_state = _download_review_state(page)
                            reference = _assert_selected_reference_is_nongating(
                                before, selected_state,
                            )
                            assert reference["criterion_id"] == "AC-03"
                            assert reference["head_sha"] == "head-demo-002"
                            assert reference["review_id"] == before["review"]["review_id"]
                            assert reference["criteria_revision_number"] == 1
                            assert reference["file_path"] == target_path
                            assert reference["line_number"] == 1002
                            assert reference["excerpt"] == target_excerpt
                            assert reference["evidence_type"] == "test"
                            assert reference["evidence_level"] == "E2"
                            assert reference["reviewer"] == reviewer
                            assert reference["rationale"] == rationale
                            assert reference["source_scope"] == "changed_file"
                            assert reference["repository"] == before["review"]["repository"]
                            assert reference["pr_number"] == before["review"]["pr_number"]
                            assert reference["criteria_source_provenance"] == (
                                before["review"]["criteria_source_provenance"]
                            )
                            assert reference["confirmed_criteria_sha256"] == (
                                before["review"]["criteria_source_provenance"][
                                    "normalized_criteria_sha256"
                                ]
                            )
                            assert reference["excerpt_sha256"] == sha256(
                                reference["excerpt"].encode("utf-8")
                            ).hexdigest()
                            assert reference["permalink"] == (
                                "https://github.com/scopeproof/demo-stock-research/blob/"
                                "head-demo-002/tests/test_late_reference.py#L1002-L1002"
                            )
                        else:
                            assert before is not None and selected_state is not None
                            page.get_by_text("Resume a saved review", exact=True).click()
                            saved_review = page.get_by_role(
                                "combobox", name="Saved review ID", exact=True,
                            )
                            reopen = page.get_by_role(
                                "button", name="Reopen local review", exact=True,
                            )
                            _choose_combobox_option(
                                page, saved_review,
                                option_name=selected_state["review"]["review_id"],
                                settled_control=reopen,
                            )
                            reopen.click()
                            expect(page.get_by_text(
                                "Review reopened from local storage after validation.", exact=True,
                            )).to_be_visible()
                            criterion = page.get_by_role(
                                "combobox", name="Inspect criterion", exact=True,
                            )
                            _choose_combobox_option(page, criterion, option_name="AC-03")
                            expect(page.get_by_text(
                                "Reviewer-selected references", exact=True,
                            )).to_be_visible()
                            page.get_by_text(
                                f"Selected reference · {target_path}:1002 · Active", exact=True,
                            ).click()
                            expect(page.get_by_text(reviewer, exact=True)).to_be_visible()
                            expect(page.get_by_text(rationale, exact=True)).to_be_visible()
                            page.get_by_text(reviewer, exact=True).scroll_into_view_if_needed()
                            page.screenshot(path=str(captures / "02-reference-after-restart.png"))
                            page.get_by_text("Select a source reference", exact=True).click()
                            expect(page.get_by_text(
                                "Load matching source before adding or correcting a reference. "
                                "Saved references remain available for withdrawal.", exact=True,
                            )).to_be_visible()
                            expect(page.get_by_role(
                                "button", name="Save selected reference", exact=True,
                            )).to_have_count(0)
                            reopened = _download_review_state(page)
                            assert reopened == selected_state
                            _assert_selected_reference_is_nongating(before, reopened)
                            page.get_by_role(
                                "button", name="Load matching reviewed source", exact=True,
                            ).click()
                            expect(page.get_by_text(
                                "Matching reviewed source loaded. "
                                "Saved analysis and decisions were preserved.", exact=True,
                            )).to_be_visible()
                            assert _download_review_state(page) == selected_state
                            selector = page.get_by_text("Select a source reference", exact=True)
                            source = page.get_by_role(
                                "combobox", name="Reference source", exact=True,
                            )
                            if not source.is_visible():
                                selector.click()
                            _choose_combobox_option(
                                page, source, option_name=f"Changed file · {target_path}",
                            )
                            reference_page = page.get_by_role(
                                "combobox", name="Reference page", exact=True,
                            )
                            _choose_combobox_option(
                                page, reference_page, option_name="Page 11 of 11",
                            )
                            line = page.get_by_role(
                                "combobox", name="Reference line", exact=True,
                            )
                            _choose_combobox_option(page, line, option_name="1001")
                            note = page.get_by_label("Why this reference matters", exact=True)
                            note.fill(resumed_rationale)
                            _run_and_wait_for_streamlit_rerun(
                                page, lambda control=note: control.press("Tab"),
                            )
                            author = page.get_by_label("Reference reviewer (required)", exact=True)
                            author.fill(resumed_reviewer)
                            _run_and_wait_for_streamlit_rerun(
                                page, lambda control=author: control.press("Tab"),
                            )
                            save = page.get_by_role(
                                "button", name="Save selected reference", exact=True,
                            )
                            expect(save).to_be_enabled()
                            _run_and_wait_for_streamlit_rerun(page, save.click)
                            expect(page.get_by_text(
                                f"Selected reference · {target_path}:1001 · Active", exact=True,
                            )).to_be_visible()
                            reopened = _download_review_state(page)
                            original_reference = _assert_selected_reference_is_nongating(
                                before, reopened, expected_count=2,
                            )
                            assert original_reference == (
                                selected_state["bundle"]["reviewer_selected_references"][0]
                            )
                            resumed_reference = (
                                reopened["bundle"]["reviewer_selected_references"][1]
                            )
                            assert resumed_reference["criterion_id"] == "AC-03"
                            assert resumed_reference["line_number"] == 1001
                            assert resumed_reference["file_path"] == target_path
                            assert resumed_reference["excerpt"] == "constructed_value_1001 = 1001"
                            assert resumed_reference["reviewer"] == resumed_reviewer
                            assert resumed_reference["rationale"] == resumed_rationale
                            assert resumed_reference["evidence_type"] == "test"
                            assert resumed_reference["evidence_level"] == "E2"
                            probe = subprocess.run(
                                [
                                    str(installed_wheel / "bin" / "python"), "-I", "-c",
                                    "import sys; from pathlib import Path; "
                                    "from scopeproof_core.storage.json_store "
                                    "import JsonReviewStore; "
                                    "print(JsonReviewStore(Path(sys.argv[1]))"
                                    ".load(sys.argv[2]).model_dump_json())",
                                    str(home_dir / ".scopeproof" / "reviews"),
                                    reopened["review"]["review_id"],
                                ],
                                cwd=runtime_dir, check=True, capture_output=True, text=True,
                            )
                            assert json.loads(probe.stdout) == reopened
                            markdown = _download_with_retry(page, button_name="Download Markdown")
                            report = markdown.path().read_text(encoding="utf-8")
                            report = re.sub(r"\\([^\w\s])", r"\1", report)
                            for expected in (
                                "AC-03", "head-demo-002", reviewer, rationale,
                                "test_late_reference.py", "1002", target_excerpt, "E2",
                                resumed_reviewer, resumed_rationale, "1001",
                                "constructed_value_1001 = 1001",
                            ):
                                assert expected in report
                            assert "non-gating static context" in report
                            assert re.search(
                                r"test/eval definitions.{0,60}not (?:execution|executed)",
                                report, re.IGNORECASE,
                            )
                            csv_download = _download_with_retry(page, button_name="Download CSV")
                            rows = list(csv.DictReader(io.StringIO(
                                csv_download.path().read_text(encoding="utf-8")
                            )))
                            assert len(rows) == len(before["bundle"]["criteria"])
                            for row in rows:
                                references = json.loads(row["reviewer_selected_references"])
                                expected = (
                                    reopened["bundle"]["reviewer_selected_references"]
                                    if row["criterion_id"] == "AC-03" else []
                                )
                                assert references == expected
                            audited = _exercise_reference_audit_actions(page, base_url, reopened)
                            for viewport in VIEWPORTS:
                                page.set_viewport_size(viewport)
                                assert page.evaluate(
                                    "document.documentElement.scrollWidth <= window.innerWidth"
                                )
                            audit_probe = subprocess.run(
                                [
                                    str(installed_wheel / "bin" / "python"),
                                    "-I",
                                    "-c",
                                    "import sys; from pathlib import Path; "
                                    "from scopeproof_core.storage.json_store "
                                    "import JsonReviewStore; "
                                    "print(JsonReviewStore(Path(sys.argv[1]))"
                                    ".load(sys.argv[2]).model_dump_json())",
                                    str(home_dir / ".scopeproof" / "reviews"),
                                    audited["review"]["review_id"],
                                ],
                                cwd=runtime_dir,
                                check=True,
                                capture_output=True,
                                text=True,
                            )
                            assert json.loads(audit_probe.stdout) == audited
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= window.innerWidth"
                        )
                    context.close()
                finally:
                    browser.close()
    assert external_requests == []
    assert browser_errors == []


def _exercise_reference_audit_actions(page: Page, base_url: str, saved: dict) -> dict:
    """Constructed actor corrects an original, restarts UI and withdraws without source."""
    original = saved["bundle"]["reviewer_selected_references"][0]
    action = page.get_by_role("combobox", name="Selected-reference action", exact=True)
    if not action.is_visible():
        page.get_by_text("Select a source reference", exact=True).click()
    _choose_combobox_option(page, action, option_name="Correct")
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Active reference to change", exact=True),
        option_name=f"{original['file_path']}:{original['line_number']} · "
        f"{original['reference_id']}",
    )
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Reference source", exact=True),
        option_name=f"Changed file · {original['file_path']}",
    )
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Reference page", exact=True),
        option_name="Page 11 of 11",
    )
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Reference line", exact=True),
        option_name=str(original["line_number"]),
    )
    actor = "Constructed browser audit actor"
    correction_reason = "Constructed correction preserves the original rationale."
    correction_rationale = "Corrected constructed static context for this line."
    for label, value in (
        ("Reference reviewer (required)", actor),
        ("Why this reference matters", correction_rationale),
        ("Reason for reference action (required)", correction_reason),
    ):
        control = page.get_by_label(label, exact=True)
        control.fill(value)
        _run_and_wait_for_streamlit_rerun(page, lambda field=control: field.press("Tab"))
    save = page.get_by_role("button", name="Save selected reference", exact=True)
    expect(save).to_be_enabled()
    _run_and_wait_for_streamlit_rerun(page, save.click)
    corrected = _download_review_state(page)
    refs = corrected["bundle"]["reviewer_selected_references"]
    assert refs[:2] == saved["bundle"]["reviewer_selected_references"]
    replacement = refs[-1]
    assert replacement["rationale"] == correction_rationale
    assert (
        corrected["bundle"]["selected_reference_events"][0]["reference_id"]
        == original["reference_id"]
    )
    assert corrected["bundle"]["active_reviewer_selected_reference_ids"] == [
        refs[1]["reference_id"],
        replacement["reference_id"],
    ]
    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Saved review ID", exact=True),
        option_name=saved["review"]["review_id"],
        settled_control=reopen,
    )
    reopen.click()
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Inspect criterion", exact=True),
        option_name="AC-03",
    )
    page.get_by_text("Select a source reference", exact=True).click()
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Selected-reference action", exact=True),
        option_name="Withdraw",
    )
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Active reference to change", exact=True),
        option_name=f"{replacement['file_path']}:{replacement['line_number']} · "
        f"{replacement['reference_id']}",
    )
    expect(page.get_by_role("combobox", name="Reference source", exact=True)).to_have_count(0)
    withdrawal_reason = "Constructed withdrawal after reopen without source."
    for label, value in (
        ("Reference reviewer (required)", actor),
        ("Reason for reference action (required)", withdrawal_reason),
    ):
        control = page.get_by_label(label, exact=True)
        control.fill(value)
        _run_and_wait_for_streamlit_rerun(page, lambda field=control: field.press("Tab"))
    expect(save).to_be_enabled()
    _run_and_wait_for_streamlit_rerun(page, save.click)
    audited = _download_review_state(page)
    assert audited["bundle"]["reviewer_selected_references"] == refs
    assert audited["bundle"]["active_reviewer_selected_reference_ids"] == [refs[1]["reference_id"]]
    assert len(audited["bundle"]["selected_reference_events"]) == 2
    before, after = dict(saved["bundle"]), dict(audited["bundle"])
    for payload in (before, after):
        for key in (
            "reviewer_selected_references",
            "selected_reference_events",
            "active_reviewer_selected_reference_ids",
        ):
            payload.pop(key)
    assert before == after
    for key in saved.keys() - {"bundle"}:
        assert saved[key] == audited[key]
    markdown = _download_with_retry(page, button_name="Download Markdown")
    text = markdown.path().read_text(encoding="utf-8")
    assert "Corrected" in text and "Withdrawn" in text
    for value in (actor, correction_reason, withdrawal_reason, original["rationale"]):
        assert value in text
    csv_download = _download_with_retry(page, button_name="Download CSV")
    row = next(
        row
        for row in csv.DictReader(io.StringIO(csv_download.path().read_text(encoding="utf-8")))
        if row["criterion_id"] == "AC-03"
    )
    assert len(json.loads(row["selected_reference_events"])) == 2
    assert json.loads(row["active_reviewer_selected_reference_ids"]) == [refs[1]["reference_id"]]
    return audited


def _reopen_saved_comparison_current(
    page: Page,
    base_url: str,
    *,
    discover: bool = False,
) -> None:
    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    if discover:
        load = page.get_by_role("button", name="Load saved review details", exact=True)
        _run_and_wait_for_streamlit_rerun(page, load.click)
        query = page.get_by_role(
            "textbox",
            name="Search loaded page by repository, PR, head, revision or ID",
            exact=True,
        )
        query.fill("ACME/WIDGET #7")
        _run_and_wait_for_streamlit_rerun(page, lambda: query.press("Tab"))
        expect(page.get_by_text("Search covers this page only.", exact=False)).to_be_visible()
        expect(page.get_by_role("button", name="Reopen local review", exact=True)).to_be_disabled()
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page,
        page.get_by_role("combobox", name="Saved review ID", exact=True),
        option_name=(
            f"acme/widget · PR #7 · head {CURRENT_HEAD[:12]} · criteria revision 2 · "
            f"{CURRENT_REVIEW_ID}"
            if discover
            else CURRENT_REVIEW_ID
        ),
        settled_control=reopen,
    )
    if discover:
        expect(page.get_by_text(f"Head: {CURRENT_HEAD}", exact=False)).to_be_visible()
        expect(page.get_by_text("Retained historical analyses: 1", exact=False)).to_be_visible()
    reopen.click()
    expect(
        page.get_by_text(
            "Review reopened from local storage after validation.",
            exact=True,
        )
    ).to_be_visible()
    page.get_by_text("Compare saved analyses", exact=True).click()
    expect(
        page.get_by_role(
            "combobox",
            name="Comparison baseline",
            exact=True,
        )
    ).to_have_value("")
    expect(
        page.get_by_role(
            "button",
            name="Compare selected saved analysis",
            exact=True,
        )
    ).to_be_disabled()
    expect(
        page.get_by_role(
            "heading",
            name="Re-review comparison",
            exact=True,
        )
    ).to_have_count(0)
    expect(
        page.get_by_role(
            "button",
            name="Download comparison JSON",
            exact=True,
        )
    ).to_have_count(0)


def _assert_saved_comparison_downloads(
    page: Page,
    *,
    previous_head: str,
    previous_review_id: str,
    previous_revision: int = 1,
    previous_analysis: dict,
    current_analysis: dict,
) -> None:
    markdown = _download_with_retry(
        page,
        button_name="Download comparison Markdown",
    )
    assert markdown.suggested_filename.endswith("-comparison.md")
    text = markdown.path().read_text(encoding="utf-8")
    display_text = re.sub(
        r"\\([" + re.escape(string.punctuation) + r"])",
        r"\1",
        html.unescape(text),
    )
    assert "Changed-file Scope Comparison" in text
    assert previous_head in text and CURRENT_HEAD in text
    assert "src/unrelated.py" in text and "notes.md" in text
    assert "Constructed saved\\-comparison reviewer" in text
    assert "No prior scope decision is carried forward" in text
    assert "Previously decided paths now unresolved" in text
    assert "Reviewer-selected Reference Comparison" in text
    assert "Only previous: 1" in text and "Only current: 1" in text
    assert "non-gating static context" in text
    assert "cross-head equivalence" in text and "intent, not execution" in text
    assert "Recorded decision and runtime context" in text

    download = _download_with_retry(page, button_name="Download comparison JSON")
    assert download.suggested_filename.endswith("-comparison.json")
    payload = json.loads(download.path().read_text(encoding="utf-8"))
    comparison = ReviewComparison.model_validate(payload)
    assert comparison.previous_head_sha == previous_head
    assert comparison.current_head_sha == CURRENT_HEAD
    context = payload["selected_reference_comparison"]
    assert payload["reviewer_selected_references_compared"] is True
    assert context["change_counts"] == {
        "identical_record": 0, "only_previous": 1, "only_current": 1,
    }
    for side, head in (("previous", previous_head), ("current", CURRENT_HEAD)):
        assert len(context[side]) == 1
        reference = context[side][0]
        assert reference["head_sha"] == head
        assert reference["criterion_id"] == "AC-01"
        assert reference["file_path"] == "notes.md" and reference["line_number"] == 1
        assert reference["evidence_level"] == "E1"
        assert reference["excerpt"] == "Constructed unrelated project note."
        assert reference["reviewer"].startswith("Constructed ")
        assert reference["rationale"].endswith("not execution evidence.")
        assert reference["reviewer"] in text and reference["rationale"] in text
        assert reference["permalink"] == (
            f"https://github.com/acme/widget/blob/{head}/notes.md#L1-L1"
        )
    assert payload["previous_gate"] == previous_analysis["gate"]["verdict"] == "needs_review"
    assert payload["current_gate"] == current_analysis["gate"]["verdict"] == "needs_review"
    # Same enum on all three saved baselines must retain the old enum-delta meaning.
    assert payload["changed_human_resolutions"] == []
    decision_context = payload["decision_context_comparison"]
    assert decision_context["repository"] == "acme/widget"
    assert decision_context["pr_number"] == 7
    assert len(decision_context["record_changes"]) == 1
    change = decision_context["record_changes"][0]
    assert change["criterion_id"] == "AC-01"
    assert change["kind"] == "recorded_context_changed"
    for side, analysis in (("previous", previous_analysis), ("current", current_analysis)):
        snapshot = decision_context[side]
        assert snapshot["review_id"] == analysis["review"]["review_id"]
        assert snapshot["head_sha"] == analysis["review"]["head_sha"]
        assert snapshot["criteria_revision_number"] == analysis["criteria_revision_number"]
        assert snapshot["criteria_source_provenance"] == (
            analysis["review"]["criteria_source_provenance"]
        )
        assert snapshot["criterion_ids"] == ["AC-01"]
        assert snapshot["resolutions"] == analysis["resolutions"]
        assert snapshot["runtime_evidence"] == analysis["runtime_evidence"]
        assert len(snapshot["resolutions"]) == len(snapshot["runtime_evidence"]) == 1
        resolution, runtime = snapshot["resolutions"][0], snapshot["runtime_evidence"][0]
        assert resolution["decision"] == "manually_verified"
        assert resolution["claimed_evidence_level"] == runtime["evidence_level"] == "E3"
        assert resolution["runtime_evidence_id"] == runtime["runtime_evidence_id"]
        assert len(runtime["runtime_evidence_id"]) > 1_000
        assert change[side]["resolution"] == resolution
        assert change[side]["runtime_evidence"] == [runtime]
        assert change[side]["runtime_link_status"] == "linked"
        # Inspect every retained field against the original persisted analysis,
        # including complete recorded timestamps, artifacts and limitations.
        for record in (resolution, runtime):
            for field, value in record.items():
                if field in {"repository", "pr_number", "head_sha", "criterion_id"}:
                    continue
                for item in value if isinstance(value, list) else [value]:
                    if item is not None:
                        rendered = str(item)
                        assert rendered in display_text or (
                            rendered.replace("Z", "+00:00") in display_text
                        )
    assert payload["evidence_change_counts"] == {
        "unchanged": 0, "relocated": 1, "modified": 0, "added": 0, "removed": 0,
    }
    scope = payload["file_scope"]
    assert scope["previous"]["review_id"] == previous_review_id
    assert scope["previous"]["criteria_revision_number"] == previous_revision
    assert scope["previous"]["head_sha"] == previous_head
    assert scope["previous"]["unresolved_paths"] == []
    assert len(scope["previous"]["latest_decisions"]) == 1
    assert scope["previous"]["latest_decisions"][0]["path"] == "notes.md"
    assert scope["previous"]["latest_decisions"][0]["disposition"] == (
        "outside_confirmed_criteria"
    )
    assert scope["current"]["review_id"] == CURRENT_REVIEW_ID
    assert scope["current"]["criteria_revision_number"] == 2
    assert scope["current"]["head_sha"] == CURRENT_HEAD
    assert scope["current"]["unresolved_paths"] == ["notes.md", "src/unrelated.py"]
    assert scope["current"]["latest_decisions"] == []
    assert scope["previously_decided_paths_now_unresolved"] == ["notes.md"]
    assert scope["inventory_changes"] == [{
        "path": "src/unrelated.py", "kind": "added_to_inventory", "previous": None,
        "current": {"path": "src/unrelated.py", "status": "added", "previous_path": None},
    }]


def _assert_decision_context_details(page: Page, *, previous_actor: str) -> None:
    """Inspect the rendered recorded facts, not just a comparison availability badge."""
    expect(page.get_by_role(
        "heading", name="Recorded decision and runtime context", exact=True,
    )).to_be_visible()
    for side, context in (("Previous", previous_actor), ("Current", "current")):
        label = context.replace("-", " ")
        disclosure = page.get_by_text(f"{side} decision context", exact=True)
        details = disclosure.locator("xpath=ancestor::details[1]")
        if not details.evaluate("node => node.open"):
            disclosure.click()
        for value in (
            f"CONSTRUCTED {label} automatic decision actor",
            f"CONSTRUCTED {label} decision rationale; not customer evidence.",
            f"constructed-{context}-runtime",
            f"CONSTRUCTED {label} CSV export observation",
            f"CONSTRUCTED {label} automatic test environment",
            f"CONSTRUCTED {label} recorded result; no target code was executed.",
            f"CONSTRUCTED {label} observation; no genuine external verification.",
            "Automatic fixture actors are not independent practitioners.",
            "<img src=x onerror=bad> **Untrusted recorded text**",
        ):
            expect(details.get_by_text(value, exact=False).first).to_be_visible()
        expect(details.locator("img[src=x]")).to_have_count(0)
        expect(details.locator("strong", has_text="Untrusted recorded text")).to_have_count(0)
        expect(details.locator(
            f'a[href="https://example.test/constructed/{context}/runtime-report"]',
        ).first).to_be_visible()


def _exercise_historical_inspection(
    page: Page, base_url: str, saved_state: dict, captures: Path,
) -> None:
    """Inspect stored history while the changed current criteria remain unconfirmed."""
    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    _choose_combobox_option(
        page, page.get_by_role("combobox", name="Saved review ID", exact=True),
        option_name=HISTORICAL_REVIEW_ID, settled_control=reopen,
    )
    _run_and_wait_for_streamlit_rerun(page, reopen.click)
    expect(page.get_by_text(
        "Review reopened from local storage after validation.", exact=True,
    )).to_be_visible()
    expect(page.get_by_text(
        "Confirm criteria and run analysis to generate the evidence matrix.", exact=True,
    )).to_be_visible()
    expect(page.get_by_role("button", name="Download JSON", exact=True)).to_have_count(0)
    expect(page.get_by_role(
        "button", name="Record final acceptance", exact=True,
    )).to_have_count(0)
    page.get_by_text("Inspect retained analysis", exact=True).click()
    choice = page.get_by_role("combobox", name="Retained historical analysis", exact=True)
    inspect = page.get_by_role(
        "button", name="Inspect selected historical analysis", exact=True,
    )
    heading = page.get_by_role("heading", name="Historical recorded analysis", exact=True)
    expect(choice).to_have_value("")
    expect(inspect).to_be_disabled()
    expect(heading).to_have_count(0)
    expect(page.get_by_role(
        "button", name="Download historical JSON", exact=True,
    )).to_have_count(0)
    _choose_combobox_option(
        page, choice,
        option_name=f"History 1 · criteria revision 1 · head {HISTORICAL_HEAD}",
        settled_control=inspect,
    )
    expect(heading).to_have_count(0)
    _run_and_wait_for_streamlit_rerun(page, inspect.click)
    expect(heading).to_be_visible()
    historical = saved_state["analysis_history"][0]
    assert historical["criteria_revision_number"] == 1
    assert saved_state["criteria_revision"]["number"] == 3
    assert saved_state["criteria_revision"]["confirmed"] is False
    assert saved_state["bundle"] is None
    assert historical["criteria"] != saved_state["criteria_revision"]["criteria"]
    panel = heading.locator("xpath=ancestor::details[1]")
    for value in (
        HISTORICAL_REVIEW_ID, HISTORICAL_HEAD, HISTORICAL_PRODUCER_VERSION,
        "CONSTRUCTED historical automatic decision actor",
        "CONSTRUCTED historical automatic reference actor",
        HISTORICAL_UNTRUSTED_TEXT,
    ):
        expect(panel.get_by_text(value, exact=False).first).to_be_visible()
    expect(panel.locator("img[src=x]")).to_have_count(0)
    expect(panel.locator(
        "strong", has_text="CONSTRUCTED inert historical result",
    )).to_have_count(0)
    json_download = _download_with_retry(page, button_name="Download historical JSON")
    report = json.loads(json_download.path().read_text(encoding="utf-8"))
    assert set(report) == {
        "report_kind", "schema_version", "boundary", "selection", "analysis",
        "validation_tool_version", "validation_ruleset_version", "validation_source_identity",
    }
    assert report["report_kind"] == "scopeproof_historical_analysis"
    assert report["schema_version"] == 1
    assert report["boundary"]
    assert report["selection"]["review_id"] == HISTORICAL_REVIEW_ID
    assert report["selection"]["history_index"] == 0
    assert report["analysis"] == historical
    assert report["analysis"]["review"]["tool_version"] == HISTORICAL_PRODUCER_VERSION
    assert report["validation_tool_version"] == version("scopeproof")
    assert report["validation_source_identity"] is not None
    markdown_download = _download_with_retry(page, button_name="Download historical Markdown")
    markdown = html.unescape(re.sub(
        r"\\([^\w\s])", r"\1", markdown_download.path().read_text(encoding="utf-8"),
    ))
    for value in (
        HISTORICAL_REVIEW_ID, HISTORICAL_HEAD, HISTORICAL_PRODUCER_VERSION,
        "CONSTRUCTED historical automatic decision actor",
        "CONSTRUCTED historical automatic reference actor",
        HISTORICAL_UNTRUSTED_TEXT,
    ):
        assert value in markdown
    assert "historical" in markdown.lower()
    assert PENDING_CRITERIA_TEXT not in markdown
    expect(page.get_by_role("button", name="Download JSON", exact=True)).to_have_count(0)
    expect(page.get_by_text(
        "Confirm criteria and run analysis to generate the evidence matrix.", exact=True,
    )).to_be_visible()

    for viewport, zoom, name in (
        (VIEWPORTS[0], "", "05-historical-desktop"),
        (VIEWPORTS[1], "", "06-historical-phone"),
        (VIEWPORTS[1], "2", "07-historical-phone-css-zoom-200"),
    ):
        page.set_viewport_size(viewport)
        page.evaluate("value => { document.documentElement.style.zoom = value; }", zoom)
        # Capture the historical section itself, after explicitly bringing its
        # heading into view; selector/sidebar screenshots do not prove this UI.
        heading.scroll_into_view_if_needed()
        expect(heading).to_be_visible()
        expect(heading).to_be_in_viewport()
        expect(panel.get_by_text(HISTORICAL_HEAD, exact=False).first).to_be_visible()
        expect(panel.get_by_text(HISTORICAL_REVIEW_ID, exact=False).first).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        geometry = panel.evaluate("element => ({width: element.getBoundingClientRect().width, "
                                  "scrollWidth: element.scrollWidth, "
                                  "clientWidth: element.clientWidth})")
        assert geometry["width"] > 0
        assert geometry["scrollWidth"] <= geometry["clientWidth"] + 1
        preview = panel.locator(".st-key-historical_analysis_preview")
        tables = preview.locator("table")
        assert tables.count() > 0
        for table in tables.all():
            reachability = table.evaluate("""element => {
                element.scrollLeft = element.scrollWidth;
                const bounds = element.getBoundingClientRect();
                const last = element.querySelector('tr').lastElementChild.getBoundingClientRect();
                const result = {
                    lastColumnReachable: last.right <= bounds.right + 1 && last.right > bounds.left,
                    overflow: getComputedStyle(element).overflowX,
                    layoutWidth: element.clientWidth,
                };
                element.scrollLeft = 0;
                return result;
            }""")
            assert reachability["overflow"] == "auto"
            assert reachability["layoutWidth"] <= geometry["clientWidth"] + 1
            assert reachability["lastColumnReachable"]
        page.screenshot(path=str(captures / f"{name}.png"))
        # At CSS 200% the introductory boundary can fill a phone viewport.
        # Preserve separate visible identity captures rather than treating
        # off-screen text or metadata as screenshot evidence.
        for identity, suffix in ((HISTORICAL_REVIEW_ID, "owner"), (HISTORICAL_HEAD, "head")):
            target = panel.get_by_text(identity, exact=False).first
            target.scroll_into_view_if_needed()
            expect(target).to_be_in_viewport()
            page.screenshot(path=str(captures / f"{name}-{suffix}.png"))
        (captures / f"{name}.json").write_text(json.dumps({
            "viewport": viewport, "css_zoom": zoom or "1", "panel": geometry,
            "historical_head": HISTORICAL_HEAD, "owner": HISTORICAL_REVIEW_ID,
        }, indent=2), encoding="utf-8")
    page.evaluate("document.documentElement.style.zoom = ''")
    page.set_viewport_size(VIEWPORTS[0])

    # Reopening the same owner must expire applied history/download state,
    # requiring an explicit choice and inspection again.
    resume = page.get_by_text("Resume a saved review", exact=True)
    if not resume.locator("xpath=ancestor::details[1]").evaluate("node => node.open"):
        resume.click()
    replace = page.get_by_role(
        "checkbox", name="Allow replacing the unsaved current review", exact=True,
    )
    expect(reopen).to_be_disabled()
    _run_and_wait_for_streamlit_rerun(
        page,
        page.get_by_text("Allow replacing the unsaved current review", exact=True).click,
    )
    expect(replace).to_be_checked()
    expect(reopen).to_be_enabled()
    _run_and_wait_for_streamlit_rerun(page, reopen.click)
    # Reopen intentionally collapses this panel. Inspect its retained DOM too:
    # hidden stale report/download nodes must not masquerade as cleared state.
    expect(page.get_by_role(
        "combobox", name="Retained historical analysis", exact=True, include_hidden=True,
    )).to_have_value("")
    expect(page.get_by_role(
        "button", name="Inspect selected historical analysis", exact=True, include_hidden=True,
    )).to_be_disabled()
    expect(page.get_by_role(
        "heading", name="Historical recorded analysis", exact=True, include_hidden=True,
    )).to_have_count(0)
    expect(page.get_by_role(
        "button", name="Download historical JSON", exact=True, include_hidden=True,
    )).to_have_count(0)
    expect(page.get_by_role(
        "button", name="Download historical Markdown", exact=True, include_hidden=True,
    )).to_have_count(0)


def test_installed_wheel_saved_comparison_survives_restart_without_record_writes(
    tmp_path: Path, installed_wheel: Path,
) -> None:
    """Persisted sources, not prior Streamlit state, supply both explicit comparisons."""
    runtime_dir = tmp_path / "runtime"
    home_dir = runtime_dir / "home"
    home_dir.mkdir(parents=True)
    review_store_dir = home_dir / ".scopeproof" / "reviews"
    recipe = runtime_dir / "constructed-saved-comparison.py"
    shutil.copy2(REPOSITORY_ROOT / "tests" / "saved_comparison_fixture.py", recipe)
    _run(
        str(installed_wheel / "bin" / "python"), "-I", "-c",
        (
            "from pathlib import Path; import runpy, sys; import apps, scopeproof_core; "
            "from scopeproof_core.storage.json_store import JsonReviewStore; "
            "assert all(Path(module.__file__).resolve().is_relative_to("
            "Path(sys.prefix).resolve()) for module in (apps, scopeproof_core)); "
            "recipe=runpy.run_path(sys.argv[1]); "
            "store=JsonReviewStore(Path(sys.argv[2])); "
            "[store.save(state) for state in recipe['saved_comparison_states']("
            "selected_references=True, foreign_history=True, decision_context=True)]"
        ),
        str(recipe), str(review_store_dir), cwd=runtime_dir,
    )
    saved_bytes = {path.name: path.read_bytes() for path in review_store_dir.glob("*.json")}
    assert set(saved_bytes) == {f"{CURRENT_REVIEW_ID}.json", f"{PREVIOUS_REVIEW_ID}.json"}
    saved_analyses = {}
    for raw_record in saved_bytes.values():
        saved_state = json.loads(raw_record)["state"]
        for analysis in [saved_state["bundle"], *saved_state["analysis_history"]]:
            saved_analyses[analysis["review"]["head_sha"]] = analysis
            assert analysis["gate"]["verdict"] == "needs_review"

    historical_recipe = runtime_dir / "constructed-historical-analysis.py"
    shutil.copy2(REPOSITORY_ROOT / "tests" / "historical_analysis_fixture.py", historical_recipe)
    _run(
        str(installed_wheel / "bin" / "python"), "-I", "-c",
        "from pathlib import Path; import runpy, sys; import apps, scopeproof_core; "
        "from scopeproof_core.storage.json_store import JsonReviewStore; "
        "assert all(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()) "
        "for module in (apps, scopeproof_core)); "
        "recipe=runpy.run_path(sys.argv[1]); "
        "JsonReviewStore(Path(sys.argv[2])).save(recipe['historical_analysis_state']())",
        str(historical_recipe), str(review_store_dir), cwd=runtime_dir,
    )
    historical_path = review_store_dir / f"{HISTORICAL_REVIEW_ID}.json"
    saved_bytes[historical_path.name] = historical_path.read_bytes()
    historical_state = json.loads(saved_bytes[historical_path.name])["state"]

    def assert_records_unchanged() -> None:
        assert {
            path.name: path.read_bytes() for path in review_store_dir.glob("*.json")
        } == saved_bytes

    captures = tmp_path / "captures"
    captures.mkdir()
    diagnostics = Path(os.environ.get(
        "SCOPEPROOF_BROWSER_DIAGNOSTIC_DIR", str(tmp_path / "diagnostics"),
    )) / "saved-comparison"
    browser_errors: list[str] = []
    external_requests: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for generation in range(3):
                with _installed_workbench_server(
                    installed_wheel, runtime_dir, home_dir,
                    log_name=f"saved-comparison-{generation}.log",
                ) as (base_url, log_path):
                    context = browser.new_context(viewport=VIEWPORTS[0])
                    try:
                        context.route(
                            "**/*", lambda route: _route_loopback_only(route, external_requests),
                        )
                        page = context.new_page()
                        page.on("console", lambda message: (
                            browser_errors.append(f"console: {message.text}")
                            if message.type == "error" else None
                        ))
                        page.on("pageerror", lambda error: browser_errors.append(f"page: {error}"))
                        page.on("websocket", lambda websocket: (
                            external_requests.append(websocket.url)
                            if not _is_loopback_request(websocket.url) else None
                        ))
                        with _capture_browser_failure(
                            page, diagnostics / f"generation-{generation}", log_path,
                        ):
                            if generation == 2:
                                _exercise_historical_inspection(
                                    page, base_url, historical_state, captures,
                                )
                                assert_records_unchanged()
                                continue
                            _reopen_saved_comparison_current(
                                page, base_url, discover=generation == 1,
                            )
                            assert_records_unchanged()
                            if generation == 0:
                                page.screenshot(path=str(captures / "01-before-restart.png"))
                                continue

                            baseline = page.get_by_role(
                                "combobox",
                                name="Comparison baseline",
                                exact=True,
                            )
                            compare = page.get_by_role(
                                "button",
                                name="Compare selected saved analysis",
                                exact=True,
                            )
                            for (
                                option,
                                analysis_option,
                                previous_head,
                                previous_id,
                                previous_revision,
                                previous_actor,
                            ) in (
                                (
                                    f"acme/widget · PR #7 · head {PREVIOUS_HEAD[:12]} · "
                                    f"criteria revision 2 · {PREVIOUS_REVIEW_ID}",
                                    None,
                                    PREVIOUS_HEAD,
                                    PREVIOUS_REVIEW_ID,
                                    2,
                                    "previous",
                                ),
                                (
                                    f"History 1 · criteria revision 1 · head {HISTORY_HEAD}",
                                    None,
                                    HISTORY_HEAD,
                                    CURRENT_REVIEW_ID,
                                    1,
                                    "historical",
                                ),
                                (
                                    f"acme/widget · PR #7 · head {PREVIOUS_HEAD[:12]} · "
                                    f"criteria revision 2 · {PREVIOUS_REVIEW_ID}",
                                    "History 1 · criteria revision 1 · head "
                                    f"{FOREIGN_HISTORY_HEAD}",
                                    FOREIGN_HISTORY_HEAD,
                                    PREVIOUS_REVIEW_ID,
                                    1,
                                    "foreign-history",
                                ),
                            ):
                                _choose_combobox_option(
                                    page,
                                    baseline,
                                    option_name=option,
                                    settled_control=compare,
                                )
                                if analysis_option is not None:
                                    analysis = page.get_by_role(
                                        "combobox", name="Baseline analysis", exact=True,
                                    )
                                    _choose_combobox_option(
                                        page, analysis, option_name=analysis_option,
                                        settled_control=compare,
                                    )
                                expect(page.get_by_role(
                                    "heading", name="Re-review comparison", exact=True,
                                )).to_have_count(0)
                                expect(page.get_by_role(
                                    "button", name="Download comparison JSON", exact=True,
                                )).to_have_count(0)
                                compare.click()
                                expect(page.get_by_role(
                                    "heading", name="Re-review comparison", exact=True,
                                )).to_be_visible()
                                expect(page.get_by_text(
                                    f"Previous head: {previous_head}", exact=True,
                                )).to_be_visible()
                                expect(page.get_by_text(
                                    f"Current head: {CURRENT_HEAD}", exact=True,
                                )).to_be_visible()
                                expect(page.get_by_role(
                                    "heading", name="Reviewer-selected reference comparison",
                                    exact=True,
                                )).to_be_visible()
                                expect(page.get_by_text(
                                    "Identical record: 0 · Only previous: 1 · Only current: 1",
                                    exact=False,
                                )).to_be_visible()
                                reference_details = {}
                                for kind in ("Only Previous", "Only Current"):
                                    disclosure = page.get_by_text(
                                        re.compile(rf"^{kind} · Reference \d+$"),
                                    )
                                    detail = disclosure.locator("xpath=ancestor::details[1]")
                                    reference_details[kind] = detail
                                    if not detail.evaluate("node => node.open"):
                                        disclosure.click()
                                expect(reference_details["Only Previous"].get_by_text(
                                    f"Constructed {previous_actor} reference reviewer", exact=True,
                                )).to_be_visible()
                                expect(reference_details["Only Current"].get_by_text(
                                    "Constructed current reference reviewer", exact=True,
                                )).to_be_visible()
                                expect(page.get_by_text(
                                    "Added to inventory: src/unrelated.py", exact=True,
                                )).to_be_visible()
                                expect(page.get_by_text(
                                    "Previously decided paths now unresolved:", exact=True,
                                )).to_be_visible()
                                _assert_decision_context_details(
                                    page, previous_actor=previous_actor,
                                )
                                _assert_saved_comparison_downloads(
                                    page, previous_head=previous_head,
                                    previous_review_id=previous_id,
                                    previous_revision=previous_revision,
                                    previous_analysis=saved_analyses[previous_head],
                                    current_analysis=saved_analyses[CURRENT_HEAD],
                                )
                                assert_records_unchanged()
                            page.get_by_role(
                                "heading", name="Re-review comparison", exact=True,
                            ).scroll_into_view_if_needed()
                            page.screenshot(path=str(captures / "02-history-comparison.png"))
                            page.set_viewport_size(VIEWPORTS[1])
                            baseline.scroll_into_view_if_needed()
                            expect(baseline).to_be_visible()
                            expect(page.get_by_role(
                                "combobox", name="Baseline analysis", exact=True,
                            )).to_be_visible()
                            expect(compare).to_be_enabled()
                            assert page.evaluate(
                                "document.documentElement.scrollWidth <= window.innerWidth"
                            )
                            page.screenshot(path=str(captures / "03-phone-comparison-controls.png"))
                            _assert_decision_context_details(
                                page, previous_actor="foreign-history",
                            )
                            assert page.evaluate(
                                "document.documentElement.scrollWidth <= window.innerWidth"
                            )
                            page.evaluate("document.documentElement.style.zoom = '2'")
                            _assert_decision_context_details(
                                page, previous_actor="foreign-history",
                            )
                            assert page.evaluate(
                                "document.documentElement.scrollWidth <= window.innerWidth"
                            )
                            page.screenshot(path=str(
                                captures / "04-phone-decision-context-css-zoom-200.png",
                            ))
                            page.evaluate("document.documentElement.style.zoom = ''")
                    finally:
                        context.close()
                assert_records_unchanged()
        finally:
            browser.close()
    assert_records_unchanged()
    assert browser_errors == []
    assert external_requests == []
    assert (captures / "01-before-restart.png").is_file()
    assert (captures / "02-history-comparison.png").is_file()
    assert (captures / "03-phone-comparison-controls.png").is_file()
    assert (captures / "04-phone-decision-context-css-zoom-200.png").is_file()
    for name in (
        "05-historical-desktop", "06-historical-phone", "07-historical-phone-css-zoom-200",
    ):
        assert (captures / f"{name}.png").is_file()
        assert (captures / f"{name}.json").is_file()
        assert (captures / f"{name}-owner.png").is_file()
        assert (captures / f"{name}-head.png").is_file()
