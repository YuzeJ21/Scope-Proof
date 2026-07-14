# Requirements Source Guard Implementation Plan

1. Add regression tests proving both persisted source fields reject spaces, tabs, and newlines.
2. Add lifecycle coverage proving a blank revised source cannot create a new revision.
3. Add valid controls proving meaningful source text, including surrounding whitespace, is
   preserved exactly.
4. Run the focused tests and confirm the current implementation fails for the intended reason.
5. Add the smallest Pydantic validators to `CriteriaRevision` and `ReviewBundle`.
6. Run focused and related tests, Ruff, full pytest, deterministic benchmark, wheel install and
   runtime smoke verification.
7. Publish through a protected pull request, merge only after required checks pass, and verify
   CI and CodeQL against the exact merged-main SHA.
