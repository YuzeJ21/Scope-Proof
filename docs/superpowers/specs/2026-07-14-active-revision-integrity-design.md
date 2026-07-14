# Active Revision Integrity Design

## Problem

`ReviewState` currently proves that an active bundle carries the same `Review`
identity as the lifecycle state. It does not prove that the bundle was produced
from the active `CriteriaRevision`. A valid persisted payload can therefore pair
one confirmed revision with a bundle containing different criteria or a different
requirements source. In addition, `new_review_state()` reuses mutable `Review` and
`Criterion` instances across these representations, so mutating one side can also
mutate the other and evade an equality check while retaining an old gate.

That ambiguity is unsafe because lifecycle operations and the workbench treat the
revision and bundle as one active review. ScopeProof must reject the inconsistent
record instead of choosing which representation to trust.

## Scope

When an active bundle exists, `ReviewState` will require:

- the active revision is confirmed;
- review confirmation exactly matches revision confirmation;
- the bundle criteria exactly match the active revision criteria, including order;
- the bundle source text exactly matches the active revision source text.

Lifecycle construction will deep-copy the active bundle, lifecycle review, and
revision criteria so mutable aliases cannot make both sides drift together.

The existing active-review identity check remains in force. Bundleless pending
revisions remain valid. Historical bundle and event integrity are intentionally
outside this bounded change and can be audited separately.

## Failure behavior

Pydantic validation fails with a stable, field-specific message. No state is
repaired, normalized, or partially accepted. This keeps persisted and exported
objects deterministic and makes a corrupted record fail closed.

## Verification

Regression tests cover each rejected mismatch plus the accepted active and
bundleless states. The full suite, Ruff, deterministic benchmark, clean-wheel
smoke, and independent review must pass before publication.
