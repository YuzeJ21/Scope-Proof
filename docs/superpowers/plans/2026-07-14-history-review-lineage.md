# Historical Review Lineage Implementation Plan

**Goal:** Reject audit-history bundles belonging to another review lifecycle.

**Architecture:** Add a narrow stable-lineage invariant to the existing
`ReviewState` cross-object validator and rely on established revalidation at
storage, export, and lifecycle trust boundaries.

### Task 1: Reproduce

- Add schema failures for divergent historical review ID, repository, and PR.
- Preserve compatibility for historical SHA differences.
- Add save and lifecycle-export rejection tests.
- Run focused tests and confirm RED.

### Task 2: Implement

- Compare each history bundle's stable lineage with the active review.
- Raise `historical bundle review lineage must match lifecycle review`.
- Run focused tests, Ruff, and diff checks.

### Task 3: Verify and integrate

- Run full pytest, Ruff, deterministic benchmark, and clean-wheel verification.
- Obtain independent Critical/Important review.
- Publish through a protected `codex/` PR; require green CI and CodeQL.
- Verify exact merged-main runs, sync local main, clean the worktree, and continue.
