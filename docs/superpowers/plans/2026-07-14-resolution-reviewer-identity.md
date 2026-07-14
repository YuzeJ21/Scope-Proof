# Resolution Reviewer Identity Implementation Plan

**Goal:** Make newly recorded human-decision events explicitly attributable
without changing deterministic gate behavior.

**Architecture:** Keep identity capture in the Streamlit layer and validation in
the Pydantic `ResolutionEvent` schema. Continue using the existing lifecycle
append function and history renderer.

## Task 1: Add failing schema coverage

- Update `tests/schemas/test_models.py` with a whitespace-only reviewer case.
- Run the focused test and confirm it fails because blank reviewers are
  currently accepted.
- Add a `ResolutionEvent.reviewer` validator in
  `scopeproof_core/schemas/models.py`.

## Task 2: Add failing UI coverage

- Update `tests/apps/test_streamlit_app.py` to prove both decision actions are
  disabled until `decision_reviewer` is non-blank.
- Add cases proving criterion resolution and final acceptance persist the
  trimmed reviewer value.
- Run the focused tests and confirm the missing control/behavior is the failure.

## Task 3: Implement the UI slice

- Add `Decision reviewer (required)` near the resolution controls.
- Add missing-input guidance.
- Include reviewer readiness in both button disabled conditions.
- Pass the trimmed reviewer to both `ResolutionEvent` constructors.

## Task 4: Verify and publish

- Run Ruff, focused tests, full pytest, deterministic benchmark, `pip check`,
  and `git diff --check`.
- Run the local web health smoke and browser-check the reviewer workflow.
- Commit, push, open a ready PR, wait for protected checks, merge only when
  green, verify the exact merge SHA on `main`, clean up, and resume the next
  audit loop.

