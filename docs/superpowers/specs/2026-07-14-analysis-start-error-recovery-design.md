# Analysis-Start Error-Recovery Design

## Reproduced Gap

After criteria confirmation, the Streamlit action computes a deterministic bundle and passes it to
either `new_review_state` or `attach_analysis` without an expected error boundary. A controlled
exact-main probe forced `new_review_state` to raise a path-bearing `ValueError`; Streamlit exposed
the traceback and local path. No review state was written and retry remained possible, but the user
received no safe recovery guidance.

The reanalysis branch uses the same unguarded transition and must receive the same protection.

## Decision

Catch `ValueError` around bundle computation and the selected validated lifecycle transition. Show:

> Analysis could not be completed. No review state was changed. Verify the confirmed criteria and
> loaded source, then try again.

On failure, preserve the exact prior review, bundle, criteria confirmation, source-reload notice,
and retry state. Do not expose raw details or rerun. On success, retain the current session updates,
source-reload-notice clearing, and rerun.

## Boundaries

- Do not change matching, findings, gates, criteria confirmation, review lineage, or reanalysis.
- Do not catch unexpected exception types.
- Do not execute PR code or claim the controlled probe as external evidence.
- Do not change schemas, lifecycle, persistence, exports, workflows, version, or release state.
