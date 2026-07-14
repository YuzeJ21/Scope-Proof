# Criterion-Resolution Error-Recovery Design

## Reproduced Gap

The criterion-resolution Save action calls the validated resolution lifecycle without an expected
error boundary. A controlled exact-main probe forced a path-bearing `ValueError`; Streamlit exposed
the raw traceback and local path. The functional lifecycle preserved the review and the populated
form, but the user received no safe recovery guidance.

## Decision

Catch `ValueError` around resolution-event construction and append. Render fixed point-of-action
copy:

> Criterion resolution could not be recorded. The review remains unchanged. Verify the active
> review state and try again.

On failure, preserve the exact review, bundle, gate, event history, saved fingerprint, selected
decision, evidence level, and reviewer note. Keep Save enabled for retry. Do not show success or
reset the form. Preserve the existing successful append/reset/rerun behavior in the `else` path.

## Boundaries

- Do not alter decision options, evidence levels, criterion targeting, gates, or final acceptance.
- Do not catch unexpected exception types or expose raw exception details.
- Do not change schemas, lifecycle, persistence, exports, workflows, version, or release state.
- Do not represent the controlled probe as external evidence or runtime validation.
