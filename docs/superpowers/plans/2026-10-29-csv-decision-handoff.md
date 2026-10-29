# Actionable CSV Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve review-level blockers and recovery guidance in existing CSV handoffs.

**Architecture:** Append six JSON-array columns in the shared CSV exporter after its existing
Pydantic validation. Reuse the validated gate and existing guidance; CLI and workbench continue
using the same exporter without new application behavior or persisted schema changes.

**Tech Stack:** Python, Pydantic, standard-library CSV/JSON, pytest, existing packaged Playwright journey.

**Spec:** `docs/superpowers/specs/2026-10-29-csv-decision-handoff-design.md`

## Global Constraints

- Preserve existing CSV column order, scalar formula safety, CRLF records and one row per criterion.
- Append `gate_reason_codes`, `gate_blocking_criteria`, `gate_conditional_criteria`,
  `gate_unresolved_criteria`, `gate_resolved_exceptions`, `gate_guidance`; all values are JSON arrays.
- No gate, retrieval, saved-schema, frozen R-002, R-003, independent-use count or stage change.
- No target-code execution, personal testing, qualifying reviews, release, deployment or outreach.

## Review Focus

- Accepted criteria with absent final acceptance retain its explicit reason and next action.
- Mixed blocking, conditional, unresolved and exception groups remain distinguishable.
- Failing observed CI remains visible even when every criterion has an accepted decision.
- CSV quoting, formula-containing text and empty JSON arrays remain reversible and safe.
- Export validation, exact-head identity and existing reviewer decisions remain unchanged.

## Task 1: Shared projection and regression coverage

**Files:** `scopeproof_core/reporting/exporters.py`, new
`tests/reporting/test_csv_gate_handoff.py`, existing CLI/browser test modules.

**Interfaces:** Consume `ReviewBundle | ReviewState`; retain `export_csv()` returning text.
Produce additive CSV columns from existing `GateDecision` fields and `gate_guidance()`.

- [x] Record the baseline reproduction and existing reporting/CLI baseline (169 passed).
- [x] Write focused reporting regressions and observe failures against the unchanged exporter.
- [x] Add CLI and installed-browser assertions; verify the missing-column failures.
- [x] Append the six columns and serialize validated gate arrays; do not change existing rows.
- [x] Run focused reporting/CLI tests and the installed-wheel browser journey.
- [x] Document the source-only CSV contract and this named product-improvement slice.
- [ ] Run Ruff, full pytest with unrounded 95% coverage, both benchmarks and package checks.
- [x] Obtain independent whole-branch agent review; resolve supported findings.
- [ ] Commit and open a reviewable PR; verify final exact-head CI/CodeQL before merging.
- [ ] Verify resulting main, preserve exact integration evidence in the PR and finish the goal.

## Execution record

- Baseline: clean isolated worktree at `a9632050b7e10fd3301d67d15f1cbffec20c5168`.
- Constructed reproduction: four accepted CSV rows, `Review incomplete`, sole validated reason
  `final_acceptance_required`, and no `gate_` CSV columns.
- Reporting regression RED: four cases fail on the absent columns; fixtures validate first.
- CLI RED: the saved-review export fails on missing `gate_reason_codes`; the installed-wheel
  Chromium journey independently fails on that missing column after a real CSV download (41.95s).
- Ruling: use the existing CSV stdout command; an initial test-only assumption about an export
  `--output` flag was removed before implementation because that flag is not supported.
- The failing-CI fixture now records a complete categorized failing observation. Omitting that
  observation correctly exercised the existing historical-unavailable migration instead, so the
  fixture was corrected rather than changing product CI policy.
- Local GREEN: 174 reporting/CLI cases; all 11 packaged-browser checks, including a CSV download
  from the freshly installed wheel (89.10s). Ruff and both deterministic benchmarks passed;
  12 gate cases and two comparison cases had no mismatches. Gates, retrieval, frozen inputs,
  workflow payloads and dependency/version files remain untouched.
- Implementation and hosted results will be bound to their actual commits in the PR record.
- Independent whole-branch agent review found no actionable findings; the reviewer did not run
  tests or judge hosted outcomes, spreadsheet-application behavior or genuine-use evidence.
