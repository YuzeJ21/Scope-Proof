# Criteria Edit Error-Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover safely and atomically when a validated criteria edit cannot be applied.

**Architecture:** Add one Streamlit-layer helper that evaluates a criteria-edit callback before
publishing session state. Route add, split, remove, and reorder handlers through it while leaving
the core criteria service unchanged.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic v2, pytest, Ruff.

## Global Constraints

- Users must confirm normalized acceptance criteria before analysis.
- Failure preserves the exact existing review, bundle, criteria, and user-entered edit.
- Failure copy is fixed and contains no raw exception text or local paths.
- Success behavior and operation-specific success copy remain unchanged.
- Catch `ValueError` only and keep the core independent from Streamlit.

---

### Task 1: Regression-first criteria edit recovery

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: the four existing criteria service functions and Streamlit button keys.
- Produces: a parameterized regression contract for failed add, split, remove, and reorder edits.

- [ ] **Step 1: Add the failing AppTest**

Add a parameterized test that starts from an analyzed demo, explicitly enables unsaved-review
replacement, prepares the operation-specific input, and patches the selected criteria service
function to raise a path-bearing `ValueError`. Require the fixed copy, no `app.exception`, no raw
details, exact review/bundle/criteria preservation, retained input text, and an enabled retry
button.

- [ ] **Step 2: Run the regression test and verify RED**

Run:

```bash
"/Users/yjian070/Documents/New project 2/.venv/bin/python" -m pytest \
  tests/apps/test_streamlit_app.py -q -k criteria_edit_failure
```

Expected: four failures because the current handlers expose the injected exception.

### Task 2: Atomic Streamlit recovery

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: a zero-argument callable returning `list[Criterion]` and an operation-specific success
  message.
- Produces: `_apply_criteria_update(operation, success_message) -> None`.

- [ ] **Step 1: Implement the minimal helper**

The helper must call the operation inside `try`, catch only `ValueError`, and render the exact
fixed failure copy. In `else`, assign the candidate criteria, call `_reset_analysis`, render the
provided success message, and rerun.

- [ ] **Step 2: Route all four handlers through the helper**

Use immediate lambdas for add, split, remove, and reorder so each candidate is computed before any
session mutation. Preserve the existing success strings exactly.

- [ ] **Step 3: Verify GREEN and adjacent behavior**

Run:

```bash
"/Users/yjian070/Documents/New project 2/.venv/bin/python" -m pytest \
  tests/apps/test_streamlit_app.py -q -k \
  'criteria_edit_failure or criteria_can_be_added or compound_criterion_can_be_split or pending_criterion or criteria_confirmation_failure'
"/Users/yjian070/Documents/New project 2/.venv/bin/python" -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: all selected tests and Ruff pass.

### Task 3: Complete verification and branch handoff

**Files:**
- Verify: the complete repository, built wheel, and installed local workbench.

**Interfaces:**
- Consumes: the completed Streamlit and regression changes.
- Produces: one reviewed local commit ready to integrate after its parent chain.

- [ ] **Step 1: Run repository-wide verification**

Run Ruff, the complete offline pytest suite, `python -m scopeproof_core.evals.runner`, and
`git diff --check`. Require zero lint/test failures, only the intentional live skip, 12 executed
benchmark cases, 13 executed criteria, zero mismatches, zero must-have False Ready, and zero false
blockers.

- [ ] **Step 2: Verify a clean installed wheel**

Build `scopeproof 0.1.19.dev0` into `/tmp`, install it with dependencies in a fresh virtual
environment, require `pip check`, rerun the installed benchmark, and require the same safety
metrics.

- [ ] **Step 3: Verify packaged runtime health**

Start the installed `scopeproof-web` with a fresh temporary `HOME` on an unused loopback port,
require `/_stcore/health` to return exactly `ok`, stop the process, and reject any traceback.

- [ ] **Step 4: Review and commit**

Require the diff to contain only `apps/web/app.py`, `tests/apps/test_streamlit_app.py`, and these
two documents. Commit on `codex/criteria-edit-error-recovery`, keep it unpushed while its parent
chain is pending, and do not create comments, labels, reviewers, releases, or notifications.
