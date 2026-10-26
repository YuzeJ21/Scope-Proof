# Changed-file Scope Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Ready when an inspectable changed file is uncited and has no explicit reviewer scope disposition.

**Architecture:** Persist an exact-head changed-file inventory on Review and append file-scope decisions in the active bundle. Derive unresolved paths in the core gate; preserve unknown historical inventories through a fail-closed record migration. Add bounded reviewer controls, versioned constructed expectations, and separate Stage 3 evidence.

**Tech Stack:** Python 3.11+, Pydantic 2, pytest, Streamlit, local JSON store.

**Spec:** `docs/superpowers/specs/2026-10-26-changed-file-scope-integrity-design.md`

## Global Constraints

- Follow `AGENTS.md`; implementation evidence is not runtime verification.
- Do not execute target-repository code in ScopeProof's server.
- Preserve frozen R-002 inputs/results and the historical `scope-expansion` label.
- Stage 3 needs genuine independent use and separate authorization.

## Review Focus

- Legacy unknown inventory versus verified empty inventory: migration and gate tests.
- Rename current path and exact-head mismatch: schema and gate tests.
- Skipped, generated-looking, and unrelated-looking paths: ingestion and gate tests.
- Changed-file versus unchanged-candidate evidence: gate tests.
- Dispositions on a superseded head or criteria revision: lifecycle and UI tests.

---

### Task 1: Core scope contract and gate

**Files:** `scopeproof_core/schemas/models.py`, `scopeproof_core/gates/evaluator.py`, `scopeproof_core/gates/validation.py`, `tests/gates/test_evaluator.py`, `tests/schemas/test_models.py`.

- [ ] Write and run failing regressions for uncited changed files, explicit decisions, invalid path/head, verified empty inventory, and unknown legacy inventory.
- [ ] Add Pydantic inventory and disposition models; derive scope coverage from exact-head changed-file citations.
- [ ] Add deterministic reason codes and ensure bundle validation recomputes the same gate.
- [ ] Run targeted tests and fix only supported failures.

### Task 2: Ingestion, lifecycle, migration, and reviewer control

**Files:** `scopeproof_core/{cli.py,demo.py,storage/json_store.py,reviews/lifecycle.py}`, `apps/web/app.py`, relevant tests.

- [ ] Write and run failing tests for inventory propagation, append-only head-bound disposition, reopened records, v1–v4 migration, and review controls.
- [ ] Implement construction and lifecycle paths; add bounded file decision UI and gate explanation.
- [ ] Run targeted tests and browser journey.

### Task 3: Benchmark and readiness record

**Files:** `scopeproof_core/evals/runner.py`, `evals/constructed_scope/`, `ROADMAP.md`, release and portfolio docs, relevant tests.

- [ ] Add a versioned current expectation without changing historical fixture/label or R-002.
- [ ] Run constructed and R-002 benchmarks and record exact results.
- [ ] Update roadmap, release status, and Stage 3 readiness with verified behavior versus missing independent-use evidence.

### Task 4: Verification and integration

- [ ] Run isolated and full automated tests at >=95% coverage, lint, clean install, packaged browser, and available Python/Windows checks.
- [ ] Obtain independent reviews, resolve supported findings, and rerun affected checks.
- [ ] Create and attach PR, verify exact head and CI, merge, then verify main and report the next genuine evidence gate.
