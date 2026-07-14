# Public PR Fetch Recovery Plan

**Goal:** Make a failed public-PR fetch clearly retryable without implying that
the user's entered requirements or prepared criteria were lost.

1. Add a Streamlit regression test that prepares a criterion, injects a typed
   GitHub network failure, and requires safe recovery copy, preserved inputs,
   preserved criteria, and an enabled retry action; require RED.
2. Extend only the existing `GitHubIngestionError` rendering with the bounded
   recovery contract; require the focused test and Ruff to pass.
3. Run the full offline suite, deterministic benchmark, `git diff --check`, and
   a real loopback Streamlit health check.
4. Review the exact four-file diff, publish one protected PR, require both
   `verify` checks and CodeQL, merge only at the reviewed SHA, and verify main.
5. Do not create a release for this copy-only development change.
