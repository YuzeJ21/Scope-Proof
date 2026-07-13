# Gate Recovery Guidance Design

## Problem and evidence

The local Streamlit audit reached a deterministic Blocked demo summary that displayed only
`blocking_criteria, conditional_criteria, unresolved_criteria`. These reason codes are reproducible
audit facts, but a first-time operator cannot tell which criteria need attention or which action is
allowed. The same raw-only output appears in Markdown exports.

The evaluator currently emits nine codes: `required_checks_failing`, `blocking_criteria`,
`conditional_criteria`, `unresolved_criteria`, `criteria_not_confirmed`, `partial_ingestion`,
`ingestion_failed`, `checks_not_passing`, and `final_acceptance_required`.

## Decision

Add a core-only pure function:

```python
gate_guidance(gate: GateDecision) -> list[str]
```

It consumes an already validated `GateDecision` and returns deterministic guidance in the same
de-duplicated order as `reason_codes`. It never recalculates or changes the verdict.

Criterion-scoped messages include the sorted IDs already present in `blocking_criteria`,
`conditional_criteria`, or `unresolved_criteria`. The messages distinguish action from proof:

- Blocking criteria must be reviewed for required changes or missing/partial evidence.
- Conditional criteria or exceptions must be explicitly reviewed before acceptance.
- Unresolved criteria require an explicit human decision; ScopeProof does not decide them.
- Criteria must be confirmed before analysis.
- Partial or failed ingestion requires retrying or documenting missing public-repository data.
- Failing, pending, or unavailable required checks must be resolved or awaited outside ScopeProof.
- Final acceptance may be recorded only after the reviewer has reviewed criteria and evidence.

An unknown future reason code produces a conservative fallback that preserves the exact code and
asks the operator to review it before acceptance. Unknown codes are never silently dropped.

## Surfaces

- Streamlit retains `Gate reasons:` and adds a `What to do next` list directly below it.
- Markdown retains `## Gate Reasons` and adds `## What To Do Next`.
- HTML retains the verdict and adds escaped gate reasons and guidance sections.
- JSON remains the canonical validated model with raw reason codes; no schema change is needed.
- CSV remains criterion-level and keeps its existing `recommended_action` column.

## Alternatives considered

1. Streamlit-only mapping is smaller but leaves downloaded reports without recovery guidance.
2. Persisting guidance in `GateDecision` makes derived prose part of the evidence contract and creates
   unnecessary migration/versioning pressure.
3. Recommended shared pure helper keeps core/UI separation, consistent exports, and deterministic
   behavior without changing stored truth.

## Boundaries

Do not change the evaluator, reason-code order, GateDecision schema, criterion status, evidence
requirements, human-resolution rules, final-acceptance rules, or gate precedence. Guidance must not
tell users to accept, waive, or mark evidence as sufficient. Do not execute PR code, call paid APIs,
or add dependencies.

## Verification

Tests first cover all nine known codes, exact criterion-ID inclusion, stable order, de-duplication,
and unknown-code fallback. Exporter tests require raw reasons and derived guidance together.
Streamlit AppTest requires the Blocked demo summary to expose actionable but non-prescriptive copy.
Full Ruff, pytest, deterministic benchmark, local runtime inspection, and protected-main checks are
required before merge. This product copy slice does not require a package-version bump or release.
