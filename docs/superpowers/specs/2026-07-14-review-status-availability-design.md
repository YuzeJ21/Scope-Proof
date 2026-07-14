# Review Status Availability Design

## Reproduced gap

A current-main browser audit followed the deliberately constructed demo through
source load, explicit criteria confirmation, and deterministic analysis. After
analysis, all four criteria remained unresolved and the deterministic verdict
remained `Blocked`, but the persistent sidebar reported:

> Complete — Review and export available

The underlying product state is honest: evidence review and exports are
available. The `Complete` prefix is not. ScopeProof has no authoritative signal
that the reviewer finished reviewing every criterion, and final acceptance is
intentionally independent from criterion resolution and cannot override blocker
precedence.

## Decision

When analysis exists, render the final sidebar status as:

> Available — Review evidence and export

Keep the status plain text because the existing browser verification found no
stable deep Summary fragment suitable for a reliable navigation affordance.

## Alternatives considered

1. **Use `Available`** — selected because it states exactly what analysis makes
   possible without claiming reviewer completion.
2. **Use `Next`** — rejected because evidence inspection, human decisions,
   runtime records, local save, and exports are parallel actions rather than one
   required next step.
3. **Derive `Complete` from final acceptance or a Ready verdict** — rejected
   because final acceptance is an independent append-only event and a blocked
   or conditional review can legitimately retain it; changing that contract is
   outside this presentation fix.

## Architecture and data flow

Change only the Streamlit sidebar label and its AppTest contracts. Continue
deriving availability from the existing `has_analysis` Boolean. Do not add
session state or change the review, lifecycle, gate, schema, export, storage, or
navigation layers.

## Verification

- Add a regression proving an analyzed demo with unresolved criteria reports
  `Available` and does not claim review/export completion.
- Update the existing sidebar navigation contract to the same exact wording.
- Run focused tests, Ruff, the complete offline suite, the deterministic
  benchmark, `git diff --check`, and a current-source loopback browser check.

## Evidence limits and boundaries

The controlled demo and screenshots prove only the workbench's rendered state
and deterministic test behavior. They are not external PR evidence, runtime
verification of third-party code, user-adoption evidence, or proof of
correctness. No paid API/LLM, billing, fork, organization, private repository,
synthetic validation, notification, release, or untrusted-code execution is
introduced.
