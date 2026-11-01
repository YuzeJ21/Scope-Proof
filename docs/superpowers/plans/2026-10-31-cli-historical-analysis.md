# Command-line Historical Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover and explicitly export one retained historical analysis through the CLI.

**Architecture:** A UI-independent metadata catalog and request model feed thin CLI handlers.
Reuse historical selection, locked consumption, report policy and atomic output helpers.

**Tech Stack:** Python 3.11+, Pydantic 2, argparse, pytest, installed Chromium.

**Spec:** `docs/superpowers/specs/2026-10-31-cli-historical-analysis-design.md`

## Global Constraints

- Explicit positive one-based position and required 64 lowercase hex whole-state fingerprint.
- No implicit selection/fallback, nested store locks, record migration or saved-byte mutation.
- Preserve historical export provenance policy, evidence boundaries and seven frozen R-002 files.
- Core stays independent of UI; no target-code execution, network fetch or new dependency.
- Source 0.2.5 unreleased/public v0.2.4 unchanged; Stage 3 dormant, no personal testing or qualifying reviews.
- No release, deployment, outreach or standing feature queue.

## Review Focus

- Pending/no-active records must allow historical handoff without confirming revised criteria.
- Duplicate heads, unknown revisions and changed history positions must not retarget selection.
- Wrong owner or changed saved state before preparation/consumption must fail without output.
- Missing provenance and invalid requests must emit no partial report or file.
- Existing/racing/symlink output targets must stay intact while saved records remain byte-identical.

### Task 1: Typed catalog and explicit CLI handoff

**Files:** Create `scopeproof_core/reviews/history_catalog.py`, `scopeproof_core/cli_history.py`,
`tests/cli/test_history.py`; modify `scopeproof_core/cli.py`; independent safety tests separate.

**Interfaces:** Consume existing `prepare_historical_analysis`, `locked_historical_analysis`,
historical JSON/Markdown renderers, `JsonReviewStore` and atomic output helper. Produce
`HistoricalExportRequest`, `RetainedAnalysisCatalog`, `build_history_catalog(state)` and
`register_history_commands(commands)`; register once from the existing parser.

- [ ] Write tests for catalog fields/order, empty and duplicate heads, unknown context, pending
  criteria, mandatory strict selection, stdout/file roundtrip, stale/owner/provenance failures and
  all five Review Focus conditions. Run `.venv/bin/python -m pytest -q tests/cli/test_history.py`;
  expect missing-command failures before production edits.
- [ ] Implement catalog/request schemas and thin explicit CLI handlers using existing services.
- [ ] Run new tests plus existing CLI/history/report tests; expect all pass and unchanged bytes.
- [ ] Commit source, tests, spec and plan. Complete task with the same focused verification.

### Task 2: Package verification and reviewed integration

**Files:** Modify `.github/workflows/ci.yml`, README, ROADMAP, release-status record;
create `docs/audits/2026-10-31-cli-historical-analysis.md` and a trusted installed CLI journey test.

**Interfaces:** Consume Task 1 commands against a fresh installed wheel outside the checkout.
Produce version-bound automatic evidence and exact-head reviewed integration.

- [ ] Add an installed CLI journey test: trusted constructed history-only record, catalog discovery,
  explicit position/fingerprint exports in JSON/Markdown, stale refusal and saved bytes unchanged.
  Run before/after against a baseline wheel to demonstrate missing-command RED, then current GREEN.
- [ ] Include new core/CLI regressions in the Windows lane; document commands and limits.
- [ ] Run full suite with unrounded 95% coverage, lint, lock, both deterministic benchmarks, clean
  install and existing packaged-browser checks; expect all pass. Verify frozen hashes unchanged.
- [ ] Obtain fresh independent whole-branch agent review, fix supported findings with regression
  coverage and rerun affected checks. Create PR, require exact-head hosted CI/CodeQL, guarded
  squash merge, clean synchronized checkouts and resulting-main checks.
