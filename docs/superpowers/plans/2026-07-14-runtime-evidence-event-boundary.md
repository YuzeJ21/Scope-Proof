# Runtime Evidence Event Boundary Implementation Plan

**Goal:** Ensure the runtime-evidence lifecycle command only returns independently
validated, non-aliased evidence state.

**Architecture:** Keep the fix in the core lifecycle boundary. Reconstruct the
input through the existing Pydantic schema before target validation and append.

### Task 1: Red regressions

Add lifecycle tests for validator-bypassing mutation before append and caller
mutation after append.

### Task 2: Minimal reconstruction

Reconstruct `RuntimeEvidence` from its Python dump before inspecting or appending
it. Preserve current missing-bundle and unknown-criterion errors.

### Task 3: Verification and publication

Run focused and full tests, Ruff, deterministic benchmark, clean-wheel installed
guards and health, independent review, and the protected PR workflow. Reconcile
merged main and continue the persistent audit loop.
