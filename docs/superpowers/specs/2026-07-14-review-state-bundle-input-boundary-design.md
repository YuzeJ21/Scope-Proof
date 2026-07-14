# Review State Bundle Input Boundary Design

## Problem

`new_review_state()` treats its `ReviewBundle` argument as already validated and
only deep-copies it. Pydantic models do not validate assignment by default, so a
caller can create a valid bundle, mutate a nested model into invalid content, and
then initialize lifecycle state that fails only when it is later persisted or
exported.

This contradicts the lifecycle boundary established for resolution events,
runtime evidence, and criteria revisions. The constructor must not return state
that fails its own schema.

## Approaches considered

1. **Reconstruct and deterministically verify the complete bundle at the lifecycle
   boundary (selected).** Call
   `ReviewBundle.model_validate(bundle.model_dump(mode="python"))`, recompute its
   gate, and reject any mismatch before deriving state. This reruns every nested
   schema, produces an independent object, and closes forged gate truth.
2. Revalidate only criteria and review fields. This leaves other nested evidence,
   findings, resolutions, and gate fields exposed to the same bypass.
3. Enable assignment validation globally on every schema. This is a broader
   compatibility change and is unnecessary for the bounded constructor defect.

## Design

At the start of `new_review_state()`, reconstruct the supplied bundle through the
existing `ReviewBundle` schema. Recompute `GateDecision` with `evaluate_gate()` and
require complete equality with the supplied decision, including criterion sets and
reason codes. Reject mismatches rather than silently correcting them so invalid
producer output remains visible and auditable. Build the active bundle, criteria
revision, and review only from the verified reconstruction. Preserve the current
deep-copy separation between lifecycle representations.

No gate rule, evidence level, confirmation rule, source text, UI behavior, or
external integration changes. The constructor still accepts every valid bundle
currently accepted by the schema.

## Verification

Regression tests must prove that:

- a valid-then-mutated nested criterion is rejected before state creation;
- a structurally valid but deterministically false Ready gate is rejected;
- mutating the caller-owned bundle after creation cannot alter the returned
  review, revision, or active bundle;
- a valid bundle still initializes equivalent, independently owned state.

Then run focused lifecycle/schema/storage/export tests, Ruff, the complete offline
suite, deterministic benchmark, clean-wheel installed probes, packaged workbench
health, independent review, protected PR checks, merge, and exact-main checks.
