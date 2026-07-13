# Gate-Reason Guidance Design

## Context

The public v0.1.15 first-use audit shows the summary rendering internal reason codes directly:
`blocking_criteria, conditional_criteria, unresolved_criteria`. The recovery guidance below is
clear, but the line immediately under the verdict requires users to translate schema identifiers
before they can understand why the gate is not ready.

Source screenshot:
`/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.15-first-use-audit/06-summary.png`

The current product pattern already humanizes enum-like values with `_status_label`, which replaces
underscores with spaces and applies title case. This slice should reuse that pattern rather than
introducing a second label system.

## Decision

Render the summary reason line as:

`Gate reasons: Blocking Criteria · Conditional Criteria · Unresolved Criteria`

Each displayed label is derived deterministically from the recorded reason code with the existing
`_status_label` helper. The centered-dot separator matches ScopeProof's existing compact metadata
lines and makes the labels easier to scan than a comma-separated identifier list.

The UI must not display underscore-delimited reason identifiers in the summary. Raw reason codes
remain unchanged in the validated gate object and in Markdown, JSON, CSV, and HTML exports so that
machine-readable and audit behavior is preserved.

Unknown future reason codes remain visible: the same deterministic transformation produces a
readable title-cased label instead of hiding the reason.

## Boundaries

- No gate evaluation, reason-code generation, schema, persistence, export, or recovery-guidance
  change.
- No new dependency, paid API, external service, issue comment, release, or untrusted-code
  execution.
- The current `0.1.16.dev0` development version remains unchanged.
- AppTest regression coverage must prove readable labels are present and raw identifiers are absent
  from the rendered summary while the underlying gate retains its original reason codes.

## Verification

- Run the new AppTest as RED before implementation and GREEN afterward.
- Run the adjacent Streamlit tests, Ruff, full offline tests, and deterministic benchmark.
- Build and clean-install the `0.1.16.dev0` wheel; verify version identity, benchmark, and health.
- Exercise the packaged demo summary in the in-app browser, capture an updated screenshot, and
  compare it beside the v0.1.15 source screenshot at the same viewport and state.
- Integrate only through a green protected-main pull request. Do not publish a release.
