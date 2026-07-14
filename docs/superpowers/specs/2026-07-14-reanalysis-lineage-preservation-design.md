# Reanalysis Lineage Preservation Design

## Problem

The Streamlit workbench correctly creates a new criteria revision when a reviewer
edits and reconfirms criteria. At that point the lifecycle state preserves the old
analysis in `analysis_history`, keeps the stable review ID, and retains prior
resolution events as revision-scoped audit history.

Clicking **Run deterministic analysis** then calls `new_review_state(bundle)`.
That constructor is correct for a new review, but incorrect for reanalysis: it
creates a new review ID, resets the criteria revision to `1`, and discards
`analysis_history` and `resolution_events`. A deterministic AppTest reproduction
observed revision `2`, one historical bundle, and one prior event immediately
before analysis; afterward it observed revision `1`, no history, no events, and a
different review ID.

## Approaches considered

1. **Attach a validated analysis through the core lifecycle (selected).** Add an
   `attach_analysis(state, bundle)` operation for a confirmed, bundleless active
   revision. It preserves lifecycle identity and history while installing only
   the new static analysis.
2. Rebuild or merge the state inside `apps/web/app.py`. Rejected because it would
   duplicate lifecycle invariants in the UI and leave other callers without the
   safe operation.
3. Add explicit revision metadata to every historical bundle and migrate records.
   Rejected for this slice because the existing ordered lifecycle already knows
   the active revision; a record-format extension is not required to stop the
   demonstrated data loss.

## Core lifecycle contract

`attach_analysis(state: ReviewState, bundle: ReviewBundle) -> ReviewState` must:

- independently revalidate both inputs;
- require `state.bundle is None`;
- require the active criteria revision to be confirmed;
- reject preloaded human resolutions or final acceptance in the incoming bundle;
- require incoming criteria and requirements source to equal the active revision;
- require incoming review facts to match the lifecycle review after replacing
  only the incoming auto-generated `review_id` and `created_at` with the stable
  lifecycle values;
- install a deep-copied bundle whose `review` is the stable lifecycle review;
- preserve `criteria_revision`, `analysis_history`, and `resolution_events`
  unchanged;
- revalidate the returned state, including deterministic active and historical
  gates.

The operation rejects contradictions. It does not normalize criteria, synthesize
events, copy prior decisions into the new revision, or infer historical metadata.

## Workbench integration

When **Run deterministic analysis** produces a bundle:

- if no lifecycle state exists, continue using `new_review_state(bundle)`;
- if a confirmed bundleless revision exists, use
  `attach_analysis(existing_state, bundle)`.

This preserves first-use behavior while making criteria reanalysis continuous.
The current revision starts with no active human decisions and final acceptance
remains false; prior-revision events remain visible only as history.

## Failure behavior

Core contradictions raise stable `ValueError` messages. The workbench normally
constructs valid inputs from its own confirmed criteria and loaded snapshot, so no
new user-facing error surface is required in this bounded slice. Pydantic remains
the defense-in-depth boundary for persisted and exported state.

## Verification

Regression-first coverage must prove:

- the reproduced AppTest path preserves review ID, revision `2`, the historical
  bundle, and prior events after reanalysis;
- the new active bundle uses the edited confirmed criteria and has no active
  resolution or final acceptance;
- the core rejects an existing active bundle, an unconfirmed revision, mismatched
  criteria/source/review facts, preloaded resolutions, preloaded final acceptance,
  and mutated invalid input;
- a valid attached state round-trips through Pydantic, storage, and lifecycle
  export.

Then run focused tests, Ruff, the complete offline suite, the deterministic
benchmark, `git diff --check`, a clean wheel installation with CLI and workbench
probes, protected PR checks, CodeQL, and exact merged-main verification.

## Boundaries

No gate semantics, evidence classification, runtime-evidence meaning, final-
acceptance meaning, external validation, paid service, API, fork, notification,
release, or record migration changes are included.
