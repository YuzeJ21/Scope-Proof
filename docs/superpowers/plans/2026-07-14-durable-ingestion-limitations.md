# Durable Ingestion Limitations Implementation Plan

## Goal

Preserve and expose bounded GitHub-ingestion details from fetch through UI, storage, CLI, and every export without changing gate semantics.

### Task 1: Persist validated review provenance

1. Add failing schema and backward-compatibility tests for `Review.ingestion_warnings` and `Review.skipped_files`.
2. Add default-empty fields to `Review`.
3. Add failing boundary tests for web/CLI/demo review construction.
4. Copy snapshot values at all three boundaries.
5. Run the focused schema, storage, CLI, and demo tests.

### Task 2: Render limitations in reports and CLI metadata

1. Add failing Markdown, CSV, HTML, JSON, escaping, and CLI metadata tests.
2. Render ingestion state, warnings, and skipped paths in every report.
3. Include the same fields in CLI completion metadata.
4. Run focused reporting and CLI tests.

### Task 3: Surface limitations in Streamlit

1. Add failing tests for a live partial snapshot and a reopened saved partial review.
2. Add one reusable renderer using existing `st.warning`, `st.caption`, and `st.expander` patterns.
3. Render from the live snapshot when present and otherwise from the stored review.
4. Run the Streamlit test suite.

### Task 4: Verify and publish

1. Run Ruff, the full test suite, bundled benchmark, and diff hygiene.
2. Start the branch app with telemetry disabled and a fresh HOME.
3. Fetch the same real public large PR used for the baseline audit and confirm visible recovery guidance and skipped paths.
4. Save and inspect the fixed-state screenshot.
5. Perform an independent diff review and fix all material findings.
6. Commit, push, open a ready PR, wait for every required check, merge with head matching, and verify exact merge-SHA CI.
7. Fast-forward local main and remove the owned worktree/branch.

