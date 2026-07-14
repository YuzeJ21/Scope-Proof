# Requirements Draft Persistence Guard Implementation Plan

> **Goal:** Make unprepared requirements text truthful across save, export,
> replacement, discard, and prepare boundaries.

## Task 1: Add RED regression coverage

In `tests/apps/test_streamlit_app.py`, add focused AppTests proving that a changed
requirements input on a saved analyzed review:

- is not claimed saved or exportable;
- blocks unrelated replacement actions and changes sidebar status;
- has an explicit discard path that restores authoritative source text without
  mutating the review;
- can still be consumed through **Prepare criteria** when it is the only pending input.

Run only these tests and record the expected failures against current `main`.

## Task 2: Implement the bounded Streamlit guard

In `apps/web/app.py`:

- add a deterministic requirements-draft comparison helper;
- consume a next-run discard reset before pending state is derived;
- include the new pending flag in `has_pending_review_input`;
- derive a prepare-specific blocker that excludes only the draft being consumed;
- add exact summary copy and explicit discard recovery.

Keep all core schemas, lifecycle services, deterministic gates, persistence, and
exports unchanged.

## Task 3: Verify focused and adjacent behavior

Run new tests, then adjacent criteria preparation, pending-input, replacement,
save/export, and source-reopen tests. Require GREEN before broad checks.

## Task 4: Verify and publish safely

Run Ruff, the full pytest suite, deterministic benchmark, `git diff --check`, and a
loopback Streamlit health smoke. Commit intentionally, push the `codex/` branch, open
a ready PR, wait for required `verify` and CodeQL, merge only if green, and verify the
exact merge commit on `main` before continuing the persistent loop.
