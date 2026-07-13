# Honest Workflow Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ScopeProof's unreachable five-step current marker with derived, immediately accurate milestone status and criterion-specific control labels.

**Architecture:** Remove mutable `active_step` state and render `Review status` at the end of the Streamlit script so it observes action results from the same run. Derive milestone copy only from existing authoritative session values, while preserving all core review and widget keys.

**Tech Stack:** Python 3.11+, Streamlit AppTest, pytest, Ruff, Chrome runtime screenshots.

## Global Constraints

- Do not change criteria parsing, confirmation, retrieval, findings, resolutions, gate evaluation, storage, exports, or demo labels.
- Use visible `Complete —`, `Next —`, and `Locked —` text rather than symbol-only state.
- Keep all existing Streamlit widget keys unchanged.
- Do not add CSS, JavaScript, dependencies, paid services, or synthetic review decisions.
- Do not claim accessibility compliance.

---

### Task 1: Derived workflow milestone status

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `snapshot`, `criteria`, `criteria_confirmed`, `bundle`, and `review_state` from `st.session_state`.
- Produces: a sidebar headed `Review status` with milestone text derived after action handlers run.

- [ ] **Step 1: Write failing AppTest regressions**

Add one test that loads the demo, confirms criteria, and asserts sidebar markdown includes
`Complete — Criteria confirmed` and `Next — Run deterministic analysis` in that same run. Add a
second test that runs analysis and asserts `Complete — Analysis generated` and
`Complete — Review and export available`. Assert `active_step` is absent from session state.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/apps/test_streamlit_app.py -q`

Expected: failures because the app still renders `Review workflow`, stores `active_step`, and shows
circle markers rather than derived milestone text.

- [ ] **Step 3: Implement the minimal derived sidebar**

Remove `active_step` from defaults and all assignments. Move the sidebar rendering block to the end
of `apps/web/app.py`. Render five stable milestone lines whose text is selected from authoritative
state after handlers have completed. Treat review/detail/export as available only when `bundle` is
not `None`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/apps/test_streamlit_app.py -q`

Expected: all Streamlit AppTest cases pass with no uncaught exceptions.

### Task 2: Criterion-specific accessible control names

**Files:**
- Modify: `tests/apps/test_web_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: each `criterion.criterion_id` in the existing criteria-edit loop.
- Produces: visible unique labels while preserving keys such as `criterion_priority_AC-01` and
  `remove_AC-01`.

- [ ] **Step 1: Write a failing source contract**

Assert app source contains `f"Priority for {criterion.criterion_id}"`,
`f"Required evidence for {criterion.criterion_id}"`, `f"Remove {criterion.criterion_id}"`, and
`f"Move {criterion.criterion_id} up"`; assert the old bare button labels are absent from the
criterion-edit block.

- [ ] **Step 2: Run the source contract and verify RED**

Run: `.venv/bin/python -m pytest tests/apps/test_web_app.py -q`

Expected: failure because current controls use generic labels.

- [ ] **Step 3: Apply criterion-specific labels**

Change only the visible label argument for priority, evidence level, remove, and move-up controls.
Do not change options, handlers, or keys.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/apps/test_web_app.py tests/apps/test_streamlit_app.py -q`

Expected: all focused tests pass.

- [ ] **Step 5: Commit the bounded implementation**

```bash
git add apps/web/app.py tests/apps/test_web_app.py tests/apps/test_streamlit_app.py
git commit -m "fix: show honest review milestones"
```

### Task 3: Runtime and publication verification

**Files:**
- Verify only; no planned source edits.

**Interfaces:**
- Consumes: the exact branch and later protected-main commits.
- Produces: AppTest, full-suite, benchmark, browser DOM, screenshot, CI, and GitHub state evidence.

- [ ] **Step 1: Run all local gates**

Run Ruff, full pytest, deterministic benchmark, `git diff --check`, and clean-tree inspection.
Expected: no lint errors; all tests pass; 12 cases with zero mismatch, zero False Ready, and zero
false blocker.

- [ ] **Step 2: Re-run the local Chrome flow**

Reload the local app, load the demo, confirm criteria, and run analysis. Capture fresh screenshots
at confirmation and export. Require the DOM to show accurate milestone copy in the same run and
criterion-specific control names. Compare against audit screenshots 03 and 07.

- [ ] **Step 3: Publish through protected main**

Push `codex/honest-workflow-status`, open a ready PR, and wait for both `verify` checks, evidence
review, and CodeQL. Merge normally only if all pass, then wait for exact merged-main CI, CodeQL, and
dependency graph success.

- [ ] **Step 4: Reconcile without release churn**

This UI-only fix does not change package version or release install contract. Do not publish a new
release unless verification proves the existing wheel guidance became inaccurate. Require zero open
PRs, only main remote branch, latest release v0.1.14, ignored notifications, required `verify`,
SHA-pinned Actions, and zero open security or dependency alerts.
