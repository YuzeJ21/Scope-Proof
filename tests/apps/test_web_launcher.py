from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def load_launcher():
    launcher_path = Path("apps/web/launcher.py")
    assert launcher_path.exists(), "installed web launcher is missing"

    spec = importlib.util.spec_from_file_location("scopeproof_test_web_launcher", launcher_path)
    assert spec is not None and spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    return launcher


def test_packaged_web_launcher_uses_current_interpreter_without_shell(monkeypatch) -> None:
    launcher = load_launcher()
    calls: list[tuple[list[str], bool]] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        calls.append((command, check))
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    assert launcher.main() == 7
    assert len(calls) == 1
    command, check = calls[0]
    assert command[:4] == [sys.executable, "-m", "streamlit", "run"]
    assert Path(command[4]).resolve() == Path("apps/web/app.py").resolve()
    assert check is False


def test_packaged_web_launcher_exits_cleanly_on_keyboard_interrupt(monkeypatch) -> None:
    launcher = load_launcher()

    def interrupted_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        raise KeyboardInterrupt

    monkeypatch.setattr(launcher.subprocess, "run", interrupted_run)

    assert launcher.main() == 130
