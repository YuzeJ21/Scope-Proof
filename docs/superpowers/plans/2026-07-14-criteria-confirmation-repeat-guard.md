# Criteria Confirmation Repeat Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent unchanged criteria from being reconfirmed and invalidating a valid analysis bundle.

**Architecture:** Reuse the existing `criteria_edits_pending` derivation and `criteria_confirmed` session flag in the Streamlit button state. Keep the lifecycle transition unchanged so a real confirmed edit still creates a revision and invalidates stale analysis.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Keep `Confirm criteria` visible after confirmation and disable it only while the confirmed visible criteria are unchanged or any visible criterion is blank.
- Re-enable confirmation immediately after any valid visible criteria edit.
- Do not change lifecycle, revision, analysis, evidence, verdict, gate, schema, export, persistence, or release semantics.
- Do not introduce paid APIs, LLMs, billing, forks, organizations, private repositories, synthetic validation, notifications, or untrusted-code execution.

---

### Task 1: Guard unchanged repeated confirmation

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`
- Verify: `docs/superpowers/specs/2026-07-14-criteria-confirmation-repeat-guard-design.md`

**Interfaces:**
- Consumes: existing `criteria_edits_pending: bool` and `st.session_state["criteria_confirmed"]`.
- Produces: a disabled `confirm_criteria` button when no confirmable revision exists.

- [ ] **Step 1: Add the regression contract first**

Add an AppTest that reaches analyzed demo state and requires `Confirm criteria` to
be disabled while revision 1 and its analysis bundle remain authoritative. Edit one
criterion and require confirmation to re-enable without mutating authoritative state.

- [ ] **Step 2: Verify RED**

Run only the new test. Expected: it fails because unchanged confirmed criteria still
leave `confirm_criteria` enabled.

- [ ] **Step 3: Implement the minimal UI guard**

Change only the button's `disabled` expression to combine blank text with the
already-confirmed-and-unchanged condition.

- [ ] **Step 4: Verify GREEN and related behavior**

Run the new test plus the existing pending-text-edit and blank-edit tests. Require
the new guard to pass while valid edits still re-enable reconfirmation and blank edits
remain non-confirmable.

- [ ] **Step 5: Run complete product verification**

Run focused Ruff, `git diff --check`, repository-wide Ruff, complete offline pytest,
the deterministic benchmark, and a loopback Streamlit health check. Require 677
passing tests, one intentional live skip, 12 benchmark cases, 13 criteria, zero
mismatches, zero must-have False Ready, zero false blockers, exact health `ok`, and
no traceback.

- [ ] **Step 6: Commit and integrate**

Stage exactly the app, AppTest, design, and plan. Commit the implementation, push
`codex/criteria-confirmation-repeat-guard`, open one ready protected PR, require both
`verify` checks plus CodeQL, merge only at the reviewed head SHA, synchronize local
main, and require exact-main CI and CodeQL success. Do not create a release, issue
comment, label, reviewer request, or other notification.
