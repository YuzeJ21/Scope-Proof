# Mobile Evidence Matrix Accessibility Implementation Plan

> Scope: local-only v0.2.2 candidate. Do not push, publish, release, or create notification-generating GitHub activity.

**Goal:** Keep all six evidence-matrix fields reachable at narrow viewports without changing evidence, gate, filtering, or review semantics.

**Architecture:** Preserve the existing ordered `matrix` records in the Streamlit layer and replace only the Markdown table renderer with one bordered evidence card per criterion. Keep the core engine, schemas, persistence, exports, and deterministic rules untouched.

**Design:** `docs/superpowers/specs/2026-07-18-mobile-evidence-matrix-accessibility-design.md`

## Task 1: Add a failing presentation contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

1. Replace the Markdown-table helper with a helper that reads the ordered evidence-card criterion markers.
2. Update filter assertions to inspect criterion IDs in the cards.
3. Replace `test_evidence_matrix_renders_as_one_markdown_table` with a regression requiring:
   - no data grid or legacy Markdown table;
   - the exact six-field contract;
   - AC-01 through AC-04 in deterministic order;
   - preserved Evidence types and Reviewer decision values;
   - inert requirement text.
4. Run the focused tests and record the expected RED result because the app still renders Markdown.

Command:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k 'evidence_matrix or primary_workbench_uses_acceptance_coverage_language'
```

## Task 2: Render responsive evidence cards

**Files:**
- Modify: `apps/web/app.py`

1. Retain the ordered `matrix` construction exactly.
2. Add a visible caption explaining that each card preserves all six fields.
3. Render one bordered `st.container` per criterion at every viewport.
4. Render repository-controlled requirement text with `st.text`; keep the other values deterministic and non-interactive.
5. Retain the current no-results information message without an empty grid.
6. Run the focused tests and confirm GREEN.

Command:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k 'evidence_matrix or primary_workbench_uses_acceptance_coverage_language'
```

## Task 3: Verify the complete presentation surface

1. Run the complete Streamlit test file.
2. Run Ruff and diff hygiene.
3. Reload the local candidate in a fresh desktop viewport (1280×720) and a fresh mobile viewport (390×844).
4. Confirm every card and field remains inside the document width without horizontal clipping or new grid tools.
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
