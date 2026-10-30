# Resume a saved analysis with matching reviewed source

Baseline: `2b94db2bd02661d99e0cfdd2f4fdd63dd914a2ef` (PR #229).
The owner delegates selection and execution of one high-value product outcome without personal
testing or qualifying reviews. Independent constructed AppTest reproduction found that reopening
clears source; the existing Check current head path resets the analysis even for identical source.
Saved bytes survive, but continuing selected-reference work requires replacing the analysis.

## Approaches and decision

The implementer's choice is a separate explicit **Load matching reviewed source** operation.
Changing Check current head would conflate source inspection with re-review and CI refresh.
Persisting entire repository snapshots introduces a larger retention/schema change. The selected
session-only attachment closes the demonstrated continuation gap using the existing source client.
Attributed reference withdrawal and saved-record discovery were inspected alternatives; withdrawal
requires a separate audit-history design and discovery has less effect on completing a review.
These are documented observations, not a standing queue or evidence of demand.

## Core contract

New pure core module `reviews/source_attachment.py` exposes:
- `review_source_context_fingerprint(state)` binds review identity and source facts, full criteria
  revision/provenance and producer metadata; excludes only final-acceptance state from Review.
- `required_source_candidate_paths(state)` returns the sorted canonical union of unchanged paths
  in automatic evidence and reviewer-selected references, at most the existing eight-file limit.
- `prepare_saved_source_attachment(store, current, *, snapshot, candidate_files, source_origin,
  expected_state_fingerprint)` validates an optimistic saved/current full-state fingerprint under
  the store lock after network requests finish, and returns a frozen Pydantic `ReviewSourceAttachment`.
- `validate_source_attachment(state, attachment, snapshot, candidate_files)` revalidates the
  source-context and complete source hashes without binding legitimate future reference/decision
  appends to the original whole-state fingerprint.

The receipt carries `review_id`, `saved_state_fingerprint`, `context_fingerprint`,
`source_fingerprint`, `source_origin`, `snapshot`, and bounded `candidate_files`. It is session-only,
never a persisted schema or exported evidence. Digests establish internal consistency, not authority.

Require a confirmed active analysis, exact repository/PR/base/head, known inventory, complete
saved/fetched ingestion without skipped/warning/truncated files, equal repository visibility,
equal check state and the complete CI observation. Ignore mutable title/description/fetch time for
matching, but show the new fetch time. Require exact inventory entries including rename metadata.
Live loading requires verified-public live origin; explicit constructed-demo loading remains demo
and does not use the network. Fixture/legacy origins are unsupported rather than relabeled.

Unchanged responses must cover exactly the requested canonical paths once, with the expected head,
unchanged scope, existing byte/count limits and no changed/renamed/skipped alias. No implicit scans,
candidate inference, source execution, gate recalculation, migration or producer relabeling.

Recorded selected references (at most 32) must reproduce the same eligible raw lines using the
existing shared source iterator. Original automatic retrieval is not rerun: its normalized or
multiline excerpts remain the original producer's analysis. A snapshot-only validation helper
checks observed source facts before unchanged-file loading, so a later fetch error cannot hide
a newly observed CI contradiction. The unchanged-file bound is 200,000 total UTF-8 bytes.

## Workbench and conflict authority

Only a clean saved reopened active review with no pending inputs can attach source. Capture its
fingerprint before loading, fetch outside storage locks, then validate the final saved/current
fingerprints and all source facts before setting snapshot/candidates/receipt together. No review
bytes, confirmation, findings, decisions, history, acceptance or provenance change on attachment.
Hydration/replacement clears the attachment. Source-neutral saved transitions may retain it.

An observed contradiction of source facts marks that saved source-context in a dedicated volatile
authority guard. Original records remain intact and inspectable, but current status becomes
refresh-required, final acceptance and exports are blocked, and old deferred export callbacks
must fail at click time. Saved comparison leases are invalidated. Clearing a draft or reopening
the same saved context cannot clear this conflict. A new analysis or explicitly successful matching
source attachment can restore authority for its own context. Network/unavailable-file failures
without an observed contradiction do not invent fresh CI facts. Storage conflicts retain their
existing separate meaning. Check current head remains the explicit replacement/re-review path.

## Evidence and boundaries

Observe RED for healthy resume and failure cases before implementation. Cover state/byte equality,
origin/visibility/CI/inventory/ingestion mismatches, candidate coverage/bounds, stale fetch CAS,
continued repeated reference saves, conflicts across reopen/draft clearing and queued exports.
Extend the constructed installed-wheel journey to reopen, explicitly load matching demo source,
append another reference without reanalysis/reconfirmation, and validate saved/downloaded state.
Actors and fixture injection stay visibly constructed; no genuine-use credit is claimed.

Preserve R-002 seven-file frozen inputs/results and normal benchmark expectations. Full coverage
must meet the existing unrounded 95%; lint, lock, deterministic benchmarks, fresh package/browser,
Python/Windows CI, independent review and exact-head/resulting-main checks remain required.
Unreleased 0.2.5 source only; no release, deployment, outreach or Stage 3 advance.
