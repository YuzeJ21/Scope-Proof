# Workbench resolution audit implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify workbench and readable-report resolution history without changing recorded truth.

**Architecture:** Extract the existing plain label/value projection into core reviews. Both report
formats and the existing workbench block consume it; Streamlit renders values inertly.

**Tech Stack:** Python >=3.11, Pydantic 2, Streamlit, pytest/AppTest, installed-wheel Playwright.

**Spec:** `docs/superpowers/specs/2026-11-01-workbench-resolution-audit-design.md`

## Global Constraints

- No schema, storage v7, lifecycle/gate, JSON/CSV, dependency or frozen R-002 change.
- Core stays independent of Streamlit/GitHub.
- No personal testing/qualifying reviews, release/deployment/outreach or Stage 3 claims.
- Coverage >=95%; merge only after exact-head checks and review findings are resolved.

## Review Focus

- Review-level final false with accepted/manual extras must remain explicitly false.
- Criterion extras must not become review-level acceptance or hide criterion-only legacy warnings.
- Offset/naive timestamps must not become UTC assertions or determine append order.
- Hostile and long fields must stay inert and reachable on narrow/zoomed viewports.
- Inspection/download must not mutate persisted records, deterministic gates or machine exports.

### Task 1: Shared audit display and regressions

**Files:** core `reviews/resolution_history.py`; `reporting/exporters.py`; `apps/web/app.py`;
`tests/apps/test_resolution_history.py`; existing Streamlit assertions; spec/roadmap/audit record.

**Interfaces:** consumes validated `ResolutionEvent`, `ResolutionEventStatus`, `ReviewState`;
produces `resolution_history_event_fields(event, status) -> list[tuple[str, str]]` and shared
boundary/empty strings. No persistence/export model is introduced.

- [ ] Add mixed-event UI regressions with hand-derived primary/additional outcomes; run RED.
- [ ] Extract unchanged projection and render all fields with inert text/code, warning only for
      an applicable criterion manual legacy link; update intentional presentation expectations.
- [ ] Run AppTest/report regressions and confirm unchanged state/gates and report bytes.
- [ ] Commit the bounded source/test/docs change.

### Task 2: Installed handoff and integration

**Files:** `tests/browser/test_packaged_workbench.py`; product-import-only constructed fixture;
roadmap/status/audit record; `.github/workflows/ci.yml` only for a bounded Windows new-test step.

**Interfaces:** consumes shared display from Task 1; produces installed reopen/download assertions.

- [ ] Add a narrow installed-wheel journey for mixed legacy records, hostile data and responsive
      display; use explicit temporary records and assert saved bytes unchanged.
- [ ] Run full suite >=95%, lint, benchmarks, isolated install/CLI and real browser journeys.
- [ ] Obtain fresh whole-branch agent review; resolve supported findings with RED→GREEN and
      affected/full verification; record limits and frozen identities separately from R-002.
- [ ] Push a reviewable PR, await exact-head Python/Windows/browser/required checks, guarded merge,
      verify resulting main and clean synchronized checkouts, and report exact identities/results.
