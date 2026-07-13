# Installed Version Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let both installed ScopeProof commands report their exact shared version without starting a review or Streamlit.

**Architecture:** Register standard argparse version actions in the existing CLI and web-launcher parsers. Both consume `scopeproof_core.version.__version__`; installed-wheel CI executes the real console scripts outside the checkout.

**Tech Stack:** Python 3.11+, argparse, pytest, Hatchling console scripts, GitHub Actions.

## Global Constraints

- Exact development outputs are `scopeproof 0.1.15.dev0` and `scopeproof-web 0.1.15.dev0`.
- The web version path must not resolve or launch Streamlit.
- Existing review, gate, evidence, persistence, launcher, and help behavior remains unchanged.
- No dependency, network call, external service, release, billing, or untrusted-code execution is added.

---

### Task 1: Add version actions to both parsers

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `apps/web/launcher.py`
- Test: `tests/cli/test_cli.py`
- Test: `tests/apps/test_web_launcher.py`

**Interfaces:**
- Consumes: `scopeproof_core.version.__version__: str`
- Produces: `scopeproof --version` and `scopeproof-web --version`

- [ ] **Step 1: Write failing parser tests**

In `tests/cli/test_cli.py`, add:

```python
def test_cli_reports_shared_version_without_a_subcommand(capsys) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == f"scopeproof {__version__}\n"
```

In `tests/apps/test_web_launcher.py`, import `__version__` and add:

```python
def test_web_launcher_reports_shared_version_without_starting_streamlit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unexpected_run(*args, **kwargs):
        raise AssertionError("Streamlit must not start for --version")

    monkeypatch.setattr(launcher.subprocess, "run", unexpected_run)

    with pytest.raises(SystemExit) as raised:
        launcher.main(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == f"scopeproof-web {__version__}\n"
```

- [ ] **Step 2: Run both tests and verify RED**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/cli/test_cli.py::test_cli_reports_shared_version_without_a_subcommand \
  tests/apps/test_web_launcher.py::test_web_launcher_reports_shared_version_without_starting_streamlit -q
```

Expected: both fail with argparse exit code 2 because `--version` is unavailable.

- [ ] **Step 3: Register the minimal argparse actions**

Import `__version__` in both production modules. In `scopeproof_core.cli._parser`, immediately after
constructing the parser, add:

```python
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
```

In `apps.web.launcher._parser`, add:

```python
    parser.add_argument(
        "--version",
        action="version",
        version=f"scopeproof-web {__version__}",
    )
```

Use the explicit launcher program name because direct module execution otherwise reports
`launcher.py`, while the public installed command is `scopeproof-web`.

- [ ] **Step 4: Run both tests and verify GREEN**

Run the command from Step 2.

Expected: `2 passed`.

- [ ] **Step 5: Run complete CLI and launcher regressions**

Run:

```bash
../../.venv/bin/python -m pytest tests/cli/test_cli.py tests/apps/test_web_launcher.py -q
../../.venv/bin/python -m ruff check scopeproof_core/cli.py apps/web/launcher.py \
  tests/cli/test_cli.py tests/apps/test_web_launcher.py
```

Expected: all selected tests and Ruff pass.

- [ ] **Step 6: Commit the parser behavior**

```bash
git add scopeproof_core/cli.py apps/web/launcher.py \
  tests/cli/test_cli.py tests/apps/test_web_launcher.py
git commit -m "feat: report installed ScopeProof version"
```

### Task 2: Verify real installed console scripts

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: installed `scopeproof` and `scopeproof-web` console scripts
- Produces: protected CI proof that both scripts report the built distribution version

- [ ] **Step 1: Add failing workflow contract assertions**

Extend `test_ci_builds_and_executes_installed_wheel`:

```python
    assert "scopeproof --version" in workflow
    assert "scopeproof-web --version" in workflow
```

Run that test and confirm it fails because neither command is in the workflow.

- [ ] **Step 2: Execute both installed commands in the wheel smoke**

After the existing Python provenance assertion in `.github/workflows/ci.yml`, add:

```yaml
          (cd "$RUNNER_TEMP" && scopeproof --version)
          (cd "$RUNNER_TEMP" && scopeproof-web --version)
```

These commands run outside the checkout after force-installing the built wheel. The web command
must exit before the later health-check block starts Streamlit normally.

- [ ] **Step 3: Run the workflow contract and verify GREEN**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_ci_builds_and_executes_installed_wheel -q
```

Expected: `1 passed`.

- [ ] **Step 4: Build, install, and execute both real scripts locally**

Build a wheel into `/tmp/scopeproof-version-command-wheel`, install it into a new temporary virtual
environment, change directory to `/tmp`, and run:

```bash
scopeproof --version
scopeproof-web --version
```

Expected exact outputs:

```text
scopeproof 0.1.15.dev0
scopeproof-web 0.1.15.dev0
```

- [ ] **Step 5: Commit installed-command coverage**

```bash
git add .github/workflows/ci.yml tests/test_repository_contracts.py
git commit -m "ci: smoke installed version commands"
```

### Task 3: Verify and publish the bounded slice

**Files:**
- Verify: all changed source, tests, docs, and installed wheel
- Publish: `codex/version-diagnostics`

**Interfaces:**
- Consumes: completed parser and installed-wheel work
- Produces: protected-main installed-version diagnostics without a release

- [ ] **Step 1: Run all local gates**

Run Ruff, the full offline pytest suite, the 12-case deterministic benchmark, a clean wheel build
and installed console-script smoke, and `git diff --check`.

Expected: zero lint/test/build failures, only the intentional live-network skip, zero benchmark
mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 2: Review scope**

Confirm only parser version actions, their tests, installed-wheel smoke, design, and plan changed.
Confirm no review schema, gate, evidence, dependency, release, license, billing, or external write.

- [ ] **Step 3: Publish through one protected PR**

Push once, open one ready PR, wait for `verify`, CodeQL, and ScopeProof evidence review, and merge
only when green. Do not create a release, issue, comment, or label.

- [ ] **Step 4: Verify main and continue**

Verify the merge SHA and post-merge main CI/CodeQL, remove the feature worktree and branches,
synchronize local main, then immediately audit the next evidence-backed adoption-readiness gap.
