# Criteria-Confirmation Error-Recovery Plan

**Goal:** Recover safely and atomically from expected criteria revision or confirmation validation
failures without changing review lineage or analysis gating.

## Task 1: Regression-first coverage

Add a parameterized AppTest for `revise_criteria` and `confirm_criteria`. Begin with an analyzed
review and a pending valid criterion edit. Force each transition to raise a path-bearing
`ValueError`. Require the baseline to fail with a raw Streamlit exception. After implementation,
require fixed copy, no raw details, exact session review/bundle/confirmed criteria preservation,
retained edited widget value, disabled analysis, and enabled confirmation retry.

## Task 2: Atomic UI recovery

Wrap both lifecycle calls in one `try/except ValueError`, and move all existing session writes and
rerun into `else`. This prevents partial publication if either transition rejects the candidate
state.

## Task 3: Verify and integrate

Run focused criteria/lineage tests, Ruff, full tests, benchmark, wheel integrity, diff checks, and
HTTP health. Keep this local child branch unpushed while parent PR #117 awaits CodeQL. After parent
and analysis-transition slices integrate, reconcile to exact main and publish through the same
protected CI/CodeQL path without labels, comments, reviewers, or release.
