# Prepared-to-Confirm Transition Implementation Plan

**Goal:** Expose the required confirmation step immediately after criteria preparation while preserving explicit human confirmation and editable inputs.

**Architecture:** Derive a presentation-only `requirements_are_prepared` boolean from existing session state in `apps/web/app.py`. Use it to disable an idempotent repeat action and render a native anchor to the existing confirmation heading. Keep the core engine and review lifecycle unchanged.

## Task 1: Lock the transition contract

- Add failing AppTests asserting that demo-loaded requirements are marked prepared, repeat preparation is disabled, and a continuation link targets `#2-confirm-criteria`.
- Add a failing AppTest asserting that editing requirements removes the prepared state and re-enables preparation.
- Run the focused tests and record the expected failures.

## Task 2: Implement the presentation state

- Derive `requirements_are_prepared` only when criteria exist and `requirements_text` exactly equals `session_state["source_text"]`.
- Disable `Prepare criteria` for that unchanged prepared state.
- Before confirmation, render the completion message and native in-page continuation link.
- Run the focused tests and all Streamlit AppTests.

## Task 3: Advance development identity

- Change the repository version contract test first to require `0.1.17.dev0` and verify it fails.
- Update `scopeproof_core/version.py` to `0.1.17.dev0`.
- Preserve every README `v0.1.16` verified-release URL and checksum instruction.

## Task 4: Verify exact source and package behavior

- Run Ruff, all offline tests, deterministic benchmark, and `git diff --check`.
- Build and clean-install the wheel in a fresh temporary directory.
- Require distribution, module, CLI, web launcher, and new-review identities to equal `0.1.17.dev0`.
- Require `pip check`, installed benchmark `12/13/0/0/0`, and exact web health `ok`.
- Browser-test the packaged demo-loaded state at 1280 by 720, inspect the screenshot, and require no browser diagnostic entries.

## Task 5: Protected integration

- Commit intentionally, push the `codex/` branch, and open a ready PR with the audit evidence and verification boundaries.
- Merge only after required checks pass.
- Verify post-merge main CI and CodeQL, fast-forward local main, clean the owned worktree and branch, and confirm the latest public release remains `v0.1.16`.
