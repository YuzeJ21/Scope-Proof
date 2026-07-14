# Criteria Revision Input Boundary Implementation Plan

**Goal:** Ensure a criteria revision contains only independently validated
criterion objects.

**Architecture:** Reconstruct the input list with the existing `Criterion` schema
inside `revise_criteria()` before creating `CriteriaRevision`.

### Task 1: Red regressions

Prove a valid-then-mutated criterion is currently accepted and a caller mutation
after revision changes returned state.

### Task 2: Minimal reconstruction

Validate each criterion from its Python dump and pass only those reconstructed
objects into the new revision.

### Task 3: Verification and publication

Run the full local, benchmark, package, runtime, review, PR, CI, CodeQL, merge, and
main-reconciliation loop, then continue the persistent audit.
