# Storage-Unavailable Save Guidance Implementation Plan

**Goal:** Explain an unavailable local-save action beside the disabled Save control while
preserving the open review and export path.

**Architecture:** Add one conditional Streamlit warning in the existing Summary & Export section.
Use the already-computed `review_store_available` state; do not change the core engine or storage
adapter.

## Task 1: Lock the missing recovery contract with a failing test

Update `tests/apps/test_streamlit_app.py` using an existing unsafe local-store fixture.

- Complete the demo analysis.
- Require the exact point-of-action warning.
- Require Save to remain disabled.
- Require the current review and unsaved fingerprint to remain unchanged.
- Require all three download controls to remain available.
- Require the rendered recovery text not to contain the temporary local path.

Run the focused test and require it to fail because the new warning is absent.

## Task 2: Add the smallest UI implementation

Update `apps/web/app.py` in the Summary & Export section.

- When `review_state is not None` and `review_store_available` is false, render the fixed warning
  from the design immediately before the Save button.
- Leave the existing button disable expression and successful/failed save paths unchanged.

Run the focused test and adjacent local-storage/save tests.

## Task 3: Verify and review

- Ruff.
- Full pytest suite.
- Deterministic benchmark with all declared cases executed and zero mismatches, must-have
  false-ready, or false-blocker.
- Wheel build and archive integrity.
- Live loopback health smoke.
- Independent task-contract and whole-branch review.
- `git diff --check` and a clean worktree.

## Task 4: Integrate through protected main

If the reviewed branch remains based on current `origin/main`, push it and create one ready PR.
Do not add the external-evidence label, comments, reviewers, or release. Merge only the exact reviewed
head after required CI and CodeQL pass. Fast-forward local main, rerun exact-main verification,
confirm post-merge CI/CodeQL, and remove the temporary branch/worktree.
