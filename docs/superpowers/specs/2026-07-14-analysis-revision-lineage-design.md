# Analysis Revision Lineage Design

## Problem

`ReviewState.analysis_history` preserves historical `ReviewBundle` objects, but a
bundle does not identify the criteria revision that produced it. History order
is insufficient because a reviewer can confirm a revision without running
analysis. For example, analyses from revisions 1 and 3 become two adjacent
history entries after revision 2 is skipped, and neither entry records that gap.

ScopeProof must not infer a missing revision number from list position. Doing so
would manufacture audit evidence.

## Outcome

Every analysis bundle inside a newly created lifecycle state is bound to an
explicit positive criteria revision number. Historical bundles migrated from
the existing record format use the explicit value `"unknown"` when their exact
revision cannot be proven.

## Chosen design

Add `criteria_revision_number` to `ReviewBundle` with the value type:

- a positive integer for lifecycle-bound analysis; or
- `"unknown"` when a standalone or legacy historical bundle has no provable
  revision binding.

The default is `"unknown"` so standalone bundle construction remains backward
compatible. A `ReviewState` is stricter:

- its active bundle must have an integer revision equal to
  `criteria_revision.number`;
- every known historical revision must be lower than the active revision;
- known historical revision numbers must be unique and strictly increasing;
- `"unknown"` is allowed only as an honest statement that historical lineage is
  unavailable.

Lifecycle operations establish known lineage:

- `new_review_state()` binds the first active bundle to revision 1;
- `attach_analysis()` binds incoming analysis to the confirmed active revision;
- `revise_criteria()` preserves the already-bound active bundle when moving it
  into history.

The incoming bundle's revision marker is not trusted as lifecycle evidence.
`new_review_state()` and `attach_analysis()` replace it with the number proven by
the lifecycle transition, then validate the complete returned state.

## Record migration

Increase the local JSON record version from 1 to 2.

When loading version 1:

1. Deep-copy the stored payload.
2. Bind the active bundle to the stored active `criteria_revision.number`.
3. Mark every historical bundle's revision as `"unknown"`.
4. Validate the migrated object through the normal Pydantic and deterministic
   gate boundary.

The migration must not enumerate historical entries as revisions 1, 2, and so
on because skipped analyses make that inference unsafe. Saving a migrated state
writes version 2 and retains explicit unknown history.

Unknown record versions remain rejected.

## Export and user meaning

Canonical JSON includes `criteria_revision_number` for active and historical
bundles. This makes new audit history self-describing and makes legacy
uncertainty machine-readable. Markdown already reports the active state revision
and does not claim historical revision numbers, so no new historical prose is
required in this slice.

## Alternatives rejected

### Infer revisions from history position

Rejected because skipped analysis makes the mapping unknowable. It would invent
evidence and violate ScopeProof's audit contract.

### Reject all version-1 records

Rejected because a safe migration can preserve content while labeling the
unprovable portion unknown.

### Store a parallel list of revision numbers on `ReviewState`

Rejected because parallel arrays can drift and would weaken Pydantic ownership
of each persisted analysis object.

### Wrap historical bundles in a new container model

Rejected for this bounded slice because it would require a broader API and
export shape migration while the provenance belongs naturally to each bundle.

## Verification

- Reproduce a skipped revision and prove history records revisions 1 and 3.
- Reject active revision mismatch and invalid/duplicate/out-of-order known
  historical revision bindings.
- Prove caller mutation cannot alter attached revision lineage.
- Migrate version-1 records with known active and unknown historical lineage.
- Round-trip version-2 records without losing lineage.
- Prove JSON export exposes active, known historical, and legacy unknown values.
- Run Ruff, the full suite, deterministic benchmark, clean wheel smoke, and the
  packaged workbench health check before publication.

## Non-goals

- Inferring revision lineage for legacy history.
- Changing gate or evidence classification semantics.
- Changing resolution-event semantics.
- Adding hosted storage, paid APIs, LLMs, generic migration infrastructure, or
  automatic fixes.
