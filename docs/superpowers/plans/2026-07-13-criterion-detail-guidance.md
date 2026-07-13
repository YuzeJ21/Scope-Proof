# Criterion Detail Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give reviewers explicit criterion-specific recovery guidance and auditable candidate-evidence provenance.

**Architecture:** Render existing validated `Finding` and `EvidenceItem` fields in the current Streamlit Criterion Detail section. Keep all domain state and calculations unchanged.

**Tech Stack:** Python 3.11+, Streamlit, Pydantic models, pytest AppTest, Ruff.

## Global Constraints

- Label implementation and test matches as candidate evidence.
- Never represent candidate evidence as runtime verification.
- Render only stored fields; do not infer or generate new evidence.

---

### Task 1: Lock the detail contract with failing AppTests

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `Finding.recommended_action`, `Finding.evidence_ids`, `EvidenceItem.relevance_reason`, `EvidenceItem.matching_rule`, `EvidenceItem.limitations`.
- Produces: labeled recovery and candidate-provenance content in Criterion Detail.

- [ ] **Step 1: Write failing regressions**

For AC-01, require `Recommended next action`, its exact stored value, `Candidate evidence`, `Matching
rationale`, `Matching rule`, immutable evidence link, excerpt, and limitation. For AC-03, require its
exact stored action and the no-candidate empty state.

- [ ] **Step 2: Verify RED**

Run: `/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest tests/apps/test_streamlit_app.py -q`

Expected: failures for the missing guidance and labels.

- [ ] **Step 3: Implement minimal rendering**

Add the guidance and Candidate evidence blocks immediately after missing-evidence details. Label
rationale and rule within the existing expanders; retain code, link, and limitation rendering.

- [ ] **Step 4: Verify GREEN and lint**

Run focused AppTests and Ruff on both changed files. Expected: all pass.

### Task 2: Verify visually and publish

**Files:**
- Verify all changed files; no additional production files expected.

**Interfaces:**
- Produces: protected merged change with before/after audit evidence and post-main checks.

- [ ] **Step 1: Run broad gates**

Run Ruff, full pytest, deterministic benchmark, and `git diff --check`. Require 12 benchmark cases,
zero must-have False Ready, zero False Blocker, and no mismatches.

- [ ] **Step 2: Run installed and browser verification**

Build and install the wheel, start Streamlit on loopback, require health `ok`, navigate the demo to
AC-01 and AC-03, and capture same-state after screenshots. Do not save runtime evidence, resolutions,
or final acceptance.

- [ ] **Step 3: Publish protected PR**

Review `main...HEAD`, push `codex/criterion-guidance`, open one PR, wait for all required verify and
CodeQL checks, merge only when green, then confirm post-main checks and clean the owned worktree.
