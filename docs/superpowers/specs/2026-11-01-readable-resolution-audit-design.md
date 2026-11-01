# Readable resolution-audit handoff

## Intent and bounded outcome

After PR #241, main is `69c8a1cc35991e20b7f5ca971a23cb10bb668c2c`. A saved review's JSON and workbench retain resolution-event context, while Markdown reduces each event to target/outcome/note and HTML omits the history. A report recipient needs to identify applicable decisions and attributed earlier inputs without opening the application or interpreting JSON.

The owner delegated the next product outcome and routine design/implementation choices, automatic testing, independent agent review and merge. This is one Stage 2 report handoff outcome. Personal testing and qualifying reviews are not required or credited.

## Approaches and decision

1. Duplicate complete event formatting in Markdown and HTML. Small, but fields/status semantics could diverge.
2. Share the recorded field projection between format-specific inert renderers in the existing exporter module. Chosen by the implementing agent: it follows current exporter helpers, keeps the existing Pydantic/deterministic validation boundary and introduces no storage or public model.
3. Implement persisted JUnit withdrawal first. This is a real recovery gap, but needs a separate lifecycle, v8 migration, effective context and comparison contract. It remains a separate future decision; this slice does not change it.

## Contract

- Existing `export_markdown` and `export_html` accept the same validated `ReviewState | ReviewBundle`. JSON/CSV contracts, saved record v7, gates, resolution lifecycle, runtime truth and frozen research are unchanged.
- Always render a Resolution History section. Full state with no events says no resolution events were recorded. Bundle-only and retained-analysis reports say full resolution history is unavailable; latest resolution snapshots do not invent a complete event history.
- Preserve append order. Use existing `resolution_event_statuses` with the active criteria revision: Current, Superseded, Prior revision. Never sort authority by timestamps.
- Every event displays event ID, status, criteria revision, target, recorded outcome, asserted reviewer, timestamp as recorded, reviewer note, evidence URL, claimed evidence level and runtime evidence link. Criterion outcomes use the recorded enum. Review-level outcomes show `final_acceptance=true` or `final_acceptance=false`; false does not imply revoked, never accepted or a fabricated event association.
- An absent optional field says Not recorded. An explicitly empty string says Empty value recorded. A manually verified event without a runtime ID retains the existing `Legacy unlinked; re-record at the active head` warning. Claim/link text does not establish runtime correctness or authenticate an actor.
- Timestamps retain the recorded ISO offset. Naive legacy timestamps explicitly say timezone not recorded; no UTC or chronology is inferred.
- Events do not retain historical heads or criteria-source provenance. Do not attach current or historical bundle identities, criterion text or runtime observations to an event by matching IDs. The history boundary states this limitation.
- All event text and URLs are inert, escaped content. New history rendering creates no anchors, scripts, network requests or target-code execution. Existing report links elsewhere retain their existing policy.
- Private render helpers consume only state validated by `_bundle_and_state`; shared field projection prevents missing fields in one format. No new exported machine object or persistence schema is introduced.

## Verification and limits

Regression fixtures cover current/superseded/prior-revision and review-level events, out-of-order timestamps, linked/legacy manual verification, absent/empty fields, offset/naive times, hostile text/URLs and bundle/history unavailability. JSON/CSV, complete saved-state bytes and deterministic truth remain unchanged. A fresh installed CLI exports both readable formats outside the checkout; an existing installed-browser journey downloads the enriched Markdown. No new browser journey/server generation is needed.

Run the full suite with the existing unrounded 95% floor, lint/lock/benchmarks, fresh package and installed-browser/CLI checks, available Python/Windows lanes and one independent whole-branch review. Merge only with exact-head required checks and resolved supported findings; verify main and both clean checkouts.

No release, deployment, participant contact, marketing post, Stage 3 advance, generic review/scanning/autofix, accounts, billing or new adapters. Source remains unreleased 0.2.5; public v0.2.4 and all seven frozen R-002 files remain unchanged. All verification actors are constructed automation, not genuine independent use or accessibility conformance.
