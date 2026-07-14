# Local Save Failure Recovery Design

## Problem

The Streamlit workbench handles an unavailable store during startup and catches failures while
reopening or deleting saved reviews. The final `Save local review` action is different: it calls
`JsonReviewStore.save()` without an exception boundary. A deterministic AppTest reproduction that
raises `OSError("disk full at /private/secret/path")` produces a Streamlit exception, exposes the raw
filesystem detail, and interrupts the workbench instead of preserving a retryable unsaved review.

`JsonReviewStore.save()` can raise `OSError` for filesystem operations and `ValueError` for unsafe
store objects or review-state integrity failures. Both are expected local persistence failure classes,
not application-programming errors that should reach the user as a traceback.

## Goal

Turn expected local save failures into a fixed, non-sensitive recovery state. Keep the current review
open and marked unsaved, keep the save action available for retry, and do not claim that any record
was written.

## Approaches Considered

### Recommended: catch expected failures at the save action boundary

Wrap only `review_store.save(review_state)` in `try/except (OSError, ValueError)`. On failure, render
a fixed error explaining that the current review remains open as unsaved work and directing the
operator to verify the local directory and review integrity. Execute the existing fingerprint,
success-notice, and rerun path only in `else` after a successful write.

This is the narrowest boundary, matches existing reopen/delete/runtime-evidence patterns, preserves a
transient-error retry, and prevents raw exception text from becoming UI copy.

### Disable local storage after the first save failure

Persist a session flag and disable save/reopen/delete until restart. This is too broad: a disk-space,
permission, or transient I/O error may be corrected while the review remains open, and disabling the
button removes the direct retry path.

### Store a failure notice and force a rerun

Write an error notice to session state and rerun immediately. A failed save does not change the
review or saved-review list, so a rerun adds state churn without improving consistency. Rendering the
error in the current run is simpler and keeps the button visibly retryable.

## Behavior

When local saving raises `OSError` or `ValueError`:

- render exactly: `The review could not be saved locally. The current review remains open as unsaved work. Verify the local review directory and review integrity, then try again.`
- do not render the underlying exception message or filesystem path;
- keep the same validated `ReviewState` in session;
- do not set or change `saved_review_fingerprint`;
- keep `Save local review` enabled when it was enabled before the attempt;
- keep the existing unsaved-review caption visible;
- do not emit the success notice or call `st.rerun()`.

Successful saving remains unchanged: persist the validated state, set its deterministic fingerprint,
store the success notice, and rerun.

## Boundaries

- Do not change `JsonReviewStore`, record format, schemas, migrations, exports, analysis, or gates.
- Do not weaken `validated_review_state()` or convert validation failures into successful writes.
- Do not log or display raw exception details.
- Keep the implementation in `apps/web/app.py`; the core remains independent from Streamlit.
- Preserve all current success-path behavior and local-only storage semantics.

## Verification

Add an AppTest regression parameterized over one `OSError` and one `ValueError`. Each case must prove
the fixed recovery copy, absence of raw details and Streamlit exceptions, exact review-state
preservation, unchanged unsaved fingerprint, enabled retry, unchanged unsaved caption, and absence of
success copy. Run the focused regression, adjacent save/reopen/delete recovery tests, Ruff, complete
offline suite, deterministic benchmark, diff hygiene, and a local runtime health smoke.
