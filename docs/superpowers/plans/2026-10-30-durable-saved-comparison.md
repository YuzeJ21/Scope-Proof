# Durable Saved Comparison Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for this integrated task. Steps track
> the shared core/UI/export contract; read the spec before implementation.

**Goal:** Reopen and explicitly compare compatible saved analyses without reanalysis or mutation.

**Architecture:** A pure core saved-selection model and locked comparison context reuse existing
storage/comparison. A small web selector and volatile lease provide explicit selection/reset and
deferred two-record exports. Existing comparison rendering consumes the validated result.

**Tech Stack:** Existing Python/Pydantic/Streamlit/pytest/Playwright; no added dependencies.

**Spec:** `docs/superpowers/specs/2026-10-30-durable-saved-comparison-design.md`

## Global Constraints

- No saved-format, gate, retrieval, dependency or frozen-research changes.
- No target execution, inferred decisions, publication, deployment or participant activity.
- Both saved-state fingerprints bind selection; downloads revalidate under shared record locks.
- No personal testing or qualifying reviews; all test actors and records are constructed.

## Review Focus

- Separate saved IDs are necessary for durable changed-head comparison, not only revision history.
- A history index must never silently retarget after record replacement.
- Record updates/deletion and candidate selection changes must invalidate old download callbacks.
- Pending drafts and current save conflicts must not expose an applied saved comparison.
- Comparison must preserve original JSON bytes, acceptance, decisions and all history.

### Task 1: Deliver durable saved comparison with complete automated evidence

**Files:** New `scopeproof_core/reviews/saved_comparison.py`, `apps/web/saved_comparison.py`,
core/web tests; modify `apps/web/app.py`, deferred exports and the packaged-browser test/fixtures.
Refresh current roadmap, README, Stage 2 packet and changelog after implementation.

**Interfaces:** `SavedComparisonSelection`; `prepare_saved_comparison(store, current,
baseline_review_id, history_index=None)`; `locked_saved_comparison(store, selection)` yields a
validated ReviewComparison. Web `render_saved_comparison_selector(...)` returns comparison and
selection; `deferred_saved_comparison_export(...)` captures a volatile selection lease.

- [x] Write and observe failing core tests for explicit other-record/history selection,
      incompatibility, stale fingerprints and record-byte preservation; implement the pure API.
- [x] Write and observe failing deferred-export tests for either-record change, selection lease
      invalidation and concurrent serialization; implement click-time rendering under both locks.
- [x] Write and observe failing AppTests for reopened explicit selection, missing analysis,
      pending input, invalidation and source identity display; wire the selector to existing view.
- [ ] Add an installed-wheel browser restart/reopen/comparison/download regression using shared
      install setup, isolated storage and accurately labelled constructed records; verify bytes.
- [ ] Refresh current guidance; run focused tests, full isolated 95% coverage, lint, benchmarks,
      packaged browser and independent whole-branch review. Fix supported findings with regression.
- [ ] Open PR; merge only after final-head CI/review are sound, then verify main and clean sync.

Expected: explicit saved-baseline selection survives the absence of the original browser session;
new and old scopes remain distinguishable, stale exports reject and saved review bytes never change.
