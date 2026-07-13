# Final-Acceptance Boundary Design

## Problem

A current-browser audit of the deliberately constructed demo confirmed that manual runtime evidence
already has explicit prerequisites, an empty-state-disabled save button, and product-facing fallback
errors. The remaining boundary is final acceptance: `Record final acceptance` appears immediately
after the selected criterion's resolution controls, without a local heading or explanation. In the
same viewport, the review can still be `Blocked` with every criterion unresolved while the button is
enabled. That is consistent with the append-only lifecycle contract, but the presentation can imply
that final acceptance resolves the selected criterion or overrides the deterministic gate.

## Decision

Clarify the existing boundary without changing behavior:

- Add a `Final review acceptance` heading immediately before the existing button.
- Explain that the action records a review-level event, does not resolve individual criteria, and
  does not override the deterministic gate.
- Tell reviewers to review every criterion and its evidence before recording final acceptance.
- Keep the existing button label, key, enabled state, event shape, lifecycle service, and success
  message unchanged.

The control remains near resolution history because both are append-only reviewer events. The new
heading separates review-level acceptance from the selected criterion's decision controls.

## Alternatives Considered

1. Clarify the boundary in place. Selected because it resolves the observed ambiguity with no domain
   or interaction change.
2. Move final acceptance into `Summary & Export`. Rejected because it creates broader layout churn
   and separates the action from its append-only history.
3. Disable final acceptance until every criterion is resolved. Rejected because the accepted
   lifecycle contract deliberately records final acceptance independently and relies on gate
   precedence to prevent False Ready.

## Architecture and Data Flow

Only `apps/web/app.py` changes. It renders static explanatory copy before the existing
`record_final_acceptance` button. `ResolutionEvent`, `append_resolution`, gate evaluation, persisted
state, exports, and the core engine remain unchanged.

## Safety and Accessibility

- Final acceptance cannot turn unresolved, blocking, conditional, or failed-check states into Ready.
- No criterion decision, evidence, runtime observation, or acceptance is inferred.
- A semantic heading improves reading order and makes the review-level action easier to identify for
  assistive-technology users. Screenshot inspection cannot establish keyboard or screen-reader
  conformance, so existing automated and browser checks remain bounded evidence.
- No network, API, billing, telemetry, dependency, or untrusted-code behavior changes.

## Verification

- Add an AppTest that requires the heading and exact boundary copy in an analyzed unresolved review.
- In the same regression, record final acceptance with all demo criteria unresolved and prove the
  review remains `Blocked` with the same blocking and unresolved criterion sets.
- Preserve the existing lifecycle regression proving a fully resolved review becomes Ready only
  after explicit final acceptance.
- Run focused AppTests, Ruff, the complete offline test suite, the 12-case deterministic benchmark,
  `git diff --check`, a clean-built installed-wheel health check, and a same-state browser comparison.

## Out of Scope

- Gating or disabling the final-acceptance control.
- Changing final-acceptance, resolution, gate, export, or persistence schemas.
- Recording invented runtime evidence or claiming the demo as external validation.
- Reorganizing unrelated Streamlit sections.
