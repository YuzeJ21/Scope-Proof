# Evidence Matrix Hierarchy Implementation Plan

**Goal:** Turn the evidence matrix into a compact overview and keep deep evidence facts in
Criterion Detail without changing review semantics.

**Architecture:** Change only the Streamlit presentation and its AppTests. Continue to derive every
displayed value from the validated `ReviewBundle`; no core or schema changes are needed.

**Tech stack:** Python, Streamlit AppTest, pytest, Ruff, Hatch wheel build.

---

### Task 1: Lock the compact-overview contract with a failing test

**Files:**

- Modify: `tests/apps/test_streamlit_app.py`

Add an analyzed-demo test that requires:

- the matrix header to contain exactly Criterion, Requirement, Priority, Status, Evidence, and
  Human resolution;
- Confidence, Count, and Concern not to be matrix columns;
- the selected detail to show `Required evidence`, `Observed evidence`, `Confidence`,
  `Candidates`, and `Human resolution`;
- the selected finding reason to remain visible;
- the former unlabelled duplicate criterion summary not to be rendered.

Run the focused test and observe failure against the nine-column implementation.

### Task 2: Implement the hierarchy change

**Files:**

- Modify: `apps/web/app.py`

Limit matrix row construction and headers to the six overview fields. Remove the repeated bold row
loop. In Criterion Detail, derive the selected resolution label and render one compact facts line
before the existing provisional reason.

Run the focused test until green, then run all Streamlit AppTests.

### Task 3: Verify source and deterministic behavior

Run:

```bash
python -m ruff check .
python -m pytest -q
python -m scopeproof_core.evals.runner
git diff --check
```

Require zero lint errors, all offline tests passing, 12 benchmark cases and 13 criteria executed,
zero mismatches, zero must-have False Ready, and zero false blockers.

### Task 4: Verify the packaged product

Build exactly one `scopeproof-0.1.16.dev0` wheel in a fresh temporary directory and install it into
a fresh virtual environment with declared dependencies. Require:

- distribution, imported module, both console scripts, and a new Review to report
  `0.1.16.dev0`;
- `pip check` clean;
- installed benchmark 12 cases, 13 criteria, zero mismatches, zero must-have False Ready, zero
  false blockers;
- packaged workbench health endpoint exactly `ok`.

### Task 5: Browser comparison and protected integration

Load the deliberately constructed demo, confirm criteria, and run deterministic analysis in the
packaged workbench at 1280 by 720. Capture the compact matrix and selected detail. Compare the
matrix beside the source screenshot, verify no clipping or collision, inspect the DOM and current
console errors, and record the controlled-product-evidence limitations.

Commit only the design, plan, application, and regression-test files. Push a `codex/` branch, open
a ready PR, wait for all PR checks, merge through protected main, wait for merged-main CI and
CodeQL, synchronize local main, and remove the owned worktree and merged branch. Do not create a
release, issue comment, reviewer request, billing, fork, synthetic evidence, or notification-only
activity.
