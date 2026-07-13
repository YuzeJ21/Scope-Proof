# Runtime-Evidence Context Design

## Problem

The continuation objective's original runtime-evidence readiness defect is already fixed on
`main`. Empty or whitespace-only required fields keep `Save manual runtime evidence` disabled,
unexpected validation failures use product-facing recovery copy, and a successful append clears
the form before another submission can occur.

A current combined UX and accessibility audit found the next first-use ambiguity in the same
surface. The runtime-evidence form binds every saved record to `selected_id`, but the form itself
does not state which criterion will receive the record. The selected criterion heading can be
outside the viewport because the evidence list above the form may be long. The evidence-level
control also exposes only `E3` and `E4`, while their accepted meanings live in the README and
product specification rather than beside the choice.

Current audit evidence is saved under
`runtime-evidence-audit-2026-07-13/01-empty-form.jpg` and
`runtime-evidence-audit-2026-07-13/02-evidence-level-gap.jpg`. The screenshots confirm healthy
required-field labels and disabled readiness, but no local criterion target or evidence-level
boundary guidance.

## Intended Outcome

Keep the existing form, values, schema, and lifecycle behavior. Add two always-visible captions:

1. Immediately below `Manual runtime evidence`, show:
   `This record will be attached to AC-01 — User can export the research list as CSV.` using the
   currently selected criterion identifier and text.
2. Immediately below `Runtime evidence level`, show:
   `E3 means manually recorded external runtime verification. E4 means explicit human
   acceptance. Saving this record does not resolve the criterion or record final review
   acceptance.`

The existing human-supplied-observation disclaimer and required-field guidance remain visible.

## Approaches Considered

### 1. Add persistent context and boundary captions — selected

This follows the workbench's existing pattern of explaining decision effects next to the control.
The information remains visible without opening a tooltip or selectbox, preserves the enum values,
and changes no domain behavior.

### 2. Expand the selectbox option labels

A `format_func` could display longer E3 and E4 names. The closed control would explain only the
selected option, long labels would consume more horizontal space, and the criterion target would
still be missing.

### 3. Remove E4 from the form or change the runtime-evidence schema

The public MVP contract distinguishes E3 runtime verification from E4 human acceptance, but the
validated `RuntimeEvidence` schema and existing UI deliberately allow both levels. Removing a
choice or changing validation would alter accepted behavior and backward compatibility without a
separate evidence-rule decision. This slice only explains the existing contract.

## Architecture and Data Flow

Only `apps/web/app.py` changes. It already holds `selected_id`, `selected_criterion`, and the
selected `EvidenceLevel`, so no helper, schema field, persisted value, or core import is needed.
The captions are derived from the same state used to construct `RuntimeEvidence`.

`RuntimeEvidence` remains the authoritative persisted-object validator.
`append_runtime_evidence` remains the only mutation path and continues to leave static findings,
human resolutions, final acceptance, and the deterministic gate unchanged.

## Safety and Accessibility

- The target criterion is stated next to the form instead of depending on scroll position.
- Evidence-level meanings and their final-acceptance boundary are exposed as readable text rather
  than color, hover state, or an unopened control.
- No runtime result, reviewer decision, acceptance, or evidence is inferred.
- No PR code executes and no network, paid API, billing, telemetry, dependency, or storage behavior
  changes.
- Screenshot and DOM inspection can verify visible text and reading order. They cannot establish
  complete keyboard or assistive-technology conformance.

## Regression Coverage

Add one Streamlit AppTest that reaches an analyzed review and requires:

- the selected criterion identifier and text in the runtime-evidence target caption;
- the accepted E3 and E4 meanings;
- the statement that saving runtime evidence does not resolve the criterion or record final review
  acceptance.

Then change the selected criterion to `AC-03` and prove the target caption follows the selection.
Preserve all existing readiness, reset, lifecycle, gate, schema, export, and final-acceptance tests.

Run focused AppTests, Ruff, the complete offline suite, the 12-case deterministic benchmark,
`git diff --check`, clean-installed wheel benchmark and health checks, and a live same-state browser
comparison before protected publication.

## Out of Scope

- Changing `RuntimeEvidence`, evidence-level, resolution, or final-acceptance schemas.
- Removing E4 or changing its persisted meaning.
- Changing gate evaluation, findings, resolution behavior, exports, or storage.
- Submitting fixture values as genuine runtime evidence.
- Paid services, APIs, telemetry, releases, fork testing, or external validation claims.
