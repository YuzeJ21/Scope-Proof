# Bounded saved-review discovery

## Intent and authority

The owner delegates selection and execution of the next bounded product improvement, including
automated verification, independent review and checked merge, without personal testing or routine
design input. This slice addresses an observed M2 gap: reopen and foreign-comparison selectors
display opaque IDs even though validated saved records contain repository, PR, head and revision.

## Approaches and implementer decision

Automatically parsing every record on every rerun risks unbounded I/O and repeated validation.
A persistent searchable index adds synchronization and migration scope. Choose an explicitly
loaded, session-only metadata page shared by reopening and comparison. Existing ID discovery
stays cheap and unchanged; no network, execution, global index or saved-record format change.

## Core contract

New `scopeproof_core/storage/discovery.py` defines frozen extra-forbid Pydantic models:

- `SavedReviewMetadata`: review_id, state_fingerprint, repository, pr_number, head_sha,
  criteria_revision_number, criteria_confirmed, has_active_analysis, retained_history_count.
  No Ready/gate, authenticity or compatibility claim. Repository/head display metadata must be
  bounded printable nonblank text (repository at most 255 characters, head at most 256).
- `SavedReviewDiscoveryEntry`: candidate review_id and optional metadata. Missing metadata
  means unavailable within preview limits, never an inferred empty review.
- `SavedReviewDiscoveryPage`: zero-based page_index, total_review_count,
  candidate_ids_fingerprint and at most ten ordered entries. Validate complete page windows,
  sorted unique candidate IDs, metadata ownership and strict counts/indices.

`discover_saved_review_page(store, *, page_index=0)` lists candidate IDs and examines only the
chosen ten. Each is loaded with full existing supported-version migration/Pydantic/gate validation
under a 1 MiB read cap. Aggregate payload budget is at most 10 MiB per request, plus the existing
one-byte overflow probe per read. Oversized/malformed/unsupported/invalid/unreadable records keep
their ID with metadata unavailable; never parse partial JSON for labels. Symlink/nonregular IDs
remain excluded and unsafe roots fail as today. Filename ID must match owning state review_id.
Loading does not rewrite files or fabricate missing history/revisions. Legacy history revision
`unknown` stays historical; current revision metadata comes from the current criteria revision.

`JsonReviewStore.load(review_id, *, max_bytes=None)` supports a caller-selected positive integer
cap no greater than the existing 64 MiB maximum; default remains the dynamic existing maximum.
Use the same no-follow descriptor read and full validation, not a pre-stat followed by larger read.

Helpers provide `saved_review_ids_fingerprint(ids)`,
`format_saved_review_label(entry)`, `matching_saved_review_ids(page, query)` and
`load_discovered_review(store, review_id, *, expected_fingerprint=None)`. Search uses bounded
plain case-insensitive AND terms, maximum 200 query characters, over ID/repository/PR/head/revision
in the loaded page only. Labels include ID to distinguish identical metadata. Reopen revalidates
the actual record, its file/owner ID and any preview fingerprint before hydration. Changed/deleted
records require explicit refresh/reselection and never silently select another record.

## Workbench and comparison

Inside Resume a saved review, explicit page/load/query controls show ten-candidate, 1 MiB per
record limits and loaded-page coverage. Default ID-based behavior remains usable without loading
details. After loading, descriptive labels and search apply to that page, including ID-only
unavailable entries. No-results text states its page scope. Direct ID entry stays reachable
for records outside the page or preview cap; it performs the unchanged full bounded validation
when opened. Page/query changes, or inventory changes while a metadata page is loaded, clear reopen/baseline choices and old download
leases before their widgets render, with no automatic replacement. Clear deletion confirmation
when its selection context changes; direct-ID entry is for reopening, not a new deletion path.
Without loaded metadata, an unrelated new ID does not invalidate an existing ID-only selection;
missing selected IDs and changed selected-record fingerprints retain their existing guards.

Share labels/visible IDs with foreign comparison selection while retaining this review's own
historical options. Current active/history compatibility checks and locked whole-record receipts
remain authoritative. A foreign record that changed since its preview must be refreshed before
its analysis can be selected. ID-only unavailable previews may still use the existing full-load
selection path. Validate filename/state ID matching in both selected-record loading and core
comparison preparation, so a catalog label cannot retarget another record. Never infer baseline
compatibility or acceptance from its descriptive metadata.
Clearing targets includes the direct-ID input. Deleting a loaded available preview supplies its
fingerprint to `JsonReviewStore.delete(..., expected_fingerprint=...)`, checked with owning ID
under the existing mutation lock before unlink. ID-only deletion retains the existing unparsed
recovery path; no new platform deletion support is added. Loader recursion failures from JSON,
migration or validation become `ValueError`, so malformed nesting remains per-record unavailable.

Selected-record summary shows full bounded repository/head/revision and active/history presence,
not a fresh-source or readiness badge. Preview names are local asserted saved metadata. Source,
criteria, producer identity, audit events, original decisions and saved JSON bytes stay unchanged.

## Verification and boundaries

RED→GREEN: paging and strict indices; exact read/aggregate caps; invalid encoding, unsupported
versions, malformed nested data, unsafe roots/paths, oversized neighbors and ownership mismatch;
legacy migration without rewrite; duplicate descriptive identity; scoped search and direct access;
changed/deleted preview receipts; pending-input, target/deletion and comparison/export guards;
historical-only and incompatible-active/compatible-history baselines. Extend an installed-wheel
restart/reopen/compare/download journey to discover by repository/PR and verify saved bytes.

Run full suite at the unrounded 95% threshold, lint/lock/workflow checks, unchanged deterministic
benchmarks, packaged browser and available Python/Windows compatibility. Obtain independent
automated review, resolve supported findings, require protected checks on the reviewed exact head,
guarded merge and resulting-main verification. Frozen R-002 bytes/results/labels and public/private
release archives remain unchanged. No release, deployment, outreach, accounts, generic scanning,
target-code execution, human validation, accessibility-conformance claim or Stage 3 advancement.
