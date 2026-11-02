# Audited withdrawal of saved JUnit imports

## Intent and verified gap

Baseline main `93fb7113e37d6f60c90b5bb83fa8de9d8a176450` (PR #243) is clean and green.
Both independent source assessments reproduced the same gap with trusted constructed core data:
an import saved against the wrong criterion has no withdrawal operation. Removing its JSON loses
history, and the same bytes cannot be imported twice. Draft mapping edits do not solve saved
record recovery. This slice lets a reviewer retire mistaken external context while retaining it.

The owner delegates task selection, routine design, automated tests, independent agent review and
guarded merge; no personal testing/qualifying reviews or design-approval menu is required.

## Selected approach and boundaries

Choose an append-only, whole-import withdrawal event. In-place edits/deletion lose audit facts.
Replacement/remapping and same-artifact reimport require separate identity/uniqueness rules and
are excluded. Inspection-only paging is smaller but cannot retire a mistaken context record.

Only the current confirmed active analysis may be mutated, including after source-free reopening.
Historical analyses remain immutable. Withdrawal applies to every criterion mapping in the chosen
import. Original imports/cases/mappings/actors/times/digests stay byte-for-byte equivalent as model
data. No slot is freed: the existing cap of 20 retained imports and duplicate artifact/ID protection
remain unchanged. No reactivation, replacement ID or inferred correction is introduced.

JUnit remains externally supplied, non-gating organizational context. Preserve criteria/provenance,
automatic evidence/findings, scope decisions, runtime observations, criterion decisions, resolution
events, final acceptance and deterministic gate exactly. Follow existing JUnit append semantics:
an already-recorded final flag is preserved, never silently revoked or newly accepted. Withdrawal
does not invalidate the separate evidence used by the gate or claim authenticated review/execution.

## Data and core API

Add frozen, extra-forbid `JUnitImportWithdrawalEvent` with fixed schema/action/boundary, unique
local event ID, target import ID and artifact SHA256, owning review ID/repository/PR/exact40-char
head, positive strict criteria revision, confirmed-criteria SHA256 and complete criteria provenance,
asserted reviewer (1..200 chars), nonblank reason (1..2000), aware timestamp normalized to UTC.
Attribution is normalized as existing selected-reference events. No raw XML/output is retained.

`ReviewBundle.junit_import_events` is an explicit bounded list (max20); derive
`active_junit_import_ids` from original import order minus terminal events. Discard serialized
derived IDs and recompute. Aggregate validation rejects duplicate event IDs, unknown targets,
foreign owner/head/revision/digest/provenance, and a second event for one target. Do not order by
timestamps or require clocks to prove chronology. Originals retain their existing strict identity.

Pure core API in `scopeproof_core/reviews/junit_audit.py`:
`withdraw_junit_evidence_import(state, *, import_id, reviewer, reason,
expected_state_fingerprint, occurred_at=None) -> ReviewState`.
Revalidate state, compare full `JsonReviewStore.state_fingerprint`, require confirmed active bundle
and active target, append to a deep copy, revalidate and assert all non-audit model data unchanged.
No fetch/execution/UI dependency. Expose `junit_import_status(bundle, import_id)` and an event lookup
for shared read-only display; status is Active/Withdrawn, not a runtime result.

## Version 8 storage

New saves use v8 with explicit JUnit and selected-reference event arrays in every active/history
bundle. v8 missing JUnit audit history rejects; v7+ still requires selected-reference event arrays.
Versions1..7 load missing/empty JUnit audit as empty with no invented events or load-time disk writes.
Any nonempty/malformed JUnit event field on a pre8 envelope rejects. Keep existing migrations,
identity validation, bounded records, atomic mutation, locks and conservative gate recomputation.
Archive/attach/revise carry whole old bundle history, never copy withdrawals onto a new analysis;
initial/attached analyses reject preloaded import context or orphan events.

## Workbench, CLI, exports and comparison

Workbench labels every retained import Active/Withdrawn and displays complete event attribution
and whole-import scope. A separate source-free withdrawal form explicitly chooses an active import,
reviewer and reason; no default target. Pending drafts block exports/acceptance/other writes under
existing input guards. Review/criterion/context changes clear drafts. Saving uses existing
conflict/deletion/pending-input signals and guarded state fingerprint persistence; stale clicks,
external changes/deletion or failed writes produce no partial event, no success notice or false
current state. All untrusted fields render through inert text/code with wrapping.

CLI adds `junit-imports REVIEW --storage-dir ...` (typed catalog incl full-state fingerprint), and
`withdraw-junit REVIEW --import-id ... --reviewer ... --reason ...
--expected-state-fingerprint ... --storage-dir ...`. Use locked store mutation and Pydantic typed
result metadata; catalog is read-only. Never guess a target/fingerprint or access a default store
in verification. Existing import/inspect commands are unchanged.

JSON retains original imports/events plus derived active IDs. Markdown/HTML show every original
and its status, all withdrawal metadata and fixed trust boundary. CSV keeps existing retained
JUnit columns and appends `junit_import_audit` JSON per criterion, tying status/event to import ID
and artifact. Withdrawn data is never silently omitted or presented as active context.

Comparison retains original artifact presence. Add explicit optional status and withdrawal-event
fields to each `JUnitImportReference`; absent fields in older serialized comparisons mean status
unavailable, never inferred Active. Fresh references always provide status. Include withdrawal
event data in the context digest only when present, preserving active-import hashes. A withdrawal
therefore becomes `context_modified`, not `removed`/`unchanged`; previous/current retain mappings,
status, attribution and owner-bound audit. Render in comparison JSON/Markdown and workbench;
decision-review guidance may change for that recorded context, never gate/acceptance truth.

## Verification and limits

TDD core/aggregate/migration, actor/time/owner forgeries, duplicate and full-cap retention, active
and archived history, source-free UI withdrawal, pending/stale/deleted record/save-failure and
locked CLI concurrency. Check exact invariance including an already accepted review. Verify
reports/comparisons preserve originals, status and inert hostile metadata; older comparison status
stays unknown. Installed Chromium import→withdraw→restart/reopen→download uses disposable data
only; installed CLI catalog/withdraw verifies exact fingerprint and unchanged gates.

Preserve all seven frozen R-002 inputs/results; new constructed cases are separate. Full suite at
unchanged unrounded>=95%, Ruff/lock, deterministic12+2 benchmarks, clean install/package/browser,
Python311/313 and Windows lanes. Independent agent review, resolve supported findings, then
expected-head guarded PR merge and resulting-main CI verification. Source0.2.5 remains unreleased;
publicv0.2.4, candidate archives and dormant Stage3 retain separate authorization/evidence gates.
No generic review/scanning/autofix, accounts/billing, target-code execution, new adapters, release,
deployment, outreach, genuine-use/customer/a11y/beta claim.
