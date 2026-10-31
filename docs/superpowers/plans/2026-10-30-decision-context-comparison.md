# Recorded Decision Context Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make same-label reviewer decision and recorded runtime-context differences inspectable in existing compatible comparisons.

**Architecture:** Add a non-gating validated projection beside existing comparison sections. Reuse existing relationship, storage-fingerprint, deferred-download and safe-rendering boundaries; never mutate a saved analysis.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit, pytest/AppTest, installed-wheel Chromium, existing protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-30-decision-context-comparison-design.md`.

## Global Constraints

- Preserve existing enum deltas, deterministic gate semantics, explicit confirmation and record version 7.
- Complete recorded latest criterion resolutions and retained runtime observations only; no final-acceptance/event-history expansion.
- Projection is non-gating reporting; no runtime execution, fetching, authentication or new evidence capture.
- Freeze the seven R-002 inputs/results; new constructed cases remain separate.
- Source stays unreleased 0.2.5; no personal testing/qualifying reviews/release/deploy/outreach/Stage 3 advance.

## Review Focus

1. Same enum, changed note/actor/runtime limitations must remain visible without changing old deltas.
2. Missing legacy runtime links and missing old comparison context must not become inferred links or invented empty snapshots.
3. Serialized/mutated owner identities, incomplete nested records and forged computed values must fail or recompute safely.
4. Untrusted notes, results, artifact references and very long identities must remain inert and within viewport bounds.
5. Saved history/reference/runtime mutations must invalidate pending/applied/deferred comparison output without writing saved records.

### Task 1: Core comparison projection

**Files:** New `scopeproof_core/reviews/decision_context_comparison.py`; modify `scopeproof_core/reviews/comparison.py`; new `tests/reviews/test_decision_context_comparison.py` and independently authored `tests/reviews/test_decision_context_safety.py`.

**Interfaces:** Produces `DecisionContextSnapshot`, `DecisionContextComparison.from_bundles(previous: ReviewBundle, current: ReviewBundle)`, derived `record_changes`, and optional `ReviewComparison.decision_context_comparison`. Rows expose `criterion_id`, `kind`, `previous`, `current`; each side exposes `resolution`, `runtime_evidence` and derived `runtime_link_status`.

- [ ] Write failing cases for same-label context changes, legacy links, known empty vs unavailable and owner/link validation. Assert original comparison fields and source bytes/gates unchanged.
- [ ] Run focused tests and record expected missing-projection RED evidence.
- [ ] Implement the detached canonical snapshots, strict complete nested input, derived rows and owning comparison checks described by the spec.
- [ ] Run core comparison/storage regressions; require all pass. Run independent adversarial cases and fix supported failures.
- [ ] Commit the verified core slice.

### Task 2: Reports and workbench

**Files:** Modify `scopeproof_core/reporting/exporters.py`, `apps/web/app.py`; new `apps/web/decision_context_comparison.py`, `tests/reporting/test_decision_context_comparison.py`, `tests/apps/test_decision_context_comparison.py`.

**Interfaces:** Consumes Task 1 projection; produces `render_decision_context_comparison(context: DecisionContextComparison | None)` and comparison JSON/Markdown context under existing render/export authority.

- [ ] Write failing JSON/Markdown/AppTest cases for both owners, same-enum notes, linked/unlinked runtime limitations, missing context, known empty and unsafe literal text/URLs.
- [ ] Run tests to observe missing-output RED, then implement safe informative rendering and integrate under existing comparison guards.
- [ ] Run affected reports/AppTests and deferred saved-comparison mutation tests; require all pass.
- [ ] Commit the verified presentation slice.

### Task 3: Installed journey and integration

**Files:** Extend `tests/saved_comparison_fixture.py`, `tests/browser/test_packaged_workbench.py`; update README, ROADMAP, current release-status record, new dated audit and Windows CI fragment if needed.

**Interfaces:** Construct explicit automated same-enum decisions and runtime observations on current/own-history/foreign-history records; preserve old fixture behavior unless opted into by keyword.

- [ ] Write/run failing installed comparison output assertions for same-label context and complete artifact/limitations; retain save/restart/byte invariants and geometry checks.
- [ ] Extend the constructed fixture and installed journey; confirm actual newly built wheel imports and source identity.
- [ ] Align current documents with exact behavior/limits; keep historical snapshots and release artifacts unchanged.
- [ ] Run isolated focused checks, full suite/95% coverage, lint/lock, deterministic benchmarks, clean install and browser checks sequentially where resource contention matters.
- [ ] Commit, obtain fresh independent whole-branch review, reproduce/fix supported findings with RED/GREEN and rerun affected checks.
- [ ] Prepare PR, verify exact-head CI/CodeQL/reviews, expected-head guarded merge, verify resulting-main CI and clean synchronized checkouts. Archive only this task's execution ledger and report source-bound results.
