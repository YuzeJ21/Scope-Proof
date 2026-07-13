from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from scopeproof_core.version import __version__


def load_launcher():
    launcher_path = Path("apps/web/launcher.py")
    assert launcher_path.exists(), "installed web launcher is missing"

    spec = importlib.util.spec_from_file_location("scopeproof_test_web_launcher", launcher_path)
    assert spec is not None and spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    return launcher


def test_web_launcher_reports_shared_version_without_starting_streamlit(
    monkeypatch, capsys
) -> None:
    launcher = load_launcher()

    def unexpected_run(*args, **kwargs):
        raise AssertionError("Streamlit must not start for --version")

    monkeypatch.setattr(launcher.subprocess, "run", unexpected_run)

    with pytest.raises(SystemExit) as raised:
        launcher.main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == f"scopeproof-web {__version__}\n"


def test_packaged_web_launcher_uses_current_interpreter_without_shell(monkeypatch) -> None:
    launcher = load_launcher()
    calls: list[tuple[list[str], bool]] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        calls.append((command, check))
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    assert (
        launcher.main(
            ["--host", "127.0.0.2", "--port", "8765", "--no-headless"]
        )
        == 7
    )
    assert len(calls) == 1
    command, check = calls[0]
    assert command[:7] == [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "--server.address=127.0.0.2",
        "--server.port=8765",
        "--server.headless=false",
    ]
    assert Path(command[7]).resolve() == Path("apps/web/app.py").resolve()
    assert check is False


def test_packaged_web_launcher_exits_cleanly_on_keyboard_interrupt(monkeypatch) -> None:
    launcher = load_launcher()

    def interrupted_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        raise KeyboardInterrupt

    monkeypatch.setattr(launcher.subprocess, "run", interrupted_run)

    assert launcher.main([]) == 130


@pytest.mark.parametrize("port", ["0", "65536"])
def test_packaged_web_launcher_rejects_out_of_range_port_before_launch(
    monkeypatch, capsys, port: str
) -> None:
    launcher = load_launcher()
    launched = False

    def unexpected_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        nonlocal launched
        launched = True
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(launcher.subprocess, "run", unexpected_run)

    with pytest.raises(SystemExit) as raised:
        launcher.main(["--port", port])

    assert raised.value.code == 2
    stderr = capsys.readouterr().err
    assert "1..65535" in stderr
    assert "Traceback" not in stderr
    assert launched is False


def test_packaged_web_launcher_rejects_unknown_option_before_launch(
    monkeypatch, capsys
) -> None:
    launcher = load_launcher()
    launched = False

    def unexpected_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        nonlocal launched
        launched = True
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(launcher.subprocess, "run", unexpected_run)

    with pytest.raises(SystemExit) as raised:
        launcher.main(["--unknown-option"])

    assert raised.value.code == 2
    stderr = capsys.readouterr().err
    assert "unrecognized arguments" in stderr
    assert "Traceback" not in stderr
    assert launched is False
