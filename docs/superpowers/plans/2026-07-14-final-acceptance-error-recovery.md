# Final-Acceptance Error-Recovery Plan

**Goal:** Recover safely from expected final-acceptance lifecycle validation failures without
changing final-acceptance or gate semantics.

## Task 1: Lock the failure contract

Add a Streamlit AppTest that patches `append_resolution` to raise a path-bearing `ValueError` when
the final-acceptance control is clicked. Require a failing baseline with a Streamlit exception and
then require fixed recovery copy, no exception/raw path, exact state preservation, zero events, no
success notice, and an enabled retry after implementation.

## Task 2: Add the bounded UI recovery

Wrap only final-acceptance event construction and append in `try/except ValueError`. Render the fixed
message on failure. Move the existing state/session updates and rerun into `else` so success behavior
is unchanged.

## Task 3: Verify and integrate

Run focused final-acceptance tests, Ruff, the full offline suite, deterministic benchmark, wheel
integrity, `git diff --check`, and a loopback health smoke. Review the complete diff for scope and
semantic preservation. Publish one ready PR without labels, comments, reviewers, or release. Merge
only the exact reviewed commit after CI and CodeQL pass, reverify exact main, then remove the
temporary branch/worktree.
