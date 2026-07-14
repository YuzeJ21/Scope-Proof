# Runtime-Evidence Prerequisite Guidance Design

## Context and Verified Current Behavior

The active goal asked for an audit of the manual runtime-evidence form and final-acceptance
boundary. Current `main` already differs from the stale defect description:

- blank or whitespace-only required runtime-evidence fields keep `Save manual runtime evidence`
  disabled;
- every required field is visibly labeled;
- the save boundary catches `ValueError` and renders fixed recovery copy instead of raw Pydantic
  output;
- final acceptance is a separate append-only review event and does not resolve criteria or override
  deterministic gate precedence.

Focused AppTest, lifecycle, and gate checks confirm those contracts. No fix is justified for the
originally described behavior.

One first-use gap remains: while Save is disabled, the form only repeats the complete static list of
required fields. It does not tell the user which fields are still missing after partial entry. The
next action is therefore less direct than it needs to be.

## Intended Outcome

When any required runtime-evidence value is blank after whitespace trimming, show one neutral
caption immediately before the Save action:

`Complete required fields to enable Save: <ordered missing field names>.`

The missing names use the same user-facing concepts as the labels and remain in form order:

1. Artifact or URL
2. Runtime scenario
3. Environment
4. Observed result
5. Runtime reviewer

As fields become nonblank, the caption updates deterministically. When all five values are present,
the caption disappears and Save becomes enabled.

## Approaches Considered

### Keep only the existing static caption

This is safe and already identifies all required fields, but it makes the user compare the whole
form manually to discover why Save remains disabled.

### Show one dynamic ordered missing-field caption — selected

This gives a precise recovery path without treating an untouched form as erroneous. It reuses the
same stripped-value predicate that controls the button, so guidance and enabled state cannot drift.

### Render an error under every blank field

Field-level errors would be visually noisy on initial page load and imply invalid submission even
though the disabled action prevents submission. Streamlit's rerun model also makes a single summary
more stable and easier to regression-test.

## Architecture and Data Flow

The change stays in `apps/web/app.py`:

1. Pair each required field's display name with its current widget value.
2. Build `missing_runtime_fields` by preserving form order and excluding values whose `.strip()` is
   nonempty.
3. Derive `runtime_evidence_ready = not missing_runtime_fields`.
4. Render the neutral caption only when the list is nonempty.
5. Continue using `disabled=not runtime_evidence_ready` for Save.

Pydantic `RuntimeEvidence` validation and the existing fixed `ValueError` recovery remain defense in
depth. The lifecycle receives no object until all presentation prerequisites are met.

## Final-Acceptance Boundary

No final-acceptance behavior changes. Repository contracts explicitly permit final acceptance as an
independently recordable append-only event. If criteria remain unresolved or blocking, deterministic
gate evaluation continues to prevent Ready even after final acceptance. The existing heading,
warning copy, repeat guard, event history, and gate tests remain authoritative.

## Error and Compatibility Behavior

- Initial empty form: Save disabled; caption lists all five fields.
- Partially complete form: Save disabled; caption lists only remaining fields in form order.
- Whitespace-only value: treated as missing.
- Complete form: Save enabled; missing-field caption absent.
- Pydantic failure after enablement: existing fixed user-safe recovery message remains unchanged.
- Successful save/reset: existing reset, success notice, append-only behavior, and disabled empty
  form remain unchanged.

## Verification

Streamlit AppTest regressions cover initial, partial, whitespace-only, and complete prerequisite
states plus final-acceptance invariants. Broader verification includes Ruff, the complete offline
suite, deterministic benchmark, `git diff --check`, clean wheel installation, installed benchmark,
and exact local workbench health. A real workbench inspection may populate fields locally but must
not save invented runtime evidence or final acceptance.

## Out of Scope

- Schema, lifecycle, gate, evidence-level, resolution, final-acceptance, persistence, or exporter
  changes.
- Executing pull-request code or claiming controlled UI checks as PR runtime evidence.
- Paid APIs, billing, organizations, second accounts, private repositories, forks, synthetic users,
  synthetic validation, GitHub comments, issue updates, or a release.
