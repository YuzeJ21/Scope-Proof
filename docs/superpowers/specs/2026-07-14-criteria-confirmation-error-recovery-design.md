# Criteria-Confirmation Error-Recovery Design

## Reproduced Gap

When an analyzed review's criteria are edited, Streamlit calls `revise_criteria` and then
`confirm_criteria` without an expected failure boundary. Controlled probes can force either
validated lifecycle step to raise path-bearing `ValueError` output. Streamlit exposes the traceback
and path. Session review and confirmed criteria remain intact, but no safe retry guidance appears.

## Decision

Catch `ValueError` around both lifecycle transitions and render:

> Criteria could not be confirmed. The current review remains unchanged. Verify the edited criteria
> and try again.

On failure, retain the exact review, active bundle, confirmed criteria, pending widget edits, and
enabled confirmation retry. Do not write partially revised state or rerun. On success, preserve the
existing atomic session writes, analysis invalidation, confirmation state, and rerun.

## Boundaries

- Do not change criterion validation, normalization, IDs, priorities, evidence levels, or lineage.
- Do not change criteria-confirmation requirements or analysis locking.
- Do not catch unexpected exception types or expose raw details.
- Do not change core lifecycle, schemas, gates, persistence, workflows, version, or release state.
