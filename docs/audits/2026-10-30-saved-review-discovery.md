# Bounded saved-review discovery

## Selected outcome and baseline

The owner asked for the next automatically executable product improvement after PR #231.
Live main `1658aec8987453b8c66ae89cdf0732459cc11bb8` and its CI were green; both checkouts were
clean and no PR was open. Reopen and foreign-comparison selectors still displayed opaque record
IDs despite validated saved state containing repository, PR, head and revision. This concrete
M2 usability gap was chosen instead of repeating closed maintenance or release preparation.

The [design](../superpowers/specs/2026-10-30-saved-review-discovery-design.md) chooses explicitly
loaded, session-only metadata pages. Automatic full-store parsing is unbounded; a persistent
search index adds synchronization and migration work. Neither is included.

## Behavior and integrity

- Each explicit page examines ten candidate IDs, with a 1 MiB read cap per record and at most
  10 MiB payload plus existing bounded overflow probes. Full existing supported-version,
  nested-schema and deterministic-gate validation supplies metadata. No partial JSON or filename
  guess supplies repository, head, revision or readiness. `list_review_ids()` remains content-free.
- Plain case-insensitive search matches recorded ID/repository/PR/head/revision values within
  that page only. Descriptive labels keep the record ID, full bounded details remain inspectable,
  and no-result text states the page scope. Presentation copy is excluded from search; an
  independently authored regression exposed and fixed that boundary during implementation.
- Malformed, unsupported, oversized, invalidly encoded, mismatched or unreadable records remain
  ID-only with details unavailable. Existing no-follow/nonregular/unsafe-root checks apply.
  Direct-ID reopen remains available under the unchanged 64 MiB full record cap.
- A preview fingerprint binds subsequent reopen and foreign-analysis selection to its saved
  snapshot. Changed/deleted records require refresh/reselection without fallback. File IDs must
  match owning review IDs before metadata, hydration or comparison preparation is trusted.
  A constructed regression reproduced the previous comparison identity gap before the fix.
- Shared labels and visible IDs feed reopening and foreign comparison; existing own-history and
  foreign active/history selection and compatibility checks remain authoritative. No compatibility,
  fresh-source, authenticity or Ready badge is inferred from metadata.
- Page/query changes and loaded-catalog inventory changes clear targets and comparison leases
  before widgets render. Default ID-only choices survive unrelated inventory additions while
  missing IDs and changed selected-state fingerprints retain existing guards. Deletion consent
  resets on target change; direct-ID reopen adds no deletion route.

Discovery does not write records, fabricate legacy metadata, call GitHub, execute target code or
rerun analysis. Existing pending-input, source authority, storage conflict, acceptance and deferred
export controls remain. Evidence, selected-reference audit events, reviewer decisions, historical
revisions, deterministic gates, record version 7 and frozen R-002 inputs/results stay unchanged.

## Automated evidence

Core tests cover paging/type/byte budgets, unavailable neighbors, supported legacy formats,
no-write behavior, ownership, full-head search and stale/deleted snapshots. Separately authored
adversarial tests cover the filesystem, strict projection and bounded-read boundaries. AppTests
cover explicit loading/search, fallback, full identity display, inventory/query/page changes,
comparison leases and history, and target-bound deletion consent. The installed-wheel journey
extends restart/reopen/compare/download to discover by repository and PR while checking original
saved bytes and viewport bounds. Actors and records are constructed automated evidence.

Full coverage, browser/install, deterministic benchmark, compatibility, independent review,
exact-head CI and resulting-main outcomes are recorded in the integration PR/private verification
packet after their runs. A stopped or earlier-head run is not a final passing result.

## Limits and remaining gate

The catalog is a bounded loaded page, not a complete-store search. A valid record larger than
the preview cap intentionally lacks metadata but can still be opened explicitly under the full
store limit. Saved metadata and internal hashes are assertions/consistency checks, not identity
authentication or independent source verification.

Source remains unreleased `0.2.5`. Public v0.2.4 and the historical private release candidate are
unchanged; no publication, deployment or participant contact follows. Stage 2 is owner-led
productization; Stage 1 remains closed at zero and Stage 3 dormant. No personal testing or
qualifying reviews were requested. Genuine independent use, customer validation and accessibility
conformance remain unestablished. No new standing task queue is created by this selected outcome.
