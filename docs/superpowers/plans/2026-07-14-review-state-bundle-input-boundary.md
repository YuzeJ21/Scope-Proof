# Review State Bundle Input Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure `new_review_state()` returns only independently validated state.

**Architecture:** Reconstruct the full caller-supplied `ReviewBundle` through its
Pydantic schema at the core lifecycle boundary, require its complete gate decision
to equal deterministic evaluation, then derive all three lifecycle representations
from that verified copy.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff.

## Global Constraints

- Do not change gate, evidence, criteria-confirmation, or final-acceptance semantics.
- Do not execute repository code or add external services.
- Preserve exact valid requirements source text.
- Treat False Ready as more harmful than False Blocked.

---

### Task 1: Lock the constructor boundary with regressions

**Files:**
- Modify: `tests/reviews/test_lifecycle.py`
- Modify: `scopeproof_core/reviews/lifecycle.py`

**Interfaces:**
- Consumes: `new_review_state(bundle: ReviewBundle) -> ReviewState`
- Produces: validated, non-aliased `ReviewState`

- [ ] **Step 1: Add a failing mutated-input test**

Create a valid bundle, mutate its nested criterion text to `""`, call
`new_review_state()`, and require the existing Pydantic minimum-length error.

- [ ] **Step 2: Add a caller-alias contract test**

Create state from a valid bundle, mutate the original review ID, criterion text,
and source text, then assert the returned review, revision, and active bundle keep
their original values. This locks the existing deep-copy behavior while the input
boundary changes.

- [ ] **Step 3: Add a failing forged-gate test**

Start from a deterministically evaluated `needs_review` bundle, change only its
verdict to `ready`, and require `new_review_state()` to reject the mismatch.

- [ ] **Step 4: Run the boundary tests and confirm the reproduced failures**

Run:
`python -m pytest tests/reviews/test_lifecycle.py::test_new_review_state_revalidates_the_supplied_bundle tests/reviews/test_lifecycle.py::test_new_review_state_rejects_a_non_deterministic_gate tests/reviews/test_lifecycle.py::test_new_review_state_does_not_alias_the_supplied_bundle -q`

Expected: the mutated-input and forged-gate tests fail because no exception is
raised; the alias contract test passes under the existing deep-copy implementation.

- [ ] **Step 5: Implement complete bundle reconstruction and gate verification**

Add:

```python
bundle = ReviewBundle.model_validate(bundle.model_dump(mode="python"))
```

as the first constructor statement, before any copy or field read.

Then recompute the complete gate with `evaluate_gate()` and raise
`ValueError("analysis bundle gate must match deterministic evaluation")` when it
does not equal `bundle.gate`.

- [ ] **Step 6: Run focused lifecycle and integrity tests**

Run lifecycle, review-state integrity, storage, and export tests plus Ruff and
`git diff --check`. Expected: all pass.

- [ ] **Step 7: Commit the bounded slice**

Stage the lifecycle implementation, regression tests, design, and plan. Commit as
`Validate review bundle lifecycle input`.

### Task 2: Verify and integrate

**Files:**
- Verify all repository files without additional implementation changes.

**Interfaces:**
- Consumes: committed constructor boundary
- Produces: protected-main evidence for the exact merge SHA

- [ ] **Step 1: Run full source verification**

Run full pytest, repository-wide Ruff, deterministic benchmark, and diff checks.

- [ ] **Step 2: Run clean-wheel verification**

Build and install the wheel in a fresh virtual environment. Run the mutated-input
and alias probes, installed benchmark, dependency check, and exact `ok` workbench
health request.

- [ ] **Step 3: Obtain independent code review**

Require no unresolved Critical or Important findings before publication.

- [ ] **Step 4: Publish through protected GitHub integration**

Push the `codex/` branch, open a ready PR, wait for `verify` and CodeQL, merge only
when green, and validate the exact merged-main SHA runs.

- [ ] **Step 5: Reconcile and continue**

Fast-forward local main, remove the merged worktree and branch, refresh security
and PR state, then immediately select the next evidence-backed improvement.
