# Local Save Failure Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve a retryable unsaved review and show fixed recovery guidance when local persistence fails.

**Architecture:** Add one exception boundary around the Streamlit save action. The existing `JsonReviewStore` remains authoritative and unchanged; only a successful store call may update the saved fingerprint, set success copy, or trigger a rerun.

**Tech Stack:** Python 3.12, Streamlit, Pydantic v2, pytest `AppTest`, Ruff.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Validate every persisted object with Pydantic schemas.
- Keep the core engine independent from Streamlit and GitHub UI layers.
- Treat False Ready as more harmful than False Blocked.
- Do not expose raw filesystem or validation details in recovery copy.

---

### Task 1: Recover safely from expected local save failures

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `JsonReviewStore.save(review_state) -> Path`, which may raise `OSError` or `ValueError`.
- Produces: a fixed Streamlit error state while leaving the current `ReviewState` and retry path unchanged.

- [ ] **Step 1: Write the failing regression**

Add `test_local_save_failure_preserves_retryable_unsaved_review_without_raw_details`, parameterized
over `OSError("disk full at /private/secret/path")` and
`ValueError("invalid record at /private/secret/path")`. Use a temporary HOME, build an analyzed demo,
capture the exact review state, patch `JsonReviewStore.save`, and click `save_review`.

Require the fixed recovery sentence from the design, zero `app.exception`, no raw error text or
`/private/secret/path`, exact review-state equality, `saved_review_fingerprint is None`, an enabled
`save_review` button, the existing unsaved caption, and no `Review saved locally` success message.

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' \
  -m pytest tests/apps/test_streamlit_app.py::test_local_save_failure_preserves_retryable_unsaved_review_without_raw_details -q
```

Expected: both parameter cases fail because the unhandled store exception appears in
`app.exception` and the fixed recovery message is absent.

- [ ] **Step 3: Implement the minimal boundary**

Wrap the existing `review_store.save(review_state)` call in `try/except (OSError, ValueError)`.
Render the exact fixed error in the exception branch. Move the existing saved-fingerprint update,
success notice, and `st.rerun()` into the `else` branch without changing them.

- [ ] **Step 4: Verify GREEN and adjacent recovery paths**

Run:

```bash
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py::test_local_save_failure_preserves_retryable_unsaved_review_without_raw_details \
  tests/apps/test_streamlit_app.py::test_current_review_id_is_copyable_and_used_in_save_confirmation \
  tests/apps/test_streamlit_app.py::test_delete_saved_review_race_uses_fixed_recovery_without_raw_details \
  tests/apps/test_streamlit_app.py::test_symlinked_review_store_has_safe_recovery_and_disables_storage_actions \
  -q
```

Expected: five cases pass: two parameterized failure cases plus three existing success/recovery cases.

- [ ] **Step 5: Run complete verification**

Run:

```bash
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m ruff check .
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest -q
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m scopeproof_core.cli benchmark
git diff --check
```

Expected: Ruff passes; all offline tests pass except the intentional live-network skip; all 12
benchmark cases and 13 criteria execute with zero mismatches, zero must-have False Ready, zero False
Blocker, and zero unexecuted declared categories; diff hygiene is clean.

- [ ] **Step 6: Run a local health smoke**

Start the branch application on loopback, require `/_stcore/health` to return `ok`, then stop it
cleanly. This is application-health evidence only, not proof of the patched failure path or external
validation.

- [ ] **Step 7: Commit the bounded slice**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py \
  docs/superpowers/specs/2026-07-14-local-save-failure-recovery-design.md \
  docs/superpowers/plans/2026-07-14-local-save-failure-recovery.md
git commit -m "fix: recover from local save failures"
```
