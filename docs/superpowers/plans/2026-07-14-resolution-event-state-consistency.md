# Resolution Event State Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make active cached resolutions and final acceptance provably derived from
append-only current-revision events.

**Architecture:** Extract existing event reduction into a shared top-level module,
use it in lifecycle recalculation and shared state validation, and require initial
analysis bundles to contain no preloaded human decisions.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff.

## Global Constraints

- Never manufacture resolution events or human provenance.
- Preserve append-only prior-revision events.
- Do not change gate evaluation or direct standalone bundle exports.
- Require active human state to match current-revision events exactly.
- Treat False Ready as more harmful than False Blocked.

---

### Task 1: Add failing active-state regressions

**Files:**
- Modify: `tests/reviews/test_lifecycle.py`
- Modify: `tests/gates/test_validation.py`
- Modify: `tests/storage/test_json_store.py`
- Modify: `tests/reporting/test_lifecycle_exports.py`

**Interfaces:**
- Consumes: current lifecycle, shared state validation, storage, and exporters
- Produces: reproduced event/cache False Ready failures

- [ ] **Step 1: Test initial human-state rejection**

Require `new_review_state()` to reject a bundle with preloaded resolutions and a
bundle with `final_acceptance=True`.

- [ ] **Step 2: Test active cache/event mismatches**

Require shared state validation to reject divergent cached resolutions, divergent
cached final acceptance, and current-revision events without an active bundle.

- [ ] **Step 3: Test forged Ready save/export rejection**

Create a state whose cached resolutions, final acceptance, and gate agree on Ready
while events remain empty. Require save and lifecycle export to reject it.

- [ ] **Step 4: Run the new tests and confirm RED**

Expected: all forged active human-state paths are accepted by current code.

### Task 2: Centralize event derivation and enforce consistency

**Files:**
- Create: `scopeproof_core/resolution_events.py`
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/gates/validation.py`
- Modify: reporting fixtures that previously preloaded lifecycle resolutions
- Test: Task 1 files and adjacent lifecycle/reporting suites

**Interfaces:**
- Produces: `current_resolutions(events, criteria_revision_number=None)`
- Produces: `final_acceptance(events, criteria_revision_number)`

- [ ] **Step 1: Move event reduction without behavior changes**

Move current-resolution and final-acceptance derivation into the new module. Import
them into lifecycle so existing `scopeproof_core.reviews.lifecycle.current_resolutions`
imports remain valid.

- [ ] **Step 2: Enforce initial analysis boundary**

Reject nonempty resolutions and true final acceptance before constructing state.

- [ ] **Step 3: Enforce active state/event consistency**

After Pydantic reconstruction, reject bundleless active events, resolution cache
mismatch, or final-acceptance mismatch before returning trusted state.

- [ ] **Step 4: Repair test fixtures through real lifecycle actions**

Where a test needs a lifecycle state with a resolution, start from a resolution-
free deterministic bundle and call `append_resolution()`.

- [ ] **Step 5: Run focused tests, Ruff, and diff checks**

Run lifecycle, validation, storage, reporting, and schema tests. Expected: green.

- [ ] **Step 6: Commit**

Commit only the event module, integrations, regressions, fixture repairs, design,
and plan as `Bind active human state to resolution events`.

### Task 3: Verify and integrate

**Files:**
- Verify the repository and installed wheel; no unrelated feature changes.

**Interfaces:**
- Consumes: committed event-consistency boundary
- Produces: exact protected-main evidence

- [ ] **Step 1: Run full source verification**

Run full pytest, repository-wide Ruff, deterministic benchmark, and diff checks.

- [ ] **Step 2: Run clean-wheel installed verification**

Probe valid event append plus forged cache/final/bundleless-event rejection, save,
export, dependency consistency, installed benchmark, and exact workbench health.

- [ ] **Step 3: Obtain independent review**

Resolve Critical and Important findings and repeat invalidated checks.

- [ ] **Step 4: Publish through protected GitHub flow**

Push a `codex/` branch, open a ready PR, wait for `verify` and CodeQL, merge only
when green, and verify exact merged-main runs.

- [ ] **Step 5: Reconcile and continue**

Fast-forward local main, clean the owned worktree/branch, refresh live state, and
immediately continue the persistent adoption-readiness loop.
