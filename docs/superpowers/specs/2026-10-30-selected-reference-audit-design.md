# Audited selected-reference correction and withdrawal

## Intent and authority

The owner requests implementation, automated verification, independent review and checked merge,
and delegates routine design decisions. This is the implementer's bounded design, requiring no
personal testing or qualifying review. ScopeProof remains an evidence assistant.

## Approaches and decision

In-place edits/deletion lose attribution and are rejected. An active-only replacement collection
would hide historical context from comparisons and is rejected. Choose immutable original
references plus append-only terminal events: `corrected` links to a fresh, source-derived
replacement; `withdrawn` has no replacement. Actor, reason and aware timestamp are required.
Corrections may change the source line and selection rationale within the same criterion.
Withdrawal needs the saved record, not live source; correction requires matching loaded source.
Neither changes findings, gate, decisions, runtime records, scope or acceptance truth.

## Core and persistence

- Add frozen Pydantic `SelectedReferenceEvent`, owned by the review/PR/head/confirmed revision
  and criteria digest. Validate unique IDs, terminal target exactly once, target ownership,
  replacement ownership, same criterion, replacement later in the immutable reference list,
  one incoming correction per replacement. Append order determines terminality; timestamps
  are metadata and clock rollback cannot prevent withdrawal. A correction's
  replacement attribution/time equals its event actor/time. Historical analysis remains intact.
- `ReviewBundle.selected_reference_events` defaults empty. Derive active reference IDs from
  validated events, never trust serialized presentation fields. References retain their UUIDs,
  exact raw lines, original attribution and source provenance. No resurrection or cycles.
- Keep at most 32 active references, 128 total retained reference records and 128 events per
  analysis. Correcting at the active limit is supported; retained-history exhaustion fails
  explicitly. Only active references must have unique criterion/scope/path/line locations.
- New pure core transitions `withdraw_reviewer_selected_reference` and
  `correct_reviewer_selected_reference` require the whole-state expected fingerprint, confirmed
  active analysis and nonaccepted state. Reject inactive/missing/stale targets. Reuse existing
  exact-source selection validation for correction and never overwrite the original record.
- Writer advances from record version 6 to 7; read 1–7 without rewriting on load. Reject any
  nonempty/malformed lifecycle events in pre-7 active/history bundles; missing/[] means no
  recorded events. Keep all earlier migrations and never invent who withdrew a reference.

## Product surfaces

Show Active, Corrected or Withdrawn on every reference, and the complete event history with
actor/reason/time/link. A separate action selector defaults to Add. Correction/withdrawal target
is explicit and limited to active references for the inspected criterion. Required actor/reason
are pending inputs and block export, acceptance, retargeting and autosave until saved/cleared.
Corrections also require an explicit source/line/rationale. Existing optimistic save conflicts
and source-authority guards apply. Reopening supports withdrawal without source; correction
uses the existing matching-source continuation. Do not silently discard actions or stale drafts.

Markdown/HTML, typed JSON and per-criterion CSV retain original records, events and explicit
active IDs/status. Comparison keeps immutable full-record presence counts and separately
includes per-side lifecycle snapshots/status/history; identical record does not mean identical
active status. Older comparisons without lifecycle snapshots say availability is unknown.
Source continuation reproduces active selected references only; historical references do not
force unnecessary source retrieval. Original automatic evidence remains required.
An existing fingerprint-bound receipt may retain previously validated candidates when an audit
action retires their last active reference. Validation still requires every current path and
unchanged receipt/source bytes, uniqueness and all path/head/size limits. New attachment
preparation continues requiring exactly the requested path set, with no surplus fetching.

## Verification and boundaries

RED→GREEN covers correction chains, same-location rationale correction, withdrawal, missing/
inactive/foreign/stale targets, duplicate active locations, aware attribution/time, tampering,
32-active limit, bounded history, version downgrade and active/history migration. Test all
exports, comparison state-only differences, source continuation and pending/conflict UI paths.
Extend the installed-wheel restart journey to correct, withdraw, reopen and inspect downloads.
Run full suite at unrounded 95% coverage, lint/lock, deterministic benchmarks, packaged browser
and available hosted Python/Windows checks; independent review, exact-head guarded merge and
resulting-main verification. Preserve frozen R-002 bytes/results. No new dependencies, server
execution of target code, generic review/scanning/autofix, release, deployment, outreach,
customer validation, accessibility conformance or Stage 3 advancement.
