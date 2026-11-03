# Workbench saved-review handoff — 2026-11-02

Baseline: PR #249 resulting main `1160eaf965461ef76e870173fc46a5de5e9466fd`.
The CLI already safely transfers complete saved records. The distinct remaining operator gap
was that a sender/recipient needed terminal commands before returning to the workbench.
This slice completes that handoff in Resume a saved review.

## Implemented behavior

A sender explicitly prepares a selected saved record and downloads its original bytes. A
recipient explicitly inspects one uploaded record, sees its recorded repository/PR/head,
producer context, confirmation state, retained analysis and decision-event counts, then
confirms/imports that exact content. Import does not open the record or replace open work.
Existing explicit reopening and its unsaved-work guard remain responsible for that choice.

The core exposes byte inspection/import and a locked saved snapshot over the existing versioned
Pydantic validation, recorded-facts guard, deterministic gates and conservative migrations.
Original records, versions, history, actor claims and source/producer identities remain intact.
No record format/version bump, implicit merge, ID renaming or authority upgrade occurs.

Prepared downloads bind to a raw-byte digest and revalidate under the store lock on click.
Selection changes and unsaved input invalidate old callbacks. Missing confirmation/provenance
alone does not block a saved-record transfer. Upload replacement/clear removes preview and
consent; the import checks the inspected digest again before atomic no-overwrite creation.
Errors show fixed recovery text, and recorded metadata is rendered as inert text.

The UI/core cap is 64 MiB. Widget and local server use 68 MB/MiB transport headroom so the full
binary limit reaches the core. JUnit retains its 2 MB widget envelope and 1 MiB parser cap.
This is local operation, with no upload to an external service and no target-code execution.

## Automated evidence and limits

Constructed tests cover pending/historical-only records, byte preservation, provenance,
explicit inspection/consent, changed uploads, stale downloads, collisions, failure recovery,
and open draft preservation. Installed Chromium journeys cover actual UI download/import/
reopen and exact 64 MiB versus one-byte-over transport. Full suite retains the unrounded 95%
threshold; required Python/Windows/locked/package/browser CI and independent automated review
remain merge gates. Exact commands, review dispositions, final counts and commit/run identities
are retained in the version-bound external packet:
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-11-02-workbench-review-handoff`.

A regression identified that the existing general pending-input flag includes missing active
provenance. Using it for transfer incorrectly blocked a reopened unconfirmed saved record.
The transfer control now uses actual unsaved-draft flags; other review authority checks are
unchanged. Independent automated review checked the corrected boundary and clearing uploads.

Frozen R-002 inputs/results remain unchanged. These are constructed automation results, not
qualifying practitioner use. Public v0.2.4 is unchanged; source stays unreleased 0.2.5.
Stage 2 continues, Stage 3 stays dormant, and no personal testing, qualifying reviews, release,
deployment or outreach are required or performed.
