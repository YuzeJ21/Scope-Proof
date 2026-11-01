# Saved Criteria Revision Changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inspect and hand off recorded requirement differences without weakening evidence comparison.

**Architecture:** Separate typed criteria snapshots and computed differences reuse the saved history
identity and locking pattern. A workbench action and deferred exports consume that core view.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit, pytest, installed Chromium.

**Spec:** `docs/superpowers/specs/2026-10-31-criteria-revision-changes-design.md`

## Global Constraints

- Preserve seven frozen R-002 files, record v7, current evidence-comparison/confirmation/gate semantics and public v0.2.4.
- Source stays 0.2.5 unreleased; Stage 1 closed at zero, Stage 2 owner-led, Stage 3 dormant.
- Core imports no UI; no target code execution or artifact fetching.
- No personal testing, qualifying reviews, release, deployment or outreach.

## Review Focus

- Same criterion ID reused for unrelated text must never imply semantic continuity.
- Provenance-only and order-only changes must remain visible without criterion-field changes.
- Missing historical provenance must stay unknown; current unconfirmed data must not gain confirmation.
- Current-revision-only mutations and old callbacks after same-record reopen must fail closed.
- Long/malicious-looking saved source text must stay complete, inert and reachable at narrow widths.

### Task 1: Typed saved criteria comparison and requirements-only exports

**Files:** Create `scopeproof_core/reviews/criteria_comparison.py`,
`scopeproof_core/reporting/criteria_comparison.py`, `tests/reviews/test_criteria_comparison.py`,
`tests/reporting/test_criteria_comparison.py`.

**Interfaces:** Consumes existing saved-state validation, `HistoricalAnalysisSelection` and store
locking. Produces `CriteriaSnapshot`, `CriteriaComparisonSelection`, `CriteriaRevisionComparison`,
`prepare_criteria_comparison(store, state, history_index)`,
`locked_criteria_comparison(store, selection)`, `export_criteria_comparison_json(report)` and
`export_criteria_comparison_markdown(report)`.

- [ ] Write tests with literal expected IDs, changed fields/positions and source/provenance flags,
  saved pending and unknown histories, rejected tampering/staleness and unchanged saved bytes.
- [ ] Run focused tests; expect missing comparison API failures before implementation.
- [ ] Implement the spec's typed receipt/snapshots, deterministic computed changes, locked saved
  preparation/consumption and safe complete exports.
- [ ] Run `python -m pytest -q tests/reviews/test_criteria_comparison.py tests/reporting/test_criteria_comparison.py`;
  expect all pass. Add independently authored safety regressions when available.
- [ ] Commit the typed core and tests.

### Task 2: Explicit workbench comparison, verification and integration

**Files:** Create `apps/web/criteria_comparison.py`, `tests/apps/test_criteria_comparison.py`;
modify `apps/web/historical_analysis.py`, `apps/web/deferred_exports.py`,
`tests/browser/test_packaged_workbench.py`, `.github/workflows/ci.yml`, README, ROADMAP,
`docs/releases/v0.2.3-status-and-next-stages.md`; create dated audit.

**Interfaces:** Consumes Task 1 APIs and existing historical selector reset/lease lifecycle.
Produces explicit criteria comparison and generation-bound click-time JSON/Markdown downloads.

- [ ] Write failing AppTest and deferred-export tests for explicit choice, saved pending revision,
  legacy unknown provenance, draft separation, reset, stale changes and post-render invalidation.
- [ ] Run focused tests; expect missing UI/lease behavior failures.
- [ ] Implement separate read-only panel/action, full inert preview and guarded deferred exports.
- [ ] Extend existing installed history journey with explicit comparison, exact downloaded JSON/MD,
  complete source text, saved-state preservation and desktop/phone/CSS-200% geometry assertions.
- [ ] Run focused UI/core tests and installed-browser checks; expect all pass. Add new core/CLI-free
  regressions to available Windows compatibility step.
- [ ] Align roadmap/release-status/README and dated audit with this outcome and evidence limits.
- [ ] Run full suite using existing 95% unrounded coverage floor; lint, lock, diff checks; both
  deterministic benchmarks; clean installed-wheel/package and frozen-hash checks. Expect all pass.
- [ ] Commit; obtain independent whole-branch agent review, resolve supported findings and rerun
  affected verification. Open PR; require exact reviewed-head CI/CodeQL, no unresolved findings,
  expected-head guarded merge and resulting-main CI/tree/clean-checkout verification.
