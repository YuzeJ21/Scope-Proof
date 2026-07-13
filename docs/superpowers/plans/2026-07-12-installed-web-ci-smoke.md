# Installed Web CI Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make protected CI execute the installed ScopeProof web entry point and require a healthy local Streamlit server.

**Architecture:** Append one bounded health smoke to the existing installed-wheel step. Linux process-group isolation plus an EXIT trap provides reliable cleanup; a loopback health poll proves the installed UI runtime starts without widening product claims.

**Tech Stack:** GitHub Actions Ubuntu shell, Streamlit health endpoint, curl, pytest repository contracts

## Global Constraints

- Run only the trusted ScopeProof wheel built from the checked-out branch.
- Never fetch or execute pull-request repository code.
- Bind only to `127.0.0.1` and run headlessly.
- Health is package-startup evidence only, not reviewed-PR runtime verification.
- Add no Action, service, account, API, dependency, release, or license.

---

### Task 1: Installed web health gate

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: installed `scopeproof-web`, Ubuntu `setsid`, curl, and `$RUNNER_TEMP`.
- Produces: a required `verify` failure when the installed local workbench cannot become healthy.

- [ ] **Step 1: Add the failing workflow contract**

Require `scopeproof-web`, all three Streamlit environment settings, the health URL and exact `ok` comparison, a 30-attempt loop, early-exit detection, process-group termination, log output, and cleanup trap.

- [ ] **Step 2: Verify RED**

Run `.venv/bin/python -m pytest tests/test_repository_contracts.py::test_ci_starts_and_cleans_up_installed_web_workbench -q`.

Expected: fail because the workflow does not contain `scopeproof-web`.

- [ ] **Step 3: Implement the minimal workflow extension**

Append the headless process-group launch, EXIT cleanup trap, bounded health poll, early-exit guard, exact response check, and failure log to the existing installed-wheel step.

- [ ] **Step 4: Verify GREEN and all local gates**

Run the focused contract, Ruff, full pytest, source benchmark, the existing local installed-wheel health reproduction, and `git diff --check`.

Expected: all pass; the local reproduction returns `health=ok` and leaves no listener.

- [ ] **Step 5: Publish through protected main**

Commit only the spec, plan, workflow, and contract; push the branch; open a ready PR; require both verify runs, evidence review, and CodeQL; merge normally; then require merged-main CI and CodeQL success. Do not create a release.
