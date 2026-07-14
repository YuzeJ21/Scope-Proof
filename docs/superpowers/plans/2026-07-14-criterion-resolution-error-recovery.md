# Criterion-Resolution Error-Recovery Plan

**Goal:** Recover safely from expected criterion-resolution lifecycle validation failures while
preserving deterministic decision and gate semantics.

## Task 1: Regression-first reproduction

Add an AppTest that selects an accepted decision, supplies a reviewer note, patches
`append_resolution` to raise a path-bearing `ValueError`, and requires safe recovery. The baseline
must fail with an unhandled Streamlit exception. After implementation require fixed copy, no raw
details, exact state preservation, retained inputs, zero appended events, no success/reset, and an
enabled retry.

## Task 2: Bounded implementation

Wrap only resolution-event construction and append in `try/except ValueError`. Put existing
session-state updates, reset notice, and rerun in `else`. Do not change successful behavior or any
core contract.

## Task 3: Verification and integration

Run focused decision/gate tests, Ruff, the full offline suite, deterministic benchmark, wheel
integrity, diff checks, and loopback health. Review scope and protected semantics. Publish one ready
PR without labels, comments, reviewers, or release; merge only the exact reviewed head after CI and
CodeQL pass, reverify exact main, and clean the temporary branch/worktree.
