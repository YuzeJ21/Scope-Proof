# Runtime Record Timestamp Clarity Implementation Plan

**Goal:** Show the persisted UTC timestamp on every saved runtime-evidence card without changing
evidence or gate semantics.

**Architecture:** Keep the change in the Streamlit presentation layer. Read the existing
Pydantic-validated `RuntimeEvidence.timestamp` and render its JSON representation in the existing
card. The core model, lifecycle, persistence, reporting, and deterministic gate remain unchanged.

## Task 1: Lock the omission with a regression test

- Extend `tests/apps/test_streamlit_app.py` with a fixed-time saved runtime record.
- Require `**Recorded at (UTC):** 2026-07-14T12:10:00Z` in the rendered Markdown tree.
- Run the focused test and confirm it fails because the timestamp row is absent.

## Task 2: Render the stored timestamp

- In `apps/web/app.py`, derive the timestamp from
  `item.model_dump(mode="json")["timestamp"]`.
- Add the labeled row after reviewer and before limitations.
- Run the focused test and adjacent runtime-record tests to green.

## Task 3: Verify without inventing evidence

- Run Ruff, the complete offline suite, deterministic benchmark, and `git diff --check`.
- Run the workbench on loopback and require exact health `ok`.
- Verify unchanged prerequisite and final-acceptance browser boundaries. Do not submit a fabricated
  runtime record for visual evidence.

## Task 4: Publish through protected main

- Review and commit only the app, tests, design, and plan.
- Push a `codex/` branch and open a ready PR without comments, labels, or reviewers.
- Wait for required `verify` and CodeQL, squash-merge with the exact head SHA, then require merged-
  main CI and CodeQL success and exact local/remote synchronization.
- Do not publish a release for this presentation-only slice. Reconcile live GitHub truth and
  rotate immediately into the next evidence-backed local improvement or genuine external input.
