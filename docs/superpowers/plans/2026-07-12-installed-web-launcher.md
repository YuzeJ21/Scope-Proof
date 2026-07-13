# Installed Web Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the packaged local Streamlit workbench directly launchable after installing the ScopeProof release wheel.

**Architecture:** A small launcher in `apps.web` resolves the packaged app resource and starts Streamlit with the current interpreter and no shell. A separate `scopeproof-web` entry point preserves the core/UI boundary; the release flow builds and verifies one v0.1.12 wheel from protected main.

**Tech Stack:** Python 3.11+, importlib.resources, subprocess, Streamlit, Hatchling, pytest

## Global Constraints

- Start only the packaged ScopeProof Streamlit application.
- Never execute reviewed pull-request code.
- Add no service, account, organization, billing, paid API, LLM API, license, or new GitHub Action.
- Runtime health proves only that the packaged application starts, not that a reviewed PR is correct.
- Publish exactly one v0.1.12 release after protected-main verification.

---

### Task 1: Packaged web launcher

**Files:**
- Create: `apps/web/launcher.py`
- Create: `tests/apps/test_web_launcher.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Produces: `apps.web.launcher.main() -> int` and the `scopeproof-web` console script.
- Consumes: packaged resource `apps/web/app.py`, current Python executable, and the installed Streamlit module.

- [ ] **Step 1: Write failing launcher and repository contracts**

Test that `main()` passes `[sys.executable, "-m", "streamlit", "run", APP_PATH]` to `subprocess.run(check=False)` and returns its exit code. Require the `scopeproof-web` entry point, version `0.1.12`, v0.1.12 wheel URL, and README command while preserving the core no-Streamlit-import contract.

- [ ] **Step 2: Verify RED**

Run `.venv/bin/python -m pytest tests/apps/test_web_launcher.py tests/test_repository_contracts.py -q`.

Expected: collection or assertion failure because the launcher and entry point do not exist.

- [ ] **Step 3: Implement the minimal launcher and documentation**

Create the resource-based launcher, register `scopeproof-web`, bump the version to 0.1.12, and update the user Quickstart to start the installed local workbench. Keep contributor setup unchanged.

- [ ] **Step 4: Verify GREEN and all repository gates**

Run the focused tests, Ruff, full pytest, source benchmark, and `git diff --check`.

Expected: all pass, with the existing deterministic Streamlit demo assertions still in the suite.

- [ ] **Step 5: Verify a clean wheel runtime**

Build a wheel into `/tmp`, install it into a fresh virtual environment, confirm both console scripts, run the installed benchmark outside the checkout, start `scopeproof-web` headlessly on an unused loopback port, and require `/_stcore/health` to return `ok` before terminating it.

- [ ] **Step 6: Publish through protected main**

Commit the scoped files, push the branch, open a ready PR, wait for required `verify`, evidence review, and CodeQL, merge normally, and confirm merged-main CI and CodeQL.

- [ ] **Step 7: Publish and verify v0.1.12**

Build from the exact main merge commit, create tag/release v0.1.12 with one wheel asset, redownload it through the public URL, compare SHA-256, rerun installed benchmark and health smoke, and confirm release target integrity.
