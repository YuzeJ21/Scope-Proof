# Local Save Freshness Implementation Plan

**Goal:** Make local persistence freshness explicit without changing the review
record or deterministic gate contract.

**Architecture:** Keep one canonical `ReviewState` fingerprint in Streamlit
session state. Compare it with the current validated model at render time.
Update the fingerprint only after a successful local save or validated reopen,
and clear it when analysis is reset for another source.

**Tech stack:** Python, Streamlit, Pydantic, pytest AppTest.

---

## Task 1: Add failing UI contract tests

Extend `tests/apps/test_streamlit_app.py` to assert:

1. a newly analyzed review shows `Unsaved changes` and enables save;
2. a successful save survives its rerun, shows the exact saved-state label, and
   disables duplicate save;
3. a post-save human resolution restores `Unsaved changes` and enables save;
4. a reopened validated review begins saved and has save disabled.

Run the focused tests and retain the expected RED result before implementation.

## Task 2: Implement session-scoped save freshness

Update `apps/web/app.py`:

1. add defaults for the saved fingerprint and retained save notice;
2. add a small canonical fingerprint helper based on `ReviewState.model_dump_json()`;
3. clear the fingerprint in `_reset_analysis()`;
4. set it in `_hydrate_reopened_review()`;
5. compare current and saved fingerprints in Summary & Export;
6. rerun after save so the disabled state and retained notice are authoritative;
7. render precise saved/unsaved captions and disable only an identical repeat save.

Run the focused tests to GREEN.

## Task 3: Verify boundaries

Run focused app/lifecycle/storage tests, then Ruff and the full suite. Run the
deterministic benchmark and confirm zero must-have False Ready, zero False
Blocker, and zero mismatches. Build and install the wheel in a clean temporary
environment, rerun the packaged benchmark, and smoke the packaged workbench
health endpoint. Verify the new, saved, changed-after-save, and reopened states
in the in-app browser.

## Task 4: Publish through protected main

Commit the reviewed slice, push `codex/local-save-freshness`, open a pull request
without reviewers or comments, wait for every required check, merge only when
green, verify merged-main CI and CodeQL, synchronize local `main`, and remove the
worktree and branches.
