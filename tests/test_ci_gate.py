import os
import re
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

WORKFLOW_PATH = Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
EXPECTED_RESULT_BINDINGS = {
    "PYTHON_311_RESULT": "${{ needs.compatibility-python-311.result }}",
    "PYTHON_313_RESULT": "${{ needs.compatibility-python-313.result }}",
    "WINDOWS_RESULT": "${{ needs.compatibility-windows.result }}",
    "LOCKED_RESULT": "${{ needs.locked-environment.result }}",
    "ENGINEERING_RESULT": "${{ needs.engineering-validation.result }}",
}
EXPECTED_PREDECESSORS = {
    "compatibility-python-311",
    "compatibility-python-313",
    "compatibility-windows",
    "locked-environment",
    "engineering-validation",
}


@pytest.fixture
def workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _job_block(workflow: str, job_id: str) -> str:
    """Bound reads to one job in the workflow's existing block-style layout."""
    jobs = workflow.split("\njobs:\n", maxsplit=1)
    assert len(jobs) == 2, "CI must have a jobs mapping"
    headers = list(re.finditer(r"^  ([A-Za-z0-9_-]+):[ \t]*$", jobs[1], re.MULTILINE))
    positions = [index for index, header in enumerate(headers) if header.group(1) == job_id]
    assert len(positions) == 1, f"Expected exactly one CI job named {job_id!r}"
    index = positions[0]
    end = headers[index + 1].start() if index + 1 < len(headers) else len(jobs[1])
    return jobs[1][headers[index].end() + 1 : end]


def _property(block: str, key: str, indent: int) -> str:
    values = re.findall(
        rf"^{' ' * indent}{re.escape(key)}:[ \t]*([^\n]*)$", block, re.MULTILINE
    )
    assert len(values) == 1, f"Expected exactly one {key!r} property at indent {indent}"
    return values[0].strip()


def _gate_step(verify: str) -> str:
    steps = re.findall(r"^    steps:\n(.*?)(?=^    \S|\Z)", verify, re.MULTILINE | re.DOTALL)
    assert len(steps) == 1, "Required verify job must have one steps mapping"
    assert len(re.findall(r"^      -[ \t]+", steps[0], re.MULTILINE)) == 1, (
        "Required verify job must have exactly one aggregate step"
    )
    assert _property(steps[0], "shell", 8) == "bash"
    assert re.search(r"^(?:      - |        )if:", steps[0], re.MULTILINE) is None
    assert re.search(r"^\s*(?:-\s+)?uses:", steps[0], re.MULTILINE) is None
    return steps[0]


def _gate_script(verify: str) -> str:
    step = _gate_step(verify)
    run_lines = list(re.finditer(r"^        run:[ \t]*\|[+-]?[ \t]*$", step, re.MULTILINE))
    assert len(run_lines) == 1, "Aggregate must run one inline literal Bash script"
    script_lines = []
    for line in step[run_lines[0].end() + 1 :].splitlines():
        if line.strip() and not line.startswith(" " * 10):
            break
        script_lines.append(line)
    script = dedent("\n".join(script_lines))
    assert script.strip(), "Aggregate script must not be empty"
    return script + "\n"


def _result_bindings(verify: str) -> dict[str, str]:
    bindings: dict[str, str] = {}
    # Either job or step env is valid; reject duplicate/overridden result bindings.
    for indent in (4, 8):
        env_blocks = re.findall(
            rf"^{' ' * indent}env:\n(.*?)(?=^{' ' * indent}\S|\Z)",
            verify,
            re.MULTILINE | re.DOTALL,
        )
        assert len(env_blocks) <= 1, f"Duplicate env mapping at indent {indent}"
        for env in env_blocks:
            for line in env.splitlines():
                if not line.strip():
                    continue
                binding = re.fullmatch(rf"{' ' * (indent + 2)}([A-Z0-9_]+):[ \t]*(.*)", line)
                assert binding is not None, f"Unsupported aggregate env binding: {line!r}"
                key, value = binding.groups()
                assert key not in bindings, f"Aggregate env must not override {key}"
                bindings[key] = value.strip()
    return bindings


