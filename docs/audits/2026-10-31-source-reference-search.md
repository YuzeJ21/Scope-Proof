# Content-first source reference selection — 2026-10-31

Baseline main: `abee995a224c8caeaf7c8aa07133d6013b484251`, merged PR #235. Live main and all
post-merge checks were rechecked green; the workspace was clean. Independent gap assessment selected
source navigation ahead of CLI history parity and another comparison projection. The reference
chooser held eligible source excerpts but displayed only physical numbers until selection.

## Delivered behavior

An explicitly selected loaded file can be searched with a maximum 200-character literal,
case-insensitive query. Empty query browses all eligible lines; whitespace/punctuation are literal,
with no regex/glob/semantic matching or ranking. Search spans the selected file's eligible loaded
lines rather than only the visible page. At most 100 complete matches are returned per page,
retaining original excerpts and physical Git coordinates, including gaps. Match and total eligible
counts distinguish no matches from missing/excluded source. No match has no selectable line.

A bounded scrollable, wrapping, inert source preview appears before explicit line selection.
Query changes clear line choice and reset page; file changes also clear the query. Existing source,
criterion, revision, owner, action, draft-clear and save resets include query state. Queries are
transient draft navigation, never persisted reference evidence. Explicit reviewer, rationale and
criterion mapping remain necessary to save a static location.

Core search uses the existing eligibility iterator and independent Pydantic search-page validation.
It preserves removed/skipped/truncated/ambiguous-source, duplicate path/coordinate, wrong-head,
unsupported-separator and line-byte exclusions. Missing sources and invalid pages never fall back.
Source and state are revalidated on append under the existing exact-head/fingerprint/provenance
rules. Search itself reads already-ingested data without new network requests or target execution.
Automatic candidates/findings/confidence, changed-file scope, reviewer decisions, runtime evidence,
final acceptance, record v7 and compatible comparisons remain unchanged.

## Verification and limits

Test-first core and workbench regressions cover literal casefold/whitespace, punctuation, Unicode,
bounds/types, no matches, partial last pages, matches beyond the global first 1,000, physical line
gaps, changed/unchanged scopes, exclusions, tampered nested models, reset behavior and unchanged data.
Independent safety tests exercise exact-source save rejection and absence of gate changes.

The existing installed selected-reference journey retains page 11 browsing, then searches by
content, checks no-match/reset/explicit line 1002 choice, saves/reopens and verifies non-gating data.
An actual hostile-looking long source line is previewed and saved as inert text. Desktop, 390px phone
and CSS-200% captures inspect the source preview and its scrollable content. Suite count remains
seventeen: three installed-wheel journeys, eight constructed selector checks, six helper/capture
checks. CSS zoom is not native zoom, accessibility conformance or genuine independent use.

Exact-head local/hosted full suite at the existing unrounded 95% floor, lint/lock/diff, deterministic
benchmarks, clean installed package/browser, Python and Windows compatibility, independent review,
guarded merge and separate main verification are recorded in the external verification packet.
Pending or failed runs are not passes. Seven frozen R-002 inputs/results are hash-bound and unchanged;
no historical research label, expectation or score is rewritten to improve results.

This closes a bounded source-navigation gap, not a retrieval-performance or usefulness hypothesis.
All fixtures and actors are constructed automation; agent review is not a qualifying practitioner
review. Source stays 0.2.5 unreleased; public v0.2.4 stays unchanged. Stage 1 is closed at zero,
Stage 2 owner-led, Stage 3 dormant. Independent usefulness, fit, repeat use and demand remain
unverified. No personal testing, qualifying reviews, release, deployment, outreach or queue follows.
