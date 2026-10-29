# Candidate-Selection Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explicitly disclose eligible, selected and omitted candidates without changing retrieval.

**Architecture:** Extend the existing Pydantic diagnostic with optional validated counters. Record
counts around the unchanged selection algorithm; use one core presentation helper for human
surfaces, and existing diagnostic serialization for JSON/CSV and saved reviews.

**Tech Stack:** Python/Pydantic, pytest, Streamlit AppTest, existing installed-wheel Playwright journey.

**Spec:** `docs/superpowers/specs/2026-10-29-candidate-selection-completeness-design.md`

## Global Constraints

- Keep the cap at 8 and matching/threshold/diversity/order/evidence/gate behavior unchanged.
- `eligible_candidate_count`, `candidate_limit`, `omitted_candidate_count`: all unknown or all
  strict integers; selected<=min(eligible,limit), eligible<=inspectable, omitted=eligible-selected.
- Historical metadata stays unknown; do not infer zero omissions or recompute a past selection.
- Preserve Pydantic export/storage validation, exact-head identity and reviewer controls.
- No frozen R-002 changes, R-003, personal tests, qualifying reviews, target execution or publication.

## Review Focus

- Zero, one, seven, eight, nine and twelve eligible lines show truthful cap counts.
- Identifier/threshold-rejected lines do not inflate eligible or omitted candidates.
- Mixed evidence and unchanged candidates retain exact IDs, order, scores and references.
- Partial/contradictory counters fail validation; raw historical records remain readable as unknown.
- Workbench, CLI and exports disclose bounded selection without changing gate or decision data.

## Task 1: Metadata and cross-surface disclosure

**Files:** diagnostic model, retrieval engine, core presentation, exporter and workbench modules;
focused schema/retrieval/report/AppTest regressions; existing CLI/browser tests; README/roadmap.

**Interfaces:** Existing retrieval/export APIs remain. Add
`candidate_selection_text(CriterionRetrievalDiagnostic) -> str` in core presentation.

- [x] Verify clean main and reproduce 12 eligible lines yielding 8 candidates without cap metadata.
- [x] Run baseline retrieval/schema/reporting/presentation/CLI checks: 653 passed.
- [x] Write focused regression tests and observe expected RED before production changes.
- [x] Add validated optional counters and record actual counts around unchanged selection.
- [x] Add shared presentation and all-format/CLI/workbench disclosure with historical fallback.
- [x] Extend the installed-wheel browser journey and verify real capped-review downloads.
- [x] Compare canonical evidence bytes against the pre-change constructed snapshot.
- [ ] Run focused and full tests, unrounded 95% coverage, Ruff and deterministic benchmarks.
- [x] Obtain independent whole-branch agent review and resolve supported findings.
- [ ] Commit/open PR; require exact-head CI/CodeQL, merge and verify resulting main.

## Execution record

- Baseline: `7086cd10efac7eed004c988f479dcf4280ddcfca`, clean reused isolated worktree.
- Constructed probe: selected lines 1–8 of twelve, 12 overlaps, zero below threshold, no omission field.
- Pre-change canonical evidence for 0/1/7/8/9/12-line constructed inputs is saved outside the repo
  for byte comparison; this is a regression fixture set, not a new research cohort or score.
- Ruling: use prose for human surfaces and typed fields for JSON/CSV; do not persist derived prose
  or change the established CSV schema merely to repeat the same facts.
- Ruling: preserve existing duplicate suppression. A constructed duplicate-line probe returns
  one candidate from two eligible entries on the baseline; the initial exact-minimum metadata
  check rejected it. A new regression observed that failure. Validate bounds instead and describe
  omissions during selection, with the unchanged limit reported separately.
- Final exact-head and resulting-main verification will be recorded in the PR integration record.
- RED: 20 core/schema failures before implementation; five report/workbench failures and four
  saved-review CLI failures on missing fields/disclosure; the installed-wheel browser check
  failed on the missing selection message (39.93s).
- The CLI JSON regression was corrected to use its existing `ReviewState.bundle` envelope before
  the final missing-field RED check; no product JSON format was changed to accommodate the test.
- Canonical evidence bytes remain identical for all six constructed boundary inputs. A separate
  duplicate-line regression confirms the baseline's one-candidate-from-two behavior remains.
- Final local focused checks: 728 passed. The complete packaged-browser module passed all 11
  checks in 120.30s, including capped-review reopening and actual CSV/JSON downloads. Ruff passed;
  both deterministic benchmarks passed (12 gate cases and two comparison cases, no mismatches).
- Independent review found a browser-fixture provenance gap: its generator inherited checkout
  cwd. It now runs from the external runtime directory and asserts the core module is inside
  the installed environment. The affected installed-wheel journey requires a fresh run.
- Follow-up agent review confirmed that fix and found no remaining actionable issues. The
  reviewer did not run tests or judge hosted outcomes, demand or Stage 3 readiness.
