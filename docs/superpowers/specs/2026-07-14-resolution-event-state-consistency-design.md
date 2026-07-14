# Resolution Event State Consistency Design

## Problem

Deterministic gate validation proves that a cached gate agrees with the cached
review and resolutions. It does not prove those cached human decisions agree with
the lifecycle's append-only `resolution_events`.

A state can set all cached criterion resolutions to Accepted, set cached final
acceptance to true, recompute a fully deterministic Ready gate, and still retain an
empty event history. Current lifecycle, persistence, and export validation accepts
that False Ready state.

`new_review_state()` also accepts an analysis bundle that already contains human
resolutions even though it creates no corresponding events.

## Approaches considered

1. **Derive and validate active human state from events (selected).** Extract the
   existing resolution and final-acceptance derivation into a dependency-light
   reviews module. Reuse it from lifecycle recalculation and shared state
   validation. Require new analysis bundles to contain no preloaded human state.
2. Copy event-reduction logic into gate validation. This risks lifecycle and
   persistence deriving different human truth after later changes.
3. Generate events automatically from preloaded bundle resolutions. Synthetic
   event IDs and provenance would manufacture audit history that the caller did
   not explicitly record.

## Design

Create the import-side-effect-free `scopeproof_core/resolution_events.py` with:

- `current_resolutions(events, criteria_revision_number=None)`;
- `final_acceptance(events, criteria_revision_number)`.

Lifecycle imports and re-exports `current_resolutions` for compatibility, and uses
both functions during deterministic recalculation.

`validated_review_state()` must:

- reject current-revision events when no active analysis bundle exists;
- require active `bundle.resolutions` to equal the latest criterion decisions
  derived from current-revision events;
- require lifecycle and active-bundle `final_acceptance` to equal the latest
  current-revision final-acceptance event (the existing ReviewState identity
  validator already requires those two review representations to match);
- continue validating active and historical gates deterministically.

`new_review_state()` rejects nonempty resolutions or final acceptance in its input
analysis bundle. Human action must enter through `append_resolution()` after state
creation. Direct standalone `ReviewBundle` export behavior is unchanged because it
does not claim lifecycle event history.

Prior-revision events remain append-only and do not affect the active revision.
Historical bundle/event linkage is not invented because historical bundles do not
currently store a revision identifier; this slice protects the active verdict and
explicitly leaves that data-model extension for separate evidence-backed design.

## Verification

Regression tests must prove rejection of:

- preloaded initial resolutions and initial final acceptance;
- cached active resolutions that differ from current events;
- cached final acceptance that differs from current events;
- current-revision events without an active bundle;
- a fully deterministic forged Ready state on save and export.

Existing valid resolution append, supersession, prior-revision history, storage,
and reporting flows must remain green. Then run Ruff, full pytest, deterministic
benchmark, clean-wheel installed probes, packaged health, independent review,
protected PR checks, and exact merged-main verification.
