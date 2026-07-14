# Runtime Guidance Rendering Implementation Plan

> **For agentic workers:** Execute each task in order with test-driven development and verify the
> live browser state before publication.

**Goal:** Keep all runtime-evidence and criterion-resolution boundary guidance visible in a fresh
Streamlit browser session.

**Architecture:** Consolidate related adjacent text elements into three atomic Streamlit blocks.
Do not change core logic, schemas, lifecycle operations, widget keys, or persisted/exported data.

**Tech Stack:** Python 3.12, Streamlit 1.59, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Constraints

- Runtime evidence remains human supplied and restricted to E3 or E4.
- Saving runtime evidence does not resolve a criterion or record final acceptance.
- Human resolution and final acceptance remain separate append-only events.
- The deterministic gate and its precedence remain unchanged.
- No synthetic runtime evidence, paid API, billing, dependency, or untrusted code execution.

### Task 1: Lock atomic guidance contracts

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

- [ ] Add an AppTest requiring the runtime target and human-observation boundary in one caption.
- [ ] Require E3/E4 meanings, non-resolution boundary, required fields, and optional limitations in
  one caption.
- [ ] Require the criterion-resolution heading, selected criterion, and final-acceptance boundary in
  one Markdown block.
- [ ] Run the focused test and retain the expected RED result caused by the current split elements.

### Task 2: Consolidate presentation blocks

**Files:**
- Modify: `apps/web/app.py`
- Modify: `tests/apps/test_streamlit_app.py`

- [ ] Join the runtime target and human-observation disclaimer in one `st.caption` call.
- [ ] Join evidence-level and required-field guidance in one `st.caption` call.
- [ ] Join the criterion-resolution heading and context in one `st.markdown` call.
- [ ] Run the focused regression until GREEN.
- [ ] Run all Streamlit AppTests, lifecycle/runtime-schema tests, Ruff on changed Python, and
  `git diff --check`.

### Task 3: Verify product behavior and package

**Files:** Verify only.

- [ ] Run repository-wide Ruff and pytest.
- [ ] Run the deterministic 12-case benchmark and confirm zero mismatches, zero must-have False
  Ready, and zero false blockers.
- [ ] Build a wheel, install it into a fresh `/tmp` virtual environment, run the packaged benchmark,
  start `scopeproof-web`, and confirm the health endpoint.
- [ ] Run a fresh branch browser flow without saving fixture evidence, resolution, or acceptance;
  inspect the DOM and screenshot at the affected state.

### Task 4: Protected publication and reconciliation

- [ ] Commit the bounded change, push one `codex/` branch, and open one ready PR without reviewers,
  comments, issue updates, or release activity.
- [ ] Wait for required `verify`, ScopeProof, and CodeQL checks.
- [ ] Merge only after checks pass, verify exact merged-main checks, fast-forward local `main`, remove
  the worktree, prune the local branch, and confirm a clean synchronized checkout.
