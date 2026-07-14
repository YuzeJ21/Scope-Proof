# Confirmed Criteria Analysis Cue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development and test-driven-development.

**Goal:** Make the enabled deterministic-analysis action discoverable immediately
after criteria confirmation without changing analysis behavior.

## Task 1: Add the transition contract and minimal cue

**Files:** `tests/apps/test_streamlit_app.py`, `apps/web/app.py`.

1. Add a focused AppTest that loads the demo and proves the continuation link is
   absent before confirmation, present after valid confirmation with the exact
   `#run-deterministic-analysis` target, absent for pending edits, and absent
   after analysis.
2. Run the focused test before implementation and require RED.
3. Add a placeholder immediately below the evidence-level caption. Fill it only
   when the already-computed `analysis_disabled` value is false.
4. Add `### Run deterministic analysis` directly before the existing button.
5. Run the focused test and adjacent transition tests; require GREEN.
6. Run Ruff and `git diff --check`; commit as
   `Add confirmed criteria analysis cue`.

## Task 2: Verify and integrate

1. Independently review spec compliance and task quality.
2. Run Ruff, complete pytest, deterministic benchmark, and diff checks.
3. Build/install an archived wheel and reproduce the confirmation transition in
   a fresh-HOME browser at 1280 by 720; save and inspect the result.
4. Push one `codex/` branch, open one ready PR, require both `verify` checks and
   CodeQL Python/Actions, then merge.
5. Fast-forward exact main; rerun local and remote exact-main gates.
6. Do not publish another release in this loop; v0.1.18 remains the current
   meaningful batch release.
