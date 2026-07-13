# Human-Decision Impact Guidance Design

## Problem

The Criterion Detail surface offers six explicit `HumanDecision` values, but the selector exposes
only their labels. Their deterministic effects differ materially: `change_required` blocks,
`accepted_exception` is conditional, `rejected_finding` does not resolve the criterion,
`manually_verified` requires an external evidence level, and `not_in_scope` records an exception.
Without local guidance, a first-time reviewer must infer these effects or learn them after saving an
append-only event.

## Decision

Add deterministic selected-decision guidance:

- Add `decision_guidance(decision: HumanDecision) -> str` to the UI-independent gate-guidance module.
- Return one fixed, evidence-bound explanation for every `HumanDecision` value.
- Before a selection, show `Select a decision to see its deterministic gate impact.`
- After a selection, show `Decision impact: <exact guidance>` directly below the selector.
- Keep the selector values, placeholder, save readiness, lifecycle, gate evaluator, schemas, exports,
  and persisted events unchanged.

## Decision Meanings

- `accepted`: records reviewer acceptance and treats the criterion as resolved.
- `accepted_exception`: records an explicit exception and makes the review conditional.
- `change_required`: makes the criterion blocking until a later decision replaces it.
- `rejected_finding`: rejects the provisional finding but does not resolve the criterion; the
  finding continues to control the gate.
- `manually_verified`: records external manual verification at the selected evidence level and
  treats the criterion as resolved.
- `not_in_scope`: records a scope exception, removes the criterion from active blocking/unresolved
  checks, and can leave the review conditional.

## Alternatives Considered

1. Put fixed guidance in the core gate-guidance module. Selected because gate impact is domain
   meaning and remains reusable without depending on Streamlit.
2. Keep a dictionary inside `apps/web/app.py`. Rejected because it would duplicate domain meaning in
   the presentation layer and make drift harder to detect.
3. Put long descriptions in select options or a separate help page. Rejected because long options
   scan poorly and detached help does not support the decision at the moment it is made.

## Safety and Accessibility

- Guidance describes existing evaluator behavior and never changes a decision or gate.
- No decision is preselected, inferred, or saved automatically.
- The caption appears in reading order immediately after the labeled selector; screenshot evidence
  cannot establish full keyboard or screen-reader conformance.
- No runtime evidence, API, billing, network, telemetry, dependency, or untrusted-code behavior
  changes.

## Verification

- Unit-test exact guidance coverage for all six enum values.
- AppTest the no-selection prompt and every selected decision's rendered impact.
- Preserve explicit-selection, save-disabled, lifecycle, and gate regressions.
- Run Ruff, the complete offline suite, the 12-case deterministic benchmark, `git diff --check`, a
  clean-installed wheel health check, and same-state browser inspection.

## Out of Scope

- Changing decision semantics, reviewer-note requirements, or final acceptance.
- Adding confirmation dialogs, undo, event deletion, or automatic recommendations.
- Treating any guidance as evidence that a criterion is satisfied.
