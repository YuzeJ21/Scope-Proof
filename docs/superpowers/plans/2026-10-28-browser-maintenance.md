# Browser maintenance implementation plan

> **For agentic workers:** Use superpowers:executing-plans to execute the bounded tasks below.

**Goal:** Repair only browser or application behavior supported by reproduced failures.

**Architecture:** Preserve the core and deterministic gates. Selection-helper regressions use
real Chromium and an isolated constructed Streamlit fixture. Download repairs retain deferred
click-time validation and are conditional on a supported reproduction.

**Tech stack:** Python, pytest, Playwright Chromium, Streamlit.

**Spec:** `docs/superpowers/specs/2026-10-28-browser-maintenance-design.md`.

## Constraints and review focus

- Typed query text is not committed selection; verify a separate server-rendered value.
- Already selected options must not require a nonexistent state-change rerun.
- Unavailable options and unsettled dependent controls must still fail.
- Download fixes must retain click-time stale-store rejection and pending-input guards.
- Preserve the original missing-dropdown finding as unresolved unless its cause is reproduced.
- Use disposable fixtures and loopback-only requests; clean up owned server/browser processes.

## Task 1: Selection helper

- [ ] Add real browser cases for an uncommitted matching query and an already committed option.
- [ ] Observe the query case fail against the unchanged helper.
- [ ] Replace text-only success with explicit selected-option state; retain bounded recovery.
- [ ] Run focused regressions and the existing helper cases.

## Task 2: Deferred-download finding

- [ ] Inspect the preserved trace and reproduce the suspected callable-response/rerun race.
- [ ] If supported, add a regression and remove only the unnecessary download-triggered rerun.
- [ ] Verify that stale persisted review state remains blocked at download time.
- [ ] Record the evidence and limits even if no repair is supported.

## Task 3: Verification and integration

- [ ] Run lint, full coverage suite, deterministic benchmarks, and all packaged browser checks.
- [ ] Align current browser-count wording only if the collected checks change.
- [ ] Obtain independent agent review; resolve supported findings and rerun affected checks.
- [ ] Create a reviewable PR, verify exact-head CI, merge, and verify resulting main.

## Execution evidence

The dated browser audit records reproduction commands, red/green results, revision bindings,
independent review disposition, and limitations. The original 2026-10-27 audit remains historical.
