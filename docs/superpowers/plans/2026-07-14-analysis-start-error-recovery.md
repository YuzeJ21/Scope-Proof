# Analysis-Start Error-Recovery Plan

**Goal:** Recover safely from expected initial-analysis and reanalysis transition validation
failures without changing deterministic analysis or review lineage.

## Task 1: Regression-first coverage

Add a parameterized AppTest covering `new_review_state` and `attach_analysis`. Force each transition
to raise a path-bearing `ValueError`. Require the current baseline to fail with a Streamlit
exception. After implementation require fixed recovery copy, no raw details, exact state and bundle
preservation, confirmed criteria, no generated result, and enabled retry.

## Task 2: Bounded implementation

Wrap `_analyze` plus the selected validated transition in `try/except ValueError`. Keep all existing
session writes, source-notice clearing, and rerun in `else` so no partial state is published.

## Task 3: Verify and integrate

Run focused initial/reanalysis/lineage tests, Ruff, full offline tests, deterministic benchmark,
wheel integrity, diff checks, and loopback health. Hold the local stacked branch unpushed until its
parent PR #117 receives CodeQL and merges. Then reconcile against exact main, review the final
base-to-head diff, publish one protected PR without labels/comments/reviewers/release, and integrate
only after CI and CodeQL pass.
