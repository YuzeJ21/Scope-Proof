# Finding Context Guard Design

## Problem

`Finding` carries the explanation and recovery context for every criterion verdict. Its required
`reason` and `recommended_action` strings, plus members of `missing_evidence` and `contradictions`,
currently have no non-whitespace validation.

A controlled probe created a `missing` finding with a spaces-only reason, tab-only missing-evidence
entry, spaces-only contradiction, and newline-only recommended action. The containing
`ReviewBundle` passed Pydantic validation. Markdown export then rendered a blank matrix concern,
blank reason, blank missing-evidence bullet, and blank recommended action. The Streamlit detail
path consumes the same values.

This violates the core rule that a verdict must cite explicit evidence or identify what evidence
is missing, and it removes the recovery guidance needed to act on a blocked result.

## Root cause

Trusted verification code currently emits explicit text, but `Finding` itself accepts whitespace.
Persisted records are revalidated through Pydantic, so the schema must enforce the invariant rather
than relying on the current producer or repairing output later.

## Approaches considered

1. **Pydantic field and list validators — selected.** Reject whitespace-only required explanation
   strings and list members once for direct callers, persistence, exporters, and UI consumers.
2. **Exporter/UI fallback copy.** This would conceal invalid persisted objects and leave JSON or
   future adapters inconsistent.
3. **Verification-service checks.** This protects only the current producer and can be bypassed by
   imported or modified persisted records.

## Design

Add a before `field_validator` for `reason` and `recommended_action`. Empty, spaces-only, and
tab/newline-only strings raise `ValueError("must contain non-whitespace text")` before Pydantic's
length behavior can produce inconsistent messages.

Add an after `field_validator` for `missing_evidence` and `contradictions`. If any list member is
whitespace-only, raise `ValueError("finding context must contain non-whitespace text")`.

Return valid strings and lists unchanged. Empty context lists remain valid: a nonblank reason may
already state why evidence is absent, while contradictions are optional. Do not infer, add, strip,
or reorder any finding content.

## Scope boundaries

The change does not alter finding statuses, evidence IDs, evidence levels, confidence, gate
precedence, verification thresholds, exporters, Streamlit rendering, or version `0.1.18.dev0`.
It does not require a nonempty missing-evidence list for every missing finding; it requires the
mandatory reason and recovery action to be explicit and every supplied list member to be real text.

## Verification

Regression-first tests cover three blank forms for each required string and each list field,
preservation of valid surrounding whitespace, and acceptance of empty lists. Run related schema,
verification, gate, reporting, lifecycle, and storage tests; Ruff; the full offline suite;
deterministic benchmark; `git diff --check`; archived-wheel install; an installed source-independent
probe; and loopback workbench health. Integrate only through a green protected PR and verify CI and
CodeQL on the exact merge SHA.

These are controlled schema, export, packaging, benchmark, and loopback-health results, not external
PR runtime evidence, customer validation, or adoption. No billing, paid API or LLM, private
repository, organization, second account, fork test, synthetic validation, or invented evidence is
involved.
