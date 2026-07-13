# Installed Wheel CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the protected `verify` check build and execute ScopeProof's installed wheel.

**Architecture:** Extend the existing repository workflow contract, then append one smoke step to the current CI job. The smoke runs last, uses `$RUNNER_TEMP` for artifacts and execution, and reuses already-installed dependencies without adding services or Actions.

**Tech Stack:** GitHub Actions YAML, Python packaging, pytest

## Global Constraints

- Add no Actions, services, accounts, paid APIs, secrets, or dependencies.
- Do not change benchmark verdict rules or product runtime.
- Do not create a release for this CI-only change.
- Preserve deterministic, evidence-bound gate behavior.

---

### Task 1: Enforce and implement the installed-wheel smoke

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the existing `verify` job and installed `scopeproof` console command.
- Produces: a required CI step named `Installed wheel smoke` that executes the packaged benchmark.

- [ ] **Step 1: Write the failing workflow contract test**

Add a test that requires the step name, wheel build, force-install, temporary-directory execution, and installed benchmark command.

- [ ] **Step 2: Verify the contract fails for the missing smoke step**

Run: `.venv/bin/python -m pytest tests/test_repository_contracts.py::test_ci_builds_and_executes_installed_wheel -q`

Expected: one assertion failure because `.github/workflows/ci.yml` does not yet contain `Installed wheel smoke`.

- [ ] **Step 3: Add the minimal workflow step**

Append a shell step that creates `$RUNNER_TEMP/scopeproof-wheel`, builds the wheel there, selects the generated `scopeproof-*.whl`, force-installs it without dependencies, and runs `scopeproof benchmark` from `$RUNNER_TEMP`.

- [ ] **Step 4: Verify the focused contract passes**

Run: `.venv/bin/python -m pytest tests/test_repository_contracts.py::test_ci_builds_and_executes_installed_wheel -q`

Expected: `1 passed`.

- [ ] **Step 5: Reproduce the installed-wheel smoke locally**

Build into a fresh `/tmp` directory, install into a fresh virtual environment, assert the imported package path is inside that environment rather than the checkout, and run `scopeproof benchmark` from `/tmp`.

Expected: 12 cases, zero mismatches, zero False Ready outcomes, and zero false blockers.

- [ ] **Step 6: Run repository verification**

Run Ruff, the full pytest suite, the source benchmark, and `git diff --check`.

Expected: all checks pass with no formatting errors.

- [ ] **Step 7: Publish through protected main**

Commit the reviewed files, push a `codex/` branch, open a pull request, require `verify` and CodeQL to pass, merge without bypassing protection, and confirm merged-main checks pass.
