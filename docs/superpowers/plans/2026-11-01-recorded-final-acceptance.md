# Recorded Final Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inspect recorded final-acceptance values separately from gate labels in comparisons.

**Architecture:** Typed bundle projections bind to existing comparison identities. Thin report/UI
renderers show explicit values and unavailable attribution; saved comparison guards remain intact.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit, pytest, installed Chromium.

**Spec:** `docs/superpowers/specs/2026-11-01-recorded-final-acceptance-design.md`

## Global Constraints

- No event reconstruction; actor/time/rationale/event association unavailable in analysis snapshots.
- Missing old projection remains unavailable; strict explicit bool, no false defaults or revocation inference.
- Preserve gates/decisions, confirmation, v7 bytes, seven frozen R-002 files and core/UI boundary.
- Source 0.2.5 unreleased/public v0.2.4; Stage 1 zero/Stage 3 dormant. No personal testing/qualifying reviews.
- No release, deployment, outreach, dependency, target execution or standing queue.

## Review Focus

- Equal Conditional gates must not hide different recorded acceptance values.
- Unknown revisions/missing old projections must not acquire invented attribution or false values.
- Incomplete, coerced, forged nested or derived fields must not bypass Pydantic validation.
- Projection identity must match both owning analyses; stale acceptance-only changes must invalidate saved selections.
- Dynamic identities must remain inert/readable in exports and desktop/phone/zoom views.

### Task 1: Validated non-gating core projection

**Files:** Create `scopeproof_core/reviews/final_acceptance_comparison.py`,
`tests/final_acceptance_fixture.py`, `tests/reviews/test_final_acceptance_comparison.py` and
independent safety tests; modify `scopeproof_core/reviews/comparison.py`.

**Interfaces:** Produce `FINAL_ACCEPTANCE_COMPARISON_BOUNDARY`, `FinalAcceptanceSnapshot`,
`FinalAcceptanceComparison.from_bundles(previous,current)` and optional comparison field
`final_acceptance_comparison`/computed `final_acceptance_compared`, exactly as spec.

- [ ] Write failing core cases for all bool pairs/equal gates, old missing projection, strict fields,
  unknown revisions, detached copies, identity binding and derived tampering. Run focused pytest;
  expect missing API/field failures before implementation.
- [ ] Implement schema/projection/owner validation, reuse existing complete bundle validation.
- [ ] Run new and existing comparison/core/benchmarks tests; expect unchanged gate/delta semantics.
- [ ] Commit core, tests, spec and plan; retain RED/GREEN evidence.

### Task 2: Reports, workbench and installed-browser inspection

**Files:** Create `apps/web/final_acceptance_comparison.py`, report/AppTest tests; modify
`scopeproof_core/reporting/exporters.py`, `apps/web/app.py`, trusted saved-comparison fixture and
`tests/browser/test_packaged_workbench.py`. Independent agent owns this presentation slice.

**Interfaces:** Consume Task1 model; produce `render_final_acceptance_comparison(context)` and
separate Markdown section. Keep existing section limits; no event/actor inference.

- [ ] Write failing JSON/Markdown/UI tests for all values, missing context, safe identities and
  separate gate display. Implement inert rendering, register once in existing comparison view.
- [ ] Extend installed saved-comparison journey for constructed equal-gate/different-flag values,
  reopened/foreign/history selection and JSON/Markdown, with existing responsive/saved-byte checks.
- [ ] Run focused presentation checks; expect pass. Commit presentation and tests.

### Task 3: Reviewed integration and source-bound evidence

**Files:** Modify CI Windows subset, README, ROADMAP and release-status; add dated audit.

**Interfaces:** Consume Tasks1/2; produce a version-bound automatic evidence packet and verified main.

- [ ] Add focused Windows coverage and align docs. Run full95% unrounded coverage, lint/lock/diff,
  both benchmarks, clean package/browser and hosted Python/Windows checks; frozen hashes unchanged.
- [ ] Obtain fresh whole-branch independent review, resolve supported findings with regressions and
  affected checks. Require exact-head CI/CodeQL, guarded squash merge and clean verified main.
- [ ] Archive only this task's owned ledger with hashes; report exact identities/results and genuine-use gate.
