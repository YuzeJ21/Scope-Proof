# Criteria Authoring Draft Lifecycle Implementation Plan

> **Goal:** Make unsubmitted add/split criterion text truthful across save, export,
> replacement, and successful-operation boundaries.

## Task 1: Add RED regression coverage

In `tests/apps/test_streamlit_app.py`, add focused AppTests that prove:

1. non-empty add or split text on a saved analyzed review disables Save and downloads,
   requires replacement approval, shows pending copy, and changes sidebar availability;
2. clearing the authoring drafts restores the last-saved state without mutating the
   review;
3. a successful add clears add text and a successful split clears split text.

Run only these tests and record the expected failures against current `main`.

## Task 2: Implement the bounded Streamlit lifecycle

In `apps/web/app.py`:

- add `_criteria_authoring_draft_pending()` and
  `_clear_criteria_authoring_drafts()` helpers;
- consume a session-only reset marker before pending state is derived;
- include authoring drafts in `has_pending_review_input`;
- add exact summary copy and an explicit clear action;
- let add/split consume their own draft when no other state requires replacement
  approval;
- arrange a next-run reset only for the successfully consumed input.

Do not change core models, lifecycle, deterministic gates, storage, or exporters.

## Task 3: Verify focused and adjacent behavior

Run the new tests, then the adjacent criteria editing, confirmation, replacement,
save/export, and operation-error recovery tests. Require GREEN before broad checks.

## Task 4: Verify and publish safely

Run Ruff, the full pytest suite, deterministic benchmark, `git diff --check`, and a
loopback Streamlit health smoke. Commit intentionally, push the `codex/` branch, open
a ready PR, wait for required `verify` and CodeQL, merge only if green, then verify the
exact merge commit on `main` before continuing the persistent improvement loop.
