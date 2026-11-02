# Saved pending-analysis continuation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this bounded task.

**Goal:** Continue a reopened confirmed criteria revision in the same saved review without inherited decisions.

**Architecture:** Extend the existing source-attachment service for confirmed pending revisions, bind
their entire state, and commit fresh analysis through the existing locked store. Keep workbench orchestration thin.

**Tech Stack:** Existing Python, Pydantic, Streamlit AppTest and installed-wheel Playwright; no dependencies.

**Spec:** docs/superpowers/specs/2026-11-02-pending-analysis-continuation-design.md

## Global constraints

Record9 and source0.2.5 unreleased; frozen R-002 unchanged. No gate changes, inferred confirmation,
target code execution, personal/qualifying testing, release/deploy/outreach or Stage3 claims.
Source restoration remains8files/200,000UTF-8bytes; existing origin and complete-inventory rules apply.

## Review focus

1. Multiple retained analyses: only the latest matching source anchor may supply unchanged paths.
2. Pending full-state changes during fetch/analysis: reject without overwriting another saved update.
3. Existing active-analysis neutral actions: retain compatibility and reference reproduction checks.
4. New analysis: preserve complete historical audit while carrying no prior manual/runtime/import context.
5. Commit errors/queued controls: no unsaved success, source lease reuse or fallback to a different head.

### Task 1: Restore the complete saved revision workflow

**Files:** core reviews/source_attachment.py; apps/web/source_attachment.py and app.py;
tests/reviews/test_pending_source_continuation.py; tests/apps/test_pending_source_continuation.py;
tests/browser/test_pending_source_continuation.py; Windows continuation step in .github/workflows/ci.yml;
README/ROADMAP/status record and bounded audit.

**Interfaces:** Consume existing prepare_saved_source_attachment/validate_source_attachment and
attach_analysis. Extend confirmed pending support without changing signatures. Produce
attach_saved_pending_analysis(store,current,bundle,*,attachment,snapshot,candidate_files)->ReviewState,
which validates full pending receipt and atomically installs fresh analysis. No schema/writer change.

- [ ] Write tests for confirmed pending attachment and real reopen/confirm/load/analyze UI path.
  Assert unchanged saved bytes on load, same ID/revision/history on analysis and clean fresh context.
- [ ] Run those tests before source changes; expect failures because pending attachment is rejected.
- [ ] Extend source anchor validation and pending full-state lease, preserving existing active path.
  Implement locked analysis completion; integrate explicit source requirements/session synchronization.
- [ ] Add negative source/anchor/receipt/race/write-failure and confirmation tests, plus positive old
  active attachment controls. Run core/AppTest source suites; expect all pass.
- [ ] Add installed browser journey with constructed offline origin: reopen active, explicitly change
  and confirm criterion, restore matching source, run analysis, restart/reopen/export. Assert exact
  history retention and current new revision with no copied prior evidence/decisions. Expect pass.
- [ ] Refresh roadmap/status/README with this selected outcome, deferred alternatives and limits.
- [ ] Run full pytest core/apps coverage with unchanged unrounded>=95%, Ruff, lock, source/installed
  12+2 deterministic benchmarks, package hash/clean-install/browser and frozen7 checks. Expect pass.
- [ ] Commit and push codex branch, open reviewable PR, dispatch one fresh whole-branch agent review.
  Fix supported findings by RED/GREEN, rerun affected/full checks if code changes, and await exact-head
  CI including installed browser and Python/Windows compatibility. Expect required checks success.
- [ ] Guarded merge, synchronize main, await resulting-main CI/CodeQL, record commands/results and
  close goal. Final task-done command validates source-bound verification artifacts rather than
  repeating an unchanged full suite after an identical-tree merge. Expect clean main and no pending work.
