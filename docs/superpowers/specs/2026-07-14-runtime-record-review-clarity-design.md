# Runtime Record Review Clarity Design

## Context

The current goal requested an audit of the manual runtime-evidence form and final-
acceptance boundary. A current-browser audit of `main` at `51fe660` confirmed that the
original blank-submission defect is already closed:

- all five required runtime fields are visibly labeled;
- missing-field guidance names the exact incomplete fields;
- `Save manual runtime evidence` remains disabled for empty input;
- fallback validation errors use stable product copy instead of raw Pydantic output;
- final acceptance is labeled as a separate review-level event that cannot resolve
  criteria or override the deterministic gate.

Current screenshots are stored under
`/Users/yjian070/.codex/visualizations/2026/07/14/scopeproof-runtime-evidence-audit-current/`.
Focused schema, lifecycle, and Streamlit coverage passed with 38 tests.

The audit found a different current gap. A manual runtime record persists
`artifact_reference`, `scenario`, `environment`, `result`, `reviewer`,
`evidence_level`, and `limitations`, but the criterion-detail workbench renders only
the artifact, scenario, environment, result, and level. The reviewer and limitations
are absent from the visible saved record even though they are present in the validated
`RuntimeEvidence` object and exports.

## Goal

Make every saved manual runtime record visibly reviewable in the criterion-detail
workbench, including who supplied the observation and every recorded limitation.

## Approaches Considered

### 1. Bordered record container — selected

Render each runtime record in the existing Streamlit bordered-container pattern. Keep
the artifact and scenario as the leading line, then show environment, observed result,
evidence level, reviewer, and limitations as labeled fields. When limitations are
empty, state `No limitations recorded.`

This keeps records distinct when several observations target the same criterion and
makes limitations visible without requiring another interaction.

### 2. Extend the existing single markdown line

Append reviewer and limitations to the existing bullet. This is the smallest diff but
creates a dense line, makes multiple limitations difficult to scan, and makes field
boundaries unclear.

### 3. Put record details in a collapsed expander

This reduces vertical space, but hides the reviewer and limitations by default. Those
fields are material review context and should not require discovery.

## Selected Behavior

For every runtime record attached to the selected criterion, render:

1. artifact reference and scenario;
2. environment;
3. observed result;
4. evidence level;
5. reviewer;
6. every recorded limitation, or the explicit empty state
   `No limitations recorded.`

Retain `render_artifact_reference_markdown()` so URL safety and plain-identifier
escaping remain unchanged. Preserve list order from the validated model. Do not trim,
rewrite, infer, or upgrade evidence.

## Architecture and Boundaries

Only `apps/web/app.py` presentation and focused Streamlit AppTests change. The
`RuntimeEvidence` Pydantic model, lifecycle append path, persisted record, exporters,
static findings, criterion resolutions, final acceptance, and deterministic gate stay
unchanged.

This slice does not record real or invented runtime evidence. Tests use controlled
fixtures solely to verify rendering behavior and make no external-validation claim.

## Error and Accessibility Behavior

- Existing validated values are rendered exactly, except the artifact reference keeps
  its established safe-markdown transformation.
- Multiple limitations are displayed as separate list entries.
- The explicit no-limitations state prevents absence from being mistaken for a render
  failure.
- Labels remain visible text, improving scanning and assistive-technology reading
  order. Screenshot evidence cannot establish full keyboard or screen-reader
  conformance.

## Verification

- Add a failing AppTest proving reviewer and every limitation are visible after save.
- Add a failing AppTest proving an empty limitations list renders the explicit empty
  state.
- Preserve the existing plain-artifact rendering and runtime append-only tests.
- Run focused and adjacent Streamlit tests, Ruff, the complete offline suite, the
  deterministic benchmark, `git diff --check`, and a loopback Streamlit health smoke.
- Reload the current browser flow and verify the unchanged prerequisite and final-
  acceptance boundaries. Do not submit invented runtime evidence solely to create a
  screenshot; use AppTest render-tree assertions as the authoritative saved-record
  display evidence.

## Approval Basis

The persistent goal explicitly authorizes autonomous, bounded, evidence-backed product
improvements without routine approval. This design stays within the approved UI-only
boundary and does not change evidence or gate semantics.
