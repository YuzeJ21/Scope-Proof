# Action-Event SHA Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject malformed pull-request head identifiers before the GitHub Action can plan or publish a ScopeProof comment.

**Architecture:** Tighten the existing `EventContext` Pydantic field and migrate only its controlled Action fixtures. Prove both direct-model and event-runner rejection while leaving the formatter and trusted-base workflow unchanged.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, Hatchling.

## Constraints

- Require exact 40-character lowercase hexadecimal shape; do not claim existence.
- Do not change the workflow, permissions, trusted-base checkout, fork policy, requirements gate, publication logic, dependencies, releases, comments, or notifications.
- Never execute pull-request code.

### Task 1: Regression-first EventContext contract

**Files:**
- Modify: `tests/github_action/test_contract.py`
- Modify: `tests/github_action/test_publisher.py`
- Modify: `tests/github_action/test_runner.py`
- Modify: `scopeproof_core/github_action.py`

- [ ] Define `HEAD_SHA = "2" * 40` and `OTHER_SHA = "3" * 40` where needed; migrate Action fixtures and exact marker assertions.
- [ ] Add parameterized direct-model tests for empty, whitespace, abbreviated, non-hex, 39/41-character, and uppercase values, expecting `string_pattern_mismatch`.
- [ ] Add a valid-value preservation test.
- [ ] Add a runner test whose event contains `not-a-sha` and require `build_event_plan` to raise `string_pattern_mismatch` before producing a plan.
- [ ] Run `'../../.venv/bin/python' -m pytest tests/github_action -q` from the isolated worktree and verify RED on the new shape tests.
- [ ] Change `EventContext.head_sha` to `Field(pattern=r"^[0-9a-f]{40}$")`.
- [ ] Rerun focused tests and Ruff; require GREEN.
- [ ] Commit as `fix: validate Action event head SHA`.

### Task 2: Source and package verification

- [ ] Run Ruff, complete pytest, deterministic benchmark, and `git diff main...HEAD --check`.
- [ ] Build `scopeproof-0.1.17.dev0`, clean-install it, run `pip check`, and record wheel SHA-256.
- [ ] In the installed package, require a valid `EventContext` to preserve its SHA and an invalid one to raise `string_pattern_mismatch`.
- [ ] Exercise installed `build_event_plan` with malformed event JSON and require rejection before plan output.
- [ ] Review the complete diff and placeholder scan.

### Task 3: Protected integration and continuation

- [ ] Rerun all source gates immediately before publishing.
- [ ] Push `codex/action-event-sha-guard` and open a ready PR without reviewers, comments, or release churn.
- [ ] Wait for every protected `verify`, ScopeProof evidence review, and CodeQL check; squash-merge only when green.
- [ ] Require CI and CodeQL success on the exact merge SHA, fast-forward local `main`, compare trees, and clean the owned worktree/branch.
- [ ] Re-audit live state and rotate into the next evidence-backed bounded loop without marking the persistent goal complete.
