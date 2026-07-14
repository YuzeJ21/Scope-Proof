# Historical Review Lineage Design

## Problem

`ReviewState.analysis_history` is an audit trail, but current validation accepts a
deterministic historical bundle from a different review, repository, and pull
request. Save and JSON export then preserve unrelated evidence as if it belonged
to the active lifecycle.

## Decision

Require every historical bundle to share the active review's stable lineage:

- `review_id`;
- `repository`;
- `pr_number`.

Put the invariant in `ReviewState` so load, save, export, lifecycle operations,
and direct Pydantic reconstruction fail closed through their existing validation
boundaries.

Historical base/head SHAs, check and ingestion states, criteria confirmation,
final acceptance, timestamps, versions, criteria, evidence, findings,
resolutions, and gates remain allowed to differ. They are historical facts, not
active-state duplicates.

Reject contradictions; do not rewrite history or infer identity.

## Verification

Add schema regressions for every stable lineage field and compatibility coverage
for changed historical SHAs. Add save and lifecycle-export regressions for a
mutated in-memory state. Run focused and full tests, Ruff, the deterministic
benchmark, clean-wheel probes, installed benchmark, and exact workbench health.

This proves controlled local record consistency only. It is not external runtime
evidence, user validation, or proof that a pull request is correct.

## Exclusions

No gate changes, record migration, UI copy, paid API, billing, fork, synthetic
validation, comment, or release.
