# Durable saved comparison — M2

The owner authorized M2 implementation, automatic tests and independent review, followed by
exact-head checked merge. No personal testing or qualifying participant reviews are required.

## Outcome and approach

Reopening currently clears the comparison base. Changed PR heads can live in separate saved
records; criteria revisions can retain historical bundles within one record. Provide explicit
selection of either another saved record's active analysis or the open record's history.

A history-only selector would miss changed-head records. A new comparison database or persisted
selection would add unnecessary migration and stale-state risks. The chosen approach reuses
validated ReviewState/ReviewBundle objects, locked_load_many and compare_reviews, with a small
typed, session-only selection binding both complete saved-state fingerprints and history position.
These are delegated implementation choices, not evidence of genuine user demand.

## Contract

- Default to no baseline after startup, reopen or current-context change. Changing a candidate
  selection clears the applied comparison; only an explicit Compare action applies it.
- Label current/baseline record, exact head and criteria revision; history labels include their
  position. Do not call review creation time an analysis timestamp. Unknown facts stay unknown.
- The current review must have a saved, clean active analysis with no pending inputs. Incompatible
  baselines remain selectable and produce bounded actionable feedback without changing the review.
- Preserve existing relationship validation: same repository/PR, eligible exact-head evidence,
  identical ordered criteria and criteria-source identity. Never relax it to create a comparison.
- Read both records under one sorted/deduplicated locked_load_many, including same-record history.
  Bind history position to the full expected record fingerprint so replacement cannot retarget it.
- Recheck both fingerprints on every rerun and at deferred download time. Missing, corrupt,
  replaced, unsupported or changed records expire the applied selection and downloads. A volatile
  export lease also invalidates old callbacks when the chosen baseline or current UI context changes.
- Render comparison exports while the shared record locks remain held. Do not nest this operation
  under the existing Summary lock. The displayed comparison is a validated point-in-time snapshot.
- Selection, comparison and downloads do not rewrite saved JSON, migrate records on disk, transfer
  decisions, change final acceptance, fetch GitHub or execute target code. Existing transient
  reload/reanalysis comparison remains available when no saved baseline was chosen.
- Core selection/loading stays independent of Streamlit. Keep gate/retrieval/schema/dependencies,
  frozen R-002, public v0.2.4 and original private v0.2.5 candidate bytes unchanged. No publication,
  deployment, outreach or Stage 3 claim.

## Verification

Test other-record and same-record history comparison; unknown history revisions/inventories;
incompatible criteria/source/PR/evidence; pending drafts; context switches; changed/deleted/corrupt
records; stale callbacks; concurrent export/mutation; and byte-for-byte record preservation.
Use one shared installed wheel for existing and new browser journeys. The new journey restarts
the server, reopens constructed records, explicitly chooses both source types, downloads both
reports, and verifies identities/scope plus unchanged record bytes. Browser traffic blocking is
not proof about server requests; pair it with fail-fast API/target-execution seams in AppTest.
Run the full 95% coverage suite, lint, benchmarks, packaged checks and hosted compatibility lanes,
then independent review, exact-head guarded merge and resulting-main verification.
