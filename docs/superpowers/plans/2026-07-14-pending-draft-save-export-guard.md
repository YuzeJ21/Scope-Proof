# Pending Criterion Draft Save and Export Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent local-save, export, and review-replacement paths from implying that unsubmitted criterion-detail inputs are part of the authoritative review.

**Architecture:** Detect non-default runtime-evidence or resolution widget state before global unsaved-state derivation. Consume successful form-reset markers first, then use the pending flag for replacement protection, summary truth, local-save readiness, and download readiness. Provide an explicit presentation-only clear action; never persist drafts.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Pending form values are not validated evidence or decisions and must never be auto-appended.
- Valid appended records remain the only form inputs eligible for local save and export.
- Do not change schemas, lifecycle services, gates, final acceptance, storage formats, or exporter contents.
- Do not introduce paid APIs, LLMs, billing, forks, organizations, private repositories, synthetic validation, notifications, or untrusted-code execution.

---

### Task 1: Make pending criterion drafts visible to persistence boundaries

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`
- Verify: `docs/superpowers/specs/2026-07-14-pending-draft-save-export-guard-design.md`

**Interfaces:**
- Consumes: existing runtime and resolution widget session keys, form-reset markers, local-save fingerprint, and replacement guard.
- Produces: one pending-draft Boolean used by replacement, summary, local Save, and three download buttons; plus an explicit clear action.

- [ ] **Step 1: Add regression contracts first**

Add AppTests for a saved review with pending runtime and resolution inputs, explicit
clear recovery, and a valid runtime submission. Require truthful captions, replacement
protection, disabled persistence actions while pending, no review mutation on clear,
and restored authoritative save/export readiness after clear or append.

- [ ] **Step 2: Verify RED**

Run only the new tests. Expected: pending inputs are currently ignored by saved-state,
replacement, and export readiness, and no clear control exists.

- [ ] **Step 3: Implement the minimal pending-state guard**

Split draft detection and form-specific clearing into presentation helpers. Consume
successful reset markers before global unsaved derivation. Apply the Boolean to the
existing replacement guard, summary captions, local-save button, and download buttons.
Add the clear control before target-specific form widgets render.

- [ ] **Step 4: Verify GREEN and adjacent behavior**

Run the new tests plus target-change, successful runtime reset, valid runtime append,
resolution append, save/reopen, local-save freshness, and export availability tests.
Run focused Ruff and `git diff --check`.

- [ ] **Step 5: Run complete product verification**

Run repository-wide Ruff, complete offline pytest, deterministic benchmark, and a
loopback Streamlit health check. Require all tests passing apart from the intentional
live skip, 12 benchmark cases, 13 criteria, zero mismatches, zero must-have False
Ready, zero false blockers, exact health `ok`, and no traceback.

- [ ] **Step 6: Commit and integrate**

Stage exactly the app, AppTests, design, and plan. Commit the implementation, push
`codex/pending-draft-save-export-guard`, open one ready protected PR, require both
`verify` checks plus CodeQL, merge only at the reviewed head SHA, synchronize local
main, and require exact-main CI and CodeQL success. Do not create a release, issue
comment, label, reviewer request, or other notification.
