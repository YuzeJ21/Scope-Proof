# Audited correction of saved JUnit mappings

Baseline: main `b02c5cb4a53490e1afcaec8d34c8db62565d62a6`, PR #244 merged,
all main CI/CodeQL/base-advance workflows green, no open PRs. Source0.2.5 is unreleased;
publicv0.2.4 remains unchanged. Owner delegates implementation, tests, independent agent review
and guarded merge, without personal testing, routine design input or qualifying reviews.

## Outcome and approach

A reviewer who saved the wrong organizational mapping can explicitly correct a whole import
after source-free reopening. Original import/results/mappings remain immutable and inspectable.
Current effective mappings and every correction are separately labelled in all handoffs.

Overwriting originals loses history and is rejected. Separate correction/withdrawal lists need
another ordering mechanism. Extend the existing append-ordered `junit_import_events` with
literal-tagged correction events; retain original withdrawal schema/default compatibility.
Use an extra-forbid typed union (not a discriminator that rejects legacy defaulted actions).
Append order, never asserted timestamps, defines applicability. These are implementer choices.

## Contracts and bounds

- New frozen `JUnitMappingCorrectionEvent`: schema `junit-mapping-correction-v1`, action
  `mapping_corrected`, same complete owner/artifact/head/revision/provenance/attribution/time/boundary
  fields as withdrawal; full replacement `criterion_mappings`, `previous_mapping_sha256`, and
  explicitly present nullable `previous_correction_event_id`.
- Canonical mapping digest hashes compact sorted-key JSON of sorted criterion groups and sorted
  unique case IDs. All cases must belong to retained import, all criteria to owning confirmed
  bundle; a case maps to at most one criterion. Partial assignment is permitted; empty final
  mappings are rejected with withdrawal guidance. Identical full snapshots are rejected.
- Replay per import starts at original mappings. Validate global unique event IDs, exact owner
  identity, previous digest AND previous correction event ID, no-op rejection, and terminal
  withdrawal. Corrections never withdraw/reactivate, free slots, or permit duplicate artifacts.
- Retain20 original imports and20 unique withdrawals. Permit20 corrections across the bundle;
  union stream maximum40 reserves a withdrawal for every retained import even after saturation.
  No trimming/compaction of historical actions. Large records retain existing byte-limit failure.
- Deep-copy projections and serialized revalidation defend mutable nested lists; frozen models
  are not claimed to provide deep Python immutability or local-file tamper resistance.
- Bundle computed `effective_junit_mappings` is derived and discarded on deserialization. Originals
  remain unchanged even when corrected mappings later return to their original arrangement.
- `correct_junit_mappings(state, *, import_id, criterion_mappings, reviewer, reason,
  expected_state_fingerprint, confirm_whole_import, occurred_at=None)` requires explicit boolean
  true, confirmed active analysis, active retained target and complete current state fingerprint.
  Append only one validated event; compare whole state excluding audit/derived projections.
  Preserve all original imports, history, gates, runtime, findings, decisions and final flags.
- Actor/time are asserted, not authenticated. JUnit remains external non-gating context, never
  runtime verification. Existing explicit criteria confirmation is mandatory.

## Persistence and historical safety

Write recordv9; read1–9. Pre-v8 nonempty audit rejects; v8 accepts withdrawal-only audit and must
reject corrections, including in history. v8+ require explicit event arrays. Legacy absent/empty
events create no actions and cause no load-time write. Do not newly recompute v8 gates merely
because current version becomes9: retain prior gate-migration cutoff<8 (or existing CI migration).
Fresh/attached analyses reject preloaded imports/events; historical bundles remain read-only.

## Workbench and CLI

Use existing Python/Pydantic/Streamlit and locked JsonReviewStore mutation. Reuse current isolated
worktree on a scoped codex branch; root implements source inline, agents support independent tests
and one fresh whole-branch review. No new dependency, parser, XML upload or target execution.

Source-free panel explicitly selects active import, initializes a Pydantic draft from effective
mappings, and shows original/current/staged whole-import mappings. Explicit criterion/case selection
replaces a group; group removal is explicit. Cases come only from retained sanitized results;
overlap rejects rather than silently stealing another group's cases. Empty intermediate drafts
are permitted; empty final drafts are not. Draft identity binds import+full state fingerprint.
Any mapping edit resets whole-import confirmation. Save requires staged actual change, no unstaged
controls, confirmation, reviewer and reason. Target/context/criterion changes clear dependent drafts.
A pristine initialized preview alone is not pending; changed mappings, unstaged controls or
attribution/confirmation block exports/acceptance/other detail writes. Withdrawal and correction
are mutually exclusive drafts. Parent `store.mutate` commits before memory/success; failures retain
draft, preserve external bytes/deletion and never fall back to whole-record save.

CLI `correct-junit-mappings` uses repeated explicit `--map CRITERION=CASE`, reviewer/reason,
fingerprint and `--confirm-whole-import`; typed receipt. Catalog exposes effective/original mappings
and correction history. Same-fingerprint competing writes permit exactly one commit.

## Handoffs and comparison

All current criterion associations/case lists use effective mappings, including withdrawal preview,
CLI catalog, workbench, Markdown/HTML/CSV and comparison. Keep original mappings explicitly labelled.
JSON retains original/events plus derived projection. New audit Markdown fields are escaped plain
text; HTML/UI inert, CSV guarded using existing policy. CSV keeps column order and existing values
for uncorrected imports; current import columns associate by effective groups, while audit column
also covers original/intermediate groups removed by correction. Complete correction events remain
inspectable without suggesting those retired groups are current mappings.

Comparison references retain original/effective mappings, bounded correction history and known
retained case/current criterion IDs to validate replay. Events require full owning decision context.
Hash correction history only when present so uncorrected context hashes remain frozen-compatible.
Changed mappings plus correction metadata are mapping_and_context_modified; returning to original
mappings remains context_modified. Include original/intermediate affected groups when requesting
decision review, without changing actual decisions/gates. Legacy missing projection facts remain
unavailable; do not infer historical correction status or authenticated approval.

## Verification and limits

TDD: chain replay/cycles, malformed identity, invalid/unknown/overlapping cases/criteria, no-op/empty,
terminal withdrawal, saturation preserving withdrawal, fingerprint and full-state invariants;
v1–8 active/history migration/downgrade and invalid-v8-gate rejection; failed saves and queued writes;
all consumer associations, removed-group audit, comparison history/ownership and hostile plain text.
Installed CLI concurrency/exports and installed Chromium source-free reopen→stage→correct→restart→
download plus changed/deleted record rejection use constructed actors/fixtures only.

Run unchanged unrounded95% full covered suite, Ruff/lock, deterministic12+2 benchmarks, clean wheel,
installed browser/CLI and available Python3.11/3.13/Windows CI. Independent fresh whole-branch agent
review before guarded exact-head merge; verify identical clean main and its separate checks.
Preserve frozen R-002 seven inputs/results and original failed-run artifacts. Do not add generic
review/security/auto-fix, adapter families, release, deployment, outreach or Stage3 claims.

Remaining boundaries: correction does not replace/reparse artifacts, reactivate withdrawn imports,
or alter original results. Owner-led Stage2 may continue; genuine independent use and separate
authorization remain the Stage3 gate. Existing PR244 minor Markdown hierarchy issue is not a
standing formatter queue; only layout directly touched by correction presentation is in scope.
