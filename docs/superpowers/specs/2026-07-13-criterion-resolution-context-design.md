# Criterion-Resolution Context Design

## Problem

A current combined UX and accessibility audit of the analyzed Streamlit workflow shows three
adjacent reviewer surfaces with inconsistent hierarchy. `Manual runtime evidence` and `Final review
acceptance` have semantic headings and explicit scope guidance, while the criterion-resolution
surface between them starts directly with a `Human decision` selectbox. When the selected
criterion heading is outside the viewport, the local surface does not say which criterion will
receive the decision.

Current audit evidence is saved under
`resolution-boundary-audit-2026-07-13/01-no-local-heading.jpg`. It shows the unheaded decision
control immediately after runtime evidence and immediately before the headed review-level final
acceptance surface.

The existing behavior is correct. A decision is appended for `selected_id`, the selected option's
deterministic effect is explained by `decision_guidance`, the latest current event controls the
criterion's gate input, earlier events remain audit history, and final acceptance remains a
separate review-level event. The gap is presentation context, not lifecycle or gate truth.

## Intended Outcome

Immediately before the existing `Human decision` selectbox, render:

1. a level-three heading: `Criterion resolution`;
2. a caption derived from the current criterion:
   `This decision will be recorded for AC-01 — User can export the research list as CSV. It does
   not record final review acceptance.`

Keep the selectbox label, options, dynamic decision-impact caption, reviewer note, save button,
reset behavior, history, final-acceptance section, and all domain behavior unchanged.

## Approaches Considered

### 1. Add a semantic heading and persistent target caption — selected

This matches the adjacent workbench sections, restores a clear reading-order boundary, and keeps
the selected criterion visible even when its detail heading is outside the viewport. It requires
only presentation copy derived from state already used by `ResolutionEvent`.

### 2. Rename the selectbox to include the criterion identifier

`Human decision for AC-01` would identify the target but would not create a semantic section
boundary, would omit the criterion text, and would still leave the final-acceptance distinction
implicit.

### 3. Move resolution controls or convert them to a separate form

Reordering or restructuring could create stronger visual separation but would change a working
interaction, reset behavior, and layout for no additional contract value.

## Architecture and Data Flow

Only `apps/web/app.py` changes. The new heading and caption consume the existing `selected_id` and
`selected_criterion.text`. The existing `HumanDecision` options, `decision_guidance`,
`ResolutionEvent`, `append_resolution`, and deterministic gate evaluator remain unchanged.

No new helper, session-state key, public API, schema field, persisted value, or core dependency is
introduced.

## Safety and Accessibility

- A semantic heading distinguishes criterion-level resolution from runtime evidence and
  review-level final acceptance.
- The target criterion is readable beside the decision control rather than inferred from scroll
  position.
- Dynamic decision-impact guidance remains the authoritative explanation of whether a choice
  resolves, blocks, rejects, verifies, or conditions the criterion.
- No decision, evidence, acceptance, or gate result is inferred or changed.
- No PR code executes and no network, API, billing, telemetry, dependency, export, or storage
  behavior changes.
- Screenshot and DOM inspection can verify visible hierarchy and reading order, but cannot prove
  complete keyboard or assistive-technology conformance.

## Regression Coverage

Add one Streamlit AppTest that reaches an analyzed review and requires:

- the `Criterion resolution` heading;
- the target caption for `AC-01` and its criterion text;
- the statement that criterion resolution does not record final review acceptance;
- the existing neutral decision-impact guidance;
- an updated target caption after selecting `AC-03`.

Preserve all decision-effect, form-reset, resolution-history, final-acceptance, lifecycle, gate,
schema, export, and runtime-evidence regressions.

Run focused AppTests, Ruff, the complete offline suite, the 12-case deterministic benchmark,
`git diff --check`, clean-installed wheel benchmark and health checks, and a live same-state browser
comparison before protected publication.

## Out of Scope

- Changing decision options, required notes, evidence-level choices, or decision effects.
- Changing resolution history, current-event selection, final acceptance, findings, gates, exports,
  or persistence.
- Moving or restructuring the reviewer surfaces.
- Submitting fixture decisions as real reviewer evidence.
- Paid services, APIs, telemetry, releases, fork testing, or external validation claims.
