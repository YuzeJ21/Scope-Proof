# Evidence Matrix Contract Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display every accepted evidence-matrix field consistently on screen and in every human-readable export.

**Architecture:** Derive presentation values directly from validated `Criterion`, `Finding`, and current `HumanResolution` objects in the existing Streamlit and exporter loops. Do not add schemas or mutate domain state.

**Tech Stack:** Python 3.11+, Pydantic models, Streamlit, csv, HTML/Markdown renderers, pytest AppTest, Ruff.

## Global Constraints

- Count only `Finding.evidence_ids`; do not count manual runtime evidence.
- Render `Finding.reason` as concern without changing finding semantics.
- Keep provisional findings visually separate from human resolutions.
- Preserve deterministic, local-first behavior and never execute PR code.

---

### Task 1: Lock the UI matrix contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `ReviewBundle.findings`, `ReviewBundle.resolutions`, `Finding.evidence_ids`.
- Produces: one Markdown matrix containing `Count`, `Concern`, and `Human resolution` columns.

- [ ] **Step 1: Write the failing AppTest regression**

Extend `test_evidence_matrix_renders_as_one_markdown_table` to require the complete header, the demo
concern, the candidate evidence count, and `Unresolved` before a resolution is recorded. Add a second
assertion after `append_resolution` through the UI that the current decision appears.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest tests/apps/test_streamlit_app.py -q`

Expected: failure because the three required columns are absent.

- [ ] **Step 3: Implement the minimal UI rendering**

Create `resolution_by_id`, add `Count`, `Concern`, and `Human resolution` values to each matrix row,
and extend `table_headers`. Reuse the existing table-cell escaping.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: all Streamlit AppTests pass.

### Task 2: Lock export parity

**Files:**
- Modify: `tests/reporting/test_exporters.py`
- Modify: `scopeproof_core/reporting/exporters.py`

**Interfaces:**
- Consumes: the same validated finding and current-resolution fields as Task 1.
- Produces: complete matrix fields in Markdown, CSV, and HTML; JSON remains unchanged.

- [ ] **Step 1: Write failing exporter regressions**

Require confidence, evidence count, concern, and current human resolution in human-readable formats;
parse CSV to assert `evidence_count` and `concern`; add one bundle with runtime evidence but no static
evidence to prove runtime evidence is excluded; add HTML concern escaping coverage.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest tests/reporting/test_exporters.py -q`

Expected: failures only for missing matrix values and columns.

- [ ] **Step 3: Implement minimal exporter rendering**

Extend Markdown/HTML matrices and the CSV field list/row mapping from existing model values. Escape
HTML and retain the current Markdown table escaping convention.

- [ ] **Step 4: Run focused tests and Ruff**

Run focused pytest plus `python -m ruff check apps/web/app.py scopeproof_core/reporting/exporters.py tests/apps/test_streamlit_app.py tests/reporting/test_exporters.py`.

Expected: all pass.

### Task 3: Verify and publish

**Files:**
- Verify all changed files; no additional production files expected.

**Interfaces:**
- Produces: protected, merged GitHub change with post-main verification evidence.

- [ ] **Step 1: Run broad local gates**

Run Ruff, full pytest, deterministic benchmark, and `git diff --check`. Expected: clean, 12 benchmark
cases, zero must-have False Ready, zero False Blocker, and no mismatches.

- [ ] **Step 2: Verify real distribution and UI behavior**

Build and force-install the wheel, run one deterministic fixture review, export JSON/Markdown/CSV/HTML,
and assert matrix parity. Start Streamlit on loopback, require `/_stcore/health` to return `ok`, and use
AppTest to confirm the rendered full matrix without recording synthetic evidence or resolutions.

- [ ] **Step 3: Self-review and publish**

Review `main...HEAD`, commit intentionally, push `codex/matrix-contract`, open one protected PR, wait
for all required `verify` and CodeQL checks, merge only when green, and confirm post-merge main checks.
