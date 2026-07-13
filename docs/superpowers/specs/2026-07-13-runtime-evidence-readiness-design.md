# ScopeProof Runtime-Evidence Readiness Design

## Problem

The Streamlit workbench exposes `Save manual runtime evidence` immediately after analysis, even
when all five required text fields are empty. Clicking it sends empty values to the validated
`RuntimeEvidence` model and displays five raw Pydantic errors. The model correctly rejects the
record and nothing is persisted, but the normal first-use path presents implementation-level
validation details instead of telling the reviewer what is required before submission.

This is a user-interface readiness gap, not a schema, evidence, lifecycle, or gate defect.
Runtime evidence is already append-only, restricted to E3 or E4, and unable to upgrade static
findings or gate truth.

## Chosen Design

Keep the existing fields and lifecycle service. Define the submission as ready only when artifact
reference, scenario, environment, observed result, and reviewer each contain non-whitespace text.
Show concise guidance naming those required fields and stating that limitations are optional.
Disable `Save manual runtime evidence` until the submission is ready.

On a valid click, continue constructing the Pydantic `RuntimeEvidence` object and appending it
through `append_runtime_evidence`. Keep the validation exception handler as defense in depth, but
translate any unexpected validation failure into a short product-facing message rather than
rendering raw Pydantic output.

Do not change final-acceptance behavior. Final acceptance remains an explicit append-only review
event. The deterministic gate continues to enforce blocker precedence, so final acceptance cannot
turn unresolved must-have findings into Ready.

## Alternatives Considered

1. Keep the button enabled and translate only the Pydantic error. This avoids raw implementation
   details but still makes an invalid click the expected first-use path.
2. Move runtime evidence into a submitted Streamlit form. This would batch field updates, but it is
   unnecessary structural churn for a five-field readiness rule.
3. Gate final acceptance on all criterion resolutions. The existing lifecycle deliberately records
   final acceptance independently and relies on deterministic gate precedence. The observed issue
   does not justify changing that contract.

## Components and Data Flow

- `apps/web/app.py` owns presentation readiness. It derives a Boolean from the five required widget
  values and uses it for guidance and button state.
- `RuntimeEvidence` remains the authoritative persisted-object validator.
- `append_runtime_evidence` remains the only runtime-evidence mutation path and continues to leave
  static findings and gate truth unchanged.
- `ResolutionEvent`, final acceptance, exports, and persisted schemas are unchanged.

## Error and Safety Behavior

- Empty or whitespace-only required fields cannot trigger submission through the normal UI.
- Limitations remain optional and blank lines are discarded.
- Unexpected model validation failures receive a concise message instructing the reviewer to check
  the required fields and evidence level. Raw validation internals are not displayed.
- No untrusted repository code is executed, no runtime result is inferred, and no evidence level is
  upgraded automatically.

## Verification

- Add Streamlit AppTest coverage proving the save button is disabled for an empty submission.
- Prove whitespace-only required values do not enable the button.
- Prove the button becomes enabled only after all five required values are nonblank.
- Preserve the existing test proving a complete manual record is appended without changing static
  findings.
- Preserve lifecycle and final-acceptance regression coverage unchanged.
- Run focused AppTests, Ruff, the complete offline pytest suite, the 12-case deterministic benchmark,
  `git diff --check`, and a real local Streamlit HTTP/browser inspection of the disabled and enabled
  states.

## Out of Scope

- Changing runtime-evidence schema fields or evidence-level rules.
- Changing gate evaluation, final acceptance, human-resolution semantics, exports, or storage.
- Executing PR code or claiming the test fixture is external runtime evidence.
- Adding paid services, APIs, telemetry, or synthetic product validation.
