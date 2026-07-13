# Export Criterion Source Transparency Implementation Plan

**Goal:** Make normalized acceptance criteria traceable to their confirmed source in every report.

## Task 1: Add failing cross-format regressions

1. Require exact `source_text` and `criterion_source` in JSON, Markdown, CSV, and HTML.
2. Assert the new structured CSV columns.
3. Prove HTML escapes source text and source classification.
4. Run focused tests and confirm RED only for missing human-readable fields.

## Task 2: Add minimal source rendering

1. Add Markdown source section and matrix column.
2. Add two additive CSV columns and values.
3. Add escaped HTML source section and table column.
4. Run focused tests and Ruff.

## Task 3: Verify and publish

1. Run the full offline suite, deterministic benchmark, and diff checks.
2. Build and install the wheel, then produce real JSON, Markdown, CSV, and HTML reports.
3. Confirm exact source fields and deterministic repeated exports.
4. Publish one protected PR, merge only after required checks, and confirm post-merge main checks.
