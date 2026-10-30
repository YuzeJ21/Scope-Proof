# Audited selected-reference correction and withdrawal

## Selected outcome and source

The owner authorized this bounded product slice after saved-source continuation in PR #230,
starting from `6b4a71e8d04c4a742362c925f2681ef2b24d4a5e`. The gap was concrete: existing
selected references could be appended but not corrected or withdrawn, and duplicate-location
rules prevented correcting a rationale for the same line.

The [design](../superpowers/specs/2026-10-30-selected-reference-audit-design.md) chooses immutable
original records with append-only terminal events, rather than editing/deleting attribution.
Correction validates a new exact-head source line and records a replacement link. Withdrawal
records asserted actor, reason and aware time without requiring source. Both reject stale,
inactive or foreign targets and require final acceptance to be revoked. Correction stays within
the same confirmed criterion; no previous decision is carried forward.

## Integrity and product behavior

- Pydantic validates event ownership, links, unique terminal targets, replacement attribution and
  source/criteria identity. Append order determines terminality; clocks do not establish authority.
  A correction cannot form a cycle, reuse an incoming replacement or revive an inactive record.
- At most 32 active references, 128 retained records and 128 events exist per analysis. Correction
  works at active capacity. Once retained history is full, further additions/corrections reject;
  one terminal event per target ensures withdrawal remains possible.
- Workbench actions require explicit target/actor/reason; correction also needs source selection
  and rationale. Pending inputs, source contradictions, acceptance and optimistic-save guards
  remain effective. Original excerpts and attribution remain alongside status and linked events.
- JSON, Markdown, HTML and per-criterion CSV retain history and active status. Saved comparisons
  separate immutable original-record presence from lifecycle changes, retaining per-side events.
  Older comparison projections with no event snapshot report lifecycle context unavailable.
- Source continuation restores active manual references and original automatic candidate paths;
  inactive selected-reference history does not force unnecessary file reads. This does not clear
  the session source-conflict guard or turn historical records into current verification.
  Existing fingerprint-bound attachments retain previously validated candidates after a neutral
  audit action; initial preparation still requires exact requested paths. A GitHub automated
  review exposed a false-conflict edge case here, reproduced in core and workbench regressions
  and fixed before merge. Source bytes, receipt/context binding and all candidate bounds remain.
- Writer version 7 requires explicit lifecycle event lists. Versions 1–6 load without invented
  events or automatic file rewrites; nonempty/malformed pre-7 events reject. Version 6 reference
  provenance is preserved. New analyses do not inherit selected context or audit events.

Gate rules, automatic findings/evidence, scope decisions, runtime/JUnit records, reviewer decisions
and historical analyses remain separate. Asserted local actor names and digests provide internal
consistency, not authenticated identity or independent source authenticity.

## Automated evidence

Constructed fixtures and actors exercise corrections (including same-location rationale changes),
withdrawal without source, chains, stale/foreign targets, malformed graph/owner/source data,
capacity and history saturation, clock rollback, version migration, exports and comparison.
Independent adversarial tests were authored separately from the production implementation.
The installed-wheel Chromium journey extends select/save/restart/reopen to correction, another
reopen and source-free withdrawal, validating downloaded and persisted records and viewport bounds.
Full-suite, coverage, package/browser, compatibility and exact-head CI results are recorded in the
integration PR and private verification report rather than claimed before their runs complete.

Frozen R-002 inputs, labels and results remain byte-for-byte unchanged. No R-002 rescore or
historical benchmark expectation change is part of this slice. Deterministic constructed
acceptance/comparison benchmarks retain their existing expectations.

## Remaining gates

Current source remains unreleased `0.2.5`; public v0.2.4 and the source-bound `4f12ae0` private
candidate archives are historical and unchanged. This work publishes no release, deploys no app
and contacts no participants. Stage 2 remains owner-led productization. Stage 1 stays closed at
zero and Stage 3 dormant. No automated test, simulated actor or agent review supplies genuine
independent use, customer validation, accessibility conformance or a completed beta.

The selected correction/withdrawal outcome is bounded. Metadata-assisted saved-review discovery
remains a possible separately selected improvement; a fresh version-bound evaluation packet and
publication require their own finite milestone and authorization. Neither is a standing queue.
