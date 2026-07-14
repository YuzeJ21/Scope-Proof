# Deterministic Gate Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent structurally valid but deterministically false gate decisions
from entering lifecycle transitions, persistence, or exports.

**Architecture:** Centralize Pydantic reconstruction plus complete deterministic
gate comparison in `scopeproof_core/gates/validation.py`. Reuse it from lifecycle,
JSON storage, and report exporters, including active and historical bundles.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff.

## Global Constraints

- Reject mismatches; never silently overwrite a supplied gate.
- Preserve the deterministic evaluator as the only gate truth table.
- Validate active and historical persisted/exported bundles.
- Do not change record version, gate semantics, UI, or external integration.
- Treat False Ready as more harmful than False Blocked.

---

### Task 1: Add failing boundary regressions

**Files:**
- Modify: `tests/storage/test_json_store.py`
- Modify: `tests/reporting/test_lifecycle_exports.py`
- Create: `tests/gates/test_validation.py`

**Interfaces:**
- Consumes: existing `JsonReviewStore`, exporters, and review-state fixtures
- Produces: regression evidence for active, persisted, direct, and historical gate mismatches

- [ ] **Step 1: Add storage save/load tests**

Mutate only the active gate verdict to `ready`. Require save to fail before file
creation. For load, save a valid record, edit the JSON verdict, and require load to
fail with the stable active-bundle message.

- [ ] **Step 2: Add export tests**

Require `export_markdown()` and `export_json()` to reject a forged active Ready
gate rather than rendering or serializing it.

- [ ] **Step 3: Add shared-validator history test**

Move a valid bundle into `analysis_history`, mutate only its gate, and require the
state validator to raise the historical-bundle message.

- [ ] **Step 4: Run the new tests and confirm RED**

Expected: storage and exports accept forged active gates; the new validation
module is absent; all failures reflect those reproduced gaps.

### Task 2: Implement shared deterministic validation

**Files:**
- Create: `scopeproof_core/gates/validation.py`
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/storage/json_store.py`
- Modify: `scopeproof_core/reporting/exporters.py`
- Test: files from Task 1 plus existing lifecycle/storage/export tests

**Interfaces:**
- Produces: `validated_review_bundle(bundle: ReviewBundle) -> ReviewBundle`
- Produces: `validated_review_state(state: ReviewState) -> ReviewState`

- [ ] **Step 1: Implement bundle validation**

Reconstruct the bundle from `model_dump(mode="python")`, evaluate its gate from
review, criteria, findings, and resolutions, and reject complete-decision mismatch.

- [ ] **Step 2: Implement state validation**

Reconstruct the state, verify its active bundle with the active message, and verify
every historical bundle with the history message.

- [ ] **Step 3: Replace boundary-local structural validation**

Use the shared functions from lifecycle, JSON save/load, and exporter validation.
Keep lifecycle gate recalculation unchanged.

- [ ] **Step 4: Run focused verification**

Run gate, lifecycle, schema, storage, and reporting tests; run focused Ruff and
`git diff --check`. Expected: all pass.

- [ ] **Step 5: Commit the bounded slice**

Stage only the shared module, integrations, regressions, design, and plan. Commit
as `Enforce deterministic gates at trust boundaries`.

### Task 3: Verify and integrate

**Files:**
- Verify repository and packaged artifact; no additional feature files.

**Interfaces:**
- Consumes: committed shared gate boundary
- Produces: exact protected-main evidence

- [ ] **Step 1: Run full source verification**

Run complete pytest, repository-wide Ruff, deterministic benchmark, and diff checks.

- [ ] **Step 2: Run clean-wheel installed verification**

Build/install a fresh wheel; probe save/load/export active and historical rejection,
dependency consistency, installed benchmark, and exact workbench health.

- [ ] **Step 3: Obtain independent review**

Resolve all Critical and Important findings and rerun invalidated checks.

- [ ] **Step 4: Publish and merge through protected GitHub flow**

Push the `codex/` branch, open a ready PR, wait for `verify` and CodeQL, merge only
when green, and wait for exact merged-main CI and CodeQL success.

- [ ] **Step 5: Reconcile and continue**

Fast-forward local main, remove the merged worktree/branch, refresh PR and security
state, and immediately continue the adoption-readiness loop.
