# Resolution Event Lineage Integrity Implementation Plan

1. Add failing schema and gate-boundary regressions for blank, duplicate, zero,
   and future resolution-event identity/lineage inputs.
2. Add a failing lifecycle regression for appending an already-used event ID.
3. Implement the smallest Pydantic state invariants and lifecycle collision guard.
4. Run focused tests, Ruff, full pytest, benchmark, package health, and runtime
   smoke checks.
5. Publish through a protected pull request and verify the exact merged main SHA.
