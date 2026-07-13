# Unsaved Review Replacement Guard Implementation Plan

**Goal:** Prevent one-click loss of an unsaved validated review while preserving
an explicit discard path.

**Architecture:** Reuse the session-only `ReviewState` fingerprint contract to
derive one `has_unsaved_review` flag before the reopen/start controls render.
Gate only operations that replace the current review, and clear the approval
after a permitted replacement.

**Tech stack:** Python, Streamlit, Pydantic, pytest AppTest.

---

## Task 1: Add failing replacement-guard tests

Extend `tests/apps/test_streamlit_app.py` to assert the warning, checkbox, and
disabled state for reopen, demo load, public-PR fetch, and criteria preparation
when a validated review is unsaved. Assert that explicit approval enables these
actions, and that replacement resets the approval.

Retain the focused RED output before implementation.

## Task 2: Implement the shared approval gate

Update `apps/web/app.py`:

1. add a `replace_unsaved_review_confirmed` session default;
2. add helpers for current save equality and replacement authorization;
3. render the warning and approval before reopen/start controls;
4. include replacement authorization in the four button disabled conditions;
5. clear the approval inside each successful replacement path and analysis reset;
6. keep all review-internal controls unchanged.

Run focused tests to GREEN.

## Task 3: Verify product boundaries

Run focused app/lifecycle/storage tests, Ruff, and the full suite. Run all 12
deterministic benchmark cases and confirm zero must-have False Ready, zero False
Blocker, and zero mismatches. Build and install the wheel in a clean temporary
environment, run its benchmark, smoke the packaged workbench health endpoint,
and verify protected and approved replacement states in the in-app browser.

## Task 4: Publish through protected main

Commit the reviewed slice, push `codex/unsaved-review-replacement-guard`, open a
pull request without reviewers or comments, wait for all required checks, merge
only when green, verify merged-main CI and CodeQL, synchronize local `main`, and
remove the worktree and branches.
