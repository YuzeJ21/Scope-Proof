# CLI Error Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give installed CLI users concise, safe errors for expected input and domain failures while documenting the proven public-PR workflow.

**Architecture:** Catch only expected exception families around parsed command handlers and delegate formatting to `ArgumentParser.error()`. Keep domain exception definitions and unexpected traceback behavior unchanged.

**Tech Stack:** Python 3.11+, argparse, pytest, Hatchling wheel, pip.

## Global Constraints

- Catch `GitHubIngestionError`, `OSError`, and `ValueError`; do not catch arbitrary `Exception`.
- Expected CLI failures exit with status 2 and contain no traceback.
- Add no GitHub write, paid API, dependency, credential persistence, evidence rule, or gate change.
- Requirements remain reviewer-authored and explicitly confirmed before analysis.

---

### Task 1: Expected CLI errors

**Files:**
- Modify: `scopeproof_core/cli.py:1-185`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `GitHubIngestionError`, `OSError`, and `ValueError` raised by command handlers.
- Produces: `SystemExit(2)` with standard argparse stderr for expected failures.

- [ ] **Step 1: Write failing tests**

Add one test that supplies a valid temporary requirements file with an invalid PR URL, and one test that supplies a missing requirements path. Each must assert `SystemExit.value.code == 2`, `"scopeproof: error:"` in stderr, the useful domain message in stderr, and `"Traceback"` absent.

- [ ] **Step 2: Verify RED**

Run the two focused tests. Expected: handlers raise their original exceptions instead of `SystemExit(2)`.

- [ ] **Step 3: Implement the CLI boundary**

Import `GitHubIngestionError`, retain `parser = _parser()`, parse args, execute the handler inside `try`, and call `parser.error(str(error))` for `(GitHubIngestionError, OSError, ValueError)`.

- [ ] **Step 4: Verify GREEN**

Run the two focused tests and all `tests/cli/test_cli.py`. Expected: all pass.

### Task 2: Installed public-PR operator guidance

**Files:**
- Modify: `README.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: the proven `scopeproof review` and `scopeproof export` commands.
- Produces: a README workflow that keeps confirmation, token, storage, and evidence boundaries explicit.

- [ ] **Step 1: Write a failing repository contract**

Require the README to contain `scopeproof review --pr`, `--requirements requirements.txt`, `scopeproof export`, and language stating that criteria are reviewer-confirmed and the optional token is not persisted.

- [ ] **Step 2: Verify RED**

Run the focused repository contract. Expected: FAIL because the README lacks the CLI workflow.

- [ ] **Step 3: Add the README workflow**

Document creating `requirements.txt`, running a public PR review into `.scopeproof/reviews`, reading the returned review ID, and exporting Markdown. State that the operation is read-only, criteria must be explicitly confirmed first, and the optional token is not required or stored.

- [ ] **Step 4: Verify GREEN**

Run the focused contract and full repository contracts. Expected: PASS.

### Task 3: Artifact and regression verification

**Files:**
- No additional repository files.

**Interfaces:**
- Consumes: a wheel built from the branch.
- Produces: clean-install evidence for success and failure paths.

- [ ] **Step 1: Run full source gates**

Run Ruff, full offline pytest, benchmark, and diff check.

- [ ] **Step 2: Build and install a fresh wheel**

Install the wheel in a new temporary environment, outside the repository.

- [ ] **Step 3: Replay source-owner-confirmed PR #22**

Use its two committed design requirements, validate the saved record through `JsonReviewStore`, and export JSON, Markdown, CSV, and HTML.

- [ ] **Step 4: Verify clean installed errors**

Run an invalid PR URL and missing requirements file. Expected: exit 2, concise error text, no traceback.

- [ ] **Step 5: Commit**

Stage `scopeproof_core/cli.py`, `tests/cli/test_cli.py`, `README.md`, `tests/test_repository_contracts.py`, and this plan; commit as `fix: make CLI failures actionable`.
