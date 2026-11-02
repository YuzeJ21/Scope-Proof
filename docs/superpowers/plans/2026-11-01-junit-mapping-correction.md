# Audited JUnit Mapping Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct saved JUnit organizational mappings through attributable immutable history.
**Architecture:** Literal-tagged union in the existing ordered audit stream, replayed against
retained originals. Shared effective mapping projection feeds source-free workbench, locked CLI,
reports and comparison; no gate or reviewer-truth change.
**Tech Stack:** Existing Python3.11+, Pydantic2, Streamlit, pytest/Playwright, JsonReviewStore.
**Spec:** docs/superpowers/specs/2026-11-01-junit-mapping-correction-design.md

## Global Constraints

-20 retained imports,20 corrections,20 unique withdrawals,40 audit events; never free slots.
-Recordv9 writes/read1–9; pre-v8 reject nonempty audit; v8 reject correction events.
-Retain gate migration cutoff<8 or existing CI migration, not current writer version.
-Explicit confirmed criteria, exact owner/head/revision/provenance and full-state fingerprint.
-Keep originals, archives, gates/runtime/findings/decisions/final flags and frozen R-002 unchanged.
-No new dependency, target execution, reimport/reactivation, release/deploy/outreach or Stage3.
-User delegates routine decisions; inline source implementation plus independent test support and
  one fresh whole-branch review. No personal testing/qualifying review or approval menus.

## Review Focus

-Mapping cycles and interleaved imports must remain ordered even with reversed asserted clocks.
-Saturated correction history must leave every retained import withdrawable.
-v8 migration must reject malformed saved gates instead of newly normalizing them.
-Criteria removed from current mappings must retain visible audit without stale current cases.
-Queued browser writes and failed storage must preserve external changes/deletions and drafts.

### Task 1: Validated correction lifecycle and historical storage

**Files:** models.py; reviews/junit_audit.py; new reviews/junit_correction.py;
storage/json_store.py; tests/reviews/test_junit_correction.py; independent
tests/reviews/test_junit_correction_safety.py; tests/storage/test_junit_correction_migration.py.

**Interfaces:**
-Produces JUnitMappingCorrectionEvent, JUnitImportEvent union, junit_mapping_sha256;
  bundle.effective_junit_mappings: dict[str,list[JUnitCriterionMapping]].
-Produces effective_junit_mappings(bundle,import_id), junit_mapping_correction_events(bundle,id),
  junit_correction_fields(event), action-filtered withdrawal/status helpers.
-Produces correct_junit_mappings(state, *, import_id,criterion_mappings,reviewer,reason,
  expected_state_fingerprint,confirm_whole_import,occurred_at=None) -> ReviewState.
-Produces JUnitMappingCorrectionDraft; new_junit_correction_draft(state,import_id),
  replace_junit_correction_group(state,draft,criterion_id,test_case_ids),
  remove_junit_correction_group(state,draft,criterion_id), all fingerprint-bound pure operations.

- [ ] Write tests for explicit full snapshot, immutable originals/full state, cycles/reversed clocks,
  chain IDs/digests, unknown/overlapping cases/criteria, nonboolean confirmation, no-op/empty,
  terminal withdrawal and saturation preserving withdrawal. Independent migration tests cover
  active/history v1–8, downgraded correction events and invalid-v8 gates.
- [ ] Run `.venv/bin/python -m pytest -q tests/reviews/test_junit_correction.py`.
  Expected: missing-feature failures before source exists.
- [ ] Implement strict event/replay/projection/transition and draft operations; retain old withdrawal
  defaults, change terminal filters to action, reserve withdrawal capacity and v9 historical checks.
- [ ] Run new core/safety/migration tests plus previous audit/lifecycle/storage regressions.
  Expected: all pass, original records unchanged on load and old withdrawal behavior preserved.
- [ ] Commit scoped source/tests/design/plan: `feat: add audited saved JUnit mapping correction`.

### Task 2: Effective mappings across product consumers

**Files:** new apps/web/junit_correction.py; apps/web/app.py and junit_audit.py;
core/cli_junit_audit.py; reporting/exporters.py; reviews/comparison.py;
new tests/apps/test_junit_correction.py, tests/cli/test_junit_correction.py,
tests/reporting/test_junit_correction.py, tests/reviews/test_junit_correction_comparison.py.

**Interfaces:** Consumes Task1 contracts. Produces source-free correction draft renderer/request,
pending/clear/prepare helpers; CLI correct-junit-mappings with repeated --map CRITERION=CASE and
--confirm-whole-import; typed catalog/receipt; original/effective/audit projections across formats.

- [ ] Write consumer failures for group move/removal/new retained cases, reset/confirmation/pending,
  locked save/stale/deleted/failure cases, explicit CLI flags/races, original/effective output,
  CSV retired-group audit and comparison mapping cycles/owner/history validation.
- [ ] Run new consumer test files. Expected: missing CLI/UI/projection behavior failures.
- [ ] Implement all associations using shared effective mappings. Preserve old uncorrected CSV
  columns/context hashes. Comparison carries original mappings, retained-case/current-criterion IDs,
  correction events and full owner context; replay validation rejects forged chains and mappings.
- [ ] Implement symmetric pending-write guards and commit-before-success UI behavior. Pristine
  initialized preview is not pending; all edits/unstaged controls invalidate confirmation.
- [ ] Run new consumers plus prior audit/reference/runtime/import/comparison regressions.
  Expected: all pass, no unrelated user-flow or gate change.
- [ ] Commit: `feat: expose corrected JUnit mappings across review handoffs`.

### Task 3: Installed journeys, review and guarded integration

**Files:** new tests/browser/test_junit_correction.py and tests/cli/test_installed_junit_correction.py;
README.md; ROADMAP.md; release-status record; new docs/audits/2026-11-01-junit-mapping-correction.md;
.github/workflows/ci.yml bounded Windows/installed CLI paths.

**Interfaces:** Consumes whole feature; produces reproducible version-bound external evidence packet.

- [ ] Write installed CLI race/export/catalog and Chromium source-free correction→restart→download
  plus changed/deleted queued-write cases. Observe failure against preserved old PR244 wheel before
  rebuilding; all actors/fixtures explicitly constructed.
- [ ] Run isolated feature regressions, full covered suite at unrounded>=95%, Ruff/lock/diff,
  source/installed deterministic12+2 benchmarks, clean wheel/pip check, installedCLI and all browser
  checks. Expected: all pass; retain original failed runs separately and frozen seven file hashes.
- [ ] Refresh docs with actual contract and remaining boundaries; no new release or genuine-use claim.
- [ ] Commit: `test: verify installed JUnit mapping correction journeys`.
- [ ] Fresh independent whole-branch review with spec/plan/ReviewFocus/rulings and exact head; fix
  supported Critical/Important findings through reproduced tests, record minors and declined areas.
- [ ] Push scoped branch, create reviewable PR, wait exact-head CI/CodeQL and unresolved reviews.
  Expected: required verify15368 and CodeQL57789 green on exact proposed head, latest base clean.
- [ ] Guarded squash merge using expected head; verify identical main tree, primary fast-forward and
  borrowed checkout detached at main, both clean. Wait separate main CI and exact-main CodeQL
  analysis jobs; do not invent a missing main aggregate check.
- [ ] Save final evidence/report/assertions, archive/hash-check only own execution ledger and complete
  goal. Expected: no pending required work and no personal testing/qualifying/Stage3 evidence claim.
