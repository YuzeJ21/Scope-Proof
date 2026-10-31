# Historical Analysis Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development task by task. Steps use checkbox syntax for tracking.

**Goal:** Inspect and hand off one retained analysis without a compatible active analysis.

**Architecture:** Add a saved-state/history-position receipt and historical-only typed report, reuse validated bundles/safe Markdown and existing record locks, and add a read-only UI with generation-bound deferred downloads. No active-state replacement or persistence migration.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit/AppTest, pytest/coverage, installed-wheel Chromium and existing protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-31-historical-analysis-inspection-design.md`.

## Global Constraints

- Keep original criteria confirmation, gate/comparison semantics, current authority controls, record v7 and frozen R-002 unchanged.
- Historical JSON/Markdown only; no synthesized ReviewState, CSV/HTML history formats or event-history replay.
- Full saved-state and analysis fingerprints bind explicit history position; typed reports carry historical/validation identity.
- Missing provenance still blocks report export; exact unknown revision remains unknown.
- No artifact access/execution, new dependencies, release/deploy/outreach/qualifying reviews/Stage 3 claim.

## Review Focus

1. Saved history-only state and incompatible current criteria must be inspectable without active confirmation or authority.
2. Stale/replaced/deleted/reordered histories and runtime/reference-only changes must block old UI/download receipts.
3. Unknown revisions, old producers and missing provenance must remain explicit; no defaults fabricate historical fields.
4. Malicious/long text and a historical Ready result must stay inert and visibly historical at phone/CSS zoom.
5. Pending current inputs, source contradictions and reopen/reset must not promote history into current controls or preserve an invalid download lease.

### Task 1: Saved historical report and export core

**Files:** New `scopeproof_core/reviews/historical_analysis.py`, `scopeproof_core/reporting/historical_analysis.py`; new tests under reviews/reporting, with independent safety tests in `tests/reviews/test_historical_analysis_safety.py`.

**Interfaces:** Produces `HistoricalAnalysisSelection`, `HistoricalAnalysisReport`, `prepare_historical_analysis(store, state, history_index)`, `locked_historical_analysis(store, selection)`, `export_historical_json(report)`, `export_historical_markdown(report)` as specified.

- [ ] Write/run RED tests for history-only/different-criteria access, explicit unknown revision, complete historical output, no state/byte mutation and stale/owner rejection.
- [ ] Implement the minimal typed receipt/report, locked selection, fingerprints and safe historical renderers; preserve existing provenance eligibility.
- [ ] Run core/report/independent safety and affected storage/comparison checks; fix supported failures and commit.

### Task 2: Read-only workbench and deferred downloads

**Files:** New `apps/web/historical_analysis.py`; modify `apps/web/deferred_exports.py`, `apps/web/app.py`; new `tests/apps/test_historical_analysis.py` and deferred tests.

**Interfaces:** Consumes Task 1. Produces `HistoricalAnalysisExportLease`, `deferred_historical_export(selection, renderer, *, store, lease)` and `render_historical_analysis_selector(current, *, store, current_is_saved)` plus `clear_historical_analysis_selection()` for reset/reopen.

- [ ] Write/run RED AppTest/deferred cases for saved unconfirmed current revision with history, no auto-selection, explicit inspection, current draft separation, missing provenance, source-conflict boundary, stale callbacks and literal text.
- [ ] Implement history selector, receipt/lease invalidation, read-only labeled historical report and JSON/Markdown downloads under the correct saved fingerprint.
- [ ] Run affected AppTest/export/storage controls, require no active-state/gate writes, and commit.

### Task 3: Installed journey, documentation and checked integration

**Files:** New constructed history fixture; extend `tests/browser/test_packaged_workbench.py`; update README, ROADMAP, current release-status record, dated audit and Windows compatibility fragment.

**Interfaces:** Trusted constructed fixture usable from installed wheel supplies saved history-only different-criteria state; existing fixture behavior remains unchanged. Installed browser reopens/inspects/downloads through restart without mutating saved records.

- [ ] Add automatic browser assertions for historical type/head/revision/producer/data, missing active analysis, JSON/Markdown downloads, desktop/phone/CSS-zoom geometry and stale-choice boundaries. Keep simulated actors explicit.
- [ ] Align current docs and preserve dated/frozen artifacts. Run full 95% coverage, lint/lock/contracts, both benchmarks and clean installed browser checks against frozen source.
- [ ] Obtain fresh independent whole-branch review, reproduce/fix supported findings and rerun affected checks. Prepare PR and require exact-head CI/review before expected-head guarded merge.
- [ ] Verify resulting-main CI/CodeQL/base advance, entire-tree/package bindings, frozen hashes and clean synchronized checkouts; save final report and archive only this task's owned ledger.
