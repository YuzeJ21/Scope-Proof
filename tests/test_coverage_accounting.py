"""Require real coverage accounting across trusted constructed execution paths."""

import json
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

PROBE = dedent("""\
    def main_path():
        return "main"  # main marker

    def thread_path():
        return "thread"  # thread marker

    def exception_path():
        try:
            raise ValueError("constructed")  # raise marker
        except ValueError:
            return "caught"  # caught marker

    def child_path():
        return "child"  # child marker

    def never_called():
        return "uncalled"  # missing control
""")

INNER_TEST = dedent("""\
    import os
    import subprocess
    import sys
    import threading

    import coverage
    import scopeproof_coverage_probe as probe

    def test_constructed_paths():
        active = coverage.Coverage.current()
        assert active is not None
        assert active._collector.tracer_name() == os.environ["SCOPEPROOF_EXPECTED_COVERAGE_CORE"]
        assert probe.main_path() == "main"
        results = []
        worker = threading.Thread(target=lambda: results.append(probe.thread_path()))
        worker.start()
        worker.join(timeout=10)
        assert not worker.is_alive()
        assert results == ["thread"]
        assert probe.exception_path() == "caught"
        child = subprocess.run(
            [sys.executable, "-c", "import os, coverage; "
             "import scopeproof_coverage_probe as probe; "
             "active = coverage.Coverage.current(); "
             "assert active is not None; "
             "assert active._collector.tracer_name() == "
             "os.environ['SCOPEPROOF_EXPECTED_COVERAGE_CORE']; "
             "assert probe.child_path() == 'child'"],
            capture_output=True, text=True, timeout=30,
        )
        assert child.returncode == 0, child.stdout + child.stderr
""")


@pytest.mark.parametrize("core,actual_name", [("ctrace", "CTracer"), ("sysmon", "SysMonitor")])
def test_coverage_engine_counts_threads_children_and_missed_control(
    tmp_path: Path,
    core: str,
    actual_name: str,
) -> None:
    if core == "sysmon" and sys.version_info < (3, 12):
        pytest.skip("sys.monitoring needs Python 3.12; the CTracer control still runs")
    source = tmp_path / "source"
    source.mkdir()
    (source / "scopeproof_coverage_probe.py").write_text(PROBE, encoding="utf-8")
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "test_probe.py").write_text(INNER_TEST, encoding="utf-8")
    config = tmp_path / "coverage.ini"
    config.write_text("[run]\nbranch = false\n", encoding="utf-8")
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COV_CORE_")
        and key
        not in {
            "COVERAGE_PROCESS_START",
            "COVERAGE_PROCESS_CONFIG",
            "COVERAGE_FILE",
            "COVERAGE_DEBUG",
            "COVERAGE_DEBUG_FILE",
            "PYTEST_ADDOPTS",
        }
    }
    environment.update(
        {
            "COVERAGE_CORE": core,
            "COVERAGE_FILE": str(tmp_path / ".coverage"),
            "SCOPEPROOF_EXPECTED_COVERAGE_CORE": actual_name,
            "PYTHONPATH": str(source) + os.pathsep + environment.get("PYTHONPATH", ""),
        }
    )
    output = tmp_path / "coverage.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(suite),
            "-q",
            "--noconftest",
            f"--cov={source}",
            f"--cov-config={config}",
            f"--cov-report=json:{output}",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no-sysmon" not in result.stdout + result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["meta"]["branch_coverage"] is False
    assert len(report["files"]) == 1
    measured = next(iter(report["files"].values()))
    lines = PROBE.splitlines()
    for marker in ("main marker", "thread marker", "raise marker", "caught marker", "child marker"):
        number = next(i for i, line in enumerate(lines, 1) if marker in line)
        assert number in measured["executed_lines"], marker
    missed = next(i for i, line in enumerate(lines, 1) if "missing control" in line)
    assert measured["missing_lines"] == [missed]
    assert measured["excluded_lines"] == []
    assert measured["summary"]["num_statements"] == len(measured["executed_lines"]) + 1
