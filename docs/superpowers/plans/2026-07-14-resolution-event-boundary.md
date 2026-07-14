# Resolution Event Boundary Implementation Plan

**Goal:** Ensure `append_resolution()` never returns state that fails its own
active bundle cross-reference contract.

**Architecture:** Put the guard in the core lifecycle command after input-state
revalidation and before event binding. Keep Streamlit and gate code unchanged.

### Task 1: Red tests

Modify `tests/reviews/test_lifecycle.py` to prove that a bundleless confirmed
revision and an unknown active criterion are currently accepted. Also prove a
valid-then-mutated event can bypass its schema and make an accepted review Ready.
Require stable fail-closed messages.

### Task 2: Minimal guard

Modify `scopeproof_core/reviews/lifecycle.py` to revalidate the supplied event,
require an active bundle and membership of non-null event criterion IDs in the
active criteria, then reconstruct the revision-bound event through its schema.

### Task 3: Verification and publication

Run focused lifecycle/schema/storage/export tests, the full suite, Ruff, the
deterministic benchmark, clean-wheel installed smoke, and independent review.
Publish through a protected PR, merge only on green, reconcile main, and
continue the persistent goal loop.
