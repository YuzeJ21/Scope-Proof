# Readable Resolution Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a readable-report recipient inspect the recorded decision audit without opening ScopeProof or parsing JSON.

**Architecture:** Extend the existing validated exporters with a shared private event-field projection and separate inert Markdown/HTML history renderers. Reuse deterministic event classification, with no storage, lifecycle, gate or machine-format change.

**Tech Stack:** Existing Python/Pydantic, pytest, installed CLI, Streamlit/Playwright Chromium checks.

**Spec:** `docs/superpowers/specs/2026-11-01-readable-resolution-audit-design.md`.

## Global Constraints

- Existing unrounded coverage floor 95%; saved record v7, public v0.2.4 and source 0.2.5 unchanged.
- Preserve all seven frozen R-002 inputs/results, complete review state, decisions, gates and runtime truth.
- No personal testing, qualifying-review credit, release/deployment/outreach or Stage 3 advancement.
- No new report command, machine-format schema, adapter family, generic review/scanning/autofix, accounts or billing.
- All app probes use pytest isolation; installed processes use explicit temporary storage. No default local review-store access.

## Review Focus

- Superseded or prior-revision events must not appear current because their timestamp is later.
- A false review-level flag and legacy-unlinked manual claims must retain uncertainty instead of inferred revocation/runtime verification.
- Bundle-only/historical exports must not fabricate empty or parent-record event history.
- Hostile metadata/URLs must remain inert and must not create HTML/Markdown links or execute content.
- Offsets, naive legacy timestamps and empty optional fields must retain their actual recorded distinctions.

---

### Task 1: Complete validated readable event history

**Files:**
- Modify: `scopeproof_core/reporting/exporters.py`
- Create: `tests/reporting/test_resolution_audit_exports.py`
- Create: `tests/resolution_audit_fixture.py`
- Independent tests: `tests/reporting/test_resolution_audit_safety.py`

**Interfaces:**
- Consumes existing `export_markdown(value)`, `export_html(value)`, `_bundle_and_state(value)` and `resolution_event_statuses(events, active_revision_number)`.
- Produces the same public exporter signatures and complete inert history sections. Private shared projection: `_resolution_history_event_fields(event: ResolutionEvent, status: ResolutionEventStatus) -> list[tuple[str, str]]`. Format renderers consume `ReviewState | None`.
- Shared fixture: `resolution_audit_state() -> ReviewState`, containing constructed current, superseded and prior-revision events plus recorded final-acceptance true/false inputs; no default-store IO.

- [ ] **Step 1: Add failing report regressions and fixture.** Cover complete event fields, hand-derived status/append order, final true/false, empty versus unavailable history, inert hostile fields, linked/legacy runtime claims, timestamp offsets/naive labels, unchanged JSON/CSV and saved-state data. Independent safety tests may use their own fixtures.
- [ ] **Step 2: Run RED.** `.venv/bin/python -m pytest -q tests/reporting/test_resolution_audit_exports.py`; expected missing metadata/history assertions, not fixture validation errors.
- [ ] **Step 3: Implement private shared field projection and inert renderers.** Replace the incomplete Markdown loop and add the HTML section, preserving existing Pydantic and gate validation before rendering. Use recorded event data only and the spec's uncertainty distinctions.
- [ ] **Step 4: Verify focused/adjacent reports.** `.venv/bin/python -m pytest -q tests/reporting`; expected all pass, including the new report/safety cases. Run scoped Ruff and diff checks.
- [ ] **Step 5: Commit source, fixtures and report regressions.** No public-release or frozen-file changes.

### Task 2: Prove installed recipient handoff and record the outcome

**Files:**
- Modify: `tests/cli/test_installed_history.py`
- Modify: `tests/browser/test_packaged_workbench.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`, `ROADMAP.md`, `docs/releases/v0.2.3-status-and-next-stages.md`
- Create: `docs/audits/2026-11-01-readable-resolution-audit.md`

**Interfaces:**
- Consumes unchanged public exporters and `tests/resolution_audit_fixture.py` from Task 1.
- Produces one added installed CLI audit handoff case, a strengthened existing Markdown download journey, bounded Windows report checks and version-bound documentation. Browser collection remains 17 checks, including 3 installed journeys.

- [ ] **Step 1: Add installed CLI regression.** Copy only the constructed fixture into a temporary directory; execute the fresh installed interpreter with `-I`, save to an explicit temporary store, export Markdown/HTML through existing CLI commands, assert recorded fields/statuses/inert data and unchanged bytes. Verify historical Markdown reports unavailability without leaking current event history.
- [ ] **Step 2: Strengthen one existing installed browser journey.** Drive/download existing controls and assert actual enriched Markdown against the downloaded validated JSON, including status, actor/time and IDs; preserve all existing assertions and 17-check collection.
- [ ] **Step 3: Add bounded Windows report tests and update product/roadmap/status/audit docs.** State recipient outcome, automation limits, release and Stage 3 boundaries; do not create an ongoing parity queue.
- [ ] **Step 4: Run integration.** Full covered suite at 95%, Ruff/lock/diff checks, deterministic benchmarks, fresh wheel/install/installed CLI/browser journeys and source/package/frozen hashes. Expected all pass; record actual counts and failures separately.
- [ ] **Step 5: Commit the tested integration, configuration and documentation.** Complete this implementation task after observed local full-suite, installed CLI/browser and other Step 4 results.

## Final verification and integration

After both implementation tasks, dispatch one fresh whole-branch agent review. Fix supported
Important/Critical findings with RED→GREEN evidence, rerun affected checks and the full suite if
source changes. Preserve review head and fix heads.

Create a reviewable PR and require exact-head CI/CodeQL/Windows/Python and resolved findings,
fresh review/protection checks, expected-head merge, identical resulting tree, clean synchronized
checkouts and green resulting-main CI. Keep evidence outside the source tree in the version-bound
audit packet. Source-task completion does not mean integration or goal completion.
