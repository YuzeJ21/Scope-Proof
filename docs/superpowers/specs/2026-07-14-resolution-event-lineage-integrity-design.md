# Resolution Event Lineage Integrity Design

## Problem

ScopeProof treats `resolution_events` as append-only audit history, but a persisted
`ReviewState` currently accepts duplicate or blank event IDs and events bound to
revision `0` or to a revision newer than the active criteria revision. These
records are ignored by active-state reduction today, yet they make event identity
ambiguous and allow future-revision data to become active after later criteria
changes. The application must fail closed instead of preserving an audit history
whose identity or revision lineage cannot be trusted.

## Approaches considered

1. **Validate event identity and state lineage at shared boundaries (selected).**
   Require non-blank `ResolutionEvent.event_id` values, unique event IDs within a
   `ReviewState`, and revision numbers between `1` and the active revision. Also
   reject an append whose supplied ID already exists so lifecycle operations never
   return a newly invalid state.
2. Silently replace duplicate IDs or rewrite revision numbers. Rejected because
   repair would mutate append-only history and invent provenance.
3. Ignore non-active events until their revision becomes active. Rejected because
   future events could later affect human state without being recorded in that
   revision's real workflow.

## Design

- `ResolutionEvent` rejects blank or whitespace-only `event_id` values.
- `ReviewState` rejects duplicate resolution-event IDs.
- `ReviewState` rejects every stored event whose `criteria_revision_number` is
  less than `1` or greater than the active criteria revision number.
- `append_resolution()` rejects an ID collision before appending. Multiple genuine
  events for the same criterion remain valid when their IDs are distinct; this
  does not deduplicate human decisions.
- Existing prior-revision events remain valid and append-only.

## Verification

Regression tests prove rejection of blank IDs, duplicate IDs, revision `0`, future
revision events, and duplicate-ID appends, while preserving distinct superseding
events and prior-revision history. Then run focused tests, Ruff, the full suite,
the deterministic benchmark, package/build probes, local runtime smoke, protected
PR checks, CodeQL, and exact merged-main verification.
