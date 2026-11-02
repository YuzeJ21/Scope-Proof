# Continue a saved confirmed criteria revision

This bounded workflow repair is selected under the owner's automatic execution/merge delegation.
It is an executor choice, not a claim of customer validation. Baseline: b15ceda1290c2477fb7c3a1915426ef90056a21c.

## Outcome and reproduced gap

Reopen a saved analysis, edit and explicitly confirm criteria, then continue the same review.
Today confirmation correctly archives the old bundle, but reopening cleared source and the matching
source action requires an active bundle. Analysis is disabled; fetching the current PR instead
resets lifecycle identity. Preserve the ID, revision and retained history while generating fresh analysis.

## Approaches and executor decisions

- Extend the existing matching-source boundary to confirmed pending revisions: selected because it
  reuses exact-source validation, explicit action, session receipt and locked storage.
- Add a new fetch/review workflow: rejected for this slice because it duplicates authority handling
  and risks losing history or silently following a changed head.
- Typed CLI criteria input or portable saved-record transfer: credible later outcomes, deferred.
  Restoring an already implemented lifecycle path has the strongest immediate source-backed trigger.

## Contract

- Only confirmed, provenance-bearing pending revisions with a retained analysis and complete known
  saved inventory may attach. Unconfirmed, unknown, incomplete and unsupported-origin cases stay blocked.
- Use the latest retained analysis as the explicit source-path anchor. Its repository/PR/base/head,
  visibility, origin, inventory, ingestion and CI facts must match the owning review. Never select a
  different historical head or silently fall back to an earlier analysis.
- Restore only recorded automatic/active-selected unchanged paths, retaining eight files and
  200,000 UTF-8 bytes. Historical references are path context only; they are not copied into new analysis
  or asserted to satisfy changed criteria. Existing active-analysis reference checks remain unchanged.
- Fresh source must match saved facts exactly through existing validation. New source conflicts revoke
  volatile authority, preserving saved history and requiring matching source or explicit re-review.
- Pending receipts bind the complete saved state as well as source/context fingerprints. Unlike active
  analysis neutral appends, pending state changes expire the receipt.
- Completing analysis revalidates receipt/source/current state and commits with store.mutate under
  the same full-state fingerprint. Reject races before writing; failed writes do not install success
  in session state. Preserve review ID/created_at, criteria revision, all retained analyses and audit.
- Fresh analysis contains no prior resolutions, runtime records, file decisions, selected references,
  JUnit imports/events or final acceptance. Existing attach_analysis validates producer identity and gates.
- The workbench clears the pending receipt after successful analysis and synchronizes its saved-state
  fingerprint. Confirming criteria expires the old receipt. Already-loaded source remains usable after
  explicit Run analysis revalidates it into a pending lease, without refetch. Missing source requires
  the matching-source action. Normal new-review and active-analysis attachment behavior remains.

## Boundaries and verification

Keep source 0.2.5 unreleased, record9, Pydantic persistence/export, explicit criteria confirmation,
deterministic gates and core independence from Streamlit/GitHub UI. Frozen R-002 inputs/results stay byte-identical.
No target code execution, new adapter family, release/deploy/outreach, personal testing, qualifying
reviews, genuine-use credit or Stage3 advancement. Source hashes establish consistency, not authenticity.

Use RED/GREEN core and actual AppTest reproduction, stale/race/write-failure regressions, and a fresh
installed-wheel Chromium reopen/revise/load/analyze/restart/export journey. Run full suite >=95%, lint,
lock, deterministic benchmarks, CI Python/Windows compatibility, fresh independent whole-branch review,
guarded exact-head merge and clean resulting-main CI verification. Constructed actors stay labeled.
