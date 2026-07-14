# Criteria Edit Error-Recovery Design

## Problem

The Streamlit workbench calls `add_criterion`, `split_criterion`, `remove_criterion`, and
`reorder_criteria` directly from button handlers. If one of these validated operations raises a
`ValueError`, Streamlit renders the raw exception and local path. The candidate edit is not
published, but the user receives no bounded recovery guidance.

## Decision

Add one Streamlit-only helper that computes a candidate criterion list before publishing any
session change. It catches only `ValueError`, renders fixed recovery copy, and otherwise commits
the candidate list, resets stale analysis, reports the operation-specific success message, and
reruns. All four edit buttons use this helper.

The fixed failure copy is:

> Criteria could not be updated. The current review remains unchanged. Verify the edit and try
> again.

## State Contract

On failure, preserve the exact confirmed criteria, review state, analysis bundle, confirmation
flag, replacement approval, and user-entered add or split text. Do not call `_reset_analysis`, do
not rerun, and leave the failed action enabled for retry. Do not render exception text or paths.

On success, preserve the existing behavior and operation-specific success copy. The updated
criteria become pending confirmation and any prior analysis is reset through the existing helper.

## Boundaries

- Catch `ValueError` only; unexpected exception types remain visible to developers.
- Do not change criteria service behavior, lifecycle semantics, gates, schemas, exports, or
  versioning.
- Keep the helper in the Streamlit layer so the core remains UI-independent.
- Treat this as recovery guidance, not evidence that the requested edit was valid or applied.

## Verification

Use one parameterized AppTest covering add, split, remove, and reorder failures. Each case injects
a path-bearing `ValueError`, proves the current implementation exposes it, then requires fixed
copy, no exception/raw path, exact state preservation, retained text inputs where applicable, and
an enabled retry action. Run adjacent criteria tests, Ruff, the complete offline test suite, the
deterministic benchmark, wheel installation checks, and packaged HTTP health.
