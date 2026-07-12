# First-Use Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the evidence matrix as one real Markdown table and prevent an implicit Accepted resolution from being saved.

**Architecture:** Keep the change inside the existing thin Streamlit layer. Escape user-authored table cells and join the already-built display rows into one Markdown block, and represent the decision placeholder as `None` only in UI state so domain models and gate behavior remain unchanged.

**Tech Stack:** Python 3.11+, Streamlit, Streamlit AppTest, pytest.

## Global Constraints

- Do not change evidence retrieval, findings, gate precedence, schemas, exports, or persistence.
- Never convert the decision placeholder into a `ResolutionEvent`.
- Keep the core engine independent from Streamlit.
- Preserve the deterministic demo results and all no-paid-API/public-only boundaries.

---

### Task 1: Safe evidence matrix presentation

**Files:**
- Modify: `apps/web/app.py:328-352`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `matrix: list[dict[str, str]]`, already filtered by status and priority.
- Produces: one atomic Markdown table plus the existing per-criterion summary Markdown.

- [ ] **Step 1: Write the failing AppTest**

Add a test that loads the demo, confirms criteria, runs analysis, and asserts exactly one Markdown block contains the header, separator, and final criterion row.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/python -m pytest tests/apps/test_streamlit_app.py::test_evidence_matrix_renders_as_table -q`

Expected: FAIL because the table is split across separate Markdown calls.

- [ ] **Step 3: Implement the static table**

Replace the separate Markdown header, separator, and row calls with one escaped block:

```python
table_headers = ["Criterion", "Requirement", "Priority", "Status", "Evidence", "Confidence"]
table_lines = [
    "| " + " | ".join(table_headers) + " |",
    "|" + "|".join("---" for _ in table_headers) + "|",
]
for row in matrix:
    cells = [str(row[header]).replace("|", "\\|").replace("\n", " ") for header in table_headers]
    table_lines.append("| " + " | ".join(cells) + " |")
st.markdown("\n".join(table_lines))
for row in matrix:
    st.markdown(f"**{row['Criterion']} — {row['Status']}** · {row['Requirement']}")
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `.venv/bin/python -m pytest tests/apps/test_streamlit_app.py::test_evidence_matrix_renders_as_table -q`

Expected: PASS.

### Task 2: Explicit human-decision selection

**Files:**
- Modify: `apps/web/app.py:432-466`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `HumanDecision` enum values.
- Produces: `decision: HumanDecision | None`; `save_resolution` is disabled while the value is `None`.

- [ ] **Step 1: Write failing AppTests**

Update the summary-control test to assert `resolution_decision.value is None` and `save_resolution.disabled is True`. Update the resolution-history test to set `HumanDecision.ACCEPTED` explicitly before clicking Save resolution.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/apps/test_streamlit_app.py::test_demo_summary_requires_explicit_resolution_decision tests/apps/test_streamlit_app.py::test_human_decision_and_final_acceptance_append_history -q`

Expected: at least the explicit-selection test FAILS because Accepted is currently preselected and Save resolution is enabled.

- [ ] **Step 3: Implement the placeholder and disabled state**

Configure the selectbox with `index=None`, `placeholder="Select a decision"`, and disable Save resolution when `decision is None`. Guard event construction inside the enabled branch so the placeholder never reaches `ResolutionEvent`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same focused command.

Expected: both tests PASS.

- [ ] **Step 5: Run full verification and browser confirmation**

Run:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff clean; all offline tests pass with only the opt-in live test skipped; 12 benchmark cases execute with zero mismatches and zero must-have False Ready; diff check clean. Then reload the local Streamlit app and capture the corrected matrix and unselected human-decision state.

- [ ] **Step 6: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py docs/superpowers/plans/2026-07-12-first-use-safety.md
git commit -m "fix: require deliberate review decisions"
```
