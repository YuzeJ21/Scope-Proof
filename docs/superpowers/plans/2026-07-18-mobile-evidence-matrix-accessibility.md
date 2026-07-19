# Mobile Evidence Matrix Accessibility Implementation Plan

> Scope: local-only v0.2.2 candidate. Do not push, publish, release, or create notification-generating GitHub activity.

**Goal:** Keep all six evidence-matrix fields reachable at narrow viewports without changing evidence, gate, filtering, or review semantics.

**Architecture:** Preserve the existing ordered `matrix` records in the Streamlit layer and replace only the Markdown table renderer with a non-editable Streamlit data grid. Keep the core engine, schemas, persistence, exports, and deterministic rules untouched.

**Design:** `docs/superpowers/specs/2026-07-18-mobile-evidence-matrix-accessibility-design.md`

## Task 1: Add a failing presentation contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

1. Replace the Markdown-table helper with a helper that reads the one evidence-matrix `st.dataframe` value.
2. Update filter assertions to inspect criterion IDs in the grid.
3. Replace `test_evidence_matrix_renders_as_one_markdown_table` with a regression requiring:
   - exactly one grid;
   - the exact six-column order;
   - AC-01 through AC-04 in deterministic order;
   - preserved values in the rightmost Evidence types and Reviewer decision columns;
   - the small-screen horizontal-scroll caption;
   - no legacy Markdown evidence table.
4. Run the focused tests and record the expected RED result because the app still renders Markdown.

Command:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k 'evidence_matrix or primary_workbench_uses_acceptance_coverage_language'
```

## Task 2: Render an accessible container-width grid

**Files:**
- Modify: `apps/web/app.py`

1. Retain `table_headers` and `matrix` construction exactly.
2. Add the visible caption explaining that all six columns remain available and narrow screens may scroll horizontally.
3. Render a single non-editable `st.dataframe` with hidden index and container width.
4. For empty filters, pass a dict keyed by all six headers so the column contract remains deterministic, then retain the current no-results information message.
5. Run the focused tests and confirm GREEN.

Command:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k 'evidence_matrix or primary_workbench_uses_acceptance_coverage_language'
```

## Task 3: Verify the complete presentation surface

1. Run the complete Streamlit test file.
2. Run Ruff and diff hygiene.
3. Reload the local candidate in a fresh desktop viewport (1280×720) and a fresh mobile viewport (390×844).
4. Confirm the grid remains container-width and that the rightmost columns are reachable by horizontal scrolling rather than clipped by the document shell.
5. Capture post-fix screenshots as engineering evidence only.

Commands:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py
uv run ruff check apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
```

## Task 4: Commit the bounded fix

1. Review the diff for unrelated behavior changes.
2. Commit only the application, test, and implementation-plan files.

Commit message:

```text
fix: keep evidence matrix reachable on mobile
```
