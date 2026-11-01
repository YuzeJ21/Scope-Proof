# Saved criteria revision change inspection — 2026-10-31

Baseline: PR #234 main `9f7a0b86316063e1fa001d9179d1c67920c42d22`, rechecked live with all
post-merge checks passing. Independent gap assessment selected requirements changes ahead of CLI
history parity and narrower final-acceptance comparison context. Editing criteria archives analysis;
existing evidence comparison correctly rejects changed definitions/provenance. This slice supplies
a separate read-only before/after requirements view, without relaxing that compatibility boundary.

## Engineering behavior

Select a retained analysis in an opened saved review, then explicitly compare its criteria with
the current saved revision. Pending/unconfirmed and history-only records are supported. Complete
criteria fields, previous/current positions, added/removed IDs, shared-ID order, source text and
recorded-provenance distinctions are separately visible and exportable as validated JSON/Markdown.
Same IDs are record keys, not proof of semantic continuity; identical text with different IDs stays
separate. Source text in JSON is exact; safe Markdown displays lines without promising identical
whitespace. No semantic matching or evidence comparison is performed.

Frozen, extra-forbid typed snapshots require complete recorded fields, validate unique IDs and
available provenance digests, and preserve unknown historical revisions/provenance. The receipt
binds owner/repository/PR, full saved state, historical position/analysis and both snapshots. Reparsed
reports revalidate snapshot hashes, owning identity, known revision ordering and installed validator
identity. Hashes are consistency checks, not authenticated provenance. Legacy nonblank saved head
strings remain literal recorded context, not freshly verified Git commit identities.

Existing record locks hold through report consumers; UI operations acquire their own locks
sequentially. Generation-bound callbacks check leases before/after locked reload/render. Changes,
deletion, reordering, retargeting, selection changes and same-record reopen invalidate output.
Unsaved widget drafts never enter saved snapshots. Original historical inspection is independent;
missing provenance still blocks full historical acceptance reports, while this requirements-only
view explicitly reports unavailable provenance. No source, artifact or target code is fetched or run.

## Verification and limits

Test-first core/report and UI/deferred regressions cover ordinary and adversarial changes, retained
unknowns, complete fields, report tampering, current-only edits, callback invalidation and unchanged
saved bytes. Independently authored safety tests cover record locks and forged nested instances.
The existing installed history-only journey is extended with both criteria downloads, saved draft
separation, exact recorded content and desktop/phone/CSS-200% geometry. Existing browser count stays
seventeen: three installed-wheel journeys, eight constructed selector checks and six helper/capture
checks. CSS zoom is not native zoom or accessibility conformance. Fixtures/actors are constructed
automation; independent agent review is not a qualifying practitioner review.

The external verification packet records local full-suite/coverage, lint/lock/diff checks,
deterministic benchmarks, installed-package/browser, frozen hashes, independent review, exact-head
hosted CI and separate resulting-main evidence. Pending runs are not passes. Seven frozen R-002
inputs/results stay unchanged; no historical benchmark expectation is rewritten.

Record v7, criteria confirmation, reviewer decisions, current gates and evidence comparison are
unchanged. Source remains 0.2.5 unreleased and public release v0.2.4. Stage 1 remains closed with all
external counts zero; Stage 2 is owner-led; Stage 3 stays dormant pending genuine independent use
and separate authorization. No personal testing, qualifying reviews, release, deployment, outreach,
accounts/billing or standing feature queue is implied.
