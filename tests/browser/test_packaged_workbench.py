from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

import pytest
from playwright.sync_api import Page, Route, expect, sync_playwright

pytestmark = pytest.mark.browser

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIEWPORTS = (
    {"width": 1280, "height": 720},
    {"width": 390, "height": 844},
)


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


def _activate_with_keyboard(page: Page, label: str) -> None:
    control = page.get_by_role("button", name=label, exact=True)
    expect(control).to_be_enabled()
    control.focus()
    control.press("Enter")


def _exercise_primary_path(page: Page, base_url: str) -> None:
    page.goto(base_url, wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="ScopeProof", exact=True)).to_be_visible()

    page.get_by_text("Try ScopeProof", exact=True).click()
    _activate_with_keyboard(page, "Load deliberately constructed demo")
    confirmer = page.get_by_label("Confirmed by", exact=True)
    expect(confirmer).to_be_visible()
    confirmer.fill("Packaged browser reviewer")
    confirmer.press("Enter")

    _activate_with_keyboard(page, "Confirm criteria")
    expect(page.get_by_text("Criteria confirmed by the reviewer.", exact=True)).to_be_visible()

    _activate_with_keyboard(page, "Run deterministic analysis")
    expect(page.get_by_role("heading", name="3 · Evidence Matrix", exact=True)).to_be_visible()
    expect(page.get_by_text("Missing evidence", exact=True).first).to_be_visible()
    expect(page.get_by_text("Review status: Action required", exact=True)).to_be_visible()
    expect(page.get_by_text("Evidence status:", exact=False).first).to_be_visible()

    for label in ("Download Markdown", "Download JSON", "Download CSV"):
        export = page.get_by_role("button", name=label, exact=True)
        expect(export).to_be_visible()
        expect(export).to_be_enabled()

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.evaluate("document.body.scrollWidth <= window.innerWidth")


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
                for viewport in VIEWPORTS:
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
                    _exercise_primary_path(page, base_url)
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
