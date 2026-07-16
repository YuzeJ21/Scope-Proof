# ScopeProof CI Trigger Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure each feature pull-request SHA runs ScopeProof CI once while every merged main SHA retains an independent full CI run.

**Architecture:** Narrow only the CI workflow's `push` trigger to `main`; leave `pull_request`, permissions, jobs, and checks unchanged. Protect the event topology with a repository contract, then verify the actual GitHub events on the feature and merge SHAs.

**Tech Stack:** GitHub Actions YAML, Python 3.11/3.12, pytest, pytest-cov, Ruff, GitHub CLI.

## Global Constraints

- Work only in the `codex/ci-trigger-deduplication` ScopeProof worktree.
- Preserve the Python 3.11 compatibility job and Python 3.12 `verify` job byte-for-byte outside the trigger header.
- Preserve main branch protection contexts exactly `verify` and `CodeQL`, with strict and administrator enforcement.
- Do not change CodeQL, ScopeProof Action, application behavior, dependencies, version, release, billing, APIs, or monitoring.
- Do not claim that workflow deduplication disables GitHub account email settings; it removes only the duplicate CI execution.

---

### Task 1: Regress and fix duplicate feature-branch CI

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: GitHub Actions `push` and `pull_request` event filters.
- Produces: a main-only push trigger and all-PR trigger contract.

- [ ] **Step 1: Add the failing event-topology contract**

Add this test beside the existing CI contracts:

```python
def test_ci_avoids_duplicate_feature_branch_runs() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "on:\n  push:\n    branches: [main]\n  pull_request:\n" in workflow
```

- [ ] **Step 2: Confirm the red state**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_ci_avoids_duplicate_feature_branch_runs -q
```

Expected: fail because the current `push` trigger has no `branches: [main]` filter.

- [ ] **Step 3: Commit the red contract**

```bash
git add tests/test_repository_contracts.py
git commit -m "test: define non-duplicate CI trigger contract"
```

- [ ] **Step 4: Apply the minimal trigger fix**

Change only the workflow header to:

```yaml
on:
  push:
    branches: [main]
  pull_request:
```

- [ ] **Step 5: Record the unreleased maintenance change**

Add under `CHANGELOG.md` Unreleased / Added:

```markdown
- CI runs feature pull-request SHAs once while retaining an independent full run after merge to
  main.
```

- [ ] **Step 6: Confirm focused and repository-contract green states**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_ci_avoids_duplicate_feature_branch_runs -q
.venv/bin/python -m pytest tests/test_repository_contracts.py -q
```

Expected: the focused test passes, followed by all repository-contract tests passing.

- [ ] **Step 7: Commit the implementation**

```bash
git add .github/workflows/ci.yml CHANGELOG.md
git commit -m "ci: avoid duplicate feature branch runs"
```

### Task 2: Verify code, workflow, and event topology

**Files:**
- Verify only; repair only defects introduced by Task 1.

**Interfaces:**
- Consumes: the updated branch and workflow.
- Produces: local verification plus live GitHub event evidence.

- [ ] **Step 1: Run local gates**

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest \
  --cov=scopeproof_core \
  --cov=apps \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=95 \
  -q
.venv/bin/python -m scopeproof_core.evals.runner
.venv/bin/python -m pip check
ruby -e 'require "yaml"; YAML.load_file(".github/workflows/ci.yml")'
git diff --check
```

Expected: Ruff passes; all tests pass at or above 95% coverage; 12 benchmark cases have zero
mismatches and zero must-have False Ready; dependency and YAML validation pass.

- [ ] **Step 2: Audit the exact diff**

Require only `CHANGELOG.md`, `.github/workflows/ci.yml`, the repository contract, and the approved
spec/plan. Confirm the jobs and permissions are unchanged by comparing the workflow content after
the `permissions:` line against `origin/main`.

- [ ] **Step 3: Publish one ready PR and verify one feature CI event**

Push the branch and open a ready PR. Query all runs for the feature head SHA and require exactly
one run with workflow name `CI`, whose event is `pull_request`; require no `CI` run whose event is
`push`. CodeQL and the intentionally skipped unlabeled ScopeProof workflow are separate workflows
and do not count as duplicate CI.

- [ ] **Step 4: Merge and verify main topology**

After Python 3.11, `verify`, and CodeQL pass, merge the PR. On the merge SHA require exactly one
workflow named `CI` with event `push`, plus successful CodeQL. Confirm branch protection remains
strict, administrator-enforced, and requires exactly `verify` plus `CodeQL`.

- [ ] **Step 5: Clean and resume audit**

Fast-forward local main, remove the owned worktree and local/remote branch, then recheck open PRs,
issue #3 external responses, security/dependency findings, latest release, SHA-pinned Actions, and
documentation drift once. Do not create a recurring monitor.
