# Evidence Matrix Filter Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the accepted blocker, status, priority, and evidence-level matrix filtering workflow.

**Architecture:** Add presentation-only Streamlit controls and apply them in the existing matrix row loop using validated gate and finding fields. Preserve every domain object unchanged.

**Tech Stack:** Python 3.11+, Streamlit, Pydantic enums, pytest AppTest, Ruff.

## Global Constraints

- Filter only from `GateDecision.blocking_criteria` and `Finding.evidence_level`.
- Combine active filters with AND semantics.
- Do not mutate evidence, findings, resolutions, or gate state.

---

### Task 1: Add failing filter regressions

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `bundle.gate.blocking_criteria`, `finding.evidence_level`.
- Produces: `blocking_only` checkbox, `evidence_level_filter` multiselect, deterministic filtered matrix.

- [ ] **Step 1: Write failing AppTests**

Require the new controls, filter the demo to blocking rows, filter to E2 rows, combine E2 with blocking,
and select an empty combination to require the recovery message.

- [ ] **Step 2: Verify RED**

Run: `/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest tests/apps/test_streamlit_app.py -q`

Expected: missing-widget failures because neither control exists.

- [ ] **Step 3: Implement minimal controls and predicates**

Add the checkbox and enum multiselect after existing filters. In the matrix loop, skip non-blocking
criteria when checked and skip evidence levels not selected. Show the explicit empty state when
`matrix` is empty.

- [ ] **Step 4: Verify GREEN and lint**

Run focused AppTests and Ruff on the changed files. Expected: all pass.

### Task 2: Verify and publish

**Files:**
- Verify all changed files; no additional production files expected.

**Interfaces:**
- Produces: protected merged change with post-main CI and CodeQL evidence.

- [ ] **Step 1: Run broad gates**

Run Ruff, full pytest, deterministic benchmark, and `git diff --check`. Require 12 benchmark cases,
zero must-have False Ready, zero False Blocker, and no mismatches.

- [ ] **Step 2: Run installed runtime smoke**

Build and install the wheel, start `scopeproof-web` on loopback, require health `ok`, and rerun focused
AppTests for the two controls and combined/empty behavior without saving synthetic evidence.

- [ ] **Step 3: Publish protected PR**

Review `main...HEAD`, push `codex/matrix-filters`, open one PR, wait for required verify and CodeQL,
merge only when green, then confirm post-main checks and clean the owned worktree.
