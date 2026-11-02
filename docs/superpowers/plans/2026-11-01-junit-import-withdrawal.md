# Audited JUnit import withdrawal implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire mistaken saved external JUnit context with immutable audit, source-free recovery
and consistent status, without changing acceptance truth or weakening import protection.

**Architecture:** Add a bounded withdrawal event to validated bundles and version8 storage, a pure
fingerprint-bound transition, and shared audit projections consumed by UI/CLI/exports/comparisons.
Original records remain retained; no replacement/reimport/reactivation protocol.

**Tech Stack:** Python>=3.11, Pydantic2, Streamlit, local JSON store/locks, pytest and Chromium.

**Spec:** `docs/superpowers/specs/2026-11-01-junit-import-withdrawal-design.md`

## Global Constraints

- Original imports and every non-audit fact/gate/decision/final flag remain unchanged.
- Existing20 retained imports and duplicate artifact/ID protection remain unchanged.
- Core has no UI/GitHub/fetch/target-code execution dependency; JUnit is non-gating external context.
- v1..7 do not acquire invented events or load-time disk writes; v8 requires explicit audit arrays.
- Frozen R-002 and existing benchmarks unchanged; unrounded coverage>=95%.
- No personal tests/qualifying reviews, release/deploy/outreach, new adapters or Stage3 claims.

## Review Focus

- Withdrawal of multi-criterion/accepted-review context must preserve whole-import scope and truth.
- Downgraded or missing active/history audit arrays must never silently reactivate data.
- Stale/deleted/externally mutated records and queued UI/CLI actions must append nothing.
- Old comparisons missing status must remain unknown; retained withdrawn artifacts are not removed.
- Hostile attribution, repeated withdrawal, full capacity and archived history retain safe boundaries.

### Task 1: Validated withdrawal lifecycle and storage8

**Files:** `scopeproof_core/schemas/models.py`, new `reviews/junit_audit.py`, `reviews/lifecycle.py`,
`storage/json_store.py`; new `tests/reviews/test_junit_audit.py`, `test_junit_audit_safety.py`,
`tests/storage/test_junit_audit_migration.py`, `tests/junit_audit_fixture.py`.

**Interfaces:** `JUnitImportWithdrawalEvent`, `ReviewBundle.junit_import_events`, derived
`active_junit_import_ids`; `withdraw_junit_evidence_import(state, *, import_id, reviewer, reason,
expected_state_fingerprint, occurred_at=None) -> ReviewState`; status/event lookup helpers.

- [ ] Add core happy/whole-import/invariance tests and independent safety/migration cases; run RED.
- [ ] Implement frozen event/aggregate validation, pure full-state bound transition and guards
      against preloaded events in initial/attached analyses. Reject repeated or foreign targets.
- [ ] Save v8; require both audit arrays in active/history bundles; pre8 rejects nonempty new events,
      preserves old read-only bytes, and keeps existing selected-reference migrations/guards.
- [ ] Run core/schema/storage/lifecycle regressions, updating current-writer assertions while
      retaining explicit historical v7 coverage. Commit verified implementation.

### Task 2: Reviewable withdrawal in workbench and CLI; complete handoff

**Files:** new `apps/web/junit_audit.py`, `scopeproof_core/cli_junit_audit.py`,
`apps/web/app.py`, `scopeproof_core/cli.py`, `reviews/comparison.py`, `reporting/exporters.py`;
new `tests/apps/test_junit_audit.py`, `tests/cli/test_junit_audit.py`,
`tests/reporting/test_junit_audit.py`, `tests/reviews/test_junit_audit_comparison.py`.

**Interfaces:** consumes Task1; `junit-imports` typed catalog and `withdraw-junit` locked command;
UI explicitly selects target and returns a proposed state for existing guarded persistence;
new optional comparison reference status/event fields; appended CSV `junit_import_audit` column.

- [ ] Write failing public-consumer tests for catalog/fingerprint, guarded mutation, status/audit
      reports and comparison context change, legacy-unavailable status and inert values.
- [ ] Implement typed CLI commands and read-only catalog, UI draft isolation/reset/guards and
      whole-import scope. Reopen without source; stale/delete/save failure must not report success.
- [ ] Render all retained originals and metadata in JSON/MD/HTML/CSV and previous/current comparison;
      hash withdrawal context without changing active-import hashes or gate truth.
- [ ] Run affected UI/CLI/report/comparison regressions and existing import-draft guards; commit.

### Task 3: Installed recovery, independent review and guarded integration

**Files:** new `tests/browser/test_junit_withdrawal.py`, installed CLI journey,
`.github/workflows/ci.yml` bounded Windows step, README/ROADMAP/status/audit documentation.

**Interfaces:** consumes Tasks1/2. Produces version-bound verification packet outside source.

- [ ] Verify installed-wheel source-free reopen→withdraw→restart→download in disposable storage,
      preserving original import/mappings and gates. Record actors/screenshots as automation.
- [ ] Run full suite>=95%, lint/lock/diff, deterministic12+2 benchmarks, clean-install/CLI/browser
      journeys, frozen hashes and native Python/Windows compatibility checks.
- [ ] Fresh independent whole-branch review; resolve supported findings with RED→GREEN and affected
      checks/full suite. Record evidence limits and rulings without invented human validation.
- [ ] Prepare PR, await exact-head checks, guarded merge, verify identical main tree and post-merge
      CI/clean synchronized checkouts. Archive only this plan's ledger and complete goal.