@pytest.fixture
def bash() -> str:
    executable = shutil.which("bash")
    if executable is None:
        pytest.skip("Executing the CI gate requires Bash; structural checks still run")
    return executable


def _run_gate(
    bash: str, script: str, results: dict[str, str], directory: Path
) -> subprocess.CompletedProcess[str]:
    # Do not inherit BASH_ENV, exported functions, shell options, or host lane results.
    environment = {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C", **results}
    return subprocess.run(
        [bash, "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def test_engineering_validation_runs_without_prerequisites(workflow: str) -> None:
    engineering = _job_block(workflow, "engineering-validation")

    assert re.search(r"^    needs:", engineering, re.MULTILINE) is None
    assert re.search(r"^    if:", engineering, re.MULTILINE) is None


def test_verify_requires_every_engineering_lane(workflow: str) -> None:
    verify = _job_block(workflow, "verify")
    needs = _property(verify, "needs", 4)
    flow_list = re.fullmatch(r"\[([^\]\n]*)\]", needs)
    assert flow_list is not None, "Required verify dependencies must be an explicit flow list"
    predecessors = [item.strip() for item in flow_list.group(1).split(",")]

    assert len(predecessors) == len(EXPECTED_PREDECESSORS)
    assert set(predecessors) == EXPECTED_PREDECESSORS
    for job_id in predecessors:
        _job_block(workflow, job_id)


def test_verify_always_runs_as_the_required_check(workflow: str) -> None:
    verify = _job_block(workflow, "verify")

    assert _property(verify, "name", 4) == "verify"
    assert re.fullmatch(r"\$\{\{\s*always\(\)\s*\}\}", _property(verify, "if", 4))


def test_verify_is_one_short_mandatory_bash_step(workflow: str) -> None:
    verify = _job_block(workflow, "verify")

    assert _property(verify, "timeout-minutes", 4) == "2"
    _gate_step(verify)
    _gate_script(verify)


def test_verify_binds_every_result_directly_to_its_predecessor(workflow: str) -> None:
    verify = _job_block(workflow, "verify")

    assert _result_bindings(verify) == EXPECTED_RESULT_BINDINGS


def test_required_ci_lanes_do_not_ignore_failures(workflow: str) -> None:
    for job_id in sorted(EXPECTED_PREDECESSORS | {"verify"}):
        job = _job_block(workflow, job_id)
        assert re.search(r"^\s*(?:-\s+)?continue-on-error:", job, re.MULTILINE) is None, job_id


def test_verify_accepts_all_success(bash: str, workflow: str, tmp_path: Path) -> None:
    script = _gate_script(_job_block(workflow, "verify"))
    results = dict.fromkeys(EXPECTED_RESULT_BINDINGS, "success")

    completed = _run_gate(bash, script, results, tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize("variable", EXPECTED_RESULT_BINDINGS)
def test_verify_rejects_any_non_success_lane(
    bash: str, workflow: str, tmp_path: Path, variable: str
) -> None:
    script = _gate_script(_job_block(workflow, "verify"))
    for value in (
        "failure",
        "cancelled",
        "skipped",
        "neutral",
        "",
        "unknown",
        " ",
        " success",
        "success ",
        "success\n",
    ):
        results = dict.fromkeys(EXPECTED_RESULT_BINDINGS, "success")
        results[variable] = value

        completed = _run_gate(bash, script, results, tmp_path)

        assert completed.returncode != 0, (
            f"Aggregate accepted {variable}={value!r}\n{completed.stdout}{completed.stderr}"
        )


@pytest.mark.parametrize("variable", EXPECTED_RESULT_BINDINGS)
def test_verify_rejects_missing_lane_result(
    bash: str, workflow: str, tmp_path: Path, variable: str
) -> None:
    script = _gate_script(_job_block(workflow, "verify"))
    results = dict.fromkeys(EXPECTED_RESULT_BINDINGS, "success")
    del results[variable]

    completed = _run_gate(bash, script, results, tmp_path)

    assert completed.returncode != 0, (
        f"Aggregate accepted unset {variable}\n{completed.stdout}{completed.stderr}"
    )
