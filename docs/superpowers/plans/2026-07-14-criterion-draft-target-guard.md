# Criterion Draft Target Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent unsaved runtime-evidence and human-resolution inputs from being recorded against a different review criterion after the detail target changes.

**Architecture:** Derive a session-only target token from active review identity, head SHA, criteria revision, and selected criterion. Before rendering target-specific forms, clear any pending form inputs when that token changes and show a recovery notice only when a real draft was discarded. Persisted models and lifecycle services remain unchanged.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Never silently retarget human-supplied runtime observations or resolutions.
- Never modify already appended evidence or resolution events.
- Keep schemas, lifecycle, gates, final acceptance, persistence, exports, and core/UI separation unchanged.
- Do not introduce paid APIs, LLMs, billing, forks, organizations, private repositories, synthetic validation, GitHub notifications, or untrusted-code execution.

---

### Task 1: Reset pending criterion-detail drafts when their target changes

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`
- Verify: `docs/superpowers/specs/2026-07-14-criterion-draft-target-guard-design.md`

**Interfaces:**
- Consumes: `ReviewState.review.review_id`, `Review.head_sha`, `criteria_revision.number`, `selected_id`, and known Streamlit form keys.
- Produces: cleared target-specific draft state, disabled save actions, and one recovery notice after a draft-bearing target change.

- [ ] **Step 1: Add the regression contracts first**

Add one AppTest that fills both target-specific forms for AC-01, changes to AC-03,
and requires all inputs cleared, both saves disabled, no appended runtime evidence or
resolution event, and one notice naming AC-03. Add a second AppTest proving a clean
target change shows no discard notice.

- [ ] **Step 2: Verify RED**

Run only the new tests. Expected: the draft-bearing test fails because the current UI
preserves the fields and leaves both actions enabled after the target changes.

- [ ] **Step 3: Implement the target guard**

Add a presentation-only draft detector/reset helper. Derive and compare the target
token immediately after the criterion selector and before form widgets render. Reset
only transient widget state and emit the notice only when pending input existed.

- [ ] **Step 4: Verify GREEN and adjacent contracts**

Run the new tests plus existing runtime-context, runtime-save, resolution-context,
manual-verification, and successful-form-reset tests. Run focused Ruff and
`git diff --check`.

- [ ] **Step 5: Run complete product verification**

Run repository-wide Ruff, complete offline pytest, deterministic benchmark, and a
loopback Streamlit health check. Require all tests passing apart from the intentional
live skip, 12 benchmark cases, 13 criteria, zero mismatches, zero must-have False
Ready, zero false blockers, exact health `ok`, and no traceback.

- [ ] **Step 6: Commit and integrate**

Stage exactly the app, AppTests, design, and plan. Commit the implementation, push
`codex/criterion-draft-target-guard`, open one ready protected PR, require both
`verify` checks plus CodeQL, merge only at the reviewed head SHA, synchronize local
main, and require exact-main CI and CodeQL success. Do not create a release, issue
comment, label, reviewer request, or other notification.
