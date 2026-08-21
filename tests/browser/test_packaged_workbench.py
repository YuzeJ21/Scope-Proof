from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import sys
import time
from hashlib import sha256
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

import pytest
from playwright.sync_api import (
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


def _choose_combobox_option(
    page: Page, combobox: Locator, *, option_name: str
) -> None:
    for attempt in range(3):
        if combobox.input_value() == option_name:
            return
        try:
            combobox.click()
            combobox.fill(option_name)
            option = page.get_by_role("option", name=option_name, exact=True)
            expect(option).to_be_visible(timeout=5_000)
            option.click(timeout=5_000)
            expect(combobox).to_have_value(option_name, timeout=5_000)
            return
        except PlaywrightTimeoutError:
            if combobox.input_value() == option_name:
                return
            if attempt == 2:
                raise


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

    class FakeOption:
        def __init__(self, combobox: FakeCombobox) -> None:
            self.combobox = combobox
            self.clicks = 0

        def click(self, *, timeout: int | None = None) -> None:
            self.clicks += 1
            if self.clicks == 1:
                raise PlaywrightTimeoutError("element was detached from the DOM")
            self.combobox.value = "junit-browser-review"

    class FakePage:
        def __init__(self, option: FakeOption) -> None:
            self.option = option

        def get_by_role(self, *args: object, **kwargs: object) -> FakeOption:
            return self.option

    class FakeExpectation:
        def __init__(self, target: object) -> None:
            self.target = target

        def to_be_visible(self, *, timeout: int | None = None) -> None:
            return None

        def to_have_value(self, expected: str, *, timeout: int | None = None) -> None:
            assert isinstance(self.target, FakeCombobox)
            assert self.target.value == expected

    combobox = FakeCombobox()
    option = FakeOption(combobox)
    monkeypatch.setattr(
        sys.modules[__name__], "expect", lambda target: FakeExpectation(target)
    )

    _choose_combobox_option(
        FakePage(option),  # type: ignore[arg-type]
        combobox,  # type: ignore[arg-type]
        option_name="junit-browser-review",
    )

    assert option.clicks == 2
    assert combobox.clicks == 2
    assert combobox.fills == ["junit-browser-review", "junit-browser-review"]


def _exercise_primary_path(
    page: Page, base_url: str, *, verify_persistence_and_downloads: bool
) -> None:
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

    if verify_persistence_and_downloads:
        save_notice = page.get_by_text("Review saved automatically. ID:", exact=False)
        expect(save_notice).to_be_visible()
        saved_id_match = re.search(
            r"Review saved automatically\. ID: ([A-Za-z0-9_-]+)\.",
            save_notice.inner_text(),
        )
        assert saved_id_match is not None
        saved_review_id = saved_id_match.group(1)

        markdown_export = page.get_by_role("button", name="Download Markdown", exact=True)
        with page.expect_download() as download_info:
            markdown_export.click()
        download = download_info.value
        assert download.suggested_filename.endswith(".md")
        assert b"head-demo-002" in download.path().read_bytes()

        page.get_by_text("Resume a saved review", exact=True).click()
        expect(page.get_by_text(re.compile(r"saved local reviews? found"))).to_be_visible()
        saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
        _choose_combobox_option(page, saved_review, option_name=saved_review_id)
        reopen = page.get_by_role("button", name="Reopen local review", exact=True)
        expect(reopen).to_be_enabled()
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


def _exercise_junit_import_round_trip(
    page: Page,
    base_url: str,
    *,
    artifact_path: Path,
    artifact_digest: str,
) -> None:
    page.goto(base_url, wait_until="domcontentloaded")
    page.get_by_text("Resume a saved review", exact=True).click()
    saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
    _choose_combobox_option(
        page, saved_review, option_name="junit-browser-review"
    )
    reopen = page.get_by_role("button", name="Reopen local review", exact=True)
    expect(reopen).to_be_enabled()
    reopen.click()
    expect(
        page.get_by_text(
            "Review reopened from local storage after validation.", exact=True
        )
    ).to_be_visible()

    junit_expander = page.get_by_text("Import external JUnit results", exact=True)
    junit_expander.click()
    page.get_by_label("Local JUnit XML artifact", exact=True).locator(
        "input[type=file]"
    ).set_input_files(artifact_path)
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
    importer.press("Tab")
    if not preview.is_visible():
        junit_expander.click()
    expect(preview).to_be_visible()
    mapping = page.get_by_role(
        "combobox", name="Map JUnit scopes to the selected criterion", exact=True
    )
    expect(mapping).to_be_enabled()
    mapping.click()
    mapping.fill("suite-0001")
    suite_option = page.get_by_text(
        "suite-0001 · suite · unit", exact=True
    ).last
    expect(suite_option).to_be_visible()
    suite_option.click()
    page.keyboard.press("Escape")
    expect(preview).to_have_count(1)
    if not preview.is_visible():
        junit_expander.click()
    importer = page.get_by_label("Asserted JUnit importer (required)", exact=True)
    importer.fill("Packaged browser reviewer")
    importer.press("Enter")
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
    save.click()
    expect(
        page.get_by_text(
            "Imported JUnit results appended as external non-gating context.",
            exact=True,
        )
    ).to_be_visible()
    boundary = page.get_by_text(JUNIT_EVIDENCE_BOUNDARY_DESCRIPTION, exact=True)
    if not boundary.is_visible():
        junit_expander.click()
    expect(boundary).to_be_visible()
    expect(page.get_by_text("Review saved automatically. ID:", exact=False)).to_be_visible()

    page.get_by_text("Resume a saved review", exact=True).click()
    saved_review = page.get_by_role("combobox", name="Saved review ID", exact=True)
    _choose_combobox_option(
        page, saved_review, option_name="junit-browser-review"
    )
    page.get_by_role("button", name="Reopen local review", exact=True).click()
    expect(
        page.get_by_text(
            "Review reopened from local storage after validation.", exact=True
        )
    ).to_be_visible()
    expect(
        page.get_by_text("Recorded imported JUnit results (1)", exact=True)
    ).to_be_visible()

    for label, suffix in (("Download Markdown", ".md"), ("Download JSON", ".json")):
        download_button = page.get_by_role("button", name=label, exact=True)
        expect(download_button).to_be_visible()
        expect(download_button).to_be_enabled()
        with page.expect_download() as download_info:
            download_button.click()
        download = download_info.value
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
    _run(
        str(environment_python),
        "-c",
        (
            "from pathlib import Path; import sys; "
            "from scopeproof_core.demo import build_demo_review; "
            "from scopeproof_core.reviews.lifecycle import new_review_state; "
            "from scopeproof_core.schemas.models import ReviewBundle; "
            "from scopeproof_core.storage.json_store import JsonReviewStore; "
            "bundle=build_demo_review().model_copy(deep=True); "
            "bundle.review.review_id='junit-browser-review'; "
            "bundle.review.head_sha='a'*40; "
            "bundle.criteria_revision_number=1; "
            "[(setattr(item, 'commit_sha', bundle.review.head_sha), "
            "setattr(item, 'permalink', item.permalink.replace('head-demo-002', "
            "bundle.review.head_sha))) for item in bundle.evidence]; "
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
                    _exercise_primary_path(
                        page,
                        base_url,
                        verify_persistence_and_downloads=viewport_index == 1,
                    )
                    if viewport_index == 0:
                        _exercise_junit_import_round_trip(
                            page,
                            base_url,
                            artifact_path=junit_artifact,
                            artifact_digest=junit_artifact_digest,
                        )
                    context.close()
            finally:
                browser.close()
        assert browser_errors == []
        assert external_requests == []
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        assert process.poll() is not None
