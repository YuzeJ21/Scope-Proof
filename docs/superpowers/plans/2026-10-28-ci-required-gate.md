# Required CI gate implementation plan

> **For agentic workers:** Use superpowers:executing-plans for the bounded implementation and one independent whole-branch review.

**Goal:** Reject every incomplete/non-success CI lane while removing unnecessary serial waiting.

**Architecture:** Preserve the existing expensive verification payload under
`engineering-validation`, scheduled independently. A final required `verify` job always evaluates
all five predecessors and accepts only explicit success from each.

**Tech stack:** GitHub Actions YAML, Bash, pytest, existing actionlint/Ruff.

**Spec:** `docs/superpowers/specs/2026-10-28-ci-required-gate-design.md`.

## Global constraints

Preserve all existing checks, unrounded 95% coverage floor, pinned actions, workflow events,
permissions, diagnostics, branch-protection contexts, product behavior and frozen benchmarks.
No new runtime dependency, human testing, qualifying review, publication, deployment or Stage 3.

## Review focus

- Any one failed, cancelled, skipped, blank or unexpected predecessor must prevent success.
- Missing/unbound result variables and omitted dependencies must not silently pass.
- The costly workload must start independently while retaining every existing step and order.
- The final required check must actually run after dependency failure; no optional/ignored errors.
- Synthetic local status tests establish script behavior, not a demonstrated hosted bypass or
  every possible GitHub cancellation behavior. Report measured timing and these limits.

## Task 1: Executable gate and graph regressions

- [ ] Add `tests/test_ci_gate.py`: parse bounded jobs from the actual workflow, verify exact
  dependency/environment wiring and unconditional aggregate scheduling, execute the actual gate
  script with all-success, per-lane bad statuses, and missing environment inputs.
- [ ] Observe focused graph/positive-script tests fail against the old workflow.

## Task 2: Workflow and existing contracts

- [ ] Rename the expensive job and remove its obsolete `needs`; keep its steps unchanged.
- [ ] Add a final `verify` job with `always()`, exact five dependencies, and strict result checks.
- [ ] Update existing job-bounded contracts to inspect the correct payload and aggregate.
- [ ] Run gate/config tests, Ruff, actionlint, whitespace and deterministic benchmarks.
- [ ] If current supported test tools expose a harness incompatibility, reproduce it and repair
  only fixture naming or fault isolation; preserve assertions, dependencies and frozen inputs.

## Task 3: Review and integration

- [ ] Record baseline timings, scope and remaining roadmap gaps in a dated audit.
- [ ] Obtain independent agent review and resolve supported findings.
- [ ] Create a PR; require the exact final head's full tests/coverage, package/browser,
  compatibility, locked-environment, CodeQL and final aggregate checks to pass.
- [ ] Verify scheduling overlap, merge, confirm resulting main and record its results.

The dated audit and PR checks are the execution ledger and integration evidence.
