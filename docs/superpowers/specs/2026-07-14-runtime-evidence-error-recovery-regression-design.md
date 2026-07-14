# Runtime-Evidence Error-Recovery Regression Design

## Verified State

Current main already disables manual runtime-evidence Save until all five required fields contain
non-whitespace text. It also catches downstream `ValueError` and shows fixed recovery copy instead
of raw Pydantic output. Final acceptance remains a separate append-only event and does not override
the deterministic gate.

A controlled AppTest probe forced the downstream lifecycle call to raise a `ValueError` containing
a local path. ScopeProof showed no Streamlit exception, did not render the raw error or path,
preserved the exact review, appended no runtime record, and kept the completed form retryable.

## Gap

No committed regression proves that defense-in-depth recovery contract. Existing tests cover form
prerequisites and successful saves, but a future refactor could restore raw validation output or
mutate state on failure without failing the suite.

## Decision

Add one Streamlit AppTest that forces the lifecycle append boundary to raise a path-bearing
`ValueError` after the form becomes ready. Require fixed recovery copy, no exception or raw detail,
exact state preservation, zero appended runtime records, retained form input, and an enabled retry.

No production behavior changes are required.

## Boundaries

- Do not alter schemas, lifecycle, evidence levels, gates, persistence, exports, or final acceptance.
- Do not save invented runtime evidence or represent the controlled probe as external validation.
- Do not expose raw exception text or local paths.
- Do not change workflows, package version, release state, billing, APIs, or fork policy.
