# Sidebar Step Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the persistent review-status sidebar a keyboard-accessible navigation path through
the available ScopeProof workflow steps.

**Architecture:** Add one Streamlit-only Markdown link helper and route each sidebar status through
it with a stable existing anchor when available. Preserve locked statuses as plain Markdown text.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff, in-app browser.

## Global Constraints

- Visible status wording, order, and prerequisite semantics remain unchanged.
- Available and next steps use existing stable heading anchors.
- Locked steps remain plain non-interactive text.
- No core, gate, lifecycle, schema, persistence, export, workflow, or version change.

---

### Task 1: Regression-first sidebar navigation contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: the existing AppTest helpers and `app.sidebar.markdown` values.
- Produces: exact navigation contracts for blank, criteria-ready, confirmed, and analyzed states.

- [x] **Step 1: Add failing tests**

Require the initial source next action to equal
`[Next — Load a public PR or demo](#1-start-review)` while all locked entries remain plain text.
Require a loaded demo to link source, prepared criteria, and confirmation next action. Require a
confirmed demo to link the analysis next action. Require an analyzed demo to link the Evidence
Matrix while keeping the unreliable deep Summary & Export fragment as plain status text.

- [x] **Step 2: Verify RED**

Run:

```bash
"/Users/yjian070/Documents/New project 2/.venv/bin/python" -m pytest \
  tests/apps/test_streamlit_app.py -q -k sidebar_step_navigation
```

Expected: failures because current sidebar statuses are plain text.

### Task 2: Deterministic sidebar anchors

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: status text plus an optional fragment anchor.
- Produces: `_render_sidebar_step(text: str, anchor: str | None = None) -> None`.

- [x] **Step 1: Implement the minimal renderer**

Render `[text](anchor)` when an anchor is supplied and render `text` unchanged otherwise.

- [x] **Step 2: Apply the approved mapping**

Replace the five direct sidebar `st.markdown` calls with explicit status calculation and helper
calls. Do not link any `Locked` state.

- [x] **Step 3: Verify GREEN and adjacent states**

Run the new tests, all existing sidebar-focused AppTests, Ruff on the two changed Python files, and
`git diff --check`.

### Task 3: Complete verification and browser proof

**Files:**
- Verify: complete repository, built wheel, and installed workbench.

**Interfaces:**
- Consumes: the completed sidebar implementation.
- Produces: a protected-PR-ready commit with runtime navigation evidence.

- [x] **Step 1: Run repository-wide verification**

Require Ruff success, the complete offline suite with only the intentional live skip, the
12-case/13-criterion benchmark with zero mismatches, zero must-have False Ready, and zero false
blockers, plus a clean diff check.

- [x] **Step 2: Verify packaging and local health**

Build and install a fresh `scopeproof 0.1.19.dev0` wheel in `/tmp`, require `pip check`, rerun the
installed benchmark, and require the installed workbench health endpoint to return exact `ok`.

- [x] **Step 3: Verify browser navigation**

Capture the sidebar after analysis, click its Evidence Matrix link using its visible name, and
require the URL fragment `#3-evidence-matrix` with the corresponding heading visible. Confirm the
deep Summary & Export status stays plain text because its Streamlit fragment navigation is not
reliable. Save and inspect the screenshot.

- [ ] **Step 4: Commit and protected integration**

Commit only the app, regression tests, design, and plan on `codex/sidebar-step-navigation`. Push,
open a protected PR, require verify and exact-head CodeQL, then merge only when both are green. Do
not add comments, labels, reviewers, releases, or optional notification activity.
