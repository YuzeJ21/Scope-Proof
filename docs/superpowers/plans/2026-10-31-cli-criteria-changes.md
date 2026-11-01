# Headless Criteria Changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export saved old-versus-current requirements changes through an explicit safe CLI command.

**Architecture:** Extend the small historical CLI adapter, reusing its typed request and the
existing criteria-comparison preparation, lock-bound consumption, exporters and atomic output.

**Tech Stack:** Python 3.11+, argparse, Pydantic 2, pytest, installed Chromium.

**Spec:** `docs/superpowers/specs/2026-10-31-cli-criteria-changes-design.md`

## Global Constraints

- Strict positive one-based history position and required 64 lowercase hex whole-state fingerprint.
- No fallback selection, nested locks, criteria confirmation, evidence/decision/gate change or saved-byte mutation.
- Requirements-only unknown provenance never relaxes full acceptance-report export policy.
- Preserve record v7, seven frozen R-002 files, core/UI boundary and source 0.2.5 unreleased/public v0.2.4.
- No target-code execution, network fetch, dependency, release, deployment, outreach or standing queue.
- No personal testing or qualifying reviews; Stage 1 zero, Stage 3 dormant.

## Review Focus

- Pending/no-active current criteria must remain saved/unconfirmed and separate from historical evidence.
- Missing provenance and unknown revisions must stay unknown without weakening acceptance-report restrictions.
- Same-head or same-ID records must not imply semantic continuity or silently change selected position.
- Owner/state changes before preparation/consumption must fail without stdout/file output.
- Existing/racing/symlink outputs and concurrent record writers must preserve lock/no-overwrite guarantees.

### Task 1: Explicit requirements-change CLI export

**Files:** Modify `scopeproof_core/cli_history.py`; create `tests/cli/test_criteria_changes.py`
and independently authored `tests/cli/test_criteria_changes_safety.py`.

**Interfaces:** Consume `HistoricalExportRequest`, `prepare_criteria_comparison(store,state,index)`,
`locked_criteria_comparison(store,selection)`, criteria JSON/Markdown exporters and atomic output.
Produce `export-criteria-changes` with the spec's exact required flags and formats.

- [ ] Write test-first checks for pending/no-active JSON/Markdown handoff, current unconfirmed state,
  full fields/source whitespace, legacy unknown provenance and unchanged acceptance-export refusal,
  duplicate-head/unknown revision selection, invalid/missing/stale/owner inputs and all Review Focus cases.
- [ ] Run `.venv/bin/python -m pytest -q tests/cli/test_criteria_changes.py`; expect missing-command
  failures. Implement the thin handler/parser; keep preparation/consumption locks sequential.
- [ ] Run new CLI tests plus existing history, criteria core/report and ordinary CLI regressions;
  expect all pass with saved bytes unchanged. Commit source, tests, spec and plan.

### Task 2: Installed handoff and reviewed integration

**Files:** Create `tests/cli/test_installed_criteria_changes.py`; modify `.github/workflows/ci.yml`,
README, ROADMAP and release-status record; create dated audit.

**Interfaces:** Consume Task 1 command and existing catalog, run child interpreter with `-I`
outside checkout against an isolated installed wheel. Produce version-bound automatic evidence.

- [ ] Write an installed journey for catalog selection, exact previous/current JSON, Markdown,
  missing-provenance distinction, stale refusal and unchanged saved bytes. Run baseline-wheel RED,
  then current-wheel GREEN; include focused and installed checks in Windows and engineering CI.
- [ ] Align docs with supported behavior and limits. Run full suite at unrounded 95%, lint/lock/diff,
  both deterministic benchmarks, clean installation and existing seventeen browser checks; verify frozen hashes.
- [ ] Obtain fresh independent whole-branch agent review, resolve supported findings with regressions,
  rerun affected checks, require exact-head CI/CodeQL, guarded squash merge and verify clean resulting main.
- [ ] Preserve complete commands/results/review scopes in an external execution packet and archive
  only this task's owned ignored ledger after all required verification succeeds.
