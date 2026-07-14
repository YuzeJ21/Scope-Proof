# Action-Event Repository Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject noncanonical public GitHub repository identities before the ScopeProof Action can plan or publish a comment.

**Architecture:** Reuse the canonical `owner/repository` Pydantic pattern already enforced by `ActionValidationRecord` on the Action `EventContext` boundary. Exercise direct construction and runner event ingestion while leaving the formatter, publisher, workflow, and HTTP behavior unchanged.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, Hatchling.

## Global Constraints

- Require `^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$` exactly and preserve accepted values without normalization.
- Validate shape only; do not claim the repository exists.
- Keep development version `0.1.17.dev0` and public release `v0.1.16` unchanged.
- Do not alter trusted-base checkout, permissions, fork exclusion, requirements confirmation, head-SHA validation, comment idempotency, publisher behavior, dependencies, billing, APIs, releases, comments, or notifications.
- Never execute pull-request code.

---

### Task 1: Regression-first EventContext repository contract

**Files:**
- Modify: `tests/github_action/test_contract.py`
- Modify: `tests/github_action/test_runner.py`
- Modify: `scopeproof_core/github_action.py:30`

**Interfaces:**
- Consumes: GitHub event `repository.full_name` copied by `_event_context` into `EventContext.repository`.
- Produces: exact supported identity preservation or a Pydantic `string_pattern_mismatch` before planning/publication.

- [ ] **Step 1: Add failing direct-model tests**

In `tests/github_action/test_contract.py`, parameterize these invalid identities:

```python
[
    " / ",
    "ac me/de mo",
    " acme/demo",
    "acme/demo\t",
    "acme/demo/extra",
    "acme@team/demo",
    "acme/demo#repo",
]
```

For each value, construct `EventContext` with the existing valid `HEAD_SHA` and require
`ValueError` matching `string_pattern_mismatch`. Add a preservation test for
`acme-team/demo.repo_name-test`.

- [ ] **Step 2: Add a failing runner-ingestion test**

In `tests/github_action/test_runner.py`, write an event whose `repository.full_name` is
`ac me/de mo` and whose head is the valid `HEAD_SHA`. Require `build_event_plan` to raise
`ValueError` matching `string_pattern_mismatch` before returning a plan.

- [ ] **Step 3: Run focused tests and verify RED**

```bash
'../../.venv/bin/python' -m pytest tests/github_action/test_contract.py tests/github_action/test_runner.py -q
```

Expected: the whitespace and unsupported-character cases plus runner case fail because the current
two-segment pattern accepts them. The extra-segment case may already reject, but must produce the
same final contract error.

- [ ] **Step 4: Implement the minimal field contract**

Replace:

```python
repository: str = Field(pattern=r"^[^/]+/[^/]+$")
```

with:

```python
repository: str = Field(pattern=r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$")
```

- [ ] **Step 5: Run focused tests and Ruff; verify GREEN**

```bash
'../../.venv/bin/python' -m pytest tests/github_action -q
'../../.venv/bin/python' -m ruff check scopeproof_core/github_action.py tests/github_action
git diff --check
```

- [ ] **Step 6: Commit the contract**

```bash
git add scopeproof_core/github_action.py tests/github_action/test_contract.py tests/github_action/test_runner.py
git diff --cached --check
git commit -m "fix: validate Action event repository identity"
```

### Task 2: Source and installed-package verification

**Files:**
- Verify: repository source and a fresh wheel under `/tmp/scopeproof-action-repository-*`.

**Interfaces:**
- Consumes: checked-in source, Pydantic model, event runner, benchmark, and package metadata.
- Produces: source-gate evidence and clean-installed valid/invalid identity probes.

- [ ] **Step 1: Run source gates**

```bash
'../../.venv/bin/python' -m ruff check .
'../../.venv/bin/python' -m pytest -q
'../../.venv/bin/python' -m scopeproof_core.evals.runner
git diff main...HEAD --check
```

Require all tests and Ruff to pass. Require 12 benchmark cases, 13 criteria, zero mismatches, zero
must-have False Ready, and zero false blockers.

- [ ] **Step 2: Build and clean-install the wheel**

Build with `pip wheel . --no-deps`, install in a fresh virtual environment, run `pip check`, verify
version `0.1.17.dev0`, and record wheel SHA-256.

- [ ] **Step 3: Run installed boundary probes**

In the clean environment:

1. construct `EventContext(repository="acme-team/demo.repo_name-test", ...)` and require exact
   preservation;
2. require direct `repository="ac me/de mo"` construction to raise `string_pattern_mismatch`;
3. require `build_event_plan` to reject the same malformed event identity;
4. run the installed benchmark and require every release gate to remain zero.

- [ ] **Step 4: Review the complete diff**

Run the complete diff, `git diff main...HEAD --check`, and placeholder scan. Confirm only the design,
plan, one Pydantic pattern, and focused tests changed.

### Task 3: Protected integration and continuation

**Files:**
- Publish: `codex/action-event-repository-guard`.

**Interfaces:**
- Consumes: fresh passing verification and reviewed diff.
- Produces: a green protected merge, synchronized clean `main`, and the next finite loop.

- [ ] **Step 1: Rerun all source gates immediately before publishing**
- [ ] **Step 2: Push and open a ready PR without reviewers, comments, or release churn**
- [ ] **Step 3: Wait for both `verify` checks, ScopeProof evidence review, and CodeQL; squash-merge only when all are green**
- [ ] **Step 4: Require CI and CodeQL success on the exact merge SHA; fast-forward local `main`, compare trees, and remove the owned worktree/branch**
- [ ] **Step 5: Re-audit live state and rotate into the next evidence-backed product or maintenance gap without marking the persistent goal complete**
