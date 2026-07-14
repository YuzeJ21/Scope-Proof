# Lifecycle State Revalidation Design

## Problem

`ReviewState` now rejects an active lifecycle review that differs from `bundle.review`, but Pydantic
models remain mutable and `model_copy(...)` does not rerun validators. A caller can therefore pass
an already-constructed contradictory state into lifecycle operations.

A current-main probe showed three different outcomes from the same invalid input:

- `revise_criteria(...)` accepted it and discarded the active bundle, concealing the contradiction;
- `append_resolution(...)` copied the top-level review into the bundle, silently normalizing it;
- `append_runtime_evidence(...)` returned another contradictory state.

The persistence boundary now rejects these objects, but lifecycle behavior can still depend on which
operation happens before persistence. An evidence assistant must reject contradictory audit state at
the lifecycle boundary rather than repair or propagate it implicitly.

## Intended Outcome

Every public lifecycle operation that consumes `ReviewState` reconstructs and validates the complete
state from `model_dump(mode="python")` before reading or changing it:

- `revise_criteria(...)`;
- `confirm_criteria(...)`;
- `append_resolution(...)`;
- `append_runtime_evidence(...)`.

Valid states retain existing behavior. Invalid mutable or `model_copy(...)` states raise their
Pydantic validation error before lifecycle-specific mutation, gate evaluation, or normalization.

## Selected Design

Add one private `_validated_state(state)` helper in the core lifecycle module. It returns
`ReviewState.model_validate(state.model_dump(mode="python"))`. Each public state-changing operation
rebinds its input to this validated reconstruction as its first statement.

This is selected over:

- relying on type annotations, because an instance can be mutated after validation;
- validating only active review identity by hand, because that would duplicate the schema invariant
  and miss other nested validation rules;
- validating only at save/export time, because lifecycle operations would still conceal, propagate,
  or act on contradictory state;
- enabling assignment validation globally, because that is a broader compatibility change and does
  not address `model_copy(...)` by itself.

## Compatibility and Error Behavior

- Valid lifecycle transitions, gates, event history, runtime evidence, and pending criteria remain
  unchanged.
- A contradictory active review fails with the existing stable message: `active bundle review must
  match lifecycle review`.
- `confirm_criteria(...)` validates state before applying its separate bundle-less pending-revision
  precondition.
- Validation rejects bad input; no identity is inferred and no audit state is silently rewritten.
- The helper stays in `scopeproof_core` and adds no Streamlit or GitHub dependency.

## Verification

Regression tests pass one validator-bypassed contradictory state through every public lifecycle
mutation and require rejection. Existing valid lifecycle tests remain green. Full verification also
includes Ruff, all offline tests, the deterministic 12-case benchmark, a clean installed wheel and
benchmark, and the installed workbench health endpoint.

## Out of Scope

- Global frozen models or assignment validation.
- Changes to review schemas, gates, evidence levels, final acceptance, persistence format, UI, or
  GitHub workflows.
- Generic code review, security scanning, auto-fix behavior, untrusted repository execution, paid
  APIs, billing, organizations, second accounts, private repositories, forks, synthetic evidence,
  comments, or a release.
