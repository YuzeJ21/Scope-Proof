# Final-Acceptance Error-Recovery Design

## Reproduced Gap

The final-acceptance control calls the validated lifecycle boundary without catching expected
`ValueError` failures. A controlled exact-main AppTest forced that boundary to reject a final event
with path-bearing validation text. Streamlit rendered a traceback and the raw local path. The
functional lifecycle left the review unchanged, but the operator received no safe recovery path.

## Decision

Catch `ValueError` only around construction/append of the final-acceptance event. Render this fixed
copy at the point of action:

> Final acceptance could not be recorded. The review remains unchanged. Verify the active review
> state and try again.

On failure, keep the exact review, bundle, gate, event history, and saved fingerprint unchanged.
Keep the final-acceptance control enabled so the operator can retry. Do not render success copy or
rerun. On success, preserve the existing append, session update, notice, rerun, and repeat guard.

## Boundaries

- Do not change final-acceptance eligibility, gate precedence, criterion resolution, or event data.
- Do not swallow unexpected exception types.
- Do not expose raw exception text or local paths.
- Do not change schemas, lifecycle, persistence, exports, workflows, version, or release state.
- Do not claim the controlled failure as external evidence or runtime validation.
