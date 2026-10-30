# File-scoped source reference paging

The owner selected this product outcome after PR #228: explicitly select eligible static
references beyond the legacy global first 1,000 lines, without personal testing or qualifying
reviews. Baseline: `af1423eab4a57f120d21fd4d172dcc9934df2c8a`.

## Approaches and decision

Raising the global cap only moves the exclusion boundary and makes the selector larger.
Loading every excerpt into the UI removes its useful bound. The implementation choice is a
deterministic file catalog followed by pages of 100 eligible lines within the selected file.
This is the implementer's decision within the authorized outcome, not an owner design review.
The existing first-1,000 API remains compatible; the workbench uses the new paged API.

## Core contract

One shared iterator applies existing source eligibility to already-ingested source. Catalogs
carry only source scope, canonical path and eligible-line count, ordered by scope/path. Each
page carries at most 100 exact, ordered source lines plus its zero-based page index and source
count; Pydantic validates request/result objects with strict nonnegative integer indexes.
Invalid or unavailable source/page requests fail closed. Page numbers count eligible lines,
not physical lines; the UI labels physical Git line numbers and never renumbers source.

Saving revalidates the full current state fingerprint, exact repository/PR/base/head inventory
and the entire selected value against the same eligibility iterator for that file. It no longer
requires membership in the legacy global prefix. Paging is session-only: no persisted record
or exported reference schema changes. No fetching or execution of target source is introduced.

## Preserved boundaries

Keep confirmed criteria and explicit reviewer/rationale; 32 saved references per analysis;
4,096 UTF-8 bytes per raw line; existing LF/CRLF handling and conservative M3 separator guard.
Removed, skipped, truncated, ambiguous, noncanonical and stale-head sources stay unavailable.
Rename references use the current path; generated code stays static implementation evidence.
No change to automatic matching, confidence, findings, scope decisions, gates, runtime evidence,
acceptance or legacy migrations. Frozen R-002 input and result bytes remain unchanged.

## UI behavior

Keep explicit file and line selection. A file selection defaults only its page to the first
page; no line is selected automatically. A labeled page selector shows page count and eligible
ordinal range. Changing source/page clears the selected line; it must not retarget a queued
save click. Existing source/head/criterion context changes clear the complete draft. Drafts
continue blocking authoritative exports and final acceptance. Saved references still reopen
and export without source loaded. Automation actors remain visibly constructed.

## Acceptance evidence

Core and AppTest coverage exercises a file with more than 1,000 lines, a later file, last page,
gaps from ineligible lines, invalid indexes/paths, exact-head/stale/source tampering, renamed,
skipped, generated, unrelated and unchanged sources. An installed-wheel browser journey selects
a line beyond the old prefix, saves, restarts, reopens and downloads the unchanged reference.
Full suite must meet the existing unrounded 95% threshold. Lint, lock, deterministic benchmarks,
fresh install/browser and hosted Python/Windows checks must pass on the reviewed head before a
guarded merge; resulting main is verified. Stage 3, public release and genuine-use evidence do
not advance.
