# Runtime-Evidence Error-Recovery Regression Plan

**Goal:** Lock the existing user-safe runtime-evidence validation recovery boundary with a
mutation-sensitive regression.

## Task 1: Add the characterization regression

In `tests/apps/test_streamlit_app.py`, complete the controlled demo form and patch
`append_runtime_evidence` to raise a path-bearing `ValueError`. Assert:

- the fixed user-facing recovery message is rendered;
- Streamlit reports no unhandled exception;
- raw validation text and the local path are absent;
- the exact review state and saved fingerprint are unchanged;
- no runtime record is appended;
- all form values remain available; and
- Save remains enabled for retry.

## Task 2: Prove mutation sensitivity

Temporarily replace the fixed recovery with raw exception rendering in the isolated worktree. Run
only the new test and require failure on the raw-detail assertion. Restore the production code with
`apply_patch`, rerun the test, and require success. Do not commit the mutation.

## Task 3: Verify and integrate

Run Ruff, the complete offline suite, deterministic benchmark, wheel integrity, `git diff --check`,
and a loopback health smoke. Review the complete base-to-head diff and require that only the
regression and its design records changed. Publish one ready protected PR without evidence labels,
comments, reviewers, or release. Merge only the exact reviewed head after CI and CodeQL pass, then
reverify exact protected main and clean the temporary branch/worktree.
