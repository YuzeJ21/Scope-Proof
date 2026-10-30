# Foreign Historical Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; one fresh
> independent whole-branch review after this coupled task.

**Goal:** Explicitly compare the current saved review with a historical analysis in another record.

**Architecture:** Extend the existing saved selector with a per-record analysis selector and snapshot
context; add an optional expected-baseline fingerprint to existing locked preparation. Existing
comparison models/exporters and download leases remain unchanged.

**Tech Stack:** Existing Python/Pydantic/Streamlit/pytest/Playwright; no new dependency.

**Spec:** `docs/superpowers/specs/2026-10-30-foreign-history-baseline-design.md`

## Global Constraints

- Load only the explicitly selected other saved record, not the entire history catalog.
- Secondary key `saved_comparison_analysis`, options `active` and `history:<index>`; no history-only
  default selection. Preserve existing top-level selector keys and current-record history behavior.
- Context binds record ID + whole fingerprint; changed snapshots require explicit reselection.
- Optional expected-baseline receipt is checked under existing core locks using Pydantic validation.
- No record/schema/gate/source-policy/frozen-study/release/deployment/human-evidence changes.

## Review Focus

- Pending selection cannot retarget after a same-index replacement or a reference-only edit.
- A record can have useful historical analysis without a compatible or available active analysis.
- A record can change after option discovery but before locked comparison preparation.
- History deletion/reorder must invalidate deferred callbacks rather than resolve a different item.
- Existing active/current-history selection and dirty-input/save-conflict protection must continue.

### Task 1: Complete foreign historical baseline selection

**Files:** Modify `apps/web/saved_comparison.py`, `scopeproof_core/reviews/saved_comparison.py`;
test core/UI/export cases; extend `tests/saved_comparison_fixture.py` and installed saved-comparison
browser journey. Align README/ROADMAP/status and existing Windows compatibility command.

**Interfaces:** Existing preparation signature plus kw-only
`expected_baseline_fingerprint: Fingerprint | None = None`; same `SavedComparisonSelection` and
`locked_saved_comparison`. UI returns the same comparison/selection tuple to existing consumers.

- [ ] Observe existing-core foreign-history support with independent constructed tests. Add failing
      expected-receipt race and UI discovery/selection assertions before production changes.
- [ ] Implement receipt validation under locks and the two-stage picker. Reset pending/applied
      choices on record/fingerprint changes, preserving current-history and active flows.
- [ ] Verify history-only/compatibility/replacement/reference mutation and deferred downloads with
      unchanged saved-byte assertions, safe actor labels and no network/target execution.
- [ ] Extend installed restart journey to choose a foreign history and verify both downloaded
      comparisons have its exact record/head/revision/reference identity and unchanged saved bytes.
- [ ] Update only current roadmap/status for this authorized outcome; preserve frozen research and
      release artifacts. Run full original95% coverage, lint/lock/diff/benchmarks, fresh browser and
      hosted Python/Windows; independently review and fix supported findings with RED→GREEN.
- [ ] Guarded exact-head merge, resulting-main checks/clean synchronization, owned-ledger archive.
