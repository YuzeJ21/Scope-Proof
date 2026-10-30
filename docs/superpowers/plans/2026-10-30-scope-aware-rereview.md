# Scope-aware Re-review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> integrated task. Steps use checkbox syntax for tracking.

**Goal:** Explain changed-file scope and unresolved scope work between reviewed heads.

**Architecture:** A pure Pydantic scope-comparison module projects validated bundle facts.
The existing comparison owns it; exports and workbench consume it without changing gates.

**Tech Stack:** Existing Python 3.11+, Pydantic, Streamlit, pytest and packaged Chromium checks.

**Spec:** `docs/superpowers/specs/2026-10-30-scope-aware-rereview-design.md`

## Global Constraints

- No target code execution, inferred acceptance, gate/retrieval changes or saved-record migration.
- Preserve unknown historical inventory, incomplete ingestion and exact-head decision identity.
- Preserve frozen R-002, public v0.2.4 and private v0.2.5 bytes at `4f12ae0`; no publication.
- Stage 2 development needs no personal test or qualifying review; Stage 3 remains dormant.

## Review Focus

- Same status/candidate counts can hide a newly uncited file: assert the new path in comparison.
- Missing inventory is not empty: assert null deltas and visible unknown context.
- Same path is not same content or transferred acceptance: inspect captions and fresh decision needs.
- Renamed/skipped/generated metadata must not invent exemptions: cover native facts and limits.
- Mutated head/decision or Markdown-like paths must reject or render inertly at exports/UI.

### Task 1: Deliver scope-aware re-review and an outcome-driven roadmap

**Files:** Create `scopeproof_core/reviews/scope_comparison.py`; modify comparison, exporters,
`apps/web/app.py`; add focused core/export/AppTest regressions; update current roadmap/positioning.

**Interfaces:** `compare_reviews(previous, current) -> ReviewComparison` keeps its signature and
gains optional `file_scope: FileScopeComparison | None`. New comparisons always populate it;
legacy missing fields stay unknown. `FileScopeComparison.previous/current` hold typed snapshots;
`inventory_changes` and each snapshot's `unresolved_paths` are computed from retained facts.

- [ ] Write core and export tests for the reproduced uncited-file omission; observe failure.
- [ ] Add snapshots/deltas and bind them to comparison heads; test latest decisions, unknowns,
      native rename metadata, skips, generated paths, order independence and nonmutation.
- [ ] Render scope context in Markdown/JSON and workbench; add behavior-based AppTests and
      escaping/tampering regressions. Capture constructed before/after screens automatically.
- [ ] Update four current guidance documents to a bounded ranked Stage 2 queue: scope comparison
      now, durable saved-history re-review next, explicit evidence selection design-only later.
- [ ] Run focused tests, lint, full suite at 95%, deterministic benchmarks and installed-browser
      journey; retain command logs. Review the complete branch independently.
- [ ] Fix supported findings, open a PR, wait for exact-head checks, merge with expected-head
      guard, verify resulting main and synchronize clean local checkouts.

Expected final evidence: all relevant automated checks pass and the added uncited path is visible
despite unchanged candidate/status counts. No human validation, release or deployment claim.
