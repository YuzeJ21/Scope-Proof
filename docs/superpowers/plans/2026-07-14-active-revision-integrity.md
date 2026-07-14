# Active Revision Integrity Implementation Plan

**Goal:** Reject active lifecycle state whose confirmed criteria revision does
not exactly describe its active analysis bundle.

**Architecture:** Keep the rule in the core `ReviewState` Pydantic validator so
all storage, lifecycle, export, CLI, and UI consumers share the same fail-closed
contract. Do not add Streamlit-specific repair behavior.

**Tech stack:** Python 3.11+, Pydantic 2, pytest, Ruff.

---

### Task 1: Add failing schema regressions

**Files:**
- Modify: `tests/schemas/test_review_state_integrity.py`

1. Add a test that changes active revision source text while leaving the bundle
   unchanged and expects validation failure.
2. Add a test that changes one active revision criterion while leaving the
   bundle unchanged and expects validation failure.
3. Add a test that marks an active revision unconfirmed while retaining the
   bundle and expects validation failure.
4. Add real lifecycle-object tests that mutate revision criteria and review
   identity and prove the active bundle does not mutate with them.
5. Add a confirmation-consistency regression covering review and revision flags.
6. Run the focused test file and confirm the new tests fail for the intended
   missing validator behavior.

### Task 2: Implement the smallest model guard

**Files:**
- Modify: `scopeproof_core/schemas/models.py`

1. Extend the `ReviewState` model validator after the existing review-identity
   check.
2. Reject an active bundle paired with an unconfirmed revision.
3. Reject review/revision confirmation, criteria, or source-text mismatches with
   stable messages.
4. Deep-copy the active bundle, lifecycle review, and revision criteria during
   `new_review_state()` construction.
5. Run the focused schema and lifecycle tests until green.

### Task 3: Verify compatibility and repository health

**Files:**
- Test: `tests/schemas/test_review_state_integrity.py`
- Test: `tests/reviews/test_lifecycle.py`
- Test: `tests/storage/test_json_store.py`
- Test: `tests/reporting/test_lifecycle_exports.py`

1. Confirm matching active state and bundleless pending revision still validate.
2. Run the full pytest suite and Ruff.
3. Run the deterministic benchmark and clean-wheel installed smoke.
4. Request independent review and address only evidence-backed findings.

### Task 4: Publish safely

1. Commit the bounded change on `codex/active-revision-integrity`.
2. Push and open a protected pull request.
3. Merge only after required CI and CodeQL succeed.
4. Verify the exact merged-main SHA, reconcile local main, remove the worktree,
   and continue the persistent goal loop.
