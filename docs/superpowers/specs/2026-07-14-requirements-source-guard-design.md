# Requirements Source Guard Design

## Problem

`CriteriaRevision.source_text` and `ReviewBundle.source_text` currently accept whitespace-only
strings. A validated review can therefore persist and export an empty "Confirmed Requirements
Source" section even though ScopeProof presents the requirements as user-confirmed.

## Decision

Add Pydantic field validators to both persisted schemas. Reject any source string whose
`strip()` result is empty, while returning valid input unchanged. This preserves source fidelity
and makes the invalid state impossible at the schema boundary.

The stable validation message is `requirements source must contain non-whitespace text`.

## Scope

- Validate `CriteriaRevision.source_text`.
- Validate `ReviewBundle.source_text`.
- Cover direct construction, JSON validation, lifecycle revision, and valid whitespace
  preservation.

No exporter, gate, UI, status, or version behavior changes.

## Verification

Use failing regression tests first, then run related schema, lifecycle, reporting, storage, CLI,
and app tests. Finish with Ruff, the full suite, deterministic benchmark, archived-wheel install,
identity checks, invalid/valid installed probes, and a live health smoke test.
